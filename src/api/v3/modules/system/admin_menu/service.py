"""admin_menu 模块业务逻辑

核心能力：**菜单授权下发** —— ``menu_codes_of_user`` 是登录时"该用户能看到哪些菜单"的唯一来源。

与权限码加载保持一致的两点：

  - 角色**沿 parent_id 递归**（继承父角色的菜单授权）
  - 只统计 ``is_active`` 的菜单；超级管理员取全部激活菜单
"""

from typing import Any, Dict, List, Optional, Sequence

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.rbac.admin_menu import AdminMenu
from shared.models.rbac.role_admin_menu import RoleAdminMenu
from src.api.v3.core.exceptions import BadRequestError, ConflictError, NotFoundError
from src.api.v3.core.logger import get_logger
from src.api.v3.modules.system.admin_menu.crud import admin_menu_crud

logger = get_logger("admin_menu")

#: 用户可见菜单：角色树（含继承的父角色）→ 角色-菜单授权 → 菜单
_USER_MENU_CODES_SQL = """
                       WITH RECURSIVE role_tree AS (SELECT r.id, r.parent_id
                                                    FROM roles r
                                                             JOIN user_role_assignments ur ON ur.role_id = r.id
                                                    WHERE ur.user_id = :user_id
                                                      AND r.is_active IS TRUE
                                                    UNION
                                                    SELECT parent.id, parent.parent_id
                                                    FROM roles parent
                                                             JOIN role_tree child ON parent.id = child.parent_id
                                                    WHERE parent.is_active IS TRUE)
                       SELECT DISTINCT m.code
                       FROM admin_menus m
                                JOIN role_admin_menus ram ON ram.admin_menu_id = m.id
                       WHERE ram.role_id IN (SELECT id FROM role_tree)
                         AND m.is_active IS TRUE \
                       """


def _menu_out(menu: AdminMenu) -> dict:
    return {
        "id": menu.id,
        "code": menu.code,
        "title": menu.title,
        "parent_id": menu.parent_id,
        "menu_type": int(menu.menu_type or 2),
        "permission_code": menu.permission_code,
        "sort_order": menu.sort_order or 0,
        "is_active": bool(menu.is_active),
        "created_at": menu.created_at,
        "updated_at": menu.updated_at,
        "children": [],
    }


def build_tree(menus: Sequence[dict]) -> List[dict]:
    by_id = {item["id"]: item for item in menus}
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


