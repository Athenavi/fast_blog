"""oauth 模块业务逻辑：OAuth 第三方登录（接线自 ``shared/services/integrations/oauth_service.py``）

**纯函数与 DB/网络操作分离**（本模块不新建 ``crud.py``，交付物为固定五件套；DB 访问集中在
``OAuthService``）。

| 源服务（``OAuthService``） | 本模块 |
|---|---|
| provider 表写在实例属性 ``self.providers`` | 提升为模块级常量 ``PROVIDERS``（可测、可复用） |
| 授权 URL 用外部传入的 ``client_id`` / ``redirect_uri`` | 从 ``system_settings`` 读配置；``build_authorize_url`` 为纯函数 |
| **没有** ``state`` 校验（只透传） | ``generate_state`` / ``verify_state``：HMAC-SHA256 签名 + 过期，纯函数、无服务端存储 |
| **没有** PKCE | ``generate_code_verifier`` / ``code_challenge_s256``（S256），纯函数 |
| 交换 token / 拉用户信息用 ``httpx``（真实） | 保留真实 ``httpx`` 调用；**配置缺失即如实报"未配置"，不伪造成功** |
| 只返回标准化用户信息，不含"绑定/建号/登录态" | 真实写 ``oauth_accounts`` + 关联/新建 ``users`` + 复用 ``auth_service.grant_tokens`` 签发登录态 |

**如实降级点**（无新表、无新 ORM）：

  1. **凭据来源**：源服务靠调用方传参；本模块改为读 ``system_settings`` 的 JSON 键
     ``oauth.providers``（结构见 ``PROVIDERS_SETTING_KEY``）。该键**不在**任何 alembic 迁移里，
     是运行期按需写入的配置项（与 ``security.anomaly.thresholds`` 等既有约定一致）。
  2. **token 落库**：``oauth_accounts.access_token`` / ``refresh_token`` / ``extra_data`` 均为
     ``String(255)``。超长时按 ``_clip`` **截断并记警告**——截断值只用于"是否已绑定"的判断，
     不作为对外调用凭据（本模块不代第三方调用业务接口）。
  3. **``client_secret`` 在本配置中按明文 JSON 存储**（未加密）——读取方仅服务端。

**根因对比 v2**：v2 仓库内**没有**任何 OAuth 登录端点（只有 ``shared/services`` 里的这个进程内服务），
因此本模块是**新接线**而非返工；能力边界以源服务为准（GitHub / Google / 微信 / QQ / 微博）。
"""

import base64
import hashlib
import hmac
import json
import re
import secrets
import time
from datetime import datetime, timedelta
from typing import Any, Optional
from urllib.parse import parse_qs, urlencode

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.config.settings import settings
from shared.models.user import OAuthAccount, User
from src.api.v3.core.exceptions import BadRequestError, NotFoundError
from src.api.v3.core.logger import get_logger
from src.api.v3.modules.system.setting.crud import setting_crud

logger = get_logger("system.oauth")

#: ``system_settings`` 中承载 OAuth 凭据的 JSON 键
PROVIDERS_SETTING_KEY = "oauth.providers"
#: state 有效期（秒）
STATE_TTL_SECONDS = 600
#: 外部调用超时（秒）
DEFAULT_TIMEOUT = 30.0
#: 调厂商接口时的 UA（GitHub 强制要求非空 User-Agent）
USER_AGENT = "FastBlog-OAuth/1.0"

#: 各提供方的官方端点与元数据（与源服务 ``OAuthService.providers`` 逐字一致）
PROVIDERS: dict[str, dict[str, str]] = {
    "github": {
        "name": "GitHub",
        "authorize_url": "https://github.com/login/oauth/authorize",
        "token_url": "https://github.com/login/oauth/access_token",
        "user_info_url": "https://api.github.com/user",
        "scope": "user:email",
        "icon": "github",
    },
    "google": {
        "name": "Google",
        "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "user_info_url": "https://www.googleapis.com/oauth2/v3/userinfo",
        "scope": "openid profile email",
        "icon": "google",
    },
    "wechat": {
        "name": "微信",
        "authorize_url": "https://open.weixin.qq.com/connect/qrconnect",
        "token_url": "https://api.weixin.qq.com/sns/oauth2/access_token",
        "user_info_url": "https://api.weixin.qq.com/sns/userinfo",
        "scope": "snsapi_login",
        "icon": "wechat",
    },
    "qq": {
        "name": "QQ",
        "authorize_url": "https://graph.qq.com/oauth2.0/authorize",
        "token_url": "https://graph.qq.com/oauth2.0/token",
        "user_info_url": "https://graph.qq.com/user/get_user_info",
        "scope": "get_user_info",
        "icon": "qq",
    },
    "weibo": {
        "name": "微博",
        "authorize_url": "https://api.weibo.com/oauth2/authorize",
        "token_url": "https://api.weibo.com/oauth2/access_token",
        "user_info_url": "https://api.weibo.com/2/users/show.json",
        "scope": "email",
        "icon": "weibo",
    },
}

