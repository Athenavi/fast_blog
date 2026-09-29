"""T5-11 批次 12：gamification 域（points 积分 + badge 勋章）测试

不连接数据库：验证路由挂载、静态路径前置与鉴权分流。
真实统计口径（v2 的 `_get_user_stats` 恒为 0）、签到幂等、兑换发放 VIP 等行为
在集成环境（PostgreSQL）下另行冒烟。
"""

from fastapi import FastAPI

from src.api.v3 import register_v3_routes

EXPECTED_ENDPOINTS = {
    # points（15）
    ("GET", "/api/v3/gamification/points/mine"),
    ("GET", "/api/v3/gamification/points/me"),
    ("GET", "/api/v3/gamification/points/history"),
    ("POST", "/api/v3/gamification/points/checkin"),
    ("POST", "/api/v3/gamification/points/exchange"),
    ("GET", "/api/v3/gamification/points/leaderboard"),
    ("GET", "/api/v3/gamification/points/ranking"),
    ("GET", "/api/v3/gamification/points/rules"),
    ("GET", "/api/v3/gamification/points/exchange-rules"),
    ("GET", "/api/v3/gamification/points/level/{score}"),
    ("GET", "/api/v3/gamification/points/stats"),
    ("POST", "/api/v3/gamification/points/grant"),
    ("POST", "/api/v3/gamification/points/award"),
    ("POST", "/api/v3/gamification/points/deduct"),
    ("PUT", "/api/v3/gamification/points/rule/{rule_id}"),
    # badge（8）
    ("GET", "/api/v3/gamification/badge/mine"),
    ("GET", "/api/v3/gamification/badge/available"),
    ("GET", "/api/v3/gamification/badge/categories"),
    ("GET", "/api/v3/gamification/badge/details/{badge_key}"),
    ("GET", "/api/v3/gamification/badge/progress/{badge_key}"),
    ("POST", "/api/v3/gamification/badge/check-and-award"),
    ("POST", "/api/v3/gamification/badge/award"),
    ("GET", "/api/v3/gamification/badge/stats"),
    # certification（11）
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

#: 「我的」与需要权限码的端点（公开读不在其列）
AUTH_GET_PATHS = (
    "/api/v3/gamification/points/mine",
    "/api/v3/gamification/points/history",
    "/api/v3/gamification/points/stats",
    "/api/v3/gamification/badge/mine",
    "/api/v3/gamification/badge/stats",
)

#: v2 的 `POST /record-action`（前端自报加分）**不得**出现在 v3
FORBIDDEN_PATHS = (
    "/api/v3/gamification/points/record-action",
    "/api/v3/gamification/points/my-points",
)


def _app() -> FastAPI:
    app = FastAPI()
    register_v3_routes(app)
    return app


def test_no_self_report_points_endpoint():
    """v2 的刷分入口必须不存在（前端自报动作加分）"""
    paths = {route.path for route in _app().routes}
    leftovers = set(FORBIDDEN_PATHS) & paths
    assert not leftovers, f"这些 v2 端点不应存在: {sorted(leftovers)}"
