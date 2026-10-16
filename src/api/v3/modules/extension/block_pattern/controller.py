"""block_pattern 模块路由（T5-11 批次 1：自 astro `admin/block-patterns` 能力域新建）

::

    GET    /api/v3/extension/block-pattern                  区块模板列表
    POST   /api/v3/extension/block-pattern                  新建区块模板
    PUT    /api/v3/extension/block-pattern/{pattern_id}     更新区块模板
    DELETE /api/v3/extension/block-pattern/{pattern_id}     删除区块模板

权限码：``module_extension:block_pattern:view/create/edit/delete``。
`blocks` 列存放编辑器 JSON；关键词逗号分隔供模板库搜索。
"""

from typing import Optional

from fastapi import APIRouter, Query

from src.api.v3.common import response as resp
from src.api.v3.common.response import ResponseModel
from src.api.v3.core.deps import AuthControl, CurrentUser, DBSession
from src.api.v3.core.permission import codes
from src.api.v3.core.router_class import OperationLogRoute
from src.api.v3.modules.extension.block_pattern.schema import (
    BlockPatternCreate,
    BlockPatternUpdate,
)
from src.api.v3.modules.extension.block_pattern.service import block_pattern_service

router = APIRouter(prefix="/block-pattern", tags=["extension-block-pattern"], route_class=OperationLogRoute)


@router.get("", response_model=ResponseModel, summary="区块模板列表")
async def list_patterns(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.BLOCK_PATTERN_VIEW),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    keyword: Optional[str] = Query(default=None),
    category: Optional[str] = Query(default=None),
) -> dict:
    items, total = await block_pattern_service.list_patterns(
        db, page=page, page_size=page_size, keyword=keyword, category=category
    )
    return resp.success_page(items, total, page, page_size)


@router.post("", response_model=ResponseModel, summary="新建区块模板")
async def create_pattern(
    payload: BlockPatternCreate,
    db: DBSession,
    current: CurrentUser,
    _perm=AuthControl(codes.BLOCK_PATTERN_CREATE),
) -> dict:
    return resp.success(
        await block_pattern_service.create_pattern(db, payload, user_id=current.id), msg="已创建"
    )


@router.put("/{pattern_id}", response_model=ResponseModel, summary="更新区块模板")
async def update_pattern(
    pattern_id: int,
    payload: BlockPatternUpdate,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.BLOCK_PATTERN_EDIT),
) -> dict:
    return resp.success(await block_pattern_service.update_pattern(db, pattern_id, payload), msg="已保存")


@router.delete("/{pattern_id}", response_model=ResponseModel, summary="删除区块模板")
async def delete_pattern(
    pattern_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.BLOCK_PATTERN_DELETE),
) -> dict:
    await block_pattern_service.delete_pattern(db, pattern_id)
    return resp.success(None, msg="已删除")
