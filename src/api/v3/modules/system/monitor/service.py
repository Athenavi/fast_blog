"""monitor 模块的业务逻辑

数据源两类，都不新增表：

  - **服务器信息**：`psutil`（已在 requirements）采集 CPU / 内存 / 磁盘 / 进程。
    采样是**同步阻塞**调用（`psutil.disk_usage` 在网络盘或卸载中的挂载点上可能卡住），
    统一用 `asyncio.to_thread` 包起来，不阻塞事件循环。
  - **在线会话**：查既有的 `user_sessions` 表；踢下线以 DB 的 `is_active` 为准，
    同时**尽力**清理 Redis 侧会话（`SessionManagementService.revoke_session`）。

功能参考官方 FastApiAdmin 的 `modules/monitor/{server,online}`，实现按 v3 风格重写。
"""

import asyncio
import os
import platform
import sys
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Tuple

import psutil
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.user.user_session import UserSession
from shared.services.users.session_management_service import session_management_service
from src.api.v3.core.logger import get_logger

logger = get_logger("monitor")

#: 超过这个秒数没有活动就不算“在线”
ONLINE_WINDOW_SECONDS = int(os.getenv("MONITOR_ONLINE_WINDOW", "1800"))


def _bytes_to_int(value: int | None) -> int:
    return int(value or 0)


class MonitorService:
    """系统监控服务"""

    # ── 服务器信息 ────────────────────────────────────────────────
    async def server_info(self) -> Dict[str, Any]:
        """采集服务器信息（同步采样放到线程里跑）"""
        return await asyncio.to_thread(self._collect_server_info)

    @staticmethod
    def _collect_server_info() -> Dict[str, Any]:
        cpu_count = psutil.cpu_count(logical=True) or 1
        cpu_percent = psutil.cpu_percent(interval=0.1)

        memory = psutil.virtual_memory()

        disks: List[Dict[str, Any]] = []
        for part in psutil.disk_partitions(all=False):
            try:
                usage = psutil.disk_usage(part.mountpoint)
            except (PermissionError, OSError):
                # 光驱 / 未挂载设备等，跳过即可
                continue
            disks.append(
                {
                    "device": part.device,
                    "mountpoint": part.mountpoint,
                    "fstype": part.fstype,
                    "total": _bytes_to_int(usage.total),
                    "used": _bytes_to_int(usage.used),
                    "percent": float(usage.percent),
                }
            )

        boot_time = psutil.boot_time()
        process = psutil.Process()
        try:
            threads = process.num_threads()
        except (psutil.Error, OSError):
            threads = 0

        return {
            "platform": f"{platform.system()} {platform.release()}",
            "hostname": platform.node(),
            "python_version": sys.version.split()[0],
            "boot_time": datetime.fromtimestamp(boot_time).isoformat(),
            "uptime_seconds": int(time.time() - boot_time),
            "cpu": {
                "count": cpu_count,
                "percent": float(cpu_percent),
                "load_avg": MonitorService._load_avg(),
            },
            "memory": {
                "total": _bytes_to_int(memory.total),
                "used": _bytes_to_int(memory.used),
                "percent": float(memory.percent),
            },
            "disks": disks,
            "process": {
                "pid": process.pid,
                "rss": _bytes_to_int(process.memory_info().rss),
                "threads": threads,
            },
        }

    @staticmethod
    def _load_avg() -> List[float]:
        """1/5/15 分钟负载；Windows 没有该指标，返回空列表"""
        if hasattr(psutil, "getloadavg"):
            try:
                return [round(value, 2) for value in psutil.getloadavg()]
            except (OSError, AttributeError):
                return []
        return []

    # ── 在线会话 ──────────────────────────────────────────────────
    @staticmethod
    def _online_condition():
        """“在线” = 会话活跃 且（窗口期内有活动，或从未记录过活动）"""
        since = datetime.now() - timedelta(seconds=ONLINE_WINDOW_SECONDS)
        return UserSession.is_active.is_(True) & (
            (UserSession.last_activity >= since) | (UserSession.last_activity.is_(None))
        )

    @staticmethod
    def _to_item(row: UserSession) -> Dict[str, Any]:
        """转成对外结构 —— **刻意不含 access_token / refresh_token**"""
        return {
            "id": row.id,
            "user_id": row.user_id,
            "device_info": row.device_info,
            "ip_address": row.ip_address,
            "location": row.location,
            "last_activity": row.last_activity.isoformat() if row.last_activity else None,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }

    async def online_list(
        self,
        db: AsyncSession,
        *,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """在线会话分页列表"""
        return await self._online_query(db, page=page, page_size=page_size)

    async def online_list_all(self, db: AsyncSession, *, limit: int = 20) -> Tuple[List[Dict[str, Any]], int]:
        """在线会话（供总览页取前 N 条）"""
        return await self._online_query(db, page=1, page_size=limit)

    async def _online_query(
        self,
        db: AsyncSession,
        *,
        page: int,
        page_size: int,
    ) -> Tuple[List[Dict[str, Any]], int]:
        condition = self._online_condition()

        total = await db.scalar(select(func.count()).select_from(UserSession).where(condition))
        rows = (
            await db.execute(
                select(UserSession)
                .where(condition)
                .order_by(UserSession.last_activity.desc().nullslast(), UserSession.id.desc())
                .offset((max(page, 1) - 1) * page_size)
                .limit(page_size)
            )
        ).scalars().all()

        return [self._to_item(row) for row in rows], int(total or 0)

    async def online_stats(self, db: AsyncSession) -> Dict[str, Any]:
        """在线统计"""
        since = datetime.now() - timedelta(seconds=ONLINE_WINDOW_SECONDS)

        active_sessions = await db.scalar(
            select(func.count()).select_from(UserSession).where(UserSession.is_active.is_(True))
        )
        recent_sessions = await db.scalar(
            select(func.count())
            .select_from(UserSession)
            .where(UserSession.is_active.is_(True), UserSession.last_activity >= since)
        )
        unique_users = await db.scalar(
            select(func.count(func.distinct(UserSession.user_id))).where(
                UserSession.is_active.is_(True)
            )
        )

        return {
            "active_sessions": int(active_sessions or 0),
            "recent_sessions": int(recent_sessions or 0),
            "unique_users": int(unique_users or 0),
            "window_seconds": ONLINE_WINDOW_SECONDS,
        }

    async def kick(self, db: AsyncSession, session_id: int) -> bool:
        """强制下线：以 DB 标记为准，Redis 侧尽力清理

        Redis 的 session_id 与 `user_sessions.id` 语义不同（前者是字符串会话标识），
        所以清理失败只记警告、不影响“已下线”的结论。
        """
        row = (
            await db.execute(select(UserSession).where(UserSession.id == session_id))
        ).scalar_one_or_none()
        if row is None:
            return False

        row.is_active = False
        await db.commit()

        try:
            await session_management_service.revoke_session(row.user_id, str(row.id))
        except Exception as exc:  # noqa: BLE001 - Redis 侧失败不应回滚 DB 标记
            logger.warning("清理 Redis 会话失败（DB 已标记下线）：%s", exc)

        return True


monitor_service = MonitorService()
