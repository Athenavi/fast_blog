"""mobile/category：移动端分类列表

路由前缀：``/api/v3/mobile/category``

复用 ``modules/content/category`` 的 ``category_service``（可见性规则一致：只返回
``is_visible=True``）。无需鉴权。
"""

from fastapi import APIRouter

from src.api.v3.common import response as resp
from src.api.v3.common.response import ResponseModel
from src.api.v3.core.deps import DBSession
from src.api.v3.modules.content.category.service import category_service

router = APIRouter(prefix="/category", tags=["mobile-category"])


@router.get("/list", response_model=ResponseModel, summary="分类列表（无需鉴权）")
async def list_categories(db: DBSession) -> dict:
    items = await category_service.list_categories(db, is_visible=True)
    return resp.success_page(items, len(items), 1, len(items) or 1)


@router.get("/tree", response_model=ResponseModel, summary="分类树（无需鉴权）")
async def category_tree(db: DBSession) -> dict:
    return resp.success(await category_service.tree(db, is_visible=True))
