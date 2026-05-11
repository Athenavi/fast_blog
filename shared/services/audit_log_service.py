"""
审计日志服务
记录系统中的关键操作和事件，用于安全审计和合规性检查
"""
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from enum import Enum

from sqlalchemy import Column, Integer, String, DateTime, Text, Index
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.future import select

logger = logging.getLogger(__name__)

Base = declarative_base()


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


class AuditLogModel(Base):
    """审计日志数据库模型"""
    __tablename__ = 'audit_logs'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=True, index=True)
    user_name = Column(String(255), nullable=True)
    action = Column(String(50), nullable=False, index=True)
    level = Column(String(20), nullable=False, index=True)
    resource_type = Column(String(100), nullable=True, index=True)
    resource_id = Column(String(100), nullable=True, index=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    details = Column(Text, nullable=True)  # JSON格式的详细信息
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # 创建索引以提高查询性能
    __table_args__ = (
        Index('idx_audit_logs_user_action_time', 'user_id', 'action', 'created_at'),
        Index('idx_audit_logs_level_time', 'level', 'created_at'),
        Index('idx_audit_logs_resource', 'resource_type', 'resource_id'),
    )


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
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

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
            user_agent: Optional[str] = None
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
        """
        if not self.enabled:
            return

        try:
            # 创建审计日志记录
            audit_log = AuditLogModel(
                user_id=user_id,
                user_name=user_name,
                action=action.value,
                level=level.value,
                resource_type=resource_type,
                resource_id=resource_id,
                ip_address=ip_address,
                user_agent=user_agent,
                description=description,
                details=json.dumps(details, ensure_ascii=False) if details else None,
                created_at=datetime.utcnow()
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
            query = select(AuditLogModel).order_by(AuditLogModel.created_at.desc())

            # 应用过滤条件
            if user_id:
                query = query.where(AuditLogModel.user_id == user_id)

            if action:
                query = query.where(AuditLogModel.action == action.value)

            if level:
                query = query.where(AuditLogModel.level == level.value)

            if resource_type:
                query = query.where(AuditLogModel.resource_type == resource_type)

            if resource_id:
                query = query.where(AuditLogModel.resource_id == resource_id)

            if ip_address:
                query = query.where(AuditLogModel.ip_address == ip_address)

            if start_date:
                query = query.where(AuditLogModel.created_at >= start_date)

            if end_date:
                query = query.where(AuditLogModel.created_at <= end_date)

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
                        'details': json.loads(log.details) if log.details else None,
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
        all_logs_query = select(AuditLogModel).order_by(AuditLogModel.created_at.desc())

        # 应用过滤条件
        if filters.get('user_id'):
            all_logs_query = all_logs_query.where(AuditLogModel.user_id == filters['user_id'])
        if filters.get('action'):
            all_logs_query = all_logs_query.where(AuditLogModel.action == filters['action'].value)
        if filters.get('level'):
            all_logs_query = all_logs_query.where(AuditLogModel.level == filters['level'].value)
        if filters.get('resource_type'):
            all_logs_query = all_logs_query.where(AuditLogModel.resource_type == filters['resource_type'])
        if filters.get('resource_id'):
            all_logs_query = all_logs_query.where(AuditLogModel.resource_id == filters['resource_id'])
        if filters.get('ip_address'):
            all_logs_query = all_logs_query.where(AuditLogModel.ip_address == filters['ip_address'])
        if filters.get('start_date'):
            all_logs_query = all_logs_query.where(AuditLogModel.created_at >= filters['start_date'])
        if filters.get('end_date'):
            all_logs_query = all_logs_query.where(AuditLogModel.created_at <= filters['end_date'])

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
                    'details': json.loads(log.details) if log.details else None,
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
                    log.details,
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
        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)

        try:
            from sqlalchemy import delete

            stmt = delete(AuditLogModel).where(AuditLogModel.created_at < cutoff_date)
            result = await db.execute(stmt)
            await db.commit()

            logger.info(f"Cleaned up {result.rowcount} old audit logs")

        except Exception as e:
            logger.error(f"Failed to clean up old audit logs: {e}")
            await db.rollback()


# 全局实例
from sqlalchemy.sql.functions import func
from datetime import timedelta

audit_log_service = AuditLogService()
