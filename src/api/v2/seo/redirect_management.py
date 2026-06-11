"""
重定向管理 API 端点
"""
from functools import wraps

from fastapi import APIRouter, Depends, HTTPException, Query

from shared.services.seo.redirect_manager import redirect_manager
from src.api.v2._helpers import ok, fail, _catch
from src.auth import jwt_required_dependency as jwt_required

router = APIRouter(tags=["redirects"])


@router.get("/", summary="获取所有重定向规则")
@_catch
async def list_redirects(
    enabled_only: bool = Query(False, description="只显示启用的"),
    page: int = Query(1, description="页码"),
    per_page: int = Query(50, description="每页数量"),
    current_user=Depends(jwt_required)
):
    """获取所有重定向规则"""
    result = redirect_manager.get_all_redirects(
        enabled_only=enabled_only,
        page=page,
        per_page=per_page
    )
    return ok(data=result)


@router.post("/", summary="创建重定向规则")
@_catch
async def create_redirect(
    source_url: str = Query(..., description="源URL"),
    target_url: str = Query(..., description="目标URL"),
    redirect_type: int = Query(301, description="重定向类型"),
    match_type: str = Query('exact', description="匹配类型 (exact/wildcard/regex)"),
    enabled: bool = Query(True, description="是否启用"),
    note: str = Query("", description="备注"),
    current_user=Depends(jwt_required)
):
    """创建重定向规则"""
    result = redirect_manager.add_redirect(
        source_url=source_url,
        target_url=target_url,
        redirect_type=redirect_type,
        match_type=match_type,
        enabled=enabled,
        note=note
    )
    if result['success']:
        return ok(data=result['redirect'], message=result['message'])
    return fail(result['error'])


@router.put("/{redirect_id}")
@_catch
async def update_redirect(
    redirect_id: int,
    source_url: str = Query(None, description="源URL"),
    target_url: str = Query(None, description="目标URL"),
    redirect_type: int = Query(None, description="重定向类型"),
    enabled: bool = Query(None, description="是否启用"),
    note: str = Query(None, description="备注"),
    current_user=Depends(jwt_required)
):
    """更新重定向规则"""
    result = redirect_manager.update_redirect(
        redirect_id=redirect_id,
        source_url=source_url,
        target_url=target_url,
        redirect_type=redirect_type,
        enabled=enabled,
        note=note
    )
    if result['success']:
        return ok(data=result['redirect'], message=result['message'])
    return fail(result['error'])


@router.delete("/{redirect_id}")
@_catch
async def delete_redirect(
    redirect_id: int,
    current_user=Depends(jwt_required)
):
    """删除重定向规则"""
    result = redirect_manager.delete_redirect(redirect_id)
    if result['success']:
        return ok(data=None, message=result['message'])
    return fail(result['error'])


@router.post("/bulk-import")
@_catch
async def bulk_import_redirects(
    redirects_data: list,
    current_user=Depends(jwt_required)
):
    """批量导入重定向规则"""
    result = redirect_manager.bulk_import(redirects_data)
    return ok(data=result, message=f"成功导入 {result['success_count']}/{result['total']} 条规则")


@router.get("/export")
@_catch
async def export_redirects(
    current_user=Depends(jwt_required)
):
    """导出所有重定向规则"""
    redirects = redirect_manager.export_redirects()
    return ok(data={"redirects": redirects})


@router.get("/404-suggestions")
@_catch
async def get_404_suggestions(
    recent_404s: list = None,
    current_user=Depends(jwt_required)
):
    """从404错误中获取重定向建议"""
    if not recent_404s:
        return fail("请提供404 URL列表")

    suggestions = redirect_manager.detect_404_candidates(recent_404s)
    return ok(data={"suggestions": suggestions, "total": len(suggestions)})


@router.get("/statistics")
@_catch
async def get_redirect_statistics(
        current_user=Depends(jwt_required)
):
    """获取重定向统计信息"""
    stats = redirect_manager.get_statistics()
    return ok(data=stats)


@router.post("/test")
@_catch
async def test_redirect_url(
        url: str = Query(..., description="要测试的URL"),
        current_user=Depends(jwt_required)
):
    """测试URL是否需要重定向"""
    result = redirect_manager.test_redirect(url)
    if result:
        return ok(data={"matched": True, "redirect": result})
    return ok(data={"matched": False, "message": "没有匹配的重定向规则"})
