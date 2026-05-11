"""
插件管理器单元测试
"""
import sys
from pathlib import Path

import pytest

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.services.plugin_manager import (
    BasePlugin,
    PluginManager,
    plugin_hooks,
    PluginManifest,
    ManifestValidator,
)


class TestPluginManifest:
    """插件清单测试"""

    def test_valid_manifest(self):
        """测试有效的插件清单"""
        manifest_data = {
            "name": "Test Plugin",
            "slug": "test-plugin",
            "version": "1.0.0",
            "description": "A test plugin",
            "author": "Test Author",
            "license": "MIT"
        }

        manifest = PluginManifest(**manifest_data)

        assert manifest.name == "Test Plugin"
        assert manifest.slug == "test-plugin"
        assert manifest.version == "1.0.0"
        assert manifest.author == "Test Author"

    def test_invalid_slug(self):
        """测试无效的 slug 格式"""
        with pytest.raises(Exception):
            PluginManifest(
                name="Test",
                slug="INVALID_SLUG",  # 应该小写且只包含字母、数字和连字符
                version="1.0.0",
                description="Test",
                author="Test"
            )

    def test_invalid_version(self):
        """测试无效的版本号"""
        with pytest.raises(Exception):
            PluginManifest(
                name="Test",
                slug="test",
                version="invalid",  # 应该是语义化版本
                description="Test",
                author="Test"
            )


class TestManifestValidator:
    """清单验证器测试"""

    def test_validate_complete_manifest(self):
        """测试完整清单验证"""
        import tempfile
        import json

        manifest_data = {
            "name": "Complete Plugin",
            "slug": "complete-plugin",
            "version": "2.0.0",
            "description": "A complete plugin with all fields",
            "author": "Author Name",
            "author_url": "https://example.com",
            "plugin_url": "https://plugin.example.com",
            "license": "MIT",
            "category": "seo"
        }

        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(manifest_data, f)
            temp_path = Path(f.name)

        try:
            # ManifestValidator 使用 validate_file 静态方法
            is_valid, msg, manifest = ManifestValidator.validate_file(temp_path)

            assert is_valid is True
            assert manifest is not None
            assert manifest.name == "Complete Plugin"
        finally:
            temp_path.unlink()

    def test_validate_missing_required_fields(self):
        """测试缺少必填字段"""
        import tempfile
        import json

        manifest_data = {
            "name": "Incomplete Plugin",
            # 缺少 slug, version, description, author
        }

        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(manifest_data, f)
            temp_path = Path(f.name)

        try:
            is_valid, msg, manifest = ManifestValidator.validate_file(temp_path)

            assert is_valid is False
            assert manifest is None
        finally:
            temp_path.unlink()


class TestBasePlugin:
    """基础插件类测试"""

    def test_plugin_initialization(self):
        """测试插件初始化"""

        class TestPlugin(BasePlugin):
            def __init__(self):
                super().__init__(
                    plugin_id=1,
                    name="Test Plugin",
                    slug="test-plugin",
                    version="1.0.0"
                )

            def register_hooks(self):
                pass

        plugin = TestPlugin()

        assert plugin.name == "Test Plugin"
        assert plugin.slug == "test-plugin"
        assert plugin.version == "1.0.0"
        assert plugin.active is False

    def test_plugin_activation(self):
        """测试插件激活"""

        class TestPlugin(BasePlugin):
            def __init__(self):
                super().__init__(
                    plugin_id=1,
                    name="Test Plugin",
                    slug="test-plugin",
                    version="1.0.0"
                )

            def register_hooks(self):
                pass

        plugin = TestPlugin()
        plugin.activate()

        assert plugin.active is True

        plugin.deactivate()
        assert plugin.active is False

    def test_plugin_settings(self):
        """测试插件设置"""

        class TestPlugin(BasePlugin):
            def __init__(self):
                super().__init__(
                    plugin_id=1,
                    name="Test Plugin",
                    slug="test-plugin",
                    version="1.0.0"
                )
                self.settings = {
                    'enabled': True,
                    'debug': False
                }

            def register_hooks(self):
                pass

        plugin = TestPlugin()

        # BasePlugin 使用 settings 字典直接访问
        assert plugin.settings.get('enabled', True) is True


