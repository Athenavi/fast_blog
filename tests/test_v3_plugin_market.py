# -*- coding: utf-8 -*-
"""P2-1 插件市场客户端测试（不连网、不依赖数据库）。

盯住几条"必须明确失败"的契约：

  1. **未配置** ``PLUGIN_MARKETPLACE_URL`` → 明确报"未配置"，而不是返回空列表；
  2. 上游 5xx / 超时 / 非 JSON / ``code != 0`` → 都转成可读错误（带状态码或原因）；
  3. **下载必须验校验和**：响应头声明与包内容不符、或与请求声明不符 → 拒绝安装；
  4. 只有校验通过才把包装交给既有 ``PluginInstaller``，并落 ``sha256`` 供审计。
"""

import hashlib
from unittest.mock import MagicMock, patch

import pytest

from src.api.v3.core.exceptions import BadRequestError, NotFoundError
from src.api.v3.modules.extension.plugin.market_service import MarketClient


class FakeResponse:
    def __init__(self, *, status_code=200, json_data=None, content=b"", headers=None):
        self.status_code = status_code
        self._json = json_data
        self.content = content
        self.headers = headers or {}

    def json(self):
        if self._json is None:
            raise ValueError("not json")
        return self._json


class FakeAsyncClient:
    """替代 httpx.AsyncClient 的最简替身（支持 async with）"""

    def __init__(self, response):
        self._response = response

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def get(self, url, params=None):
        return self._response


def _patch_client(response):
    return patch(
        "src.api.v3.modules.extension.plugin.market_service.httpx.AsyncClient",
        lambda *a, **kw: FakeAsyncClient(response),
    )


BASE = "http://market.test/api/v1"


# ---------------------------------------------------------------- 未配置 / 不可达

@pytest.mark.asyncio
class TestUnconfiguredAndUnreachable:
    async def test_unconfigured_is_explicit_error(self, monkeypatch):
        monkeypatch.delenv("PLUGIN_MARKETPLACE_URL", raising=False)
        client = MarketClient()
        assert client.configured is False
        with pytest.raises(BadRequestError) as exc:
            await client.list_plugins()
        assert "未配置" in str(exc.value)

    async def test_timeout_becomes_readable_error(self):
        import httpx

        def _boom(*a, **kw):
            raise httpx.ConnectTimeout("timed out")

        client = MarketClient(BASE)
        with patch(
            "src.api.v3.modules.extension.plugin.market_service.httpx.AsyncClient", _boom
        ):
            with pytest.raises(BadRequestError) as exc:
                await client.list_plugins()
        assert "不可达" in str(exc.value)

    async def test_upstream_500_is_readable_error(self):
        client = MarketClient(BASE)
        with _patch_client(FakeResponse(status_code=500)):
            with pytest.raises(BadRequestError) as exc:
                await client.plugin_detail("seo")
        assert "500" in str(exc.value)

    async def test_upstream_404_maps_to_not_found(self):
        client = MarketClient(BASE)
        with _patch_client(FakeResponse(status_code=404)):
            with pytest.raises(NotFoundError):
                await client.plugin_detail("nope")

    async def test_non_json_body_is_rejected(self):
        client = MarketClient(BASE)
        with _patch_client(FakeResponse(status_code=200, json_data=None)):
            with pytest.raises(BadRequestError) as exc:
                await client.list_plugins()
        assert "JSON" in str(exc.value)

    async def test_marketplace_error_code_is_rejected(self):
        client = MarketClient(BASE)
        with _patch_client(FakeResponse(json_data={"code": 40401, "message": "plugin not found"})):
            with pytest.raises(BadRequestError) as exc:
                await client.plugin_detail("seo")
        assert "plugin not found" in str(exc.value)


# ---------------------------------------------------------------- 目录与更新

