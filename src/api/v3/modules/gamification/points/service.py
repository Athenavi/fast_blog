"""points 模块业务逻辑（积分账户 / 流水 / 规则 / 签到 / 兑换）

**与 v2 的差异**（v2 在 `services/advanced_features/points_system.py`）：

| v2 的做法 | 问题 | 本模块 |
|---|---|---|
| 模块级**内存单例**（`_users` / `_transactions` 字典） | 重启即失、多 worker 各一份 | 真表 ``user_points`` / ``points_transactions`` |
| 暴露 ``POST /record-action`` 让**前端自己报动作加分** | 任何登录用户可任意刷分 | **不暴露**这种接口。第一期只保留**每日签到**（幂等、一天一次）与管理端加减分；发文章 / 评论 / 被赞的自动加分留二期，且届时由**服务端事件**触发而非前端上报 |
| 规则是**类内常量** `_rules` | 改积分要改代码 | 规则入库（``points_rules``，含 ``daily_limit`` 防刷） |
| 无余额校验、无流水 | 无法对账 | 每次变动写流水并带 ``balance_after``；扣减时**余额不足直接拒绝** |

兑换**真实发放**：兑拨项就是 ``points_rules`` 里 ``action`` 以 ``exchange:`` 开头的行，
兑换时用同一个 DB 事务「扣分 + 写流水 + 调 ``MembershipService.create_subscription`` 开通套餐」，
不是只记一笔"待发放"。

**等级**：按累计获得积分（``user_points.total_earned``）在 ``LEVELS`` 阈值表里定位等级名，
``level_for`` 是**纯函数**（``GET /points/level/{score}`` 直接暴露它）；当 ``points_rules``
为空（未跑 seed）时，``GET /points/rules`` 回退内置常量 ``DEFAULT_POINT_RULES``
（与 ``scripts/seed_gamification.py`` 的 ``POINTS_RULES`` 一致），公开端点不返回空数组。
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.gamification import PointsRule, PointsTransaction, UserPoints
from shared.models.user import User
from src.api.v3.core.exceptions import BadRequestError, NotFoundError
from src.api.v3.core.logger import get_logger
from src.api.v3.modules.gamification.points.crud import (
    points_rule_crud,
    points_transaction_crud,
    user_points_crud,
)
from src.api.v3.modules.gamification.points.schema import (
    CHECKIN_ACTION,
    EXCHANGE_PREFIX,
    ExchangeRequest,
    PointsAccountOut,
    PointsGrantRequest,
    PointsRuleOut,
    PointsRuleUpdate,
    PointsTransactionOut,
)

logger = get_logger("gamification.points")

MAX_PAGE_SIZE = 100
MAX_LEADERBOARD = 100

# ---------------------------------------------------------------- 常量规则表 / 等级（纯函数，无 DB 依赖）
#: **默认积分规则**（``action -> 积分值``）。与 ``scripts/seed_gamification.py`` 的
#: ``POINTS_RULES`` 保持一致；``points_rules`` 表为空（未跑 seed）时作为回退展示。
DEFAULT_POINT_RULES: dict[str, int] = {
    "daily_checkin": 5,
    "publish_article": 10,
    "publish_comment": 2,
    "receive_like": 1,
    "profile_completed": 5,
    # 二级/加码规则：由服务端事件计算（首篇发文、连续发文），不单独作为可领取动作
    "first_article": 20,
    "continuous_posting_7d": 50,
    "continuous_posting_30d": 200,
}

#: 默认兑换项（值是需要消耗的**正数**积分）
DEFAULT_EXCHANGE_RULES: dict[str, int] = {
    "exchange:vip": 1000,
}

#: 等级阈值：``(最低累计获得积分, 等级序号, 等级名)``，按阈值升序
LEVELS: tuple[tuple[int, int, str], ...] = (
    (0, 1, "新手"),
    (100, 2, "学徒"),
    (500, 3, "活跃"),
    (2000, 4, "资深"),
    (5000, 5, "达人"),
    (10000, 6, "大师"),
    (50000, 7, "宗师"),
)


def level_for(score: int) -> dict:
    """按累计积分算等级（**纯函数**）

    ``score`` 为累计获得积分（``user_points.total_earned``）；负数按 0 处理，
    超过最高阈值封顶在最高等级。返回当前等级、下一级所需积分与区间进度。
    """
    value = max(0, int(score or 0))
    current = LEVELS[0]
    next_entry: Optional[tuple[int, int, str]] = None
    for entry in LEVELS:
        if value >= entry[0]:
            current = entry
        else:
            next_entry = entry
            break
    min_score, level, name = current
    result: dict = {
        "score": value,
        "level": level,
        "name": name,
        "min_score": min_score,
        "next_level": None,
        "next_level_name": None,
        "next_level_score": None,
        "points_to_next": 0,
        "progress": 0.0,
    }
    if next_entry is None:
        # 已封顶：进度视为 100%
        result["progress"] = 1.0
    else:
        next_min, next_level, next_name = next_entry
        span = next_min - min_score
        result.update(
            next_level=next_level,
            next_level_name=next_name,
            next_level_score=next_min,
            points_to_next=next_min - value,
            progress=round((value - min_score) / span, 4) if span > 0 else 0.0,
        )
    return result


def reward_for(
    action: str,
    *,
    is_first: bool = False,
    streak_days: int = 0,
    rules: Optional[dict[str, int]] = None,
) -> int:
    """按动作计算应发积分（**纯函数**）

    ``publish_article`` 支持加码：首篇叠加 ``first_article``；连续发文 ≥7 / ≥30 天再叠加
    对应奖励。未知动作返回 0（不臆造）。``rules`` 可注入覆盖（默认用 ``DEFAULT_POINT_RULES``）。
    """
    table = rules if rules is not None else DEFAULT_POINT_RULES
    total = int(table.get(action, 0))
    if total == 0:
        return 0
    if action == "publish_article":
        if is_first:
            total += int(table.get("first_article", 0))
        if int(streak_days) >= 30:
            total += int(table.get("continuous_posting_30d", 0))
        elif int(streak_days) >= 7:
            total += int(table.get("continuous_posting_7d", 0))
    return total


def rank_entries(entries: list[dict], *, limit: int = 20) -> list[dict]:
    """排行榜排序并赋名次（**纯函数**）

    输入每项形如 ``{"user_id": int, "username": str|None, "balance": int}``；
    按 ``balance`` 降序、``user_id`` 升序打破并列，截取前 ``limit`` 名并写 ``rank``。
    ``limit <= 0`` 时回退上限 ``MAX_LEADERBOARD``。
    """
    ordered = sorted(
        entries,
        key=lambda e: (-int(e.get("balance", 0) or 0), int(e.get("user_id", 0) or 0)),
    )
    cap = int(limit) if int(limit) > 0 else MAX_LEADERBOARD
    return [
        {
            "rank": index + 1,
            "user_id": entry.get("user_id"),
            "username": entry.get("username"),
            "balance": int(entry.get("balance", 0) or 0),
        }
        for index, entry in enumerate(ordered[:cap])
    ]


def _account_out(row: UserPoints, *, checked_in_today: bool) -> dict:
    return PointsAccountOut(
        user_id=row.user_id,
        balance=int(row.balance or 0),
        total_earned=int(row.total_earned or 0),
        total_spent=int(row.total_spent or 0),
        last_checkin_at=row.last_checkin_at,
        checked_in_today=checked_in_today,
        updated_at=row.updated_at,
    ).model_dump(mode="json")


def _tx_out(row: PointsTransaction) -> dict:
    return PointsTransactionOut.model_validate(row, from_attributes=True).model_dump(mode="json")


def _rule_out(row: PointsRule) -> dict:
    return PointsRuleOut.model_validate(row, from_attributes=True).model_dump(mode="json")


class PointsService:
    """积分"""

    # ------------------------------------------------------------ 账户与变动
    async def _account(self, db: AsyncSession, user_id: int, *, create: bool = True) -> UserPoints:
        row = await user_points_crud.get_by(db, user_id=user_id)
        if row is None:
            if not create:
                raise NotFoundError("积分账户不存在")
            if await db.get(User, user_id) is None:
                raise NotFoundError("用户不存在")
            now = datetime.now()
            row = await user_points_crud.create(
                db,
                {
                    "user_id": user_id,
                    "balance": 0,
                    "total_earned": 0,
                    "total_spent": 0,
                    "updated_at": now,
                },
            )
        return row

    async def _apply(
        self,
        db: AsyncSession,
        user_id: int,
        *,
        amount: int,
        action: str,
        description: Optional[str] = None,
        reference_id: Optional[int] = None,
        reference_type: Optional[str] = None,
    ) -> tuple[UserPoints, PointsTransaction]:
        """给账户加分/扣分并写一条流水（同一事务内）"""
        if amount == 0:
            raise BadRequestError("变动值不能为 0")
        account = await self._account(db, user_id)
        now = datetime.now()
        balance = int(account.balance or 0) + int(amount)
        if balance < 0:
            raise BadRequestError(f"积分不足（当前 {int(account.balance or 0)}，需要 {-int(amount)}）")
        data: dict = {"balance": balance, "updated_at": now}
        if amount > 0:
            data["total_earned"] = int(account.total_earned or 0) + int(amount)
        else:
            data["total_spent"] = int(account.total_spent or 0) + int(-amount)
        account = await user_points_crud.update(db, account, data)
        tx = await points_transaction_crud.create(
            db,
            {
                "user_id": user_id,
                "amount": int(amount),
                "balance_after": balance,
                "action": action,
                "description": description,
                "reference_id": reference_id,
                "reference_type": reference_type,
                "created_at": now,
                "updated_at": now,
            },
        )
        return account, tx

    @staticmethod
    def _checked_in_today(account: UserPoints) -> bool:
        last = account.last_checkin_at
        return bool(last is not None and last.date() == datetime.now().date())

    async def award(
        self,
        db: AsyncSession,
        user_id: int,
        *,
        amount: int,
        action: str,
        description: Optional[str] = None,
        reference_id: Optional[int] = None,
        reference_type: Optional[str] = None,
    ) -> tuple[UserPoints, PointsTransaction]:
        """**公开的加分入口**：供其它模块联动（如勋章奖励、二期的事件埋点）

        与内部的 ``_apply`` 的区别：只接受**正数** —— 扣分请走 ``deduct`` / ``exchange``。
        """
        if int(amount) <= 0:
            raise BadRequestError("award 只用于加分（amount 必须为正）")
        return await self._apply(
            db,
            user_id,
            amount=int(amount),
            action=action,
            description=description,
            reference_id=reference_id,
            reference_type=reference_type,
        )

    # ------------------------------------------------------------ 查询
    async def account(self, db: AsyncSession, user_id: int) -> dict:
        row = await self._account(db, user_id)
        return _account_out(row, checked_in_today=self._checked_in_today(row))

    async def history(
        self, db: AsyncSession, user_id: int, *, page: int = 1, page_size: int = 20
    ) -> tuple[list[dict], int]:
        rows, total = await points_transaction_crud.list(
            db, page=page, page_size=min(page_size, MAX_PAGE_SIZE), filters={"user_id": user_id}
        )
        return [_tx_out(row) for row in rows], total

    async def me(self, db: AsyncSession, user_id: int, *, recent: int = 10) -> dict:
        """我的积分：余额 + 等级 + 最近流水（一次拿齐，供 ``GET /points/me``）"""
        row = await self._account(db, user_id)
        txs, _total = await points_transaction_crud.list(
            db, page=1, page_size=max(1, min(recent, MAX_PAGE_SIZE)), filters={"user_id": user_id}
        )
        return {
            "account": _account_out(row, checked_in_today=self._checked_in_today(row)),
            "level": level_for(int(row.total_earned or 0)),
            "recent_transactions": [_tx_out(tx) for tx in txs],
        }

    async def leaderboard(self, db: AsyncSession, *, limit: int = 20) -> list[dict]:
        """排行榜：SQL 先按余额倒序取前 N（真表聚合），再用 ``rank_entries`` 赋名次"""
        cap = max(1, min(limit, MAX_LEADERBOARD))
        rows = (
            await db.execute(
                select(UserPoints, User)
                .join(User, User.id == UserPoints.user_id)
                .order_by(UserPoints.balance.desc(), UserPoints.user_id.asc())
                .limit(cap)
            )
        ).all()
        entries = [
            {
                "user_id": account.user_id,
                "username": getattr(user, "username", None),
                "balance": int(account.balance or 0),
            }
            for account, user in rows
        ]
        return rank_entries(entries, limit=cap)

    async def rules(self, db: AsyncSession, *, exchange: Optional[bool] = None) -> list[dict]:
        rows, _total = await points_rule_crud.list(db, page=1, page_size=0)
        if not rows:
            # 未跑 seed（points_rules 为空）时回退内置常量，公开端点不返回空数组
            return self._default_rules(exchange)
        items: list[dict] = []
        for row in sorted(rows, key=lambda r: (r.sort_order or 0, r.id)):
            is_exchange = str(row.action or "").startswith(EXCHANGE_PREFIX)
            if exchange is not None and is_exchange != exchange:
                continue
            if is_exchange:
                # 兑换项对外暴露「需要消耗的正数积分」
                items.append(
                    {
                        "action": row.action,
                        "cost": abs(int(row.points or 0)),
                        "description": row.description,
                        "is_active": bool(row.is_active),
                    }
                )
            else:
                items.append(_rule_out(row))
        return items

    @staticmethod
    def _default_rules(exchange: Optional[bool]) -> list[dict]:
        """内置常量规则的回退视图（``points_rules`` 为空时使用）

        ``exchange=False`` 只给加分规则；``True`` 只给兑换项；``None`` 全给。
        """
        items: list[dict] = []
        if exchange is not True:
            for action, points in DEFAULT_POINT_RULES.items():
                items.append(
                    {
                        "id": 0,
                        "action": action,
                        "points": points,
                        "description": "内置默认规则（未跑 seed_gamification.py）",
                        "daily_limit": 0,
                        "is_active": True,
                        "sort_order": 0,
                    }
                )
        if exchange is not False:
            for action, cost in DEFAULT_EXCHANGE_RULES.items():
                items.append(
                    {
                        "action": action,
                        "cost": abs(int(cost)),
                        "description": "内置默认兑换项（未跑 seed_gamification.py）",
                        "is_active": True,
                    }
                )
        return items

    # ------------------------------------------------------------ 签到
    async def checkin(self, db: AsyncSession, user_id: int) -> dict:
        rule = await points_rule_crud.get_by(db, action=CHECKIN_ACTION)
        if rule is None or not rule.is_active:
            raise BadRequestError("签到未启用（缺少 daily_checkin 规则，请先跑 seed 脚本）")
        account = await self._account(db, user_id)
        if self._checked_in_today(account):
            raise BadRequestError("今天已经签到过了")
        amount = int(rule.points or 0)
        account, _tx = await self._apply(
            db,
            user_id,
            amount=amount,
            action=CHECKIN_ACTION,
            description=rule.description or "每日签到",
        )
        now = datetime.now()
        account = await user_points_crud.update(
            db, account, {"last_checkin_at": now, "updated_at": now}
        )
        return _account_out(account, checked_in_today=True) | {"awarded": amount}

    # ------------------------------------------------------------ 兑换（真实发放）
    async def exchange(self, db: AsyncSession, user_id: int, payload: ExchangeRequest) -> dict:
        if not payload.action.startswith(EXCHANGE_PREFIX):
            raise BadRequestError(f"兑换项必须以 {EXCHANGE_PREFIX} 开头")
        rule = await points_rule_crud.get_by(db, action=payload.action)
        if rule is None or not rule.is_active:
            raise NotFoundError("兑换项不存在或已停用")
        cost = abs(int(rule.points or 0))
        if cost <= 0:
            raise BadRequestError("兑换项的积分消耗未正确配置")
        if payload.plan_id is None:
            raise BadRequestError("兑换 VIP 需要提供 plan_id")

        # 先确认套餐真实存在（拿价格用于开通订阅的"已付金额"）
        from shared.services.core.membership import create_membership_service

        membership = create_membership_service(db)
        plans = await membership.get_available_plans()
        plan = next((item for item in plans if int(item.get("id", -1)) == int(payload.plan_id)), None)
        if plan is None:
            raise NotFoundError("套餐不存在或未上架")

        account, tx = await self._apply(
            db,
            user_id,
            amount=-cost,
            action=payload.action,
            description=rule.description or f"兑换 {payload.action}",
            reference_id=payload.plan_id,
            reference_type="vip_plan",
        )
        # 用积分抵扣：把套餐价格作为"已付金额"传给订阅服务（积分即货币），transaction_id 标注来源
        subscription = await membership.create_subscription(
            user_id,
            int(payload.plan_id),
            payment_amount=float(plan.get("price") or 0),
            transaction_id=f"points:{tx.id}",
        )
        logger.info(
            "积分兑换成功: user=%s action=%s cost=%s plan=%s",
            user_id,
            payload.action,
            cost,
            payload.plan_id,
        )
        return {
            "account": _account_out(account, checked_in_today=self._checked_in_today(account)),
            "transaction": _tx_out(tx),
            "subscription": subscription,
        }

    # ------------------------------------------------------------ 管理端
    async def stats(self, db: AsyncSession) -> dict:
        aggregates = (
            await db.execute(
                select(
                    func.count().label("accounts"),
                    func.coalesce(func.sum(UserPoints.balance), 0).label("balance"),
                    func.coalesce(func.sum(UserPoints.total_earned), 0).label("earned"),
                    func.coalesce(func.sum(UserPoints.total_spent), 0).label("spent"),
                ).select_from(UserPoints)
            )
        ).one()
        transactions = int(
            (
                await db.execute(select(func.count()).select_from(PointsTransaction))
            ).scalar()
            or 0
        )
        active_rules = int(
            (
                await db.execute(
                    select(func.count())
                    .select_from(PointsRule)
                    .where(PointsRule.is_active.is_(True))
                )
            ).scalar()
            or 0
        )
        return {
            "total_accounts": int(aggregates.accounts or 0),
            "total_balance": int(_num(aggregates.balance)),
            "total_earned": int(_num(aggregates.earned)),
            "total_spent": int(_num(aggregates.spent)),
            "transaction_count": transactions,
            "active_rules": active_rules,
            "top_holders": await self.leaderboard(db, limit=10),
        }

    async def grant(
        self, db: AsyncSession, payload: PointsGrantRequest, operator_id: int
    ) -> dict:
        account, tx = await self._apply(
            db,
            payload.user_id,
            amount=int(payload.amount),
            action="admin_grant",
            description=payload.reason or f"管理员加分（operator={operator_id}）",
            reference_id=operator_id,
            reference_type="admin",
        )
        return {
            "account": _account_out(account, checked_in_today=self._checked_in_today(account)),
            "transaction": _tx_out(tx),
        }

    async def deduct(
        self, db: AsyncSession, payload: PointsGrantRequest, operator_id: int
    ) -> dict:
        account, tx = await self._apply(
            db,
            payload.user_id,
            amount=-int(payload.amount),
            action="admin_deduct",
            description=payload.reason or f"管理员扣分（operator={operator_id}）",
            reference_id=operator_id,
            reference_type="admin",
        )
        return {
            "account": _account_out(account, checked_in_today=self._checked_in_today(account)),
            "transaction": _tx_out(tx),
        }

    async def update_rule(
        self, db: AsyncSession, rule_id: int, payload: PointsRuleUpdate
    ) -> dict:
        row = await points_rule_crud.get(db, rule_id)
        if row is None:
            raise NotFoundError("积分规则不存在")
        data = payload.model_dump(exclude_unset=True)
        if not data:
            return _rule_out(row)
        updated = await points_rule_crud.update(db, row, data | {"updated_at": datetime.now()})
        return _rule_out(updated)


def _num(value) -> Decimal:
    """聚合结果可能是 Decimal / int / None，统一成可 int() 的值"""
    if value is None:
        return Decimal("0")
    return value if isinstance(value, Decimal) else Decimal(str(value))


points_service = PointsService()
