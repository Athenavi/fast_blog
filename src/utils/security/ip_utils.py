"""兼容层：客户端 IP 解析的权威实现已迁至 ``shared.utils.client_ip``。

保留本模块只是为了让既有的 ``from src.utils.security.ip_utils import get_client_ip``
不失效；新代码请直接从 ``shared.utils.client_ip`` 导入 —— 那里有完整的安全说明。

**历史实现已废弃**：它取 ``X-Forwarded-For`` 的**首值**，而该头由 nginx 以
`$proxy_add_x_forwarded_for` 追加速度写入，首值完全由客户端控制，可被用来绕过
限流与登录防爆破。
"""

from shared.utils.client_ip import (  # noqa: F401
    TRUSTED_PROXY_NETWORKS,
    get_client_ip,
    is_trusted_proxy,
    parse_ip,
    resolve_client_ip,
)

__all__ = [
    "TRUSTED_PROXY_NETWORKS",
    "anonymize_ip_address",
    "get_client_ip",
    "is_trusted_proxy",
    "parse_ip",
    "resolve_client_ip",
]


def anonymize_ip_address(ip: str) -> str:
    """把 IPv4 的后两段打码（GDPR 展示用）；非 IPv4 原样返回"""
    parts = str(ip).split(".")
    if len(parts) == 4:
        return f"{parts[0]}.{parts[1]}.***.***"
    return ip
