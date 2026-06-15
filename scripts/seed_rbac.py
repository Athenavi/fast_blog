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
from src.utils.database.main import get_async_session_context


# ============================================================
# 预定义权限列表（与已删除的 permission_system.py 一致）
# ============================================================
PERMISSIONS = {
    "article": {
        "view": "查看文章",
        "create": "创建文章",
        "edit": "编辑文章",
        "delete": "删除文章",
        "publish": "发布文章",
        "edit_others": "编辑他人文章",
        "delete_others": "删除他人文章",
    },
    "category": {
        "view": "查看分类",
        "create": "创建分类",
        "edit": "编辑分类",
        "delete": "删除分类",
    },
    "page": {
        "view": "查看页面",
        "create": "创建页面",
        "edit": "编辑页面",
        "delete": "删除页面",
        "publish": "发布页面",
    },
    "menu": {
        "view": "查看菜单",
        "create": "创建菜单",
        "edit": "编辑菜单",
        "delete": "删除菜单",
    },
    "media": {
        "view": "查看媒体",
        "upload": "上传文件",
        "delete": "删除文件",
    },
    "user": {
        "view": "查看用户",
        "create": "创建用户",
        "edit": "编辑用户",
        "delete": "删除用户",
        "manage_roles": "管理角色",
    },
    "plugin": {
        "view": "查看插件",
        "install": "安装插件",
        "activate": "激活/停用插件",
        "delete": "删除插件",
        "configure": "配置插件",
    },
    "theme": {
        "view": "查看主题",
        "install": "安装主题",
        "activate": "激活主题",
        "delete": "删除主题",
        "customize": "自定义主题",
    },
    "settings": {
        "view": "查看设置",
        "edit": "编辑设置",
    },
    "backup": {
        "create": "创建备份",
        "restore": "恢复备份",
        "delete": "删除备份",
    },
    "comment": {
        "view": "查看评论",
        "approve": "审核评论",
        "edit": "编辑评论",
        "delete": "删除评论",
    },
}


def _build_capability_list():
    """将 PERMISSIONS 字典展开为 (code, name, resource_type, action) 列表"""
    result = []
    for resource, actions in PERMISSIONS.items():
        for action, label in actions.items():
            code = f"{resource}:{action}"
            result.append((code, label, resource, action))
    return result


ALL_CAPABILITIES = _build_capability_list()


def _cap_codes(*specs):
    """根据 (resource, action) 对生成 capability code 列表"""
    return [f"{r}:{a}" for r, a in specs]


# ============================================================
# 角色定义
# ============================================================
ROLE_DEFS = [
    {
        "slug": "superadmin",
        "name": "超级管理员",
        "description": "拥有系统所有权限",
        "capability_codes": [c[0] for c in ALL_CAPABILITIES],
    },
    {
        "slug": "admin",
        "name": "管理员",
        "description": "管理类权限，不含敏感系统设置",
        "capability_codes": _cap_codes(
            ("article", "view"), ("article", "create"), ("article", "edit"),
            ("article", "delete"), ("article", "publish"), ("article", "edit_others"),
            ("article", "delete_others"),
            ("category", "view"), ("category", "create"), ("category", "edit"),
            ("category", "delete"),
            ("page", "view"), ("page", "create"), ("page", "edit"),
            ("page", "delete"), ("page", "publish"),
            ("menu", "view"), ("menu", "create"), ("menu", "edit"), ("menu", "delete"),
            ("media", "view"), ("media", "upload"), ("media", "delete"),
            ("user", "view"), ("user", "create"), ("user", "edit"),
            ("user", "delete"), ("user", "manage_roles"),
            ("plugin", "view"), ("plugin", "install"), ("plugin", "activate"),
            ("plugin", "delete"), ("plugin", "configure"),
            ("theme", "view"), ("theme", "install"), ("theme", "activate"),
            ("theme", "delete"), ("theme", "customize"),
            ("backup", "create"), ("backup", "restore"), ("backup", "delete"),
            ("comment", "view"), ("comment", "approve"),
            ("comment", "edit"), ("comment", "delete"),
            ("settings", "view"),   # 可查看设置但不能编辑
        ),
    },
    {
        "slug": "editor",
        "name": "编辑者",
        "description": "内容管理权限",
        "capability_codes": _cap_codes(
            ("article", "view"), ("article", "create"), ("article", "edit"),
            ("article", "delete"), ("article", "publish"),
            ("category", "view"), ("category", "create"), ("category", "edit"),
            ("page", "view"), ("page", "create"), ("page", "edit"),
            ("page", "delete"), ("page", "publish"),
            ("menu", "view"),
            ("media", "view"), ("media", "upload"), ("media", "delete"),
            ("comment", "view"), ("comment", "approve"),
            ("comment", "edit"), ("comment", "delete"),
        ),
    },
    {
        "slug": "user",
        "name": "普通用户",
        "description": "基础浏览和互动权限",
        "capability_codes": _cap_codes(
            ("article", "view"),
            ("category", "view"),
            ("page", "view"),
            ("media", "view"), ("media", "upload"),
            ("comment", "view"), ("comment", "edit"),
        ),
    },
]


async def seed_capabilities(db) -> dict:
    """同步 capabilities 表，返回 {code: Capability} 映射"""
    result = await db.execute(select(Capability))
    existing = {c.code: c for c in result.scalars().all()}

    now = datetime.utcnow()
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
    now = datetime.utcnow()

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
