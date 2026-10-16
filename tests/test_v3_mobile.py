"""mobile 域（骨架 / VIP 自助 / 关注 / 关注流 / 公开主页）

由同域多个测试文件合并（断言与注释原样保留，仅重排文件组织）。
"""

import asyncio
import json
from datetime import datetime
from fastapi import FastAPI
from fastapi.testclient import TestClient
from src.api.v3 import register_v3_routes
from src.api.v3.modules.content.article.service import article_service
from src.api.v3.modules.mobile.user.service import SENSITIVE_FIELDS, build_public_profile
from types import SimpleNamespace

# ============================================================ 来自 test_v3_mobile.py（1 项）
REMOVED_PATHS = {
    # 旧的扁平 mobile 路径
    "/api/v3/articles/list",
    "/api/v3/articles/search",
    "/api/v3/auth/login",
    "/api/v3/categories/list",
    "/api/v3/users/profile",
    "/api/v3/media/upload/image",
    # 旧 admin 路径（从未加载成功）
    "/api/v3/admin/user/list",
    "/api/v3/admin/dashboard/traffic",
}

PUBLIC_GET_PATHS = (
    "/api/v3/mobile/article/list",
    "/api/v3/mobile/category/list",
    "/api/v3/mobile/comment/article/1",
)

AUTH_GET_PATHS = (
    "/api/v3/mobile/user/profile",
    "/api/v3/mobile/user/stats",
    "/api/v3/mobile/media/1/metadata",
)


def _app() -> FastAPI:
    app = FastAPI()
    register_v3_routes(app)
    return app


def test_comment_vote_model_exists():
    """点赞必须用真实模型 CommentVote（legacy 引用的 CommentLike 并不存在）"""
    from shared.models.comment.comment_vote import CommentVote

    assert CommentVote.__tablename__ == "comment_votes"


# ============================================================ 来自 test_v3_mobile_vip.py（5 项）
EXPECTED_ENDPOINTS = {
    ("GET", "/api/v3/mobile/vip/my-subscription"),
    ("POST", "/api/v3/mobile/vip/create-payment"),
    ("POST", "/api/v3/mobile/vip/my-subscription/cancel"),
    ("GET", "/api/v3/mobile/vip/check-access"),
    ("GET", "/api/v3/mobile/vip/premium-content"),
    ("POST", "/api/v3/mobile/vip/callback/{provider}"),
}

#: 仅需登录的 GET（前端 401 分流依赖它）
AUTH_GET_PATHS__mobile_vip = (
    "/api/v3/mobile/vip/my-subscription",
    "/api/v3/mobile/vip/check-access",
    "/api/v3/mobile/vip/premium-content",
)


def _app__mobile_vip() -> FastAPI:
    app = FastAPI()
    register_v3_routes(app)
    return app


# ------------------------------------------------------------------ 路由契约


# ------------------------------------------------------------------ 鉴权分流


def test_callback_endpoint_is_public():
    """网关回调无鉴权（安全性由插件验签把守），不能因为 401 而丢掉回调"""
    client = TestClient(_app__mobile_vip(), raise_server_exceptions=False)
    resp = client.post("/api/v3/mobile/vip/callback/alipay", json={})
    assert resp.status_code != 401


# ------------------------------------------------------------------ 状态语义
def test_subscription_status_semantics_are_consistent():
    """三处必须一致：0=进行中 / 1=已过期 / 2=已取消

    历史坑：`MembershipService` 早期把 1 当"有效"，与 `marketing/vip` 相反，
    导致积分兑换 / 管理端手动开通两条路径互相"看不见"。
    """
    from shared.services.core.membership import MembershipService
    from src.api.v3.modules.marketing.vip import service as vip_service
    from src.api.v3.modules.mobile.vip import schema as mobile_vip_schema

    triple = (0, 1, 2)
    assert (MembershipService.SUB_ACTIVE, MembershipService.SUB_EXPIRED, MembershipService.SUB_CANCELLED) == triple
    assert (vip_service.SUB_ACTIVE, vip_service.SUB_EXPIRED, vip_service.SUB_CANCELLED) == triple
    assert (
               mobile_vip_schema.SUB_ACTIVE,
               mobile_vip_schema.SUB_EXPIRED,
               mobile_vip_schema.SUB_CANCELLED,
           ) == triple


