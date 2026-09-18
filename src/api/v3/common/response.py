"""V3 统一响应模型与工厂

结构对齐 FastApiAdmin `app/common/response.py`：以 `code / msg / data` 表达业务结果，
分页统一放在 `pagination` 字段。

与 v2 的差异（有意为之）：
  - v2 用 ``{success, data, message, error, pagination}``（``src/api/v2/_base.py``）
  - v3 用 ``{code, msg, data, pagination}``
  两套格式在 v2 冻结期内并存：旧移动端接口仍走 v2 格式，v3 新模块一律用本模块。

约定：
  - ``code == 200`` 表示成功；其余为业务/校验错误码
  - HTTP 状态码仍由 FastAPI 决定，业务失败默认仍返回 200 + 非 200 code（前端据 code 分支），
    需要非 200 HTTP 时用 ``fail(..., http_status=...)`` 配合 ``JSONResponse``
"""

from typing import Any, Iterable, Optional

from pydantic import BaseModel

# 常用业务码（与前端 src/api/request.ts 的错误处理对齐）
CODE_SUCCESS = 200
CODE_BAD_REQUEST = 400
CODE_UNAUTHORIZED = 401
CODE_FORBIDDEN = 403
CODE_NOT_FOUND = 404
CODE_CONFLICT = 409
CODE_SERVER_ERROR = 500


class ResponseModel(BaseModel):
    """统一响应模型（供 OpenAPI 文档使用）"""

    code: int = CODE_SUCCESS
    msg: str = "success"
    data: Optional[Any] = None
    pagination: Optional[dict] = None


class Pagination(BaseModel):
    """分页元信息"""

    page: int = 1
    page_size: int = 20
    total: int = 0
    pages: int = 0


def build_pagination(page: int, page_size: int, total: int) -> dict:
    """构造分页元信息（page_size <= 0 时不分页，pages 记 0）"""
    pages = (total + page_size - 1) // page_size if page_size > 0 else 0
    return Pagination(page=page, page_size=page_size, total=total, pages=pages).model_dump()


def success(
    data: Any = None,
    msg: str = "success",
    *,
    code: int = CODE_SUCCESS,
    pagination: Optional[dict] = None,
) -> dict:
    """构造成功响应"""
    return ResponseModel(code=code, msg=msg, data=data, pagination=pagination).model_dump()


def success_page(
    items: Iterable[Any],
    total: int,
    page: int,
    page_size: int,
    msg: str = "success",
) -> dict:
    """构造分页成功响应"""
    return success(
        data=list(items),
        msg=msg,
        pagination=build_pagination(page, page_size, total),
    )


def fail(
    msg: str = "操作失败",
    *,
    code: int = CODE_BAD_REQUEST,
    data: Any = None,
) -> dict:
    """构造失败响应"""
    return ResponseModel(code=code, msg=msg, data=data).model_dump()


def unauthorized(msg: str = "未认证或登录已过期") -> dict:
    return fail(msg, code=CODE_UNAUTHORIZED)


def forbidden(msg: str = "权限不足") -> dict:
    return fail(msg, code=CODE_FORBIDDEN)


def not_found(msg: str = "资源不存在") -> dict:
    return fail(msg, code=CODE_NOT_FOUND)


def server_error(msg: str = "服务器内部错误") -> dict:
    return fail(msg, code=CODE_SERVER_ERROR)
