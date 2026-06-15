"""
SSO单点登录 API
提供OAuth2.0、SAML和LDAP认证功能
"""
from functools import wraps
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Body, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from shared.services.integrations.sso_service import sso_service
from src.api.v2._helpers import ok, fail
from src.auth.auth_deps import jwt_required_dependency as jwt_required
from src.extensions import get_async_db_session as get_async_db

router = APIRouter(tags=["sso"])


def _catch(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except HTTPException:
            raise
        except Exception as e:
            import traceback
            traceback.print_exc()
            return fail(str(e))
    return wrapper


# ==================== OAuth2.0 ====================

@router.get("/oauth/{provider}/authorize", summary="OAuth2授权")
@_catch
async def oauth_authorize(
        provider: str,
        redirect_uri: str = Query(..., description="回调URL"),
        state: Optional[str] = Query(None, description="状态参数"),
        request: Request = None,
):
    """
    获取OAuth2授权URL并重定向
    
    Args:
        provider: OAuth提供商 (google/github/microsoft)
        redirect_uri: 回调URL
        state: 状态参数
        
    Returns:
        重定向到OAuth提供商
    """
    # SECURITY: Validate redirect_uri against the app's own callback URL
    # to prevent open-redirect attacks (Fix 2).
    if request:
        base_url = str(request.base_url).rstrip('/')
        expected_callback = f"{base_url}/api/v2/sso/oauth/{provider}/callback"
        if redirect_uri != expected_callback and not redirect_uri.startswith(expected_callback + '?'):
            raise HTTPException(status_code=400, detail="Invalid redirect_uri: not in whitelist")

    authorization_url = await sso_service.get_oauth_authorization_url(
        provider=provider,
        redirect_uri=redirect_uri,
        state=state
    )

    return RedirectResponse(url=authorization_url)


@router.post("/oauth/{provider}/callback", summary="OAuth2回调处理")
@_catch
async def oauth_callback(
        provider: str,
        code: str = Body(..., description="授权码"),
        redirect_uri: str = Body(..., description="回调URL"),
        state: Optional[str] = Body(None, description="状态参数"),
        request: Request = None,
        db: AsyncSession = Depends(get_async_db)
):
    """
    处理OAuth2回调
    
    Args:
        provider: OAuth提供商
        code: 授权码
        redirect_uri: 回调URL
        state: 状态参数
        
    Returns:
        用户信息和令牌
    """
    # SECURITY: Validate state parameter to prevent CSRF account takeover.
    # In production, state should be generated during /authorize, stored in
    # session, and validated here. At minimum, ensure it's non-empty.
    if not state:
        raise HTTPException(status_code=400, detail="Missing or empty 'state' parameter (CSRF protection)")

    # SECURITY: Validate Origin / Referer header as additional check
    if request:
        origin = request.headers.get("origin")
        referer = request.headers.get("referer")
        if origin or referer:
            # Both should match the application's own base URL
            base_url = str(request.base_url).rstrip('/')
            allowed = False
            for header_val in [origin, referer]:
                if header_val and (header_val.rstrip('/') == base_url or header_val.startswith(base_url + '/')):
                    allowed = True
                    break
            if not allowed:
                raise HTTPException(status_code=403, detail="Cross-origin request denied")

    result = await sso_service.handle_oauth_callback(
        db=db,
        provider=provider,
        code=code,
        redirect_uri=redirect_uri
    )

    # 生成JWT令牌
    from src.auth import create_access_token
    jwt_token = create_access_token(user_id=result['user'].id)

    return ok(
        data={
            'access_token': jwt_token,
            'token_type': 'Bearer',
            'user_id': result['user'].id,
            'username': result['user'].username,
            'email': result['user'].email,
            'provider': result['provider'],
        },
        msg="OAuth authentication successful"
    )


@router.get("/oauth/providers", summary="获取支持的OAuth提供商")
@_catch
async def get_oauth_providers():
    """
    获取所有支持的OAuth提供商列表
    
    Returns:
        提供商列表
    """
    providers = []
    for name, config in sso_service.oauth_providers.items():
        if config.get('client_id'):  # 只返回已配置的提供商
            providers.append({
                'name': name,
                'display_name': name.title(),
                'configured': True,
            })
        else:
            providers.append({
                'name': name,
                'display_name': name.title(),
                'configured': False,
            })

    return ok(
        data={
            'providers': providers,
            'total': len(providers)
        }
    )


# ==================== LDAP ====================

@router.post("/ldap/authenticate", summary="LDAP认证")
@_catch
async def ldap_authenticate(
        username: str = Body(..., description="用户名"),
        password: str = Body(..., description="密码"),
        db: AsyncSession = Depends(get_async_db)
):
    """
    LDAP认证
    
    Args:
        username: 用户名
        password: 密码
        
    Returns:
        认证结果
    """
    userinfo = await sso_service.authenticate_ldap(username, password)

    if not userinfo:
        return fail("Invalid credentials")

    # 查找或创建用户
    from sqlalchemy import select
    from shared.models.user import User

    stmt = select(User).where(User.email == userinfo.get('email'))
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        # 创建新用户
        user = User(
            username=userinfo['username'],
            email=userinfo.get('email') or f"{userinfo['username']}@company.com",
            password='',  # LDAP用户不需要本地密码
            is_active=True,
            auth_method='ldap',
        )

        db.add(user)
        await db.commit()
        await db.refresh(user)

        logger.info(f"New user created via LDAP: {userinfo['username']}")

    # 生成JWT令牌
    from src.auth import create_access_token
    jwt_token = create_access_token(user_id=user.id)

    return ok(
        data={
            'access_token': jwt_token,
            'token_type': 'Bearer',
            'user_id': user.id,
            'username': user.username,
            'email': user.email,
            'auth_method': 'ldap',
        },
        msg="LDAP authentication successful"
    )


# ==================== SAML ====================

@router.get("/saml/login", summary="SAML登录")
@_catch
async def saml_login():
    """
    发起SAML登录请求
    
    Returns:
        SAML登录请求数据
    """
    raise HTTPException(
        status_code=501,
        detail="SAML login endpoint is not implemented yet. "
               "A full SAML implementation requires "
               "python3-saml / signxml integration."
    )


@router.post("/saml/acs", summary="SAML断言消费者服务")
@_catch
async def saml_acs(
        saml_response: str = Body(..., description="SAML响应"),
        db: AsyncSession = Depends(get_async_db)
):
    """
    处理SAML响应（ACS端点）
    
    Args:
        saml_response: SAML响应数据
        
    Returns:
        认证结果
    """
    # SAML ACS is not yet implemented. This endpoint returns 501 explicitly
    # to avoid silent failures that could mask security issues.
    raise HTTPException(
        status_code=501,
        detail="SAML ACS endpoint is not implemented yet. "
               "A full SAML implementation requires: "
               "1) Onelogin python3-saml integration "
               "2) Certificate validation "
               "3) Attribute mapping "
               "4) Session management."
    )


# ==================== SSO会话管理 ====================

@router.post("/session/create", summary="创建SSO会话")
@_catch
async def create_sso_session(
        user_id: int = Body(..., description="用户ID"),
        session_id: str = Body(..., description="会话ID"),
        current_user=Depends(jwt_required)
):
    """
    创建SSO会话（仅管理员或本人可操作）
    """
    # 仅允许管理员或自己
    is_admin = getattr(current_user, 'is_superuser', False) or getattr(current_user, 'is_staff', False)
    if current_user.id != user_id and not is_admin:
        return fail("无权为此用户创建SSO会话")
    sso_token = await sso_service.create_sso_session(user_id, session_id)

    return ok(
        data={
            'sso_token': sso_token,
            'user_id': user_id,
        },
        msg="SSO session created"
    )


@router.post("/session/validate", summary="验证SSO令牌")
@_catch
async def validate_sso_token(
        sso_token: str = Body(..., description="SSO令牌"),
):
    """
    验证SSO令牌
    
    Args:
        sso_token: SSO令牌
        
    Returns:
        验证结果
    """
    user_id = await sso_service.validate_sso_token(sso_token)

    if not user_id:
        return fail("Invalid or expired SSO token")

    return ok(
        data={
            'valid': True,
            'user_id': user_id,
        }
    )


# ==================== 配置管理 ====================

@router.get("/config", summary="获取SSO配置状态")
@_catch
async def get_sso_config(current_user=Depends(jwt_required)):
    """
    获取SSO配置状态
    
    Returns:
        配置状态
    """
    config = {
        'oauth': {
            'google': bool(sso_service.oauth_providers['google']['client_id']),
            'github': bool(sso_service.oauth_providers['github']['client_id']),
            'microsoft': bool(sso_service.oauth_providers['microsoft']['client_id']),
        },
        'saml': bool(sso_service.saml_config['entity_id']),
        'ldap': bool(sso_service.ldap_config['server']),
    }

    return ok(data=config)


# 导入logger

from src.unified_logger import default_logger as logger
