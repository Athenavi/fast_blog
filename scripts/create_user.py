#!/usr/bin/env python3
"""创建用户并绑定内置角色（安装初始化用，也可独立运行）。

用法::

    python -m scripts.create_user --list-roles          # 列出库里可用角色
    python -m scripts.create_user -u admin -r superadmin
    python -m scripts.create_user -u editor1 -r editor -e editor1@example.com
    python -m scripts.create_user -u admin -r admin --force     # 已存在则重置密码并覆盖角色
    FASTBLOG_PW=xxx python -m scripts.create_user -u ops -r admin --password-env FASTBLOG_PW

角色来自 ``roles`` 表（由 ``python -m scripts.seed_rbac`` 写入四个内置角色：
``superadmin`` / ``admin`` / ``editor`` / ``user``）。本脚本**真实写库**：
``users`` 与 ``user_role_assignments``；``superadmin`` 角色会同时置 ``is_superuser=True``。

密码来源优先级：``--password`` > ``--password-env`` > 交互式输入（getpass，不回显）。
退出码：0 成功；1 参数或业务错误；2 前置条件不满足（未迁移、未 seed 角色等）。
"""

from __future__ import annotations

import argparse
import asyncio
import getpass
import importlib
import os
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

#: 内置角色 slug（与 scripts/seed_rbac.py::ROLE_DEFS 一致）
BUILTIN_ROLES = ("superadmin", "admin", "editor", "user")

EXIT_OK = 0
EXIT_USAGE = 1
EXIT_PRECONDITION = 2


def _load_all_models() -> None:
    """显式导入全部模型，确保 relationship 的字符串目标都能解析（否则 NoReferencedTableError）。"""
    from shared.models import _LAZY_IMPORTS

    for module_path in sorted(set(_LAZY_IMPORTS.values())):
        importlib.import_module(module_path, package="shared.models")


def _resolve_password(args: argparse.Namespace) -> str:
    """按优先级取密码：--password > --password-env > 交互输入。"""
    if args.password:
        return args.password

    if args.password_env:
        value = os.environ.get(args.password_env)
        if not value:
            raise ValueError(f"环境变量 {args.password_env} 为空或未设置")
        return value

    if not sys.stdin.isatty():
        raise ValueError("非交互环境下必须提供 --password 或 --password-env")

    first = getpass.getpass("密码: ")
    second = getpass.getpass("确认密码: ")
    if first != second:
        raise ValueError("两次输入的密码不一致")
    return first


async def list_roles() -> int:
    """打印库中可用角色。"""
    from sqlalchemy import select

    from shared.models.rbac.role import Role
    from src.utils.database.unified_manager import db_manager

    async with db_manager.get_session() as db:
        roles = (await db.execute(select(Role).order_by(Role.id))).scalars().all()

    if not roles:
        print("库里没有任何角色。请先执行: python -m scripts.seed_rbac")
        return EXIT_PRECONDITION

    print(f"可用角色（{len(roles)} 个）:")
    for role in roles:
        marker = " [内置]" if role.slug in BUILTIN_ROLES else ""
        print(f"  - {role.slug:<12} {role.name or ''}{marker}")
    return EXIT_OK


