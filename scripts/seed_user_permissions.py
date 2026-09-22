#!/usr/bin/env python3
"""为指定用户（默认"第一个用户"）播种**全部后台页面**的访问权限（解决页面 403）。

## 为什么需要它

页面级 403 由前端中间件判定：``frontend/web/src/middleware/auth.ts`` 把页面的
``definePageMeta({permission})`` 与后端 ``/system/auth/me`` 下发的 ``permissions``
做**严格字符串比较**，不匹配即跳转 ``/403``。而后端这份 ``permissions`` 的唯一来源是::

    user_role_assignments → roles → role_capabilities → capabilities

用户没有任何角色绑定 ⇒ ``permissions`` 为空 ⇒ 除少数未声明 ``meta.permission`` 的页面外
**全部 403**（实测库内 1 个用户、0 条用户角色绑定，正是这种状态）。

## 本脚本做什么（全部幂等，只增不减）

1. 选中目标用户：``--user-id`` / ``--username``，缺省取 id 最小的用户（第一个用户）
2. 同步 ``capabilities`` 表与 ``src/api/v3/core/permission/codes.py`` 的码表：缺码补齐，
   复用 ``scripts/seed_rbac.py::seed_capabilities``，**不在此处重新定义码表**
3. 把**全部**权限码 + **全部**激活后台菜单授权给目标角色（默认 ``superadmin``），
   并把该角色的 ``data_scope`` 提升为 3（全部数据）—— 否则列表类接口只按
   "仅本人"过滤（``data_scope`` 为 NULL 时业务层按 1 处理）
4. 绑定"用户 ↔ 角色"
5. 失效该用户的权限缓存
6. 复核：重新从库读取该用户的权限码/菜单码，并核对**前端每个页面**声明的码是否都在
   授予集合内（哪个页面仍会 403 一目了然）

## 用法::

    python -m scripts.seed_user_permissions                     # 默认写库（幂等）
    python -m scripts.seed_user_permissions --dry-run           # 只打印计划，不写库
    python -m scripts.seed_user_permissions -u yang             # 按用户名选用户
    python -m scripts.seed_user_permissions --user-id 3
    python -m scripts.seed_user_permissions --role admin        # 默认 superadmin
    python -m scripts.seed_user_permissions --data-scope 2      # 默认 3（全部数据）
    python -m scripts.seed_user_permissions --keep-data-scope   # 不动角色已有数据范围

## 生效范围（写库后）

- **后端**：脚本会清 Redis 键并广播失效；API 进程的内存缓存 TTL 为 300s，
  若 Redis 未配置（``config/.env`` 无 ``REDIS_*``）则需**重启 API 服务**或等待 TTL。
- **前端**：``localStorage`` 里缓存的 ``userInfo`` 含旧的空 ``permissions``，
  必须**重新登录**（或清掉本地存储）后才会重新拉取。

退出码：0 成功；1 参数/业务错误；2 前置条件不满足（库不可连、角色不存在等）。
"""

from __future__ import annotations

import argparse
import asyncio
import importlib
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, Sequence

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

#: 前端页面目录（页面级权限声明的唯一位置）
PAGES_DIR = PROJECT_ROOT / "frontend" / "web" / "src" / "pages"

#: 页面文件里的权限声明（``definePageMeta({permission})`` 与页面内按钮权限共用同一字段名）
_PAGE_PERMISSION_RE = re.compile(r"permission\s*:\s*'([^']+)'")

EXIT_OK = 0
EXIT_USAGE = 1
EXIT_PRECONDITION = 2


def _load_all_models() -> None:
    """显式导入全部模型，确保 relationship 的字符串目标都能解析（否则 NoReferencedTableError）"""
    from shared.models import _LAZY_IMPORTS

    for module_path in sorted(set(_LAZY_IMPORTS.values())):
        importlib.import_module(module_path, package="shared.models")


