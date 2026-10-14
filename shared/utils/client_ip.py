"""客户端真实 IP 解析（唯一权威实现）

## 为什么不能取 X-Forwarded-For 的首值

nginx 用 ``$proxy_add_x_forwarded_for`` 写这个头，语义是**追加**而不是覆盖：

    客户端发送    X-Forwarded-For: 1.2.3.4
    nginx 转发    X-Forwarded-For: 1.2.3.4, <真实客户端 IP>

于是首值是**客户端可自由伪造**的内容。若拿首值当限流 / 登录防爆破 / 审计的键，
攻击者每次换一个伪造值就能绕过所有 IP 维度的限制。

## 策略（fail-closed）

1. 先看直连方 ``request.client.host``。**只有**它落在可信代理网段（回环 + 私有网段，
   覆盖 Docker bridge 的 172.16.0.0/12）时才采信代理头；否则一律用直连地址 ——
   这样"端口被直连 + 伪造代理头"这条路径自动失效。
2. 可信时优先 ``X-Real-IP``：nginx 用 ``$remote_addr`` **覆盖**写入，客户端无法伪造。
3. 其次取 ``X-Forwarded-For`` 的**最后一个**有效地址（最近一跳代理写入的值的位置
   由代理而非客户端决定）。
4. 都取不到时回落直连地址；直连地址也拿不到则返回 ``"unknown"``。

## 使用

新代码统一 ``from shared.utils.client_ip import get_client_ip``。
旧路径 ``src.utils.security.ip_utils`` 保留为兼容层。
"""

from __future__ import annotations

import ipaddress
from typing import Optional, Tuple, Union

_IPAddress = Union[ipaddress.IPv4Address, ipaddress.IPv6Address]
_IPNetwork = Union[ipaddress.IPv4Network, ipaddress.IPv6Network]

#: 可信代理来源：回环 + 私有网段（Docker 默认 bridge 落在 172.16.0.0/12）
TRUSTED_PROXY_NETWORKS: Tuple[_IPNetwork, ...] = (
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("fc00::/7"),
)


def parse_ip(value: Optional[str]) -> Optional[_IPAddress]:
    """把单个候选字符串解析成 IP 对象；不合法返回 ``None``。

    兼容两种常见写法：

    - IPv4-mapped IPv6（``::ffff:172.17.0.1``）→ 归一成 IPv4
    - 尾随端口（``1.2.3.4:5678``）→ 去掉端口（IPv6 的冒号不按端口处理）
    """
    if not value:
        return None
    candidate = value.strip()
    if not candidate or candidate.lower() == "unknown":
        return None
    if candidate.count(":") == 1 and "." in candidate:
        candidate = candidate.split(":", 1)[0]
    try:
        addr = ipaddress.ip_address(candidate)
    except ValueError:
        return None
    if isinstance(addr, ipaddress.IPv6Address) and addr.ipv4_mapped is not None:
        return addr.ipv4_mapped
    return addr


def _is_trusted(addr: _IPAddress) -> bool:
    return any(addr in net for net in TRUSTED_PROXY_NETWORKS if net.version == addr.version)


def is_trusted_proxy(host: Optional[str]) -> bool:
    """直连方是否属于可信代理网段"""
    addr = parse_ip(host)
    return addr is not None and _is_trusted(addr)


def resolve_client_ip(
    direct_host: Optional[str],
    *,
    x_real_ip: Optional[str] = None,
    x_forwarded_for: Optional[str] = None,
) -> str:
    """纯函数：给定直连地址与两个代理头，返回应采信的客户端 IP。

    拆成纯函数是为了让单测不必构造 ``Request``。
    """
    direct_addr = parse_ip(direct_host)
    direct = str(direct_addr) if direct_addr is not None else ""

    # 不可信来源：忽略全部代理头（它们可被客户端伪造）
    if direct_addr is None or not _is_trusted(direct_addr):
        return direct or "unknown"

    real = parse_ip(x_real_ip)
    if real is not None:
        return str(real)

    if x_forwarded_for:
        valid = [addr for addr in (parse_ip(part) for part in x_forwarded_for.split(",")) if addr is not None]
        if valid:
            # 取最后一个：其位置由最近一跳代理写入，客户端无法控制
            return str(valid[-1])

    return direct or "unknown"


def get_client_ip(request) -> str:
    """从 Starlette / FastAPI ``Request`` 解析客户端 IP（全局统一入口）"""
    direct = getattr(getattr(request, "client", None), "host", None)
    headers = getattr(request, "headers", None)
    if headers is None:
        addr = parse_ip(direct)
        return str(addr) if addr is not None else "unknown"
    return resolve_client_ip(
        direct,
        x_real_ip=headers.get("X-Real-IP"),
        x_forwarded_for=headers.get("X-Forwarded-For"),
    )


__all__ = [
    "TRUSTED_PROXY_NETWORKS",
    "get_client_ip",
    "is_trusted_proxy",
    "parse_ip",
    "resolve_client_ip",
]
