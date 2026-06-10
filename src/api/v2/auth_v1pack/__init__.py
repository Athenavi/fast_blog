"""
认证 API - V2 原生实现

整合 JWT 登录/注册/验证码/登出/token刷新
优化: _catch 统一处理 13 处重复 try/except
"""
import re
import uuid
from datetime import datetime, timedelta, timezone
from functools import wraps
from typing import Optional

import jwt
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse
from jwt.exceptions import InvalidTokenError
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.user import User as UserModel
from shared.services.users.email_verification_service import email_verification_service
from shared.services.users.login_security_service import login_security_service
from shared.services.users.session_management_service import session_management_service
from shared.services.users.sms_verification_service import sms_verification_service
from shared.services.users.user_manager import create_user_account
from src.api.v2._base import ApiResponse
from src.api.v2._helpers import ok, fail
from src.auth.auth_deps import jwt_required_dependency as jwt_required
from src.extensions import get_async_db_session as get_async_db
from src.setting import settings
from src.unified_logger import default_logger as logger


_tb_instance = None


def _get_token_blacklist():
    global _tb_instance
    if _tb_instance is None:
        from src.utils.token_blacklist import token_blacklist
        _tb_instance = token_blacklist
    return _tb_instance


def _catch(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"[{func.__name__}] {e}")
            return fail(str(e))
    return wrapper


router = APIRouter(tags=["auth"])


# ─── 请求模型 ───

class LoginRequest(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None
    password: str
    remember_me: Optional[bool] = False


class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str


# ─── JWT 工具函数 ───

async def authenticate_user_with_session(username_or_email: str, password: str, db: AsyncSession) -> Optional[UserModel]:
    from src.utils.security.password_validator import verify_password
    user = await db.scalar(select(UserModel).where(
        (UserModel.username == username_or_email) | (UserModel.email == username_or_email)))
    if not user or not user.password:
        return None
    return user if verify_password(password, user.password) else None


def create_jwt_token(subject: str, token_type: str = "access", expires_delta: Optional[timedelta] = None) -> str:
    now = datetime.now(timezone.utc)
    if expires_delta is None:
        expires_delta = timedelta(seconds=settings.JWT_EXPIRATION_DELTA if token_type == "access" else settings.REFRESH_TOKEN_EXPIRATION_DELTA)
    payload = {"sub": subject, "iat": now, "exp": now + expires_delta, "jti": str(uuid.uuid4()), "type": token_type}
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_jwt_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM], options={"verify_exp": True})
        jti = payload.get("jti")
        tb = _get_token_blacklist()
        if jti and tb.is_available and tb.is_blacklisted(jti):
            raise HTTPException(401, "Token has been revoked")
        return payload
    except InvalidTokenError as e:
        raise HTTPException(401, f"Invalid token: {e}")


def extract_token_from_request(request: Request) -> Optional[str]:
    auth = request.headers.get("Authorization")
    if auth and auth.startswith("Bearer "):
        return auth[7:]
    return request.cookies.get("access_token") or request.cookies.get("access_token_cookie")


# ─── 用户名/邮箱检查 ───

@router.get("/check-username")
@_catch
async def check_username(username: str = Query(...), db: AsyncSession = Depends(get_async_db)):
    existing = await db.scalar(select(UserModel).where(func.lower(UserModel.username) == func.lower(username)))
    return JSONResponse({"success": True, "available": existing is None, "exists": existing is not None})


@router.get("/check-email")
@_catch
async def check_email(email: str = Query(...), db: AsyncSession = Depends(get_async_db)):
    existing = await db.scalar(select(UserModel).where(func.lower(UserModel.email) == func.lower(email)))
    return JSONResponse({"success": True, "available": existing is None, "exists": existing is not None})


@router.get('/status')
@_catch
async def check_login_status(current_user=Depends(jwt_required)):
    return {'logged_in': True, 'user_id': current_user.id if hasattr(current_user, 'id') else None}


# ─── 登录 ───

@router.post("/login")
@_catch
async def login_api(request: Request, db: AsyncSession = Depends(get_async_db)):
    ct = request.headers.get('content-type', '')
    if 'application/json' in ct:
        body = await request.json()
        username = body.get('username') or body.get('email')
        password = body.get('password')
        remember_me = body.get('remember_me') or body.get('rememberMe', False)
    else:
        form = await request.form()
        username = form.get('username') or form.get('email')
        password = form.get('password')
        raw = form.get('remember_me')
        remember_me = str(raw).lower() in ('true', '1', 'on') if raw is not None else False

    if not username or not password:
        return fail("缺少用户名或密码")

    ip = request.client.host if request.client else "unknown"
    ua = request.headers.get("user-agent", "")

    locked, unlock_time = await login_security_service.check_account_locked_async(username, db)
    if locked:
        await login_security_service.record_login_attempt_async(username, ip, ua, False,
            "Account locked", db)
        mins = (unlock_time - datetime.now()).total_seconds() / 60
        return fail(f"账户已锁定，请 {mins:.0f} 分钟后再试")

    user = await authenticate_user_with_session(username, password, db)
    if not user:
        await login_security_service.record_login_attempt_async(username, ip, ua, False, "Invalid credentials", db)
        return fail("用户名或密码错误")

    await login_security_service.record_login_attempt_async(username, ip, ua, True, db=db)
    await login_security_service.clear_failed_attempts_async(username, db)

    if not user.is_active:
        return fail("账户已停用")

    access_token = create_jwt_token(subject=str(user.id), token_type="access")
    refresh_token = create_jwt_token(subject=str(user.id), token_type="refresh") if remember_me else None

    session_management_service.create_session(user.id, {"ip": ip, "user_agent": ua}, ip, ua)

    resp_data = {"access_token": access_token, "token_type": "bearer"}
    if refresh_token:
        resp_data["refresh_token"] = refresh_token

    resp = JSONResponse(content={"success": True, "data": resp_data})
    is_https = str(settings.SITE_URL).startswith('https://') if hasattr(settings, 'SITE_URL') else False
    resp.set_cookie("access_token", access_token, httponly=True, secure=is_https, samesite="strict", max_age=3600)
    if refresh_token:
        resp.set_cookie("refresh_token", refresh_token, httponly=True, secure=is_https, samesite="strict", max_age=2592000)
    return resp


