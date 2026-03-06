"""
To register service the container may provide. Use decorator to register service.
"""

from typing import Callable, Dict, Any, Type

# 扩展注册表类型：支持存储函数（Callable）或类（Type）
ServiceRegistry = Dict[str, Dict[str, Any]]


class ServiceManager:
    """增强版服务管理类：支持注册函数/类，保持原有功能兼容"""

    _registry: ServiceRegistry = {}

    @classmethod
    def register_service(cls, service_name: str = None, **metadata) -> Callable:
        """
        通用注册装饰器：支持装饰函数/类
        :param service_name: 自定义服务名，默认用函数/类名
        :param metadata: 服务元数据（描述、版本等）
        :return: 装饰器（兼容函数/类）
        """

        def decorator(obj: Callable | Type) -> Callable | Type:
            # 确定服务名：优先自定义，否则用对象名（函数/类的__name__）
            actual_name = service_name or obj.__name__

            # 统一存储：区分对象类型（函数/类），便于后续处理
            cls._registry[actual_name] = {
                "obj": obj,  # 存储函数/类对象
                "type": (
                    "function"
                    if callable(obj) and not isinstance(obj, type)
                    else "class"
                ),
                "metadata": metadata,
                "name": obj.__name__,
            }

            # 装饰器返回原对象（函数/类），不改变其原有特性
            return obj

        return decorator

    @classmethod
    def discover_service(cls, service_name: str) -> Callable | Type:
        """
        通用服务发现：返回注册的函数/类对象
        :param service_name: 服务名
        :raises KeyError: 服务未注册时抛出异常
        """
        if service_name not in cls._registry:
            raise KeyError(f"服务 {service_name} 未注册")
        return cls._registry[service_name]["obj"]

    @classmethod
    def list_all_services(cls) -> ServiceRegistry:
        """列出所有服务，包含对象类型信息"""
        return cls._registry.copy()

    @classmethod
    def unregister_service(cls, service_name: str) -> None:
        """注销服务（兼容函数/类）"""
        if service_name in cls._registry:
            del cls._registry[service_name]
            print(f"服务 {service_name} 已注销")
        else:
            print(f"服务 {service_name} 不存在")
