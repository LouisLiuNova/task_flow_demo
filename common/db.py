"""
SQLite database module for task state persistence.
Provides database connection, table initialization, and CRUD operations.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import (
    Column,
    DateTime,
    String,
    Integer,
    Boolean,
    Float,
    create_engine,
    text,
)
from sqlalchemy.orm import sessionmaker, Session, declarative_base

from common import logger
from common.config import db_config
from common.models.enums import TaskStatus, TaskType

Base = declarative_base()


class TaskState(Base):
    """
    Task state table definition.
    
    Columns:
        - id: UUID, primary key
        - task_type: Task type (query/write/delete)
        - task_name: Task name
        - if_success: Whether the task should succeed (simulated)
        - execution_time: Expected execution time in seconds
        - status: Current task status (pending/routed/executing/success/failed/timeout)
        - queue_name: Target queue name after routing
        - worker_hostname: Worker hostname that executed the task
        - result: JSON-serialized result data
        - exception: Error message if failed
        - traceback: Stack trace if failed
        - created_at: Record creation timestamp
        - updated_at: Record last update timestamp
    """
    __tablename__ = "task_states"

    id = Column(String(36), primary_key=True)
    task_type = Column(String(20), nullable=False)
    task_name = Column(String(255))
    if_success = Column(Boolean, default=True)
    execution_time = Column(Integer, nullable=False)
    status = Column(String(20), nullable=False, default=TaskStatus.PENDING.value)
    queue_name = Column(String(50))
    worker_hostname = Column(String(255))
    result = Column(String(1024))
    exception = Column(String(1024))
    traceback = Column(String(4096))
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)


class DatabaseManager:
    """Database connection and session management."""

    def __init__(self, database_url: str | None = None, echo: bool = False):
        self.database_url = database_url or db_config.url
        self.echo = echo or db_config.echo
        self.engine = create_engine(
            self.database_url,
            echo=self.echo,
            future=True,
        )
        self.SessionLocal = sessionmaker(
            bind=self.engine, autocommit=False, autoflush=False, future=True
        )

    def init_db(self) -> None:
        """Initialize database tables."""
        Base.metadata.create_all(bind=self.engine)
        logger.info("database tables initialized")

    def get_session(self) -> Session:
        """Get a database session."""
        return self.SessionLocal()


# Global database manager instance
db_manager = DatabaseManager()


def get_session() -> Session:
    """Get a database session from global manager."""
    return db_manager.get_session()


def init_tables() -> None:
    """Initialize all tables."""
    db_manager.init_db()


class TaskStateCRUD:
    """CRUD operations for TaskState table."""

    @staticmethod
    def create_task_state(session: Session, task_data: dict[str, Any]) -> TaskState:
        """
        Create a new task state record.
        
        Args:
            session: Database session
            task_data: Task data dictionary containing:
                - id: UUID or str
                - task_type: TaskType or str
                - task_name: str (optional)
                - if_success: bool
                - execution_time: int
            
        Returns:
            Created TaskState instance
        """
        now = datetime.now(timezone.utc)
        task_id = task_data.get("id")
        if isinstance(task_id, UUID):
            task_id = str(task_id)

        task_type = task_data.get("task_type")
        if isinstance(task_type, TaskType):
            task_type = task_type.value

        task_state = TaskState(
            id=task_id,
            task_type=task_type,
            task_name=task_data.get("task_name"),
            if_success=task_data.get("if_success", True),
            execution_time=task_data.get("execution_time", 0),
            status=TaskStatus.PENDING.value,
            created_at=now,
            updated_at=now,
        )
        session.add(task_state)
        session.commit()
        session.refresh(task_state)
        logger.debug("task state created: id={}, status={}", task_state.id, task_state.status)
        return task_state

    @staticmethod
    def get_task_state(session: Session, task_id: str) -> TaskState | None:
        """
        Get a task state by ID.
        
        Args:
            session: Database session
            task_id: Task UUID as string
            
        Returns:
            TaskState instance or None if not found
        """
        return session.get(TaskState, task_id)

    @staticmethod
    def update_task_status(
        session: Session,
        task_id: str,
        status: TaskStatus,
        **kwargs: Any,
    ) -> TaskState | None:
        """
        Update task status and optional fields.
        
        Args:
            session: Database session
            task_id: Task UUID as string
            status: New TaskStatus
            **kwargs: Additional fields to update (queue_name, worker_hostname, result, exception, traceback)
            
        Returns:
            Updated TaskState instance or None if not found
        """
        task_state = session.get(TaskState, task_id)
        if task_state is None:
            logger.warning("task state not found: id={}", task_id)
            return None

        task_state.status = status.value
        task_state.updated_at = datetime.now(timezone.utc)

        for key, value in kwargs.items():
            if hasattr(task_state, key):
                if key in ("result", "exception", "traceback") and value is not None:
                    value = str(value)
                setattr(task_state, key, value)

        session.commit()
        session.refresh(task_state)
        logger.debug(
            "task state updated: id={}, status={}, queue_name={}",
            task_state.id,
            task_state.status,
            task_state.queue_name,
        )
        return task_state

    @staticmethod
    def mark_as_routed(
        session: Session,
        task_id: str,
        queue_name: str,
    ) -> TaskState | None:
        """Mark task as routed after successful queue assignment."""
        return TaskStateCRUD.update_task_status(
            session,
            task_id,
            TaskStatus.ROUTED,
            queue_name=queue_name,
        )

    @staticmethod
    def mark_as_executing(
        session: Session,
        task_id: str,
        worker_hostname: str,
    ) -> TaskState | None:
        """Mark task as executing when worker starts processing."""
        return TaskStateCRUD.update_task_status(
            session,
            task_id,
            TaskStatus.EXECUTING,
            worker_hostname=worker_hostname,
        )

    @staticmethod
    def mark_as_success(
        session: Session,
        task_id: str,
        result: dict[str, Any],
    ) -> TaskState | None:
        """Mark task as successfully completed."""
        return TaskStateCRUD.update_task_status(
            session,
            task_id,
            TaskStatus.SUCCESS,
            result=json.dumps(result, ensure_ascii=False, default=str),
        )

    @staticmethod
    def mark_as_failed(
        session: Session,
        task_id: str,
        exception: str,
        traceback: str | None = None,
    ) -> TaskState | None:
        """Mark task as failed."""
        return TaskStateCRUD.update_task_status(
            session,
            task_id,
            TaskStatus.FAILED,
            exception=exception,
            traceback=traceback,
        )

    @staticmethod
    def mark_as_timeout(
        session: Session,
        task_id: str,
        exception: str,
        traceback: str | None = None,
    ) -> TaskState | None:
        """Mark task as timed out."""
        return TaskStateCRUD.update_task_status(
            session,
            task_id,
            TaskStatus.TIMEOUT,
            exception=exception,
            traceback=traceback,
        )
