"""utility 模块的请求 / 响应模型（Pydantic v2）

端点多为公开只读或复用现有权限码，故这里的模型同时承担**请求校验**与 **OpenAPI 文档**；
service 用这些模型对源模块的真实返回值做归一化，保证对外结构稳定。
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import Field

from src.api.v3.core.base_schema import SchemaBase


class NlpParseRequest(SchemaBase):
    """``POST /utility/nlp/parse``：待解析的自然语言命令"""

    command: str = Field(
        min_length=1,
        max_length=2000,
        description="自然语言命令，如「创建文章」「删除3篇文章」「搜索 关键词」",
    )


class NlpIntentCatalogOut(SchemaBase):
    """NLP 解析器支持的能力目录（直接读源解析器的模式表）"""

    intents: List[str] = Field(default_factory=list, description="支持的意图类型")
    intent_patterns: Dict[str, List[str]] = Field(
        default_factory=dict, description="意图 → 触发关键词正则"
    )
    entity_types: List[str] = Field(default_factory=list, description="可识别的实体类型")
    time_ranges: List[str] = Field(default_factory=list, description="可识别的时间表达式")


class NlpParseResultOut(SchemaBase):
    """命令解析结果（结构与源 ``NLPCommandParser.parse_command`` 一致）"""

    original_command: str = Field(description="原始命令文本")
    intent: Optional[str] = Field(default=None, description="识别出的意图，无法识别时为 None")
    entity_type: Optional[str] = Field(default=None, description="识别出的实体类型")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="抽取到的参数")
    confidence: float = Field(default=0.0, description="意图置信度 0.0~1.0")
    timestamp: Optional[str] = Field(default=None, description="解析时间（ISO 8601）")
    error: Optional[str] = Field(default=None, description="无法识别意图时的原因")


class UserVipStatusOut(SchemaBase):
    """用户 VIP 状态（由 ``user_defs.is_vip`` 判定）"""

    user_id: int
    is_vip: bool = Field(description="是否为 VIP（源 is_vip 判定结果）")
    vip_level: Optional[int] = Field(default=None, description="缓存 VIP 等级字段")
    vip_expires_at: Optional[datetime] = Field(default=None, description="VIP 过期时间")


class BlockPatternDefOut(SchemaBase):
    """区块模式定义展开结果（由 ``block_pattern_defs.to_pattern_dict`` 产出）"""

    name: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    blocks: List[Any] = Field(default_factory=list, description="解析后的块数据列表")
    keywords: List[str] = Field(default_factory=list, description="关键词列表")
    thumbnail: Optional[str] = None
    viewport_width: Optional[int] = None
    is_public: bool = False
    created_at: Optional[str] = Field(default=None, description="ISO 8601 字符串")
    updated_at: Optional[str] = Field(default=None, description="ISO 8601 字符串")
