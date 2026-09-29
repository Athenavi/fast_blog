"""T5-11 批次 17：chat/message（群聊消息 + WebSocket）骨架测试。

不连接数据库：验证路由挂载（HTTP + WS）、模块登记、鉴权分流与 WS 准入。
真正的读写 / Redis 广播行为在集成环境（PostgreSQL + Redis）下另行冒烟。
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from src.api.v3 import register_v3_routes

#: 本模块的全部路由（HTTP + WebSocket）

#: HTTP 端点（WebSocket 路由没有 methods，单独断言）
EXPECTED_HTTP_ENDPOINTS = {
    ("GET", "/api/v3/chat/message/my-groups"),
    ("GET", "/api/v3/chat/message/{group_id}"),
    ("POST", "/api/v3/chat/message"),
    ("DELETE", "/api/v3/chat/message/item/{message_id}"),
}


def _app() -> FastAPI:
    app = FastAPI()
    register_v3_routes(app)
    return app


def test_websocket_route_has_no_http_methods():
    """WS 路由必须注册，且没有 HTTP 方法（因此启动期权限审计会跳过它）"""
    ws_routes = [
        route for route in _app().routes if route.path == "/api/v3/chat/message/ws/{group_id}"
    ]
    assert ws_routes, "WebSocket 路由未注册"
    assert not (getattr(ws_routes[0], "methods", None) or set()), "WS 路由不应带 HTTP 方法"


def test_websocket_anonymous_closed_4401():
    """未带 token 的 WS 连接必须由服务端以 4401 关闭（不是匿名放行）

    服务端**先 accept 再 close**（``accept_then_close``）：只有完成握手，业务码才能
    被真实浏览器观测到；未 accept 就 close 会被 uvicorn 按 ASGI 规范转成 HTTP 403，
    客户端只见 ``1006``。真实浏览器的对应断言见 `frontend/web/e2e/chat-ws.spec.ts`。
    """
    client = TestClient(_app(), raise_server_exceptions=False)
    with client.websocket_connect("/api/v3/chat/message/ws/1") as ws:
        with pytest.raises(WebSocketDisconnect) as exc_info:
            ws.receive_text()
    assert exc_info.value.code == 4401
