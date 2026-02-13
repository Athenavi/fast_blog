"""
用户管理器
处理用户创建、验证等操作
"""
from typing import Optional

from fastapi import Depends
from fastapi_users import BaseUserManager, IntegerIDMixin
from fastapi_users_db_sqlalchemy import SQLAlchemyUserDatabase

from src.models.user import User as UserModel
from src.setting import settings
from src.utils.database.main import get_async_session
from src.utils.security.password_validator import verify_password


class UserManager(IntegerIDMixin, BaseUserManager[UserModel, int]):
    def __init__(self, user_db: SQLAlchemyUserDatabase):
        super().__init__(user_db)
        self.reset_password_token_secret = settings.SECRET_KEY
        self.verification_token_secret = settings.SECRET_KEY

    async def get(self, id: int) -> Optional[UserModel]:
        """根据ID获取用户"""
        return await self.user_db.get(id)

    async def get_by_email(self, email: str) -> Optional[UserModel]:
        """根据邮箱获取用户"""
        return await self.user_db.get_by_email(email)

    async def create(self, user_create_dict: dict) -> UserModel:
        """创建新用户"""
        # 提取密码
        password = user_create_dict.get('password', '')
        
        # 从字典中移除密码，因为不应该直接传递给User模型构造函数
        user_data = {k: v for k, v in user_create_dict.items() if k != 'password'}
        
        # 确保不包含数据库自动生成的时间戳字段，让数据库/SQLAlchemy处理这些字段
        # 避免手动设置 created_at 和 updated_at，因为这可能导致时区冲突
        for field in ['created_at', 'updated_at']:
            user_data.pop(field, None)
        
        # 创建用户对象
        user = UserModel(**user_data)
        
        # 设置密码
        user.set_password(password)
        
        # 使用数据库会话保存用户
        from src.utils.database.main import get_async_session
        async for session in get_async_session():
            session.add(user)
            await session.commit()
            await session.refresh(user)
            return user

    async def update(self, user: UserModel, update_dict: dict) -> UserModel:
        """更新用户信息"""
        for field, value in update_dict.items():
            setattr(user, field, value)
        return await self.user_db.update(user)

    async def authenticate(self, email: str, password: str) -> Optional[UserModel]:
        """验证用户凭据"""
        user = await self.get_by_email(email)
        if not user:
            return None
        if not user.is_active:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user


async def get_user_db():
    """获取用户数据库实例"""
    async for session in get_async_session():
        yield SQLAlchemyUserDatabase(session, UserModel)


async def get_user_manager(user_db=Depends(get_user_db)):
    """获取用户管理器实例"""
    yield UserManager(user_db)