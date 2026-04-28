"""
社交媒体分享API
提供分享链接生成、定时分享、分享统计等功能
"""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession

from .social_share_service import social_share
from src.api.v1.responses import ApiResponse
from src.auth.auth_deps import  admin_required as admin_required_api
from src.extensions import get_async_db_session as get_async_db

router = APIRouter(tags=["social-share"])


@router.get("/share/generate-links")
async def generate_share_links(
        url: str = Query(..., description="分享的URL"),
        title: str = Query(..., description="标题"),
        summary: str = Query('', description="摘要"),
        image: str = Query('', description="图片URL"),
        platforms: Optional[str] = Query(None, description="指定平台,逗号分隔")
):
    """
    生成社交媒体分享链接
    
    支持平台: weibo, wechat, qq, twitter, facebook, linkedin, telegram
    """
    try:
        platform_list = platforms.split(',') if platforms else None

        links = social_share.generate_share_links(
            url=url,
            title=title,
            summary=summary,
            image=image,
            platforms=platform_list
        )

        return ApiResponse(
            success=True,
            data={
                'links': links,
                'metadata': social_share.get_share_metadata(
                    title=title,
                    description=summary,
                    url=url,
                    image=image
                )
            }
        )

    except Exception as e:
        return ApiResponse(success=False, error=f"生成分享链接失败: {str(e)}")


@router.get("/share/platforms")
async def get_supported_platforms():
    """获取支持的社交平台列表"""
    try:
        platforms = []
        for key, config in social_share.platforms.items():
            platforms.append({
                'id': key,
                'name': config['name'],
                'icon': config['icon'],
                'requires_api': config['requires_api']
            })

        return ApiResponse(
            success=True,
            data={'platforms': platforms}
        )

    except Exception as e:
        return ApiResponse(success=False, error=f"获取平台列表失败: {str(e)}")


@router.post("/share/schedule")
async def schedule_social_share(
        article_id: int = Body(...),
        platforms: List[str] = Body(...),
        scheduled_time: Optional[str] = Body(None),
        db: AsyncSession = Depends(get_async_db),
        current_user=Depends(admin_required_api)
):
    """
    调度文章分享到社交平台
    
    Args:
        article_id: 文章ID
        platforms: 目标平台列表
        scheduled_time: 计划时间(ISO格式),None表示立即分享
    """
    try:
        # 解析时间
        schedule_dt = None
        if scheduled_time:
            schedule_dt = datetime.fromisoformat(scheduled_time)

        result = await social_share.schedule_share(
            article_id=article_id,
            platforms=platforms,
            scheduled_time=schedule_dt,
            db_session=db
        )

        if result['success']:
            return ApiResponse(
                success=True,
                data=result,
                message="分享调度成功"
            )
        else:
            return ApiResponse(success=False, error=result.get('error'))

    except Exception as e:
        return ApiResponse(success=False, error=f"调度分享失败: {str(e)}")


@router.get("/share/statistics/{article_id}")
async def get_share_statistics(
        article_id: int,
        db: AsyncSession = Depends(get_async_db),
        current_user=Depends(admin_required_api)
):
    """获取文章分享统计数据"""
    try:
        result = social_share.get_share_statistics(article_id, db)

        if result['success']:
            return ApiResponse(
                success=True,
                data=result['data']
            )
        else:
            return ApiResponse(success=False, error=result.get('error'))

    except Exception as e:
        return ApiResponse(success=False, error=f"获取统计数据失败: {str(e)}")


@router.get("/share/buttons-html")
async def get_share_buttons_html(
        url: str = Query(..., description="分享URL"),
        title: str = Query(..., description="标题"),
        summary: str = Query('', description="摘要"),
        image: str = Query('', description="图片URL"),
        platforms: Optional[str] = Query(None, description="平台列表,逗号分隔"),
        style: str = Query('default', description="按钮样式(default/round/square)")
):
    """
    获取分享按钮HTML代码
    
    可直接嵌入到文章页面
    """
    try:
        platform_list = platforms.split(',') if platforms else None

        html = social_share.create_share_buttons_html(
            url=url,
            title=title,
            summary=summary,
            image=image,
            platforms=platform_list,
            style=style
        )

        return ApiResponse(
            success=True,
            data={'html': html}
        )

    except Exception as e:
        return ApiResponse(success=False, error=f"生成按钮HTML失败: {str(e)}")


@router.post("/share/validate-config")
async def validate_platform_config(
        platform: str = Body(...),
        config: dict = Body(...),
        current_user=Depends(admin_required_api)
):
    """
    验证社交平台API配置
    
    用于管理员配置各平台的API密钥
    """
    try:
        is_valid = social_share.validate_share_config(platform, config)

        return ApiResponse(
            success=True,
            data={
                'platform': platform,
                'is_valid': is_valid,
                'message': '配置有效' if is_valid else '配置不完整'
            }
        )

    except Exception as e:
        return ApiResponse(success=False, error=f"验证配置失败: {str(e)}")


@router.get("/share/og-metadata")
async def get_og_metadata(
        url: str = Query(...),
        title: str = Query(...),
        description: str = Query(...),
        image: str = Query(...)
):
    """
    获取Open Graph和Twitter Card元数据
    
    用于SEO优化
    """
    try:
        metadata = social_share.get_share_metadata(
            title=title,
            description=description,
            url=url,
            image=image
        )

        return ApiResponse(
            success=True,
            data={'metadata': metadata}
        )

    except Exception as e:
        return ApiResponse(success=False, error=f"获取元数据失败: {str(e)}")
