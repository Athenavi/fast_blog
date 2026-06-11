"""
SSO 会话策略管理 API
提供会话策略的查询、更新以及活跃会话列表功能
"""
from functools import wraps

from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.system.system_settings import SystemSettings
from src.api.v2._helpers import ok, fail
from src.auth.auth_deps import jwt_required_dependency as jwt_required
from src.utils.database.main import get_async_session as get_async_db

router = APIRouter(tags=["session-policy"])

SESSION_POLICY_PREFIX = "session_policy_"


def _catch(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except HTTPException:
            raise
        except Exception as e:
            return fail(str(e))
    return wrapper


async def _require_superuser(current_user):
    """检查超级管理员权限"""
    if not getattr(current_user, 'is_superuser', False):
        raise HTTPException(status_code=403, detail="需要超级管理员权限")
    return current_user


async def _get_setting(db: AsyncSession, key: str, default_value=None):
    """从 SystemSettings 读取配置"""
    from sqlalchemy import select
    stmt = select(SystemSettings).where(SystemSettings.setting_key == key)
    result = await db.execute(stmt)
    setting = result.scalar_one_or_none()
    if setting:
        return setting.setting_value
    return default_value


async def _set_setting(db: AsyncSession, key: str, value: str, description: str = ""):
    """保存配置到 SystemSettings"""
    from sqlalchemy import select
    stmt = select(SystemSettings).where(SystemSettings.setting_key == key)
    result = await db.execute(stmt)
    setting = result.scalar_one_or_none()
    if setting:
        setting.setting_value = value
    else:
        import datetime
        setting = SystemSettings(
            setting_key=key,
            setting_value=value,
            setting_type='string',
            description=description,
            created_at=datetime.datetime.now(),
            updated_at=datetime.datetime.now(),
        )
        db.add(setting)
    await db.commit()
    return setting


@router.get("/integrations/session/policy", summary="获取当前会话策略设置")
@_catch
async def get_session_policy(
        current_user=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """获取当前会话策略设置（需要超级管理员权限）"""
    await _require_superuser(current_user)

    max_session_hours = await _get_setting(db, f"{SESSION_POLICY_PREFIX}max_session_hours", "24")
    max_concurrent_sessions = await _get_setting(db, f"{SESSION_POLICY_PREFIX}max_concurrent_sessions", "5")
    enforce_ip_binding = await _get_setting(db, f"{SESSION_POLICY_PREFIX}enforce_ip_binding", "false")
    enforce_device_fingerprint = await _get_setting(db, f"{SESSION_POLICY_PREFIX}enforce_device_fingerprint", "false")
    session_timeout_minutes = await _get_setting(db, f"{SESSION_POLICY_PREFIX}session_timeout_minutes", "30")

    return ok(data={
        'max_session_hours': int(max_session_hours),
        'max_concurrent_sessions': int(max_concurrent_sessions),
        'enforce_ip_binding': enforce_ip_binding.lower() == 'true' if isinstance(enforce_ip_binding, str) else bool(enforce_ip_binding),
        'enforce_device_fingerprint': enforce_device_fingerprint.lower() == 'true' if isinstance(enforce_device_fingerprint, str) else bool(enforce_device_fingerprint),
        'session_timeout_minutes': int(session_timeout_minutes),
    })


@router.put("/integrations/session/policy", summary="更新会话策略设置")
@_catch
async def update_session_policy(
        max_session_hours: int = Body(24, description="最大会话小时数"),
        max_concurrent_sessions: int = Body(5, description="最大并发会话数"),
        enforce_ip_binding: bool = Body(False, description="是否强制 IP 绑定"),
        enforce_device_fingerprint: bool = Body(False, description="是否强制设备指纹"),
        session_timeout_minutes: int = Body(30, description="会话超时分钟数"),
        current_user=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """更新会话策略设置（需要超级管理员权限）"""
    await _require_superuser(current_user)

    await _set_setting(db, f"{SESSION_POLICY_PREFIX}max_session_hours", str(max_session_hours), "最大会话小时数")
    await _set_setting(db, f"{SESSION_POLICY_PREFIX}max_concurrent_sessions", str(max_concurrent_sessions), "最大并发会话数")
    await _set_setting(db, f"{SESSION_POLICY_PREFIX}enforce_ip_binding", str(enforce_ip_binding).lower(), "是否强制 IP 绑定")
    await _set_setting(db, f"{SESSION_POLICY_PREFIX}enforce_device_fingerprint", str(enforce_device_fingerprint).lower(), "是否强制设备指纹")
    await _set_setting(db, f"{SESSION_POLICY_PREFIX}session_timeout_minutes", str(session_timeout_minutes), "会话超时分钟数")

    return ok(data={
        'max_session_hours': max_session_hours,
        'max_concurrent_sessions': max_concurrent_sessions,
        'enforce_ip_binding': enforce_ip_binding,
        'enforce_device_fingerprint': enforce_device_fingerprint,
        'session_timeout_minutes': session_timeout_minutes,
    }, msg="Session policy updated successfully")


@router.get("/integrations/session/active", summary="获取当前活跃会话列表")
@_catch
async def get_active_sessions(
        current_user=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """获取当前活跃会话列表（需要超级管理员权限）"""
    await _require_superuser(current_user)

    from sqlalchemy import select
    from shared.models.user.user_session import UserSession

    stmt = select(UserSession).where(
        UserSession.is_active == True
    ).order_by(UserSession.last_activity.desc()).limit(100)

    result = await db.execute(stmt)
    sessions = result.scalars().all()

    sessions_list = []
    for s in sessions:
        sessions_list.append({
            'id': s.id,
            'user_id': s.user_id,
            'device_info': s.device_info,
            'ip_address': s.ip_address,
            'last_activity': s.last_activity.isoformat() if s.last_activity else None,
            'expires_at': s.expires_at.isoformat() if s.expires_at else None,
            'created_at': s.created_at.isoformat() if s.created_at else None,
        })

    return ok(data={
        'sessions': sessions_list,
        'total': len(sessions_list),
    })
