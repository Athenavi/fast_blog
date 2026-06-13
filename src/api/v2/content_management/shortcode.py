"""
Shortcode短代码API
提供短代码解析和管理功能
"""

from functools import wraps

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from shared.services.content_management.shortcode_service import shortcode_service
from src.api.v2._helpers import ok, fail

router = APIRouter(tags=["shortcode"])


class ShortcodeParseRequest(BaseModel):
    """短代码解析请求"""
    content: str


def _catch(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except HTTPException:
            raise
        except Exception as e:
            return fail(str(e))
    return wrapper


@router.post("/parse")
@_catch
async def parse_shortcodes(request_data: ShortcodeParseRequest):
    """
    解析内容中的短代码

    Args:
        request_data: 包含内容的请求体

    Returns:
        解析后的内容
    """
    parsed_content = shortcode_service.parse(request_data.content)

    return ok(data={
        'original': request_data.content,
        'parsed': parsed_content
    })


@router.get("/list")
@_catch
async def list_shortcodes():
    """
    获取所有已注册的短代码列表

    Returns:
        短代码名称列表
    """
    shortcodes = list(shortcode_service.shortcodes.keys())

    return ok(data={
        'shortcodes': shortcodes,
        'count': len(shortcodes)
    })


@router.get("/help/{name}")
@_catch
async def get_shortcode_help(name: str):
    """
    获取短代码使用说明

    Args:
        name: 短代码名称

    Returns:
        使用说明
    """
    help_docs = {
        'code': {
            'description': '嵌入格式化代码块',
            'usage': '[code language="python"]print("hello")[/code]',
            'attributes': {
                'language': '编程语言(默认text)'
            },
            'example': '[code language="python"]def hello():\\n    print("Hello, World!")[/code]'
        },
        'gist': {
            'description': '嵌入 GitHub Gist',
            'usage': '[gist id="abc123"]',
            'attributes': {
                'id': 'Gist ID'
            },
            'example': '[gist id="username/abc123"]'
        },
        'youtube': {
            'description': '嵌入 YouTube 视频',
            'usage': '[youtube id="dQw4w9WgXcQ"]',
            'attributes': {
                'id': 'YouTube 视频 ID'
            },
            'example': '[youtube id="dQw4w9WgXcQ"]'
        },
        'bilibili': {
            'description': '嵌入 Bilibili 视频',
            'usage': '[bilibili id="BV1xx411c7mD"]',
            'attributes': {
                'id': 'Bilibili 视频 BV 号'
            },
            'example': '[bilibili id="BV1xx411c7mD"]'
        },
        'note': {
            'description': '显示提示框',
            'usage': '[note type="info|warning|tip"]内容[/note]',
            'attributes': {
                'type': '类型: info(默认), warning, tip'
            },
            'example': '[note type="tip"]这是一个提示消息[/note]'
        },
        'tabs': {
            'description': '创建标签切换',
            'usage': '[tabs][tab name="A"]内容A[/tab][tab name="B"]内容B[/tabs]',
            'attributes': {
                'name': '标签名称(在[tab]上使用)'
            },
            'example': '[tabs]\\n[tab name="Python"]Python 内容[/tab]\\n[tab name="JavaScript"]JS 内容[/tab]\\n[/tabs]'
        }
    }

    if name in help_docs:
        return ok(data=help_docs[name])
    else:
        return fail(f"未找到短代码 '{name}' 的说明")
