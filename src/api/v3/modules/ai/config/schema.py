"""ai.config 模块的请求 / 响应模型（api_key 只写不读）"""

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import Field

from src.api.v3.core.base_schema import SchemaBase


class AIConfigCreate(SchemaBase):
    user_id: int = Field(description="归属用户 ID")
    name: str = Field(min_length=1, max_length=100)
    api_url: str = Field(min_length=1, max_length=500, description="base_url 或完整端点")
    api_key: str = Field(min_length=1, description="API Key 明文（入参），落库前按「用户密码 + SECRET_KEY」派生密钥加密")
    model: str = Field(min_length=1, max_length=100)
    provider: str = Field(
        default="openai",
        max_length=50,
        description="协议/厂商：openai 兼容系（deepseek/qwen/ollama/azure…）或 anthropic",
    )
    api_version: Optional[str] = Field(
        default=None, max_length=100, description="Anthropic 的 anthropic-version / Azure 的 api-version"
    )
    extra_headers: Optional[Dict[str, Any]] = Field(
        default=None, description="自定义请求头（如 Azure 的 api-key、自建网关鉴权）"
    )
    max_tokens: int = Field(default=1024, ge=1, le=128000)
    is_active: bool = False
    sort_order: int = Field(default=0, ge=0)


class AIConfigUpdate(SchemaBase):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    api_url: Optional[str] = Field(default=None, min_length=1, max_length=500)
    api_key: Optional[str] = Field(default=None, description="留空保持原值")
    model: Optional[str] = Field(default=None, min_length=1, max_length=100)
    provider: Optional[str] = Field(default=None, max_length=50)
    api_version: Optional[str] = Field(default=None, max_length=100)
    extra_headers: Optional[Dict[str, Any]] = None
    max_tokens: Optional[int] = Field(default=None, ge=1, le=128000)
    is_active: Optional[bool] = None
    sort_order: Optional[int] = Field(default=None, ge=0)


class AIConfigOut(SchemaBase):
    id: int
    user_id: int
    name: Optional[str] = None
    api_url: Optional[str] = None
    has_api_key: bool = False
    model: Optional[str] = None
    provider: Optional[str] = None
    api_version: Optional[str] = None
    extra_headers: Optional[Dict[str, Any]] = None
    max_tokens: int = 1024
    is_active: bool = False
    sort_order: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class AIConfigTestOut(SchemaBase):
    """连接测试结果（真实调用一次 LLM）"""

    ok: bool = True
    provider: Optional[str] = None
    protocol: Optional[str] = None
    model: Optional[str] = None
    reply: Optional[str] = None
    latency_ms: Optional[int] = None
    usage: Dict[str, int] = Field(default_factory=dict)
