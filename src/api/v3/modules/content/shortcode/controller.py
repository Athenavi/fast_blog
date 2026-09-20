"""shortcode 模块路由（批次 5：admin/shortcodes 短代码库）

::

    GET    /api/v3/content/shortcode                 短代码列表（分页 + keyword + is_active 过滤）
    POST   /api/v3/content/shortcode                 新建短代码
    PUT    /api/v3/content/shortcode/{shortcode_id}  更新短代码
    DELETE /api/v3/content/shortcode/{shortcode_id}  删除短代码

权限码：``module_content:shortcode:view/create/edit/delete``。
code 唯一；创建后锁定（更新接口不接受 code）。
"""

from typing import Optional

from fastapi import APIRouter, Query

from src.api.v3.common import response as resp
from src.api.v3.common.response import ResponseModel
from src.api.v3.core.deps import AuthControl, CurrentUser, DBSession
from src.api.v3.core.permission import codes
from src.api.v3.core.router_class import OperationLogRoute
from src.api.v3.modules.content.shortcode.schema import (
    ShortcodeCreate,
    ShortcodeUpdate,
)
from src.api.v3.modules.content.shortcode.service import shortcode_service

router = APIRouter(
    prefix="/shortcode", tags=["content-shortcode"], route_class=OperationLogRoute
)


@router.get("", response_model=ResponseModel, summary="短代码列表")
async def list_shortcodes(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.SHORTCODE_VIEW),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    keyword: Optional[str] = Query(default=None),
    is_active: Optional[bool] = Query(default=None),
) -> dict:
    items, total = await shortcode_service.list_shortcodes(
        db, page=page, page_size=page_size, keyword=keyword, is_active=is_active
    )
    return resp.success_page(items, total, page, page_size)


@router.post("", response_model=ResponseModel, summary="新建短代码")
async def create_shortcode(
    payload: ShortcodeCreate,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.SHORTCODE_CREATE),
) -> dict:
    return resp.success(await shortcode_service.create_shortcode(db, payload), msg="已创建")


@router.put("/{shortcode_id}", response_model=ResponseModel, summary="更新短代码")
async def update_shortcode(
    shortcode_id: int,
    payload: ShortcodeUpdate,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.SHORTCODE_EDIT),
) -> dict:
    return resp.success(await shortcode_service.update_shortcode(db, shortcode_id, payload), msg="已保存")


@router.delete("/{shortcode_id}", response_model=ResponseModel, summary="删除短代码")
async def delete_shortcode(
    shortcode_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.SHORTCODE_DELETE),
) -> dict:
    await shortcode_service.delete_shortcode(db, shortcode_id)
    return resp.success(None, msg="已删除")
