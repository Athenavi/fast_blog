"""V3 业务异常体系与异常处理器

结构对齐 FastApiAdmin `app/core/exceptions.py`：用业务异常表达「可预期的失败」，
由统一处理器转成 v3 响应格式，避免每个 controller 里写 ``return fail(...)``。

与全局处理器（``src/app.py`` 的 ``register_error_handlers``）的关系：
本模块的处理器**只接管 ``/api/v3/**`` 路径**，v2 与页面路由维持原有行为不变。
"""

from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from src.api.v3.common import response as resp
from src.api.v3.core.logger import get_logger

logger = get_logger("exceptions")

V3_PREFIX = "/api/v3"


class V3Error(Exception):
    """v3 业务异常基类

    默认返回 HTTP 200 + 业务 ``code``（前端按 code 分支，与项目既有习惯一致）；
    认证 / 权限类异常用真实 HTTP 状态码（见子类），以便前端拦截器统一处理。
    """

    code: int = resp.CODE_BAD_REQUEST
    msg: str = "操作失败"
    http_status: Optional[int] = None

    def __init__(
        self,
        msg: Optional[str] = None,
        *,
        code: Optional[int] = None,
        http_status: Optional[int] = None,
        data: Any = None,
    ) -> None:
        self.msg = msg or self.msg
        self.code = code if code is not None else self.code
        self.http_status = http_status if http_status is not None else self.http_status
        self.data = data
        super().__init__(self.msg)

    def to_response(self) -> JSONResponse:
        status = self.http_status if self.http_status is not None else 200
        return JSONResponse(status_code=status, content=resp.fail(self.msg, code=self.code, data=self.data))


class BadRequestError(V3Error):
    code = resp.CODE_BAD_REQUEST
    msg = "请求参数有误"


class UnauthorizedError(V3Error):
    code = resp.CODE_UNAUTHORIZED
    msg = "未认证或登录已过期"
    http_status = resp.CODE_UNAUTHORIZED


class ForbiddenError(V3Error):
    code = resp.CODE_FORBIDDEN
    msg = "权限不足"
    http_status = resp.CODE_FORBIDDEN


class NotFoundError(V3Error):
    code = resp.CODE_NOT_FOUND
    msg = "资源不存在"
    http_status = resp.CODE_NOT_FOUND


class ConflictError(V3Error):
    code = resp.CODE_CONFLICT
    msg = "资源状态冲突"


class ServerError(V3Error):
    code = resp.CODE_SERVER_ERROR
    msg = "服务器内部错误"
    http_status = resp.CODE_SERVER_ERROR


def register_v3_exception_handlers(app: FastAPI) -> None:
    """注册 v3 异常处理器（仅作用于 ``/api/v3/**``）"""

    @app.exception_handler(V3Error)
    async def _v3_error_handler(request: Request, exc: V3Error) -> JSONResponse:  # noqa: ARG001
        logger.warning("业务异常 %s %s -> code=%s msg=%s", request.method, request.url.path, exc.code, exc.msg)
        return exc.to_response()

    @app.exception_handler(HTTPException)
    async def _v3_http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        """把 HTTPException（如鉴权依赖抛的 401/403）也统一成 v3 格式"""
        if not request.url.path.startswith(V3_PREFIX):
            # 保持 FastAPI 默认行为（含 WWW-Authenticate 等 headers）
            return JSONResponse(
                status_code=exc.status_code,
                content={"detail": exc.detail},
                headers=getattr(exc, "headers", None),
            )
        return JSONResponse(
            status_code=exc.status_code,
            content=resp.fail(str(exc.detail), code=exc.status_code),
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(Exception)
    async def _v3_unhandled_handler(request: Request, exc: Exception):
        # 非 v3 路径交回默认机制（返回 ASGI 默认 500），避免改变既有行为
        if not request.url.path.startswith(V3_PREFIX):
            raise exc
        logger.exception("未处理异常 %s %s", request.method, request.url.path)
        return JSONResponse(status_code=500, content=resp.server_error())
