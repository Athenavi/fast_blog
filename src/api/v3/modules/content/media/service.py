"""media 模块业务逻辑

上传链路**照搬** v2 的实现（``src/api/v2/media_legacy/routes_upload.py:81``）：
``FileProcessor.validate_file`` 校验（类型/大小）→ ``process_single_file`` 落盘 + 建记录。
不重写校验与落盘逻辑，避免两套行为漂移。
"""

from typing import Any, List, Optional, Sequence, Tuple

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.config.settings import app_config
from shared.models.media.media import Media
from shared.models.media.media_folder import MediaFolder
from src.api.v3.common.tags import normalize_tags
from src.api.v3.core.exceptions import BadRequestError, ConflictError, NotFoundError
from src.api.v3.core.logger import get_logger
from src.api.v3.core.permission.scope import ensure_object_in_scope
from src.api.v3.modules.content.media.crud import media_crud, media_folder_crud
from src.api.v3.modules.content.media.schema import (
    MediaFolderCreate,
    MediaFolderUpdate,
    MediaUpdate,
)

logger = get_logger("media")

DEFAULT_UPLOAD_LIMIT = 10 * 1024 * 1024


def to_out(media: Media) -> dict:
    """媒体条目 → 响应字典（**不含 file_path**，避免暴露磁盘结构）"""
    return {
        "id": media.id,
        "user_id": media.user,
        "filename": media.filename,
        "original_filename": media.original_filename,
        "file_url": media.file_url,
        "file_size": media.file_size,
        "mime_type": media.mime_type,
        "file_type": media.file_type,
        "width": media.width,
        "height": media.height,
        "duration": media.duration,
        "thumbnail_url": media.thumbnail_url,
        "description": media.description,
        "alt_text": media.alt_text,
        "is_public": bool(media.is_public),
        "download_count": media.download_count or 0,
        "category": media.category,
        "tags": normalize_tags(media.tags),
        "folder_id": media.folder_id,
        "created_at": media.created_at,
        "updated_at": media.updated_at,
    }


def _folder_out(folder: MediaFolder) -> dict:
    return {
        "id": folder.id,
        "name": folder.name,
        "parent_id": folder.parent_id,
        "user_id": folder.user,
        "description": folder.description,
        "sort_order": folder.sort_order or 0,
        "is_public": bool(folder.is_public),
        "media_count": folder.media_count or 0,
        "created_at": folder.created_at,
        "updated_at": folder.updated_at,
        "children": [],
    }


def build_folder_tree(folders: Sequence[dict]) -> List[dict]:
    by_id = {item["id"]: item for item in folders}
    roots: List[dict] = []
    for item in by_id.values():
        parent = by_id.get(item["parent_id"]) if item["parent_id"] else None
        if parent is not None and parent["id"] != item["id"]:
            parent["children"].append(item)
        else:
            roots.append(item)

    def _sort(nodes: List[dict]) -> List[dict]:
        nodes.sort(key=lambda node: (node.get("sort_order") or 0, node["id"]))
        for node in nodes:
            _sort(node["children"])
        return nodes

    return _sort(roots)


