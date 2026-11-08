# -*- coding: utf-8 -*-
"""出站请求的 SSRF 兜底（`src/utils/security/outbound.py`）。

重点是"每一次请求都校验"，包括重定向产生的下一跳 —— 只校验首跳等于没校验。
"""

import pytest

from src.utils.security.outbound import (
    OutboundBlockedError,
    guarded_async_client,
    guarded_client,
)


class TestOutboundGuard:
    @pytest.mark.asyncio
    async def test_loopback_is_blocked_before_connect(self):
        """回环地址在发出请求**之前**就被拒绝（不需要真实网络）。"""
        async with guarded_async_client(timeout=0.1, trust_env=False) as client:
            with pytest.raises(OutboundBlockedError):
                await client.get("http://127.0.0.1:1/")

    def test_link_local_metadata_is_blocked(self):
        with guarded_client(timeout=0.1, trust_env=False) as client:
            with pytest.raises(OutboundBlockedError):
                client.get("http://169.254.169.254/latest/meta-data/")

    def test_non_http_scheme_is_blocked(self):
        with guarded_client(timeout=0.1, trust_env=False) as client:
            with pytest.raises(OutboundBlockedError):
                client.get("file:///etc/passwd")

    def test_guard_is_installed_on_request_hook(self):
        """重定向的下一跳同样走 request 钩子 —— 校验点与真实出站目标同一集合。"""
        with guarded_client(trust_env=False) as client:
            hooks = client.event_hooks["request"]
            assert any(h is not None for h in hooks)
            assert client.follow_redirects is True
