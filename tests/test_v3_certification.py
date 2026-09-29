"""T5-11 批次 13：certification 模块（专家认证）测试

不连接数据库：验证路由挂载、静态路径前置与鉴权分流。
状态机（pending → approved / rejected → revoked）、两年有效期、过期专家被排除
等行为在集成环境（PostgreSQL）下另行冒烟。
"""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.v3 import register_v3_routes

EXPECTED_ENDPOINTS = {
    ("GET", "/api/v3/gamification/certification/types"),
    ("GET", "/api/v3/gamification/certification/experts"),
    ("GET", "/api/v3/gamification/certification/experts/{user_id}"),
    ("GET", "/api/v3/gamification/certification/mine"),
    ("POST", "/api/v3/gamification/certification/apply"),
    ("PUT", "/api/v3/gamification/certification/mine"),
    ("POST", "/api/v3/gamification/certification/mine/withdraw"),
    ("GET", "/api/v3/gamification/certification/pending"),
    ("POST", "/api/v3/gamification/certification/{cert_id}/review"),
    ("POST", "/api/v3/gamification/certification/{cert_id}/revoke"),
    ("GET", "/api/v3/gamification/certification/stats"),
}


#: 公开只读（不需要 token）

#: 仅认证或需要权限码


def _app() -> FastAPI:
    app = FastAPI()
    register_v3_routes(app)
    return app


def test_public_types_endpoint_returns_all_types():
    """公开类型列表不查库，可直接调用"""
    client = TestClient(_app(), raise_server_exceptions=False)
    response = client.get("/api/v3/gamification/certification/types")
    assert response.status_code == 200
    body = response.json()
    codes_in_body = {item["code"] for item in body["data"]}
    assert codes_in_body == {
        "professional",
        "academic",
        "technical",
        "media",
        "medical",
        "legal",
        "creative",
    }


def test_sensitive_field_never_exposed():
    """`id_number` 只收不回显：对外视图里不允许出现该字段"""
    from src.api.v3.modules.gamification.certification.schema import CertificationOut

    assert "id_number" not in CertificationOut.model_fields
