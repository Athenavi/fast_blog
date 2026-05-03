"""
块编辑器 API 测试
"""

import pytest
from fastapi.testclient import TestClient

from src.app import app


@pytest.fixture
def client():
    """创建测试客户端"""
    return TestClient(app)


class TestBlockEditorAPI:
    """块编辑器 API 测试"""

    def test_get_block_types(self, client):
        """测试获取所有块类型"""
        response = client.get("/api/v1/block-editor/block-types")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

        # 验证块类型结构
        block = data[0]
        assert "name" in block
        assert "display_name" in block
        assert "category" in block
        assert "icon" in block
        assert "attributes" in block

    def test_get_block_types_by_category(self, client):
        """测试按分类获取块类型"""
        response = client.get("/api/v1/block-editor/block-types?category=text")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

        # 验证所有返回的块都是 text 分类
        for block in data:
            assert block["category"] == "text"

    def test_get_block_categories(self, client):
        """测试获取所有块分类"""
        response = client.get("/api/v1/block-editor/block-categories")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

        # 验证包含预期的分类
        expected_categories = {"text", "media", "layout", "widget", "embed"}
        actual_categories = set(data)
        assert expected_categories.issubset(actual_categories)

    def test_validate_valid_block(self, client):
        """测试验证有效的块"""
        block_data = {
            "block": {
                "type": "paragraph",
                "attributes": {
                    "content": "Hello World",
                    "alignment": "center"
                }
            }
        }

        response = client.post("/api/v1/block-editor/validate", json=block_data)

        assert response.status_code == 200
        data = response.json()
        assert data["is_valid"] is True
        assert data["error_message"] == ""

    def test_validate_invalid_block(self, client):
        """测试验证无效的块"""
        block_data = {
            "block": {
                "type": "paragraph",
                "attributes": {
                    "alignment": "center"
                    # 缺少必需的 content 属性
                }
            }
        }

        response = client.post("/api/v1/block-editor/validate", json=block_data)

        assert response.status_code == 200
        data = response.json()
        assert data["is_valid"] is False
        assert "缺少必需属性" in data["error_message"]

    def test_validate_unknown_block_type(self, client):
        """测试验证未知块类型"""
        block_data = {
            "block": {
                "type": "unknown-block",
                "attributes": {}
            }
        }

        response = client.post("/api/v1/block-editor/validate", json=block_data)

        assert response.status_code == 200
        data = response.json()
        assert data["is_valid"] is False
        assert "未知的块类型" in data["error_message"]

    def test_render_blocks(self, client):
        """测试渲染块为 HTML"""
        blocks_data = {
            "blocks": [
                {
                    "type": "heading",
                    "attributes": {
                        "level": 1,
                        "content": "Test Title"
                    }
                },
                {
                    "type": "paragraph",
                    "attributes": {
                        "content": "Test paragraph"
                    }
                }
            ]
        }

        response = client.post("/api/v1/block-editor/render", json=blocks_data)

        assert response.status_code == 200
        data = response.json()
        assert "html" in data

        html = data["html"]
        assert "<h1" in html
        assert "Test Title" in html
        assert "<p" in html
        assert "Test paragraph" in html

    def test_render_image_block(self, client):
        """测试渲染图片块"""
        blocks_data = {
            "blocks": [
                {
                    "type": "image",
                    "attributes": {
                        "url": "https://example.com/image.jpg",
                        "alt": "Test Image",
                        "caption": "Image Caption",
                        "alignment": "center"
                    }
                }
            ]
        }

        response = client.post("/api/v1/block-editor/render", json=blocks_data)

        assert response.status_code == 200
        data = response.json()

        html = data["html"]
        assert "<figure" in html
        assert 'src="https://example.com/image.jpg"' in html
        assert 'alt="Test Image"' in html
        assert "<figcaption>Image Caption</figcaption>" in html

    def test_render_code_block(self, client):
        """测试渲染代码块"""
        blocks_data = {
            "blocks": [
                {
                    "type": "code",
                    "attributes": {
                        "language": "python",
                        "content": "print('Hello')",
                        "showLineNumbers": True
                    }
                }
            ]
        }

        response = client.post("/api/v1/block-editor/render", json=blocks_data)

        assert response.status_code == 200
        data = response.json()

        html = data["html"]
        assert "<pre" in html
        assert '<code class="language-python">' in html
        assert "line-numbers" in html

    def test_get_example_blocks(self, client):
        """测试获取示例块数据"""
        response = client.get("/api/v1/block-editor/example")

        assert response.status_code == 200
        data = response.json()
        assert "examples" in data

        examples = data["examples"]
        assert isinstance(examples, list)
        assert len(examples) > 0

        # 验证示例块结构
        example = examples[0]
        assert "type" in example
        assert "attributes" in example

    def test_convert_html_to_blocks(self, client):
        """测试 HTML 转块（目前未完全实现）"""
        html = "<p>Hello World</p>"

        response = client.post(
            "/api/v1/block-editor/convert/html-to-blocks",
            params={"html": html}
        )

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "not fully implemented" in data["message"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
