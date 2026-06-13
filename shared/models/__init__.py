"""
Models 包 - 懒加载版本

所有模型类通过 __getattr__ 按需导入，避免启动时一次性加载所有模型文件。
Base 保持立即导入（SQLAlchemy 元数据初始化必需）。

由代码生成器自动生成 - 请勿手动修改
"""

from sqlalchemy.orm import declarative_base

Base = declarative_base()

# ==================== 懒加载映射表 ====================
# 模型名 -> 相对模块路径（不含 shared.models 前缀）
_LAZY_IMPORTS = {
    'Notification': '.notification.notification',
}

# 已加载的模型缓存（避免重复导入）
_loaded_models = {}


def __getattr__(name):
    """模块级 __getattr__：按需懒加载模型类"""
    if name in _loaded_models:
        return _loaded_models[name]

    module_path = _LAZY_IMPORTS.get(name)
    if module_path is not None:
        import importlib
        module = importlib.import_module(module_path, package='shared.models')
        cls = getattr(module, name)
        # 缓存到模块命名空间，后续访问直接命中
        globals()[name] = cls
        _loaded_models[name] = cls
        return cls

    raise AttributeError(f"module 'shared.models' has no attribute {name!r}")


# ==================== 自动生成 - __all__ ====================
# 此部分由脚本自动生成 - 请勿手动修改

__all__ = [
    'Base',
    'Notification',
]
# ============================================================================