# ------------------------------------------------------------------ 正文闸门
def _gate(data: dict, viewer=None) -> dict:
    """`apply_vip_gate` 的这两个分支都不查库，可以传 db=None 直接断言"""
    return asyncio.run(article_service.apply_vip_gate(None, data, viewer))


def test_plain_article_is_untouched():
    data = {"id": 1, "user_id": 7, "is_vip_only": False, "required_vip_level": 0, "content": "公开正文"}

    out = _gate(data)

    assert out["content"] == "公开正文"
    assert out["locked"] is False


def test_vip_article_hides_content_for_anonymous():
    data = {"id": 1, "user_id": 7, "is_vip_only": True, "required_vip_level": 0, "content": "付费正文"}

    out = _gate(data)

    assert out["content"] is None
    assert out["locked"] is True
    # `is_vip_only=True` 且等级留 0 → 对外统一成"任何 VIP 等级即可"
    assert out["required_vip_level"] == 1


def test_vip_article_keeps_content_for_author():
    data = {"id": 1, "user_id": 7, "is_vip_only": True, "required_vip_level": 2, "content": "付费正文"}

    out = _gate(data, SimpleNamespace(id=7))

    assert out["content"] == "付费正文"
    assert out["locked"] is False
    assert out["required_vip_level"] == 2


# ============================================================ 来自 test_v3_follow.py（2 项）
FOLLOW_PATHS = {
    "/api/v3/mobile/follow/follower",
    "/api/v3/mobile/follow/following",
    "/api/v3/mobile/follow/{user_id}",
    "/api/v3/mobile/follow/{user_id}/status",
    "/api/v3/mobile/follow/{user_id}/follower",
    "/api/v3/mobile/follow/{user_id}/following",
}

FOLLOW_ENDPOINTS = {
    ("GET", "/api/v3/mobile/follow/follower"),
    ("GET", "/api/v3/mobile/follow/following"),
    ("POST", "/api/v3/mobile/follow/{user_id}"),
    ("DELETE", "/api/v3/mobile/follow/{user_id}"),
    ("GET", "/api/v3/mobile/follow/{user_id}/status"),
    ("GET", "/api/v3/mobile/follow/{user_id}/follower"),
    ("GET", "/api/v3/mobile/follow/{user_id}/following"),
}

#: 需要登录的端点（公开读不在其列）
FOLLOW_AUTH_PATHS = (
    "/api/v3/mobile/follow/follower",
    "/api/v3/mobile/follow/following",
)


def _app__follow() -> FastAPI:
    app = FastAPI()
    register_v3_routes(app)
    return app


def test_follow_write_requires_auth():
    client = TestClient(_app__follow(), raise_server_exceptions=False)
    assert client.post("/api/v3/mobile/follow/2").status_code == 401
    assert client.delete("/api/v3/mobile/follow/2").status_code == 401


def test_install_status_is_public_and_read_only():
    """安装自检**公开可读**（未安装时没有管理员可用），且**没有**任何写口"""
    app = _app__follow()
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get("/api/v3/system/install/status")
    # 无 DB 时也应返回 200（把 database.ok 报成 false），而不是 500
    assert resp.status_code == 200, f"install/status 应为公开 200，实际 {resp.status_code}"

    install_methods = {
        method
        for route in app.routes
        if getattr(route, "path", "").startswith("/api/v3/system/install")
        for method in (getattr(route, "methods", None) or set())
        if method != "HEAD"
    }
    assert install_methods == {"GET"}, f"install 只应有只读端点，实际 {install_methods}"


# ============================================================ 来自 test_v3_feed.py（2 项）
FEED_PATH = "/api/v3/mobile/feed"


def _app__feed() -> FastAPI:
    app = FastAPI()
    register_v3_routes(app)
    return app


def test_feed_requires_auth():
    client = TestClient(_app__feed(), raise_server_exceptions=False)
    resp = client.get(FEED_PATH)
    assert resp.status_code == 401
    assert resp.json()["code"] == 401


def test_feed_subpath_not_matched():
    """feed 只有 ``/feed`` 一个端点：不存在的子路径应 404，而不是被误匹配"""
    client = TestClient(_app__feed(), raise_server_exceptions=False)
    resp = client.get(f"{FEED_PATH}/unknown")
    assert resp.status_code == 404


