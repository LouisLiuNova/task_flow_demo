"""
The global config of the app
"""

from dataclasses import dataclass
import os

from dotenv import load_dotenv

# 加载.env文件（仅开发环境生效，生产环境会自动读取系统环境变量）
# 参数override=True表示：系统环境变量优先级高于.env文件
load_dotenv(override=True)


@dataclass
class DatabaseConfig:
    url: str = os.getenv("DATABASE_URL")


@dataclass
class TaskConfig:
    QPS: int = int(os.getenv("QPS", 100))
    FAIL_RATE: float = float(os.getenv("FAIL_RATE", 0.2))
    MAX_RETRY: int = int(os.getenv("MAX_RETRY", 3))
    TIMEOUT_THRESHOLD: int = int(os.getenv("TIMEOUT_THRESHOLD", 30))
    MAX_TIME: int = int(os.getenv("MAX_TIME", 40))
    MIN_TIME: int = int(os.getenv("MIN_TIME", 5))
    SERVICE_ROLE: str | None = os.getenv("SERVICE_ROLE")


@dataclass
class KafkaConfig:
    BOOTSTRAP_SERVERS: str = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    TASK_TOPIC: str = os.getenv("KAFKA_TASK_TOPIC", "task_input")
    RESULT_TOPIC: str = os.getenv("KAFKA_RESULT_TOPIC", "task_result")
    CONSUMER_GROUP: str = os.getenv("KAFKA_CONSUMER_GROUP", "task_flow_demo")


@dataclass
class RedisConfig:
    URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    RESULT_CHANNEL: str = os.getenv("REDIS_RESULT_CHANNEL", "task_result_channel")


@dataclass
class CeleryConfig:
    BROKER_URL: str = os.getenv(
        "CELERY_BROKER_URL", os.getenv("REDIS_URL", "redis://localhost:6379/0")
    )
    BACKEND_URL: str = os.getenv(
        "CELERY_BACKEND_URL", os.getenv("REDIS_URL", "redis://localhost:6379/0")
    )
    QUEUE: str | None = os.getenv("CELERY_QUEUE")
    DEFAULT_QUEUE: str | None = os.getenv("CELERY_DEFAULT_QUEUE")
    WORKER_TASK_TYPE: str | None = os.getenv("CELERY_WORKER_TASK_TYPE")


@dataclass
class LogConfig:
    LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    FORMAT: str = os.getenv(
        "LOG_FORMAT",
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>",
    )
    FILE_PATH: str | None = os.getenv("LOG_FILE_PATH")
    ROTATION: str = os.getenv("LOG_ROTATION", "10 MB")
    RETENTION: str = os.getenv("LOG_RETENTION", "7 days")


# 导出便捷的配置对象（推荐）
db_config = DatabaseConfig()
task_config = TaskConfig()
kafka_config = KafkaConfig()
redis_config = RedisConfig()
celery_config = CeleryConfig()
log_config = LogConfig()
