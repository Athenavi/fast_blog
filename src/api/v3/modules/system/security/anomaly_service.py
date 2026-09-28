"""异常行为检测（v3 真实实现：真表窗口聚合，不再使用内存态）

替代 v2 的 ``shared/services/articles/anomaly_detector.py``：v2 把登录尝试、用户活动、
访问模式都塞进 ``defaultdict(list)``（重启即丢、多 worker 各一份、跨进程不可见），
本实现改为对**真表**做时间窗聚合：

  - ``login_attempts``：username / ip_address / is_success / created_at
  - ``audit_logs``：ip_address / user_name / action / created_at

四类检测（全部可解释，阈值可在后台调整并**持久化**到 ``system_settings``）：

  1. **暴力破解**：同一「账号 + IP」在窗口内失败次数超阈值
  2. **撞库扫描**：同一 IP 在窗口内尝试了过多**不同**账号
  3. **非常规时段登录**：成功登录集中在深夜时段且次数偏多
  4. **速率滥用**：同一 IP 在窗口内的审计动作数异常偏高

可疑 IP 评分 = 失败数×2 + 不同账号数×3 + 动作数/10，用于排序定位源头。
"""

import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.security.login_attempt import LoginAttempt
from shared.models.system.audit_log import AuditLog
from src.api.v3.core.exceptions import BadRequestError
from src.api.v3.core.logger import get_logger
from src.api.v3.modules.system.setting.crud import setting_crud

logger = get_logger("security.anomaly")

#: 阈值持久化键（``system_settings``，值为 JSON 文本）
THRESHOLDS_KEY = "security.anomaly.thresholds"

DEFAULT_THRESHOLDS: Dict[str, Any] = {
    "brute_force_failures": 5,
    "brute_force_window_minutes": 15,
    "spray_usernames": 5,
    "spray_window_minutes": 15,
    "unusual_hour_start": 0,
    "unusual_hour_end": 6,
    "unusual_hour_logins": 3,
    "unusual_hour_window_hours": 24,
    "rate_abuse_actions": 120,
    "rate_abuse_window_minutes": 5,
    "max_items": 50,
}

#: 可调阈值的合法键集合
THRESHOLD_KEYS = frozenset(DEFAULT_THRESHOLDS)


def _iso(value: Any) -> Optional[str]:
    return value.isoformat() if isinstance(value, datetime) else None


def _severity(count: int, threshold: int) -> str:
    """超过阈值越多越严重：≥3 倍 critical，≥2 倍 high，其余 medium"""
    if threshold <= 0:
        return "medium"
    ratio = count / threshold
    if ratio >= 3:
        return "critical"
    if ratio >= 2:
        return "high"
    return "medium"


def _ip_weight(item: Dict[str, Any]) -> int:
    """可疑 IP 的加权分（不同异常类型权重不同）"""
    kind = item["type"]
    if kind == "brute_force":
        return int(item["count"]) * 2
    if kind == "credential_spray":
        return int(item["count"]) * 3
    if kind == "rate_abuse":
        return int(item["count"]) // 10
    return int(item["count"])


