"""
块编辑器服务测试
"""

import pytest

from shared.services.block_editor_service import BlockEditorService, BlockType


class TestBlockEditorService:
    """块编辑器服务测试"""

    def setup_method(self):
        """每个测试前初始化服务"""
        self.service = BlockEditorService()

    def test_service_initialization(self):
        """测试服务初始化"""
        assert self.service is not None
        assert len(self.service.block_types) > 0

    def test_default_blocks_registered(self):
        """测试默认块类型已注册"""
        # 文本块
        assert "paragraph" in self.service.block_types
        assert "heading" in self.service.block_types
        assert "quote" in self.service.block_types

        # 媒体块
        assert "image" in self.service.block_types
        assert "video" in self.service.block_types
        assert "gallery" in self.service.block_types

        # 布局块
        assert "columns" in self.service.block_types
        assert "separator" in self.service.block_types

        # Widget 块
        assert "code" in self.service.block_types
        assert "table" in self.service.block_types
        assert "list" in self.service.block_types

        # Embed 块
        assert "embed" in self.service.block_types

    def test_get_block_type(self):
        """测试获取块类型"""
        block_type = self.service.get_block_type("paragraph")

        assert block_type is not None
        assert block_type.name == "paragraph"
        assert block_type.display_name == "段落"
        assert block_type.category == "text"

    def test_get_nonexistent_block_type(self):
        """测试获取不存在的块类型"""
        block_type = self.service.get_block_type("nonexistent")

        assert block_type is None

    def test_get_all_block_types(self):
        """测试获取所有块类型"""
        all_blocks = self.service.get_all_block_types()

        assert len(all_blocks) >= 12  # 至少有12个默认块
        assert all(isinstance(bt, BlockType) for bt in all_blocks)

    def test_get_block_types_by_category(self):
        """测试按分类获取块类型"""
        text_blocks = self.service.get_block_types_by_category("text")
        media_blocks = self.service.get_block_types_by_category("media")
        layout_blocks = self.service.get_block_types_by_category("layout")

        assert len(text_blocks) >= 3
        assert len(media_blocks) >= 3
        assert len(layout_blocks) >= 2

        # 验证分类正确性
        assert all(bt.category == "text" for bt in text_blocks)
        assert all(bt.category == "media" for bt in media_blocks)
        assert all(bt.category == "layout" for bt in layout_blocks)

    def test_register_custom_block(self):
        """测试注册自定义块类型"""
        custom_block = BlockType(
            name="custom-button",
            display_name="自定义按钮",
            category="widget",
            icon="🔘",
            description="可点击的按钮",
            attributes={
                "text": {"type": "string", "required": True},
                "url": {"type": "string", "required": True},
                "style": {"type": "string", "enum": ["primary", "secondary"], "default": "primary"}
            }
        )

        self.service.register_block(custom_block)

        assert "custom-button" in self.service.block_types
        retrieved = self.service.get_block_type("custom-button")
        assert retrieved.display_name == "自定义按钮"

    def test_validate_valid_block(self):
        """测试验证有效的块数据"""
        block_data = {
            "type": "paragraph",
            "attributes": {
                "content": "Hello World",
                "alignment": "center"
            }
        }

        is_valid, error_msg = self.service.validate_block(block_data)

        assert is_valid is True
        assert error_msg == ""

    def test_validate_missing_type(self):
        """测试验证缺少类型的块"""
        block_data = {
            "attributes": {
                "content": "Hello World"
            }
        }

        is_valid, error_msg = self.service.validate_block(block_data)

        assert is_valid is False
        assert "缺少块类型" in error_msg

    def test_validate_unknown_block_type(self):
        """测试验证未知块类型"""
        block_data = {
            "type": "unknown-block",
            "attributes": {}
        }

        is_valid, error_msg = self.service.validate_block(block_data)

        assert is_valid is False
        assert "未知的块类型" in error_msg

    def test_validate_missing_required_attribute(self):
        """测试验证缺少必需属性"""
        block_data = {
            "type": "paragraph",
            "attributes": {
                "alignment": "center"
                # 缺少必需的 content 属性
            }
        }

        is_valid, error_msg = self.service.validate_block(block_data)

        assert is_valid is False
        assert "缺少必需属性" in error_msg

    def test_validate_invalid_attribute_type(self):
        """测试验证无效的属性类型"""
        block_data = {
            "type": "heading",
            "attributes": {
                "level": "not-an-integer",  # 应该是整数
                "content": "Title"
            }
        }

        is_valid, error_msg = self.service.validate_block(block_data)

        assert is_valid is False
        assert "应该是整数类型" in error_msg

    def test_validate_invalid_enum_value(self):
        """测试验证无效的枚举值"""
        block_data = {
            "type": "paragraph",
            "attributes": {
                "content": "Text",
                "alignment": "invalid-align"  # 不是有效的对齐方式
            }
        }

        is_valid, error_msg = self.service.validate_block(block_data)

        assert is_valid is False
        assert "必须是以下之一" in error_msg

    def test_render_paragraph(self):
        """测试渲染段落块"""
        block_data = {
            "type": "paragraph",
            "attributes": {
                "content": "Hello World",
                "alignment": "center"
            }
        }

        html = self.service.render_block(block_data)

        assert "<p" in html
        assert "Hello World" in html
        assert 'text-align: center' in html

    def test_render_heading(self):
        """测试渲染标题块"""
        block_data = {
            "type": "heading",
            "attributes": {
                "level": 2,
                "content": "My Title"
            }
        }

        html = self.service.render_block(block_data)

        assert "<h2" in html
        assert "My Title" in html
        assert "</h2>" in html

    def test_render_image(self):
        """测试渲染图片块"""
        block_data = {
            "type": "image",
            "attributes": {
                "url": "https://example.com/image.jpg",
                "alt": "Example Image",
                "caption": "A beautiful image",
                "alignment": "center"
            }
        }

        html = self.service.render_block(block_data)

        assert "<figure" in html
        assert 'src="https://example.com/image.jpg"' in html
        assert 'alt="Example Image"' in html
        assert "<figcaption>A beautiful image</figcaption>" in html

    def test_render_code(self):
        """测试渲染代码块"""
        block_data = {
            "type": "code",
            "attributes": {
                "language": "python",
                "content": "print('Hello')",
                "showLineNumbers": True
            }
        }

        html = self.service.render_block(block_data)

        assert "<pre" in html
        assert '<code class="language-python">' in html
        assert "line-numbers" in html
        assert "print('Hello')" in html

    def test_render_separator(self):
        """测试渲染分隔线"""
        block_data = {
            "type": "separator",
            "attributes": {
                "style": "dashed",
                "color": "#ff0000",
                "thickness": "2px"
            }
        }

        html = self.service.render_block(block_data)

        assert "<hr" in html
        assert "wp-block-separator" in html
        assert "border-top:" in html
        assert "dashed" in html

    def test_render_unknown_block(self):
        """测试渲染未知块类型"""
        block_data = {
            "type": "unknown",
            "attributes": {}
        }

        html = self.service.render_block(block_data)

        assert "<!-- 未知块类型: unknown -->" in html

    def test_blocks_to_html(self):
        """测试将块列表转换为 HTML"""
        blocks = [
            {
                "type": "heading",
                "attributes": {"level": 1, "content": "Title"}
            },
            {
                "type": "paragraph",
                "attributes": {"content": "Paragraph 1"}
            },
            {
                "type": "paragraph",
                "attributes": {"content": "Paragraph 2"}
            }
        ]

        html = self.service.blocks_to_html(blocks)

        assert "<h1" in html
        assert "Title" in html
        assert "Paragraph 1" in html
        assert "Paragraph 2" in html

    def test_block_with_children(self):
        """测试带子块的块渲染"""
        block_data = {
            "type": "columns",
            "attributes": {"columns": 2},
            "children": [
                {
                    "type": "column",
                    "attributes": {"width": "50%"},
                    "children": [
                        {
                            "type": "paragraph",
                            "attributes": {"content": "Column 1"}
                        }
                    ]
                },
                {
                    "type": "column",
                    "attributes": {"width": "50%"},
                    "children": [
                        {
                            "type": "paragraph",
                            "attributes": {"content": "Column 2"}
                        }
                    ]
                }
            ]
        }

        html = self.service.render_block(block_data)

        assert "Column 1" in html
        assert "Column 2" in html

    def test_block_attributes_defaults(self):
        """测试块属性默认值"""
        paragraph_type = self.service.get_block_type("paragraph")

        assert paragraph_type.attributes["alignment"]["default"] == "left"
        assert paragraph_type.attributes["fontSize"]["default"] == "normal"

    def test_block_categories(self):
        """测试块分类完整性"""
        categories = set(bt.category for bt in self.service.get_all_block_types())

        assert "text" in categories
        assert "media" in categories
        assert "layout" in categories
        assert "widget" in categories
        assert "embed" in categories


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
