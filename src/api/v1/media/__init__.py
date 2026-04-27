"""
媒体资源API包 - 汇总所有子路由
"""
from fastapi import APIRouter

from .routes_edit import router as edit_router
from .routes_edit_tools import router as edit_tools_router
from .routes_enhancement import router as enhancement_router
from .routes_folders import router as folders_router
from .routes_list import router as list_router
from .routes_stream import router as stream_router
from .routes_tags import router as tags_router
from .routes_upload import router as upload_router

router = APIRouter(tags=["media"])

# 按顺序包含子路由
# 注意：具体路径的路由必须先于通配符路由注册，避免路径冲突
# 1. 首先注册所有具体路径的路由
router.include_router(list_router, prefix="")  # /list, /statistics, /categories, /tags
router.include_router(upload_router, prefix="")  # /upload, /upload/chunked/*
router.include_router(edit_router, prefix="")  # /detail/{media_id}, /batch-delete 等
router.include_router(folders_router, prefix="")  # /folders/* - 文件夹相关路由
router.include_router(tags_router, prefix="")  # /{media_id}/tags 等（虽然有动态参数，但有后缀）
router.include_router(edit_tools_router, prefix="")  # /process, /crop 等
router.include_router(enhancement_router, prefix="")  # /optimize/{file_id} 等（虽然有动态参数，但有前缀）

# 2. 最后注册包含根路径通配符的路由（必须放在最后！）
router.include_router(stream_router, prefix="")  # /{media_id} - 通配符，必须最后
