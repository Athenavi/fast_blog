"""form 模块路由（T5-11 批次 2：自 astro `admin/forms` 能力域新建）

管理端::

    GET    /api/v3/marketing/form                        表单列表
    POST   /api/v3/marketing/form                        新建表单
    PUT    /api/v3/marketing/form/{form_id}              更新表单
    DELETE /api/v3/marketing/form/{form_id}              删除表单（级联字段/提交）
    GET    /api/v3/marketing/form/{form_id}/field        字段列表
    POST   /api/v3/marketing/form/{form_id}/field        新建字段
    PUT    /api/v3/marketing/form/field/{field_id}       更新字段
    DELETE /api/v3/marketing/form/field/{field_id}       删除字段
    GET    /api/v3/marketing/form/submission             提交列表（可按 form_id 过滤）
    DELETE /api/v3/marketing/form/submission/{sub_id}    删除提交

公开端点（无需鉴权，前台渲染表单用）::

    GET    /api/v3/marketing/form/public/{slug}          表单定义（含字段，公开状态）
    POST   /api/v3/marketing/form/public/{slug}/submit   匿名提交

权限码：``module_marketing:form:view/create/edit/delete``。
"""

from typing import Optional

from fastapi import APIRouter, Query, Request
from sqlalchemy import select

from shared.models.form import Form, FormField
from src.api.v3.common import response as resp
from src.api.v3.common.response import ResponseModel
from src.api.v3.core.deps import AuthControl, CurrentUser, DBSession
from src.api.v3.core.exceptions import NotFoundError
from src.api.v3.core.permission import codes
from src.api.v3.core.router_class import OperationLogRoute
from src.api.v3.modules.marketing.form.schema import (
    FormCreate,
    FormFieldCreate,
    FormFieldOut,
    FormFieldUpdate,
    FormOut,
    FormPublicSubmitRequest,
    FormUpdate,
)
from src.api.v3.modules.marketing.form.service import form_service

router = APIRouter(prefix="/form", tags=["marketing-form"], route_class=OperationLogRoute)


# ---------------------------------------------------------------- 表单
@router.get("", response_model=ResponseModel, summary="表单列表")
async def list_forms(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.FORM_VIEW),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    keyword: Optional[str] = Query(default=None),
) -> dict:
    items, total = await form_service.list_forms(db, page=page, page_size=page_size, keyword=keyword)
    return resp.success_page(items, total, page, page_size)


@router.post("", response_model=ResponseModel, summary="新建表单")
async def create_form(
    payload: FormCreate,
    db: DBSession,
    current: CurrentUser,
    _perm=AuthControl(codes.FORM_CREATE),
) -> dict:
    return resp.success(await form_service.create_form(db, payload, user_id=current.id), msg="已创建")


@router.put("/{form_id}", response_model=ResponseModel, summary="更新表单")
async def update_form(
    form_id: int,
    payload: FormUpdate,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.FORM_EDIT),
) -> dict:
    return resp.success(await form_service.update_form(db, form_id, payload), msg="已保存")


@router.delete("/{form_id}", response_model=ResponseModel, summary="删除表单")
async def delete_form(
    form_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.FORM_DELETE),
) -> dict:
    await form_service.delete_form(db, form_id)
    return resp.success(None, msg="已删除")


# ---------------------------------------------------------------- 字段（静态路径前置）
@router.get("/{form_id}/field", response_model=ResponseModel, summary="字段列表")
async def list_fields(
    form_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.FORM_VIEW),
) -> dict:
    return resp.success(await form_service.list_fields(db, form_id))


@router.post("/{form_id}/field", response_model=ResponseModel, summary="新建字段")
async def create_field(
    form_id: int,
    payload: FormFieldCreate,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.FORM_EDIT),
) -> dict:
    return resp.success(await form_service.create_field(db, form_id, payload), msg="已创建")


@router.put("/field/{field_id}", response_model=ResponseModel, summary="更新字段")
async def update_field(
    field_id: int,
    payload: FormFieldUpdate,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.FORM_EDIT),
) -> dict:
    return resp.success(await form_service.update_field(db, field_id, payload), msg="已保存")


@router.delete("/field/{field_id}", response_model=ResponseModel, summary="删除字段")
async def delete_field(
    field_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.FORM_EDIT),
) -> dict:
    await form_service.delete_field(db, field_id)
    return resp.success(None, msg="已删除")


# ---------------------------------------------------------------- 提交（静态路径前置）
@router.get("/submission", response_model=ResponseModel, summary="提交列表")
async def list_submissions(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.FORM_VIEW),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    form_id: Optional[int] = Query(default=None),
) -> dict:
    items, total = await form_service.list_submissions(db, form_id=form_id, page=page, page_size=page_size)
    return resp.success_page(items, total, page, page_size)


@router.delete("/submission/{submission_id}", response_model=ResponseModel, summary="删除提交")
async def delete_submission(
    submission_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.FORM_DELETE),
) -> dict:
    await form_service.delete_submission(db, submission_id)
    return resp.success(None, msg="已删除")


# ---------------------------------------------------------------- 公开端点（无鉴权）
@router.get("/public/{slug}", response_model=ResponseModel, summary="表单定义（公开）", include_in_schema=False)
async def public_form(
    slug: str,
    db: DBSession,
) -> dict:
    """前台渲染表单用：published 状态的表单 + 激活字段"""
    form = (await db.execute(
        select(Form).where(Form.slug == slug, Form.status == "published")
    )).scalar_one_or_none()
    if form is None:
        raise NotFoundError("表单不存在或未开放")
    fields = (await db.execute(
        select(FormField)
        .where(FormField.form_id == form.id, FormField.is_active.is_(True))
        .order_by(FormField.order_index, FormField.id)
    )).scalars().all()
    data = FormOut.model_validate(form, from_attributes=True).model_dump(mode="json")
    data["fields"] = [FormFieldOut.model_validate(f, from_attributes=True).model_dump(mode="json") for f in fields]
    return resp.success(data)


@router.post("/public/{slug}/submit", response_model=ResponseModel, summary="匿名提交表单")
async def public_submit(
    slug: str,
    payload: FormPublicSubmitRequest,
    request: Request,
    db: DBSession,
) -> dict:
    ip = request.client.host if request.client else "unknown"
    ua = request.headers.get("user-agent", "")
    return resp.success(
        await form_service.public_submit(db, slug, payload, ip=ip, user_agent=ua), msg="提交成功"
    )
