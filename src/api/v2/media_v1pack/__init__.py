"""
媒体资源API包 - V2 统一入口（懒加载优化版）
"""
from fastapi import APIRouter

_router = None


def _build_router():
    global _router
    if _router is not None:
        return _router

    router = APIRouter(tags=["media"])

    # ── 延迟导入：仅在首次构建 router 时加载 ──
    from .routes_list import router as list_router
    from .routes_upload import router as upload_router
    from .routes_edit import router as edit_router
    from .routes_folders import router as folders_router
    from .routes_tags import router as tags_router
    from .routes_cover import router as cover_router
    from .cover_upload import router as cover_upload_router
    from .routes_cover_external import router as cover_external_router
    from .routes_edit_tools import router as edit_tools_router
    from .routes_enhancement import router as enhancement_router
    from .routes_thumbnail import router as thumbnail_router
    from .routes_audio_metadata import router as audio_metadata_router
    from .routes_settings_media import router as settings_media_router
    from .routes_stream import router as stream_router

    # ── 按顺序注册子路由（具体路径的必须优先于通配符）──
    router.include_router(list_router, prefix="")               # /files, /statistics, /categories, /tags
    router.include_router(upload_router, prefix="")             # /upload, /upload/chunked/*
    router.include_router(edit_router, prefix="")               # /detail/{media_id}, /batch-delete 等
    router.include_router(folders_router, prefix="/folders")    # /folders/*
    router.include_router(tags_router, prefix="")               # /{media_id}/tags
    router.include_router(cover_router, prefix="")              # /generate-cover/{media_id}, /remove-cover/{media_id}
    router.include_router(cover_upload_router, prefix="")       # /cover (POST)
    router.include_router(cover_external_router, prefix="/cover")   # /cover/from-url
    router.include_router(edit_tools_router, prefix="/edit")    # /edit/process, /edit/crop
    router.include_router(enhancement_router, prefix="")        # /optimize/{file_id}
    router.include_router(thumbnail_router, prefix="")          # /{media_id}/thumbnail
    router.include_router(audio_metadata_router, prefix="")     # /{media_id}/metadata
    router.include_router(settings_media_router, prefix="")     # /settings/upload
    router.include_router(stream_router, prefix="")             # /{media_id} — 通配符，必须最后

    _router = router
    return _router


def __getattr__(name):
    if name == "router":
        return _build_router()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
