"""
OAuth 第三方登录 API 端点
"""

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import create_access_token
from shared.services.oauth_service import oauth_service
from src.api.v1.responses import ApiResponse
from src.auth import jwt_required_dependency as jwt_required
from src.extensions import get_async_db_session as get_async_db

router = APIRouter(prefix="/oauth", tags=["oauth"])


@router.get("/providers")
async def list_oauth_providers():
    """获取支持的OAuth提供商列表"""
    try:
        providers = oauth_service.get_supported_providers()
        
        return ApiResponse(
            success=True,
            data={"providers": providers}
        )
    except Exception as e:
        return ApiResponse(success=False, error=str(e))


@router.get("/authorize/{provider}")
async def authorize(
    provider: str,
    request: Request,
    state: str = Query(..., description="CSRF状态")
):
    """
    生成OAuth授权URL
    
    Args:
        provider: 提供商名称 (github/google/wechat/qq/weibo)
        state: CSRF保护状态
        
    Returns:
        授权URL
    """
    try:
        # 从环境变量或配置获取client_id和redirect_uri
        import os
        
        client_id = os.getenv(f"OAUTH_{provider.upper()}_CLIENT_ID", "")
        redirect_uri = request.url_for("oauth_callback", provider=provider).__str__()
        
        if not client_id:
            return ApiResponse(
                success=False,
                error=f"未配置 {provider} 的 Client ID"
            )
        
        auth_url = oauth_service.get_authorization_url(
            provider=provider,
            client_id=client_id,
            redirect_uri=redirect_uri,
            state=state
        )
        
        return ApiResponse(
            success=True,
            data={
                "authorization_url": auth_url,
                "provider": provider
            }
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return ApiResponse(success=False, error=str(e))


@router.get("/callback/{provider}")
async def oauth_callback(
    provider: str,
    request: Request,
    code: str = Query(..., description="授权码"),
    state: str = Query(..., description="CSRF状态"),
    db: AsyncSession = Depends(get_async_db)
):
    """
    OAuth回调处理
    
    Args:
        provider: 提供商名称
        code: 授权码
        state: CSRF状态
        
    Returns:
        用户信息和JWT令牌
    """
    try:
        import os
        from src.extensions import cache
        
        # 验证state（防止CSRF攻击）
        if not state:
            return ApiResponse(success=False, error="缺少state参数")
        
        # 从 Redis 获取存储的 state
        stored_state = await cache.get(f"oauth_state:{state}")
        if not stored_state:
            return ApiResponse(success=False, error="state已过期或无效")
        
        # 验证后删除state(一次性使用)
        await cache.delete(f"oauth_state:{state}")
        
        # 获取配置
        client_id = os.getenv(f"OAUTH_{provider.upper()}_CLIENT_ID", "")
        client_secret = os.getenv(f"OAUTH_{provider.upper()}_CLIENT_SECRET", "")
        redirect_uri = request.url_for("oauth_callback", provider=provider).__str__()
        
        if not client_id or not client_secret:
            return ApiResponse(
                success=False,
                error=f"未配置 {provider} 的凭证"
            )
        
        # 交换授权码为访问令牌
        token_result = await oauth_service.exchange_code_for_token(
            provider=provider,
            code=code,
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri
        )
        
        if not token_result["success"]:
            return ApiResponse(
                success=False,
                error=token_result["error"]
            )
        
        access_token = token_result["access_token"]
        
        # 获取用户信息
        user_result = await oauth_service.get_user_info(
            provider=provider,
            access_token=access_token
        )
        
        if not user_result["success"]:
            return ApiResponse(
                success=False,
                error=user_result["error"]
            )
        
        user_info = user_result["user"]
        
        # 1. 检查用户是否已存在（根据provider + provider_id）
        from shared.models import OAuthAccount
        from shared.models import User
        from sqlalchemy import select
        from datetime import datetime
        
        stmt = select(OAuthAccount).where(
            OAuthAccount.provider == provider,
            OAuthAccount.provider_user_id == user_info.get('id')
        )
        result = await db.execute(stmt)
        oauth_account = result.scalar_one_or_none()
        
        if oauth_account:
            # 2. 如果存在，获取关联的用户
            stmt = select(User).where(User.id == oauth_account.user_id)
            result = await db.execute(stmt)
            user = result.scalar_one_or_none()
            
            if not user:
                return ApiResponse(success=False, error="用户不存在")
        else:
            # 3. 如果不存在，创建新用户
            # 检查邮箱是否已存在
            email = user_info.get('email', '')
            if email:
                stmt = select(User).where(User.email == email)
                result = await db.execute(stmt)
                existing_user = result.scalar_one_or_none()
                
                if existing_user:
                    user = existing_user
                else:
                    # 创建新用户
                    user = User(
                        username=user_info.get('username', f"{provider}_{user_info.get('id')}"),
                        email=email,
                        nickname=user_info.get('name', ''),
                        avatar_url=user_info.get('avatar', ''),
                        is_active=True,
                        created_at=datetime.utcnow()
                    )
                    db.add(user)
                    await db.flush()  # 获取user.id
            else:
                return ApiResponse(success=False, error="未获取到邮箱信息")
            
            # 创建OAuth关联记录
            oauth_account = OAuthAccount(
                user_id=user.id,
                provider=provider,
                provider_user_id=str(user_info.get('id')),
                access_token=access_token,
                created_at=datetime.utcnow()
            )
            db.add(oauth_account)
        
        await db.commit()
        
        # 4. 生成JWT令牌
        jwt_token = create_access_token(data={"sub": str(user.id)})
        
        # 临时返回用户信息
        return ApiResponse(
            success=True,
            message=f"{provider} 登录成功",
            data={
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "nickname": user.nickname,
                    "avatar_url": user.avatar_url
                },
                "access_token": jwt_token,
                "token_type": "Bearer"
            }
        )
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return ApiResponse(success=False, error=str(e))


