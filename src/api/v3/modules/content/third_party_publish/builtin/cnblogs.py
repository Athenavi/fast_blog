"""博客园适配器：**MetaWeblog（XML-RPC）**，博客园官方支持的发布接口

    端点：``https://rpc.cnblogs.com/metaweblog/{blogApp}``（blogApp 通常是你的博客园用户名；
          也可直接在渠道里覆盖 endpoint）
    凭据：``{"blog_app": "...", "username": "...", "password": "..."}``
          —— ``password`` 填博客园后台「设置 → 其他设置 → MetaWeblog」里生成的**访问令牌**
    可选：``{"blog_id": "", "categories": "栏目1,栏目2", "publish_immediately": true}``

    自检 ``verify``：调标准方法 ``blogger.getUsersBlogs``（**能拿到博客列表才算通**，不是只查参数齐全）；
    发布 ``publish``：``metaWeblog.newPost``，struct 带 title / description(HTML) / mt_keywords(标签)。

XML-RPC 的编解码用标准库 ``xmlrpc.client``（真实协议），传输交给 httpx。
"""

import xmlrpc.client
from typing import Any

from src.api.v3.core.exceptions import BadRequestError
from src.api.v3.modules.content.third_party_publish.adapters import (
    ChannelConfig,
    PublishPayload,
    PublishResult,
    register_adapter,
)
from src.api.v3.modules.content.third_party_publish.builtin._http import post_raw, require

#: 博客园 MetaWeblog 端点模板
DEFAULT_ENDPOINT = "https://rpc.cnblogs.com/metaweblog/{blog_app}"

#: 发布后的文章地址规律（MetaWeblog 只回 postid，不回 URL）
POST_URL_TEMPLATE = "https://www.cnblogs.com/{blog_app}/p/{post_id}.html"


def _endpoint(channel: ChannelConfig) -> str:
    if channel.endpoint:
        return channel.endpoint.rstrip("/")
    blog_app = require(
        channel.credentials,
        "blog_app",
        "博客园适配器需要凭据 blog_app（通常是你的博客园用户名）",
    )
    return DEFAULT_ENDPOINT.format(blog_app=blog_app)


async def _call(channel: ChannelConfig, method: str, params: list) -> Any:
    """发一次 XML-RPC 调用并取回值（fault 响应按失败抛出）"""
    # 注意：xmlrpc.client.dumps 只接受 tuple（传 list 会 assert 失败）
    request_xml = xmlrpc.client.dumps(
        tuple(params), methodname=method, encoding="utf-8", allow_none=False
    )
    resp = await post_raw(
        _endpoint(channel),
        request_xml.encode("utf-8"),
        headers={"Content-Type": "text/xml; charset=utf-8"},
    )
    if resp.status_code >= 400:
        raise BadRequestError(
            f"博客园 XML-RPC 返回 HTTP {resp.status_code}：{(resp.text or '')[:200]}"
        )
    try:
        values, _method = xmlrpc.client.loads(resp.text)
    except xmlrpc.client.Fault as exc:
        raise BadRequestError(f"博客园拒绝调用（{exc.faultCode}）：{exc.faultString}") from exc
    except Exception as exc:  # noqa: BLE001 - 解析不了也要如实报，不能当成功
        raise BadRequestError(
            f"博客园返回了无法解析的 XML-RPC 响应：{(resp.text or '')[:200]}"
        ) from exc
    return values[0] if values else None


class CnblogsAdapter:
    """博客园（MetaWeblog）"""

    platform = "cnblogs"
    display_name = "博客园"

    async def verify(self, channel: ChannelConfig) -> PublishResult:
        username = require(channel.credentials, "username", "需要凭据 username（博客园用户名）")
        password = require(
            channel.credentials, "password", "需要凭据 password（博客园「访问令牌」）"
        )
        blogs = await _call(channel, "blogger.getUsersBlogs", ["", username, password])
        if not isinstance(blogs, list) or not blogs:
            return PublishResult.fail("博客园没有返回任何博客（访问令牌可能无效或权限不足）")
        names = ", ".join(
            str(blog.get("blogName") or blog.get("url") or "?")
            for blog in blogs
            if isinstance(blog, dict)
        )
        return PublishResult.ok(message=f"凭据有效，可用博客：{names or '（未命名）'}")

    async def publish(self, channel: ChannelConfig, payload: PublishPayload) -> PublishResult:
        username = require(channel.credentials, "username", "需要凭据 username（博客园用户名）")
        password = require(
            channel.credentials, "password", "需要凭据 password（博客园「访问令牌」）"
        )
        blog_id = str(channel.credentials.get("blog_id") or "")
        publish_immediately = bool(channel.credentials.get("publish_immediately", True))

        struct: dict[str, Any] = {
            "title": payload.title or "未命名",
            "description": payload.content or payload.excerpt or "",
            "mt_keywords": ",".join(payload.tags or []),
            "post_status": "publish" if publish_immediately else "draft",
        }
        categories = str(channel.credentials.get("categories") or "").strip()
        if categories:
            struct["categories"] = [part.strip() for part in categories.split(",") if part.strip()]

        post_id = await _call(
            channel,
            "metaWeblog.newPost",
            [blog_id, username, password, struct, publish_immediately],
        )
        external_id = str(post_id or "")
        if not external_id:
            return PublishResult.fail("博客园没有返回文章 ID（发布可能未生效）")

        blog_app = str(channel.credentials.get("blog_app") or username)
        external_url = (
            POST_URL_TEMPLATE.format(blog_app=blog_app, post_id=external_id)
            if str(external_id).isdigit() and blog_app
            else (payload.url or None)
        )
        return PublishResult.ok(
            external_id=external_id,
            external_url=external_url,
            message=f"博客园已{'发布' if publish_immediately else '存为草稿'}（postid={external_id}）",
        )


register_adapter(CnblogsAdapter())