# ─── 注册 ───

@router.post("/register")
@_catch
async def register_api(data: RegisterRequest, request: Request, db: AsyncSession = Depends(get_async_db)):
    if not re.match(r'^[a-zA-Z0-9_]+$', data.username):
        return fail("用户名只能包含字母、数字和下划线")
    if len(data.username) < 3 or len(data.username) > 30:
        return fail("用户名长度需在 3-30 字符之间")

    existing = await db.scalar(select(UserModel).where(
        (UserModel.username == data.username) | (UserModel.email == data.email)))
    if existing:
        return fail("用户名或邮箱已被注册")

    try:
        user = await create_user_account(username=data.username, email=data.email, password=data.password, db=db)
    except Exception as e:
        return fail(f"注册失败: {e}")

    access_token = create_jwt_token(subject=str(user.id), token_type="access")
    refresh_token = create_jwt_token(subject=str(user.id), token_type="refresh")

    resp = JSONResponse(content={"success": True, "data": {"access_token": access_token, "refresh_token": refresh_token}})
    is_https = str(settings.SITE_URL).startswith('https://') if hasattr(settings, 'SITE_URL') else False
    resp.set_cookie("access_token", access_token, httponly=True, secure=is_https, samesite="strict", max_age=3600)
    resp.set_cookie("refresh_token", refresh_token, httponly=True, secure=is_https, samesite="strict", max_age=2592000)
    return resp


# ─── 邮箱验证码 ───

@router.post("/email/send-code")
@_catch
async def send_email_verification_code(data: dict, current_user=Depends(jwt_required)):
    result = await email_verification_service.send_verification_code(current_user.id, data.get('email', ''))
    return ok(data=result, msg="验证码已发送")


@router.post("/email/verify-code")
@_catch
async def verify_email_code(data: dict, current_user=Depends(jwt_required)):
    result = email_verification_service.verify_code(current_user.id, data.get('code', ''))
    if not result:
        return fail("验证码无效或已过期")
    return ok(msg="邮箱验证成功")


# ─── 短信验证码 ───

@router.post("/sms/send-code")
@_catch
async def send_sms_verification_code(data: dict, current_user=Depends(jwt_required)):
    result = await sms_verification_service.send_verification_code(current_user.id, data.get('phone', ''))
    return ok(data=result, msg="验证码已发送")


@router.post("/sms/verify-code")
@_catch
async def verify_sms_code(data: dict, current_user=Depends(jwt_required)):
    result = sms_verification_service.verify_code(current_user.id, data.get('code', ''))
    if not result:
        return fail("验证码无效或已过期")
    return ok(msg="验证成功")


# ─── 登出 ───

@router.post("/logout")
@_catch
async def logout_api(request: Request, current_user=Depends(jwt_required)):
    tb = _get_token_blacklist()
    token = extract_token_from_request(request)
    if token and tb.is_available:
        try:
            payload = decode_jwt_token(token)
            tb.blacklist(payload['jti'], payload['exp'])
            session_management_service.revoke_all_sessions(current_user.id)
        except Exception:
            pass
    resp = JSONResponse(content={"success": True, "message": "已登出"})
    resp.delete_cookie("access_token")
    resp.delete_cookie("refresh_token")
    return resp


# ─── Token 刷新 ───

@router.post("/token/refresh")
@_catch
async def refresh_token_api(request: Request):
    refresh_token = extract_token_from_request(request)
    if not refresh_token:
        return fail("未提供刷新令牌")

    try:
        payload = decode_jwt_token(refresh_token)
    except HTTPException:
        return fail("刷新令牌无效或已过期")

    if payload.get('type') != 'refresh':
        return fail("令牌类型错误")

    new_access = create_jwt_token(subject=payload['sub'], token_type="access")
    new_refresh = create_jwt_token(subject=payload['sub'], token_type="refresh")

    resp = JSONResponse(content={"success": True, "data": {"access_token": new_access, "refresh_token": new_refresh}})
    is_https = str(settings.SITE_URL).startswith('https://') if hasattr(settings, 'SITE_URL') else False
    resp.set_cookie("access_token", new_access, httponly=True, secure=is_https, samesite="strict", max_age=3600)
    resp.set_cookie("refresh_token", new_refresh, httponly=True, secure=is_https, samesite="strict", max_age=2592000)
    return resp
