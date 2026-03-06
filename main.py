import importlib
import sys

from celery import Celery

from common import logger
from common.config import task_config
from services.registry import ServiceManager

SERVICE_MODULES = (
    "services.task_generator",
    "services.router",
    "services.worker",
    "services.result_proxy",
    "services.result_display",
)

ROLE_ALIASES = {
    "generator": "task_gen_and_push",
    "task_gen_and_push": "task_gen_and_push",
    "router": "task_router",
    "task_router": "task_router",
    "worker": "task_worker",
    "task_worker": "task_worker",
    "result_receiver": "task_result_proxy",
    "result_proxy": "task_result_proxy",
    "task_result_proxy": "task_result_proxy",
    "result_viewer": "task_result_viewer",
    "result_display": "task_result_viewer",
    "task_result_viewer": "task_result_viewer",
}


def _register_services() -> None:
    for module_name in SERVICE_MODULES:
        importlib.import_module(module_name)


def _resolve_service_name(role: str | None) -> str | None:
    if role is None:
        return None
    normalized = role.strip().lower()
    if not normalized:
        return None
    return ROLE_ALIASES.get(normalized, normalized)


def _available_services() -> str:
    services = sorted(ServiceManager.list_all_services().keys())
    return ", ".join(services)


def _run_service(service_name: str) -> None:
    service = ServiceManager.discover_service(service_name)
    result = service()
    if isinstance(result, Celery):
        result.worker_main(argv=["worker", "--loglevel=info"])


def main() -> None:
    _register_services()
    service_name = _resolve_service_name(task_config.SERVICE_ROLE)
    if not service_name:
        logger.error(
            "SERVICE_ROLE not set, available services: {}", _available_services()
        )
        sys.exit(1)
    try:
        logger.info("start service role: {}", service_name)
        _run_service(service_name)
    except KeyError:
        logger.error(
            "unknown SERVICE_ROLE: {}, available services: {}",
            service_name,
            _available_services(),
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
