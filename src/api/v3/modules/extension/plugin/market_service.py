"""远程插件市场客户端。

市场服务端由站点自建（实现见仓库 ``plugin-market-server/``，契约见其 ``API.md``）。

设计要点（都对应一个明确的失败姿势，不做静默降级）：

  - **未配置即报错**：没设 ``PLUGIN_MARKETPLACE_URL`` 时必须明说"未配置"，
    绝不能返回空列表冒充"市场里没有插件"。
  - **不可达即报错**：超时/连接失败/4xx/5xx/非 JSON 都转成可读错误（含 URL 与状态码）。
  - **下载必须验校验和**：比对响应头 ``X-Checksum-Sha256`` 与包内容的 sha256，
    不一致直接拒绝安装（篡改或传输损坏都不该进 ``plugins/``）。
  - 出站地址来自**管理员配置**，可指向内网自建市场，故此处不做私网地址拦截。
"""

import asyncio
import hashlib
import os
import tempfile
from typing import Any, Dict, Optional

import httpx

from src.api.v3.core.exceptions import BadRequestError, NotFoundError
from src.api.v3.core.logger import get_logger

logger = get_logger("extension.plugin.market")

_API_TIMEOUT = 10.0
_DOWNLOAD_TIMEOUT = 30.0


class MarketClient:
    """远程市场访问封装（每次调用现开连接，不共享长连接状态）"""

    def __init__(self, base_url: Optional[str] = None, *, timeout: float = _API_TIMEOUT) -> None:
        raw = base_url if base_url is not None else os.environ.get("PLUGIN_MARKETPLACE_URL", "")
        self.base_url = (raw or "").strip().rstrip("/")
        self.timeout = timeout

    # ---------------------------------------------------------------- 基础

    @property
    def configured(self) -> bool:
        return bool(self.base_url)

    def _require_configured(self) -> str:
        if not self.configured:
            raise BadRequestError(
                "未配置远程插件市场：请设置环境变量 PLUGIN_MARKETPLACE_URL"
                "（自建服务端见仓库 plugin-market-server/）"
            )
        return self.base_url

    async def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> httpx.Response:
        base = self._require_configured()
        url = f"{base}{path}"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, params=params)
        except httpx.HTTPError as exc:
            raise BadRequestError(f"插件市场不可达（{url}）：{exc}") from exc
        if response.status_code == 404:
            raise NotFoundError(f"插件市场中不存在（{url}）")
        if response.status_code >= 400:
            raise BadRequestError(f"插件市场返回 {response.status_code}（{url}）")
        return response

    async def _get_json(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        response = await self._get(path, params)
        try:
            body = response.json()
        except ValueError as exc:
            raise BadRequestError(f"插件市场响应不是合法 JSON（{path}）") from exc
        if isinstance(body, dict):
            if body.get("code") not in (0, None):
                raise BadRequestError(
                    f"插件市场返回错误：{body.get('message') or body.get('code')}"
                )
            return body.get("data")
        return body

    # ---------------------------------------------------------------- 目录

    async def list_plugins(
        self,
        *,
        keyword: str = "",
        category: str = "",
        page: int = 1,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        data = await self._get_json(
            "/plugins",
            {
                "keyword": keyword or None,
                "category": category or None,
                "page": page,
                "page_size": page_size,
            },
        )
        return data or {"items": [], "total": 0, "page": page, "page_size": page_size}

    async def plugin_detail(self, slug: str) -> Dict[str, Any]:
        data = await self._get_json(f"/plugins/{slug}")
        if not isinstance(data, dict):
            raise BadRequestError(f"插件市场返回了非预期的详情结构（{slug}）")
        return data

    async def updates(self, installed: Dict[str, str]) -> Dict[str, Any]:
        """``installed``：``{slug: 当前版本}`` → 只回有更新的条目"""
        if not installed:
            return {"updates": []}
        params = [("slug", f"{slug}:{version or ''}") for slug, version in installed.items()]
        data = await self._get_json("/updates", params)
        return data or {"updates": []}

    # ---------------------------------------------------------------- 下载与安装

    async def download(self, slug: str, version: str, expect_sha256: str = "") -> bytes:
        """下载插件包；校验和不符一律拒绝（返回前即抛错）。"""
        base = self._require_configured()
        url = f"{base}/plugins/{slug}/download/{version}"
        try:
            async with httpx.AsyncClient(timeout=_DOWNLOAD_TIMEOUT) as client:
                response = await client.get(url)
        except httpx.HTTPError as exc:
            raise BadRequestError(f"下载插件包失败（{url}）：{exc}") from exc
        if response.status_code >= 400:
            raise BadRequestError(f"下载插件包失败：市场返回 {response.status_code}（{url}）")

        content = response.content
        actual = hashlib.sha256(content).hexdigest()
        declared = (response.headers.get("X-Checksum-Sha256") or "").strip().lower()
        if declared and declared != actual:
            raise BadRequestError("插件包校验和与市场声明不一致，已拒绝（可能被篡改或传输损坏）")
        if expect_sha256 and expect_sha256.strip().lower() != actual:
            raise BadRequestError("插件包校验和与请求所声明的不一致，已拒绝安装")
        return content

    async def install_from_market(
        self,
        slug: str,
        version: str,
        *,
        expect_sha256: str = "",
    ) -> Dict[str, Any]:
        """下载 → 验签 → 交给既有 ``PluginInstaller`` 安装（依赖/兼容检查都在那边）。"""
        from shared.services.plugins.plugin_manager.installer import plugin_installer

        content = await self.download(slug, version, expect_sha256)
        digest = hashlib.sha256(content).hexdigest()

        tmp_path = ""
        try:
            with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as handle:
                handle.write(content)
                tmp_path = handle.name
            # installer 是同步实现（zipfile + 目录拷贝），放线程池避免阻塞事件循环
            ok, message, metadata = await asyncio.to_thread(
                plugin_installer.install_from_zip, tmp_path
            )
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except OSError:
                    logger.warning("清理插件临时包失败: %s", tmp_path)

        if not ok:
            raise BadRequestError(f"安装失败：{message}")

        logger.info("从市场安装插件 %s@%s（sha256=%s…）", slug, version, digest[:12])
        return {
            "slug": slug,
            "version": version,
            "sha256": digest,
            "marketplace": self.base_url,
            "message": message,
            "metadata": metadata or {},
        }


market_client = MarketClient()
