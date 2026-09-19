"""sensitive_word 的请求 / 响应模型"""

from typing import Optional

from pydantic import Field

from src.api.v3.core.base_schema import SchemaBase


class SensitiveWordCreate(SchemaBase):
    word: str = Field(min_length=1, max_length=100, description="敏感词内容")
    level: int = Field(default=1, ge=1, le=3, description="敏感级别 (1:低, 2:中, 3:高)")
    action: str = Field(default="block", pattern="^(block|replace|warn)$", description="处理方式")
    replacement: Optional[str] = Field(default=None, max_length=100, description="替换词")
    category: Optional[str] = Field(default=None, max_length=50, description="分类")
    is_active: bool = Field(default=True, description="是否激活")


class SensitiveWordUpdate(SchemaBase):
    word: Optional[str] = Field(default=None, min_length=1, max_length=100)
    level: Optional[int] = Field(default=None, ge=1, le=3)
    action: Optional[str] = Field(default=None, pattern="^(block|replace|warn)$")
    replacement: Optional[str] = Field(default=None, max_length=100)
    category: Optional[str] = Field(default=None, max_length=50)
    is_active: Optional[bool] = None


class SensitiveWordBatchImport(SchemaBase):
    words: list[str] = Field(min_length=1, max_length=5000, description="敏感词列表")
    level: int = Field(default=1, ge=1, le=3)
    action: str = Field(default="block", pattern="^(block|replace|warn)$")
    category: Optional[str] = Field(default=None, max_length=50)
