"""mobile/auth 业务逻辑

登录直接复用 ``modules/system/auth`` 的 ``AuthService``（含限流/锁定/会话/审计），
注册复用 ``user_manager.create_user_account`` + 唯一性校验，随后同样走 ``AuthService``
签发令牌，保证移动端与后台的登录语义一致。
"""

from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.user import User as UserModel
from shared.services.users.user_manager import create_user_account
from src.api.v3.core.exceptions import BadRequestError, ConflictError
from src.api.v3.core.logger import get_logger
from src.api.v3.modules.mobile.auth.schema import MobileRegisterRequest
from src.api.v3.modules.system.auth.service import auth_service
from src.api.v3.modules.system.user.crud import user_crud

logger = get_logger("mobile.auth")


class MobileAuthService:
    """移动端登录 / 注册"""

    async def login(
        self,
        db: AsyncSession,
        *,
        identifier: str,
        password: str,
        remember_me: bool = True,
        ip: str = "unknown",
        user_agent: str = "",
        user: Optional[UserModel] = None,
    ) -> dict:
        data = await auth_service.login(
            db,
            identifier=identifier,
            password=password,
            remember_me=remember_me,
            ip=ip,
            user_agent=user_agent,
        )
        if user is not None:
            data.setdefault("user_id", user.id)
        return data

    async def register(
        self,
        db: AsyncSession,
        payload: MobileRegisterRequest,
        *,
        ip: str = "unknown",
        user_agent: str = "",
    ) -> dict:
        if await user_crud.exists(db, username=payload.username):
            raise ConflictError("用户名已被占用")
        if await user_crud.exists(db, email=payload.email):
            raise ConflictError("邮箱已被注册")

        user = await create_user_account(
            db,
            username=payload.username,
            email=payload.email,
            password=payload.password,
            is_active=True,
            is_staff=False,
            is_superuser=False,
        )
        if user is None:
            raise BadRequestError("注册失败，请稍后重试")

        await db.commit()
        await db.refresh(user)

        data = await auth_service.grant_tokens(
            db, user, remember_me=True, ip=ip, user_agent=user_agent
        )
        data.update({"user_id": user.id, "username": user.username})
        return data


mobile_auth_service = MobileAuthService()
