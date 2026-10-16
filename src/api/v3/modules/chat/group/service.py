"""chat.group 模块业务逻辑：群聊会话与成员管理

- 成员表列名是 ``group``/``user``（代码生成器产物）；
- 建群时自动把 creator 写成 owner 成员并同步 member_count；
- 成员唯一（group+user）重复添加返回 409；
- 增删成员后同步群主表 member_count；解散群时级联删除成员关系。
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import delete as sa_delete
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.chat import ChatMessage
from src.api.v3.core.exceptions import ConflictError, NotFoundError
from src.api.v3.modules.chat.group.crud import chat_group_crud, chat_group_member_crud
from src.api.v3.modules.chat.group.schema import (
    ChatGroupCreate,
    ChatGroupOut,
    ChatGroupUpdate,
    GroupMemberOut,
    GroupMemberUpdate,
)

VALID_MEMBER_ROLES = {"owner", "admin", "member"}


def _group_out(row) -> dict:
    return ChatGroupOut.model_validate(row, from_attributes=True).model_dump(mode="json")


def _member_out(row) -> dict:
    return GroupMemberOut.model_validate(row, from_attributes=True).model_dump(mode="json")


class ChatGroupService:
    """群聊管理（chat 域）"""

    # ------------------------------------------------------------ 群
    async def list_groups(
        self, db: AsyncSession, *, page: int = 1, page_size: int = 20,
        keyword: Optional[str] = None, is_active: Optional[bool] = None,
    ) -> tuple[list[dict], int]:
        rows, total = await chat_group_crud.list(
            db, page=page, page_size=page_size, keyword=keyword, filters={"is_active": is_active}
        )
        return [_group_out(r) for r in rows], total

    async def create_group(self, db: AsyncSession, payload: ChatGroupCreate) -> dict:
        row = await chat_group_crud.create(
            db,
            payload.model_dump() | {"member_count": 1, "created_at": datetime.now(), "updated_at": datetime.now()},
        )
        await chat_group_member_crud.create(
            db,
            {"group": row.id, "user": payload.creator, "role": "owner", "joined_at": datetime.now()},
        )
        return _group_out(row)

    async def update_group(self, db: AsyncSession, group_id: int, payload: ChatGroupUpdate) -> dict:
        row = await chat_group_crud.get(db, group_id)
        if row is None:
            raise NotFoundError("群聊不存在")
        updated = await chat_group_crud.update(
            db, row, payload.model_dump(exclude_unset=True) | {"updated_at": datetime.now()}
        )
        return _group_out(updated)

    async def delete_group(self, db: AsyncSession, group_id: int) -> None:
        row = await chat_group_crud.get(db, group_id)
        if row is None:
            raise NotFoundError("群聊不存在")
        # 群消息是批次 17 新增的关联表：显式清空，避免外键挡住群删除
        # （迁移里也声明了 ON DELETE CASCADE，这里是语义上更明确的一层）
        await db.execute(sa_delete(ChatMessage).where(ChatMessage.group == group_id))
        await db.commit()
        members, _total = await chat_group_member_crud.list(db, page=1, page_size=0, filters={"group": group_id})
        for member in members:
            await chat_group_member_crud.remove(db, member)
        await chat_group_crud.remove(db, row)

    # ------------------------------------------------------------ 成员
    async def list_members(
        self, db: AsyncSession, group_id: int, *, page: int = 1, page_size: int = 50,
        role: Optional[str] = None,
    ) -> tuple[list[dict], int]:
        if await chat_group_crud.get(db, group_id) is None:
            raise NotFoundError("群聊不存在")
        rows, total = await chat_group_member_crud.list(
            db, page=page, page_size=page_size, filters={"group": group_id, "role": role}
        )
        return [_member_out(r) for r in rows], total

    async def add_member(self, db: AsyncSession, group_id: int, user_id: int, role: str) -> dict:
        if await chat_group_crud.get(db, group_id) is None:
            raise NotFoundError("群聊不存在")
        if role not in VALID_MEMBER_ROLES:
            raise ConflictError(f"非法成员角色: {role}（可选 {sorted(VALID_MEMBER_ROLES)}）")
        if await chat_group_member_crud.exists(db, group=group_id, user=user_id):
            raise ConflictError(f"用户已是群成员: {user_id}")
        row = await chat_group_member_crud.create(
            db, {"group": group_id, "user": user_id, "role": role, "joined_at": datetime.now()}
        )
        await self._sync_member_count(db, group_id)
        return _member_out(row)

    async def update_member(self, db: AsyncSession, member_id: int, payload: GroupMemberUpdate) -> dict:
        row = await chat_group_member_crud.get(db, member_id)
        if row is None:
            raise NotFoundError("成员记录不存在")
        data = payload.model_dump(exclude_unset=True)
        if "role" in data and data["role"] is not None and data["role"] not in VALID_MEMBER_ROLES:
            raise ConflictError(f"非法成员角色: {data['role']}（可选 {sorted(VALID_MEMBER_ROLES)}）")
        updated = await chat_group_member_crud.update(db, row, data)
        return _member_out(updated)

    async def remove_member(self, db: AsyncSession, member_id: int) -> None:
        row = await chat_group_member_crud.get(db, member_id)
        if row is None:
            raise NotFoundError("成员记录不存在")
        if row.role == "owner":
            raise ConflictError("群主不能被移出，请先转让或解散群聊")
        await chat_group_member_crud.remove(db, row)
        await self._sync_member_count(db, row.group)

    @staticmethod
    async def _sync_member_count(db: AsyncSession, group_id: int) -> None:
        count = await chat_group_member_crud.count(db, group=group_id)
        group = await chat_group_crud.get(db, group_id)
        if group is not None:
            await chat_group_crud.update(db, group, {"member_count": count, "updated_at": datetime.now()})


chat_group_service = ChatGroupService()
