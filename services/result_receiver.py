"""
Compatibility module for legacy imports.
"""

from __future__ import annotations

from services.result_display import consume_kafka_results
from services.result_proxy import consume_celery_results

__all__ = ["consume_celery_results", "consume_kafka_results"]
