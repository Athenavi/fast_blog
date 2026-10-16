"""utility 模块路由（system 域：系统工具 / 定义展开 / 命令解析 / Markdown 导出）

::

    GET  /api/v3/system/utility/nlp/intents            NLP 解析能力目录（公开）
    POST /api/v3/system/utility/nlp/parse              解析自然语言命令（公开）
    GET  /api/v3/system/utility/user/vip-status        当前用户 VIP 状态（仅认证）
    GET  /api/v3/system/utility/block-pattern/{id}     展开区块模式定义（需 block_pattern:view）
    GET  /api/v3/system/utility/article/{id}/markdown  导出文章 Markdown 附件（需 article:view）

权限与数据源：

- NLP 端点**公开**（纯计算 / 静态枚举，无用户数据泄露，对齐 ``system/help`` 的公开读策略）；
- ``user/vip-status`` 读**当前登录用户**，仅认证（不暴露任意用户信息）；
- ``block-pattern/{id}`` 复用 ``module_extension:block_pattern:view``；
- ``article/{id}/markdown`` 复用 ``module_content:article:view``（只读导出）。

.. note::
   本模块需在 ``src/api/v3/__init__.py`` 的 ``DOMAIN_MODULES["/system"]`` 登记 ``"utility"``
   才会被加载；本任务受约束不得改动该文件。
"""

from typing import Optional

from fastapi import APIRouter, Query

from src.api.v3.common import response as resp
from src.api.v3.common.response import ResponseModel
from src.api.v3.core.deps import AuthControl, CurrentUser, DBSession
from src.api.v3.core.permission import codes
from src.api.v3.core.router_class import OperationLogRoute
from src.api.v3.modules.system.utility.schema import NlpParseRequest
from src.api.v3.modules.system.utility.service import (
    intent_catalog,
    parse_command,
    utility_service,
)
from src.utils.http.generate_response import send_chunk_md

router = APIRouter(prefix="/utility", tags=["system-utility"], route_class=OperationLogRoute)


# ------------------------------------------------------------------ NLP（公开）
@router.get("/nlp/intents", response_model=ResponseModel, summary="NLP 解析能力目录（公开）")
async def nlp_intents() -> dict:
    """返回源解析器 ``nlp_parser`` 支持的意图 / 实体 / 时间表达式（真实读取模式表，非重写）"""
    return resp.success(intent_catalog())


@router.post("/nlp/parse", response_model=ResponseModel, summary="解析自然语言命令（公开）")
async def nlp_parse(payload: NlpParseRequest) -> dict:
    """纯解析：返回意图 / 实体类型 / 参数 / 置信度；无法识别意图时结果带 ``error`` 说明原因"""
    return resp.success(parse_command(payload.command))


# ------------------------------------------------------------------ 用户 VIP（仅认证）
@router.get("/user/vip-status", response_model=ResponseModel, summary="当前用户 VIP 状态")
async def user_vip_status(db: DBSession, current: CurrentUser) -> dict:
    """调用源 ``user_defs.is_vip`` 判定当前登录用户是否为 VIP（含过期时间处理）"""
    return resp.success(await utility_service.user_vip_status(db, current.id))


# ------------------------------------------------------------------ 区块模式定义展开
@router.get(
    "/block-pattern/{pattern_id}",
    response_model=ResponseModel,
    summary="展开区块模式定义",
)
async def expand_block_pattern(
    pattern_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.BLOCK_PATTERN_VIEW),
) -> dict:
    """读取区块模式并把 ``blocks``（JSON）与 ``keywords``（逗号分隔）展开为列表

    复用源 ``block_pattern_defs.to_pattern_dict``（不复制展开逻辑）。
    """
    return resp.success(await utility_service.block_pattern(db, pattern_id))


# ------------------------------------------------------------------ 文章 Markdown 导出
@router.get("/article/{article_id}/markdown", summary="导出文章 Markdown 附件")
async def article_markdown(
    article_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.ARTICLE_VIEW),
    language: Optional[str] = Query(default=None, max_length=20, description="语言代码，如 zh-CN"),
    include_title: bool = Query(default=True, description="是否在正文前加一级标题"),
):
    """从真表 ``article_content`` 取正文，交给源 ``send_chunk_md`` 流式导出为 ``.md`` 附件

    注：源函数只做「文本 → 附件下载响应」的封装，**不做** HTML→Markdown 转换，
    导出内容即文章正文原文（按需前置标题）。返回 ``StreamingResponse``，故不声明 ``response_model``。
    """
    data = await utility_service.article_markdown(
        db, article_id, language=language, include_title=include_title
    )
    return send_chunk_md(data["content"], data["aid"], data["iso"])
