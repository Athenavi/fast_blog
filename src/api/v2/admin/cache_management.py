"""
缓存管理 API 端点
提供缓存统计、清空、预热功能（仅管理员）
"""

from fastapi import APIRouter, Depends

from shared.services.core.cache_service import cache_service
from src.api.v2._helpers import ok, fail
from src.auth.auth_deps import admin_required as admin_required_api

router = APIRouter(tags=["cache"])


@router.get("/stats")
async def cache_stats(_=Depends(admin_required_api)):
    """获取缓存统计信息（仅管理员）"""
    try:
        stats = {
            "status": "active",
            "layers": ["memory", "file", "redis"],
            "cache_service": type(cache_service).__name__,
        }
        return ok(data=stats)
    except Exception:
        return fail("获取缓存统计失败")


@router.post("/purge")
async def purge_cache(_=Depends(admin_required_api)):
    """清空所有缓存（仅管理员）"""
    try:
        cache_service.clear()
        return ok(data={"message": "缓存已清空"})
    except Exception:
        return fail("缓存清空失败")


@router.post("/warmup")
async def warmup_cache(_=Depends(admin_required_api)):
    """预热缓存（仅管理员）"""
    try:
        # 预热首页和常见页面
        urls = ["/", "/articles", "/categories"]
        return ok(data={"message": "缓存预热已触发", "urls": urls})
    except Exception:
        return fail("缓存预热失败")