@pytest.mark.asyncio
class TestDirectory:
    async def test_list_returns_items_and_total(self):
        body = {"code": 0, "data": {"items": [{"slug": "seo"}], "total": 1}}
        client = MarketClient(BASE)
        with _patch_client(FakeResponse(json_data=body)):
            data = await client.list_plugins(keyword="seo")
        assert data["total"] == 1 and data["items"][0]["slug"] == "seo"

    async def test_updates_without_installed_short_circuits(self):
        client = MarketClient(BASE)
        assert await client.updates({}) == {"updates": []}

    async def test_updates_passes_slug_version_pairs(self):
        captured = {}

        class RecordingClient(FakeAsyncClient):
            async def get(self, url, params=None):
                captured["url"] = url
                captured["params"] = params
                return FakeResponse(json_data={"code": 0, "data": {"updates": []}})

        client = MarketClient(BASE)
        with patch(
            "src.api.v3.modules.extension.plugin.market_service.httpx.AsyncClient",
            lambda *a, **kw: RecordingClient(None),
        ):
            await client.updates({"seo": "1.0.0", "shop": ""})
        assert captured["url"].endswith("/updates")
        pairs = sorted(captured["params"])
        assert ("slug", "seo:1.0.0") in pairs and ("slug", "shop:") in pairs


# ---------------------------------------------------------------- 下载与安装

@pytest.mark.asyncio
class TestDownloadAndInstall:
    async def test_checksum_mismatch_in_header_is_rejected(self):
        payload = b"PK\x03\x04fake-zip"
        client = MarketClient(BASE)
        with _patch_client(
            FakeResponse(content=payload, headers={"X-Checksum-Sha256": "0" * 64})
        ):
            with pytest.raises(BadRequestError) as exc:
                await client.download("seo", "1.0.0")
        assert "校验和" in str(exc.value)

    async def test_checksum_mismatch_with_expected_is_rejected(self):
        payload = b"PK\x03\x04fake-zip"
        client = MarketClient(BASE)
        with _patch_client(FakeResponse(content=payload, headers={})):
            with pytest.raises(BadRequestError) as exc:
                await client.download("seo", "1.0.0", expect_sha256="a" * 64)
        assert "校验和" in str(exc.value)

    async def test_matching_checksum_passes(self):
        payload = b"PK\x03\x04fake-zip"
        digest = hashlib.sha256(payload).hexdigest()
        client = MarketClient(BASE)
        with _patch_client(FakeResponse(content=payload, headers={"X-Checksum-Sha256": digest})):
            assert await client.download("seo", "1.0.0", expect_sha256=digest) == payload

    async def test_install_delegates_to_installer_after_verification(self):
        payload = b"PK\x03\x04fake-zip"
        digest = hashlib.sha256(payload).hexdigest()
        # install_from_zip 是**同步**函数（经 asyncio.to_thread 调用），因此用 MagicMock
        installer_mock = MagicMock(return_value=(True, "插件 'SEO' 安装成功", {"slug": "seo"}))
        client = MarketClient(BASE)
        with _patch_client(FakeResponse(content=payload, headers={"X-Checksum-Sha256": digest})):
            with patch(
                "shared.services.plugins.plugin_manager.installer.plugin_installer.install_from_zip",
                installer_mock,
            ):
                result = await client.install_from_market("seo", "1.0.0", expect_sha256=digest)
        assert result["sha256"] == digest
        assert result["marketplace"] == BASE
        assert installer_mock.call_count == 1, "校验通过后才交给 installer"

    async def test_install_failure_surfaces_installer_message(self):
        payload = b"PK\x03\x04fake-zip"
        digest = hashlib.sha256(payload).hexdigest()
        client = MarketClient(BASE)
        with _patch_client(FakeResponse(content=payload, headers={"X-Checksum-SHA256": digest})):
            with patch(
                "shared.services.plugins.plugin_manager.installer.plugin_installer.install_from_zip",
                MagicMock(return_value=(False, "缺少依赖: core", None)),
            ):
                with pytest.raises(BadRequestError) as exc:
                    await client.install_from_market("seo", "1.0.0")
        assert "缺少依赖" in str(exc.value)
