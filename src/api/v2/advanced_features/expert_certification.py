"""
专家认证系统 API
提供领域专家申请、审核、认证标识等功能
"""
from functools import wraps

from fastapi import APIRouter, Depends, HTTPException, Query, Body

from shared.models.user import User as UserModel
from shared.services.advanced_features.expert_certification_system import expert_certification_system
from src.api.v2._helpers import ok, fail, _catch
from src.auth.auth_deps import get_current_active_user, admin_required as admin_required_api

router = APIRouter(tags=["expert-certification"])


@router.get("/fields", summary="获取可认证领域")
@_catch
async def get_available_fields():
    """获取所有可申请的认证领域"""
    fields = expert_certification_system.get_available_fields()
    return ok(data={'fields': fields, 'count': len(fields)})


@router.post("/apply", summary="申请专家认证")
@_catch
async def apply_certification(
        field_id: str = Body(..., description="认证领域ID"),
        credentials: dict = Body(..., description="资质证明"),
        bio: str = Body('', description="个人简介"),
        current_user: UserModel = Depends(get_current_active_user)
):
    """提交专家认证申请"""
    app_id = expert_certification_system.apply_certification(
        user_id=current_user.id, field_id=field_id,
        credentials=credentials, bio=bio,
    )
    return ok(data={'application_id': app_id}, message='申请已提交，等待审核')


@router.get("/my-status", summary="获取我的认证状态")
@_catch
async def get_my_certification_status(current_user: UserModel = Depends(get_current_active_user)):
    """获取当前用户的认证状态"""
    cert = expert_certification_system.get_user_certification(current_user.id)
    if not cert:
        return ok(data={'is_certified': False, 'message': '未认证'})
    return ok(data={'is_certified': True, 'certification': cert})


@router.get("/check-expert/{user_id}", summary="检查用户是否是专家")
@_catch
async def check_expert(
        user_id: int,
        field_id: str = Query(None, description="领域ID(可选)"),
):
    """检查指定用户是否是认证专家"""
    is_expert = expert_certification_system.is_expert(user_id, field_id)
    return ok(data={'user_id': user_id, 'is_expert': is_expert, 'field_id': field_id})


@router.get("/experts", summary="获取认证专家列表")
@_catch
async def get_certified_experts(
        field_id: str = Query(None, description="领域过滤"),
        limit: int = Query(100, ge=1, le=500, description="返回数量"),
):
    """获取已认证的专家列表"""
    experts = expert_certification_system.get_certified_experts(field_id=field_id, limit=limit)
    return ok(data={'experts': experts, 'count': len(experts), 'field_id': field_id})


@router.get("/admin/pending-applications", summary="获取待审核申请")
@_catch
async def get_pending_applications(
        field_id: str = Query(None, description="领域过滤"),
        current_user: UserModel = Depends(admin_required_api)
):
    """获取所有待审核的认证申请"""
    applications = expert_certification_system.get_pending_applications(field_id=field_id)
    return ok(data={'applications': applications, 'count': len(applications)})


@router.get("/admin/application/{application_id}", summary="获取申请详情")
@_catch
async def get_application_details(
        application_id: str,
        current_user: UserModel = Depends(admin_required_api)
):
    """获取认证申请详情"""
    details = expert_certification_system.get_application_details(application_id)
    if not details:
        return fail('申请不存在')
    return ok(data=details)


@router.post("/admin/review", summary="审核认证申请")
@_catch
async def review_application(
        application_id: str = Body(..., description="申请ID"),
        approved: bool = Body(..., description="是否通过"),
        rejection_reason: str = Body(None, description="拒绝原因"),
        current_user: UserModel = Depends(admin_required_api)
):
    """审核专家认证申请"""
    success = expert_certification_system.review_application(
        application_id=application_id, reviewer_id=current_user.id,
        approved=approved, rejection_reason=rejection_reason,
    )
    if success:
        status = '已通过' if approved else '已拒绝'
        return ok(data=None, message=f'申请{status}')
    return fail('审核失败')


@router.post("/admin/revoke", summary="撤销专家认证")
@_catch
async def revoke_certification(
        user_id: int = Body(..., description="用户ID"),
        reason: str = Body('', description="撤销原因"),
        current_user: UserModel = Depends(admin_required_api)
):
    """撤销用户的专家认证"""
    success = expert_certification_system.revoke_certification(user_id, reason)
    if success:
        return ok(data=None, message='认证已撤销')
    return fail('撤销失败')


@router.get("/admin/stats", summary="获取认证系统统计")
@_catch
async def get_certification_stats(current_user: UserModel = Depends(admin_required_api)):
    """获取专家认证系统整体统计"""
    stats = expert_certification_system.get_certification_stats()
    return ok(data=stats)
