"""
Generate tasks flow randomly with configured QPS and loss rate
"""

import random
import time
from collections.abc import Iterator

from common.config import app_config
from common.models.enums import TaskType
from common.models.task import Task


def generate_task() -> Task:
    """
    Generate a task randomly with configured QPS and loss rate
    """
    if_success = random.random() > app_config.FAIL_RATE
    execution_time = random.randint(app_config.MIN_TIME, app_config.MAX_TIME)
    return Task(
        task_type=random.choice(list(TaskType)),
        if_success=if_success,
        execution_time=execution_time,
    )


def produce_tasks() -> Iterator[Task]:
    """
    按配置的 QPS 持续输出任务，使用单调时钟对齐节奏，支持动态 QPS 调整。

    当 QPS 小于等于 0 时会短暂休眠并等待恢复；每次产生一个 Task 后推进下一次
    目标发送时间，避免累计漂移。按 Ctrl+C 中断生成循环。
    """
    interval = None
    next_emit_time = time.perf_counter()
    while True:
        try:
            qps = app_config.QPS
            if qps <= 0:
                time.sleep(0.1)
                next_emit_time = time.perf_counter()
                interval = None
                continue
            new_interval = 1.0 / qps
            if interval is None or abs(new_interval - interval) > 1e-12:
                interval = new_interval
                next_emit_time = time.perf_counter() + interval
            now = time.perf_counter()
            if now < next_emit_time:
                time.sleep(next_emit_time - now)
            else:
                if now - next_emit_time > interval:
                    next_emit_time = now
            yield generate_task()
            next_emit_time += interval
        except KeyboardInterrupt:
            break