# ============================================================ 来自 test_v3_user_home.py（5 项）
PUBLIC_PROFILE_PATH = "/api/v3/mobile/user/public/{username}"

EXPECTED_FIELDS = {
    "bio",
    "date_joined",
    "id",
    "is_certified",
    "is_following",
    "is_mutual",
    "is_private",
    "profile_picture",
    "stats",
    "username",
    "vip_level",
}


class FakeUser:
    """只带公开主页需要的属性（含**敏感**字段，用于验证它们不外泄）"""

    def __init__(self, **kwargs):
        self.id = kwargs.get("id", 1)
        self.username = kwargs.get("username", "alice")
        self.profile_picture = kwargs.get("profile_picture", "https://example.com/a.png")
        self.bio = kwargs.get("bio", "hello")
        self.vip_level = kwargs.get("vip_level", 1)
        self.date_joined = kwargs.get("date_joined", datetime(2026, 1, 1))
        self.profile_private = kwargs.get("profile_private", False)
        self.is_active = kwargs.get("is_active", True)
        # ---- 以下全部是敏感字段，任何分支都不得出现在响应里 ----
        self.email = kwargs.get("email", "alice@example.com")
        self.password = kwargs.get("password", "hashed")
        self.totp_secret = kwargs.get("totp_secret", "SECRET")
        self.backup_codes = kwargs.get("backup_codes", "codes")
        self.last_login_ip = kwargs.get("last_login_ip", "127.0.0.1")
        self.register_ip = kwargs.get("register_ip", "127.0.0.1")
        self.is_superuser = kwargs.get("is_superuser", True)
        self.is_staff = kwargs.get("is_staff", True)


def _app__user_home() -> FastAPI:
    app = FastAPI()
    register_v3_routes(app)
    return app


# ------------------------------------------------------------------ 路由契约


def test_public_profile_reachable_anonymously():
    """公开端点：匿名请求不应被要求登录（非 401）"""
    client = TestClient(_app__user_home(), raise_server_exceptions=False)
    resp = client.get("/api/v3/mobile/user/public/nobody")
    assert resp.status_code != 401, "公开主页不应要求鉴权"


# ------------------------------------------------------------------ 字段白名单
def test_public_profile_schema_fields():
    data = build_public_profile(
        FakeUser(),
        is_following=True,
        is_mutual=True,
        is_certified=True,
        stats={"articles": 3, "followers": 5, "following": 2},
    )

    assert set(data) == EXPECTED_FIELDS
    assert data["id"] == 1 and data["username"] == "alice"
    assert data["is_private"] is False
    assert data["is_following"] is True
    assert data["is_mutual"] is True
    assert data["is_certified"] is True
    assert data["stats"] == {"articles": 3, "followers": 5, "following": 2}


def test_public_profile_excludes_sensitive_fields():
    data = build_public_profile(FakeUser(), stats={"articles": 1, "followers": 1, "following": 1})

    blob = json.dumps(data, ensure_ascii=False)
    for field in SENSITIVE_FIELDS:
        assert field not in blob, f"公开主页不得出现敏感字段：{field}"


# ------------------------------------------------------------------ 隐私分支
def test_private_profile_hides_bio_and_stats():
    user = FakeUser(bio="绝密简介", vip_level=9, profile_private=True)

    data = build_public_profile(
        user,
        is_following=True,
        is_mutual=True,
        is_certified=True,
        stats={"articles": 9, "followers": 9, "following": 9},
    )

    assert data["is_private"] is True
    assert data["id"] == user.id and data["username"] == user.username
    assert data["bio"] is None and data["vip_level"] == 0 and data["date_joined"] is None
    assert data["is_following"] is False
    assert data["is_mutual"] is False
    assert data["is_certified"] is False
    assert data["stats"] == {"articles": 0, "followers": 0, "following": 0}


def test_private_profile_excludes_sensitive_fields():
    blob = json.dumps(build_public_profile(FakeUser(profile_private=True)), ensure_ascii=False)

    for field in SENSITIVE_FIELDS:
        assert field not in blob, f"私密主页不得出现敏感字段：{field}"
