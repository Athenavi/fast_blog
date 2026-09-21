"""微博适配器：**分享接口** ``statuses/share``（官方 API，OAuth 2.0 access_token）

    端点：``https://api.weibo.com/2``（可用渠道的 endpoint 覆盖）
    凭据：``{"access_token": "..."}`` —— 微博开放平台 OAuth 2.0 授权后拿到（需应用审核）

  - 自检 ``verify``：``GET /account/get_uid.json``（能拿到 uid 才算通）；
  - 发布 ``publish``：``POST /statuses/share.json`` —— 这是微博的**分享链接**接口，
    要求正文里带 URL（正好适合"分享本站文章"）。

可选凭据：``{"share_suffix": "#技术#"（话题前缀）}``。
⚠️ ``statuses/share`` 只接受带链接的文本（微博的规则），正文超长由微博侧截断/报错会如实带回。
"""

from src.api.v3.modules.content.third_party_publish.adapters import (
    ChannelConfig,
    PublishPayload,
    PublishResult,
    register_adapter,
)
from src.api.v3.modules.content.third_party_publish.builtin._http import (
    get_json,
    post_form,
    require,
)

DEFAULT_ENDPOINT = "https://api.weibo.com/2"


def _base(channel: ChannelConfig) -> str:
    return (channel.endpoint or DEFAULT_ENDPOINT).rstrip("/")


def _token(channel: ChannelConfig) -> str:
    return require(
        channel.credentials, "access_token", "微博需要凭据 access_token（OAuth 2.0 授权所得）"
    )


class WeiboAdapter:
    """微博（statuses/share 分享接口）"""

    platform = "weibo"
    display_name = "微博"

    async def verify(self, channel: ChannelConfig) -> PublishResult:
        payload = await get_json(
            f"{_base(channel)}/account/get_uid.json", params={"access_token": _token(channel)}
        )
        uid = payload.get("uid")
        if not uid:
            return PublishResult.fail(f"微博没有返回 uid：{payload}")
        return PublishResult.ok(message=f"凭据有效，uid={uid}")

    async def publish(self, channel: ChannelConfig, payload: PublishPayload) -> PublishResult:
        if not payload.url:
            return PublishResult.fail(
                "微博的 statuses/share 接口要求正文里包含链接，但这篇文章没有可用的 URL"
            )
        prefix = str(channel.credentials.get("share_suffix") or "").strip()
        text = f"{prefix}{payload.title or ''} {payload.url}".strip()
        if payload.excerpt:
            text = f"{prefix}{payload.title or ''}：{payload.excerpt[:80]} {payload.url}".strip()

        created = await post_form(
            f"{_base(channel)}/statuses/share.json",
            {"status": text, "access_token": _token(channel)},
        )
        weibo_id = str(created.get("idstr") or created.get("id") or "")
        if not weibo_id:
            return PublishResult.fail(f"微博没有返回微博 id：{created}")
        user = created.get("user") if isinstance(created.get("user"), dict) else {}
        screen_name = str(user.get("screen_name") or "")
        external_url = (
            f"https://weibo.com/{user.get('id')}/{weibo_id}" if user.get("id") else payload.url
        )
        return PublishResult.ok(
            external_id=weibo_id,
            external_url=external_url,
            message=f"微博已发布（id={weibo_id}{'，@' + screen_name if screen_name else ''}）",
        )


register_adapter(WeiboAdapter())
