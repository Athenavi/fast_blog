"""微信公众号适配器：**草稿箱 + 发布**（官方 API，全程真实调用）

流程（每一步都是真实请求）：

  1. ``access_token``：``GET /cgi-bin/token``（进程内按 appid 缓存，提前 5 分钟过期）；
  2. **封面**：草稿的 ``thumb_media_id`` 必须是**永久素材** —— 优先用凭据里的 ``thumb_media_id``，
     否则用 ``cover_image_url`` 下载后 ``POST /cgi-bin/material/add_material?type=image`` 上传；
  3. 建草稿：``POST /cgi-bin/draft/add``；
  4. 可选发布：``POST /cgi-bin/freepublish/submit``（异步，返回 ``publish_id``）。

凭据：``{"appid": "...", "appsecret": "...", "thumb_media_id": "..."}``
或 ``{"appid": "...", "appsecret": "...", "cover_image_url": "https://..."}``；
可选 ``{"author": "...", "content_source_url": "...", "publish_immediately": true}``。

⚠️ 调用方服务器 IP 必须在公众号后台的 **IP 白名单**里，否则会收到 ``errcode=40164`` ——
适配器会把微信给的原因原样带出来（不吞错）。认证服务号才有该接口权限。
"""

import time
from typing import Any

import httpx

from src.api.v3.core.exceptions import BadRequestError
from src.api.v3.modules.content.third_party_publish.adapters import (
    ChannelConfig,
    PublishPayload,
    PublishResult,
    register_adapter,
)
from src.api.v3.modules.content.third_party_publish.builtin._http import (
    DEFAULT_TIMEOUT,
    extract_error,
    post_json,
    require,
)

DEFAULT_ENDPOINT = "https://api.weixin.qq.com"

#: access_token 进程内缓存：appid → (token, 过期时间戳)
_TOKEN_CACHE: dict[str, tuple[str, float]] = {}

#: 提前多久认为 token 过期（秒）
_TOKEN_SAFETY_MARGIN = 300


def _base(channel: ChannelConfig) -> str:
    return (channel.endpoint or DEFAULT_ENDPOINT).rstrip("/")


async def _access_token(channel: ChannelConfig) -> str:
    """取 access_token（带进程内缓存；微信按日限次，不能每次都现取）"""
    appid = require(channel.credentials, "appid", "微信适配器需要凭据 appid")
    cached = _TOKEN_CACHE.get(appid)
    if cached and cached[1] > time.time():
        return cached[0]

    appsecret = require(channel.credentials, "appsecret", "微信适配器需要凭据 appsecret")
    payload = await post_json(
        f"{_base(channel)}/cgi-bin/token",
        {},
        params={"grant_type": "client_credential", "appid": appid, "secret": appsecret},
    )
    token = str(payload.get("access_token") or "")
    if not token:
        raise BadRequestError(f"微信没有返回 access_token：{extract_error(payload, '未知原因')}")
    expires_in = int(payload.get("expires_in") or 7200)
    _TOKEN_CACHE[appid] = (token, time.time() + max(60, expires_in - _TOKEN_SAFETY_MARGIN))
    return token


async def _upload_cover(channel: ChannelConfig, url: str) -> str:
    """把封面图下载后上传为**永久素材**，返回 media_id（草稿封面要求永久素材）"""
    try:
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT, follow_redirects=True) as client:
            downloaded = await client.get(url)
    except httpx.HTTPError as exc:
        raise BadRequestError(f"下载封面图失败（{url}）：{exc}") from exc
    if downloaded.status_code >= 400:
        raise BadRequestError(f"下载封面图失败（HTTP {downloaded.status_code}）：{url}")

    content_type = downloaded.headers.get("Content-Type") or "image/jpeg"
    filename = url.rsplit("/", 1)[-1].split("?")[0] or "cover.jpg"
    token = await _access_token(channel)
    try:
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            resp = await client.post(
                f"{_base(channel)}/cgi-bin/material/add_material",
                params={"access_token": token, "type": "image"},
                files={"media": (filename, downloaded.content, content_type)},
            )
    except httpx.HTTPError as exc:
        raise BadRequestError(f"上传封面素材失败：{exc}") from exc

    payload = resp.json() if resp.content else {}
    if resp.status_code >= 400 or not isinstance(payload, dict) or not payload.get("media_id"):
        raise BadRequestError(
            f"微信拒绝了封面素材（HTTP {resp.status_code}）：{extract_error(payload, (resp.text or '')[:200])}"
        )
    return str(payload["media_id"])


class WechatMpAdapter:
    """微信公众号（草稿箱 + 发布）"""

    platform = "wechat_mp"
    display_name = "微信公众号"

    async def verify(self, channel: ChannelConfig) -> PublishResult:
        """真实自检：能拿到 access_token 才算通（这是微信所有接口的前提）"""
        token = await _access_token(channel)
        return PublishResult.ok(message=f"凭据有效，access_token 长度 {len(token)}")

    async def publish(self, channel: ChannelConfig, payload: PublishPayload) -> PublishResult:
        token = await _access_token(channel)

        thumb_media_id = str(channel.credentials.get("thumb_media_id") or "").strip()
        if not thumb_media_id:
            cover_url = str(channel.credentials.get("cover_image_url") or "").strip()
            if not cover_url:
                return PublishResult.fail(
                    "微信公众号草稿要求封面图：请在凭据里提供 thumb_media_id（永久素材 ID）"
                    "或 cover_image_url（由适配器下载并上传为永久素材）"
                )
            thumb_media_id = await _upload_cover(channel, cover_url)

        article: dict[str, Any] = {
            "title": (payload.title or "未命名")[:64],
            "author": str(channel.credentials.get("author") or payload.author or "")[:8],
            "digest": (payload.excerpt or "")[:120],
            "content": payload.content or f"<p>{payload.excerpt or payload.title or ''}</p>",
            "content_source_url": str(
                channel.credentials.get("content_source_url") or payload.url or ""
            )[:200],
            "thumb_media_id": thumb_media_id,
            "need_open_comment": 0,
            "only_fans_can_comment": 0,
        }
        draft = await post_json(
            f"{_base(channel)}/cgi-bin/draft/add",
            {"articles": [article]},
            params={"access_token": token},
        )
        draft_media_id = str(draft.get("media_id") or "")
        if not draft_media_id:
            raise BadRequestError(f"微信没有返回草稿 media_id：{extract_error(draft, '未知原因')}")

        publish_immediately = bool(channel.credentials.get("publish_immediately", False))
        if not publish_immediately:
            return PublishResult.ok(
                external_id=draft_media_id,
                message=f"已存入公众号草稿箱（media_id={draft_media_id}）",
            )

        submitted = await post_json(
            f"{_base(channel)}/cgi-bin/freepublish/submit",
            {"media_id": draft_media_id},
            params={"access_token": token},
        )
        publish_id = str(submitted.get("publish_id") or "")
        if not publish_id:
            raise BadRequestError(
                f"微信没有返回 publish_id：{extract_error(submitted, '未知原因')}（草稿已创建，media_id="
                f"{draft_media_id}）"
            )
        return PublishResult.ok(
            external_id=publish_id,
            message=f"已提交发布（draft media_id={draft_media_id}，publish_id={publish_id}，发布为异步）",
        )


register_adapter(WechatMpAdapter())
