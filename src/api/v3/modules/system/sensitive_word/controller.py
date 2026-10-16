"""sensitive_word 模块路由（T5-11 样板：自 astro `admin/sensitive-words` 能力域平移）

::

    GET    /api/v3/system/sensitive-word               敏感词列表
    POST   /api/v3/system/sensitive-word               添加敏感词
    PUT    /api/v3/system/sensitive-word/{word_id}     更新敏感词
    DELETE /api/v3/system/sensitive-word/{word_id}     删除敏感词
    POST   /api/v3/system/sensitive-word/batch/import  批量导入

权限码：``module_system:sensitive_word:view/create/edit/delete``。
写操作经共享服务落库并刷新其内存缓存，评论/投稿的反垃圾立即生效。
"""

from typing import Optional

from fastapi import APIRouter, Query

from src.api.v3.common import response as resp
from src.api.v3.common.response import ResponseModel
from src.api.v3.core.deps import AuthControl, CurrentUser, DBSession
from src.api.v3.core.permission import codes
from src.api.v3.core.router_class import OperationLogRoute
from src.api.v3.modules.system.sensitive_word.schema import (
    SensitiveWordBatchImport,
    SensitiveWordCreate,
    SensitiveWordUpdate,
)
from src.api.v3.modules.system.sensitive_word.service import sensitive_word_module_service

router = APIRouter(prefix="/sensitive-word", tags=["system-sensitive-word"], route_class=OperationLogRoute)


@router.get("", response_model=ResponseModel, summary="敏感词列表")
async def list_words(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.SENSITIVE_WORD_VIEW),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    keyword: Optional[str] = Query(default=None),
    level: Optional[int] = Query(default=None, ge=1, le=3),
    category: Optional[str] = Query(default=None),
    is_active: Optional[bool] = Query(default=None),
) -> dict:
    items, total = await sensitive_word_module_service.list_words(
        db,
        page=page,
        page_size=page_size,
        keyword=keyword,
        level=level,
        category=category,
        is_active=is_active,
    )
    return resp.success_page(items, total, page, page_size)


@router.post("", response_model=ResponseModel, summary="添加敏感词")
async def create_word(
    payload: SensitiveWordCreate,
    _current: CurrentUser,
    _perm=AuthControl(codes.SENSITIVE_WORD_CREATE),
) -> dict:
    return resp.success(
        await sensitive_word_module_service.create_word(payload, user_id=_current.id),
        msg="已添加",
    )


@router.post("/batch/import", response_model=ResponseModel, summary="批量导入敏感词")
async def batch_import(
    payload: SensitiveWordBatchImport,
    _current: CurrentUser,
    _perm=AuthControl(codes.SENSITIVE_WORD_CREATE),
) -> dict:
    return resp.success(
        await sensitive_word_module_service.batch_import(payload, user_id=_current.id),
        msg="导入完成",
    )


@router.put("/{word_id}", response_model=ResponseModel, summary="更新敏感词")
async def update_word(
    word_id: int,
    payload: SensitiveWordUpdate,
    _current: CurrentUser,
    _perm=AuthControl(codes.SENSITIVE_WORD_EDIT),
) -> dict:
    return resp.success(
        await sensitive_word_module_service.update_word(word_id, payload), msg="已保存"
    )


@router.delete("/{word_id}", response_model=ResponseModel, summary="删除敏感词")
async def delete_word(
    word_id: int,
    _current: CurrentUser,
    _perm=AuthControl(codes.SENSITIVE_WORD_DELETE),
) -> dict:
    await sensitive_word_module_service.delete_word(word_id)
    return resp.success(None, msg="已删除")