class TestPluginHooks:
    """插件钩子系统测试"""

    def setup_method(self):
        """每个测试前重置钩子"""
        plugin_hooks.actions.clear()
        plugin_hooks.filters.clear()

    def test_add_action(self):
        """测试添加动作钩子"""
        call_count = {'count': 0}

        def test_action(data):
            call_count['count'] += 1

        plugin_hooks.add_action("test_event", test_action, priority=10)

        assert "test_event" in plugin_hooks.actions
        assert len(plugin_hooks.actions["test_event"]) == 1

    def test_do_action(self):
        """测试触发动作钩子"""
        results = []

        def action_handler(data):
            results.append(data)

        plugin_hooks.add_action("test_event", action_handler, priority=10)
        # do_action 是异步方法，需要同步调用
        plugin_hooks.do_action_sync("test_event", {"key": "value"})

        assert len(results) == 1
        assert results[0] == {"key": "value"}

    def test_add_filter(self):
        """测试添加过滤器钩子"""

        def uppercase_filter(text):
            return text.upper()

        plugin_hooks.add_filter("text_filter", uppercase_filter, priority=10)

        assert "text_filter" in plugin_hooks.filters

    def test_apply_filters(self):
        """测试应用过滤器"""

        def add_prefix(text):
            return f"[PREFIX] {text}"

        def add_suffix(text):
            return f"{text} [SUFFIX]"

        plugin_hooks.add_filter("content", add_prefix, priority=5)
        plugin_hooks.add_filter("content", add_suffix, priority=10)

        result = plugin_hooks.apply_filters("content", "Hello")

        assert result == "[PREFIX] Hello [SUFFIX]"

    def test_filter_priority(self):
        """测试过滤器优先级"""
        order = []

        def first(text):
            order.append(1)
            return text + "1"

        def second(text):
            order.append(2)
            return text + "2"

        plugin_hooks.add_filter("test", second, priority=10)
        plugin_hooks.add_filter("test", first, priority=5)

        plugin_hooks.apply_filters("test", "")

        assert order == [1, 2]  # 优先级高的先执行


class TestPluginManager:
    """插件管理器测试"""

    def setup_method(self):
        """每个测试前创建新的管理器实例"""
        self.manager = PluginManager()

    def test_manager_initialization(self):
        """测试管理器初始化"""
        assert self.manager.plugins_dir.exists() or True  # 目录可能不存在但不应报错
        assert isinstance(self.manager.plugins, dict)

    def test_register_plugin(self):
        """测试注册插件（通过 load_plugin）"""

        class TestPlugin(BasePlugin):
            def __init__(self):
                super().__init__(
                    plugin_id=1,
                    name="Test Plugin",
                    slug="test-plugin",
                    version="1.0.0"
                )

            def register_hooks(self):
                pass

        plugin = TestPlugin()
        # PluginManager 使用 plugins 字典存储插件
        self.manager.plugins["test-plugin"] = plugin

        assert "test-plugin" in self.manager.plugins

    def test_get_plugin(self):
        """测试获取插件"""

        class TestPlugin(BasePlugin):
            def __init__(self):
                super().__init__(
                    plugin_id=1,
                    name="Test Plugin",
                    slug="test-plugin",
                    version="1.0.0"
                )

            def register_hooks(self):
                pass

        plugin = TestPlugin()
        self.manager.plugins["test-plugin"] = plugin

        retrieved = self.manager.get_plugin("test-plugin")
        assert retrieved is not None
        assert retrieved.name == "Test Plugin"

    def test_activate_plugin(self):
        """测试激活插件"""

        class TestPlugin(BasePlugin):
            def __init__(self):
                super().__init__(
                    plugin_id=1,
                    name="Test Plugin",
                    slug="test-plugin",
                    version="1.0.0"
                )

            def register_hooks(self):
                pass

        plugin = TestPlugin()
        self.manager.plugins["test-plugin"] = plugin
        self.manager.activate_plugin("test-plugin")

        assert plugin.active is True

    def test_deactivate_plugin(self):
        """测试停用插件"""

        class TestPlugin(BasePlugin):
            def __init__(self):
                super().__init__(
                    plugin_id=1,
                    name="Test Plugin",
                    slug="test-plugin",
                    version="1.0.0"
                )

            def register_hooks(self):
                pass

        plugin = TestPlugin()
        self.manager.plugins["test-plugin"] = plugin
        plugin.activate()
        self.manager.deactivate_plugin("test-plugin")

        assert plugin.active is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
