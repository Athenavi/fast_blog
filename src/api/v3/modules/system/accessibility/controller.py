"""accessibility 模块路由（任务 14b：无障碍 / WCAG 2.1）

::

    GET  /api/v3/system/accessibility/config      读取配置（公开）
    PUT  /api/v3/system/accessibility/config      保存配置（需 setting:edit）
    GET  /api/v3/system/accessibility/css         生成可注入前台的样式表（公开）
    GET  /api/v3/system/accessibility/skip-links  跳过链接（公开）
    GET  /api/v3/system/accessibility/shortcuts   键盘快捷键（公开）
    POST /api/v3/system/accessibility/aria        元素 ARIA 建议（公开）
    POST /api/v3/system/accessibility/validate    HTML 无障碍校验（需 article:edit）
    GET  /api/v3/system/accessibility/guide       使用指南（公开）

公开读是刻意的：前台的"高对比度 / 字号 / 减少动效"开关需要在未登录时也能读到样式。
配置写入需要 ``setting:edit``，校验需要 ``article:edit``（用于编辑器提交前自检）。
"""

from typing import Any, Dict

from fastapi import APIRouter, Body

from src.api.v3.common import response as resp
from src.api.v3.common.response import ResponseModel
from src.api.v3.core.deps import AuthControl, CurrentUser, DBSession
from src.api.v3.core.permission import codes
from src.api.v3.core.router_class import OperationLogRoute
from src.api.v3.modules.system.accessibility.schema import (
    AccessibilityValidateRequest,
    AriaRequest,
)
from src.api.v3.modules.system.accessibility.service import accessibility_service

router = APIRouter(
    prefix="/accessibility", tags=["system-accessibility"], route_class=OperationLogRoute
)


@router.get("/config", response_model=ResponseModel, summary="读取无障碍配置（公开）")
async def get_config(db: DBSession) -> dict:
    return resp.success(await accessibility_service.get_config(db))


@router.put("/config", response_model=ResponseModel, summary="保存无障碍配置")
async def save_config(
    db: DBSession,
    current: CurrentUser,
    payload: Dict[str, Any] = Body(
        ...,
        description="只接受已知配置项；未知键会被明确拒绝（不是静默忽略）",
        examples=[{"high_contrast_mode": True, "font_size": "large"}],
    ),
    _perm=AuthControl(codes.SETTING_EDIT),
) -> dict:
    """落到 ``system_settings``（键 ``accessibility.config``，JSON）

    这里刻意收**原始 dict** 而不是 pydantic 模型：模型的默认行为会静默丢弃未知字段，
    那样 service 里的"未知键校验"就成了死代码（曾经真的发生过）。
    """
    return resp.success(
        await accessibility_service.save_config(
            db, payload, user_id=getattr(current, "id", None)
        ),
        msg="已保存",
    )


@router.get("/css", response_model=ResponseModel, summary="生成无障碍样式表（公开）")
async def accessibility_css(db: DBSession) -> dict:
    config = await accessibility_service.get_config(db)
    return resp.success({"config": config, "css": accessibility_service.css(config)})


@router.get("/skip-links", response_model=ResponseModel, summary="跳过链接（公开）")
async def skip_links() -> dict:
    return resp.success(accessibility_service.skip_links())


@router.get("/shortcuts", response_model=ResponseModel, summary="键盘快捷键（公开）")
async def keyboard_shortcuts() -> dict:
    return resp.success(accessibility_service.keyboard_shortcuts())


@router.post("/aria", response_model=ResponseModel, summary="元素 ARIA 建议（公开）")
async def aria_labels(payload: AriaRequest) -> dict:
    return resp.success(
        {
            "element_type": payload.element_type,
            "attributes": accessibility_service.aria_labels(payload.element_type, payload.context),
        }
    )


@router.post("/validate", response_model=ResponseModel, summary="HTML 无障碍校验")
async def validate_accessibility(
    payload: AccessibilityValidateRequest,
    _current: CurrentUser,
    _perm=AuthControl(codes.ARTICLE_EDIT),
) -> dict:
    """按元素解析（不是整篇子串判断），返回规则名 / 严重级别 / 评分"""
    return resp.success(accessibility_service.validate(payload.html))


@router.get("/guide", response_model=ResponseModel, summary="无障碍使用指南（公开）")
async def accessibility_guide() -> dict:
    return resp.success(accessibility_service.guide())