def scan_page_permission_codes(pages_dir: Path = PAGES_DIR) -> dict[str, list[str]]:
    """扫描前端 ``pages/**/*.vue`` 里声明的权限码

    返回 ``{权限码: [声明它的页面 ...]}``。页面级 403 由 ``definePageMeta({permission})``
    决定（``frontend/web/src/middleware/auth.ts``），同名的按钮级 ``permission:`` 也一并纳入，
    因为它们指向同一份 ``capabilities`` 码表、缺一个就会在页面上表现为不可用。
    """
    found: dict[str, list[str]] = {}
    if not pages_dir.exists():
        return found

    for path in sorted(pages_dir.rglob("*.vue")):
        rel = str(path.relative_to(PROJECT_ROOT))
        for code in _PAGE_PERMISSION_RE.findall(path.read_text(encoding="utf-8")):
            # 只认"像权限码"的值，跳过 '...' / 'edit' 这类局部标记
            if ":" not in code and "." not in code:
                continue
            found.setdefault(code, []).append(rel)
    return found


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m scripts.seed_user_permissions",
        description="为指定用户（默认第一个用户）播种全部后台页面访问权限（真实写库）",
    )
    parser.add_argument("--user-id", type=int, help="目标用户 ID（缺省取 id 最小的用户）")
    parser.add_argument("--username", "-u", help="目标用户名（与 --user-id 互斥，后者优先）")
    parser.add_argument("--role", "-r", default="superadmin", help="承载全部权限的角色 slug，默认 superadmin")
    parser.add_argument(
        "--data-scope",
        type=int,
        choices=[1, 2, 3, 5],
        default=3,
        help="目标角色的数据范围（1 仅本人 / 2 本组及以下 / 3 全部 / 5 自定义组），默认 3",
    )
    parser.add_argument("--keep-data-scope", action="store_true", help="不修改角色已有的数据范围")
    parser.add_argument("--dry-run", action="store_true", help="只打印计划，不写库")
    parser.add_argument("--no-page-check", action="store_true", help="跳过前端页面权限码覆盖核对")
    return parser


async def _resolve_user(db: Any, args: argparse.Namespace) -> Optional[Any]:
    """按 --user-id / --username 取用户；都没有则取 id 最小的用户（第一个用户）"""
    from sqlalchemy import select

    from shared.models.user import User

    if args.user_id is not None:
        return (await db.execute(select(User).where(User.id == args.user_id))).scalar_one_or_none()

    if args.username:
        return (
            await db.execute(select(User).where(User.username == args.username))
        ).scalar_one_or_none()

    return (await db.execute(select(User).order_by(User.id.asc()).limit(1))).scalar_one_or_none()


async def _seed(args: argparse.Namespace) -> int:
    from sqlalchemy import select

    from scripts.seed_rbac import seed_capabilities
    from shared.models.rbac.admin_menu import AdminMenu
    from shared.models.rbac.role import Role
    from shared.models.rbac.role_admin_menu import RoleAdminMenu
    from shared.models.rbac.role_capability import RoleCapability
    from shared.models.rbac.user_role import UserRole
    from src.api.v3.core.permission.codes import CODE_LABELS
    from src.utils.database.unified_manager import db_manager

    async with db_manager.get_session_no_auto_commit() as db:
        user = await _resolve_user(db, args)
        if user is None:
            if args.user_id is not None:
                target = f"user_id={args.user_id}"
            elif args.username:
                target = f"username={args.username!r}"
            else:
                target = "库内没有任何用户"
            print(f"[ERROR] 找不到目标用户（{target}）", file=sys.stderr)
            return EXIT_PRECONDITION

        role = (await db.execute(select(Role).where(Role.slug == args.role))).scalar_one_or_none()
        if role is None:
            available = sorted((await db.execute(select(Role.slug))).scalars().all())
            print(
                f"[ERROR] 角色 '{args.role}' 不存在。库中现有角色: {', '.join(a for a in available if a) or '（无）'}\n"
                "        请先执行: python -m scripts.seed_rbac",
                file=sys.stderr,
            )
            return EXIT_PRECONDITION

        print("== 目标用户 ==")
        print(
            f"  id={user.id} username={user.username} email={user.email or '-'} "
            f"is_active={bool(user.is_active)} is_staff={bool(user.is_staff)} is_superuser={bool(user.is_superuser)}"
        )

        print("== 目标角色 ==")
        print(
            f"  slug={role.slug} id={role.id} name={role.name or '-'} is_system={bool(role.is_system)} "
            f"is_active={bool(role.is_active)} data_scope={role.data_scope}（NULL 视为 1）"
        )

        # ---------------- 权限码：以 codes.py 为权威，库内缺码补齐（复用 seed_rbac）
        cap_map = await seed_capabilities(db)
        target_codes = set(CODE_LABELS) | {
            code for code, cap in cap_map.items() if code and cap.is_active
        }
        cap_ids = {cap_map[code].id for code in target_codes if code in cap_map and cap_map[code].id}
        existing_cap_ids = set(
            (
                await db.execute(select(RoleCapability.capability_id).where(RoleCapability.role_id == role.id))
            )
            .scalars()
            .all()
        )
        to_add_caps = sorted(cap_ids - existing_cap_ids)

        # ---------------- 后台菜单：全部激活菜单授权给该角色
        target_menu_ids = set(
            (await db.execute(select(AdminMenu.id).where(AdminMenu.is_active.is_(True)))).scalars().all()
        )
        existing_menu_ids = set(
            (
                await db.execute(select(RoleAdminMenu.admin_menu_id).where(RoleAdminMenu.role_id == role.id))
            )
            .scalars()
            .all()
        )
        to_add_menus = sorted(target_menu_ids - existing_menu_ids)

        # ---------------- 角色数据范围
        scope_change: Optional[tuple[Any, int]] = None
        if not args.keep_data_scope and role.data_scope != args.data_scope:
            scope_change = (role.data_scope, args.data_scope)

        # ---------------- 用户 ↔ 角色绑定
        link = (
            await db.execute(
                select(UserRole).where(UserRole.user_id == user.id, UserRole.role_id == role.id)
            )
        ).scalar_one_or_none()

        print("== 计划（幂等，只增不减）==")
        print(f"  capabilities 目标 {len(target_codes)} 个码 → 新增关联 {len(to_add_caps)} 条")
        print(f"  admin_menus  目标 {len(target_menu_ids)} 个菜单 → 新增授权 {len(to_add_menus)} 条")
        if scope_change is not None:
            old, new = scope_change
            print(f"  data_scope   {old} → {new}")
        elif args.keep_data_scope:
            print(f"  data_scope   保持不变（{role.data_scope}）")
        else:
            print(f"  data_scope   已是 {args.data_scope}，无需变更")
        print(
            "  user_role_assignments "
            + ("已存在绑定，无需新增" if link is not None else f"新增 user={user.id} → role={role.slug}")
        )

        user_id = int(user.id)

        if args.dry_run:
            print("\n[dry-run] 未写库；去掉 --dry-run 即执行上述变更。")
        else:
            now = datetime.now()
            for capability_id in to_add_caps:
                db.add(RoleCapability(role_id=role.id, capability_id=capability_id, created_at=now))
            for menu_id in to_add_menus:
                db.add(RoleAdminMenu(role_id=role.id, admin_menu_id=menu_id, created_at=now))
            if scope_change is not None:
                role.data_scope = scope_change[1]
                role.updated_at = now
            if link is None:
                db.add(UserRole(user_id=user.id, role_id=role.id, created_at=now))
            await db.commit()
            print(
                f"\n[OK] 已写库：角色 {role.slug} 关联 +{len(to_add_caps)} 权限、+{len(to_add_menus)} 菜单，用户绑定已确保。")

    if args.dry_run:
        return EXIT_OK

    await _post_write(user_id, args)
    return EXIT_OK


