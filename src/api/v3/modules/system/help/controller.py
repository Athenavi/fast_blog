"""help 模块路由（帮助中心 / 上下文帮助）

::

    GET    /api/v3/system/help/topics                 全部主题（公开）
    GET    /api/v3/system/help/topic/{page_key}       单条主题（公开）
    GET    /api/v3/system/help/search?q=              相关性搜索（公开）
    POST   /api/v3/system/help/topic                  新增 / 覆盖自定义帮助（需 setting:edit）
    DELETE /api/v3/system/help/topic/{page_key}       删除自定义帮助（需 setting:edit）
    GET    /api/v3/system/help/tooltip?field=&context= 字段提示（公开）
    GET    /api/v3/system/help/videos                 视频教程（公开）

公开读是刻意的：帮助 / 提示 / 教程在前台和登录页都需要展示。
写操作落 ``system_settings``（键 ``help.topics``），需要 ``setting:edit``。
"""

from typing import Any, Dict, Optional

from fastapi import APIRouter, Body, Query

from src.api.v3.common import response as resp
from src.api.v3.common.response import ResponseModel
from src.api.v3.core.deps import AuthControl, CurrentUser, DBSession
from src.api.v3.core.permission import codes
from src.api.v3.core.router_class import OperationLogRoute
from src.api.v3.modules.system.help.service import DEFAULT_TOPICS, help_service

router = APIRouter(prefix="/help", tags=["system-help"], route_class=OperationLogRoute)


@router.get("/topics", response_model=ResponseModel, summary="全部帮助主题（公开）")
async def list_topics(db: DBSession) -> dict:
    """返回主题概览（``page_key`` / ``title`` / ``tags`` / ``language`` + 是否覆盖默认）"""
    topics = await help_service.get_all_topics(db)
    default_keys = {topic["page_key"] for topic in DEFAULT_TOPICS}
    items = [
        {
            "page_key": topic["page_key"],
            "title": topic["title"],
            "tags": topic["tags"],
            "language": topic["language"],
            "is_default": topic["page_key"] in default_keys,
        }
        for topic in topics
    ]
    return resp.success(items)


@router.get("/topic/{page_key}", response_model=ResponseModel, summary="单条帮助主题（公开）")
async def get_topic(page_key: str, db: DBSession) -> dict:
    return resp.success(await help_service.get_topic(db, page_key))


@router.get("/search", response_model=ResponseModel, summary="搜索帮助内容（公开）")
async def search_help(
    db: DBSession,
    q: str = Query(..., min_length=1, max_length=200, description="搜索关键词"),
    limit: int = Query(default=20, ge=1, le=100),
) -> dict:
    return resp.success(await help_service.search(db, q, limit=limit))


@router.post("/topic", response_model=ResponseModel, summary="新增 / 覆盖自定义帮助")
async def upsert_topic(
    db: DBSession,
    current: CurrentUser,
    payload: Dict[str, Any] = Body(
        ...,
        description="只接受已知字段；未知字段会被明确拒绝（不是静默忽略）",
        examples=[
            {
                "page_key": "article_editor",
                "title": "文章编辑器（自定义）",
                "content": "<h3>自定义帮助</h3>",
                "tags": ["文章", "编辑器"],
                "language": "zh_CN",
            }
        ],
    ),
    _perm=AuthControl(codes.SETTING_EDIT),
) -> dict:
    """落到 ``system_settings``（键 ``help.topics``，JSON 数组）

    这里刻意收**原始 dict** 而不是 pydantic 模型：模型默认会静默丢弃未知字段，
    那样 service 里的"未知字段校验"就成了死代码（本项目踩过这个坑）。
    """
    return resp.success(
        await help_service.upsert_topic(db, payload, user_id=getattr(current, "id", None)),
        msg="已保存",
    )


@router.delete("/topic/{page_key}", response_model=ResponseModel, summary="删除自定义帮助")
async def delete_topic(
    page_key: str,
    db: DBSession,
    current: CurrentUser,
    _perm=AuthControl(codes.SETTING_EDIT),
) -> dict:
    """仅删除自定义 / 覆盖条目；默认主题本身无法删除（删除覆盖后回到默认内容）"""
    return resp.success(
        await help_service.delete_topic(db, page_key, user_id=getattr(current, "id", None)),
        msg="已删除",
    )


@router.get("/tooltip", response_model=ResponseModel, summary="字段提示（公开）")
async def field_tooltip(
    db: DBSession,
    field: str = Query(..., min_length=1, max_length=100, description="字段名，如 slug"),
    context: Optional[str] = Query(default="general", max_length=100, description="上下文，如 article_editor"),
) -> dict:
    text = await help_service.field_tooltip(db, field, context or "general")
    return resp.success({"field": field, "context": context or "general", "tooltip": text})


@router.get("/videos", response_model=ResponseModel, summary="视频教程（公开）")
async def video_tutorials(
    topic: Optional[str] = Query(default=None, max_length=100),
) -> dict:
    return resp.success(help_service.videos(topic))
