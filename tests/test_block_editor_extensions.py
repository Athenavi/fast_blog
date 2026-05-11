"""
块编辑器扩展服务测试
"""

import pytest

from shared.services.block_editor_extensions import create_extensions
from shared.services.block_editor_service import BlockEditorService


class TestBlockEditorExtensions:
    """块编辑器扩展服务测试"""

    def setup_method(self):
        """每个测试前初始化服务"""
        self.base_service = BlockEditorService()
        self.extensions = create_extensions(self.base_service)

    def test_extensions_initialization(self):
        """测试扩展服务初始化"""
        assert self.extensions is not None
        assert self.extensions.base_service == self.base_service

    def test_extended_blocks_registered(self):
        """测试扩展块类型已注册"""
        # YouTube
        assert "youtube" in self.base_service.block_types
        youtube = self.base_service.get_block_type("youtube")
        assert youtube.category == "embed"

        # Bilibili
        assert "bilibili" in self.base_service.block_types

        # Twitter
        assert "twitter" in self.base_service.block_types

        # Button
        assert "button" in self.base_service.block_types
        button = self.base_service.get_block_type("button")
        assert button.category == "widget"

        # Callout
        assert "callout" in self.base_service.block_types

        # Accordion
        assert "accordion" in self.base_service.block_types
        assert "accordion-item" in self.base_service.block_types

        # Audio
        assert "audio" in self.base_service.block_types

        # Tabs
        assert "tabs" in self.base_service.block_types
        assert "tab-pane" in self.base_service.block_types

    def test_convert_heading_to_paragraph(self):
        """测试转换标题为段落"""
        heading_block = {
            "type": "heading",
            "attributes": {
                "level": 2,
                "content": "Test Title",
                "alignment": "center"
            }
        }

        result = self.extensions.convert_block_type(heading_block, "paragraph")

        assert result is not None
        assert result["type"] == "paragraph"
        assert result["attributes"]["content"] == "Test Title"
        assert result["attributes"]["alignment"] == "center"

    def test_convert_paragraph_to_heading(self):
        """测试转换段落为标题"""
        paragraph_block = {
            "type": "paragraph",
            "attributes": {
                "content": "Test Content",
                "alignment": "left"
            }
        }

        result = self.extensions.convert_block_type(paragraph_block, "heading")

        assert result is not None
        assert result["type"] == "heading"
        assert result["attributes"]["content"] == "Test Content"
        assert result["attributes"]["level"] == 2  # 默认 H2

    def test_convert_invalid_type(self):
        """测试转换为无效类型"""
        block = {
            "type": "paragraph",
            "attributes": {"content": "Test"}
        }

        result = self.extensions.convert_block_type(block, "nonexistent")

        assert result is None

    def test_duplicate_block(self):
        """测试复制块"""
        original = {
            "type": "paragraph",
            "attributes": {"content": "Original"},
            "children": [{"type": "text"}]
        }

        duplicate = self.extensions.duplicate_block(original)

        # 验证内容相同
        assert duplicate["type"] == original["type"]
        assert duplicate["attributes"]["content"] == original["attributes"]["content"]

        # 验证是深拷贝（修改副本不影响原件）
        duplicate["attributes"]["content"] = "Modified"
        assert original["attributes"]["content"] == "Original"

    def test_merge_paragraphs(self):
        """测试合并段落"""
        block1 = {
            "type": "paragraph",
            "attributes": {"content": "First paragraph"}
        }
        block2 = {
            "type": "paragraph",
            "attributes": {"content": "Second paragraph"}
        }

        merged = self.extensions.merge_blocks(block1, block2)

        assert merged is not None
        assert merged["type"] == "paragraph"
        assert merged["attributes"]["content"] == "First paragraph Second paragraph"

    def test_merge_different_types(self):
        """测试合并不同类型（应该失败）"""
        heading = {
            "type": "heading",
            "attributes": {"content": "Title"}
        }
        paragraph = {
            "type": "paragraph",
            "attributes": {"content": "Content"}
        }

        merged = self.extensions.merge_blocks(heading, paragraph)

        assert merged is None

    def test_split_paragraph(self):
        """测试分割段落"""
        block = {
            "type": "paragraph",
            "attributes": {"content": "Hello World"}
        }

        blocks = self.extensions.split_block(block, 5)

        assert len(blocks) == 2
        assert blocks[0]["attributes"]["content"] == "Hello"
        assert blocks[1]["attributes"]["content"] == " World"

    def test_split_at_invalid_position(self):
        """测试在无效位置分割"""
        block = {
            "type": "paragraph",
            "attributes": {"content": "Test"}
        }

        # 位置超出范围
        blocks = self.extensions.split_block(block, 100)

        assert len(blocks) == 1
        assert blocks[0] == block

    def test_export_import_json(self):
        """测试导出导入 JSON"""
        original_blocks = [
            {
                "type": "heading",
                "attributes": {"level": 1, "content": "Title"}
            },
            {
                "type": "paragraph",
                "attributes": {"content": "Content"}
            }
        ]

        # 导出
        json_str = self.extensions.export_blocks_json(original_blocks)

        # 验证是有效的 JSON
        assert isinstance(json_str, str)
        assert '"type": "heading"' in json_str

        # 导入
        imported_blocks = self.extensions.import_blocks_json(json_str)

        # 验证数据一致
        assert len(imported_blocks) == len(original_blocks)
        assert imported_blocks[0]["type"] == "heading"
        assert imported_blocks[1]["type"] == "paragraph"

    def test_import_invalid_json(self):
        """测试导入无效 JSON"""
        result = self.extensions.import_blocks_json("invalid json")

        assert result == []

    def test_get_block_statistics(self):
        """测试获取块统计信息"""
        blocks = [
            {"type": "heading", "attributes": {}},
            {"type": "paragraph", "attributes": {}},
            {"type": "paragraph", "attributes": {}},
            {"type": "image", "attributes": {}},
            {"type": "youtube", "attributes": {}}
        ]

        stats = self.extensions.get_block_statistics(blocks)

        assert stats["total_blocks"] == 5
        assert stats["by_type"]["heading"] == 1
        assert stats["by_type"]["paragraph"] == 2
        assert stats["by_type"]["image"] == 1
        assert stats["by_type"]["youtube"] == 1
        assert stats["has_media"] is True
        assert stats["has_embeds"] is True
        assert "text" in stats["by_category"]
        assert "media" in stats["by_category"]
        assert "embed" in stats["by_category"]

    def test_empty_blocks_statistics(self):
        """测试空块列表的统计"""
        stats = self.extensions.get_block_statistics([])

        assert stats["total_blocks"] == 0
        assert stats["by_type"] == {}
        assert stats["by_category"] == {}
        assert stats["has_media"] is False
        assert stats["has_embeds"] is False

    def test_youtube_block_validation(self):
        """测试 YouTube 块验证"""
        valid_block = {
            "type": "youtube",
            "attributes": {
                "videoId": "dQw4w9WgXcQ"
            }
        }

        is_valid, error = self.base_service.validate_block(valid_block)
        assert is_valid is True

        # 缺少必需的 videoId
        invalid_block = {
            "type": "youtube",
            "attributes": {}
        }

        is_valid, error = self.base_service.validate_block(invalid_block)
        assert is_valid is False
        assert "videoId" in error

    def test_button_block_validation(self):
        """测试按钮块验证"""
        valid_block = {
            "type": "button",
            "attributes": {
                "text": "Click Me",
                "url": "https://example.com",
                "style": "primary",
                "size": "medium"
            }
        }

        is_valid, error = self.base_service.validate_block(valid_block)
        assert is_valid is True

        # 无效的 style 值
        invalid_block = {
            "type": "button",
            "attributes": {
                "text": "Click Me",
                "url": "https://example.com",
                "style": "invalid"
            }
        }

        is_valid, error = self.base_service.validate_block(invalid_block)
        assert is_valid is False

    def test_callout_block_validation(self):
        """测试提示框块验证"""
        valid_block = {
            "type": "callout",
            "attributes": {
                "type": "warning",
                "title": "Warning",
                "content": "This is a warning message"
            }
        }

        is_valid, error = self.base_service.validate_block(valid_block)
        assert is_valid is True

    def test_accordion_block_structure(self):
        """测试折叠面板块结构"""
        accordion = self.base_service.get_block_type("accordion")

        assert accordion.allowed_children == ["accordion-item"]
        assert "items" in accordion.attributes

        accordion_item = self.base_service.get_block_type("accordion-item")
        assert accordion_item.is_inline is True

    def test_tabs_block_structure(self):
        """测试标签页块结构"""
        tabs = self.base_service.get_block_type("tabs")

        assert tabs.allowed_children == ["tab-pane"]
        assert "tabs" in tabs.attributes
        assert "defaultTab" in tabs.attributes

    def test_audio_block_rendering(self):
        """测试音频块渲染（使用默认渲染器）"""
        block = {
            "type": "audio",
            "attributes": {
                "url": "https://example.com/audio.mp3",
                "title": "Sample Audio",
                "artist": "Artist Name"
            }
        }

        html = self.base_service.render_block(block)

        # 音频块没有专门的渲染器，使用默认渲染
        assert "<!-- Block: audio -->" in html

    def test_total_block_count(self):
        """测试总块类型数量"""
        all_blocks = self.base_service.get_all_block_types()

        # 基础块 (12) + 扩展块 (至少 10)
        assert len(all_blocks) >= 22

        # 验证所有分类都存在
        categories = set(b.category for b in all_blocks)
        assert "text" in categories
        assert "media" in categories
        assert "layout" in categories
        assert "widget" in categories
        assert "embed" in categories


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
