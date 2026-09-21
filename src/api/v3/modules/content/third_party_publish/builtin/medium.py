"""Medium 适配器：Integration Token API（官方 REST）

    端点：``https://api.medium.com/v1``（可用渠道的 endpoint 覆盖）
    凭据：``{"integration_token": "..."}`` —— Medium 后台 Settings → Security and apps
          → Integration tokens 生成
    可选：``{"publish_status": "public" | "draft"（默认 draft）, "content_format": "html" | "markdown"}``

流程（真实调用）：
  1. 自检 ``verify``：``GET /v1/me``（拿到用户信息才算通）；
  2. 发布 ``publish``：``GET /v1/me`` 取作者 id → ``POST /v1/users/{authorId}/posts``。

⚠️ Medium 已收紧新 token 的发放（老 token 仍可用）；凭据无效时会带出 Medium 给的原因。
"""

from typing import Any

from src.api.v3.modules.content.third_party_publish.adapters import (
    ChannelConfig,
    PublishPayload,
    PublishResult,
    register_adapter,
)
from src.api.v3.modules.content.third_party_publish.builtin._http import get_json, post_json, require

DEFAULT_ENDPOINT = "https://api.medium.com/v1"


def _base(channel: ChannelConfig) -> str:
    return (channel.endpoint or DEFAULT_ENDPOINT).rstrip("/")


def _headers(channel: ChannelConfig) -> dict[str, str]:
    token = require(
        channel.credentials, "integration_token", "Medium 需要凭据 integration_token"
    )
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _me(channel: ChannelConfig) -> Any:
    return get_json(f"{_base(channel)}/me", headers=_headers(channel))


class MediumAdapter:
    """Medium（Integration Token API）"""

    platform = "medium"
    display_name = "Medium"

    async def verify(self, channel: ChannelConfig) -> PublishResult:
        payload = await _me(channel)
        data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
        if not data.get("id"):
            return PublishResult.fail(f"Medium 没有返回用户信息：{payload}")
        return PublishResult.ok(
            message=f"凭据有效：{data.get('name') or data.get('username') or data.get('id')}"
        )

    async def publish(self, channel: ChannelConfig, payload: PublishPayload) -> PublishResult:
        me = await _me(channel)
        author = me.get("data") if isinstance(me.get("data"), dict) else {}
        author_id = str(author.get("id") or "")
        if not author_id:
            return PublishResult.fail("Medium 没有返回作者 id，无法发布")

        status = str(channel.credentials.get("publish_status") or "draft")
        if status not in ("public", "draft", "unlisted"):
            status = "draft"
        content_format = str(channel.credentials.get("content_format") or "html")
        if content_format not in ("html", "markdown"):
            content_format = "html"

        body: dict[str, Any] = {
            "title": payload.title or "Untitled",
            "contentFormat": content_format,
            "content": payload.content or payload.excerpt or payload.title or "",
            "tags": (payload.tags or [])[:5],  # Medium 最多 5 个标签
            "publishStatus": status,
        }
        if payload.url:
            body["canonicalUrl"] = payload.url

        created = await post_json(
            f"{_base(channel)}/users/{author_id}/posts", body, headers=_headers(channel)
        )
        data = created.get("data") if isinstance(created.get("data"), dict) else {}
        post_id = str(data.get("id") or "")
        if not post_id:
            return PublishResult.fail(f"Medium 没有返回文章 id：{created}")
        return PublishResult.ok(
            external_id=post_id,
            external_url=str(data.get("url") or "") or None,
            message=f"Medium 已创建文章（{status}，id={post_id}）",
        )


register_adapter(MediumAdapter())
