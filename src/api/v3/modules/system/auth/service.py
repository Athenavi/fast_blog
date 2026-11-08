"""auth 模块业务逻辑

复用既有安全能力（IP 限流、账户锁定、会话管理、审计日志、事件总线），
**不重复实现**任何安全策略，保证 v3 与 v2 的登录行为一致。
"""

from datetime import datetime, timedelta
from typing import Any, Optional

from sqlalchemy import func, select
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
from shared.services.security.two_factor_service import two_factor_service
from shared.services.users.login_security_service import login_security_service
from shared.services.users.session_management_service import session_management_service
from src.api.v3.core.exceptions import BadRequestError, UnauthorizedError
from src.api.v3.core.logger import get_logger
from src.api.v3.core.security import authenticate_user, decode_token_async, issue_token

logger = get_logger("auth")

#: OAuth 自助建号后，邮箱验证的宽限窗口
EMAIL_VERIFICATION_GRACE = timedelta(hours=24)


def email_verification_expired(user: Any, now=None) -> bool:
    """未验证邮箱是否已过宽限期。

    规则只作用于 **``is_email_verified=False`` 的账号**（即 OAuth 自助建号）：
      - 宽限期内（24h）照常使用，期间应引导用户完成验证；
      - 过期后拒绝签发新令牌（登录被拦），必须完成验证才能继续；
      - 没有邮箱的第三方账号（微信/QQ/微博）无从验证，不适用。
    """
    if bool(getattr(user, "is_email_verified", True)):
        return False
    if not getattr(user, "email", None):
        return False
    joined = getattr(user, "date_joined", None)
    if joined is None:
        return False
    now = now or datetime.now()
    try:
        return (now - joined) > EMAIL_VERIFICATION_GRACE
    except TypeError:  # 混用 aware/naive 时间时按未过期处理，避免误锁账号
        return False


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
        if email_verification_expired(user):
            # 24h 宽限期已过仍未验证：不再签发令牌，必须完成邮箱验证
            raise UnauthorizedError(
                "邮箱尚未验证，且已超过 24 小时宽限期；请重新发送验证邮件并完成验证后再登录"
            )

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

        payload = await decode_token_async(refresh_token)
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

    async def verify_2fa(
        self,
        db: AsyncSession,
        *,
        temp_token: str,
        code: str,
        remember_me: bool = False,
        ip: str = "unknown",
        user_agent: str = "",
    ) -> dict:
        """登录第二步：用 ``temp_2fa`` 令牌 + 验证码换正式令牌。

        temp_token 只能当"第二步凭证"用：鉴权依赖会拒绝所有非 access 类型
        （见 ``src/auth/auth_deps.py``），所以它无法被当成登录态使用。
        验证通过后立即吊销它，避免同一枚令牌被重放。
        """
        payload = await decode_token_async(temp_token)
        if payload.get("type") != "temp_2fa":
            raise UnauthorizedError("无效的验证令牌")
        try:
            user_id = int(payload.get("sub") or "")
        except (TypeError, ValueError):
            raise UnauthorizedError("无效的验证令牌") from None

        user = await db.get(UserModel, user_id)
        if user is None or not user.is_active or not user.is_2fa_enabled:
            raise UnauthorizedError("无效的验证令牌")

        result = await two_factor_service.verify(db, user_id, code)
        if not result.get("success"):
            # 失败也计一次登录尝试：否则 2FA 环节可以无限次猜码
            await login_security_service.record_login_attempt_async(
                user.username, ip, user_agent, False, db=db
            )
            raise UnauthorizedError(result.get("error") or "验证码无效")

        from src.api.v3.core.security import revoke_token

        revoke_token(temp_token)

        return await self.grant_tokens(
            db, user, remember_me=remember_me, ip=ip, user_agent=user_agent
        )

    async def logout(self, token: Optional[str], user: UserModel) -> None:
        """登出：当前令牌入黑名单 + 该用户全部令牌失效 + 撤销会话记录"""
        from src.api.v3.core.security import revoke_token, revoke_user_tokens

        if token:
            revoke_token(token)
        # 令牌不带会话 id，`revoke_all_sessions` 只能清记录，动不了已发出的令牌。
        # 水位线把该用户此刻之前签发的所有令牌（含 refresh）一并作废。
        revoke_user_tokens(user.id)
        try:
            await session_management_service.revoke_all_sessions(user.id)
        except Exception:  # noqa: BLE001 - 撤销失败不应阻断登出
            logger.exception("撤销用户会话失败 user_id=%s", getattr(user, "id", None))
        await event_bus.emit(
            "user.logout",
            {"user_id": user.id, "username": getattr(user, "username", None)},
        )

    async def send_email_verification(self, db: AsyncSession, *, email: str) -> bool:
        """给"待验证"的账号发验证邮件；返回值**不对外暴露**（防账号枚举）。"""
        normalized = str(email or "").strip().lower()
        if not normalized:
            return False
        user = (
            await db.execute(
                select(UserModel)
                .where(func.lower(UserModel.email) == normalized)
                .limit(1)
            )
        ).scalars().first()
        if user is None or bool(getattr(user, "is_email_verified", True)):
            return False

        token = issue_token(str(user.id), "email_verify", timedelta(hours=24))
        base = str(getattr(settings, "SITE_URL", "") or "").rstrip("/")
        link = f"{base}/api/v3/system/auth/email/verify?token={token}"
        body = chr(10).join(
            [
                "请点击下面的链接完成邮箱验证（24 小时内有效）：",
                "",
                link,
                "",
                "如果这不是你的操作，请忽略本邮件。",
            ]
        )
        try:
            from src.utils.send_email import api_mail

            await api_mail(user.id, body, site_name="邮箱验证", recipient=user.email)
        except Exception:  # noqa: BLE001 - 发信失败不向调用方泄露内部错误
            logger.exception("发送邮箱验证邮件失败 user_id=%s", getattr(user, "id", None))
        return True

    async def verify_email(self, db: AsyncSession, token: str) -> UserModel:
        """验证邮件里的 token：只接受 ``email_verify`` 类型，成功后置为已验证。"""
        payload = await decode_token_async(token)
        if payload.get("type") != "email_verify":
            raise UnauthorizedError("验证链接无效或已过期")
        try:
            user_id = int(payload.get("sub") or "")
        except (TypeError, ValueError):
            raise UnauthorizedError("验证链接无效或已过期") from None

        user = await db.get(UserModel, user_id)
        if user is None:
            raise UnauthorizedError("验证链接无效或已过期")
        if not bool(getattr(user, "is_email_verified", False)):
            user.is_email_verified = True
            await db.commit()
            await db.refresh(user)
            logger.info("邮箱验证通过 user_id=%s", user.id)
        return user

    async def build_current_user(self, db: AsyncSession, user: UserModel) -> dict:
        """组装当前用户信息（含角色 slug、权限码与菜单授权，供前端菜单/按钮权限使用）"""
        permissions = sorted(await rbac_service.get_permission_codes_set(db, user.id))
        roles = [role.slug for role in await rbac_service.get_user_roles(db, user.id)]

        # 菜单级授权（P3：后端管授权、前端管结构）。延迟导入避免模块加载环。
        from src.api.v3.modules.system.admin_menu.service import admin_menu_service

        menu_codes = await admin_menu_service.menu_codes_with_ancestors(
            db, user.id, is_superuser=bool(user.is_superuser)
        )

        return {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "email_verified": bool(getattr(user, "is_email_verified", True)),
            "is_active": bool(user.is_active),
            "is_staff": bool(user.is_staff),
            "is_superuser": bool(user.is_superuser),
            "vip_level": int(user.vip_level or 0),
            "locale": user.locale,
            "profile_picture": user.profile_picture,
            "roles": roles,
            "permissions": permissions,
            "menu_codes": menu_codes,
        }


auth_service = AuthService()
