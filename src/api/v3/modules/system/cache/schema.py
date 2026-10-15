"""cache 模块的请求/响应模型"""

from typing import Any, Dict, List

from pydantic import Field

from src.api.v3.core.base_schema import SchemaBase


class CacheItemUpsert(SchemaBase):
    """写入单个缓存键的请求体"""

    value: Any = Field(description="缓存值（任意 JSON 可序列化结构）")
    ttl: int | None = Field(default=None, description="过期秒数；不传表示不过期")


class CacheWarmupItem(SchemaBase):
    """一条预热数据"""

    key: str = Field(description="缓存键")
    value: Any = Field(description="缓存值")
    ttl: int | None = Field(default=None, description="过期秒数")


class CacheWarmupPayload(SchemaBase):
    """批量预热请求体"""

    items: List[CacheWarmupItem] = Field(default_factory=list, description="预热条目列表")


class CacheStatsPayload(SchemaBase):
    """缓存统计（多级缓存 + 权限缓存）"""

    multi_level: Dict[str, Any] = Field(
        default_factory=dict,
        description="多级缓存统计：total_requests / total_hits / hit_rate / levels.{L1_memory,L2_redis,L3_file}",
    )
    permission: Dict[str, Any] = Field(default_factory=dict, description="权限缓存统计")


class CacheItemPayload(SchemaBase):
    """单个缓存键的读取结果"""

    key: str = Field(description="缓存键")
    value: Any = Field(description="缓存值")
