"""
To define a task
"""

from random import randint
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from common.config import task_config
from common.models.enums import TaskStatus, TaskType


class Task(BaseModel):
    """
    A task definition
    """

    id: UUID = Field(default_factory=uuid4)
    task_type: TaskType = Field(default=TaskType.QUERY)
    if_success: bool = Field(
        description="If the task can be processed successfully", default=True
    )
    execution_time: int = Field(
        description="The execution time of the task in seconds",
        default_factory=lambda: randint(task_config.MIN_TIME, task_config.MAX_TIME),
    )
