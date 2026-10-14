"""客户端 IP 解析回归测试

核心回归点：**不能取 X-Forwarded-For 的首值**。
nginx 用 `$proxy_add_x_forwarded_for` 追加写入该头，首值由客户端完全控制；
取首值等于把限流 / 登录防爆破的键交给攻击者随意设置。
"""
import ipaddress

from starlette.requests import Request

from shared.utils.client_ip import (
    TRUSTED_PROXY_NETWORKS,
    get_client_ip,
    is_trusted_proxy,
    parse_ip,
    resolve_client_ip,
)


def _request(client_host, headers=None):
    raw = [(k.lower().encode(), v.encode()) for k, v in (headers or {}).items()]
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": raw,
        "client": (client_host, 12345) if client_host else None,
    }
    return Request(scope)


class TestParseIp:
    def test_plain_ipv4(self):
        assert str(parse_ip("1.2.3.4")) == "1.2.3.4"

    def test_strips_port(self):
        assert str(parse_ip("1.2.3.4:5678")) == "1.2.3.4"

    def test_ipv4_mapped_ipv6_is_normalised(self):
        assert str(parse_ip("::ffff:172.17.0.1")) == "172.17.0.1"

    def test_plain_ipv6_kept(self):
        assert str(parse_ip("::1")) == "::1"

    def test_rejects_unknown_and_empty(self):
        assert parse_ip("unknown") is None
        assert parse_ip("") is None
        assert parse_ip(None) is None

    def test_rejects_garbage(self):
        assert parse_ip("not-an-ip") is None
        assert parse_ip("<script>") is None


class TestTrustedProxy:
    def test_loopback_and_private_are_trusted(self):
        assert is_trusted_proxy("127.0.0.1")
        assert is_trusted_proxy("172.17.0.5")
        assert is_trusted_proxy("10.0.0.7")
        assert is_trusted_proxy("192.168.1.9")

    def test_public_ip_is_not_trusted(self):
        assert not is_trusted_proxy("8.8.8.8")
        assert not is_trusted_proxy("203.0.113.9")

    def test_none_is_not_trusted(self):
        assert not is_trusted_proxy(None)


class TestResolveClientIp:
    def test_first_xff_value_is_never_used(self):
        """伪造首值不能改变结果 —— 本模块存在的理由"""
        assert resolve_client_ip(
            "172.17.0.1",
            x_forwarded_for="1.2.3.4, 203.0.113.9",
        ) == "203.0.113.9"

    def test_x_real_ip_wins_over_xff(self):
        assert resolve_client_ip(
            "172.17.0.1",
            x_real_ip="203.0.113.9",
            x_forwarded_for="1.2.3.4",
        ) == "203.0.113.9"

    def test_untrusted_direct_peer_ignores_all_headers(self):
        assert resolve_client_ip(
            "8.8.8.8",
            x_real_ip="203.0.113.9",
            x_forwarded_for="1.2.3.4",
        ) == "8.8.8.8"

    def test_falls_back_to_direct_peer(self):
        assert resolve_client_ip("172.17.0.1") == "172.17.0.1"

    def test_unknown_when_nothing_available(self):
        assert resolve_client_ip(None) == "unknown"

    def test_invalid_header_falls_back_to_direct_peer(self):
        assert resolve_client_ip("172.17.0.1", x_real_ip="<script>") == "172.17.0.1"

    def test_ipv4_mapped_direct_peer_is_trusted(self):
        assert resolve_client_ip(
            "::ffff:172.17.0.1",
            x_real_ip="203.0.113.9",
        ) == "203.0.113.9"


class TestGetClientIp:
    def test_uses_x_real_ip_behind_trusted_proxy(self):
        req = _request("172.18.0.3", {"X-Real-IP": "203.0.113.9", "X-Forwarded-For": "1.2.3.4"})
        assert get_client_ip(req) == "203.0.113.9"

    def test_direct_client_without_proxy(self):
        assert get_client_ip(_request("203.0.113.9")) == "203.0.113.9"

    def test_spoofed_headers_from_public_peer_are_ignored(self):
        req = _request("203.0.113.9", {"X-Forwarded-For": "1.2.3.4"})
        assert get_client_ip(req) == "203.0.113.9"

    def test_no_client_returns_unknown(self):
        assert get_client_ip(_request(None)) == "unknown"


def test_trusted_networks_cover_docker_bridge():
    """Docker 默认 bridge 是 172.17/172.18，必须落在可信集合内"""
    docker = ipaddress.ip_address("172.18.0.2")
    assert any(docker in net for net in TRUSTED_PROXY_NETWORKS)
