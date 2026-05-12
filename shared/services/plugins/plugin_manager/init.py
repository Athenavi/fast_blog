"""
插件系统初始化
在应用启动时自动加载和激活插件
"""

from pathlib import Path


def initialize_plugins():
    """
    初始化插件系统
    
    在应用启动时调用此函数来加载所有插件
    """
    try:
        from shared.services.plugin_manager.core import plugin_manager

        print("[PluginSystem] Initializing plugin system...")

        # 确保插件目录存在
        plugins_dir = Path("plugins")
        plugins_dir.mkdir(exist_ok=True)

        # 确保storage目录存在
        storage_dir = Path("storage")
        storage_dir.mkdir(exist_ok=True)

        # 加载所有插件
        plugin_manager.load_all_plugins()

        # 加载之前的状态(自动激活之前激活的插件)
        plugin_manager._load_plugin_state()

        active_count = len(plugin_manager.get_active_plugins())
        total_count = len(plugin_manager.plugins)

        print(f"[PluginSystem] Plugin system initialized: {active_count}/{total_count} plugins active")

        return True

    except Exception as e:
        import traceback
        print(f"[PluginSystem] Failed to initialize: {str(e)}")
        print(traceback.format_exc())
        return False


async def trigger_plugin_event(event_name: str, *args, **kwargs):
    """
    触发插件事件
    
    Args:
        event_name: 事件名称
        *args: 位置参数
        **kwargs: 关键字参数
    """
    from shared.services.plugin_manager.core import plugin_hooks

    await plugin_hooks.do_action(event_name, *args, **kwargs)


def apply_plugin_filter(filter_name: str, value, *args, **kwargs):
    """
    应用插件过滤器
    
    Args:
        filter_name: 过滤器名称
        value: 要过滤的值
        *args: 额外位置参数
        **kwargs: 额外关键字参数
        
    Returns:
        过滤后的值
    """
    from shared.services.plugin_manager.core import plugin_hooks

    return plugin_hooks.apply_filters(filter_name, value, *args, **kwargs)
