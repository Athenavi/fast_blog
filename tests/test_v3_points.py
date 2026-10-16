"""_pending_test_points.py —— 待迁入 ``tests/`` 的**纯函数**单测

本任务的环境**禁止写 ``tests/`` 目录、禁止执行 shell**，因此把积分模块的纯函数单测
临时放在模块目录内（文件名以下划线开头，不会被当作业务模块导入）。恢复后应移动到
``tests/api/v3/gamification/test_points.py``。

只覆盖**不依赖 DB / 网络 / FastAPI / 时钟**的纯函数：:

  - ``level_for``     等级阈值计算（越界 / 封顶 / 区间进度）
  - ``DEFAULT_POINT_RULES`` 规则常量表
  - ``reward_for``    奖励计算（首篇加码、连续发文加码、未知动作）
  - ``rank_entries``  排行榜排序（降序 + 并列打破 + 截断 + 名次）

运行（在仓库根目录，确保可 ``import src.*``）::

    python -m pytest src/api/v3/modules/gamification/points/_pending_test_points.py -q

**本文件尚未运行**：本任务执行环境不允许跑 pytest，故仅静态编写。
"""

from src.api.v3.modules.gamification.points.service import (
    DEFAULT_POINT_RULES,
    LEVELS,
    level_for,
    rank_entries,
    reward_for,
)


# --------------------------------------------------------------------- 等级
def test_level_thresholds():
    # 边界：0 → 新手；99 仍是新手；恰好 100 → 学徒
    assert level_for(0)["level"] == 1
    assert level_for(0)["name"] == "新手"
    assert level_for(99)["level"] == 1
    assert level_for(100)["level"] == 2
    assert level_for(499)["level"] == 2
    assert level_for(500)["level"] == 3
    assert level_for(2000)["level"] == 4
    assert level_for(5000)["level"] == 5
    assert level_for(10000)["level"] == 6
    assert level_for(50000)["level"] == 7


def test_level_bounds_and_next():
    # 负分按 0 处理
    neg = level_for(-30)
    assert neg["level"] == 1
    assert neg["score"] == 0

    # 封顶：最高等级没有下一级，进度记 100%
    top = level_for(10 ** 9)
    assert top["level"] == 7
    assert top["next_level"] is None
    assert top["points_to_next"] == 0
    assert top["progress"] == 1.0

    # 区间中段：level 2（100..499），下一级阈值 500
    mid = level_for(300)
    assert mid["level"] == 2
    assert mid["next_level"] == 3
    assert mid["next_level_score"] == 500
    assert mid["points_to_next"] == 200
    assert 0.0 <= mid["progress"] <= 1.0


def test_levels_monotonic_ascending():
    mins = [entry[0] for entry in LEVELS]
    assert mins == sorted(mins)
    assert mins[0] == 0
    # 等级名非空
    assert all(entry[2] for entry in LEVELS)


# ------------------------------------------------------------------- 规则表
def test_default_rules_present_and_positive():
    for action in ("daily_checkin", "publish_article", "publish_comment", "receive_like"):
        assert action in DEFAULT_POINT_RULES
        assert DEFAULT_POINT_RULES[action] > 0


# ----------------------------------------------------------------- 奖励计算
def test_reward_for_basic():
    assert reward_for("publish_article") == 10
    assert reward_for("publish_comment") == 2
    assert reward_for("receive_like") == 1
    assert reward_for("daily_checkin") == 5


def test_reward_for_unknown_is_zero():
    assert reward_for("no_such_action") == 0


def test_reward_for_first_article_bonus():
    expected = 10 + DEFAULT_POINT_RULES["first_article"]
    assert reward_for("publish_article", is_first=True) == expected


def test_reward_for_streak_bonus():
    # 6 天不足 7 天 → 不加码
    assert reward_for("publish_article", streak_days=6) == 10
    assert reward_for("publish_article", streak_days=7) == 10 + DEFAULT_POINT_RULES["continuous_posting_7d"]
    # 30 天走 30 天档（含 7 天档不叠加，只取更高档）
    assert reward_for("publish_article", streak_days=30) == 10 + DEFAULT_POINT_RULES["continuous_posting_30d"]


def test_reward_for_injected_rules():
    assert reward_for("custom", rules={"custom": 42}) == 42
    assert reward_for("publish_article", is_first=True, rules={"publish_article": 1, "first_article": 2}) == 3


# ----------------------------------------------------------------- 排行排序
def test_rank_entries_order_and_tiebreak():
    entries = [
        {"user_id": 3, "username": "c", "balance": 100},
        {"user_id": 1, "username": "a", "balance": 300},
        {"user_id": 2, "username": "b", "balance": 100},
    ]
    ranked = rank_entries(entries)
    # balance 300 第一；并列 100 时 user_id 小者在前
    assert [e["user_id"] for e in ranked] == [1, 2, 3]
    assert [e["rank"] for e in ranked] == [1, 2, 3]


def test_rank_entries_limit_and_rank():
    entries = [{"user_id": i, "balance": i} for i in range(1, 6)]
    ranked = rank_entries(entries, limit=2)
    assert len(ranked) == 2
    assert ranked[0]["user_id"] == 5
    assert ranked[0]["rank"] == 1
    assert ranked[1]["user_id"] == 4
