"""
数据保留策略服务模块
提供数据保留策略的 CRUD 操作以及批量过期数据清理功能。
"""
from datetime import datetime, timedelta
from typing import Optional, List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import delete as sa_delete

from shared.models.enterprise.data_retention_policy import DataRetentionPolicy
from src.unified_logger import default_logger as logger


class DataRetentionService:
    """
    数据保留策略服务

    功能：
    1. 获取/设置/列出/删除保留策略
    2. 按策略执行数据清理（删除过期记录）
    3. 批量执行所有类别的保留策略
    """

    async def get_policy(self, db: AsyncSession, category: str) -> Optional[DataRetentionPolicy]:
        """
        获取某类数据的保留策略

        Args:
            db: 数据库会话
            category: 数据类别

        Returns:
            保留策略对象，不存在则返回 None
        """
        stmt = select(DataRetentionPolicy).where(
            DataRetentionPolicy.data_category == category,
            DataRetentionPolicy.is_active == True
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def set_policy(
            self,
            db: AsyncSession,
            category: str,
            days: int,
            action: str = 'delete'
    ) -> DataRetentionPolicy:
        """
        设置/更新保留策略

        Args:
            db: 数据库会话
            category: 数据类别
            days: 保留天数
            action: 到期动作 (delete/archive)

        Returns:
            创建或更新后的策略对象
        """
        now = datetime.now()

        # 检查是否已有策略
        existing = await self.get_policy(db, category)
        if existing:
            existing.retention_days = days
            existing.action = action
            existing.updated_at = now
            policy = existing
        else:
            policy = DataRetentionPolicy(
                data_category=category,
                retention_days=days,
                action=action,
                is_active=True,
                created_at=now,
                updated_at=now
            )
            db.add(policy)

        await db.commit()
        await db.refresh(policy)

        logger.info(f"Data retention policy set: category={category}, days={days}, action={action}")
        return policy

    async def list_policies(self, db: AsyncSession) -> List[DataRetentionPolicy]:
        """
        列出所有策略

        Args:
            db: 数据库会话

        Returns:
            策略列表
        """
        stmt = select(DataRetentionPolicy).order_by(DataRetentionPolicy.data_category)
        result = await db.execute(stmt)
        return result.scalars().all()

    async def delete_policy(self, db: AsyncSession, policy_id: int) -> bool:
        """
        删除策略

        Args:
            db: 数据库会话
            policy_id: 策略 ID

        Returns:
            是否成功删除
        """
        stmt = select(DataRetentionPolicy).where(DataRetentionPolicy.id == policy_id)
        result = await db.execute(stmt)
        policy = result.scalar_one_or_none()

        if not policy:
            logger.warning(f"Data retention policy not found: id={policy_id}")
            return False

        await db.delete(policy)
        await db.commit()

        logger.info(f"Data retention policy deleted: id={policy_id}, category={policy.data_category}")
        return True

    async def apply_retention(self, db: AsyncSession, category: str, model_cls=None) -> int:
        """
        对某类数据执行保留策略（删除过期记录）

        根据策略中设定的保留天数，删除该类别下 early 于截止日期的记录。

        Args:
            db: 数据库会话
            category: 数据类别
            model_cls: 可选，数据对应的 SQLAlchemy 模型类。如果未提供，则通过
                       _resolve_model_for_category 自动解析。

        Returns:
            清理的记录数量
        """
        policy = await self.get_policy(db, category)
        if not policy:
            logger.info(f"No active retention policy for category: {category}")
            return 0

        if model_cls is None:
            model_cls = await self._resolve_model_for_category(category)
            if model_cls is None:
                logger.warning(f"Cannot resolve model for category: {category}, skipping")
                return 0

        cutoff_date = datetime.now() - timedelta(days=policy.retention_days)
        delete_stmt = sa_delete(model_cls).where(model_cls.created_at < cutoff_date)

        result = await db.execute(delete_stmt)
        await db.commit()

        deleted_count = result.rowcount
        logger.info(
            f"Retention applied: category={category}, "
            f"cutoff={cutoff_date.isoformat()}, deleted={deleted_count}"
        )
        return deleted_count

    async def apply_all(self, db: AsyncSession, model_map: dict = None) -> dict:
        """
        对所有数据类别执行保留策略

        Args:
            db: 数据库会话
            model_map: 可选，类别名称到模型类的映射字典。未提供的类别将自动解析。

        Returns:
            字典，key 为类别名称，value 为清理记录数
        """
        policies = await self.list_policies(db)
        results = {}

        for policy in policies:
            if not policy.is_active:
                continue
            model_cls = None
            if model_map:
                model_cls = model_map.get(policy.data_category)
            count = await self.apply_retention(db, policy.data_category, model_cls=model_cls)
            results[policy.data_category] = count

        logger.info(f"Retention applied for all categories: {results}")
        return results

    async def _resolve_model_for_category(self, category: str):
        """
        根据类别名称自动解析对应的 SQLAlchemy 模型类。

        默认实现将 data_category 转换为模型名（snake_case 转 PascalCase），
        然后从 shared.models 中尝试导入。

        Args:
            category: 数据类别名称

        Returns:
            模型类，如果无法解析则返回 None
        """
        import importlib
        try:
            module = importlib.import_module('shared.models')
            # 蛇形命名转驼峰命名：audit_log -> AuditLog
            parts = category.split('_')
            model_name = ''.join(p.capitalize() for p in parts)
            return getattr(module, model_name, None)
        except (ImportError, AttributeError):
            return None


# 全局实例
data_retention_service = DataRetentionService()
