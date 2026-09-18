"""auth 模块业务逻辑

复用既有安全能力（IP 限流、账户锁定、会话管理、审计日志、事件总线），
**不重复实现**任何安全策略，保证 v3 与 v2 的登录行为一致。
"""

from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from shared.config.settings import settings
from shared.models.user import User as UserModel
from shared.services.plugins.event_bus import event_bus
from shared.services.security.audit_log_service import (
    AuditLogAction,
    AuditLogLevel,
    audit_log_service,
)
from shared.services.security.rate_limiter import rate_limiter
from shared.services.security.rbac_service import rbac_service
from shared.services.users.login_security_service import login_security_service
from shared.services.users.session_management_service import session_management_service
from src.api.v3.core.exceptions import BadRequestError, UnauthorizedError
from src.api.v3.core.logger import get_logger
from src.api.v3.core.security import authenticate_user, decode_token, issue_token

logger = get_logger("auth")


class AuthService:
    """登录 / 登出 / 刷新 / 当前用户"""

    async def login(
        self,
        db: AsyncSession,
        *,
        identifier: str,
        password: str,
        remember_me: bool = False,
        ip: str = "unknown",
        user_agent: str = "",
    ) -> dict:
        """登录：限流 → 账户锁定 → 密码校验 → 2FA → 签发令牌

        失败路径都会写登录尝试记录与审计日志（与 v2 一致）。
        """
        ip_limited, _info = await rate_limiter.check_ip_limit(ip)
        if ip_limited:
            raise BadRequestError("登录尝试过于频繁，请稍后再试", code=429)

        locked, _unlock_at = await login_security_service.check_account_locked_async(identifier, db)
        if locked:
            await login_security_service.record_login_attempt_async(
                identifier, ip, user_agent, False, "Account locked", db
            )
            raise BadRequestError("账户已被临时锁定，请稍后再试", code=423)

        user = await authenticate_user(db, identifier, password)
        if not user:
            await login_security_service.record_login_attempt_async(
                identifier, ip, user_agent, False, "Invalid credentials", db
            )
            await audit_log_service.log_action(
                db=db,
                user_id=None,
                user_name=identifier,
                action=AuditLogAction.LOGIN,
                level=AuditLogLevel.WARNING,
                resource_type="user",
                description="登录失败：用户名或密码错误",
                ip_address=ip,
                user_agent=user_agent,
            )
            await event_bus.emit(
                "user.login_failed", {"user_id": None, "username": identifier, "ip_address": ip}
            )
            raise UnauthorizedError("用户名或密码错误")

        await login_security_service.record_login_attempt_async(identifier, ip, user_agent, True, db=db)
        await login_security_service.clear_failed_attempts_async(identifier, db)

        if not user.is_active:
            raise BadRequestError("账户已停用")

        if user.is_2fa_enabled:
            from datetime import timedelta

            temp_token = issue_token(str(user.id), "temp_2fa", timedelta(minutes=5))
            return {
                "requires_2fa": True,
                "temp_token": temp_token,
                "message": "请输入双因素验证码",
            }

        return await self.grant_tokens(
            db, user, remember_me=remember_me, ip=ip, user_agent=user_agent
        )

    async def grant_tokens(
        self,
        db: AsyncSession,
        user: UserModel,
        *,
        remember_me: bool = False,
        ip: str = "unknown",
        user_agent: str = "",
    ) -> dict:
        """签发令牌、轮换会话并写审计日志"""
        access_token = issue_token(str(user.id), "access")
        refresh_token = issue_token(str(user.id), "refresh") if remember_me else None

        session_id = await session_management_service.create_session(
            user.id, {"ip": ip, "user_agent": user_agent}, ip, user_agent
        )
        # 会话轮换：撤销除当前会话以外的所有会话
        await session_management_service.revoke_all_sessions(
            user.id, exclude_session_id=session_id
        )

        await audit_log_service.log_action(
            db=db,
            user_id=user.id,
            user_name=user.username,
            action=AuditLogAction.LOGIN,
            level=AuditLogLevel.INFO,
            resource_type="user",
            resource_id=str(user.id),
            description="用户登录成功",
            ip_address=ip,
            user_agent=user_agent,
        )
        await event_bus.emit(
            "user.login", {"user_id": user.id, "username": user.username, "ip_address": ip}
        )

        data: dict[str, Any] = {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": int(settings.JWT_EXPIRATION_DELTA),
            "email_verified": bool(getattr(user, "is_email_verified", False)),
        }
        if refresh_token:
            data["refresh_token"] = refresh_token
        return data

    async def refresh(self, refresh_token: Optional[str]) -> dict:
        """用 refresh token 换新令牌"""
        if not refresh_token:
            raise BadRequestError("未提供刷新令牌")

        payload = decode_token(refresh_token)
        if payload.get("type") != "refresh":
            raise BadRequestError("令牌类型错误")

        subject = str(payload.get("sub") or "")
        if not subject:
            raise UnauthorizedError("令牌无效")
        return {
            "access_token": issue_token(subject, "access"),
            "refresh_token": issue_token(subject, "refresh"),
            "token_type": "bearer",
            "expires_in": int(settings.JWT_EXPIRATION_DELTA),
        }

    async def logout(self, token: Optional[str], user: UserModel) -> None:
        """登出：token 入黑名单 + 撤销该用户全部会话"""
        from src.api.v3.core.security import revoke_token

        if token:
            revoke_token(token)
        try:
            await session_management_service.revoke_all_sessions(user.id)
        except Exception:  # noqa: BLE001 - 撤销失败不应阻断登出
            logger.exception("撤销用户会话失败 user_id=%s", getattr(user, "id", None))
        await event_bus.emit(
            "user.logout",
            {"user_id": user.id, "username": getattr(user, "username", None)},
        )

    async def build_current_user(self, db: AsyncSession, user: UserModel) -> dict:
        """组装当前用户信息（含角色 slug 与权限码，供前端菜单/按钮权限使用）"""
        permissions = sorted(await rbac_service.get_permission_codes_set(db, user.id))
        roles = [role.slug for role in await rbac_service.get_user_roles(db, user.id)]
        return {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "is_active": bool(user.is_active),
            "is_staff": bool(user.is_staff),
            "is_superuser": bool(user.is_superuser),
            "vip_level": int(user.vip_level or 0),
            "locale": user.locale,
            "profile_picture": user.profile_picture,
            "roles": roles,
            "permissions": permissions,
        }


auth_service = AuthService()
