"""
安装向导 — 管理员创建模块
"""
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from shared.logging import default_logger as logger


async def create_admin_user(project_root: Path, username: str, email: str, password: str) -> Dict[str, Any]:
    """创建管理员用户"""
    if not username or not email or not password:
        return {"success": False, "message": "用户名、邮箱和密码不能为空"}
    if len(password) < 8:
        return {"success": False, "message": "密码长度不能少于8位"}

    try:
        from src.utils.database.main import get_async_session_context
        from shared.models.user import User as UserModel
        from src.utils.security.password_validator import hash_password
        from sqlalchemy import select

        async with get_async_session_context() as db:
            existing = await db.execute(
                select(UserModel).where(UserModel.username == username)
            )
            if existing.scalar_one_or_none():
                return {"success": False, "message": "用户名已存在"}

            now = datetime.utcnow()
            admin = UserModel(
                username=username,
                email=email,
                password=hash_password(password),
                is_superuser=True,
                is_staff=True,
                is_active=True,
                date_joined=now,
            )
            db.add(admin)
            await db.commit()
            return {"success": True, "message": f"管理员 {username} 创建成功", "user_id": admin.id}
    except Exception as e:
        logger.exception(f"创建管理员失败")
        return {"success": False, "message": f"创建失败: {str(e)}"}


async def seed_rbac_if_empty() -> Dict[str, Any]:
    """如果 RBAC 角色表为空，则种子初始角色权限数据。"""
    try:
        from src.utils.database.main import get_async_session_context
        from shared.models.rbac import Role
        from scripts.seed_rbac import seed_capabilities, seed_roles
        from sqlalchemy import select

        async with get_async_session_context() as db:
            existing = await db.execute(select(Role).limit(1))
            if existing.scalar_one_or_none():
                return {"success": True, "message": "RBAC 数据已存在，跳过"}

            cap_map = await seed_capabilities(db)
            await seed_roles(db, cap_map)
            await db.commit()
            logger.info("RBAC 角色权限种子数据已初始化")
            return {"success": True, "message": "RBAC 种子数据初始化成功"}
    except Exception as e:
        logger.warning(f"RBAC 种子数据初始化失败（可稍后手动运行 scripts/seed_rbac.py）: {e}")
        return {"success": False, "message": str(e)}
