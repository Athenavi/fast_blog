#!/usr/bin/env python3
"""
RBAC 种子数据脚本

初始化系统所需的 Capabilities 和 Roles，确保：
1. 从 models.yaml 定义的 PERMISSIONS 列表同步到 capabilities 表
2. 创建 4 个系统角色并分配对应权限
3. 幂等（可重复运行，不重复插入）

用法:  python -m scripts.seed_rbac
"""
import asyncio
from datetime import datetime

from sqlalchemy import select

from shared.models.rbac import Capability, Role, RoleCapability
from src.api.v3.core.permission import codes as C
from src.api.v3.core.permission.codes import CODE_LABELS
from src.utils.database.main import get_async_session_context


# ============================================================
# 预定义权限列表（与已删除的 permission_system.py 一致）
# ============================================================
# ============================================================
# 权限清单：**唯一真相在 src/api/v3/core/permission/codes.py**
# 这里只做 (code, label) → (code, name, resource_type, action) 的展开
# ============================================================


def _build_capability_list():
    """把 CODE_LABELS 展开为 (code, name, resource_type, action) 列表

    ``resource_type`` / ``action`` 由三段码自身解析：``module_{域}:{模块}:{动作}``。
    """
    result = []
    for code, label in CODE_LABELS.items():
        parts = code.split(":")
        if len(parts) != 3:
            raise ValueError(f"权限码必须是三段式 module_{{域}}:{{模块}}:{{动作}}，收到：{code}")
        _domain, module, action = parts
        result.append((code, label, module, action))
    return result


ALL_CAPABILITIES = _build_capability_list()


def _cap_codes(*codes: str) -> list[str]:
    """角色能力清单（直接写三段码常量，见 codes.py）"""
    return list(codes)


# ============================================================
# 角色定义
# ============================================================
ROLE_DEFS = [
    {
        "slug": "superadmin",
        "name": "超级管理员",
        "description": "拥有系统所有权限",
        "capability_codes": list(CODE_LABELS),
    },
    {
        "slug": "admin",
        "name": "管理员",
        "description": "管理类权限，不含敏感系统设置（不可编辑系统设置、不可恢复/删除备份）",
        "capability_codes": _cap_codes(
            # 内容：全套
            C.ARTICLE_VIEW, C.ARTICLE_CREATE, C.ARTICLE_EDIT, C.ARTICLE_DELETE,
            C.ARTICLE_PUBLISH, C.ARTICLE_EDIT_OTHERS, C.ARTICLE_DELETE_OTHERS,
            C.CATEGORY_VIEW, C.CATEGORY_CREATE, C.CATEGORY_EDIT, C.CATEGORY_DELETE,
            C.TAG_VIEW, C.TAG_EDIT,
            C.PAGE_VIEW, C.PAGE_CREATE, C.PAGE_EDIT, C.PAGE_DELETE, C.PAGE_PUBLISH,
            C.COMMENT_VIEW, C.COMMENT_APPROVE, C.COMMENT_EDIT, C.COMMENT_DELETE,
            C.MEDIA_VIEW, C.MEDIA_UPLOAD, C.MEDIA_DELETE,
            # 系统：管理类
            C.USER_VIEW, C.USER_CREATE, C.USER_EDIT, C.USER_DELETE, C.USER_MANAGE_ROLES,
            C.ROLE_VIEW, C.ROLE_EDIT,
            C.NAVMENU_VIEW, C.NAVMENU_CREATE, C.NAVMENU_EDIT, C.NAVMENU_DELETE,
            C.MENU_VIEW, C.MENU_CREATE, C.MENU_EDIT, C.MENU_DELETE, C.MENU_GRANT,
            C.GROUP_VIEW, C.GROUP_CREATE, C.GROUP_EDIT, C.GROUP_DELETE,
            C.GROUP_MANAGE_MEMBERS, C.GROUP_MANAGE_ROLES,
            C.PERMISSION_VIEW,
            C.SETTING_VIEW,  # 只能看，不能改
            C.LOG_VIEW,
            C.DASHBOARD_VIEW,
            # 数据与 SEO
            C.SEO_VIEW, C.SEO_EDIT, C.SEARCH_VIEW,
            # 扩展
            C.PLUGIN_VIEW, C.PLUGIN_INSTALL, C.PLUGIN_ACTIVATE, C.PLUGIN_DELETE,
            C.PLUGIN_CONFIGURE,
            C.THEME_VIEW, C.THEME_INSTALL, C.THEME_ACTIVATE, C.THEME_DELETE,
            C.THEME_CUSTOMIZE,
            C.WIDGET_VIEW, C.WIDGET_EDIT,
            # 运维：可建备份，不可恢复/删除
            C.BACKUP_VIEW, C.BACKUP_CREATE,
            C.WEBHOOK_VIEW, C.WEBHOOK_EDIT,
            C.NOTIFICATION_VIEW, C.NOTIFICATION_EDIT,
        ),
    },
    {
        "slug": "editor",
        "name": "编辑者",
        "description": "内容管理权限",
        "capability_codes": _cap_codes(
            C.ARTICLE_VIEW, C.ARTICLE_CREATE, C.ARTICLE_EDIT, C.ARTICLE_DELETE,
            C.ARTICLE_PUBLISH,
            C.CATEGORY_VIEW, C.CATEGORY_CREATE, C.CATEGORY_EDIT,
            C.TAG_VIEW, C.TAG_EDIT,
            C.PAGE_VIEW, C.PAGE_CREATE, C.PAGE_EDIT, C.PAGE_DELETE, C.PAGE_PUBLISH,
            C.COMMENT_VIEW, C.COMMENT_APPROVE, C.COMMENT_EDIT, C.COMMENT_DELETE,
            C.MEDIA_VIEW, C.MEDIA_UPLOAD, C.MEDIA_DELETE,
            C.NAVMENU_VIEW,
            C.DASHBOARD_VIEW,
        ),
    },
    {
        "slug": "user",
        "name": "普通用户",
        "description": "基础浏览和互动权限",
        "capability_codes": _cap_codes(
            C.ARTICLE_VIEW,
            C.CATEGORY_VIEW,
            C.TAG_VIEW,
            C.PAGE_VIEW,
            C.MEDIA_VIEW, C.MEDIA_UPLOAD,
            C.COMMENT_VIEW, C.COMMENT_EDIT,
            C.DASHBOARD_VIEW,
        ),
    },
]


