"""skill 模块路由（AI Agent 技能框架）

::

    GET  /api/v3/ai/skill              技能清单（可按分类 / 关键字过滤）
    GET  /api/v3/ai/skill/categories   技能分类
    GET  /api/v3/ai/skill/{name}       技能详情（含参数说明）
    POST /api/v3/ai/skill/{name}/run   执行技能（真实执行）

权限码：``module_ai:workflow:view``（查看）/ ``module_ai:workflow:execute``（执行）。
技能自身声明的 ``required_permission`` 会在执行时**再校验一次**（例如 ``seo_optimizer``
额外要求 ``module_analytics:seo:edit``）—— 只给查看权的人不能借技能绕过写权限。
"""

from typing import Optional

from fastapi import APIRouter, Query, Request

from src.api.v3.common import response as resp
from src.api.v3.common.response import ResponseModel
from src.api.v3.core.deps import AuthControl, CurrentUser, DBSession
from src.api.v3.core.permission import codes
from src.api.v3.core.router_class import OperationLogRoute
from src.api.v3.modules.ai.skill import SKILL_CATEGORIES, registry
from src.api.v3.modules.ai.skill.registry import SkillContext
from src.api.v3.modules.ai.skill.schema import SkillRunRequest

router = APIRouter(prefix="/skill", tags=["ai-skill"], route_class=OperationLogRoute)


@router.get("", response_model=ResponseModel, summary="技能清单")
async def list_skills(
    _current: CurrentUser,
    _perm=AuthControl(codes.AI_WORKFLOW_VIEW),
    category: Optional[str] = Query(default=None, description="按分类过滤"),
    keyword: Optional[str] = Query(default=None, description="按名称 / 描述模糊搜索"),
) -> dict:
    items = registry.list_skills(category=category, keyword=keyword)
    return resp.success({"total": len(items), "items": items})


@router.get("/categories", response_model=ResponseModel, summary="技能分类")
async def skill_categories(
    _current: CurrentUser,
    _perm=AuthControl(codes.AI_WORKFLOW_VIEW),
) -> dict:
    return resp.success(
        [{"category": key, "label": label} for key, label in SKILL_CATEGORIES.items()]
    )


@router.get("/{name}", response_model=ResponseModel, summary="技能详情")
async def get_skill(
    name: str,
    _current: CurrentUser,
    _perm=AuthControl(codes.AI_WORKFLOW_VIEW),
) -> dict:
    return resp.success(registry.describe(name))


@router.post("/{name}/run", response_model=ResponseModel, summary="执行技能（真实执行）")
async def run_skill(
    name: str,
    payload: SkillRunRequest,
    request: Request,
    db: DBSession,
    current: CurrentUser,
    _perm=AuthControl(codes.AI_WORKFLOW_EXECUTE),
) -> dict:
    """技能内部会再校验它声明的权限；失败时返回可读原因（不会静默成功）"""
    ctx = SkillContext(
        db=db,
        params=payload.params or {},
        user=current,
        request=request,
        config_id=payload.config_id,
    )
    result = await registry.execute(ctx, name)
    return resp.success(
        result, msg=f"技能「{result['label']}」执行完成（{result['duration_ms']}ms）"
    )
