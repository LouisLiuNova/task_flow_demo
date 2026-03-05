import sys

from loguru import logger as _logger

from common.config import log_config

_logger.remove()
_logger.add(
    sys.stdout,
    level=log_config.LEVEL,
    format=log_config.FORMAT,
    enqueue=True,
    backtrace=False,
    diagnose=False,
)

if log_config.FILE_PATH:
    _logger.add(
        log_config.FILE_PATH,
        level=log_config.LEVEL,
        format=log_config.FORMAT,
        enqueue=True,
        backtrace=False,
        diagnose=False,
        rotation=log_config.ROTATION,
        retention=log_config.RETENTION,
    )

logger = _logger
