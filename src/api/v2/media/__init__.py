"""
媒体API聚合路由器 - V2统一入口
包装 V1 media 包（13 个子路由），后续逐步迁移为原生 V2 实现
"""
from fastapi import APIRouter

_router = None


def _build_router():
    global _router
    if _router is not None:
        return _router

    router = APIRouter(tags=["media"])

    from src.api.v2.media_v1pack import router as media_router
    router.include_router(media_router)

    # VIP 离线下载路由
    from src.api.v2.media.offline_download import router as offline_download_router
    router.include_router(offline_download_router)

    # 图片编辑路由
    from src.api.v2.media.image_edit import router as image_edit_router
    router.include_router(image_edit_router, prefix="/edit")

    _router = router
    return _router


def __getattr__(name):
    if name == "router":
        return _build_router()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
