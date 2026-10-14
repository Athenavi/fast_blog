"""
审计日志服务
记录系统中的关键操作和事件，用于安全审计和合规性检查
"""
import json
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, Any, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.sql.functions import func

from shared.models.system.audit_log import AuditLog
from shared.logging import default_logger as logger
from shared.utils import audit_chain

#: 审计哈希链串行化用的 advisory lock 键（全实例共用一个固定值）。
#: 事务结束时由 PostgreSQL 自动释放，不需要显式解锁。
_AUDIT_CHAIN_LOCK_KEY = 918273645


class AuditLogAction(Enum):
    """审计操作类型"""
    LOGIN = "login"
    LOGOUT = "logout"
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    VIEW = "view"
    EXPORT = "export"
    IMPORT = "import"
    CONFIG_CHANGE = "config_change"
    PERMISSION_CHANGE = "permission_change"
    SECURITY_EVENT = "security_event"


class AuditLogLevel(Enum):
    """审计日志级别"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"





class AuditLogService:
    """
    审计日志服务

    功能:
    1. 操作日志记录
    2. 登录日志记录
    3. 数据变更追踪
    4. 日志查询和过滤
    5. 日志导出
    """

    def __init__(self):
        self.enabled = True
        self.retention_days = 90  # 默认保留90天日志

    async def initialize(self, db: AsyncSession):
        """
        初始化审计日志服务

        Args:
            db: 数据库会话
        """
        # 确保表已创建

        # 注意：在实际应用中，表创建可能在数据库初始化时完成
        pass

    async def log_action(
            self,
            db: AsyncSession,
            user_id: Optional[int],
            user_name: Optional[str],
            action: AuditLogAction,
            resource_type: Optional[str] = None,
            resource_id: Optional[str] = None,
            description: Optional[str] = None,
            details: Optional[Dict[str, Any]] = None,
            level: AuditLogLevel = AuditLogLevel.INFO,
            ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        before: Optional[Dict[str, Any]] = None,
        after: Optional[Dict[str, Any]] = None,
    ):
        """
        记录审计日志

        Args:
            db: 数据库会话
            user_id: 用户ID
            user_name: 用户名
            action: 操作类型
            resource_type: 资源类型
            resource_id: 资源ID
            description: 操作描述
            details: 详细信息
            level: 日志级别
            ip_address: IP地址
            user_agent: 用户代理
            before: 变更前值快照（脱敏后写入 ``before_data``）
            after: 变更后值快照（脱敏后写入 ``after_data``；未提供时回落到 ``details``）
        """
        if not self.enabled:
            return

        try:
            created_at = datetime.now()
            resolved_resource_id = (
                int(resource_id)
                if resource_id is not None and str(resource_id).isdigit()
                else (resource_id if resource_id else None)
            )
            # 快照一律脱敏后再落库（请求体里常带 password / token）
            before_data = audit_chain.dump_snapshot(before)
            after_data = audit_chain.dump_snapshot(after) or audit_chain.dump_snapshot(details)
            request_data = json.dumps(details, ensure_ascii=False) if details else None

            # 哈希链：本条的 prev_hash 取上一条的 entry_hash。
            #
            # 并发保护分两层：
            #   1) 先取一把**事务级 advisory lock** —— 这是关键。只靠下面的
            #      ``with_for_update()`` 不够：当"还没有任何带 entry_hash 的行"时，
            #      SELECT 匹配不到行就**不会加锁**，于是并发的两个事务都会读到
            #      prev_hash=None，各自算出不同摘要指向同一个前驱 —— 链从此分叉，
            #      verify_chain 会把正常的并发写入误报成"被篡改"。
            #   2) 再行锁住那条记录，保证读取与写入之间没有别人插队。
            await db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": _AUDIT_CHAIN_LOCK_KEY})
            prev_hash = (
                await db.execute(
                    select(AuditLog.entry_hash)
                    .where(AuditLog.entry_hash.is_not(None))
                    .order_by(AuditLog.id.desc())
                    .limit(1)
                    .with_for_update()
                )
            ).scalar()

            entry_hash = audit_chain.compute_entry_hash(
                prev_hash,
                user_id=user_id,
                user_name=user_name,
                action=action.value,
                level=level.value,
                resource_type=resource_type,
                resource_id=resolved_resource_id,
                description=description,
                ip_address=ip_address,
                before_data=before_data,
                after_data=after_data,
                created_at=created_at,
            )

            # 创建审计日志记录
            audit_log = AuditLog(
                user_id=user_id,
                user_name=user_name,
                action=action.value,
                level=level.value,
                resource_type=resource_type,
                resource_id=resolved_resource_id,
                ip_address=ip_address,
                user_agent=user_agent,
                description=description,
                request_data=request_data,
                before_data=before_data,
                after_data=after_data,
                prev_hash=prev_hash,
                entry_hash=entry_hash,
                created_at=created_at
            )

            # 添加到数据库
            db.add(audit_log)
            await db.commit()

            logger.info(f"Audit log recorded: {action.value} by {user_name or user_id}")

        except Exception as e:
            logger.error(f"Failed to record audit log: {e}")
            # 即使记录失败也不影响主业务流程
            await db.rollback()

    async def get_logs(
            self,
            db: AsyncSession,
            user_id: Optional[int] = None,
            action: Optional[AuditLogAction] = None,
            level: Optional[AuditLogLevel] = None,
            resource_type: Optional[str] = None,
            resource_id: Optional[str] = None,
            ip_address: Optional[str] = None,
            start_date: Optional[datetime] = None,
            end_date: Optional[datetime] = None,
            page: int = 1,
            per_page: int = 50
    ) -> Dict[str, Any]:
        """
        查询审计日志

        Args:
            db: 数据库会话
            user_id: 用户ID过滤
            action: 操作类型过滤
            level: 日志级别过滤
            resource_type: 资源类型过滤
            resource_id: 资源ID过滤
            ip_address: IP地址过滤
            start_date: 开始日期
            end_date: 结束日期
            page: 页码
            per_page: 每页数量

        Returns:
            日志列表和分页信息
        """
        try:
            query = select(AuditLog).order_by(AuditLog.created_at.desc())

            # 应用过滤条件
            if user_id:
                query = query.where(AuditLog.user_id == user_id)

            if action:
                query = query.where(AuditLog.action == action.value)

            if level:
                query = query.where(AuditLog.level == level.value)

            if resource_type:
                query = query.where(AuditLog.resource_type == resource_type)

            if resource_id:
                query = query.where(AuditLog.resource_id == resource_id)

            if ip_address:
                query = query.where(AuditLog.ip_address == ip_address)

            if start_date:
                query = query.where(AuditLog.created_at >= start_date)

            if end_date:
                query = query.where(AuditLog.created_at <= end_date)

            # 计算总数
            count_query = select(func.count()).select_from(query.subquery())
            total = await db.execute(count_query)
            total_count = total.scalar()

            # 应用分页
            offset = (page - 1) * per_page
            query = query.offset(offset).limit(per_page)

            result = await db.execute(query)
            logs = result.scalars().all()

            return {
                'logs': [
                    {
                        'id': log.id,
                        'user_id': log.user_id,
                        'user_name': log.user_name,
                        'action': log.action,
                        'level': log.level,
                        'resource_type': log.resource_type,
                        'resource_id': log.resource_id,
                        'ip_address': log.ip_address,
                        'user_agent': log.user_agent,
                        'description': log.description,
                        'details': json.loads(log.request_data) if log.request_data else None,
                        'before_data': json.loads(log.before_data) if log.before_data else None,
                        'after_data': json.loads(log.after_data) if log.after_data else None,
                        'entry_hash': log.entry_hash,
                        'created_at': log.created_at.isoformat()
                    }
                    for log in logs
                ],
                'pagination': {
                    'current_page': page,
                    'per_page': per_page,
                    'total': total_count,
                    'total_pages': (total_count + per_page - 1) // per_page
                }
            }

        except Exception as e:
            logger.error(f"Failed to query audit logs: {e}")
            raise

    async def export_logs(
            self,
            db: AsyncSession,
            output_format: str = 'json',
            **filters
    ) -> str:
        """
        导出审计日志

        Args:
            db: 数据库会话
            output_format: 输出格式 ('json', 'csv', 'excel')
            **filters: 过滤条件

        Returns:
            导出的数据
        """
        # 获取所有符合条件的日志（不分页）
        all_logs_query = select(AuditLog).order_by(AuditLog.created_at.desc())

        # 应用过滤条件
        if filters.get('user_id'):
            all_logs_query = all_logs_query.where(AuditLog.user_id == filters['user_id'])
        if filters.get('action'):
            all_logs_query = all_logs_query.where(AuditLog.action == filters['action'].value)
        if filters.get('level'):
            all_logs_query = all_logs_query.where(AuditLog.level == filters['level'].value)
        if filters.get('resource_type'):
            all_logs_query = all_logs_query.where(AuditLog.resource_type == filters['resource_type'])
        if filters.get('resource_id'):
            all_logs_query = all_logs_query.where(AuditLog.resource_id == filters['resource_id'])
        if filters.get('ip_address'):
            all_logs_query = all_logs_query.where(AuditLog.ip_address == filters['ip_address'])
        if filters.get('start_date'):
            all_logs_query = all_logs_query.where(AuditLog.created_at >= filters['start_date'])
        if filters.get('end_date'):
            all_logs_query = all_logs_query.where(AuditLog.created_at <= filters['end_date'])

        result = await db.execute(all_logs_query)
        logs = result.scalars().all()

        if output_format.lower() == 'json':
            import json as json_module
            logs_data = [
                {
                    'id': log.id,
                    'user_id': log.user_id,
                    'user_name': log.user_name,
                    'action': log.action,
                    'level': log.level,
                    'resource_type': log.resource_type,
                    'resource_id': log.resource_id,
                    'ip_address': log.ip_address,
                    'user_agent': log.user_agent,
                    'description': log.description,
                    'details': json.loads(log.request_data) if log.request_data else None,
                    'created_at': log.created_at.isoformat()
                }
                for log in logs
            ]
            return json_module.dumps(logs_data, ensure_ascii=False, indent=2)

        elif output_format.lower() == 'csv':
            import io
            import csv

            output = io.StringIO()
            writer = csv.writer(output)

            # 写入CSV头部
            writer.writerow([
                'ID', 'User ID', 'User Name', 'Action', 'Level', 'Resource Type',
                'Resource ID', 'IP Address', 'User Agent', 'Description', 'Details', 'Created At'
            ])

            # 写入数据行
            for log in logs:
                writer.writerow([
                    log.id,
                    log.user_id,
                    log.user_name,
                    log.action,
                    log.level,
                    log.resource_type,
                    log.resource_id,
                    log.ip_address,
                    log.user_agent,
                    log.description,
                    log.request_data,
                    log.created_at.isoformat()
                ])

            return output.getvalue()

        else:
            raise ValueError(f"Unsupported export format: {output_format}")

    async def cleanup_old_logs(self, db: AsyncSession, days: int = None):
        """
        清理旧的审计日志

        Args:
            db: 数据库会话
            days: 保留天数，默认使用实例配置
        """
        retention_days = days or self.retention_days
        cutoff_date = datetime.now() - timedelta(days=retention_days)

        try:
            from sqlalchemy import delete

            stmt = delete(AuditLog).where(AuditLog.created_at < cutoff_date)
            result = await db.execute(stmt)
            await db.commit()

            logger.info(f"Cleaned up {result.rowcount} old audit logs")

        except Exception as e:
            logger.error(f"Failed to clean up old audit logs: {e}")
            await db.rollback()

    async def verify_chain(self, db: AsyncSession, limit: Optional[int] = None) -> Dict[str, Any]:
        """校验审计日志的哈希链，返回第一个断点

        起点是**现存最早**的、``entry_hash`` 非空的记录：更早的记录可能已被保留策略
        清理，其 ``prev_hash`` 指向的行确实不存在，不算断裂。从第二条起要求
        ``prev_hash == 上一条的 entry_hash``，并逐条重算摘要比对内容。
        """
        query = (
            select(AuditLog)
            .where(AuditLog.entry_hash.is_not(None))
            .order_by(AuditLog.id.asc())
        )
        if limit:
            query = query.limit(limit)
        rows = (await db.execute(query)).scalars().all()

        if not rows:
            return {'valid': True, 'checked': 0, 'reason': '尚无启用哈希链的审计记录'}

        expected_prev = rows[0].prev_hash
        for index, row in enumerate(rows, start=1):
            if row.prev_hash != expected_prev:
                return {
                    'valid': False,
                    'checked': index,
                    'broken_at_id': row.id,
                    'reason': 'prev_hash 与上一条记录的 entry_hash 不一致（记录被删除或插入）',
                }
            recomputed = audit_chain.compute_entry_hash(
                row.prev_hash,
                user_id=row.user_id,
                user_name=row.user_name,
                action=row.action,
                level=row.level,
                resource_type=row.resource_type,
                resource_id=row.resource_id,
                description=row.description,
                ip_address=row.ip_address,
                before_data=row.before_data,
                after_data=row.after_data,
                created_at=row.created_at,
            )
            if recomputed != row.entry_hash:
                return {
                    'valid': False,
                    'checked': index,
                    'broken_at_id': row.id,
                    'reason': 'entry_hash 与记录内容不匹配（该行内容被修改过）',
                }
            expected_prev = row.entry_hash

        return {'valid': True, 'checked': len(rows)}


# 全局实例
audit_log_service = AuditLogService()