#: 支持标准 PKCE（RFC 7636）的提供方；微信 / QQ / 微博走各自的非标准流程，不附加 code_challenge
PKCE_PROVIDERS = frozenset({"github", "google"})


# =====================================================================================
# 纯函数（无 DB / 无网络；可被 ``_pending_test_oauth.py`` 直接单测）
# =====================================================================================
def get_provider(provider: str) -> Optional[dict[str, str]]:
    """取提供方元数据；不支持返回 ``None``（纯函数）"""
    return PROVIDERS.get(str(provider or "").strip().lower())


def require_provider(provider: str) -> dict[str, str]:
    """取提供方元数据；不支持抛 ``BadRequestError``（纯函数）"""
    meta = get_provider(provider)
    if meta is None:
        raise BadRequestError(f"不支持的 OAuth 提供方：{provider}（支持：{', '.join(PROVIDERS)}）")
    return meta


def _sign(payload: str, secret: str) -> str:
    """对载荷做 HMAC-SHA256 并做 base64url（去 padding，纯函数）"""
    digest = hmac.new(secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def generate_state(
    provider: str,
    secret: str,
    *,
    ttl_seconds: int = STATE_TTL_SECONDS,
    now: Optional[float] = None,
) -> str:
    """生成带签名与签发时间的 ``state``（纯函数）

    格式 ``"{provider}:{issued_at}:{nonce}:{signature}"``。无需服务端存储即可校验
    （签名 + 过期 + 提供方一致性），避免了源服务"state 只透传、不校验"的 CSRF 缺陷。
    """
    norm = str(provider or "").strip().lower()
    issued = int(now if now is not None else time.time())
    nonce = secrets.token_urlsafe(12)
    payload = f"{norm}:{issued}:{nonce}"
    return f"{payload}:{_sign(payload, secret)}"


def verify_state(
    state: str,
    provider: str,
    secret: str,
    *,
    ttl_seconds: int = STATE_TTL_SECONDS,
    now: Optional[float] = None,
) -> bool:
    """校验 ``state``：结构、提供方一致、签名、有效期（纯函数，返回布尔）"""
    if not state or not isinstance(state, str):
        return False
    parts = state.split(":")
    if len(parts) != 4:
        return False
    prov, issued_raw, nonce, signature = parts
    if prov != str(provider or "").strip().lower():
        return False
    payload = f"{prov}:{issued_raw}:{nonce}"
    if not hmac.compare_digest(signature, _sign(payload, secret)):
        return False
    try:
        issued = int(issued_raw)
    except (TypeError, ValueError):
        return False
    current = int(now if now is not None else time.time())
    if issued > current + 60:  # 容忍时钟偏移
        return False
    return (current - issued) <= int(ttl_seconds)


def generate_code_verifier(length: int = 64) -> str:
    """生成 PKCE ``code_verifier``（纯函数）

    RFC 7636 要求 43–128 个 ``[A-Za-z0-9-._~]`` 字符；``secrets.token_urlsafe`` 产出 base64url
    字符集（``A-Za-z0-9-_``）且不含 ``:``，可直接用于签名 state / 表单。
    """
    size = max(43, min(int(length), 128))
    # token_urlsafe(n) 约产出 ceil(4n/3) 个字符；反推出需要的字节数
    nbytes = max(32, (size * 3 + 3) // 4)
    return secrets.token_urlsafe(nbytes)[:size]


def code_challenge_s256(verifier: str) -> str:
    """计算 PKCE ``code_challenge`` = ``BASE64URL(SHA256(verifier))``（去 padding，纯函数）"""
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def build_authorize_url(
    provider: str,
    client_id: str,
    redirect_uri: str,
    state: str,
    *,
    code_challenge: Optional[str] = None,
) -> str:
    """构造授权跳转 URL（纯函数）

    与源服务逐字一致地拼接 ``response_type`` / ``scope`` / ``state`` / ``redirect_uri``；
    微信按官方要求用 ``appid`` 取代 ``client_id`` 并追加 ``#wechat_redirect`` 片段；
    支持 PKCE 的提供方（``PKCE_PROVIDERS``）在传入 ``code_challenge`` 时附加
    ``code_challenge`` 与 ``code_challenge_method=S256``。
    """
    config = require_provider(provider)
    params: dict[str, str] = {
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "scope": config["scope"],
        "state": state,
    }
    if provider == "wechat":
        params["appid"] = client_id
    else:
        params["client_id"] = client_id
    if code_challenge and provider in PKCE_PROVIDERS:
        params["code_challenge"] = code_challenge
        params["code_challenge_method"] = "S256"
    url = f"{config['authorize_url']}?{urlencode(params)}"
    if provider == "wechat":
        url += "#wechat_redirect"
    return url


def build_token_request(
    provider: str,
    code: str,
    client_id: str,
    client_secret: str,
    redirect_uri: str,
    *,
    code_verifier: Optional[str] = None,
) -> dict[str, str]:
    """构造"授权码换令牌"的请求体（纯函数，供真实 ``httpx`` 调用使用）

    微信按官方要求用 ``appid`` / ``secret``；QQ 追加 ``fmt=json`` 以便返回 JSON；
    支持 PKCE 的提供方带上 ``code_verifier``。
    """
    require_provider(provider)
    data: dict[str, str] = {"grant_type": "authorization_code", "code": code}
    if provider == "wechat":
        data["appid"] = client_id
        data["secret"] = client_secret
    else:
        data["client_id"] = client_id
        data["client_secret"] = client_secret
        data["redirect_uri"] = redirect_uri
        if provider == "qq":
            data["fmt"] = "json"
    if code_verifier and provider in PKCE_PROVIDERS:
        data["code_verifier"] = code_verifier
    return data


def normalize_user_info(provider: str, raw_data: dict) -> dict[str, Any]:
    """把各提供方差异化的用户信息标准化（纯函数，逻辑与源服务 ``_normalize_user_info`` 一致）"""
    raw = raw_data or {}
    if provider == "github":
        return {
            "provider": "github",
            "provider_id": str(raw.get("id")),
            "username": raw.get("login"),
            "email": raw.get("email"),
            "name": raw.get("name") or raw.get("login"),
            "avatar": raw.get("avatar_url"),
            "profile_url": raw.get("html_url"),
        }
    if provider == "google":
        return {
            "provider": "google",
            "provider_id": raw.get("sub"),
            "username": raw.get("email"),
            "email": raw.get("email"),
            "name": raw.get("name"),
            "avatar": raw.get("picture"),
            "profile_url": None,
        }
    if provider == "wechat":
        return {
            "provider": "wechat",
            "provider_id": raw.get("unionid") or raw.get("openid"),
            "username": raw.get("nickname"),
            "email": None,  # 微信不提供邮箱
            "name": raw.get("nickname"),
            "avatar": raw.get("headimgurl"),
            "profile_url": None,
        }
    if provider == "qq":
        return {
            "provider": "qq",
            "provider_id": raw.get("openid"),
            "username": raw.get("nickname"),
            "email": None,  # QQ 不直接提供邮箱
            "name": raw.get("nickname"),
            "avatar": raw.get("figureurl_qq_2"),
            "profile_url": None,
        }
    if provider == "weibo":
        return {
            "provider": "weibo",
            "provider_id": str(raw.get("id")),
            "username": raw.get("screen_name"),
            "email": raw.get("email"),
            "name": raw.get("screen_name"),
            "avatar": raw.get("avatar_large"),
            "profile_url": f"https://weibo.com/{raw.get('profile_url', '')}",
        }
    return dict(raw)


def parse_providers_config(setting_value: Optional[str]) -> dict[str, Any]:
    """把 ``system_settings`` 里的字符串值解析成配置字典（纯函数；损坏即回退空字典）"""
    if not setting_value:
        return {}
    try:
        parsed = json.loads(setting_value)
    except (TypeError, ValueError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def provider_credentials(config: dict[str, Any], provider: str) -> Optional[dict[str, str]]:
    """从配置字典取出某提供方的凭据（纯函数）

    结构：``{"github": {"client_id": "...", "client_secret": "...", "redirect_uri": "..."}}``。
    ``client_id`` / ``client_secret`` 任一缺失即视为**未配置**，返回 ``None``。
    """
    if not isinstance(config, dict):
        return None
    entry = config.get(str(provider or "").strip().lower())
    if not isinstance(entry, dict):
        return None
    client_id = str(entry.get("client_id") or "").strip()
    client_secret = str(entry.get("client_secret") or "").strip()
    if not client_id or not client_secret:
        return None
    redirect_uri = str(entry.get("redirect_uri") or "").strip()
    return {"client_id": client_id, "client_secret": client_secret, "redirect_uri": redirect_uri}


def _clip(value: Any, limit: int) -> Optional[str]:
    """按列宽截断字符串（``None`` 原样返回）"""
    if value is None:
        return None
    return str(value)[:limit]


def _binding_out(row: OAuthAccount) -> dict:
    return {
        "id": row.id,
        "provider": row.provider,
        "provider_user_id": row.provider_user_id,
        "has_token": bool(row.access_token),
        "token_expires_at": row.token_expires_at,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


def _parse_token_response(resp: httpx.Response, provider: str) -> dict[str, Any]:
    """解析令牌响应（JSON 或 form-urlencoded，与源服务的双格式处理一致）"""
    content_type = resp.headers.get("content-type", "")
    payload: dict[str, Any] = {}
    if "application/json" in content_type:
        try:
            data = resp.json()
            if isinstance(data, dict):
                payload = data
        except ValueError:
            payload = {}
    if not payload:
        try:
            payload = {k: v[0] for k, v in parse_qs(resp.text or "").items()}
        except (TypeError, ValueError):
            payload = {}
    access_token = payload.get("access_token")
    if not access_token:
        raise BadRequestError(f"{provider} 未返回 access_token：{_clip(resp.text, 200)}")
    return {
        "access_token": access_token,
        "refresh_token": payload.get("refresh_token"),
        "expires_in": payload.get("expires_in"),
        "token_type": payload.get("token_type") or "Bearer",
        # 微信令牌响应携带 openid、微博携带 uid，供后续拉取用户信息使用
        "openid": payload.get("openid"),
        "uid": payload.get("uid"),
    }


class OAuthService:
    """OAuth 第三方登录（真表 ``oauth_accounts`` + 真配置 ``system_settings``）"""

    # ------------------------------------------------------------ 配置读取（DB）
    async def _config(self, db: AsyncSession) -> dict[str, Any]:
        row = await setting_crud.get_by(db, setting_key=PROVIDERS_SETTING_KEY)
        return parse_providers_config(row.setting_value if row is not None else None)

    async def _credentials(self, db: AsyncSession, provider: str) -> dict[str, str]:
        """取提供方凭据；未配置即如实报错（**绝不**以外观伪造成功）"""
        provider = str(provider or "").strip().lower()
        require_provider(provider)
        creds = provider_credentials(await self._config(db), provider)
        if creds is None:
            raise BadRequestError(
                f"OAuth 提供方 {provider} 未配置：请在系统设置项 {PROVIDERS_SETTING_KEY} 中"
                f"为该提供方填写 client_id 与 client_secret"
            )
        return creds

    # ------------------------------------------------------------ 提供方 / 授权 URL
    async def list_providers(self, db: AsyncSession) -> list[dict]:
        """支持的提供方列表 + 是否已配置（真读 ``system_settings``）"""
        config = await self._config(db)
        return [
            {
                "key": key,
                "name": meta["name"],
                "icon": meta["icon"],
                "configured": provider_credentials(config, key) is not None,
                "supports_pkce": key in PKCE_PROVIDERS,
            }
            for key, meta in PROVIDERS.items()
        ]

    async def build_authorize_url(
        self, db: AsyncSession, provider: str, *, redirect_uri: Optional[str] = None
    ) -> dict:
        """生成授权跳转信息（真实拼接 scope / state / PKCE challenge）"""
        provider = str(provider or "").strip().lower()
        meta = require_provider(provider)
        creds = await self._credentials(db, provider)
        final_redirect = (redirect_uri or creds.get("redirect_uri") or "").strip()
        if not final_redirect:
            raise BadRequestError(
                "缺少 redirect_uri：请在系统设置里配置，或在请求中显式传入 redirect_uri"
            )

        state = generate_state(provider, settings.SECRET_KEY)
        verifier: Optional[str] = None
        challenge: Optional[str] = None
        if provider in PKCE_PROVIDERS:
            verifier = generate_code_verifier()
            challenge = code_challenge_s256(verifier)
        authorize_url = build_authorize_url(
            provider, creds["client_id"], final_redirect, state, code_challenge=challenge
        )
        return {
            "provider": provider,
            "name": meta["name"],
            "authorize_url": authorize_url,
            "state": state,
            "redirect_uri": final_redirect,
            "code_verifier": verifier,
            "code_challenge": challenge,
            "code_challenge_method": "S256" if challenge else None,
        }

    # ------------------------------------------------------------ 回调（真实换令牌 + 绑定 + 登录态）
    async def handle_callback(
        self,
        db: AsyncSession,
        provider: str,
        *,
        code: str,
        state: str,
        code_verifier: Optional[str] = None,
        current_user_id: Optional[int] = None,
        remember_me: bool = False,
        ip: str = "unknown",
        user_agent: str = "",
    ) -> dict:
        """处理回调：校验 state → 换令牌 → 拉用户信息 → 绑定/建号 → 签发登录态"""
        provider = str(provider or "").strip().lower()
        require_provider(provider)
        creds = await self._credentials(db, provider)

        if not code:
            raise BadRequestError("缺少授权码 code")
        if not verify_state(state, provider, settings.SECRET_KEY):
            raise BadRequestError("state 校验失败（可能已过期或被伪造），请重新发起授权")

        token = await self._exchange_token(provider, code, creds, code_verifier)
        info = await self._fetch_user_info(provider, token, creds)
        provider_user_id = info.get("provider_id")
        if not provider_user_id:
            raise BadRequestError(f"{provider} 未返回可用于标识用户的字段（provider_user_id）")

        account = await db.scalar(
            select(OAuthAccount).where(
                OAuthAccount.provider == provider,
                OAuthAccount.provider_user_id == str(provider_user_id),
            )
        )
        created_user = False
        if account is not None:
            if current_user_id is not None and account.user_id != current_user_id:
                raise BadRequestError("该第三方账号已绑定到其他用户，无法重复绑定")
            user = await db.get(User, account.user_id)
            if user is None:
                raise BadRequestError("绑定记录对应的本地用户不存在")
        else:
            user, created_user = await self._resolve_user(db, info, provider, current_user_id)

        now = datetime.now()
        fields = self._binding_fields(token, info, now)
        if account is None:
            account = OAuthAccount(
                user_id=user.id,
                provider=provider,
                provider_user_id=str(provider_user_id),
                created_at=now,
                updated_at=now,
                **fields,
            )
            db.add(account)
        else:
            for key, value in fields.items():
                setattr(account, key, value)
            account.updated_at = now
        await db.commit()
        await db.refresh(user)

        # 复用 v3 的登录签发（会话轮换 + 审计 + 事件），保证与账号密码登录一致
        from src.api.v3.modules.system.auth.service import auth_service

        tokens = await auth_service.grant_tokens(
            db, user, remember_me=remember_me, ip=ip, user_agent=user_agent
        )
        logger.info(
            "OAuth 登录成功 provider=%s user=%s created=%s", provider, user.id, created_user
        )
        return {
            "provider": provider,
            "user_id": user.id,
            "username": user.username,
            "bound": True,
            "created_user": created_user,
            "access_token": tokens.get("access_token"),
            "refresh_token": tokens.get("refresh_token"),
            "token_type": tokens.get("token_type", "bearer"),
            "expires_in": tokens.get("expires_in"),
        }

    # ------------------------------------------------------------ 绑定列表 / 解绑
    async def list_bindings(self, db: AsyncSession, user_id: int) -> list[dict]:
        """本人已绑定的第三方账号（脱敏）"""
        rows = (
            await db.execute(
                select(OAuthAccount)
                .where(OAuthAccount.user_id == user_id)
                .order_by(OAuthAccount.id.desc())
            )
        ).scalars().all()
        return [_binding_out(row) for row in rows]

    async def unbind(self, db: AsyncSession, user_id: int, provider: str) -> dict:
        """解除**本人**对某提供方的绑定（未绑定返回 404）"""
        provider = str(provider or "").strip().lower()
        require_provider(provider)
        account = await db.scalar(
            select(OAuthAccount).where(
                OAuthAccount.user_id == user_id, OAuthAccount.provider == provider
            )
        )
        if account is None:
            raise NotFoundError("未绑定该第三方账号")
        await db.delete(account)
        await db.commit()
        logger.info("OAuth 解绑 provider=%s user=%s", provider, user_id)
        return {"provider": provider, "unbound": True}

    # ------------------------------------------------------------ 真实外部调用（HTTP）
    async def _exchange_token(
        self, provider: str, code: str, creds: dict[str, str], code_verifier: Optional[str]
    ) -> dict[str, Any]:
        meta = require_provider(provider)
        data = build_token_request(
            provider,
            code,
            creds["client_id"],
            creds["client_secret"],
            creds.get("redirect_uri") or "",
            code_verifier=code_verifier,
        )
        try:
            async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT, follow_redirects=True) as client:
                resp = await client.post(
                    meta["token_url"], data=data, headers={"Accept": "application/json"}
                )
        except httpx.HTTPError as exc:
            raise BadRequestError(f"请求 {provider} 令牌端点失败：{exc}") from exc
        if resp.status_code >= 400:
            raise BadRequestError(
                f"{provider} 令牌端点拒绝请求（HTTP {resp.status_code}）：{_clip(resp.text, 200)}"
            )
        return _parse_token_response(resp, provider)

    async def _fetch_user_info(
        self, provider: str, token: dict[str, Any], creds: dict[str, str]
    ) -> dict[str, Any]:
        meta = require_provider(provider)
        access = token["access_token"]
        headers = {"Accept": "application/json", "User-Agent": USER_AGENT}
        params: dict[str, str] = {}
        qq_openid: Optional[str] = None

        if provider in {"github", "google"}:
            headers["Authorization"] = f"Bearer {access}"
        elif provider == "wechat":
            if not token.get("openid"):
                raise BadRequestError("微信未返回 openid，无法拉取用户信息")
            params = {"access_token": access, "openid": token["openid"], "lang": "zh_CN"}
        elif provider == "qq":
            qq_openid = await self._fetch_qq_openid(access)
            params = {
                "access_token": access,
                "oauth_consumer_key": creds["client_id"],
                "openid": qq_openid,
            }
        elif provider == "weibo":
            if not token.get("uid"):
                raise BadRequestError("微博未返回 uid，无法拉取用户信息")
            params = {"access_token": access, "uid": token["uid"]}

        try:
            async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT, follow_redirects=True) as client:
                resp = await client.get(meta["user_info_url"], headers=headers, params=params)
        except httpx.HTTPError as exc:
            raise BadRequestError(f"请求 {provider} 用户信息端点失败：{exc}") from exc
        if resp.status_code >= 400:
            raise BadRequestError(
                f"{provider} 用户信息端点拒绝请求（HTTP {resp.status_code}）：{_clip(resp.text, 200)}"
            )
        try:
            raw = resp.json()
        except ValueError as exc:
            raise BadRequestError(f"{provider} 用户信息端点返回非 JSON 响应") from exc
        if not isinstance(raw, dict):
            raise BadRequestError(f"{provider} 用户信息端点返回了意外结构")

        if provider == "qq":
            # QQ 的 openid 来自 /oauth2.0/me，不在 userinfo 响应里；复用上面已取到的值
            raw = dict(raw)
            if qq_openid:
                raw.setdefault("openid", qq_openid)
        normalized = normalize_user_info(provider, raw)

        # GitHub 未公开邮箱时，凭 user:email scope 再取一次主邮箱
        if provider == "github" and not normalized.get("email"):
            email = await self._fetch_github_primary_email(access)
            if email:
                normalized["email"] = email
        return normalized

    async def _fetch_qq_openid(self, access_token: str) -> str:
        """QQ：GET /oauth2.0/me 取 openid（fmt=json 下直接返回 JSON）"""
        try:
            async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
                resp = await client.get(
                    "https://graph.qq.com/oauth2.0/me",
                    params={"access_token": access_token, "fmt": "json"},
                    headers={"Accept": "application/json"},
                )
        except httpx.HTTPError as exc:
            raise BadRequestError(f"请求 QQ openid 端点失败：{exc}") from exc
        text = (resp.text or "").strip()
        data: dict[str, Any] = {}
        try:
            parsed = resp.json()
            if isinstance(parsed, dict):
                data = parsed
        except ValueError:
            match = re.search(r"\{.*\}", text, re.S)
            if match:
                try:
                    parsed = json.loads(match.group(0))
                    if isinstance(parsed, dict):
                        data = parsed
                except ValueError:
                    data = {}
        openid = data.get("openid")
        if not openid:
            raise BadRequestError(f"QQ 未返回 openid：{_clip(text, 200)}")
        return str(openid)

    async def _fetch_github_primary_email(self, access_token: str) -> Optional[str]:
        """GitHub：GET /user/emails 取已验证主邮箱（失败一律返回 None，不阻断登录）"""
        try:
            async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
                resp = await client.get(
                    "https://api.github.com/user/emails",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Accept": "application/json",
                        "User-Agent": USER_AGENT,
                    },
                )
        except httpx.HTTPError:
            return None
        if resp.status_code >= 400:
            return None
        try:
            data = resp.json()
        except ValueError:
            return None
        if not isinstance(data, list):
            return None
        primary = next(
            (
                item.get("email")
                for item in data
                if isinstance(item, dict) and item.get("primary") and item.get("verified")
            ),
            None,
        )
        if primary:
            return str(primary)
        first = next(
            (item.get("email") for item in data if isinstance(item, dict) and item.get("email")),
            None,
        )
        return str(first) if first else None

    # ------------------------------------------------------------ 本地账号解析
    async def _resolve_user(
        self,
        db: AsyncSession,
        info: dict[str, Any],
        provider: str,
        current_user_id: Optional[int],
    ) -> tuple[User, bool]:
        """定位要绑定的本地用户：优先登录用户 → 同邮箱用户 → 新建（返回 ``(user, created)``）"""
        if current_user_id is not None:
            user = await db.get(User, current_user_id)
            if user is None:
                raise BadRequestError("当前登录用户不存在")
            return user, False

        email = str(info.get("email") or "").strip().lower()
        if email:
            existing = await db.scalar(
                select(User).where(func.lower(User.email) == email).limit(1)
            )
            if existing is not None:
                return existing, False

        username = await self._unique_username(
            db, info.get("username") or (email.split("@")[0] if email else ""), provider
        )
        now = datetime.now()
        user = User(
            username=username,
            email=email or None,
            password=None,  # OAuth 账号无本地密码，只能经第三方登录
            profile_picture=info.get("avatar"),
            locale="zh_CN",
            is_active=True,
            date_joined=now,
        )
        db.add(user)
        await db.flush()
        logger.info("OAuth 新建本地账号 provider=%s user=%s username=%s", provider, user.id, username)
        return user, True

    async def _unique_username(self, db: AsyncSession, base: str, provider: str) -> str:
        """按第三方昵称派生唯一用户名（去噪 + 冲突追加随机后缀）"""
        cleaned = re.sub(r"[^\w.\-]", "", str(base or "").strip())[:24]
        seed = cleaned or f"{provider}_user"
        candidate = seed
        for _ in range(20):
            exists = await db.scalar(select(User.id).where(User.username == candidate).limit(1))
            if exists is None:
                return candidate
            candidate = f"{seed}_{secrets.token_hex(2)}"
        return f"{seed}_{secrets.token_hex(4)}"

    @staticmethod
    def _binding_fields(token: dict[str, Any], info: dict[str, Any], now: datetime) -> dict[str, Any]:
        """组装要落到 ``oauth_accounts`` 的字段（超长按列宽截断并记警告）"""
        expires_in = token.get("expires_in")
        token_expires_at: Optional[datetime] = None
        if expires_in:
            try:
                token_expires_at = now + timedelta(seconds=int(expires_in))
            except (TypeError, ValueError):
                token_expires_at = None
        extra = json.dumps(
            {
                "username": info.get("username"),
                "name": info.get("name"),
                "avatar": info.get("avatar"),
                "profile_url": info.get("profile_url"),
            },
            ensure_ascii=False,
        )
        access = _clip(token.get("access_token"), 255)
        if token.get("access_token") and len(str(token["access_token"])) > 255:
            logger.warning("access_token 超过 255 列宽，已截断存储（仅用于存在性判断）")
        return {
            "access_token": access,
            "refresh_token": _clip(token.get("refresh_token"), 255),
            "token_expires_at": token_expires_at,
            "extra_data": _clip(extra, 255),
        }


oauth_service = OAuthService()
