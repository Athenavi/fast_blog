"""T5-11 批次 9：content/collaboration 模块测试（工作区 / 任务 / 评论 / 邀请 / yjs 协同）

不连接数据库：验证路由挂载（**含 v3 的第一个 WebSocket 端点**）、模块登记与鉴权分流。
工作区权限层级、邀请接受、CRDT 同步的真实行为在集成环境（PostgreSQL + Redis）下另行冒烟。
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from src.api.v3 import register_v3_routes

#: HTTP 端点（WebSocket 路由没有 methods，单独断言）
EXPECTED_HTTP_ENDPOINTS = {
    ("GET", "/api/v3/content/collaboration/workspace"),
    ("POST", "/api/v3/content/collaboration/workspace"),
    ("GET", "/api/v3/content/collaboration/workspace/by-slug/{slug}"),
    ("GET", "/api/v3/content/collaboration/workspace/{workspace_id}"),
    ("PUT", "/api/v3/content/collaboration/workspace/{workspace_id}"),
    ("DELETE", "/api/v3/content/collaboration/workspace/{workspace_id}"),
    ("GET", "/api/v3/content/collaboration/workspace/{workspace_id}/member"),
    ("POST", "/api/v3/content/collaboration/workspace/{workspace_id}/member"),
    ("PUT", "/api/v3/content/collaboration/workspace/{workspace_id}/member/{member_user_id}"),
    ("DELETE", "/api/v3/content/collaboration/workspace/{workspace_id}/member/{member_user_id}"),
    ("GET", "/api/v3/content/collaboration/workspace/{workspace_id}/task"),
    ("POST", "/api/v3/content/collaboration/workspace/{workspace_id}/task"),
    ("PUT", "/api/v3/content/collaboration/task/{task_id}"),
    ("DELETE", "/api/v3/content/collaboration/task/{task_id}"),
    ("GET", "/api/v3/content/collaboration/comment"),
    ("GET", "/api/v3/content/collaboration/comment/mentions"),
    ("GET", "/api/v3/content/collaboration/comment/statistics"),
    ("POST", "/api/v3/content/collaboration/comment"),
    ("PUT", "/api/v3/content/collaboration/comment/{comment_id}"),
    ("DELETE", "/api/v3/content/collaboration/comment/{comment_id}"),
    ("POST", "/api/v3/content/collaboration/comment/{comment_id}/resolve"),
    ("GET", "/api/v3/content/collaboration/invite"),
    ("POST", "/api/v3/content/collaboration/invite"),
    ("POST", "/api/v3/content/collaboration/invite/accept"),
    ("GET", "/api/v3/content/collaboration/invite/{invite_id}"),
    ("DELETE", "/api/v3/content/collaboration/invite/{invite_id}"),
    ("GET", "/api/v3/content/collaboration/yjs/rooms"),
    ("POST", "/api/v3/content/collaboration/yjs/document/{document_id}/save"),
}

AUTH_GET_PATHS = (
    "/api/v3/content/collaboration/workspace",
    "/api/v3/content/collaboration/comment/statistics",
    "/api/v3/content/collaboration/invite",
    "/api/v3/content/collaboration/yjs/rooms",
)

#: 静态路径必须排在参数路径之前（否则会被 /{id} 吞掉）
ORDERED_STATIC_BEFORE_PARAM = (
    ("/api/v3/content/collaboration/comment/mentions", "/api/v3/content/collaboration/comment/{comment_id}"),
    ("/api/v3/content/collaboration/comment/statistics", "/api/v3/content/collaboration/comment/{comment_id}"),
    ("/api/v3/content/collaboration/invite/accept", "/api/v3/content/collaboration/invite/{invite_id}"),
)


def _app() -> FastAPI:
    app = FastAPI()
    register_v3_routes(app)
    return app


def test_websocket_route_registered():
    """v3 的第一个 WS 端点：路径必须注册，且**没有** HTTP 方法"""
    ws_routes = [
        route
        for route in _app().routes
        if route.path == "/api/v3/content/collaboration/yjs/ws/{document_id}"
    ]
    assert ws_routes, "WebSocket 路由未注册"
    assert not (getattr(ws_routes[0], "methods", None) or set()), "WS 路由不应带 HTTP 方法"


def test_websocket_rejects_anonymous():
    """未带 token 的 WS 连接必须以 ``4401`` 关闭（v2 是匿名放行）

    服务端**先 accept 再 close**（``accept_then_close``）：只有完成握手，业务码才能
    被客户端观测到；未 accept 就 close 会被 uvicorn 按 ASGI 规范转成 HTTP 403，
    浏览器侧只看到 ``1006``。
    """
    client = TestClient(_app(), raise_server_exceptions=False)
    with client.websocket_connect("/api/v3/content/collaboration/yjs/ws/1") as ws:
        with pytest.raises(WebSocketDisconnect) as exc_info:
            ws.receive_text()
    assert exc_info.value.code == 4401
