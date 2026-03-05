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
class AppConfig:
    QPS: int = int(os.getenv("QPS", 100))
    FAIL_RATE: float = float(os.getenv("FAIL_RATE", 0.2))
    MAX_RETRY: int = int(os.getenv("MAX_RETRY", 3))
    TIMEOUT_THRESHOLD: int = int(os.getenv("TIMEOUT_THRESHOLD", 30))
    MAX_TIME: int = int(os.getenv("MAX_TIME", 40))
    MIN_TIME: int = int(os.getenv("MIN_TIME", 5))


@dataclass
class KafkaConfig:
    BOOTSTRAP_SERVERS: str = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    TASK_TOPIC: str = os.getenv("KAFKA_TASK_TOPIC", "task_input")
    RESULT_TOPIC: str = os.getenv("KAFKA_RESULT_TOPIC", "task_result")
    CONSUMER_GROUP: str = os.getenv("KAFKA_CONSUMER_GROUP", "task_flow_demo")


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
app_config = AppConfig()
kafka_config = KafkaConfig()
log_config = LogConfig()
