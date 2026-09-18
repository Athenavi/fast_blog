"""category 模块业务逻辑

分类树在应用层按 ``parent_id`` 组装（与 menu 模块同一策略）。
删除分类前必须没有子分类与文章，避免产生孤儿数据。
"""

from typing import List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.article.article import Article
from shared.models.category.category import Category
from src.api.v3.core.exceptions import BadRequestError, ConflictError, NotFoundError
from src.api.v3.core.logger import get_logger
from src.api.v3.modules.content.category.crud import category_crud
from src.api.v3.modules.content.category.schema import CategoryCreate, CategoryUpdate

logger = get_logger("category")


def _out(category: Category) -> dict:
    return {
        "id": category.id,
        "name": category.name,
        "slug": category.slug,
        "description": category.description,
        "parent_id": category.parent_id,
        "sort_order": category.sort_order or 0,
        "icon": category.icon,
        "color": category.color,
        "is_visible": bool(category.is_visible),
        "articles_count": category.articles_count or 0,
        "created_at": category.created_at,
        "updated_at": category.updated_at,
        "children": [],
    }


def build_tree(categories: List[dict]) -> List[dict]:
    """按 ``parent_id`` 组装分类树"""
    by_id = {item["id"]: item for item in categories}
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


class CategoryService:
    """分类管理"""

    async def list_categories(
        self,
        db: AsyncSession,
        *,
        is_visible: Optional[bool] = None,
        keyword: Optional[str] = None,
    ) -> List[dict]:
        categories, _total = await category_crud.list(
            db,
            page=1,
            page_size=0,
            keyword=keyword,
            filters={"is_visible": is_visible},
            order_by="sort_order",
            order="asc",
        )
        return [_out(category) for category in categories]

    async def tree(self, db: AsyncSession, *, is_visible: Optional[bool] = None) -> List[dict]:
        return build_tree(await self.list_categories(db, is_visible=is_visible))

    async def get_category(self, db: AsyncSession, category_id: int) -> Category:
        category = await category_crud.get(db, category_id)
        if category is None:
            raise NotFoundError("分类不存在")
        return category

    async def create_category(self, db: AsyncSession, payload: CategoryCreate) -> dict:
        if payload.slug and await category_crud.exists(db, slug=payload.slug):
            raise ConflictError(f"分类标识 {payload.slug} 已存在")
        if payload.parent_id is not None:
            await self.get_category(db, payload.parent_id)
        category = await category_crud.create(db, payload.model_dump(exclude_unset=True))
        return _out(category)

    async def update_category(
        self, db: AsyncSession, category_id: int, payload: CategoryUpdate
    ) -> dict:
        category = await self.get_category(db, category_id)
        data = payload.model_dump(exclude_unset=True)

        if data.get("parent_id") == category_id:
            raise BadRequestError("父分类不能是自己")
        if "slug" in data and data["slug"]:
            existing = await category_crud.get_by(db, slug=data["slug"])
            if existing is not None and existing.id != category_id:
                raise ConflictError(f"分类标识 {data['slug']} 已存在")
        if data.get("parent_id") is not None:
            await self._assert_no_cycle(db, category_id, data["parent_id"])

        category = await category_crud.update(db, category, data)
        return _out(category)

    async def _assert_no_cycle(self, db: AsyncSession, category_id: int, parent_id: int) -> None:
        """防止把分类挂到自己的后代下形成环"""
        current = parent_id
        for _ in range(32):
            if current == category_id:
                raise BadRequestError("父分类不能是自身或其子分类")
            parent = await category_crud.get(db, current)
            if parent is None or parent.parent_id is None:
                return
            current = parent.parent_id
        raise BadRequestError("分类层级过深，疑似存在循环引用")

    async def delete_category(self, db: AsyncSession, category_id: int) -> None:
        await self.get_category(db, category_id)

        child_count = await category_crud.count(db, parent_id=category_id)
        if child_count:
            raise ConflictError(f"存在 {child_count} 个子分类，请先处理")

        article_count = int(
            (
                await db.execute(
                    select(func.count()).select_from(Article).where(Article.category == category_id)
                )
            ).scalar()
            or 0
        )
        if article_count:
            raise ConflictError(f"该分类下仍有 {article_count} 篇文章，请先移动或删除")

        await category_crud.remove(db, await self.get_category(db, category_id))


category_service = CategoryService()
