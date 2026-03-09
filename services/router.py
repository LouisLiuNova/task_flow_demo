from __future__ import annotations

from celery import Celery
from confluent_kafka import Consumer
from pydantic import ValidationError

from common import logger
from common.config import kafka_config, redis_config
from common.db import TaskStateCRUD, init_tables, get_session
from common.models.enums import TaskType
from common.models.task import Task
from services.registry import ServiceManager


def _build_celery_app() -> Celery:
    broker_url = redis_config.URL
    backend_url = redis_config.URL
    return Celery("task_flow_router", broker=broker_url, backend=backend_url)


def _queue_for_task_type(task_type: TaskType) -> str:
    return f"{task_type.value}_queue"


def _task_name_for_task_type(task_type: TaskType) -> str:
    return task_type.value


@ServiceManager.register_service(service_name="task_router")
def consume_and_route_tasks(
    consumer: Consumer | None = None,
    celery_app: Celery | None = None,
    topic: str | None = None,
) -> None:
    # Initialize database tables
    init_tables()
    
    kafka_consumer = consumer or Consumer(
        {
            "bootstrap.servers": kafka_config.BOOTSTRAP_SERVERS,
            "group.id": kafka_config.CONSUMER_GROUP,
            "auto.offset.reset": "earliest",
            "enable.auto.commit": False,
        }
    )
    target_topic = topic or kafka_config.TASK_TOPIC
    app = celery_app or _build_celery_app()
    kafka_consumer.subscribe([target_topic])
    logger.info("start consume tasks from kafka topic: {}", target_topic)
    try:
        while True:
            message = kafka_consumer.poll(1.0)
            if message is None:
                continue
            if message.error():
                logger.error("kafka consume error: {}", message.error())
                continue
            try:
                task = Task.model_validate_json(message.value())
            except ValidationError as exc:
                logger.error("invalid task payload: {}", exc)
                kafka_consumer.commit(message=message, asynchronous=False)
                continue
            
            # Create task state record in SQLite
            try:
                with get_session() as session:
                    TaskStateCRUD.create_task_state(session, task.model_dump())
                    logger.debug("task state created in db: id={}", task.id)
            except Exception as db_exc:
                logger.error("failed to create task state: {}", db_exc)
            
            queue_name = _queue_for_task_type(task.task_type)
            task_name = _task_name_for_task_type(task.task_type)
            app.send_task(
                task_name, kwargs={"task": task.model_dump()}, queue=queue_name
            )
            
            # Update task status to ROUTED after successful send
            try:
                with get_session() as session:
                    TaskStateCRUD.mark_as_routed(session, str(task.id), queue_name)
                    logger.debug("task marked as routed: id={}, queue={}", task.id, queue_name)
            except Exception as db_exc:
                logger.error("failed to update task status to routed: {}", db_exc)
            
            kafka_consumer.commit(message=message, asynchronous=False)
    except KeyboardInterrupt:
        pass
    finally:
        kafka_consumer.close()
