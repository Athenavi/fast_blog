"""
懒加载优化 API
提供图片懒加载、内容优化等功能
"""

from fastapi import APIRouter, Depends, Body

from shared.services.performance.lazy_load_service import lazy_load_optimizer
from src.api.v1.core.responses import ApiResponse
from src.auth.auth_deps import admin_required

router = APIRouter(prefix="/lazy-load", tags=["lazy-load"])


@router.post("/optimize-content", summary="优化内容中的图片")
async def optimize_content(
        content: str = Body(..., description="HTML内容"),
        current_user=Depends(admin_required)
):
    """
    优化文章内容中的图片，转换为懒加载格式
    
    Args:
        content: HTML内容
        
    Returns:
        优化后的HTML内容
    """
    try:
        optimized = lazy_load_optimizer.optimize_content_images(content)

        return ApiResponse(
            success=True,
            data={
                'optimized_content': optimized,
                'original_length': len(content),
                'optimized_length': len(optimized),
            }
        )
    except Exception as e:
        return ApiResponse(success=False, error=f"优化失败: {str(e)}")


@router.get("/image-tag", summary="生成懒加载图片标签")
async def generate_lazy_image(
        src: str,
        alt: str = "",
        width: int = None,
        height: int = None,
        class_name: str = "",
):
    """
    生成懒加载图片HTML标签
    
    Args:
        src: 图片URL
        alt: 替代文本
        width: 宽度
        height: 高度
        class_name: CSS类名
        
    Returns:
        图片HTML标签
    """
    try:
        html = lazy_load_optimizer.generate_lazy_image(
            src=src,
            alt=alt,
            width=width,
            height=height,
            class_name=class_name
        )

        return ApiResponse(
            success=True,
            data={'html': html}
        )
    except Exception as e:
        return ApiResponse(success=False, error=f"生成失败: {str(e)}")


@router.get("/responsive-image", summary="生成响应式图片")
async def generate_responsive_image(
        base_url: str,
        alt: str = "",
):
    """
    生成响应式懒加载图片
    
    Args:
        base_url: 图片基础URL
        alt: 替代文本
        
    Returns:
        响应式图片HTML
    """
    try:
        html = lazy_load_optimizer.generate_responsive_image(
            base_url=base_url,
            alt=alt
        )

        return ApiResponse(
            success=True,
            data={'html': html}
        )
    except Exception as e:
        return ApiResponse(success=False, error=f"生成失败: {str(e)}")


@router.get("/placeholder-svg", summary="生成SVG占位符")
async def generate_placeholder(
        width: int = 800,
        height: int = 600,
):
    """
    生成SVG占位符
    
    Args:
        width: 宽度
        height: 高度
        
    Returns:
        SVG占位符data URI
    """
    try:
        svg_uri = lazy_load_optimizer.generate_placeholder_svg(width, height)

        return ApiResponse(
            success=True,
            data={'svg_uri': svg_uri}
        )
    except Exception as e:
        return ApiResponse(success=False, error=f"生成失败: {str(e)}")


@router.get("/script", summary="获取懒加载JavaScript")
async def get_lazy_load_script():
    """
    获取懒加载JavaScript代码
    
    Returns:
        JavaScript代码
    """
    try:
        script = lazy_load_optimizer.get_lazy_load_script()

        return ApiResponse(
            success=True,
            data={'script': script}
        )
    except Exception as e:
        return ApiResponse(success=False, error=f"获取失败: {str(e)}")


@router.get("/styles", summary="获取懒加载CSS样式")
async def get_lazy_load_styles():
    """
    获取懒加载CSS样式
    
    Returns:
        CSS样式
    """
    try:
        styles = lazy_load_optimizer.get_lazy_load_styles()

        return ApiResponse(
            success=True,
            data={'styles': styles}
        )
    except Exception as e:
        return ApiResponse(success=False, error=f"获取失败: {str(e)}")


@router.get("/config", summary="获取懒加载配置")
async def get_config(current_user=Depends(admin_required)):
    """
    获取懒加载配置
    
    Returns:
        配置信息
    """
    try:
        return ApiResponse(
            success=True,
            data=lazy_load_optimizer.config
        )
    except Exception as e:
        return ApiResponse(success=False, error=f"获取配置失败: {str(e)}")


@router.post("/update-config", summary="更新懒加载配置")
async def update_config(
        threshold: int = None,
        placeholder_color: str = None,
        fade_in_duration: int = None,
        current_user=Depends(admin_required)
):
    """
    更新懒加载配置
    
    Args:
        threshold: 提前加载距离（像素）
        placeholder_color: 占位符颜色
        fade_in_duration: 淡入动画时长（毫秒）
        
    Returns:
        更新结果
    """
    try:
        if threshold is not None:
            lazy_load_optimizer.config['threshold'] = threshold

        if placeholder_color is not None:
            lazy_load_optimizer.config['placeholder_color'] = placeholder_color

        if fade_in_duration is not None:
            lazy_load_optimizer.config['fade_in_duration'] = fade_in_duration

        return ApiResponse(
            success=True,
            data={
                'message': '配置已更新',
                'config': lazy_load_optimizer.config
            }
        )
    except Exception as e:
        return ApiResponse(success=False, error=f"更新配置失败: {str(e)}")