async def _post_write(user_id: int, args: argparse.Namespace) -> None:
    """写库后的收尾：失效缓存 + 从库复核 + 前端页面覆盖核对"""
    from src.api.v3.core.permission.cache import native_client
    from src.api.v3.core.permission.invalidate import invalidate_user

    await invalidate_user(user_id)
    if native_client() is None:
        # Redis 是可选依赖（config/.env 未配 REDIS_* 时即此情形）：
        # 上面的 delete/publish 会各自降级并打印一行 "Redis 未连接" —— 那不是脚本失败。
        print(
            "  [提示] Redis 未连接：本次缓存失效只覆盖本进程，API 服务需**重启**"
            "（否则最长等内存缓存 TTL 300s）才会读到新权限集。"
        )

    from src.api.v3.core.permission.loader import load_codes_from_db
    from src.api.v3.modules.system.admin_menu.service import admin_menu_service
    from src.utils.database.unified_manager import db_manager

    async with db_manager.get_session() as db:
        codes = await load_codes_from_db(db, user_id)
        menus = await admin_menu_service.menu_codes_with_ancestors(db, user_id, is_superuser=False)

    print("== 复核（重新从库读取该用户）==")
    print(f"  权限码 {len(codes)} 个 / 菜单码 {len(menus)} 个")

    if args.no_page_check:
        return

    pages = scan_page_permission_codes()
    if not pages:
        print("  [提示] 未扫描到前端页面权限声明（pages 目录不存在？），跳过覆盖核对")
        return

    missing = {code: paths for code, paths in pages.items() if code not in codes}
    covered = len(pages) - len(missing)
    print("== 页面覆盖（frontend/web/src/pages 里声明的权限码）==")
    print(f"  页面权限码 {len(pages)} 个 → 已覆盖 {covered} 个，未覆盖 {len(missing)} 个")
    for code, paths in sorted(missing.items()):
        print(f"  [WARN] 未覆盖: {code} ← {', '.join(paths)}")
    if not missing:
        print("  全部页面权限码均已在授予集合内 ✔")

    print(
        "\n提醒：前端 localStorage 缓存的 userInfo 含旧权限集，请**退出并重新登录**；"
        "后端如未配置 Redis，需重启 API 服务或等待内存缓存 TTL(300s)。"
    )


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    _load_all_models()

    try:
        return asyncio.run(_seed(args))
    except ValueError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return EXIT_USAGE
    except Exception as exc:  # noqa: BLE001 - 顶层兜底，给出可读错误而不是 traceback
        print(f"[ERROR] 执行失败: {type(exc).__name__}: {exc}", file=sys.stderr)
        print("        请确认数据库可连接、已执行 python -m alembic upgrade head、且已执行 python -m scripts.seed_rbac",
              file=sys.stderr)
        return EXIT_PRECONDITION


if __name__ == "__main__":
    raise SystemExit(main())
