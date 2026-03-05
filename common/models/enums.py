from enum import StrEnum

from pydantic import BaseModel, Field


class TaskStatus(StrEnum):
    """
    Task status enum
    """

    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"


class TaskType(StrEnum):
    QUERY = "query"
    WRITE = "write"
    DELETE = "delete"
