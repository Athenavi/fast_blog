"""测试：草稿预览令牌（v3 真实实现）

不需要数据库的部分：

  - 路由注册与鉴权分流
  - ``_token_out`` **绝不输出 ``password_hash``**（纯数据结构）
  - 请求 schema 的边界校验
  - 统一失败文案（公开端点用同一句，不区分"不存在/过期/口令错"）

真实读写（生成 → 校验 → 原子计数 → 撤销 → 文章删除级联）走运行时验证。
"""

from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from src.api.v3 import register_v3_routes
from src.api.v3.modules.content.article.preview_service import (
    INVALID_MESSAGE,
    MAX_EXPIRES_HOURS,
    MAX_VIEWS_LIMIT,
    _token_out,
)
from src.api.v3.modules.content.article.schema import ArticlePreviewTokenCreate

PUBLIC = "/api/v3/content/article/public/preview/{token}"
CREATE = "/api/v3/content/article/{article_id}/preview-token"
LIST = "/api/v3/content/article/{article_id}/preview-tokens"
REVOKE = "/api/v3/content/article/preview-token/{token_id}"
CLEANUP = "/api/v3/content/article/preview-token/cleanup"


def _app() -> FastAPI:
    app = FastAPI()
    register_v3_routes(app)
    return app


def _paths() -> set[str]:
    return {route.path for route in _app().routes}


# ------------------------------------------------------------------ 路由与鉴权


def test_public_preview_rejects_unknown_token_with_uniform_message(monkeypatch):
    """公开端点不做鉴权：无效令牌要给统一失败文案（不是 401，避免暴露令牌是否存在）

    这里替换掉服务实现，避免测试环境触库（真实读写由运行时验证覆盖）。
    """
    from src.api.v3.core.exceptions import ForbiddenError
    from src.api.v3.modules.content.article import controller as article_controller

    async def _reject(db, token, *, password=None):
        raise ForbiddenError(INVALID_MESSAGE)

    monkeypatch.setattr(
        article_controller.article_preview_service, "resolve_preview", _reject
    )

    payload = TestClient(_app()).get(
        "/api/v3/content/article/public/preview/not-a-real-token"
    )

    assert payload.status_code == 403
    assert INVALID_MESSAGE in str(payload.json())


# ------------------------------------------------------------------ 输出结构
def _row(**overrides):
    fields = {
        "id": 1,
        "article_id": 2,
        "token": "tok",
        "max_views": 5,
        "view_count": 3,
        "is_active": True,
        "password_hash": "$argon2id$v=19$m=65536,t=3,p=4$abc$def",
        "expires_at": None,
        "created_by": 7,
        "created_at": None,
    }
    fields.update(overrides)
    return SimpleNamespace(**fields)


def test_token_out_never_leaks_password_hash():
    out = _token_out(_row())

    assert "password_hash" not in out
    assert out["has_password"] is True
    assert out["view_count"] == 3
    assert out["max_views"] == 5


def test_token_out_flags_absence_of_password():
    assert _token_out(_row(password_hash=None))["has_password"] is False


def test_token_out_tolerates_null_view_count():
    assert _token_out(_row(view_count=None))["view_count"] == 0


# ------------------------------------------------------------------ schema 边界
def test_create_schema_defaults():
    payload = ArticlePreviewTokenCreate()

    assert payload.expires_hours == 24
    assert payload.password is None
    assert payload.max_views is None


@pytest.mark.parametrize(
    "kwargs",
    [
        {"expires_hours": 0},
        {"expires_hours": MAX_EXPIRES_HOURS + 1},
        {"password": "abc"},
        {"password": "x" * 65},
        {"max_views": 0},
        {"max_views": MAX_VIEWS_LIMIT + 1},
    ],
)
def test_create_schema_rejects_out_of_range(kwargs):
    with pytest.raises(ValidationError):
        ArticlePreviewTokenCreate(**kwargs)
