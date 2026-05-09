"""
广告管理系统 API
提供广告位管理、广告投放、统计等功能
"""

from fastapi import APIRouter, Depends, Query, Body
from datetime import datetime
from typing import Optional

from src.auth.auth_deps import get_current_active_user, admin_required as admin_required_api
from shared.models.user import User as UserModel
from shared.utils.response import ApiResponse
from shared.services.advertisement_system import advertisement_system

router = APIRouter(prefix="/ads", tags=["advertisements"])


@router.get("/slots", summary="获取所有广告位")
async def get_ad_slots():
    """
    获取系统中定义的所有广告位
    
    Returns:
        广告位列表
    """
    try:
        slots = advertisement_system.get_all_slots()

        return ApiResponse(
            success=True,
            data={
                'slots': slots,
                'count': len(slots),
            }
        )
    except Exception as e:
        return ApiResponse(success=False, error=f"获取广告位失败: {str(e)}")


@router.get("/slot/{slot_id}/ads", summary="获取广告位的广告")
async def get_slot_ads(
        slot_id: str,
):
    """
    获取指定广告位的可用广告(用于前端展示)
    
    Args:
        slot_id: 广告位ID
        
    Returns:
        广告列表
    """
    try:
        ads = advertisement_system.get_slot_ads(slot_id)

        # 记录展示
        for ad in ads:
            advertisement_system.record_impression(ad['ad_id'])

        return ApiResponse(
            success=True,
            data={
                'slot_id': slot_id,
                'ads': ads,
                'count': len(ads),
            }
        )
    except Exception as e:
        return ApiResponse(success=False, error=f"获取广告失败: {str(e)}")


@router.post("/click", summary="记录广告点击")
async def record_ad_click(
        ad_id: str = Body(..., embed=True, description="广告ID"),
        cost_per_click: float = Body(0, description="每次点击费用"),
):
    """
    记录广告点击(前端调用)
    
    Args:
        ad_id: 广告ID
        cost_per_click: 每次点击费用
        
    Returns:
        操作结果
    """
    try:
        advertisement_system.record_click(ad_id, cost_per_click)

        return ApiResponse(
            success=True,
            message='点击已记录'
        )
    except Exception as e:
        return ApiResponse(success=False, error=f"记录失败: {str(e)}")


# 管理员接口

@router.post("/admin/create", summary="创建广告")
async def create_ad(
        title: str = Body(..., description="广告标题"),
        slot_id: str = Body(..., description="广告位ID"),
        ad_type: str = Body('image', enum=['image', 'html', 'adsense', 'baidu'], description="广告类型"),
        content: str = Body('', description="广告内容"),
        image_url: Optional[str] = Body(None, description="图片URL"),
        link_url: Optional[str] = Body(None, description="跳转链接"),
        html_code: Optional[str] = Body(None, description="HTML代码"),
        start_date: Optional[str] = Body(None, description="开始时间(ISO格式)"),
        end_date: Optional[str] = Body(None, description="结束时间(ISO格式)"),
        priority: int = Body(5, ge=1, le=10, description="优先级(1-10)"),
        budget: Optional[float] = Body(None, description="预算上限"),
        current_user: UserModel = Depends(admin_required_api)
):
    """
    创建新广告
    
    Args:
        title: 广告标题
        slot_id: 广告位ID
        ad_type: 广告类型(image/html/adsense/baidu)
        content: 广告内容
        image_url: 图片URL
        link_url: 跳转链接
        html_code: HTML代码
        start_date: 开始时间
        end_date: 结束时间
        priority: 优先级
        budget: 预算上限
        
    Returns:
        创建结果
    """
    try:
        # 解析时间
        parsed_start = datetime.fromisoformat(start_date) if start_date else None
        parsed_end = datetime.fromisoformat(end_date) if end_date else None

        ad = advertisement_system.create_ad(
            title=title,
            slot_id=slot_id,
            ad_type=ad_type,
            content=content,
            image_url=image_url,
            link_url=link_url,
            html_code=html_code,
            start_date=parsed_start,
            end_date=parsed_end,
            priority=priority,
            budget=budget,
        )

        return ApiResponse(
            success=True,
            message='广告创建成功',
            data=ad
        )
    except ValueError as e:
        return ApiResponse(success=False, error=str(e))
    except Exception as e:
        return ApiResponse(success=False, error=f"创建失败: {str(e)}")


