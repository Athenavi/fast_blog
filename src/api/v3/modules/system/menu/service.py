"""menu 模块业务逻辑

直接操作 ``menus`` / ``menu_items``；树结构在应用层组装（``parent_id`` 无外键约束）。
"""

from typing import List, Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.menu.menu_items import MenuItems
from src.api.v3.core.exceptions import ConflictError, NotFoundError
from src.api.v3.core.logger import get_logger
from src.api.v3.modules.system.menu.crud import menu_crud, menu_item_crud
from src.api.v3.modules.system.menu.schema import (
    MenuCreate,
    MenuItemCreate,
    MenuItemUpdate,
    MenuUpdate,
)

logger = get_logger("menu")


def _item_out(item: MenuItems) -> dict:
    return {
        "id": item.id,
        "menu_id": item.menu_id,
        "parent_id": item.parent_id,
        "title": item.title,
        "url": item.url,
        "target": item.target,
        "order_index": item.order_index or 0,
        "is_active": bool(item.is_active),
        "created_at": item.created_at,
        "children": [],
    }


def build_tree(items: Sequence[dict]) -> List[dict]:
    """把平铺菜单项按 ``parent_id`` 组装成树（按 order_index 排序）"""
    by_id = {item["id"]: {**item, "children": []} for item in items}
    roots: List[dict] = []
    for item in by_id.values():
        parent_id = item.get("parent_id")
        parent = by_id.get(parent_id) if parent_id else None
        if parent is not None and parent["id"] != item["id"]:
            parent["children"].append(item)
        else:
            roots.append(item)

    def _sort(nodes: List[dict]) -> List[dict]:
        nodes.sort(key=lambda node: (node.get("order_index") or 0, node["id"]))
        for node in nodes:
            _sort(node["children"])
        return nodes

    return _sort(roots)


class MenuService:
    """菜单管理"""

    async def _items_of(self, db: AsyncSession, menu_id: int) -> List[MenuItems]:
        stmt = (
            select(MenuItems)
            .where(MenuItems.menu_id == menu_id)
            .order_by(MenuItems.order_index.asc(), MenuItems.id.asc())
        )
        return list((await db.execute(stmt)).scalars().all())

    async def list_menus(
        self,
        db: AsyncSession,
        *,
        is_active: Optional[bool] = None,
        with_items: bool = True,
    ) -> List[dict]:
        menus, _total = await menu_crud.list(
            db,
            page=1,
            page_size=0,
            filters={"is_active": is_active},
            order_by="id",
            order="asc",
        )
        result = []
        for menu in menus:
            payload = {
                "id": menu.id,
                "name": menu.name,
                "slug": menu.slug,
                "description": menu.description,
                "is_active": bool(menu.is_active),
                "created_at": menu.created_at,
                "updated_at": menu.updated_at,
                "items": [],
            }
            if with_items:
                items = [_item_out(item) for item in await self._items_of(db, menu.id)]
                payload["items"] = build_tree(items)
            result.append(payload)
        return result

    async def get_menu(self, db: AsyncSession, menu_id: int) -> dict:
        menu = await menu_crud.get(db, menu_id)
        if menu is None:
            raise NotFoundError("菜单不存在")
        items = [_item_out(item) for item in await self._items_of(db, menu.id)]
        return {
            "id": menu.id,
            "name": menu.name,
            "slug": menu.slug,
            "description": menu.description,
            "is_active": bool(menu.is_active),
            "created_at": menu.created_at,
            "updated_at": menu.updated_at,
            "items": build_tree(items),
        }

    async def create_menu(self, db: AsyncSession, payload: MenuCreate) -> dict:
        if await menu_crud.exists(db, slug=payload.slug):
            raise ConflictError(f"菜单标识 {payload.slug} 已存在")
        menu = await menu_crud.create(
            db,
            {"name": payload.name, "slug": payload.slug, "description": payload.description, "is_active": True},
        )
        return await self.get_menu(db, menu.id)

    async def update_menu(self, db: AsyncSession, menu_id: int, payload: MenuUpdate) -> dict:
        menu = await menu_crud.get(db, menu_id)
        if menu is None:
            raise NotFoundError("菜单不存在")
        await menu_crud.update(db, menu, payload.model_dump(exclude_unset=True))
        return await self.get_menu(db, menu_id)

    async def delete_menu(self, db: AsyncSession, menu_id: int) -> None:
        menu = await menu_crud.get(db, menu_id)
        if menu is None:
            raise NotFoundError("菜单不存在")
        # 先删子项（parent_id 无外键约束，不会级联）
        for item in await self._items_of(db, menu_id):
            await db.delete(item)
        await db.commit()
        await menu_crud.remove(db, menu)

    async def add_item(self, db: AsyncSession, menu_id: int, payload: MenuItemCreate) -> dict:
        if await menu_crud.get(db, menu_id) is None:
            raise NotFoundError("菜单不存在")
        item = await menu_item_crud.create(
            db,
            {
                "menu_id": menu_id,
                "title": payload.title,
                "url": payload.url,
                "parent_id": payload.parent_id,
                "target": payload.target,
                "order_index": payload.order_index,
                "is_active": payload.is_active,
            },
        )
        return _item_out(item)

    async def update_item(self, db: AsyncSession, item_id: int, payload: MenuItemUpdate) -> dict:
        item = await menu_item_crud.get(db, item_id)
        if item is None:
            raise NotFoundError("菜单项不存在")
        item = await menu_item_crud.update(db, item, payload.model_dump(exclude_unset=True))
        return _item_out(item)

    async def delete_item(self, db: AsyncSession, item_id: int) -> None:
        item = await menu_item_crud.get(db, item_id)
        if item is None:
            raise NotFoundError("菜单项不存在")
        # 子项上提一层，避免出现孤儿节点
        children = await db.execute(select(MenuItems).where(MenuItems.parent_id == item.id))
        for child in children.scalars().all():
            child.parent_id = item.parent_id
            db.add(child)
        await db.commit()
        await menu_item_crud.remove(db, item)

    async def reorder_items(self, db: AsyncSession, menu_id: int, order: Sequence[tuple[int, int]]) -> List[dict]:
        items = {item.id: item for item in await self._items_of(db, menu_id)}
        for item_id, order_index in order:
            item = items.get(item_id)
            if item is None:
                continue
            item.order_index = order_index
            db.add(item)
        await db.commit()
        return [_item_out(item) for item in await self._items_of(db, menu_id)]

    async def tree(self, db: AsyncSession, menu_id: Optional[int] = None) -> List[dict]:
        """菜单项树（供前端动态路由使用）"""
        if menu_id is not None:
            return (await self.get_menu(db, menu_id))["items"]

        menus = await self.list_menus(db, with_items=True)
        return [
            {"id": menu["id"], "name": menu["name"], "slug": menu["slug"], "items": menu["items"]}
            for menu in menus
        ]


menu_service = MenuService()
