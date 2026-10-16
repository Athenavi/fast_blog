"""search 模块：Meilisearch 连接配置与索引操作（system 域）

路由前缀：``/api/v3/system/search``

配置存 ``system_settings`` 的 JSON 键 ``search.meilisearch``（运行期写入，不进迁移），
与 ``system/oauth`` 的 ``oauth.providers`` 同一约定。
"""

from src.api.v3.modules.system.search.controller import router

__all__ = ["router"]
