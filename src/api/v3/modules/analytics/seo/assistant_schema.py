"""analytics/seo 的请求模型（SEO 生成 / 保存）"""

from typing import Optional

from pydantic import Field

from src.api.v3.core.base_schema import SchemaBase


class SEOSaveRequest(SchemaBase):
    """手工保存 SEO 元信息（写 ``article_seo`` 真表）"""

    seo_title: Optional[str] = Field(default=None, max_length=255)
    seo_description: Optional[str] = None
    seo_keywords: Optional[str] = Field(
        default=None, max_length=255, description="逗号分隔的关键词（生成结果会自动 join）"
    )
    og_title: Optional[str] = Field(default=None, max_length=255)
    og_description: Optional[str] = None
    og_image: Optional[str] = Field(default=None, max_length=500)
    og_type: Optional[str] = Field(default=None, max_length=50)
    twitter_title: Optional[str] = Field(default=None, max_length=255)
    twitter_description: Optional[str] = None
    twitter_image: Optional[str] = Field(default=None, max_length=500)
    twitter_card: Optional[str] = Field(default=None, max_length=50)
    canonical_url: Optional[str] = Field(default=None, max_length=500)
    robots_meta: Optional[str] = Field(default=None, max_length=255)
    schema_org_enabled: Optional[bool] = None
    schema_org_type: Optional[str] = Field(default=None, max_length=50)


class SEOGenerateRequest(SchemaBase):
    """用真实 LLM 生成 SEO 元信息"""

    config_id: Optional[int] = Field(
        default=None, description="AI 配置 ID；留空则用第一条配置"
    )
    apply: bool = Field(default=False, description="true 时把生成结果写入 article_seo")
    max_tokens: Optional[int] = Field(default=None, ge=1, le=32000)


class SchemaPreviewRequest(SchemaBase):
    """生成 JSON-LD 结构化数据预览（不落库）

    ``params`` 直接透传给生成器，例如 Article 需要 ``title`` / ``description`` / ``url`` / ``author_name``。
    """

    schema_type: str = Field(default="Article", max_length=50)
    params: dict = Field(default_factory=dict)
    base_url: Optional[str] = Field(default=None, max_length=500, description="覆盖站点基址")