class MediaService:
    """媒体库"""

    # ------------------------------------------------------------------ 查询
    async def list_media(
        self,
        db: AsyncSession,
        *,
        page: int = 1,
        page_size: int = 20,
        keyword: Optional[str] = None,
        folder_id: Optional[int] = None,
        mime_type: Optional[str] = None,
        user_id: Optional[int] = None,
        is_public: Optional[bool] = None,
        category: Optional[str] = None,
        order_by: Optional[str] = None,
        order: str = "desc",
        scope_user: Any = None,
    ) -> Tuple[List[dict], int]:
        items, total = await media_crud.list(
            db,
            page=page,
            page_size=page_size,
            keyword=keyword,
            filters={
                "folder_id": folder_id,
                "mime_type": mime_type,
                "user": user_id,
                "is_public": is_public,
                "category": category,
            },
            order_by=order_by or "id",
            order=order,
            scope_user=scope_user,
        )
        return [to_out(item) for item in items], total

    async def get_media(
        self, db: AsyncSession, media_id: int, *, scope_user: Any = None
    ) -> dict:
        media = await media_crud.get(db, media_id)
        if media is None:
            raise NotFoundError("媒体不存在")
        if scope_user is not None:
            await ensure_object_in_scope(db, Media, media, user=scope_user)
        return to_out(media)

    # ------------------------------------------------------------------ 上传
    async def upload_files(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        files: Sequence[Tuple[str, bytes]],
    ) -> List[dict]:
        """批量上传（复用现有处理器做校验与落盘）"""
        from src.api.v2.media_legacy.allowed_mimes import ALLOWED_MIMES_LIST
        from src.utils.upload.public_upload import FileProcessor, process_single_file

        allowed_size = getattr(app_config, "UPLOAD_LIMIT", DEFAULT_UPLOAD_LIMIT)
        allowed_mimes = set(str(m) for m in getattr(app_config, "ALLOWED_MIMES", ALLOWED_MIMES_LIST))

        results: List[dict] = []
        for filename, file_data in files:
            processor = FileProcessor(
                user_id, allowed_mimes=allowed_mimes, allowed_size=allowed_size
            )
            is_valid, validation_result = processor.validate_file(file_data, filename)
            if not is_valid:
                logger.warning("文件校验未通过 filename=%s reason=%s", filename, validation_result)
                results.append({"filename": filename, "success": False, "error": str(validation_result)})
                continue

            try:
                result = await process_single_file(processor, file_data, filename, db)
            except Exception as exc:  # noqa: BLE001
                logger.exception("文件处理失败 filename=%s", filename)
                results.append({"filename": filename, "success": False, "error": str(exc)})
                continue

            if not result.get("success"):
                results.append(
                    {"filename": filename, "success": False, "error": result.get("error", "处理失败")}
                )
                continue

            data = result.get("data") or {}
            data["success"] = True
            results.append(data)
            await self._trigger_webhook(db, data, user_id)

        succeeded = [item for item in results if item.get("success")]
        if not succeeded:
            errors = "; ".join(str(item.get("error")) for item in results) or "上传失败"
            raise BadRequestError(f"文件上传失败：{errors}")
        return results

    @staticmethod
    async def _trigger_webhook(db: AsyncSession, data: dict, user_id: int) -> None:
        try:
            from datetime import datetime

            from shared.services.notifications.webhook_service import webhook_service

            await webhook_service.trigger_event(
                "media.uploaded",
                {
                    "file_id": data.get("id"),
                    "filename": data.get("filename"),
                    "file_type": data.get("mime_type"),
                    "file_size": data.get("size"),
                    "url": data.get("url"),
                    "uploaded_by": user_id,
                    "uploaded_at": datetime.now().isoformat(),
                },
                db=db,
            )
        except Exception:  # noqa: BLE001 - webhook 失败不影响上传
            logger.exception("媒体上传 webhook 触发失败")

    # ------------------------------------------------------------------ 更新 / 删除
    async def update_media(self, db: AsyncSession, media_id: int, payload: MediaUpdate) -> dict:
        media = await media_crud.get(db, media_id)
        if media is None:
            raise NotFoundError("媒体不存在")

        data = payload.model_dump(exclude_unset=True)
        if "tags" in data and data["tags"] is not None:
            data["tags"] = ",".join(normalize_tags(data["tags"]))
        if "folder_id" in data and data["folder_id"] is not None:
            folder = await media_folder_crud.get(db, data["folder_id"])
            if folder is None:
                raise NotFoundError("目标文件夹不存在")

        media = await media_crud.update(db, media, data)
        return to_out(media)

    async def delete_media(self, db: AsyncSession, media_id: int) -> None:
        """删除媒体记录

        说明：只删数据库记录；磁盘/对象存储上的文件由存储清理任务处理（二期），
        因为 ``s3_storage`` 的删除接口尚未在 v3 侧确认。
        """
        media = await media_crud.get(db, media_id)
        if media is None:
            raise NotFoundError("媒体不存在")
        await media_crud.remove(db, media)

    async def batch_delete(self, db: AsyncSession, ids: Sequence[int]) -> int:
        count = 0
        for media_id in ids:
            try:
                await self.delete_media(db, media_id)
                count += 1
            except NotFoundError:
                continue
        return count

    # ------------------------------------------------------------------ 文件夹
    async def list_folders(
        self, db: AsyncSession, *, user_id: Optional[int] = None, is_public: Optional[bool] = None
    ) -> List[dict]:
        folders, _total = await media_folder_crud.list(
            db,
            page=1,
            page_size=0,
            filters={"user": user_id, "is_public": is_public},
            order_by="sort_order",
            order="asc",
        )
        return [_folder_out(folder) for folder in folders]

    async def folder_tree(
        self, db: AsyncSession, *, user_id: Optional[int] = None, is_public: Optional[bool] = None
    ) -> List[dict]:
        return build_folder_tree(await self.list_folders(db, user_id=user_id, is_public=is_public))

    async def create_folder(
        self, db: AsyncSession, payload: MediaFolderCreate, *, user_id: Optional[int] = None
    ) -> dict:
        if payload.parent_id is not None:
            parent = await media_folder_crud.get(db, payload.parent_id)
            if parent is None:
                raise NotFoundError("父文件夹不存在")

        data = payload.model_dump()
        data["user"] = user_id
        folder = await media_folder_crud.create(db, data)
        return _folder_out(folder)

    async def update_folder(
        self, db: AsyncSession, folder_id: int, payload: MediaFolderUpdate
    ) -> dict:
        folder = await media_folder_crud.get(db, folder_id)
        if folder is None:
            raise NotFoundError("文件夹不存在")

        data = payload.model_dump(exclude_unset=True)
        if data.get("parent_id") == folder_id:
            raise BadRequestError("父文件夹不能是自己")
        if data.get("parent_id") is not None:
            parent = await media_folder_crud.get(db, data["parent_id"])
            if parent is None:
                raise NotFoundError("父文件夹不存在")

        folder = await media_folder_crud.update(db, folder, data)
        return _folder_out(folder)

    async def delete_folder(self, db: AsyncSession, folder_id: int) -> None:
        folder = await media_folder_crud.get(db, folder_id)
        if folder is None:
            raise NotFoundError("文件夹不存在")

        child_count = await media_folder_crud.count(db, parent_id=folder_id)
        if child_count:
            raise ConflictError(f"存在 {child_count} 个子文件夹，请先处理")

        media_count = int(
            (
                await db.execute(
                    select(func.count()).select_from(Media).where(Media.folder_id == folder_id)
                )
            ).scalar()
            or 0
        )
        if media_count:
            raise ConflictError(f"文件夹内仍有 {media_count} 个媒体文件，请先移动或删除")

        await media_folder_crud.remove(db, folder)


media_service = MediaService()
