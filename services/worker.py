"""
Celery worker 任务执行入口，按环境变量选择队列并模拟任务执行。
"""

from __future__ import annotations

import time
from typing import Any

from celery import Celery
from kombu import Queue

from common import logger
from common.config import celery_config, task_config
from common.models.enums import TaskType
from common.models.task import Task
from services.registry import ServiceManager


def _resolve_queue_name() -> str:
    """
    解析 worker 绑定的 Celery 队列名称。
    """
    queue_name = celery_config.QUEUE
    if queue_name:
        return queue_name
    task_type = celery_config.WORKER_TASK_TYPE
    if task_type:
        try:
            return f"{TaskType(task_type).value}_queue"
        except ValueError:
            logger.warning("invalid WORKER_TASK_TYPE: {}", task_type)
    return celery_config.DEFAULT_QUEUE or f"{TaskType.QUERY.value}_queue"


def _build_celery_app(queue_name: str) -> Celery:
    """
    创建 Celery 应用并绑定到指定队列。
    """
    app = Celery(
        "task_flow_worker",
        broker=celery_config.BROKER_URL,
        backend=celery_config.BACKEND_URL,
    )
    app.conf.update(
        task_default_queue=queue_name,
        task_queues=(Queue(queue_name),),
        worker_send_task_events=True,
        task_send_sent_event=True,
    )
    logger.info(
        "celery worker bound to queue: {}, timeout_threshold: {}s",
        queue_name,
        task_config.TIMEOUT_THRESHOLD,
    )
    return app


def _parse_task(task_payload: Task | dict[str, Any]) -> Task:
    """
    将任务负载解析为 Task 对象。
    """
    if isinstance(task_payload, Task):
        return task_payload
    return Task.model_validate(task_payload)


def _simulate_execution(task: Task) -> dict[str, Any]:
    """
    模拟任务执行，并根据配置判断成功或失败。
    """
    timeout_threshold = task_config.TIMEOUT_THRESHOLD
    execution_time = task.execution_time
    logger.info(
        "task received id={}, type={}, if_success={}, execution_time={}s",
        task.id,
        task.task_type,
        task.if_success,
        execution_time,
    )
    sleep_time = max(0, execution_time)
    if sleep_time != execution_time:
        logger.warning("task id={} execution_time < 0, normalized to 0", task.id)
    logger.info("task id={} start execution sleep {}s", task.id, sleep_time)
    time.sleep(sleep_time)
    if execution_time > timeout_threshold:
        message = (
            f"task id={task.id} timeout: execution_time={execution_time}s "
            f"threshold={timeout_threshold}s"
        )
        logger.error(message)
        raise TimeoutError(message)
    if not task.if_success:
        message = f"task id={task.id} failed by if_success=false"
        logger.error(message)
        raise RuntimeError(message)
    logger.info("task id={} success", task.id)
    return {
        "task_id": str(task.id),
        "task_type": task.task_type,
        "execution_time": execution_time,
        "status": "success",
    }


queue_name = _resolve_queue_name()
app = _build_celery_app(queue_name)


@app.task(name=TaskType.QUERY.value)
def run_query(task: dict[str, Any]) -> dict[str, Any]:
    """
    执行 query 类型任务。
    """
    return _simulate_execution(_parse_task(task))


@app.task(name=TaskType.WRITE.value)
def run_write(task: dict[str, Any]) -> dict[str, Any]:
    """
    执行 write 类型任务。
    """
    return _simulate_execution(_parse_task(task))


@app.task(name=TaskType.DELETE.value)
def run_delete(task: dict[str, Any]) -> dict[str, Any]:
    """
    执行 delete 类型任务。
    """
    return _simulate_execution(_parse_task(task))


@ServiceManager.register_service(service_name="task_worker")
def get_worker_app() -> Celery:
    """
    获取已配置的 Celery worker 应用。
    """
    return app
