"""
用户画像 API
提供用户活跃度、兴趣标签、流失风险等查询功能
"""

from fastapi import APIRouter, Depends, Query

from src.api.v1.core.responses import ApiResponse
from shared.services.users.user_profile_service import user_profile_service
from src.auth.auth_deps import get_current_active_user, admin_required as admin_required_api

router = APIRouter(tags=["user-profile"])


@router.get("/activity/{user_id}", summary="获取用户活跃度")
async def get_user_activity(
        user_id: int,
        days: int = Query(30, ge=7, le=90, description="统计天数"),
        current_user=Depends(get_current_active_user)
):
    """
    获取用户活跃度等级和评分
    
    Args:
        user_id: 用户ID
        days: 统计天数（7-90天）
        
    Returns:
        活跃度信息 {score, level, level_name, description}
    """
    try:
        activity = user_profile_service.get_activity_level(user_id, days)

        return ApiResponse(
            success=True,
            data=activity
        )
    except Exception as e:
        return ApiResponse(success=False, error=f"获取活跃度失败: {str(e)}")


@router.get("/interests/{user_id}", summary="获取用户兴趣标签")
async def get_user_interests(
        user_id: int,
        top_n: int = Query(10, ge=1, le=50, description="返回标签数量"),
        current_user=Depends(get_current_active_user)
):
    """
    获取用户兴趣标签列表
    
    基于用户的阅读历史、点赞、收藏等行为分析得出。
    
    Args:
        user_id: 用户ID
        top_n: 返回前N个标签（1-50）
        
    Returns:
        兴趣标签列表 [{tag, weight, article_count}]
    """
    try:
        interests = user_profile_service.get_user_interests(user_id, top_n)

        return ApiResponse(
            success=True,
            data={
                'interests': interests,
                'count': len(interests),
            }
        )
    except Exception as e:
        return ApiResponse(success=False, error=f"获取兴趣标签失败: {str(e)}")


@router.get("/churn-risk/{user_id}", summary="预测用户流失风险")
async def predict_churn_risk(
        user_id: int,
        current_user=Depends(get_current_active_user)
):
    """
    预测用户流失风险
    
    分析用户登录频率、活跃度趋势、互动行为等指标，
    评估流失风险并提供建议。
    
    Args:
        user_id: 用户ID
        
    Returns:
        流失风险信息 {risk_level, risk_score, reasons, suggestions}
    """
    try:
        risk = user_profile_service.predict_churn_risk(user_id)

        return ApiResponse(
            success=True,
            data=risk
        )
    except Exception as e:
        return ApiResponse(success=False, error=f"预测流失风险失败: {str(e)}")


@router.get("/{user_id}", summary="获取完整用户画像")
async def get_user_profile(
        user_id: int,
        current_user=Depends(get_current_active_user)
):
    """
    获取完整的用户画像数据
    
    包括活跃度、兴趣标签、流失风险、统计数据等。
    
    Args:
        user_id: 用户ID
        
    Returns:
        完整用户画像
    """
    try:
        profile = user_profile_service.get_user_profile(user_id)

        return ApiResponse(
            success=True,
            data=profile
        )
    except Exception as e:
        return ApiResponse(success=False, error=f"获取用户画像失败: {str(e)}")


@router.post("/track-activity", summary="记录用户活动")
async def track_user_activity(
        user_id: int = Query(..., description="用户ID"),
        activity_type: str = Query(..., enum=['view', 'like', 'comment', 'share', 'bookmark', 'login'],
                                   description="活动类型"),
        article_id: int = Query(None, description="文章ID"),
        tags: str = Query(None, description="文章标签（逗号分隔）"),
        current_user=Depends(get_current_active_user)
):
    """
    记录用户活动用于画像分析
    
    前端应在用户执行相应操作时调用此接口。
    
    Args:
        user_id: 用户ID
        activity_type: 活动类型 (view/like/comment/share/bookmark/login)
        article_id: 文章ID（可选）
        tags: 文章标签（可选，逗号分隔）
        
    Returns:
        操作结果
    """
    try:
        # 解析标签
        tag_list = [t.strip() for t in tags.split(',')] if tags else []

        user_profile_service.record_activity(
            user_id=user_id,
            activity_type=activity_type,
            article_id=article_id,
            tags=tag_list,
        )

        return ApiResponse(
            success=True,
            message='活动已记录'
        )
    except Exception as e:
        return ApiResponse(success=False, error=f"记录活动失败: {str(e)}")


# ==================== 管理员接口 ====================

@router.get("/admin/activity-distribution", summary="获取活跃度分布（管理员）")
async def get_activity_distribution(
        days: int = Query(30, ge=7, le=90, description="统计天数"),
        current_user=Depends(admin_required_api)
):
    """
    获取所有用户的活跃度分布统计
    
    仅管理员可访问。
    
    Args:
        days: 统计天数
        
    Returns:
        活跃度分布数据
    """
    try:
        # 这里应该从数据库查询所有用户
        # 简化实现：返回示例数据
        distribution = {
            'super_active': 0,  # 超级活跃
            'active': 0,  # 活跃
            'moderate': 0,  # 一般
            'inactive': 0,  # 不活跃
            'dormant': 0,  # 沉睡
        }

        return ApiResponse(
            success=True,
            data={
                'distribution': distribution,
                'period_days': days,
                'note': '需要集成数据库查询以获取真实数据',
            }
        )
    except Exception as e:
        return ApiResponse(success=False, error=f"获取分布失败: {str(e)}")


@router.get("/admin/churn-risk-summary", summary="获取流失风险汇总（管理员）")
async def get_churn_risk_summary(
        current_user=Depends(admin_required_api)
):
    """
    获取用户流失风险汇总统计
    
    仅管理员可访问。
    
    Returns:
        流失风险汇总数据
    """
    try:
        # 简化实现：返回示例数据
        summary = {
            'high_risk_count': 0,
            'medium_risk_count': 0,
            'low_risk_count': 0,
            'minimal_risk_count': 0,
            'total_analyzed': 0,
        }

        return ApiResponse(
            success=True,
            data=summary
        )
    except Exception as e:
        return ApiResponse(success=False, error=f"获取汇总失败: {str(e)}")