class AnomalyDetectionService:
    """异常行为检测（真表聚合 + 可持久化阈值）"""

    # ------------------------------------------------------------------ 阈值
    async def load_thresholds(self, db: AsyncSession) -> Dict[str, Any]:
        """读取阈值（缺失或损坏时回退默认值）"""
        row = await setting_crud.get_by(db, setting_key=THRESHOLDS_KEY)
        stored: Dict[str, Any] = {}
        if row is not None and row.setting_value:
            try:
                parsed = json.loads(row.setting_value)
                if isinstance(parsed, dict):
                    stored = parsed
            except (TypeError, ValueError):
                logger.warning("异常检测阈值不是合法 JSON，已回退默认值")

        merged = dict(DEFAULT_THRESHOLDS)
        for key, value in stored.items():
            if key in THRESHOLD_KEYS and isinstance(value, (int, float)) and not isinstance(value, bool):
                merged[key] = int(value)
        return merged

    async def save_thresholds(
        self, db: AsyncSession, values: Dict[str, Any]
    ) -> Dict[str, Any]:
        """增量更新阈值并持久化（未知键一律拒绝，避免写脏数据）

        注意：``system_settings`` 表没有 ``created_by`` 列，故不记录修改人；
        变更会在应用日志中留痕（``security.anomaly`` logger）。
        """
        unknown = set(values) - THRESHOLD_KEYS
        if unknown:
            raise BadRequestError(f"不支持的阈值项：{', '.join(sorted(unknown))}")
        if not values:
            raise BadRequestError("没有需要更新的阈值")

        merged = {**(await self.load_thresholds(db)), **{k: int(v) for k, v in values.items()}}
        payload = json.dumps(merged, ensure_ascii=False)

        row = await setting_crud.get_by(db, setting_key=THRESHOLDS_KEY)
        if row is None:
            await setting_crud.create(
                db,
                {
                    "setting_key": THRESHOLDS_KEY,
                    "setting_value": payload,
                    "setting_type": "json",
                    "description": "异常行为检测阈值（JSON）",
                    "is_public": False,
                },
            )
        else:
            await setting_crud.update(db, row, {"setting_value": payload})
        logger.info("异常检测阈值已更新：%s", values)
        return merged

    # ------------------------------------------------------------------ 检测
    async def detect(
        self, db: AsyncSession, *, limit: Optional[int] = None, thresholds: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """执行四类检测并汇总（全部来自真表聚合，无内存态）"""
        th = thresholds or await self.load_thresholds(db)
        now = datetime.now()
        limit = int(limit or th["max_items"])
        items: List[Dict[str, Any]] = []

        items.extend(await self._detect_brute_force(db, now, th, limit))
        items.extend(await self._detect_credential_spray(db, now, th, limit))
        items.extend(await self._detect_unusual_hours(db, now, th, limit))
        items.extend(await self._detect_rate_abuse(db, now, th, limit))

        by_type: Dict[str, int] = {}
        by_severity: Dict[str, int] = {}
        ip_scores: Dict[str, Dict[str, Any]] = {}
        for item in items:
            by_type[item["type"]] = by_type.get(item["type"], 0) + 1
            by_severity[item["severity"]] = by_severity.get(item["severity"], 0) + 1
            ip = item.get("ip_address")
            if ip:
                entry = ip_scores.setdefault(ip, {"ip_address": ip, "score": 0, "anomalies": []})
                entry["score"] += _ip_weight(item)
                entry["anomalies"].append(item["type"])

        top_ips: Sequence[Dict[str, Any]] = sorted(
            ip_scores.values(), key=lambda entry: entry["score"], reverse=True
        )[:10]

        return {
            "generated_at": now.isoformat(),
            "data_source": "login_attempts + audit_logs（真实表窗口聚合）",
            "thresholds": th,
            "summary": {"total": len(items), "by_type": by_type, "by_severity": by_severity},
            "items": items,
            "top_suspicious_ips": list(top_ips),
        }

    @staticmethod
    async def _detect_brute_force(
        db: AsyncSession, now: datetime, th: Dict[str, Any], limit: int
    ) -> List[Dict[str, Any]]:
        threshold = int(th["brute_force_failures"])
        window = int(th["brute_force_window_minutes"])
        since = now - timedelta(minutes=window)

        rows = (
            await db.execute(
                select(
                    LoginAttempt.username,
                    LoginAttempt.ip_address,
                    func.count().label("failures"),
                    func.min(LoginAttempt.created_at).label("first_at"),
                    func.max(LoginAttempt.created_at).label("last_at"),
                )
                .where(
                    LoginAttempt.created_at >= since,
                    LoginAttempt.is_success.is_(False),
                    LoginAttempt.username.is_not(None),
                )
                .group_by(LoginAttempt.username, LoginAttempt.ip_address)
                .having(func.count() >= threshold)
                .order_by(func.count().desc())
                .limit(limit)
            )
        ).all()

        return [
            {
                "type": "brute_force",
                "severity": _severity(int(row.failures), threshold),
                "target": row.username,
                "ip_address": row.ip_address,
                "count": int(row.failures),
                "threshold": threshold,
                "window_minutes": window,
                "first_at": _iso(row.first_at),
                "last_at": _iso(row.last_at),
                "detail": f"账号「{row.username}」在 {window} 分钟内失败 {row.failures} 次（阈值 {threshold}）",
            }
            for row in rows
        ]

    @staticmethod
    async def _detect_credential_spray(
        db: AsyncSession, now: datetime, th: Dict[str, Any], limit: int
    ) -> List[Dict[str, Any]]:
        threshold = int(th["spray_usernames"])
        window = int(th["spray_window_minutes"])
        since = now - timedelta(minutes=window)
        distinct_users = func.count(func.distinct(LoginAttempt.username))

        rows = (
            await db.execute(
                select(
                    LoginAttempt.ip_address,
                    distinct_users.label("usernames"),
                    func.count().label("attempts"),
                )
                .where(LoginAttempt.created_at >= since, LoginAttempt.ip_address.is_not(None))
                .group_by(LoginAttempt.ip_address)
                .having(distinct_users >= threshold)
                .order_by(distinct_users.desc())
                .limit(limit)
            )
        ).all()

        return [
            {
                "type": "credential_spray",
                "severity": _severity(int(row.usernames), threshold),
                "target": None,
                "ip_address": row.ip_address,
                "count": int(row.usernames),
                "attempts": int(row.attempts),
                "threshold": threshold,
                "window_minutes": window,
                "detail": (
                    f"IP {row.ip_address} 在 {window} 分钟内尝试了 {row.usernames} 个不同账号"
                    f"（共 {row.attempts} 次，阈值 {threshold}）"
                ),
            }
            for row in rows
        ]

    @staticmethod
    async def _detect_unusual_hours(
        db: AsyncSession, now: datetime, th: Dict[str, Any], limit: int
    ) -> List[Dict[str, Any]]:
        threshold = int(th["unusual_hour_logins"])
        window_hours = int(th["unusual_hour_window_hours"])
        hour_start = int(th["unusual_hour_start"])
        hour_end = int(th["unusual_hour_end"])
        since = now - timedelta(hours=window_hours)
        hour_expr = func.extract("hour", LoginAttempt.created_at)

        rows = (
            await db.execute(
                select(LoginAttempt.username, func.count().label("logins"))
                .where(
                    LoginAttempt.created_at >= since,
                    LoginAttempt.is_success.is_(True),
                    LoginAttempt.username.is_not(None),
                    hour_expr.between(hour_start, hour_end),
                )
                .group_by(LoginAttempt.username)
                .having(func.count() >= threshold)
                .order_by(func.count().desc())
                .limit(limit)
            )
        ).all()

        return [
            {
                "type": "unusual_hours",
                "severity": _severity(int(row.logins), threshold),
                "target": row.username,
                "ip_address": None,
                "count": int(row.logins),
                "threshold": threshold,
                "window_hours": window_hours,
                "detail": (
                    f"账号「{row.username}」在 {window_hours} 小时内的 {hour_start}:00-{hour_end}:59 "
                    f"时段成功登录 {row.logins} 次（阈值 {threshold}）"
                ),
            }
            for row in rows
        ]

    @staticmethod
    async def _detect_rate_abuse(
        db: AsyncSession, now: datetime, th: Dict[str, Any], limit: int
    ) -> List[Dict[str, Any]]:
        threshold = int(th["rate_abuse_actions"])
        window = int(th["rate_abuse_window_minutes"])
        since = now - timedelta(minutes=window)

        rows = (
            await db.execute(
                select(AuditLog.ip_address, func.count().label("actions"))
                .where(AuditLog.created_at >= since, AuditLog.ip_address.is_not(None))
                .group_by(AuditLog.ip_address)
                .having(func.count() >= threshold)
                .order_by(func.count().desc())
                .limit(limit)
            )
        ).all()

        return [
            {
                "type": "rate_abuse",
                "severity": _severity(int(row.actions), threshold),
                "target": None,
                "ip_address": row.ip_address,
                "count": int(row.actions),
                "threshold": threshold,
                "window_minutes": window,
                "detail": f"IP {row.ip_address} 在 {window} 分钟内产生 {row.actions} 条审计动作（阈值 {threshold}）",
            }
            for row in rows
        ]


anomaly_detection_service = AnomalyDetectionService()
