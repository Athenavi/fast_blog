"""mobile/media 的业务逻辑

设计要点：**前台媒体库只允许操作自己的数据**。

复用 ``modules/content/media`` 的 ``media_service``（校验、落盘、序列化都在那里），
但所有读取都带上 ``user_id=current.id``，所有写入先用 ``_mine_or_404`` 校验归属——
归属不符时返回 404 而不是 403，避免泄露"这条记录存在"的信息。
"""

from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.media.media import Media
from shared.models.media.media_folder import MediaFolder
from src.api.v3.core.exceptions import BadRequestError, NotFoundError
from src.api.v3.modules.content.media.crud import media_crud, media_folder_crud
from src.api.v3.modules.content.media.schema import MediaFolderUpdate, MediaUpdate
from src.api.v3.modules.content.media.service import media_service
from src.api.v3.modules.mobile.media.schema import (
    MobileFolderCreate,
    MobileMediaUpdate,
)


class MobileMediaService:
    """前台媒体库（全部以当前用户为界）"""

    # ------------------------------------------------------------ 读
    async def list_mine(
        self,
        db: AsyncSession,
        user,
        *,
        page: int = 1,
        page_size: int = 24,
        folder_id: Optional[int] = None,
        mime_type: Optional[str] = None,
        keyword: Optional[str] = None,
    ) -> tuple[list[dict], int]:
        return await media_service.list_media(
            db,
            page=page,
            page_size=page_size,
            keyword=keyword,
            folder_id=folder_id,
            mime_type=mime_type,
            user_id=user.id,
        )

    async def get_mine(self, db: AsyncSession, user, media_id: int) -> dict:
        await self._mine_or_404(db, user, media_id)
        return await media_service.get_media(db, media_id)

    async def folder_tree(self, db: AsyncSession, user) -> list[dict]:
        return await media_service.folder_tree(db, user_id=user.id)

    async def stats(self, db: AsyncSession, user) -> dict:
        total, size = (
            await db.execute(
                select(
                    func.count(Media.id),
                    func.coalesce(func.sum(Media.file_size), 0),
                ).where(Media.user == user.id)
            )
        ).one()

        rows = (
            await db.execute(
                select(Media.file_type, func.count(Media.id))
                .where(Media.user == user.id)
                .group_by(Media.file_type)
            )
        ).all()

        return {
            "total": int(total or 0),
            "total_size": int(size or 0),
            "by_type": {(row[0] or "other"): int(row[1]) for row in rows},
        }

    # ------------------------------------------------------------ 写
    async def create_folder(self, db: AsyncSession, user, payload: MobileFolderCreate) -> dict:
        if payload.parent_id is not None:
            # 父文件夹也必须属于自己
            parent = await media_folder_crud.get(db, payload.parent_id)
            if parent is None or parent.user != user.id:
                raise NotFoundError("父文件夹不存在")
        from src.api.v3.modules.content.media.schema import MediaFolderCreate

        created = await media_service.create_folder(
            db,
            MediaFolderCreate(
                name=payload.name,
                parent_id=payload.parent_id,
                description=payload.description,
                sort_order=payload.sort_order,
            ),
            user_id=user.id,
        )
        return created

    async def update_mine(
        self, db: AsyncSession, user, media_id: int, payload: MobileMediaUpdate
    ) -> dict:
        await self._mine_or_404(db, user, media_id)
        data = payload.model_dump(exclude_unset=True)
        if data.get("folder_id") is not None:
            folder = await media_folder_crud.get(db, data["folder_id"])
            if folder is None or folder.user != user.id:
                raise NotFoundError("目标文件夹不存在")
        return await media_service.update_media(db, media_id, MediaUpdate(**data))

    async def delete_mine(self, db: AsyncSession, user, media_id: int) -> None:
        await self._mine_or_404(db, user, media_id)
        await media_service.delete_media(db, media_id)

    async def batch_delete_mine(self, db: AsyncSession, user, ids: list[int]) -> dict:
        if not ids:
            raise BadRequestError("请提供要删除的媒体 ID")
        affected = 0
        for media_id in ids:
            try:
                await self._mine_or_404(db, user, media_id)
            except NotFoundError:
                continue
            await media_service.delete_media(db, media_id)
            affected += 1
        return {"affected": affected}

    async def rename_folder(self, db: AsyncSession, user, folder_id: int, payload: dict) -> dict:
        await self._mine_folder_or_404(db, user, folder_id)
        return await media_service.update_folder(db, folder_id, MediaFolderUpdate(**payload))

    async def delete_folder(self, db: AsyncSession, user, folder_id: int) -> None:
        await self._mine_folder_or_404(db, user, folder_id)
        await media_service.delete_folder(db, folder_id)

    # ------------------------------------------------------------ 归属校验
    async def _mine_or_404(self, db: AsyncSession, user, media_id: int) -> Media:
        media = await media_crud.get(db, media_id)
        # 归属不符同样返回 404，避免泄露记录是否存在
        if media is None or media.user != user.id:
            raise NotFoundError("媒体不存在")
        return media

    async def _mine_folder_or_404(self, db: AsyncSession, user, folder_id: int) -> MediaFolder:
        folder = await media_folder_crud.get(db, folder_id)
        if folder is None or folder.user != user.id:
            raise NotFoundError("文件夹不存在")
        return folder


mobile_media_service = MobileMediaService()
