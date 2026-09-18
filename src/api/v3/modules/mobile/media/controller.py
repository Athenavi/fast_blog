"""mobile/media：前台用户端的媒体库

路由前缀：``/api/v3/mobile/media``

范围（**只操作自己的数据**）：
- 上传：``/upload/image``、``/upload/article-cover``
- 我的媒体：``/list``、``/{id}``（含更新与删除）、``/batch/delete``
- 我的文件夹：``/folders``（树）、``/folders/{id}``
- 容量统计：``/stats``

复用 ``modules/content/media`` 的 ``media_service``（校验、落盘、序列化都在那里），
归属过滤与越权拦截在 ``mobile/media/service.py`` 里统一处理。

> 路由注册顺序：``/list``、``/folders``、``/stats`` 等静态路径必须写在 ``/{media_id}`` 之前，
> 否则会被动态段抢先匹配。

范围说明：legacy 移动端上传里有一段图片压缩处理（依赖 PIL），本次**未迁移**——
它属于上传优化而非功能必需，且需要单独确认压缩参数与目标目录，记入二期。
"""

from typing import Optional

from fastapi import APIRouter, Depends, File, Query, UploadFile

from src.api.v3.common import response as resp
from src.api.v3.common.response import ResponseModel
from src.api.v3.core.deps import DBSession, PageDep
from src.api.v3.core.exceptions import BadRequestError
from src.api.v3.core.router_class import OperationLogRoute
from src.api.v3.modules.content.media.service import media_service
from src.api.v3.modules.mobile.media.schema import (
    MobileFolderCreate,
    MobileMediaQuery,
    MobileMediaUpdate,
)
from src.api.v3.modules.mobile.media.service import mobile_media_service
from src.auth.auth_deps import jwt_required_dependency

router = APIRouter(prefix="/media", tags=["mobile-media"], route_class=OperationLogRoute)


# ---------------------------------------------------------------- 上传
async def _store(current, db: DBSession, file: UploadFile) -> dict:
    if file is None or not file.filename:
        raise BadRequestError("未找到上传的文件")
    results = await media_service.upload_files(
        db, user_id=current.id, files=[(file.filename, await file.read())]
    )
    return results[0] if results else {}


@router.post("/upload/image", response_model=ResponseModel, summary="上传图片（需登录）")
async def upload_image(
    db: DBSession,
    user=Depends(jwt_required_dependency),
    file: UploadFile = File(...),
) -> dict:
    return resp.success(await _store(user, db, file), msg="上传成功")


@router.post("/upload/article-cover", response_model=ResponseModel, summary="上传文章封面（需登录）")
async def upload_article_cover(
    db: DBSession,
    user=Depends(jwt_required_dependency),
    file: UploadFile = File(...),
) -> dict:
    """与 ``/upload/image`` 同一实现，语义别名（移动端封面场景）"""
    return resp.success(await _store(user, db, file), msg="上传成功")


# ---------------------------------------------------------------- 我的媒体（静态路径在前）
@router.get("/list", response_model=ResponseModel, summary="我的媒体列表（需登录）")
async def list_my_media(
    db: DBSession,
    page: PageDep,
    user=Depends(jwt_required_dependency),
    folder_id: Optional[int] = Query(default=None),
    mime_type: Optional[str] = Query(default=None, description="前缀匹配，如 image/"),
    keyword: Optional[str] = Query(default=None),
) -> dict:
    query = MobileMediaQuery(
        page=page.page,
        page_size=page.page_size,
        folder_id=folder_id,
        mime_type=mime_type,
        keyword=keyword,
    )
    items, total = await mobile_media_service.list_mine(
        db,
        user,
        page=query.page,
        page_size=query.page_size,
        folder_id=query.folder_id,
        mime_type=query.mime_type,
        keyword=query.keyword,
    )
    return resp.success_page(items, total, query.page, query.page_size)


@router.get("/stats", response_model=ResponseModel, summary="我的容量统计（需登录）")
async def my_media_stats(db: DBSession, user=Depends(jwt_required_dependency)) -> dict:
    return resp.success(await mobile_media_service.stats(db, user))


@router.get("/folders", response_model=ResponseModel, summary="我的文件夹树（需登录）")
async def my_folders(db: DBSession, user=Depends(jwt_required_dependency)) -> dict:
    return resp.success(await mobile_media_service.folder_tree(db, user))


@router.post("/folders", response_model=ResponseModel, summary="新建文件夹（需登录）")
async def create_my_folder(
    payload: MobileFolderCreate,
    db: DBSession,
    user=Depends(jwt_required_dependency),
) -> dict:
    return resp.success(await mobile_media_service.create_folder(db, user, payload), msg="已创建")


@router.put("/folders/{folder_id}", response_model=ResponseModel, summary="重命名文件夹（需登录）")
async def update_my_folder(
    folder_id: int,
    payload: MobileMediaUpdate,
    db: DBSession,
    user=Depends(jwt_required_dependency),
) -> dict:
    data = payload.model_dump(exclude_unset=True, exclude={"folder_id", "tags", "alt_text"})
    return resp.success(
        await mobile_media_service.rename_folder(db, user, folder_id, data), msg="已保存"
    )


@router.delete("/folders/{folder_id}", response_model=ResponseModel, summary="删除文件夹（需登录）")
async def delete_my_folder(
    folder_id: int,
    db: DBSession,
    user=Depends(jwt_required_dependency),
) -> dict:
    await mobile_media_service.delete_folder(db, user, folder_id)
    return resp.success(None, msg="已删除")


@router.post("/batch/delete", response_model=ResponseModel, summary="批量删除我的媒体（需登录）")
async def batch_delete_my_media(
    payload: dict,
    db: DBSession,
    user=Depends(jwt_required_dependency),
) -> dict:
    ids = payload.get("ids") or []
    if not isinstance(ids, list):
        raise BadRequestError("ids 必须是数组")
    return resp.success(
        await mobile_media_service.batch_delete_mine(db, user, [int(i) for i in ids]),
        msg="已删除",
    )


# ---------------------------------------------------------------- 单条（动态段在最后）
@router.get("/{media_id}", response_model=ResponseModel, summary="媒体详情（需登录，仅限本人）")
async def get_my_media(
    media_id: int,
    db: DBSession,
    user=Depends(jwt_required_dependency),
) -> dict:
    return resp.success(await mobile_media_service.get_mine(db, user, media_id))


@router.put("/{media_id}", response_model=ResponseModel, summary="更新媒体信息（需登录，仅限本人）")
async def update_my_media(
    media_id: int,
    payload: MobileMediaUpdate,
    db: DBSession,
    user=Depends(jwt_required_dependency),
) -> dict:
    return resp.success(
        await mobile_media_service.update_mine(db, user, media_id, payload), msg="已保存"
    )


@router.delete("/{media_id}", response_model=ResponseModel, summary="删除媒体（需登录，仅限本人）")
async def delete_my_media(
    media_id: int,
    db: DBSession,
    user=Depends(jwt_required_dependency),
) -> dict:
    await mobile_media_service.delete_mine(db, user, media_id)
    return resp.success(None, msg="已删除")