@router.get("/admin/list", summary="获取广告列表")
async def get_ad_list(
        slot_id: Optional[str] = Query(None, description="广告位过滤"),
        status: Optional[str] = Query(None, enum=['active', 'paused', 'expired'], description="状态过滤"),
        current_user: UserModel = Depends(admin_required_api)
):
    """
    获取广告列表(管理员)
    
    Args:
        slot_id: 广告位过滤
        status: 状态过滤
        
    Returns:
        广告列表
    """
    try:
        ads = advertisement_system.get_user_ads()

        # 过滤
        if slot_id:
            ads = [ad for ad in ads if ad['slot_id'] == slot_id]
        if status:
            ads = [ad for ad in ads if ad['status'] == status]

        return ApiResponse(
            success=True,
            data={
                'ads': ads,
                'count': len(ads),
            }
        )
    except Exception as e:
        return ApiResponse(success=False, error=f"获取列表失败: {str(e)}")


@router.post("/admin/{ad_id}/pause", summary="暂停广告")
async def pause_ad(
        ad_id: str,
        current_user: UserModel = Depends(admin_required_api)
):
    """
    暂停指定广告
    
    Args:
        ad_id: 广告ID
        
    Returns:
        操作结果
    """
    try:
        success = advertisement_system.pause_ad(ad_id)

        if success:
            return ApiResponse(
                success=True,
                message='广告已暂停'
            )
        else:
            return ApiResponse(success=False, error='广告不存在')
    except Exception as e:
        return ApiResponse(success=False, error=f"操作失败: {str(e)}")


@router.post("/admin/{ad_id}/activate", summary="激活广告")
async def activate_ad(
        ad_id: str,
        current_user: UserModel = Depends(admin_required_api)
):
    """
    激活指定广告
    
    Args:
        ad_id: 广告ID
        
    Returns:
        操作结果
    """
    try:
        success = advertisement_system.activate_ad(ad_id)

        if success:
            return ApiResponse(
                success=True,
                message='广告已激活'
            )
        else:
            return ApiResponse(success=False, error='广告不存在')
    except Exception as e:
        return ApiResponse(success=False, error=f"操作失败: {str(e)}")


@router.delete("/admin/{ad_id}", summary="删除广告")
async def delete_ad(
        ad_id: str,
        current_user: UserModel = Depends(admin_required_api)
):
    """
    删除指定广告
    
    Args:
        ad_id: 广告ID
        
    Returns:
        操作结果
    """
    try:
        success = advertisement_system.delete_ad(ad_id)

        if success:
            return ApiResponse(
                success=True,
                message='广告已删除'
            )
        else:
            return ApiResponse(success=False, error='广告不存在')
    except Exception as e:
        return ApiResponse(success=False, error=f"删除失败: {str(e)}")


@router.get("/admin/{ad_id}/stats", summary="获取广告统计")
async def get_ad_stats(
        ad_id: str,
        current_user: UserModel = Depends(admin_required_api)
):
    """
    获取广告统计数据
    
    Args:
        ad_id: 广告ID
        
    Returns:
        统计数据
    """
    try:
        stats = advertisement_system.get_ad_stats(ad_id)

        return ApiResponse(
            success=True,
            data=stats
        )
    except Exception as e:
        return ApiResponse(success=False, error=f"获取统计失败: {str(e)}")


@router.get("/admin/slot/{slot_id}/stats", summary="获取广告位统计")
async def get_slot_stats(
        slot_id: str,
        current_user: UserModel = Depends(admin_required_api)
):
    """
    获取广告位统计数据
    
    Args:
        slot_id: 广告位ID
        
    Returns:
        统计数据
    """
    try:
        stats = advertisement_system.get_slot_stats(slot_id)

        return ApiResponse(
            success=True,
            data=stats
        )
    except Exception as e:
        return ApiResponse(success=False, error=f"获取统计失败: {str(e)}")
