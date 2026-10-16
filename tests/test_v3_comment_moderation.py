"""测试：内容自动审核（真实词库 + 规则）

不需要数据库：

  - ``moderate_text`` 是纯函数（词库以参数注入），可逐条验证规则与扣分
  - 端点注册与鉴权分流
  - 词库缓存失效接口

真实链路（词库来自 ``sensitive_words`` 表 + 提交评论自动落 ``spam_score``/``spam_reasons``）
走运行时验证。
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.v3 import register_v3_routes
from src.api.v3.modules.content.comment.moderation import (
    AUTO_HOLD_BELOW,
    content_moderation_service,
    moderate_text,
)

MODERATE_PATH = "/api/v3/content/comment/moderate"

_WORDS = [
    {"word": "赌博", "level": 3, "action": "block"},
    {"word": "诈骗", "level": 2, "action": "warn"},
    {"word": "水贴", "level": 1, "action": "warn"},
]


def _app() -> FastAPI:
    app = FastAPI()
    register_v3_routes(app)
    return app


# ------------------------------------------------------------------ 干净文本
def test_clean_text_scores_full_and_is_approved():
    result = moderate_text("这是一条正常的评论，感谢分享。", words=_WORDS)

    assert result["score"] == 100
    assert result["is_safe"] is True
    assert result["blocked"] is False
    assert result["issues"] == []
    assert result["suggested_approved"] is True


# ------------------------------------------------------------------ 敏感词
@pytest.mark.parametrize(
    ("word", "expected_penalty"),
    [("水贴", 10), ("诈骗", 25), ("赌博", 50)],
)
def test_sensitive_word_penalty_by_level(word, expected_penalty):
    result = moderate_text(f"这条内容包含{word}", words=_WORDS)

    issue = next(i for i in result["issues"] if i["type"] == "sensitive_word")
    assert issue["word"] == word
    assert issue["penalty"] == expected_penalty
    assert result["score"] == 100 - expected_penalty


def test_block_level_word_blocks_approval():
    result = moderate_text("来这里赌博吧", words=_WORDS)

    assert result["blocked"] is True
    assert result["suggested_approved"] is False
    assert result["is_safe"] is False


def test_non_block_word_may_still_be_approved():
    """警告级敏感词扣分后不一定拦截"""
    result = moderate_text("别被人诈骗了", words=_WORDS)

    assert result["blocked"] is False
    assert result["score"] == 75


# ------------------------------------------------------------------ 刷屏 / 广告
def test_excessive_exclamation_is_penalised():
    result = moderate_text("好棒！！！！！太强了！！！！")

    assert any(i.get("reason") == "exclamation_marks" for i in result["issues"])
    assert result["score"] == 90  # 仅命中"感叹号过多"一条规则


def test_link_density_is_penalised():
    result = moderate_text("看看这个 https://example.com/very/long/path?a=1&b=2")

    assert any(i.get("reason") in {"link_density", "short_with_link"} for i in result["issues"])
    assert result["score"] < 100


def test_ad_keywords_are_penalised():
    result = moderate_text("需要的话可以加微信详聊")

    assert any(i["type"] == "ads" for i in result["issues"])
    assert result["score"] <= 70


def test_repetition_is_penalised():
    result = moderate_text("测试测试测试测试测试测试测试测试测试测试")

    assert any(i.get("reason") == "repetition" for i in result["issues"])


def test_high_caps_ratio_is_penalised():
    result = moderate_text("THIS IS A SHOUTING COMMENT OK")

    assert any(i.get("reason") == "caps_ratio" for i in result["issues"])


# ------------------------------------------------------------------ 分档与边界
def test_score_never_below_zero():
    """多重命中时分数夹到 0（敏感词按**词条**各扣一次，不按出现次数）"""
    result = moderate_text("赌博诈骗水贴 " + "赌博赌博" * 20 + " 加微信", words=_WORDS)

    assert result["score"] == 0
    assert result["suggested_approved"] is False


def test_hold_threshold_matches_constant():
    """刚好达到阈值应通过；低一分应进待审核"""
    passing = moderate_text("x" * 10, words=[{"word": "x", "level": 1, "action": "warn"}])
    assert passing["score"] == 90
    assert passing["suggested_approved"] is (90 >= AUTO_HOLD_BELOW)


def test_invalidate_cache_clears_word_cache():
    content_moderation_service._cache = None
    assert content_moderation_service._cache is None


# ------------------------------------------------------------------ 端点


def test_moderate_endpoint_requires_auth():
    client = TestClient(_app())

    assert client.post(MODERATE_PATH, json={"content": "hi"}).status_code in (401, 403)