@router.post("/unlink/{provider}")
async def unlink_oauth_account(
    provider: str,
    current_user=Depends(jwt_required),
    db: AsyncSession = Depends(get_async_db)
):
    """
    解绑OAuth账号
    
    Args:
        provider: 提供商名称
        
    Returns:
        解绑结果
    """
    try:
        from shared.models import OAuthAccount, User
        from sqlalchemy import select, func
        
        # 1. 从数据库中删除用户的OAuth关联
        stmt = select(OAuthAccount).where(
            OAuthAccount.user_id == current_user.id,
            OAuthAccount.provider == provider
        )
        result = await db.execute(stmt)
        oauth_account = result.scalar_one_or_none()
        
        if not oauth_account:
            return ApiResponse(success=False, error=f"未绑定 {provider} 账号")
        
        # 2. 确保用户至少有一个登录方式
        # 检查是否还有其他OAuth账号或密码
        stmt = select(func.count(OAuthAccount.id)).where(
            OAuthAccount.user_id == current_user.id
        )
        result = await db.execute(stmt)
        oauth_count = result.scalar() or 0
        
        # 检查是否有密码
        user_stmt = select(User).where(User.id == current_user.id)
        user_result = await db.execute(user_stmt)
        user = user_result.scalar_one_or_none()
        
        has_password = user and user.password_hash
        
        # 如果只有这一个OAuth账号且没有密码，不允许解绑
        if oauth_count <= 1 and not has_password:
            return ApiResponse(
                success=False, 
                error="至少需要保留一个登录方式，请先设置密码"
            )
        
        # 删除OAuth关联
        await db.delete(oauth_account)
        await db.commit()
        
        return ApiResponse(
            success=True,
            message=f"已解绑 {provider} 账号"
        )
    except Exception as e:
        return ApiResponse(success=False, error=str(e))