async def seed_capabilities(db) -> dict:
    """同步 capabilities 表，返回 {code: Capability} 映射"""
    result = await db.execute(select(Capability))
    existing = {c.code: c for c in result.scalars().all()}

    now = datetime.now()
    code_map = {}

    for code, name, resource, action in ALL_CAPABILITIES:
        if code in existing:
            cap = existing[code]
            # 更新名称（可能修改过）
            if cap.name != name:
                cap.name = name
                cap.updated_at = now
        else:
            cap = Capability(
                code=code,
                name=name,
                resource_type=resource,
                action=action,
                is_active=True,
                created_at=now,
                updated_at=now,
            )
            db.add(cap)
        code_map[code] = cap

    await db.flush()
    # 刷新未持久化的对象获取 id
    for code, cap in code_map.items():
        if cap.id is None:
            await db.refresh(cap)

    return code_map


async def seed_roles(db, capability_map: dict):
    """创建/更新系统角色"""
    now = datetime.now()

    result = await db.execute(select(Role))
    existing_roles = {r.slug: r for r in result.scalars().all()}

    for rdef in ROLE_DEFS:
        slug = rdef["slug"]
        if slug in existing_roles:
            role = existing_roles[slug]
            role.name = rdef["name"]
            role.description = rdef["description"]
            role.updated_at = now
        else:
            role = Role(
                slug=slug,
                name=rdef["name"],
                description=rdef["description"],
                is_system=True,
                is_active=True,
                created_at=now,
                updated_at=now,
            )
            db.add(role)
            await db.flush()
            await db.refresh(role)

        # 同步角色-能力关联
        target_codes = set(rdef["capability_codes"])
        target_ids = {capability_map[c].id for c in target_codes if c in capability_map}

        # 查询已有的关联
        existing_rc = await db.execute(
            select(RoleCapability).where(RoleCapability.role_id == role.id)
        )
        existing_ids = {rc.capability_id for rc in existing_rc.scalars().all()}

        # 需要新增的
        to_add = target_ids - existing_ids
        for cid in to_add:
            db.add(RoleCapability(
                role_id=role.id,
                capability_id=cid,
                created_at=now,
            ))

        # 需要删除的（从角色移除的权限）
        to_remove = existing_ids - target_ids
        if to_remove:
            await db.execute(
                RoleCapability.__table__.delete().where(
                    RoleCapability.role_id == role.id,
                    RoleCapability.capability_id.in_(to_remove),
                )
            )

        print(f"  {'更新' if slug in existing_roles else '创建'} 角色: {slug} ({len(target_ids)} 能力)")

    await db.flush()


async def main():
    print("=" * 50)
    print("RBAC 种子数据初始化")
    print("=" * 50)

    print("\n[1/3] 同步 capabilities ...")
    async with get_async_session_context() as db:
        capability_map = await seed_capabilities(db)
        print(f"  共 {len(capability_map)} 个权限能力")

        print("\n[2/3] 同步系统角色 ...")
        await seed_roles(db, capability_map)

        print("\n[3/3] 提交事务 ...")
        await db.commit()

    print("\n" + "=" * 50)
    print("[OK] RBAC 种子数据初始化完成！")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
