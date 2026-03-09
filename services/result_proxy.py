"""
Consume Celery task results, log them, and publish to Kafka.
"""

from __future__ import annotations

import json
import re
from typing import Any

from celery import Celery
from celery.events import EventReceiver
from confluent_kafka import Producer

from common import logger
from common.config import kafka_config, redis_config
from services.registry import ServiceManager


def _build_celery_app() -> Celery:
    return Celery(
        "task_flow_result_proxy",
        broker=redis_config.URL,
        backend=redis_config.URL,
    )


def _build_kafka_producer() -> Producer:
    return Producer({"bootstrap.servers": kafka_config.BOOTSTRAP_SERVERS})


def _serialize_payload(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8")


def _extract_result(app: Celery, task_id: str | None) -> tuple[Any | None, str | None]:
    if not task_id:
        return None, None
    async_result = app.AsyncResult(task_id)
    if async_result.successful():
        return async_result.result, None
    if async_result.failed():
        return None, str(async_result.result)
    return async_result.result, None


def _resolve_task_name(
    event: dict[str, Any], result: Any, exception: Any, task_id: str | None
) -> str | None:
    event_name = event.get("name")
    if isinstance(event_name, str) and event_name:
        return event_name
    task_type = _extract_task_type(result)
    if task_type is None:
        routing_key = event.get("routing_key")
        if isinstance(routing_key, str) and routing_key:
            task_type = (
                routing_key.removesuffix("_queue")
                if routing_key.endswith("_queue")
                else routing_key
            )
    if task_type is None:
        task_type = _extract_task_type_from_traceback(event.get("traceback"))
    business_task_id = _extract_business_task_id(result, exception, task_id)
    if task_type and business_task_id:
        return f"{task_type}_{business_task_id}"
    return None


def _extract_task_type(result: Any) -> str | None:
    if isinstance(result, dict):
        raw_task_type = result.get("task_type")
        if raw_task_type:
            return str(raw_task_type)
        return None
    if isinstance(result, str):
        try:
            parsed = json.loads(result)
        except json.JSONDecodeError:
            return None
        if isinstance(parsed, dict):
            raw_task_type = parsed.get("task_type")
            if raw_task_type:
                return str(raw_task_type)
    return None


def _extract_task_type_from_traceback(traceback: Any) -> str | None:
    if not isinstance(traceback, str):
        return None
    match = re.search(r"\bin run_(query|write|delete)\b", traceback)
    if not match:
        return None
    return match.group(1)


def _extract_business_task_id(
    result: Any, exception: Any, task_id: str | None
) -> str | None:
    if isinstance(result, dict):
        raw_task_id = result.get("task_id")
        if raw_task_id:
            return str(raw_task_id)
    candidates = [exception, result]
    for candidate in candidates:
        if not isinstance(candidate, str):
            continue
        match = re.search(
            r"\btask id=([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})\b",
            candidate,
        )
        if match:
            return match.group(1)
    return task_id


def _build_payload(app: Celery, event: dict[str, Any]) -> dict[str, Any]:
    event_type = event.get("type")
    task_id = event.get("uuid")
    result = event.get("result")
    exception = event.get("exception")
    fallback_result, fallback_exception = _extract_result(app, task_id)
    if result is None and exception is None:
        result = fallback_result
        exception = fallback_exception
    task_name = _resolve_task_name(event, result, exception, task_id)
    if task_name is None:
        task_name = _resolve_task_name(
            event, fallback_result, fallback_exception, task_id
        )
    return {
        "event_type": event_type,
        "task_id": task_id,
        "task_name": task_name,
        "status": "success" if event_type == "task-succeeded" else "failed",
        "result": result,
        "exception": exception,
        "traceback": event.get("traceback"),
        "runtime": event.get("runtime"),
        "timestamp": event.get("timestamp"),
        "hostname": event.get("hostname"),
    }


@ServiceManager.register_service(service_name="task_result_proxy")
def consume_celery_results(
    celery_app: Celery | None = None,
    kafka_producer: Producer | None = None,
    topic: str | None = None,
) -> None:
    app = celery_app or _build_celery_app()
    producer = kafka_producer or _build_kafka_producer()
    target_topic = topic or kafka_config.RESULT_TOPIC
    logger.info(
        "start consume celery results, publish to kafka topic: {}", target_topic
    )

    def _handle_event(event: dict[str, Any]) -> None:
        payload = _build_payload(app, event)
        logger.info(
            "celery result received task_id={}, task_name={}, status={}, runtime={}",
            payload.get("task_id"),
            payload.get("task_name"),
            payload.get("status"),
            payload.get("runtime"),
        )
        producer.produce(target_topic, _serialize_payload(payload))
        producer.poll(0)

    try:
        with app.connection() as connection:
            receiver = EventReceiver(
                connection,
                handlers={
                    "task-succeeded": _handle_event,
                    "task-failed": _handle_event,
                },
            )
            receiver.capture(limit=None, timeout=None, wakeup=True)
    except KeyboardInterrupt:
        pass
    finally:
        producer.flush()
