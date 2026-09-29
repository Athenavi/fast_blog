"""amp 模块的请求模型"""

from typing import Optional

from pydantic import Field

from src.api.v3.core.base_schema import SchemaBase


class AmpValidateRequest(SchemaBase):
    """校验一段 HTML 是否符合 AMP 规范"""

    html: str = Field(min_length=1, max_length=500_000)


class AmpConvertRequest(SchemaBase):
    """把一段 HTML 转换成 AMP 文档（可附带标题 / 作者 / canonical 等元信息）"""

    html: str = Field(min_length=1, max_length=500_000, description="待转换的正文 HTML")
    title: Optional[str] = Field(default=None, max_length=255)
    author_name: Optional[str] = Field(default=None, max_length=255)
    canonical_url: Optional[str] = Field(default=None, max_length=500)
    site_name: Optional[str] = Field(default=None, max_length=255)
    featured_image: Optional[str] = Field(default=None, max_length=1000)
    published_at: Optional[str] = Field(
        default=None, max_length=64, description="ISO 时间字符串，可空"
    )
    extra_css: Optional[str] = Field(
        default=None, max_length=200_000, description="额外 CSS，会并入 <style amp-custom>"
    )
