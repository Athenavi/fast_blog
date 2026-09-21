"""X（Twitter）适配器：**API v2 发推** ``POST /2/tweets``

    端点：``https://api.twitter.com/2``（可用渠道的 endpoint 覆盖）
    凭据：``{"access_token": "..."}`` —— OAuth 2.0 **user context** access token
          （在 X Developer Portal 建 App 后走授权码/PKCE 流程取得；写权限需要相应套餐）

  - 自检 ``verify``：``GET /users/me``；
  - 发布 ``publish``：``POST /tweets``，正文 = 标题/摘要 + 原文链接（**受 280 字符限制**，
    超出部分由适配器截断摘要并保留链接 —— 不静默丢失链接）。

⚠️ X 的长文（Articles）没有公开写接口；这里发的是标准推文（带链接）。OAuth 1.0a（consumer
key/secret + access token/secret + 签名）未实现 —— 需要时再补，当前只支持 Bearer user token。
"""

from src.api.v3.modules.content.third_party_publish.adapters import (
    ChannelConfig,
    PublishPayload,
    PublishResult,
    register_adapter,
)
from src.api.v3.modules.content.third_party_publish.builtin._http import (
    get_json,
    post_json,
    require,
)

DEFAULT_ENDPOINT = "https://api.twitter.com/2"

#: 推文长度上限（X 的硬限制）
TWEET_LIMIT = 280


def _base(channel: ChannelConfig) -> str:
    return (channel.endpoint or DEFAULT_ENDPOINT).rstrip("/")


def _headers(channel: ChannelConfig) -> dict[str, str]:
    token = require(
        channel.credentials,
        "access_token",
        "X 需要凭据 access_token（OAuth 2.0 user context token）",
    )
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def _compose_text(payload: PublishPayload) -> str:
    """组推文：标题 +（截断的）摘要 + 链接，保证不超过 280 字符且**链接不丢**"""
    title = (payload.title or "").strip()
    url = (payload.url or "").strip()
    suffix = f" {url}" if url else ""
    budget = TWEET_LIMIT - len(suffix) - 1  # 换行占 1
    head = f"{title}\n{payload.excerpt or ''}".strip()
    if len(head) > budget:
        head = head[: max(0, budget - 1)].rstrip() + "…"
    return f"{head}{suffix}".strip()


class TwitterAdapter:
    """X（Twitter）API v2"""

    platform = "twitter"
    display_name = "X / Twitter"

    async def verify(self, channel: ChannelConfig) -> PublishResult:
        payload = await get_json(f"{_base(channel)}/users/me", headers=_headers(channel))
        data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
        if not data.get("id"):
            return PublishResult.fail(f"X 没有返回用户信息：{payload}")
        return PublishResult.ok(
            message=f"凭据有效：@{data.get('username') or data.get('id')}"
        )

    async def publish(self, channel: ChannelConfig, payload: PublishPayload) -> PublishResult:
        text = _compose_text(payload)
        if not text:
            return PublishResult.fail("推文内容为空（标题/摘要/链接都没有）")

        created = await post_json(
            f"{_base(channel)}/tweets", {"text": text}, headers=_headers(channel)
        )
        data = created.get("data") if isinstance(created.get("data"), dict) else {}
        tweet_id = str(data.get("id") or "")
        if not tweet_id:
            return PublishResult.fail(f"X 没有返回推文 id：{created}")

        username = str(channel.credentials.get("username") or "").strip()
        external_url = (
            f"https://x.com/{username}/status/{tweet_id}"
            if username
            else f"https://x.com/i/status/{tweet_id}"
        )
        return PublishResult.ok(
            external_id=tweet_id,
            external_url=external_url,
            message=f"已发布推文（{len(text)}/{TWEET_LIMIT} 字符，id={tweet_id}）",
        )


register_adapter(TwitterAdapter())
