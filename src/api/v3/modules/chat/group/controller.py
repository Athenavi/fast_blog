"""chat.group 模块路由（T5-11 批次 4：自 astro `admin/chat-groups` 能力域新建）

::

    GET    /api/v3/chat/group                                群聊列表
    POST   /api/v3/chat/group                                建群（creator 自动成为 owner）
    PUT    /api/v3/chat/group/{group_id}                     更新群信息
    DELETE /api/v3/chat/group/{group_id}                     解散群（级联删成员）
    GET    /api/v3/chat/group/{group_id}/member              成员列表
    POST   /api/v3/chat/group/{group_id}/member              添加成员（唯一，重复 409）
    PUT    /api/v3/chat/group/member/{member_id}             改角色 / 静音
    DELETE /api/v3/chat/group/member/{member_id}             移出成员（群主不可移出）

权限码：``module_chat:group:view/create/edit/delete`` 与 ``module_chat:group:manage_members``。
"""

from typing import Optional

from fastapi import APIRouter, Query

from src.api.v3.common import response as resp
from src.api.v3.common.response import ResponseModel
from src.api.v3.core.deps import AuthControl, CurrentUser, DBSession
from src.api.v3.core.permission import codes
from src.api.v3.core.router_class import OperationLogRoute
from src.api.v3.modules.chat.group.schema import (
    ChatGroupCreate,
    ChatGroupUpdate,
    GroupMemberAdd,
    GroupMemberUpdate,
)
from src.api.v3.modules.chat.group.service import chat_group_service

router = APIRouter(prefix="/group", tags=["chat-group"], route_class=OperationLogRoute)


@router.get("", response_model=ResponseModel, summary="群聊列表")
async def list_groups(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.CHAT_GROUP_VIEW),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    keyword: Optional[str] = Query(default=None),
    is_active: Optional[bool] = Query(default=None),
) -> dict:
    items, total = await chat_group_service.list_groups(
        db, page=page, page_size=page_size, keyword=keyword, is_active=is_active
    )
    return resp.success_page(items, total, page, page_size)


@router.post("", response_model=ResponseModel, summary="创建群聊")
async def create_group(
    payload: ChatGroupCreate,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.CHAT_GROUP_CREATE),
) -> dict:
    return resp.success(await chat_group_service.create_group(db, payload), msg="已创建")


@router.put("/{group_id}", response_model=ResponseModel, summary="更新群聊")
async def update_group(
    group_id: int,
    payload: ChatGroupUpdate,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.CHAT_GROUP_EDIT),
) -> dict:
    return resp.success(await chat_group_service.update_group(db, group_id, payload), msg="已保存")


@router.delete("/{group_id}", response_model=ResponseModel, summary="解散群聊")
async def delete_group(
    group_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.CHAT_GROUP_DELETE),
) -> dict:
    await chat_group_service.delete_group(db, group_id)
    return resp.success(None, msg="已解散")


@router.get("/{group_id}/member", response_model=ResponseModel, summary="成员列表")
async def list_members(
    group_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.CHAT_GROUP_VIEW),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    role: Optional[str] = Query(default=None),
) -> dict:
    items, total = await chat_group_service.list_members(
        db, group_id, page=page, page_size=page_size, role=role
    )
    return resp.success_page(items, total, page, page_size)


@router.post("/{group_id}/member", response_model=ResponseModel, summary="添加成员")
async def add_member(
    group_id: int,
    payload: GroupMemberAdd,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.CHAT_GROUP_MANAGE_MEMBERS),
) -> dict:
    return resp.success(
        await chat_group_service.add_member(db, group_id, payload.user_id, payload.role), msg="已加入"
    )


@router.put("/member/{member_id}", response_model=ResponseModel, summary="更新成员")
async def update_member(
    member_id: int,
    payload: GroupMemberUpdate,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.CHAT_GROUP_MANAGE_MEMBERS),
) -> dict:
    return resp.success(await chat_group_service.update_member(db, member_id, payload), msg="已保存")


@router.delete("/member/{member_id}", response_model=ResponseModel, summary="移出成员")
async def remove_member(
    member_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.CHAT_GROUP_MANAGE_MEMBERS),
) -> dict:
    await chat_group_service.remove_member(db, member_id)
    return resp.success(None, msg="已移出")
