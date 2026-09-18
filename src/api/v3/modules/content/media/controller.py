"""media 模块路由

**管理端（需权限码）**::

    GET    /api/v3/content/media                     媒体列表
    POST   /api/v3/content/media/upload              上传（multipart，多文件）
    POST   /api/v3/content/media/batch/delete        批量删除
    GET    /api/v3/content/media/folders             文件夹列表
    GET    /api/v3/content/media/folders/tree        文件夹树
    POST   /api/v3/content/media/folders             新建文件夹
    PUT    /api/v3/content/media/folders/{folder_id} 更新文件夹
    DELETE /api/v3/content/media/folders/{folder_id} 删除文件夹
    GET    /api/v3/content/media/{media_id}          媒体详情
    PUT    /api/v3/content/media/{media_id}          更新元信息
    DELETE /api/v3/content/media/{media_id}          删除媒体

静态路径（``/upload``、``/folders``、``/batch/delete``）必须在 ``/{media_id}`` 之前注册。

权限码：``media:view`` / ``media:upload`` / ``media:delete``
"""

from typing import List, Optional

from fastapi import APIRouter, File, Query, UploadFile

from src.api.v3.common import response as resp
from src.api.v3.common.response import ResponseModel
from src.api.v3.core.deps import AuthControl, CurrentUser, DBSession, PageDep
from src.api.v3.core.exceptions import BadRequestError
from src.api.v3.core.permission import codes
from src.api.v3.core.router_class import OperationLogRoute
from src.api.v3.modules.content.media.schema import (
    MediaBatchDeleteRequest,
    MediaFolderCreate,
    MediaFolderUpdate,
    MediaUpdate,
)
from src.api.v3.modules.content.media.service import media_service

router = APIRouter(prefix="/media", tags=["content-media"], route_class=OperationLogRoute)


# ─────────────────────────── 上传（静态路径优先）───────────────────────────
@router.post("/upload", response_model=ResponseModel, summary="上传媒体文件")
async def upload_media(
    db: DBSession,
    current: CurrentUser,
    _perm=AuthControl(codes.MEDIA_UPLOAD),
    files: List[UploadFile] = File(..., description="可多选"),
) -> dict:
    if not files:
        raise BadRequestError("未找到上传的文件")
    payloads = [(file.filename or "unnamed", await file.read()) for file in files]
    results = await media_service.upload_files(db, user_id=current.id, files=payloads)
    return resp.success({"files": results}, msg="上传完成")


# ─────────────────────────── 批量删除 ───────────────────────────
@router.post("/batch/delete", response_model=ResponseModel, summary="批量删除媒体")
async def batch_delete_media(
    payload: MediaBatchDeleteRequest,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.MEDIA_DELETE),
) -> dict:
    affected = await media_service.batch_delete(db, payload.ids)
    return resp.success({"affected": affected}, msg=f"已删除 {affected} 项")


# ─────────────────────────── 文件夹（静态路径优先）───────────────────────────
@router.get("/folders", response_model=ResponseModel, summary="文件夹列表")
async def list_folders(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.MEDIA_VIEW),
    user_id: Optional[int] = Query(default=None),
    is_public: Optional[bool] = Query(default=None),
) -> dict:
    folders = await media_service.list_folders(db, user_id=user_id, is_public=is_public)
    return resp.success_page(folders, len(folders), 1, len(folders) or 1)


@router.get("/folders/tree", response_model=ResponseModel, summary="文件夹树")
async def folder_tree(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.MEDIA_VIEW),
    user_id: Optional[int] = Query(default=None),
) -> dict:
    return resp.success(await media_service.folder_tree(db, user_id=user_id))


@router.post("/folders", response_model=ResponseModel, summary="新建文件夹")
async def create_folder(
    payload: MediaFolderCreate,
    db: DBSession,
    current: CurrentUser,
    _perm=AuthControl(codes.MEDIA_UPLOAD),
) -> dict:
    return resp.success(
        await media_service.create_folder(db, payload, user_id=current.id), msg="创建成功"
    )


@router.put("/folders/{folder_id}", response_model=ResponseModel, summary="更新文件夹")
async def update_folder(
    folder_id: int,
    payload: MediaFolderUpdate,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.MEDIA_UPLOAD),
) -> dict:
    return resp.success(await media_service.update_folder(db, folder_id, payload), msg="更新成功")


@router.delete("/folders/{folder_id}", response_model=ResponseModel, summary="删除文件夹")
async def delete_folder(
    folder_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.MEDIA_UPLOAD),
) -> dict:
    await media_service.delete_folder(db, folder_id)
    return resp.success(None, msg="已删除")


# ─────────────────────────── 列表 ───────────────────────────
@router.get("", response_model=ResponseModel, summary="媒体列表")
@router.get(
    "/list",
    response_model=ResponseModel,
    include_in_schema=False,
    summary="[兼容 FastApiAdmin] 媒体列表",
)
async def list_media(
    page: PageDep,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.MEDIA_VIEW),
    folder_id: Optional[int] = Query(default=None),
    mime_type: Optional[str] = Query(default=None),
    user_id: Optional[int] = Query(default=None),
    is_public: Optional[bool] = Query(default=None),
    category: Optional[str] = Query(default=None),
) -> dict:
    items, total = await media_service.list_media(
        db,
        page=page.page,
        page_size=page.page_size,
        keyword=page.keyword,
        folder_id=folder_id,
        mime_type=mime_type,
        user_id=user_id,
        is_public=is_public,
        category=category,
        order_by=page.order_by,
        order=page.order,
        scope_user=_current,
    )
    return resp.success_page(items, total, page.page, page.page_size)


# ─────────────────────────── 详情 / 更新 / 删除 ───────────────────────────
@router.get("/{media_id}", response_model=ResponseModel, summary="媒体详情")
@router.get(
    "/detail/{media_id}",
    response_model=ResponseModel,
    include_in_schema=False,
    summary="[兼容 FastApiAdmin] 媒体详情",
)
async def get_media(
    media_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.MEDIA_VIEW),
) -> dict:
    return resp.success(await media_service.get_media(db, media_id, scope_user=_current))


@router.put("/{media_id}", response_model=ResponseModel, summary="更新媒体元信息")
@router.put(
    "/update/{media_id}",
    response_model=ResponseModel,
    include_in_schema=False,
    summary="[兼容 FastApiAdmin] 更新媒体",
)
async def update_media(
    media_id: int,
    payload: MediaUpdate,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.MEDIA_UPLOAD),
) -> dict:
    return resp.success(await media_service.update_media(db, media_id, payload), msg="更新成功")


@router.delete("/{media_id}", response_model=ResponseModel, summary="删除媒体")
async def delete_media(
    media_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.MEDIA_DELETE),
) -> dict:
    await media_service.delete_media(db, media_id)
    return resp.success(None, msg="已删除")
