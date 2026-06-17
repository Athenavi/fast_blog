"""
组件和模板 API - 为 PageBuilder 提供组件库数据
"""
from functools import wraps
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v2._helpers import ok, fail
from src.auth import jwt_required_dependency as jwt_required
from src.utils.database.main import get_async_session as get_async_db

def _catch(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            return fail(str(e))
    return wrapper

router = APIRouter(tags=["components"])

# 11 个内置模式 + 单个组件
COMPONENT_TEMPLATES = [
    # 完整页面模板（带 id）
    {"id": 1, "name": "hero-basic", "title": "基础 Hero 区域", "description": "简洁的首页英雄区域", "category": "hero", "blocks": [{"type": "hero", "props": {"title": "欢迎来到我们的网站", "subtitle": "发现精彩内容", "bgColor": "#1e40af"}}]},
    {"id": 2, "name": "hero-with-image", "title": "带图片的 Hero", "description": "右侧配图的英雄区域", "category": "hero", "blocks": [{"type": "hero", "props": {"title": "标题文字", "subtitle": "副标题", "imageUrl": "", "bgColor": "#1e3a5f"}}]},
    {"id": 3, "name": "features-grid", "title": "特性网格", "description": "展示核心功能的三列网格", "category": "features", "blocks": [{"type": "grid", "props": {"columns": 3, "items": [{"title": "特性 1", "desc": "描述"}, {"title": "特性 2", "desc": "描述"}, {"title": "特性 3", "desc": "描述"}]}}]},
    {"id": 4, "name": "team-members", "title": "团队成员", "description": "团队成员展示区域", "category": "team", "blocks": [{"type": "team", "props": {"members": [{"name": "成员 1", "role": "职位"}, {"name": "成员 2", "role": "职位"}]}}]},
    {"id": 5, "name": "pricing-table", "title": "价格表", "description": "三栏定价方案", "category": "pricing", "blocks": [{"type": "pricing", "props": {"plans": [{"name": "基础版", "price": "¥99"}, {"name": "专业版", "price": "¥199"}, {"name": "企业版", "price": "¥499"}]}}]},
    {"id": 6, "name": "contact-form", "title": "联系表单", "description": "访问者联系表单", "category": "contact", "blocks": [{"type": "form", "props": {"fields": [{"type": "text", "label": "姓名"}, {"type": "email", "label": "邮箱"}]}}]},
    {"id": 7, "name": "cta-banner", "title": "CTA 横幅", "description": "号召性用语横幅", "category": "cta", "blocks": [{"type": "cta", "props": {"text": "立即行动", "buttonText": "了解更多", "bgColor": "#2563eb"}}]},
    {"id": 8, "name": "testimonials", "title": "客户评价", "description": "客户评价轮播", "category": "testimonials", "blocks": [{"type": "testimonial", "props": {"items": [{"quote": "评价内容", "author": "客户名"}]}}]},
    {"id": 9, "name": "faq-section", "title": "FAQ 常见问题", "description": "常见问题手风琴", "category": "faq", "blocks": [{"type": "faq", "props": {"items": [{"q": "问题", "a": "答案"}]}}]},
    {"id": 10, "name": "newsletter-signup", "title": "邮件订阅", "description": "邮件订阅区域", "category": "newsletter", "blocks": [{"type": "newsletter", "props": {"placeholder": "输入邮箱", "buttonText": "订阅"}}]},
    {"id": 11, "name": "stats-counter", "title": "统计数据", "description": "数据统计展示", "category": "stats", "blocks": [{"type": "stats", "props": {"items": [{"value": "100+", "label": "客户"}]}}]},
    # 单个组件块（无 id，用于添加到当前页面）
    {"title": "文本块", "description": "纯文本段落", "category": "basic", "blocks": [{"type": "text", "props": {"content": "在此输入文本内容..."}}]},
    {"title": "图片块", "description": "单张图片", "category": "media", "blocks": [{"type": "image", "props": {"src": "", "alt": "图片描述"}}]},
    {"title": "视频块", "description": "嵌入视频", "category": "media", "blocks": [{"type": "video", "props": {"url": "", "title": "视频标题"}}]},
    {"title": "按钮块", "description": "单按钮", "category": "basic", "blocks": [{"type": "button", "props": {"text": "点击", "url": "#", "style": "primary"}}]},
    {"title": "分隔线", "description": "水平分割线", "category": "basic", "blocks": [{"type": "divider", "props": {}}]},
    {"title": "引用块", "description": "引用样式", "category": "basic", "blocks": [{"type": "quote", "props": {"text": "引用内容", "author": "作者"}}]},
    {"title": "两列布局", "description": "左右两栏", "category": "layout", "blocks": [{"type": "columns", "props": {"count": 2, "content": ["左列", "右列"]}}]},
    {"title": "三列布局", "description": "等宽三栏", "category": "layout", "blocks": [{"type": "columns", "props": {"count": 3, "content": ["列1", "列2", "列3"]}}]},
    {"title": "图标列表", "description": "带图标的列表", "category": "features", "blocks": [{"type": "icon-list", "props": {"items": [{"icon": "check", "text": "特点一"}]}}]},
    {"title": "进度条", "description": "百分比进度", "category": "basic", "blocks": [{"type": "progress", "props": {"value": 75, "label": "进度"}}]},
    {"title": "代码块", "description": "代码片段", "category": "basic", "blocks": [{"type": "code", "props": {"language": "javascript", "code": "console.log('hello')"}}]},
]

@router.get("/templates")
@_catch
async def list_component_templates(current_user=Depends(jwt_required)):
    """获取组件库模板列表（包含页面模板和单个组件）"""
    return ok(data=COMPONENT_TEMPLATES)