class AdminMenuService:
    """后台菜单定义与角色授权"""

    # ------------------------------------------------------------------ 菜单定义
    async def list_menus(
        self,
        db: AsyncSession,
        *,
        is_active: Optional[bool] = None,
        keyword: Optional[str] = None,
    ) -> List[dict]:
        menus, _total = await admin_menu_crud.list(
            db,
            page=1,
            page_size=0,
            keyword=keyword,
            filters={"is_active": is_active},
            order_by="sort_order",
            order="asc",
        )
        return [_menu_out(menu) for menu in menus]

    async def tree(self, db: AsyncSession, *, is_active: Optional[bool] = None) -> List[dict]:
        return build_tree(await self.list_menus(db, is_active=is_active))

    async def get_menu(self, db: AsyncSession, menu_id: int) -> AdminMenu:
        menu = await admin_menu_crud.get(db, menu_id)
        if menu is None:
            raise NotFoundError("菜单不存在")
        return menu

    async def get_menu_out(self, db: AsyncSession, menu_id: int) -> dict:
        return _menu_out(await self.get_menu(db, menu_id))

    async def create_menu(self, db: AsyncSession, payload: Any) -> dict:
        data = payload.model_dump(exclude_unset=True)
        if await admin_menu_crud.exists(db, code=data.get("code")):
            raise ConflictError(f"菜单标识 {data.get('code')} 已存在")
        if data.get("parent_id") is not None:
            await self.get_menu(db, data["parent_id"])

        menu = await admin_menu_crud.create(db, data)
        return _menu_out(menu)

    async def update_menu(self, db: AsyncSession, menu_id: int, payload: Any) -> dict:
        menu = await self.get_menu(db, menu_id)
        data = payload.model_dump(exclude_unset=True)

        if data.get("parent_id") == menu_id:
            raise BadRequestError("父菜单不能是自己")
        if data.get("code"):
            existing = await admin_menu_crud.get_by(db, code=data["code"])
            if existing is not None and existing.id != menu_id:
                raise ConflictError(f"菜单标识 {data['code']} 已存在")
        if data.get("parent_id") is not None:
            await self._assert_no_cycle(db, menu_id, data["parent_id"])

        menu = await admin_menu_crud.update(db, menu, data)
        return _menu_out(menu)

    async def _assert_no_cycle(self, db: AsyncSession, menu_id: int, parent_id: int) -> None:
        current = parent_id
        for _ in range(64):
            if current == menu_id:
                raise BadRequestError("父菜单不能是自身或其子菜单")
            parent = await admin_menu_crud.get(db, current)
            if parent is None or parent.parent_id is None:
                return
            current = parent.parent_id
        raise BadRequestError("菜单层级过深，疑似存在循环引用")

    async def delete_menu(self, db: AsyncSession, menu_id: int) -> None:
        menu = await self.get_menu(db, menu_id)

        child_count = await admin_menu_crud.count(db, parent_id=menu_id)
        if child_count:
            raise ConflictError(f"存在 {child_count} 个子菜单，请先处理")

        # 授权记录可安全清理
        await db.execute(RoleAdminMenu.__table__.delete().where(RoleAdminMenu.admin_menu_id == menu_id))
        await db.commit()
        await admin_menu_crud.remove(db, menu)

    # ------------------------------------------------------------------ 角色授权
    async def menu_ids_of_role(self, db: AsyncSession, role_id: int) -> List[int]:
        rows = await db.execute(
            select(RoleAdminMenu.admin_menu_id).where(RoleAdminMenu.role_id == role_id)
        )
        return sorted(int(mid) for mid in rows.scalars().all() if mid is not None)

    async def set_role_menus(
        self, db: AsyncSession, role_id: int, menu_ids: Sequence[int]
    ) -> List[int]:
        """全量覆盖某角色的菜单授权（差量增删）"""
        from shared.models.rbac.role import Role

        if (await db.execute(select(Role.id).where(Role.id == role_id))).scalar() is None:
            raise NotFoundError("角色不存在")

        target = {int(mid) for mid in menu_ids}
        if target:
            found = (
                (await db.execute(select(AdminMenu.id).where(AdminMenu.id.in_(sorted(target)))))
                .scalars()
                .all()
            )
            missing = target - {int(mid) for mid in found}
            if missing:
                raise BadRequestError(f"菜单不存在: {', '.join(str(m) for m in sorted(missing))}")

        current = set(await self.menu_ids_of_role(db, role_id))
        for menu_id in target - current:
            db.add(RoleAdminMenu(role_id=role_id, admin_menu_id=menu_id))
        for menu_id in current - target:
            await db.execute(
                RoleAdminMenu.__table__.delete().where(
                    RoleAdminMenu.role_id == role_id,
                    RoleAdminMenu.admin_menu_id == menu_id,
                )
            )
        await db.commit()
        return await self.menu_ids_of_role(db, role_id)

    # ------------------------------------------------------------------ 下发
    async def menu_codes_of_user(
        self, db: AsyncSession, user_id: int, *, is_superuser: bool = False
    ) -> List[str]:
        """用户可见的菜单标识集合（登录时下发给前端）"""
        if is_superuser:
            rows = await db.execute(
                select(AdminMenu.code).where(AdminMenu.is_active.is_(True))
            )
            return sorted({code for code in rows.scalars().all() if code})

        rows = await db.execute(text(_USER_MENU_CODES_SQL), {"user_id": user_id})
        return sorted({code for code in rows.scalars().all() if code})

    async def menu_codes_with_ancestors(
        self, db: AsyncSession, user_id: int, *, is_superuser: bool = False
    ) -> List[str]:
        """在可见菜单基础上**补齐祖先目录**

        只授权了子菜单而未授权其父目录时，前端按 code 过滤会把子菜单一起隐藏——
        这里主动补齐祖先，避免"授权了却看不见"。
        """
        codes = set(await self.menu_codes_of_user(db, user_id, is_superuser=is_superuser))
        if not codes:
            return []

        menu_rows = await admin_menu_crud.list(
            db, page=1, page_size=0, filters={"is_active": True}
        )
        menus = menu_rows[0]
        by_id: Dict[int, AdminMenu] = {menu.id: menu for menu in menus}
        by_code = {menu.code: menu for menu in menus if menu.code}

        code_cache: Dict[int, Optional[str]] = {}

        def code_of(menu_id: int) -> Optional[str]:
            if menu_id not in code_cache:
                menu = by_id.get(menu_id)
                code_cache[menu_id] = menu.code if menu is not None else None
            return code_cache[menu_id]

        def ancestors(menu_id: int, seen: set[int]) -> None:
            menu = by_id.get(menu_id)
            if menu is None or menu.parent_id is None or menu.parent_id in seen:
                return
            seen.add(menu.parent_id)
            code = code_of(menu.parent_id)
            if code:
                codes.add(code)
            ancestors(menu.parent_id, seen)

        for code in list(codes):
            menu = by_code.get(code)
            if menu is not None:
                ancestors(menu.id, set())

        return sorted(codes)


admin_menu_service = AdminMenuService()
