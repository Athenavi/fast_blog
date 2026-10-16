"""发布适配器注册表 —— 多平台发布的**唯一扩展点**（2026-09-21 批次 18）

底座（渠道配置 / 发布任务 / 尝试记录 / 手动重试）已经完整可用；**"怎么发到某个平台"
由适配器决定**。本期**注册表为空**：适配器按用户给定的平台清单逐个补，补一个就多一个可用平台。

**没有适配器的平台一律如实失败**：任务置 ``failed``、``last_error`` 写明
``未实现该平台的发布适配器（platform=xxx）``，并落一条 failed 日志。
底座里**没有任何"假装成功"的路径** —— 这是本仓对 mock 的硬约定。

新接一个平台的步骤：

  1. 写一个满足 ``PublishAdapter`` 协议的类（``platform`` / ``display_name`` /
     ``verify`` / ``publish``）；
  2. 在本模块底部 ``register_adapter(...)`` 注册（幂等：同平台重复注册抛错）；
  3. 在 ``config/models.yaml`` 的渠道说明里补充该平台的凭据字段名（供前端表单提示）；
  4. 端到端跑通一次真实发布（无凭据/无沙箱平台用 verify 覆盖凭据校验路径）。
"""

from dataclasses import dataclass, field
from typing import Any, Optional, Protocol


class AdapterNotRegisteredError(RuntimeError):
    """该平台尚未实现适配器（**如实失败**，绝不假装发布成功）"""


@dataclass
class PublishPayload:
    """发布载荷：创建任务时从文章生成的**快照**（重试复用同一份，保证可复现）"""

    article_id: int
    title: str
    slug: Optional[str] = None
    excerpt: Optional[str] = None
    content: Optional[str] = None
    #: 站内相对链接（如 ``/articles/hello``）；是否转绝对地址由适配器按平台要求处理
    url: Optional[str] = None
    author: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    published_at: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "article_id": self.article_id,
            "title": self.title,
            "slug": self.slug,
            "excerpt": self.excerpt,
            "content": self.content,
            "url": self.url,
            "author": self.author,
            "tags": list(self.tags),
            "published_at": self.published_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PublishPayload":
        return cls(
            article_id=int(data.get("article_id") or 0),
            title=str(data.get("title") or ""),
            slug=data.get("slug"),
            excerpt=data.get("excerpt"),
            content=data.get("content"),
            url=data.get("url"),
            author=data.get("author"),
            tags=[str(item) for item in (data.get("tags") or [])],
            published_at=data.get("published_at"),
        )


@dataclass
class ChannelConfig:
    """解密后的渠道配置（**只传给适配器**，不进日志、不回传前端）"""

    id: int
    name: str
    platform: str
    endpoint: Optional[str] = None
    credentials: dict[str, Any] = field(default_factory=dict)

    def to_safe_dict(self) -> dict[str, Any]:
        """去掉凭据的版本（可安全写日志 / 返回给前端）"""
        return {
            "id": self.id,
            "name": self.name,
            "platform": self.platform,
            "endpoint": self.endpoint,
        }


@dataclass
class PublishResult:
    """适配器返回结果"""

    success: bool
    external_id: Optional[str] = None
    external_url: Optional[str] = None
    message: Optional[str] = None

    @classmethod
    def ok(
        cls,
        *,
        external_id: Optional[str] = None,
        external_url: Optional[str] = None,
        message: Optional[str] = None,
    ) -> "PublishResult":
        return cls(True, external_id=external_id, external_url=external_url, message=message)

    @classmethod
    def fail(cls, message: str) -> "PublishResult":
        return cls(False, message=message)


class PublishAdapter(Protocol):
    """平台发布适配器协议（结构子类型：不要求显式继承）"""

    #: 平台标识（唯一 key，写入 ``publish_channels.platform``）
    platform: str
    #: 展示名（前端下拉与错误提示用）
    display_name: str

    async def verify(self, channel: ChannelConfig) -> PublishResult:
        """凭据 / 连通性自检（不产生对外发布）"""
        ...

    async def publish(self, channel: ChannelConfig, payload: PublishPayload) -> PublishResult:
        """执行发布；**失败必须返回 ``PublishResult.fail(...)`` 或抛异常**，不要吞掉"""
        ...


#: 已注册适配器（platform -> adapter）
ADAPTERS: dict[str, PublishAdapter] = {}


def register_adapter(adapter: PublishAdapter) -> None:
    """注册适配器（同平台重复注册直接抛错，避免静默覆盖）"""
    platform = str(getattr(adapter, "platform", "") or "").strip()
    if not platform:
        raise ValueError("适配器必须声明非空的 platform")
    if platform in ADAPTERS:
        raise ValueError(f"平台适配器重复注册: {platform}")
    ADAPTERS[platform] = adapter


def get_adapter(platform: str) -> Optional[PublishAdapter]:
    """取适配器；未实现返回 ``None``（调用方据此如实失败）"""
    return ADAPTERS.get(str(platform or "").strip())


def require_adapter(platform: str) -> PublishAdapter:
    """取适配器；未实现抛 ``AdapterNotRegisteredError``"""
    adapter = get_adapter(platform)
    if adapter is None:
        raise AdapterNotRegisteredError(
            f"未实现该平台的发布适配器（platform={platform}）；"
            f"当前可用平台：{sorted(ADAPTERS) or '（暂无）'}"
        )
    return adapter


def adapter_platforms() -> list[dict[str, str]]:
    """已注册平台清单（前端下拉用；空列表表示暂无可用适配器）"""
    return [
        {
            "platform": platform,
            "display_name": str(getattr(adapter, "display_name", platform)),
        }
        for platform, adapter in sorted(ADAPTERS.items())
    ]


def load_builtin_adapters() -> None:
    """导入内置适配器包（每个平台一个模块，**导入即注册**）

    单独放函数里并容错：某个平台模块写坏了不该让整个 API 起不来 ——
    但要留下**警告**（否则就成了"静默少了一批平台"，与"如实"相悖）。
    """
    try:
        from src.api.v3.modules.content.third_party_publish import builtin  # noqa: F401
    except Exception as exc:  # noqa: BLE001 - 平台模块的导入错误不拖垮应用，但必须出声
        import logging

        logging.getLogger("third_party_publish").warning("内置平台适配器加载失败：%s", exc)


load_builtin_adapters()
