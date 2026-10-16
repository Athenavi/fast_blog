# -*- coding: utf-8 -*-
"""API 令牌：对外接入（第三方应用 / CI）的凭证解析。

设计要点
========

- **明文只在创建时返回一次**：库里只有 ``token_hash``（Argon2，与用户密码同一套实现）
  与 ``token_prefix``。
- 明文格式 ``fbk_<prefix8>_<secret43>``：前缀可索引，避免"为找记录而逐个 Argon2 校验"
  的 O(n) 问题；真正的强度来自 secret（``secrets.token_urlsafe(32)``）。
- 任何失败（格式错/不存在/已撤销/已过期/哈希不匹配）一律返回 ``None``，由调用方统一
  给出同一个 401 文案，避免用错误差异枚举令牌。
- 校验通过后由认证层把 :class:`Principal` 挂到 ``request.state.principal``，
  权限层据此把可用权限**收窄**到 ``scopes``（见 ``core/permission/control.py``）。

与用户会话的关系
================

``Principal.scopes is None`` 表示"用户会话（JWT）"，此时权限就是该用户的全部权限码；
``scopes`` 是集合时表示"API 令牌"，权限 = ``scopes ∩ 该用户当前权限码``——
用户被降权/撤销角色后，其令牌的对应权限**立即同步失效**。
"""

import json
import secrets
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models import ApiToken

#: 明文前缀，便于在日志/界面里一眼认出这是 FastBlog 令牌
TOKEN_SCHEME = "fbk"
#: 用 ``token_hex`` 而**不是** ``token_urlsafe``：后者字母表含 ``-`` 与 ``_``，
#: 会与 ``fbk_<prefix>_<secret>`` 的下划线分隔符冲突 —— 一旦随机串里出现下划线，
#: 刚签发的令牌就会解析失败。（本缺陷由 tests/test_api_token.py 的往返测试发现。）
_PREFIX_HEX_BYTES = 4  # → 8 个十六进制字符（列宽上限 16）
_SECRET_HEX_BYTES = 32  # → 64 个十六进制字符（256 bit 熵）

#: ``last_used_at`` 的写入节流间隔（秒）：避免每个请求都写一次库
_LAST_USED_THROTTLE_SECONDS = 60


@dataclass(frozen=True)
class Principal:
    """请求主体：既可能是用户会话，也可能是 API 令牌。"""

    user: Any
    #: None = JWT 会话（用用户全部权限）；集合 = API 令牌（权限收窄到该集合）
    scopes: Optional[frozenset[str]]
    source: str  # "jwt" | "api_key"
    token_id: Optional[int] = None


# ---------------------------------------------------------------- 生成与校验

def _hash(secret: str) -> str:
    from src.utils.security.password_validator import hash_password
    return hash_password(secret)


def verify_secret(secret: str, hashed: str) -> bool:
    from src.utils.security.password_validator import verify_password
    if not hashed:
        return False
    try:
        return bool(verify_password(secret, hashed))
    except Exception:  # noqa: BLE001 - 任何异常都视为校验失败（fail-closed）
        return False


def generate_token() -> tuple[str, str, str]:
    """生成新令牌，返回 ``(明文, prefix, hash)``。明文**只在本次返回**。"""
    prefix = secrets.token_hex(_PREFIX_HEX_BYTES)
    secret = secrets.token_hex(_SECRET_HEX_BYTES)
    plaintext = f"{TOKEN_SCHEME}_{prefix}_{secret}"
    return plaintext, prefix, _hash(secret)


def split_token(raw: str) -> Optional[tuple[str, str]]:
    """解析明文为 ``(prefix, secret)``；格式非法返回 ``None``。"""
    parts = (raw or "").strip().split("_")
    if len(parts) != 3:
        return None
    scheme, prefix, secret = parts
    if scheme != TOKEN_SCHEME or not prefix or not secret:
        return None
    return prefix, secret


def scopes_to_text(scopes: Any) -> str:
    """权限码集合 → 入库文本（排序去重后再序列化，便于比对与审计）"""
    return json.dumps(sorted({str(s) for s in scopes if str(s).strip()}), ensure_ascii=False)


def scopes_from_text(text: Optional[str]) -> frozenset[str]:
    """入库文本 → 权限码集合；任何异常一律返回空集合（fail-closed）"""
    if not text:
        return frozenset()
    try:
        data = json.loads(text)
    except (ValueError, TypeError):
        return frozenset()
    if not isinstance(data, list):
        return frozenset()
    return frozenset(str(item) for item in data if isinstance(item, str) and item.strip())


async def authenticate_api_key(db: AsyncSession, raw: str) -> Optional[ApiToken]:
    """校验明文令牌，返回可用记录；任何失败返回 ``None``。"""
    parsed = split_token(raw)
    if parsed is None:
        return None
    prefix, secret = parsed

    row = (
        await db.execute(select(ApiToken).where(ApiToken.token_prefix == prefix))
    ).scalars().first()
    if row is None or not row.is_active:
        return None
    if row.expires_at is not None and row.expires_at < datetime.now():
        return None
    if not verify_secret(secret, row.token_hash or ""):
        return None

    # 使用时间戳节流写入：既留下审计线索，又不至于每个请求写一次库
    try:
        now = datetime.now()
        if row.last_used_at is None or (now - row.last_used_at).total_seconds() > _LAST_USED_THROTTLE_SECONDS:
            row.last_used_at = now
            await db.commit()
    except Exception:  # noqa: BLE001 - 记录使用时间失败不应影响鉴权结果
        await db.rollback()

    return row


def principal_from_token(row: ApiToken, user: Any) -> Principal:
    return Principal(
        user=user,
        scopes=scopes_from_text(row.scopes),
        source="api_key",
        token_id=getattr(row, "id", None),
    )
