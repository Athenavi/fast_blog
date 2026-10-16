"""search 模块的请求 / 响应模型（**密钥一律脱敏，绝不回显**）

## 为什么 `api_key` 只入不出

与 `system/oauth` 对 `client_secret`、`system/integration` 对 `idp_certificate` 的处理一致：
配置响应只给 `has_api_key: bool`，让前端知道"已配置/未配置"，但不把密钥发回浏览器 ——
否则它就会出现在浏览器历史、日志、截图、以及任何一次前端报错上报里。

## 为什么 `api_key` 留空表示"保持原值"

前端保存时不必回填密钥（回填意味着密钥必须先发给前端一次）。显式清空需要同时置
`clear_api_key=True`，把"没改"和"要清空"两件事区分开 —— 否则一次误提交就会静默丢掉凭据。
"""

from typing import Optional

from pydantic import Field

from src.api.v3.core.base_schema import SchemaBase


class SearchConfigOut(SchemaBase):
    """Meilisearch 连接配置（**不回显 api_key**）"""

    enabled: bool = False
    host: str = ""
    index_name: str = "articles"
    has_api_key: bool = False

    #: 环境变量侧的取值（只给 host，不给 key 的值，只给"有没有"）。
    #: 作用：管理员改完配置发现没生效时，能立刻看出"数据库里没配、用的是环境变量"。
    env_host: Optional[str] = None
    env_has_api_key: bool = False


class SearchConfigUpdate(SchemaBase):
    """保存连接配置"""

    enabled: bool = Field(default=True, description="关闭后搜索回退数据库")
    host: str = Field(min_length=1, max_length=255, description="如 http://127.0.0.1:7700")
    index_name: str = Field(default="articles", min_length=1, max_length=100)
    api_key: Optional[str] = Field(
        default=None, max_length=255, description="留空表示保持原值，不修改已保存的密钥"
    )
    clear_api_key: bool = Field(default=False, description="显式清空密钥（与'留空'区分）")


class SearchTestOut(SchemaBase):
    """连接测试结果

    **不伪造成功**：连不上就 `ok=False` 并带上真实原因（超时 / 401 / DNS），
    而不是返回一个好看的"测试通过"。
    """

    ok: bool
    message: str
    version: Optional[str] = None
    latency_ms: Optional[int] = None


class SearchReindexOut(SchemaBase):
    """重建索引结果"""

    ok: bool
    message: str
    indexed: int = 0
    skipped: int = 0


class SearchStatsOut(SchemaBase):
    """索引统计（引擎不可用时 `available=False`，不报 0 冒充"空索引"）"""

    ok: bool
    available: bool = False
    message: str = ""
    index_name: str = "articles"
    documents: int = 0
    is_indexing: bool = False
