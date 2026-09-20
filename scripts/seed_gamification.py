#!/usr/bin/env python3
"""T5-11 批次 12：灌入积分规则与勋章定义（幂等）。

**为什么需要种子**：v2 把「积分规则」写成 `services/advanced_features/points_system.py` 里的
类内常量 `_rules`、把「18 个内置徽章」写成 `achievement_badges.py` 里的类内常量 —— 改一条
就得改代码。v3 把它们**入库**（``points_rules`` / ``badge_definitions``），因此需要本脚本灌初值。

**统计口径说明**：自动授予只支持 ``badge_definitions.condition_type`` 里的五种
（``article_count`` / ``max_article_likes`` / ``follower_count`` / ``comment_count`` /
``like_received``），它们都能在真实表上算出来。v2 里那类"连续 N 天发文"等**无统计源**的
勋章，这里一律标成 ``is_manual=True``（只能手工授予），而不是假装能自动判定。

用法::

    python -m scripts.seed_gamification            # dry-run：只打印将要写入的内容
    python -m scripts.seed_gamification --apply    # 幂等写库（按 action / badge_key upsert）
"""

from __future__ import annotations

import argparse
import asyncio
import importlib
from datetime import datetime

from sqlalchemy import select

from shared.models import _LAZY_IMPORTS

for _m in sorted(set(_LAZY_IMPORTS.values())):
    importlib.import_module(f"shared.models{_m}")

from shared.models.gamification import BadgeDefinition, PointsRule  # noqa: E402
from src.utils.database.main import get_async_session_context  # noqa: E402

#: 积分规则：(action, points, description, daily_limit, sort_order)
POINTS_RULES: list[tuple[str, int, str, int, int]] = [
    ("daily_checkin", 5, "每日签到", 1, 1),
    ("publish_article", 10, "发布文章", 0, 2),
    ("publish_comment", 2, "发表评论", 0, 3),
    ("receive_like", 1, "作品被赞", 0, 4),
    # 兑换项：action 以 exchange: 开头，points 为负 = 需要消耗的积分
    ("exchange:vip", -1000, "积分兑换 VIP（需选择套餐）", 0, 9),
]

#: 勋章定义：(badge_key, name, category, condition_type, condition_value, points_reward, is_manual, icon, sort_order)
BADGES: list[tuple[str, str, str, str | None, int, int, bool, str, int]] = [
    ("first_article", "初次执笔", "writing", "article_count", 1, 10, False, "edit", 1),
    ("article_10", "笔耕不辍", "writing", "article_count", 10, 50, False, "document", 2),
    ("article_50", "多产作者", "writing", "article_count", 50, 200, False, "collection", 3),
    ("article_100", "著作等身", "writing", "article_count", 100, 500, False, "files", 4),
    ("likes_10", "小有名气", "quality", "max_article_likes", 10, 20, False, "star", 1),
    ("likes_100", "广受欢迎", "quality", "max_article_likes", 100, 100, False, "star", 2),
    ("likes_500", "爆款作者", "quality", "max_article_likes", 500, 300, False, "trending-up", 3),
    ("liked_1000", "千赞达人", "quality", "like_received", 1000, 500, False, "heart", 4),
    ("follower_10", "初具人气", "social", "follower_count", 10, 30, False, "user", 1),
    ("follower_100", "百人关注", "social", "follower_count", 100, 150, False, "user", 2),
    ("follower_1000", "千人瞩目", "social", "follower_count", 1000, 800, False, "users", 3),
    ("comment_10", "热心读者", "community", "comment_count", 10, 20, False, "message", 1),
    ("comment_100", "社区活跃", "community", "comment_count", 100, 100, False, "message", 2),
    ("comment_500", "评论之星", "community", "comment_count", 500, 300, False, "award", 3),
    # 无统计源 → 只能手工授予（诚实标注，不做假判定）
    ("verified_expert", "认证专家", "special", None, 0, 200, True, "badge-check", 1),
    ("top_writer", "年度作者", "special", None, 0, 500, True, "trophy", 2),
    ("early_bird", "元老用户", "special", None, 0, 100, True, "clock", 3),
    ("contributor", "优秀贡献者", "special", None, 0, 300, True, "hand-heart", 4),
]


async def main(apply: bool) -> int:
    if not apply:
        print(f"[dry-run] 积分规则 {len(POINTS_RULES)} 条：")
        for action, points, description, daily_limit, _order in POINTS_RULES:
            print(f"  {action:<18} points={points:<6} limit={daily_limit:<3} {description}")
        print(
            f"[dry-run] 勋章定义 {len(BADGES)} 条（自动 {sum(1 for b in BADGES if not b[6])} / 手工 {sum(1 for b in BADGES if b[6])}）：")
        for key, name, category, ctype, cvalue, reward, manual, _icon, _order in BADGES:
            kind = "manual" if manual else f"{ctype}>={cvalue}"
            print(f"  {key:<18} {category:<10} {kind:<22} reward={reward:<4} {name}")
        print("\n[dry-run] 未写库。确认无误后加 --apply")
        return 0

    async with get_async_session_context() as db:
        now = datetime.now()
        created = updated = 0
        for action, points, description, daily_limit, sort_order in POINTS_RULES:
            row = (
                await db.execute(select(PointsRule).where(PointsRule.action == action))
            ).scalar_one_or_none()
            data = {
                "action": action,
                "points": points,
                "description": description,
                "daily_limit": daily_limit,
                "is_active": True,
                "sort_order": sort_order,
                "updated_at": now,
            }
            if row is None:
                db.add(PointsRule(created_at=now, **data))
                created += 1
            else:
                for key, value in data.items():
                    setattr(row, key, value)
                updated += 1
        print(f"  points_rules: 新建 {created} / 更新 {updated}")

        created = updated = 0
        for key, name, category, ctype, cvalue, reward, manual, icon, sort_order in BADGES:
            row = (
                await db.execute(
                    select(BadgeDefinition).where(BadgeDefinition.badge_key == key)
                )
            ).scalar_one_or_none()
            data = {
                "badge_key": key,
                "name": name,
                "category": category,
                "icon": icon,
                "points_reward": reward,
                "condition_type": ctype,
                "condition_value": cvalue,
                "is_manual": manual,
                "is_active": True,
                "sort_order": sort_order,
                "updated_at": now,
            }
            if row is None:
                db.add(BadgeDefinition(created_at=now, **data))
                created += 1
            else:
                for field, value in data.items():
                    setattr(row, field, value)
                updated += 1
        print(f"  badge_definitions: 新建 {created} / 更新 {updated}")

        await db.commit()
        print("[OK] gamification 种子数据写入完成")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="灌入积分规则与勋章定义（幂等）")
    parser.add_argument("--apply", action="store_true", help="写库（默认仅 dry-run）")
    args = parser.parse_args()
    raise SystemExit(asyncio.run(main(args.apply)))
