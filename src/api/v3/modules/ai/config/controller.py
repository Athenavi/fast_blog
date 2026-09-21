"""ai.config 模块路由（T5-11 批次 4：自 astro `admin/ai` 能力域新建）

::

    GET    /api/v3/ai/config                  配置列表（跨用户，可按 user_id/provider/is_active 过滤）
    GET    /api/v3/ai/config/providers        支持的 provider 与协议（openai 兼容 / anthropic）
    POST   /api/v3/ai/config                  新建配置（api_key 入参：按「用户密码 + SECRET_KEY」加密落库）
    PUT    /api/v3/ai/config/{config_id}      更新配置（api_key 留空保持原值）
    POST   /api/v3/ai/config/{config_id}/test 测试连接（**真实调用一次模型**）
    DELETE /api/v3/ai/config/{config_id}      删除配置

权限码：``module_ai:config:view/create/edit/delete``。
api_key 明文只出现在请求里，响应只有 has_api_key 布尔位。
静态路径 ``/providers`` 注册在 ``/{config_id}`` 之前（启动期会拦路径遮蔽）。
"""

from typing import Optional

from fastapi import APIRouter, Query

from src.api.v3.common import response as resp
from src.api.v3.common.response import ResponseModel
from src.api.v3.core.deps import AuthControl, CurrentUser, DBSession
from src.api.v3.core.permission import codes
from src.api.v3.core.router_class import OperationLogRoute
from src.api.v3.modules.ai import llm
from src.api.v3.modules.ai.config.schema import AIConfigCreate, AIConfigUpdate
from src.api.v3.modules.ai.config.service import ai_config_service

router = APIRouter(prefix="/config", tags=["ai-config"], route_class=OperationLogRoute)


@router.get("", response_model=ResponseModel, summary="AI 配置列表")
async def list_configs(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.AI_CONFIG_VIEW),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user_id: Optional[int] = Query(default=None),
    provider: Optional[str] = Query(default=None),
    is_active: Optional[bool] = Query(default=None),
    keyword: Optional[str] = Query(default=None),
) -> dict:
    items, total = await ai_config_service.list_configs(
        db, page=page, page_size=page_size, user_id=user_id,
        provider=provider, is_active=is_active, keyword=keyword,
    )
    return resp.success_page(items, total, page, page_size)


@router.get("/providers", response_model=ResponseModel, summary="支持的提供商与协议")
async def list_providers(
    _current: CurrentUser,
    _perm=AuthControl(codes.AI_CONFIG_VIEW),
) -> dict:
    """前端下拉用：未知 provider 走 OpenAI 兼容协议（自建网关基本都兼容）。"""
    return resp.success(
        [
            {"provider": provider, "protocol": protocol}
            for provider, protocol in sorted(llm.PROVIDER_PROTOCOLS.items())
        ]
    )


@router.post("", response_model=ResponseModel, summary="新建 AI 配置")
async def create_config(
    payload: AIConfigCreate,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.AI_CONFIG_CREATE),
) -> dict:
    return resp.success(await ai_config_service.create_config(db, payload), msg="已创建")


@router.put("/{config_id}", response_model=ResponseModel, summary="更新 AI 配置")
async def update_config(
    config_id: int,
    payload: AIConfigUpdate,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.AI_CONFIG_EDIT),
) -> dict:
    return resp.success(await ai_config_service.update_config(db, config_id, payload), msg="已保存")


@router.post("/{config_id}/test", response_model=ResponseModel, summary="测试连接（真实调用）")
async def test_config(
    config_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.AI_CONFIG_EDIT),
) -> dict:
    """真的发一次请求给模型（会消耗少量 token）；凭据解不开 / 厂商拒绝都会带回原因。"""
    return resp.success(await ai_config_service.test_connection(db, config_id), msg="连接正常")


@router.delete("/{config_id}", response_model=ResponseModel, summary="删除 AI 配置")
async def delete_config(
    config_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.AI_CONFIG_DELETE),
) -> dict:
    await ai_config_service.delete_config(db, config_id)
    return resp.success(None, msg="已删除")
