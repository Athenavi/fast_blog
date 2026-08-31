"""
插件系统初始化
在应用启动时自动加载和激活插件
使用 EventBus 事件系统
"""

import logging
from pathlib import Path

from shared.services.plugins.plugin_manager.core import plugin_manager

logger = logging.getLogger(__name__)


def initialize_plugins():
    """
    初始化插件系统

    在应用启动时调用此函数来加载所有插件。
    首次运行时自动激活所有已加载的插件；后续启动时恢复上次的激活状态。
    """
    try:
        logger.info("[PluginSystem] Initializing plugin system...")

        # 确保插件目录存在
        plugins_dir = Path("plugins")
        plugins_dir.mkdir(exist_ok=True)

        # 确保storage目录存在
        storage_dir = Path("storage")
        storage_dir.mkdir(exist_ok=True)

        # 加载所有插件
        plugin_manager.load_all_plugins()

        # 尝试恢复之前的插件状态（从数据库或文件）
        state_restored = plugin_manager._load_plugin_state()

        # 如果没有恢复到任何状态（首次运行），自动激活所有已加载的插件
        active_count = len(plugin_manager.get_active_plugins())
        total_count = len(plugin_manager.plugins)

        if not state_restored and total_count > 0:
            logger.info("[PluginSystem] No saved state found, activating all %d plugins...", total_count)
            for slug in list(plugin_manager.plugins.keys()):
                try:
                    plugin_manager.activate_plugin(slug)
                except Exception as e:
                    logger.error("[PluginSystem] Failed to auto-activate plugin '%s': %s", slug, e)

            # 保存初始状态，以便后续启动时恢复
            plugin_manager._save_plugin_state()
            active_count = len(plugin_manager.get_active_plugins())

        logger.info("[PluginSystem] Plugin system initialized: %d/%d plugins active", active_count, total_count)
        return True

    except Exception as e:
        logger.exception("[PluginSystem] Failed to initialize: %s", str(e))
        return False
