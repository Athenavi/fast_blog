"""
用户管理命令（真实实现：直接操作数据库）
"""
import asyncio
from datetime import datetime

import typer
from sqlalchemy import select, func

app = typer.Typer(help="用户管理")


def _run(coro):
    """在独立事件循环中执行异步数据库操作"""
    return asyncio.run(coro)


async def _get_db():
    from src.utils.database.unified_manager import db_manager
    return db_manager


@app.command("create")
def create_user(
    username: str = typer.Option(..., "--username", "-u", prompt=True, help="用户名"),
    email: str = typer.Option(None, "--email", "-e", help="邮箱"),
    password: str = typer.Option(..., "--password", "-p", prompt=True, hide_input=True,
                                 confirmation_prompt=True, help="密码"),
    is_superuser: bool = typer.Option(False, "--superuser", help="是否为超级管理员"),
):
    """创建新用户"""
    async def _create():
        from shared.models.user import User
        from src.utils.security.password_validator import hash_password

        if len(password) < 6:
            raise ValueError("密码长度至少 6 位")

        db = await _get_db()
        async with db.get_session() as session:
            exists = (await session.execute(
                select(User.id).where(User.username == username)
            )).scalar_one_or_none()
            if exists:
                raise ValueError(f"用户名 {username} 已存在")

            now = datetime.now()
            user = User(
                username=username,
                email=email or None,
                password=hash_password(password),
                is_superuser=is_superuser,
                is_active=True,
                date_joined=now,
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            return user.id

    try:
        uid = _run(_create())
        typer.echo(f"✅ 用户 {username} 创建成功 (ID={uid})")
    except Exception as e:
        typer.echo(f"❌ 创建失败: {e}", err=True)
        raise typer.Exit(code=1)


@app.command("list")
def list_users(
    page: int = typer.Option(1, "--page", help="页码"),
    limit: int = typer.Option(20, "--limit", help="每页数量"),
):
    """列出所有用户"""
    async def _list():
        from shared.models.user import User

        db = await _get_db()
        async with db.get_session() as session:
            total = (await session.execute(select(func.count(User.id)))).scalar() or 0
            rows = (await session.execute(
                select(User).order_by(User.id).offset((page - 1) * limit).limit(limit)
            )).scalars().all()
            return total, rows

    try:
        total, rows = _run(_list())
        typer.echo(f"用户总数: {total} (第 {page} 页, 每页 {limit} 条)")
        for u in rows:
            flags = []
            if u.is_superuser:
                flags.append("superuser")
            if u.is_staff:
                flags.append("staff")
            if not u.is_active:
                flags.append("inactive")
            typer.echo(f"  [{u.id}] {u.username or ''} <{u.email or ''}> {' '.join(flags)}")
    except Exception as e:
        typer.echo(f"❌ 查询失败: {e}", err=True)
        raise typer.Exit(code=1)


@app.command("activate")
def activate_user(
    user_id: int = typer.Argument(..., help="用户 ID"),
):
    """激活用户"""
    async def _activate():
        from shared.models.user import User

        db = await _get_db()
        async with db.get_session() as session:
            user = (await session.execute(
                select(User).where(User.id == user_id)
            )).scalar_one_or_none()
            if not user:
                raise ValueError(f"用户 {user_id} 不存在")
            user.is_active = True
            await session.commit()
            return user

    try:
        u = _run(_activate())
        typer.echo(f"✅ 用户 {u.id} 已激活")
    except Exception as e:
        typer.echo(f"❌ 激活失败: {e}", err=True)
        raise typer.Exit(code=1)


@app.command("deactivate")
def deactivate_user(
    user_id: int = typer.Argument(..., help="用户 ID"),
):
    """停用用户"""
    async def _deactivate():
        from shared.models.user import User

        db = await _get_db()
        async with db.get_session() as session:
            user = (await session.execute(
                select(User).where(User.id == user_id)
            )).scalar_one_or_none()
            if not user:
                raise ValueError(f"用户 {user_id} 不存在")
            user.is_active = False
            await session.commit()
            return user

    try:
        u = _run(_deactivate())
        typer.echo(f"✅ 用户 {u.id} 已停用")
    except Exception as e:
        typer.echo(f"❌ 停用失败: {e}", err=True)
        raise typer.Exit(code=1)


@app.command("reset-password")
def reset_password(
    user_id: int = typer.Argument(..., help="用户 ID"),
    new_password: str = typer.Option(..., "--password", "-p", prompt=True, hide_input=True,
                                     confirmation_prompt=True, help="新密码"),
):
    """重置用户密码"""
    async def _reset():
        from shared.models.user import User
        from src.utils.security.password_validator import hash_password

        if len(new_password) < 6:
            raise ValueError("密码长度至少 6 位")

        db = await _get_db()
        async with db.get_session() as session:
            user = (await session.execute(
                select(User).where(User.id == user_id)
            )).scalar_one_or_none()
            if not user:
                raise ValueError(f"用户 {user_id} 不存在")
            user.password = hash_password(new_password)
            await session.commit()
            return user

    try:
        u = _run(_reset())
        typer.echo(f"✅ 用户 {u.id} 密码已重置")
    except Exception as e:
        typer.echo(f"❌ 重置失败: {e}", err=True)
        raise typer.Exit(code=1)
