"""测试：推荐类（任务 12）

不需要数据库：

  - 纯函数：``split_tags`` / ``jaccard`` / ``recency_score`` / ``popularity_score`` /
    ``interest_weights`` / ``category_affinity`` / ``score_candidate`` / ``slug_from_page_url``
  - 端点注册、公开读与鉴权分流

真实排序（真表候选集、page_views 窗口计数、用户行为画像）走运行时验证。
"""

from datetime import datetime, timedelta

import pytest
from fastapi import FastAPI

from src.api.v3 import register_v3_routes
from src.api.v3.modules.content.recommend.service import (
    ACTION_WEIGHTS,
    WEIGHTS,
    category_affinity,
    interest_weights,
    jaccard,
    popularity_score,
    recency_score,
    score_candidate,
    slug_from_page_url,
    split_tags,
)

BASE = "/api/v3/content/recommend"


def _app() -> FastAPI:
    app = FastAPI()
    register_v3_routes(app)
    return app


# ------------------------------------------------------------------ 纯函数
@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ('["a", "b"]', ["a", "b"]),
        ("a, b;c", ["a", "b", "c"]),
        (["x", "x", "y"], ["x", "y"]),
        ("", []),
        (None, []),
        ("单标签", ["单标签"]),
    ],
)
def test_split_tags(raw, expected):
    assert split_tags(raw) == expected


def test_jaccard_ignores_empty_sets():
    assert jaccard(["a", "b"], ["b", "c"]) == pytest.approx(1 / 3)
    assert jaccard([], ["b"]) == 0.0
    assert jaccard(["a"], []) == 0.0
    assert jaccard(["a", "b"], ["a", "b"]) == 1.0


def test_recency_score_decays_and_handles_missing_date():
    now = datetime(2026, 1, 31)
    fresh = recency_score(now - timedelta(days=1), now=now)
    old = recency_score(now - timedelta(days=90), now=now)

    assert fresh > old > 0
    assert recency_score(None, now=now) == 0.3


def test_popularity_score_is_capped():
    assert popularity_score(0, 0) == 0.0
    assert popularity_score(500, 10) == pytest.approx(0.6)
    assert popularity_score(100000, 100000) == 1.0
    assert popularity_score("bad", None) == 0.0


def test_interest_weights_favour_likes_and_decay_with_time():
    now = datetime(2026, 1, 31)
    actions = [
        {"tags": ["python"], "action": "like", "at": now},
        {"tags": ["python"], "action": "view", "at": now - timedelta(days=100)},
        {"tags": ["sql"], "action": "view", "at": now},
    ]

    weights = interest_weights(actions, now=now)

    assert weights["python"] > weights["sql"] > 0
    assert sum(weights.values()) == pytest.approx(1.0, abs=1e-5)
    assert ACTION_WEIGHTS["like"] > ACTION_WEIGHTS["view"]


def test_interest_weights_empty_when_no_actions():
    assert interest_weights([]) == {}


def test_category_affinity_normalizes():
    now = datetime(2026, 1, 31)
    actions = [
        {"category": 1, "action": "like", "at": now},
        {"category": 2, "action": "view", "at": now},
        {"category": None, "action": "view", "at": now},
    ]

    affinity = category_affinity(actions, now=now)

    assert set(affinity) == {1, 2}
    assert affinity[1] > affinity[2]
    assert sum(affinity.values()) == pytest.approx(1.0, abs=1e-5)


def test_score_candidate_returns_explainable_parts():
    now = datetime(2026, 1, 31)
    parts = score_candidate(
        interests={"python": 0.6},
        candidate_tags=["python"],
        category_score=1.0,
        published_at=now,
        views=1000,
        likes=100,
        now=now,
    )

    assert set(parts) == {"score", "tag_score", "category_score", "recency_score", "popularity_score"}
    assert parts["tag_score"] == pytest.approx(0.6)
    assert parts["category_score"] == 1.0
    assert parts["popularity_score"] == 1.0
    expected = 0.6 * WEIGHTS["tag"] + 1.0 * WEIGHTS["category"] + parts["recency_score"] * WEIGHTS["recency"] + 1.0 * \
               WEIGHTS["popularity"]
    assert parts["score"] == pytest.approx(expected, abs=1e-4)


def test_score_candidate_without_interests_is_not_negative():
    parts = score_candidate(
        interests={},
        candidate_tags=["nope"],
        category_score=0.0,
        published_at=None,
        views=0,
        likes=0,
    )

    assert parts["score"] >= 0
    assert parts["tag_score"] == 0.0


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://blog.example.com/article/hello", "hello"),
        ("/article/hello/?utm=1", "hello"),
        ("/hello", "hello"),
        ("", None),
        (None, None),
    ],
)
def test_slug_from_page_url(url, expected):
    assert slug_from_page_url(url) == expected

# ------------------------------------------------------------------ 端点