async def create_user(args: argparse.Namespace) -> int:
    """真实创建用户并按角色绑定；``--force`` 时重置密码并覆盖角色。"""
    from sqlalchemy import delete, select

    from shared.models.rbac.role import Role
    from shared.models.rbac.user_role import UserRole
    from shared.models.user import User
    from src.utils.database.unified_manager import db_manager
    from src.utils.security.password_validator import hash_password, validate_password_strength

    password = args.password_value
    ok, message = validate_password_strength(password)
    if not ok:
        raise ValueError(f"密码不符合要求: {message}")

    async with db_manager.get_session() as db:
        role = (await db.execute(select(Role).where(Role.slug == args.role))).scalar_one_or_none()
        if role is None:
            available = (await db.execute(select(Role.slug))).scalars().all()
            hint = f"库中现有角色: {', '.join(available)}" if available else "库中没有任何角色"
            print(
                f"角色 '{args.role}' 不存在（{hint}）。\n"
                "请先执行: python -m scripts.seed_rbac",
                file=sys.stderr,
            )
            return EXIT_PRECONDITION

        user = (await db.execute(select(User).where(User.username == args.username))).scalar_one_or_none()
        if user is not None and not args.force:
            print(f"用户 '{args.username}' 已存在（ID={user.id}）。如需重置密码并覆盖角色请加 --force", file=sys.stderr)
            return EXIT_USAGE

        if args.email:
            email_owner = (
                await db.execute(select(User).where(User.email == args.email, User.username != args.username))
            ).scalar_one_or_none()
            if email_owner is not None:
                print(f"邮箱 '{args.email}' 已被用户 '{email_owner.username}' 使用", file=sys.stderr)
                return EXIT_USAGE

        is_superuser = args.superuser if args.superuser is not None else (args.role == "superadmin")

        if user is None:
            user = User(
                username=args.username,
                email=args.email or None,
                password=hash_password(password),
                is_superuser=is_superuser,
                is_active=True,
                is_staff=args.role in ("superadmin", "admin"),
                date_joined=datetime.now(),
            )
            db.add(user)
            await db.flush()
            action = "创建"
        else:
            user.password = hash_password(password)
            user.is_superuser = is_superuser
            user.is_active = True
            await db.flush()
            action = "更新"

        await db.execute(delete(UserRole).where(UserRole.user_id == user.id))
        db.add(UserRole(user_id=user.id, role_id=role.id, created_at=datetime.now()))
        await db.flush()

        user_id, username, email = user.id, user.username, user.email

    print(f"[OK] 用户{action}成功: id={user_id} username={username} email={email or '-'}")
    print(f"     角色={args.role}（{role.name or ''}） is_superuser={is_superuser}")
    return EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m scripts.create_user",
        description="创建用户并绑定内置角色（真实写库）",
    )
    parser.add_argument("--username", "-u", help="用户名（唯一）")
    parser.add_argument("--email", "-e", help="邮箱（可选，唯一）")
    parser.add_argument("--role", "-r", default="user", help=f"角色 slug，默认 user；内置: {', '.join(BUILTIN_ROLES)}")
    parser.add_argument("--password", "-p", help="密码（明文；不建议，会出现在进程列表）")
    parser.add_argument("--password-env", help="从该环境变量读取密码（推荐给自动化）")
    parser.add_argument("--force", action="store_true", help="用户已存在时重置密码并覆盖角色绑定")
    parser.add_argument("--superuser", dest="superuser", action="store_true", default=None, help="显式置为超级管理员")
    parser.add_argument("--no-superuser", dest="superuser", action="store_false", help="显式取消超级管理员")
    parser.add_argument("--list-roles", action="store_true", help="列出库中可用角色后退出")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    _load_all_models()

    try:
        if args.list_roles:
            return asyncio.run(list_roles())

        if not args.username:
            print("必须提供 --username（或用 --list-roles 查看角色）", file=sys.stderr)
            return EXIT_USAGE

        try:
            args.password_value = _resolve_password(args)
        except ValueError as exc:
            print(f"{exc}", file=sys.stderr)
            return EXIT_USAGE

        return asyncio.run(create_user(args))
    except ValueError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return EXIT_USAGE
    except Exception as exc:  # noqa: BLE001 - 顶层兜底，给出可读错误而不是 traceback
        print(f"[ERROR] 执行失败: {type(exc).__name__}: {exc}", file=sys.stderr)
        print("        请确认数据库可连接、且已执行 python -m alembic upgrade head", file=sys.stderr)
        return EXIT_PRECONDITION


if __name__ == "__main__":
    raise SystemExit(main())
