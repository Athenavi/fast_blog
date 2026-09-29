"""Phase 2：system 域（auth / user）骨架测试

不连接数据库：只验证路由挂载、鉴权依赖与统一错误响应格式。
真正的读写行为在集成环境（PostgreSQL + Redis）下另行验证。
"""

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from src.api.v3 import register_v3_routes


def _app() -> FastAPI:
    app = FastAPI()
    register_v3_routes(app)
    return app


def test_shadowed_static_route_is_rejected():
    """静态路径若注册在能匹配它的参数路径之后，必须被启动期检测拦下"""
    from fastapi import APIRouter

    from src.api.v3.core.discover import (
        RouteRegistrationError,
        assert_no_shadowed_routes,
        find_shadowed_routes,
    )

    router = APIRouter()

    @router.get("/user/{user_id}")
    async def get_user(user_id: int):  # pragma: no cover - 仅注册
        return {}

    @router.get("/user/export")
    async def export_users():  # pragma: no cover - 仅注册
        return {}

    assert find_shadowed_routes(router.routes), "必须检出 /user/export 被 /user/{user_id} 遮蔽"

    app = FastAPI()
    app.include_router(router)
    with pytest.raises(RouteRegistrationError):
        assert_no_shadowed_routes(app, source="测试")


def test_login_validation_rejects_empty_payload():
    """缺少密码时由 Pydantic 直接 422（FastAPI 校验），不会打到达业务逻辑"""
    client = TestClient(_app())
    resp = client.post("/api/v3/system/auth/login", json={"username": "someone"})

    assert resp.status_code == 422


def test_non_v3_paths_keep_default_error_shape():
    """v3 的异常处理器不得改变非 v3 路径的行为"""
    app = _app()

    @app.get("/api/v2/__probe_401__")
    async def _probe():  # pragma: no cover - 仅注册
        from fastapi import HTTPException

        raise HTTPException(status_code=401, detail="nope")

    resp = TestClient(app).get("/api/v2/__probe_401__")
    assert resp.status_code == 401
    assert resp.json() == {"detail": "nope"}
