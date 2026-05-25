"""
插件动态热插拔管理器
支持在不重启服务的情况下加载、卸载和更新插件
"""
import importlib
import sys
from pathlib import Path
from typing import Dict, Any


class PluginHotSwapper:
    """插件热插拔核心逻辑"""

    def __init__(self):
        self.loaded_plugins: Dict[str, Any] = {}

    async def load_plugin(self, plugin_slug: str):
        """动态加载插件模块"""
        plugin_path = Path(f"plugins/{plugin_slug}")
        if not (plugin_path / "plugin.py").exists():
            raise FileNotFoundError(f"Plugin {plugin_slug} not found")

        # 将插件路径加入系统路径
        if str(plugin_path) not in sys.path:
            sys.path.insert(0, str(plugin_path))

        try:
            # 动态导入模块
            module = importlib.import_module("plugin")
            if hasattr(module, "plugin_instance"):
                self.loaded_plugins[plugin_slug] = module.plugin_instance
                # 注册钩子
                if hasattr(module.plugin_instance, "register_hooks"):
                    module.plugin_instance.register_hooks()
                return True
        except Exception as e:
            print(f"Failed to load plugin {plugin_slug}: {e}")
            return False

    async def unload_plugin(self, plugin_slug: str):
        """动态卸载插件"""
        if plugin_slug in self.loaded_plugins:
            plugin = self.loaded_plugins.pop(plugin_slug)
            # 注销钩子（需要插件系统支持反向注销）
            if hasattr(plugin, "unregister_hooks"):
                plugin.unregister_hooks()

            # 从 sys.modules 中移除
            if "plugin" in sys.modules:
                del sys.modules["plugin"]
            return True
        return False

    async def reload_plugin(self, plugin_slug: str):
        """热更新插件"""
        await self.unload_plugin(plugin_slug)
        return await self.load_plugin(plugin_slug)


hot_swapper = PluginHotSwapper()
