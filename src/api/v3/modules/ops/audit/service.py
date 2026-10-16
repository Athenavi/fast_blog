"""审计日志导出（真实文件下载）。

数据源：``permission_audit_logs``（写操作审计：谁、何时、对什么资源、做了什么）。

设计要点：

  - **产出真实文件**（CSV 带 UTF-8 BOM，Excel 直接识别中文；或 JSON），
    不是把字符串塞进 JSON 响应体 —— 与项目既有的导出端点口径一致；
  - 时间区间与条数上限都由参数控制，避免一次导出把库拖垮；
  - 字段**显式列举**，新增模型字段不会"顺带"泄露出去。
"""

import csv
import io
import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models import PermissionAuditLog  # 走 __init__ 懒加载，确保模型完整注册
from src.api.v3.core.logger import get_logger

logger = get_logger("ops.audit.export")

#: 导出列（顺序即 CSV 列序）
COLUMNS: Tuple[str, ...] = (
    "id",
    "created_at",
    "user_id",
    "action",
    "resource_type",
    "resource_id",
    "ip_address",
    "details",
)

#: 单次导出的硬上限（管理端点另有更小的默认值）
MAX_ROWS = 50_000


class AuditExportService:
    """审计日志导出（只读）"""

    async def fetch(
        self,
        db: AsyncSession,
        *,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        limit: int = 5000,
    ) -> List[Dict[str, Any]]:
        """按时间区间取审计记录（升序，便于人工比对）"""
        stmt = select(PermissionAuditLog)
        if date_from is not None:
            stmt = stmt.where(PermissionAuditLog.created_at >= date_from)
        if date_to is not None:
            stmt = stmt.where(PermissionAuditLog.created_at <= date_to)
        stmt = stmt.order_by(PermissionAuditLog.id.asc()).limit(min(int(limit), MAX_ROWS))

        rows = (await db.execute(stmt)).scalars().all()
        return [self._row_to_dict(row) for row in rows]

    @staticmethod
    def _row_to_dict(row: Any) -> Dict[str, Any]:
        data = {}
        for column in COLUMNS:
            value = getattr(row, column, None)
            if isinstance(value, datetime):
                value = value.isoformat()
            data[column] = value
        return data

    def to_csv(self, rows: Sequence[Dict[str, Any]]) -> bytes:
        """CSV（UTF-8 **带 BOM**，Excel 打开中文不乱码）"""
        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=list(COLUMNS), extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: ("" if row.get(key) is None else row.get(key)) for key in COLUMNS})
        return b"\xef\xbb\xbf" + buffer.getvalue().encode("utf-8")

    def to_json(self, rows: Sequence[Dict[str, Any]]) -> bytes:
        return json.dumps(rows, ensure_ascii=False, indent=2).encode("utf-8")

    async def export(
        self,
        db: AsyncSession,
        *,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        fmt: str = "csv",
        limit: int = 5000,
    ) -> Tuple[bytes, str, str]:
        """返回 ``(内容, media_type, filename)``，供 controller 直接作为附件返回。"""
        rows = await self.fetch(db, date_from=date_from, date_to=date_to, limit=limit)
        stamp = datetime.now().strftime("%Y%m%d%H%M%S")

        if fmt == "json":
            return self.to_json(rows), "application/json; charset=utf-8", f"audit-{stamp}.json"
        content = self.to_csv(rows)
        logger.info("导出审计日志 %d 条（%s）", len(rows), fmt)
        return content, "text/csv; charset=utf-8", f"audit-{stamp}.csv"


audit_export_service = AuditExportService()
