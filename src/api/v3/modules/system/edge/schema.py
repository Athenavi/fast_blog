"""edge 模块的请求模型

只描述**可表达**的输入；未知字段由 service 显式拒绝（不用 pydantic 静默丢弃，参
``accessibility`` 模块踩过的坑）。
"""

from typing import Optional

from pydantic import Field

from src.api.v3.core.base_schema import SchemaBase

#: 平台名允许的写法（规范化在 service.normalize_platform 完成，这里只做长度约束）
PLATFORM_HINT = "cloudflare_workers / vercel_edge"


class EdgeFunctionCreate(SchemaBase):
    """注册一个边缘函数（写入 ``system_settings`` 键 ``edge.functions``）"""

    name: str = Field(
        min_length=1,
        max_length=100,
        pattern=r"^[A-Za-z][A-Za-z0-9_-]{0,99}$",
        description="函数名（唯一，字母开头，可含字母/数字/下划线/连字符）",
    )
    platform: str = Field(min_length=1, max_length=40, description=f"边缘平台：{PLATFORM_HINT}")
    route: str = Field(
        min_length=1,
        max_length=255,
        description="路由规则：精确路径（/api/edge/hello）或以 * 结尾的前缀通配（/blog/*）",
    )
    code: str = Field(
        default="",
        max_length=1_048_576,
        description="边缘函数源码；留空则部署平台自带的转发模板",
    )
    cache_ttl: int = Field(default=0, ge=0, le=86_400, description="边缘缓存秒数，0 表示不缓存")
    description: str = Field(default="", max_length=500)
    enabled: bool = Field(default=True, description="是否参与路由匹配")


class EdgeFunctionValidateRequest(SchemaBase):
    """校验（可选 body）：编辑器实时校验尚未保存的代码

    不传 body 则校验**已保存**的定义。
    """

    code: Optional[str] = Field(default=None, max_length=1_048_576)
