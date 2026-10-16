"""ops.cdn 模块的请求 / 响应模型（凭据脱敏）"""

from typing import Optional

from pydantic import Field

from src.api.v3.core.base_schema import SchemaBase

SUPPORTED_PROVIDERS = ("cloudflare", "aws_cloudfront", "aliyun_cdn", "tencent_cdn", "custom")


class CDNConfigPayload(SchemaBase):
    provider: str = Field(description="提供商：cloudflare/aws_cloudfront/aliyun_cdn/tencent_cdn/custom")
    domain: Optional[str] = Field(default=None, max_length=255, description="加速域名")
    cdn_url: Optional[str] = Field(default=None, max_length=500, description="CDN 资源前缀 URL")
    api_token: Optional[str] = Field(default=None, description="API 凭据（入参），落库前脱敏；留空保持原值")
    zone_id: Optional[str] = Field(default=None, max_length=100)
    settings: Optional[dict] = Field(default=None, description="缓存/压缩等开关（JSON）")
    is_active: bool = Field(default=False, description="是否启用 CDN 静态资源前缀")


class CDNConfigOut(SchemaBase):
    provider: Optional[str] = None
    domain: Optional[str] = None
    cdn_url: Optional[str] = None
    has_api_token: bool = False
    zone_id: Optional[str] = None
    settings: Optional[dict] = None
    is_active: bool = False
    updated_at: Optional[str] = None


class CDNPurgePayload(SchemaBase):
    """清缓存 / 预热的入参"""

    urls: list[str] = Field(default_factory=list, description="要处理的 URL 列表")
    purge_everything: bool = Field(default=False, description="全量清理（仅 Cloudflare 支持）")


class CDNPurgeResult(SchemaBase):
    """远端动作结果（``success=false`` 的情况一律由异常承载，不会返回"看起来成功"）"""

    provider: str
    success: bool = True
    status_code: Optional[int] = None
    purge_everything: bool = False
    urls: list[str] = Field(default_factory=list)
    message: Optional[str] = None
