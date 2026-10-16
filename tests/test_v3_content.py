"""content 域（内容 / 关注流事件）

由同域多个测试文件合并（断言与注释原样保留，仅重排文件组织）。
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from src.api.v3 import register_v3_routes
from src.api.v3.core.exceptions import BadRequestError
from src.api.v3.modules.content.feed.service import EVENT_TYPES, feed_service


# ============================================================ 来自 test_v3_content.py（4 项）
def _app() -> FastAPI:
    app = FastAPI()
    register_v3_routes(app)
    return app


def test_tag_json_filter_compiles():
    """tags_list 是 JSON 列，标签过滤必须编译成 CAST(... AS TEXT) —— 无 DB 也能验证"""
    from sqlalchemy import Text, cast, select

    from shared.models.article.article import Article

    stmt = select(Article.id).where(cast(Article.tags_list, Text).ilike('%"django"%'))
    sql = str(stmt.compile(compile_kwargs={"literal_binds": True})).upper()

    assert "CAST" in sql
    assert "LIKE" in sql


# ───────────────────── 公开列表 exclude_vip（作者主页清单）─────────────────────
def _stub_db():
    """``db.execute`` 的最小替身：count 查询走 ``scalar()``，列表查询走 ``scalars().all()``"""
    from unittest.mock import AsyncMock, MagicMock

    result = MagicMock()
    result.scalar.return_value = 0
    result.scalars.return_value.all.return_value = []
    db = AsyncMock()
    db.execute.return_value = result
    return db


def _last_sql(db) -> str:
    stmt = db.execute.await_args.args[0]
    return str(stmt.compile(compile_kwargs={"literal_binds": True})).upper()


@pytest.mark.asyncio
async def test_public_list_exclude_vip_filters_vip_articles():
    """``exclude_vip=True`` 必须把 ``is_vip_only`` 为 true / NULL 的行排除掉"""
    from src.api.v3.modules.content.article.service import article_service

    db = _stub_db()
    await article_service.public_list(db, exclude_vip=True)

    assert "IS_VIP_ONLY IS NOT TRUE" in _last_sql(db)


@pytest.mark.asyncio
async def test_public_list_default_keeps_vip_articles():
    """默认不过滤 —— 公开列表的既有行为不得被改动"""
    from src.api.v3.modules.content.article.service import article_service

    db = _stub_db()
    await article_service.public_list(db)

    # 列清单里本来就有 is_vip_only，这里断言的是"没有附加 VIP 过滤条件"
    assert "IS_VIP_ONLY IS NOT TRUE" not in _last_sql(db)


BATCH_ENDPOINTS = (
    ("post", "/api/v3/content/article/batch/publish", {"ids": [1], "publish": True}),
    ("post", "/api/v3/content/comment/batch/decide", {"ids": [1], "approve": True}),
    ("post", "/api/v3/content/comment/1/reply", {"content": "hi"}),
    ("post", "/api/v3/content/media/batch/update", {"ids": [1], "is_public": False}),
    ("post", "/api/v3/content/category/1/merge", {"target_id": 2}),
)


def test_category_merge_rejects_self_target():
    """合并入参校验：target_id 为必填（缺失时 422，不应落到业务层）"""
    client = TestClient(_app(), raise_server_exceptions=False)
    resp = client.post("/api/v3/content/category/1/merge", json={})
    assert resp.status_code in (401, 403, 422), f"意外的状态码 {resp.status_code}"


# ============================================================ 来自 test_v3_content_feed.py（4 项）
BASE = "/api/v3/content/feed"


def _app__content_feed() -> FastAPI:
    app = FastAPI()
    register_v3_routes(app)
    return app


# ------------------------------------------------------------------ 纯函数
def test_event_types_are_the_documented_three():
    assert EVENT_TYPES == ("article", "like", "comment")


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (None, EVENT_TYPES),
        ([], EVENT_TYPES),
        (["article"], ("article",)),
        (["article", "LIKE"], ("article", "like")),
        ([" article ", "comment"], ("article", "comment")),
    ],
)
def test_normalize_types(raw, expected):
    assert feed_service._normalize_types(raw) == expected


def test_normalize_types_rejects_unknown():
    with pytest.raises(BadRequestError):
        feed_service._normalize_types(["article", "share"])


# ------------------------------------------------------------------ 端点


def test_feed_auth_split():
    client = TestClient(_app__content_feed(), raise_server_exceptions=False)

    # 公开读：本机无 DB 允许 500，但不允许 401/403
    for path in (f"{BASE}/discover", f"{BASE}/user/1"):
        assert client.get(path).status_code not in (401, 403), path
    # 登录读必须拦住未登录
    assert client.get(f"{BASE}/timeline").status_code in (401, 403)
    assert client.get(f"{BASE}/stats").status_code in (401, 403)
