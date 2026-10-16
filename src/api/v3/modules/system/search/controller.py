"""search 模块路由（system 域：全文搜索连接配置）

::

    GET  /api/v3/system/search/config     读连接配置（脱敏，不回显 api_key）
    PUT  /api/v3/system/search/config     保存连接配置（**立即生效**，无需重启）
    POST /api/v3/system/search/test       真实连通性测试（连不上就如实报错）
    POST /api/v3/system/search/reindex    从数据库重建索引（只索引当前站点可见文章）
    GET  /api/v3/system/search/stats      索引统计（引擎不可用时 available=False）

**权限码**：复用 ``settings:view`` / ``settings:edit``（``codes.SETTING_VIEW`` /
``codes.SETTING_EDIT``）。不新造权限码 —— 这组配置与 `system/setting` 同类，
都是"站点级运行配置"；单独造码只会让 RBAC 里多一个永远与 setting 同步的项。

**为什么没有公开端点**：连接配置含 host 与"密钥是否存在"，属运维信息；
前台不需要它（站点搜索走 `content/article/public/list`）。
"""

from fastapi import APIRouter

from src.api.v3.common import response as resp
from src.api.v3.common.response import ResponseModel
from src.api.v3.core.deps import AuthControl, CurrentUser, DBSession
from src.api.v3.core.permission import codes
from src.api.v3.core.router_class import OperationLogRoute
from src.api.v3.modules.system.search.schema import SearchConfigUpdate
from src.api.v3.modules.system.search.service import search_settings_service

router = APIRouter(prefix="/search", tags=["system-search"], route_class=OperationLogRoute)


@router.get("/config", response_model=ResponseModel, summary="读 Meilisearch 连接配置")
async def get_search_config(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.SETTING_VIEW),
) -> dict:
    """返回生效中的配置（数据库优先、环境变量兜底），**不含 api_key**"""
    return resp.success(await search_settings_service.get_config(db))


@router.put("/config", response_model=ResponseModel, summary="保存 Meilisearch 连接配置")
async def update_search_config(
    db: DBSession,
    _current: CurrentUser,
    payload: SearchConfigUpdate,
    _perm=AuthControl(codes.SETTING_EDIT),
) -> dict:
    """保存后**立刻推给服务单例**，不重启即生效；``api_key`` 留空表示保持原值"""
    return resp.success(await search_settings_service.update_config(db, payload))


@router.post("/test", response_model=ResponseModel, summary="测试 Meilisearch 连接")
async def test_search_connection(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.SETTING_EDIT),
) -> dict:
    """真打一次 ``/health`` 与 ``/version``，返回真实版本与延迟"""
    return resp.success(await search_settings_service.test_connection(db))


@router.post("/reindex", response_model=ResponseModel, summary="重建搜索索引")
async def reindex_search(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.SETTING_EDIT),
) -> dict:
    """从数据库全量重建；只索引**当前站点可见**的文章（与前台口径一致）"""
    return resp.success(await search_settings_service.reindex(db))


@router.get("/stats", response_model=ResponseModel, summary="搜索索引统计")
async def search_stats(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.SETTING_VIEW),
) -> dict:
    return resp.success(await search_settings_service.stats(db))
