"""审计日志哈希链与脱敏（纯函数，便于单测）

## 哈希链

每条审计记录的 ``entry_hash`` 覆盖 ``prev_hash`` 与自身全部关键字段：

    entry_hash(N) = sha256(canonical(prev_hash, 字段…) )

于是任何一行被事后修改（例如把"删除了用户 X"的 ``action`` 改掉），其
``entry_hash`` 就不再匹配，且后续所有行的 ``prev_hash`` 也会对不上 ——
``verify_chain`` 会定位到第一个断点。

字段用 ``json.dumps(sort_keys=True, separators=(",", ":"))`` 规范化，保证
同一份内容在任何进程里算出同一个摘要。

## 删除与链首

审计日志有保留策略（``cleanup_old_logs``），删除**最早**的记录会让现存第一条的
``prev_hash`` 指向已不存在的行。这是允许的：``verify_chain`` 从现存最早的
非空 ``entry_hash`` 记录建立起点，只校验它之后的连续性。

## 脱敏

审计要记"改了什么"，但请求体里常有密码 / 令牌。``redact`` 会按键名屏蔽敏感字段，
**替换为固定标记而不是删除键**（保留"这里有过一个字段"的事实）。
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any, Dict, Optional

#: 链首占位（prev_hash 为空时参与计算）
GENESIS = "GENESIS"

#: 键名命中即打码（小写比较，含子串匹配）
SENSITIVE_KEY_PARTS = (
    "password",
    "passwd",
    "pwd",
    "secret",
    "token",
    "api_key",
    "apikey",
    "authorization",
    "cookie",
    "private_key",
    "credential",
)

REDACTED = "***REDACTED***"


def _is_sensitive(key: str) -> bool:
    lowered = str(key).lower()
    return any(part in lowered for part in SENSITIVE_KEY_PARTS)


def redact(data: Any, *, _depth: int = 0) -> Any:
    """递归屏蔽敏感键的值（保留键本身与结构，便于审计"改过哪些字段"）"""
    if _depth > 6:
        return "<max-depth>"
    if isinstance(data, dict):
        return {
            key: (REDACTED if _is_sensitive(key) else redact(value, _depth=_depth + 1))
            for key, value in data.items()
        }
    if isinstance(data, (list, tuple)):
        return [redact(item, _depth=_depth + 1) for item in data]
    return data


def dump_snapshot(data: Any) -> Optional[str]:
    """把快照序列化成 JSON 文本（含脱敏）；``None`` 原样返回"""
    if data is None:
        return None
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except (ValueError, TypeError):
            # 不是 JSON 就按原文记（已经过脱敏调用方的判断）
            return data
    return json.dumps(redact(data), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def compute_entry_hash(
    prev_hash: Optional[str],
    *,
    user_id: Optional[int],
    user_name: Optional[str],
    action: Optional[str],
    level: Optional[str],
    resource_type: Optional[str],
    resource_id: Any,
    description: Optional[str],
    ip_address: Optional[str],
    before_data: Optional[str],
    after_data: Optional[str],
    created_at: Optional[datetime],
) -> str:
    """计算一条审计记录的 ``entry_hash``"""
    payload: Dict[str, Any] = {
        "prev": prev_hash or GENESIS,
        "user_id": user_id,
        "user_name": user_name,
        "action": action,
        "level": level,
        "resource_type": resource_type,
        "resource_id": None if resource_id is None else str(resource_id),
        "description": description,
        "ip_address": ip_address,
        "before_data": before_data,
        "after_data": after_data,
        "created_at": created_at.isoformat() if created_at else None,
    }
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


__all__ = [
    "GENESIS",
    "REDACTED",
    "SENSITIVE_KEY_PARTS",
    "compute_entry_hash",
    "dump_snapshot",
    "redact",
]
