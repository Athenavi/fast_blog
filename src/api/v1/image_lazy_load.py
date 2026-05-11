"""
图片懒加载管理 API

提供懒加载配置和优化工具
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Body

from shared.services.image_lazy_load import image_lazy_load_service
from src.api.v1.responses import ApiResponse
from src.auth.auth_deps import jwt_required_dependency as jwt_required

router = APIRouter()


@router.get("/config", summary="获取懒加载配置", description="获取当前懒加载配置")
async def get_lazy_load_config(
        current_user=Depends(jwt_required),
):
    """获取懒加载配置"""
    # 检查权限
    is_admin = getattr(current_user, 'is_superuser', False) or getattr(current_user, 'is_staff', False)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Permission denied")

    return ApiResponse(
        success=True,
        data={
            "placeholder_color": image_lazy_load_service.placeholder_color,
            "fade_in_duration": image_lazy_load_service.fade_in_duration,
            "root_margin": image_lazy_load_service.root_margin,
        }
    )


@router.post("/config", summary="更新懒加载配置", description="更新懒加载配置参数")
async def update_lazy_load_config(
        placeholder_color: str = Body(None, description="占位符背景色"),
        fade_in_duration: int = Body(None, ge=100, le=1000, description="淡入动画时长(毫秒)"),
        root_margin: str = Body(None, description="IntersectionObserver的rootMargin"),
        current_user=Depends(jwt_required),
):
    """更新懒加载配置"""
    # 检查权限
    is_admin = getattr(current_user, 'is_superuser', False) or getattr(current_user, 'is_staff', False)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Permission denied")

    if placeholder_color:
        image_lazy_load_service.placeholder_color = placeholder_color

    if fade_in_duration:
        image_lazy_load_service.fade_in_duration = fade_in_duration

    if root_margin:
        image_lazy_load_service.root_margin = root_margin

    return ApiResponse(
        success=True,
        message="Configuration updated",
        data={
            "placeholder_color": image_lazy_load_service.placeholder_color,
            "fade_in_duration": image_lazy_load_service.fade_in_duration,
            "root_margin": image_lazy_load_service.root_margin,
        }
    )


@router.post("/generate-lazy-image", summary="生成懒加载图片HTML", description="生成懒加载图片的HTML代码")
async def generate_lazy_image(
        src: str = Body(..., description="图片URL"),
        alt: str = Body("", description="替代文本"),
        width: Optional[int] = Body(None, description="图片宽度"),
        height: Optional[int] = Body(None, description="图片高度"),
        class_name: str = Body("", description="CSS类名"),
):
    """生成懒加载图片HTML"""
    html = image_lazy_load_service.generate_lazy_image(
        src=src,
        alt=alt,
        width=width,
        height=height,
        class_name=class_name
    )

    return ApiResponse(
        success=True,
        data={
            "html": html,
        }
    )


@router.post("/generate-progressive-image", summary="生成渐进式图片HTML", description="生成渐进式加载图片的HTML代码")
async def generate_progressive_image(
        low_quality_src: str = Body(..., description="低质量图片URL"),
        high_quality_src: str = Body(..., description="高质量图片URL"),
        alt: str = Body("", description="替代文本"),
        width: Optional[int] = Body(None, description="图片宽度"),
        height: Optional[int] = Body(None, description="图片高度"),
):
    """生成渐进式图片HTML"""
    html = image_lazy_load_service.generate_progressive_image(
        low_quality_src=low_quality_src,
        high_quality_src=high_quality_src,
        alt=alt,
        width=width,
        height=height
    )

    return ApiResponse(
        success=True,
        data={
            "html": html,
        }
    )


@router.get("/get-script", summary="获取懒加载脚本", description="获取懒加载JavaScript代码")
async def get_lazy_load_script():
    """获取懒加载JavaScript"""
    script = image_lazy_load_service.generate_lazy_load_script()

    return ApiResponse(
        success=True,
        data={
            "script": script,
            "type": "javascript",
        }
    )


@router.get("/get-css", summary="获取懒加载样式", description="获取懒加载CSS样式代码")
async def get_lazy_load_css():
    """获取懒加载CSS"""
    css = image_lazy_load_service.generate_css_styles()

    return ApiResponse(
        success=True,
        data={
            "css": css,
            "type": "css",
        }
    )


@router.post("/inject-to-html", summary="注入到HTML", description="将懒加载脚本注入到HTML中")
async def inject_to_html(
        html_content: str = Body(..., description="HTML内容"),
):
    """注入懒加载脚本到HTML"""
    optimized_html = image_lazy_load_service.inject_lazy_load(html_content)

    return ApiResponse(
        success=True,
        data={
            "optimized_html": optimized_html,
            "original_length": len(html_content),
            "optimized_length": len(optimized_html),
        }
    )


@router.get("/examples", summary="使用示例", description="获取懒加载使用示例")
async def get_usage_examples():
    """获取使用示例"""
    examples = {
        "basic_lazy_load": {
            "description": "基本懒加载用法",
            "code": '''
from shared.services.image_lazy_load import image_lazy_load_service

# 生成懒加载图片HTML
html = image_lazy_load_service.generate_lazy_image(
    src="/images/photo.jpg",
    alt="Beautiful photo",
    width=800,
    height=600
)

# 在模板中使用
return {"image_html": html}
            '''.strip()
        },
        "progressive_loading": {
            "description": "渐进式加载（先显示模糊图，再加载清晰图）",
            "code": '''
# 生成渐进式图片HTML
html = image_lazy_load_service.generate_progressive_image(
    low_quality_src="/images/photo-thumb.jpg",  # 小尺寸模糊图
    high_quality_src="/images/photo-full.jpg",  # 原始高清图
    alt="Beautiful photo",
    width=800,
    height=600
)
            '''.strip()
        },
        "inject_to_page": {
            "description": "将懒加载脚本注入到页面",
            "code": '''
# 在渲染HTML后注入懒加载脚本
html_content = render_template("article.html", ...)
optimized_html = image_lazy_load_service.inject_lazy_load(html_content)

return Response(content=optimized_html, media_type="text/html")
            '''.strip()
        },
        "frontend_integration": {
            "description": "前端集成建议",
            "recommendations": [
                "在</body>前引入懒加载脚本",
                "为图片设置固定宽高避免布局偏移",
                "使用data-src而非src存储真实图片地址",
                "添加loading='lazy'作为额外保障",
                "为关键 Above-the-fold 图片禁用懒加载",
            ]
        },
        "performance_tips": {
            "description": "性能优化建议",
            "tips": [
                "rootMargin设置为200px提前加载",
                "使用WebP格式减小图片体积",
                "为不同屏幕尺寸提供srcset",
                "实现图片预加载策略",
                "监控懒加载成功率",
            ]
        }
    }

    return ApiResponse(
        success=True,
        data=examples
    )


@router.get("/best-practices", summary="最佳实践", description="获取图片懒加载最佳实践")
async def get_best_practices():
    """获取最佳实践"""
    practices = {
        "when_to_use": {
            "title": "何时使用懒加载",
            "items": [
                "长页面中的图片列表",
                "文章中的非首屏图片",
                "评论区的用户头像",
                "相关产品推荐",
                "画廊和相册",
            ]
        },
        "when_not_to_use": {
            "title": "何时不使用懒加载",
            "items": [
                "首屏可见的关键图片（Logo、Hero图）",
                "单页应用的关键视觉元素",
                "已经非常小的图标",
                "需要立即显示的验证码图片",
            ]
        },
        "accessibility": {
            "title": "无障碍考虑",
            "items": [
                "始终提供有意义的alt文本",
                "确保图片加载失败时有降级方案",
                "不要仅依赖JavaScript显示重要内容",
                "测试键盘导航和屏幕阅读器",
            ]
        },
        "seo_considerations": {
            "title": "SEO注意事项",
            "items": [
                "Google可以执行JavaScript并索引懒加载图片",
                "确保图片有正确的alt属性",
                "使用结构化数据标记重要图片",
                "为关键图片考虑不使用懒加载",
            ]
        }
    }

    return ApiResponse(
        success=True,
        data=practices
    )
