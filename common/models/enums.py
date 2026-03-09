from enum import StrEnum


class TaskStatus(StrEnum):
    """
    Task status enum
    """

    PENDING = "pending"
    ROUTED = "routed"
    EXECUTING = "executing"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"


class TaskType(StrEnum):
    QUERY = "query"
    WRITE = "write"
    DELETE = "delete"
