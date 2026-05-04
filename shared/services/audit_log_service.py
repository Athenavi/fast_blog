"""
审计日志服务

记录所有管理操作，包括CRUD操作、用户登录、配置更改等
支持日志搜索和导出功能
"""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.user_activity import UserActivity


class AuditLogService:
    """审计日志服务"""

    # 活动类型常量
    ACTIVITY_TYPES = {
        'LOGIN': '用户登录',
        'LOGOUT': '用户登出',
        'CREATE': '创建资源',
        'UPDATE': '更新资源',
        'DELETE': '删除资源',
        'CONFIG_CHANGE': '配置更改',
        'PLUGIN_ACTIVATE': '激活插件',
        'PLUGIN_DEACTIVATE': '停用插件',
        'THEME_CHANGE': '更换主题',
        'USER_CREATE': '创建用户',
        'USER_UPDATE': '更新用户',
        'USER_DELETE': '删除用户',
        'ARTICLE_CREATE': '创建文章',
        'ARTICLE_UPDATE': '更新文章',
        'ARTICLE_DELETE': '删除文章',
        'ARTICLE_PUBLISH': '发布文章',
        'CATEGORY_CREATE': '创建分类',
        'CATEGORY_UPDATE': '更新分类',
        'CATEGORY_DELETE': '删除分类',
    }

    # 目标类型常量
    TARGET_TYPES = {
        'user': '用户',
        'article': '文章',
        'category': '分类',
        'tag': '标签',
        'media': '媒体',
        'page': '页面',
        'comment': '评论',
        'plugin': '插件',
        'theme': '主题',
        'setting': '设置',
        'menu': '菜单',
        'widget': '小部件',
    }

    def __init__(self, db: AsyncSession):
        self.db = db

    async def log_activity(
            self,
            user_id: int,
            activity_type: str,
            target_type: Optional[str] = None,
            target_id: Optional[int] = None,
            details: Optional[Dict[str, Any]] = None,
            ip_address: Optional[str] = None,
            user_agent: Optional[str] = None,
    ) -> UserActivity:
        """
        记录用户活动
        
        Args:
            user_id: 用户ID
            activity_type: 活动类型
            target_type: 目标类型
            target_id: 目标ID
            details: 活动详情（字典）
            ip_address: IP地址
            user_agent: 用户代理
        
        Returns:
            创建的活动记录
        """
        # 序列化详情
        details_json = json.dumps(details, ensure_ascii=False, default=str) if details else None

        activity = UserActivity(
            user=user_id,
            activity_type=activity_type,
            target_type=target_type,
            target_id=target_id,
            details=details_json,
            ip_address=ip_address,
            user_agent=user_agent,
            created_at=datetime.utcnow(),
        )

        self.db.add(activity)
        await self.db.flush()

        return activity

    async def get_activities(
            self,
            page: int = 1,
            per_page: int = 20,
            user_id: Optional[int] = None,
            activity_type: Optional[str] = None,
            target_type: Optional[str] = None,
            start_date: Optional[datetime] = None,
            end_date: Optional[datetime] = None,
            search_keyword: Optional[str] = None,
    ) -> tuple[List[UserActivity], int]:
        """
        获取活动日志列表
        
        Args:
            page: 页码
            per_page: 每页数量
            user_id: 用户ID过滤
            activity_type: 活动类型过滤
            target_type: 目标类型过滤
            start_date: 开始日期
            end_date: 结束日期
            search_keyword: 搜索关键词
        
        Returns:
            (活动列表, 总数) 元组
        """
        query = select(UserActivity)

        # 应用过滤条件
        if user_id:
            query = query.where(UserActivity.user == user_id)

        if activity_type:
            query = query.where(UserActivity.activity_type == activity_type)

        if target_type:
            query = query.where(UserActivity.target_type == target_type)

        if start_date:
            query = query.where(UserActivity.created_at >= start_date)

        if end_date:
            query = query.where(UserActivity.created_at <= end_date)

        if search_keyword:
            # 在详情中搜索
            query = query.where(UserActivity.details.contains(search_keyword))

        # 获取总数
        count_query = select(UserActivity).select_from(UserActivity)
        if user_id:
            count_query = count_query.where(UserActivity.user == user_id)
        if activity_type:
            count_query = count_query.where(UserActivity.activity_type == activity_type)
        if target_type:
            count_query = count_query.where(UserActivity.target_type == target_type)
        if start_date:
            count_query = count_query.where(UserActivity.created_at >= start_date)
        if end_date:
            count_query = count_query.where(UserActivity.created_at <= end_date)
        if search_keyword:
            count_query = count_query.where(UserActivity.details.contains(search_keyword))

        total_result = await self.db.execute(
            select(UserActivity).select_from(count_query.subquery()).with_only_columns(UserActivity.id.count()))
        total = total_result.scalar() or 0

        # 分页和排序
        offset = (page - 1) * per_page
        query = query.order_by(desc(UserActivity.created_at)).offset(offset).limit(per_page)

        result = await self.db.execute(query)
        activities = result.scalars().all()

        return list(activities), total

    async def get_activity_detail(self, activity_id: int) -> Optional[UserActivity]:
        """
        获取活动详情
        
        Args:
            activity_id: 活动ID
        
        Returns:
            活动记录或None
        """
        query = select(UserActivity).where(UserActivity.id == activity_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def delete_old_activities(self, days: int = 90) -> int:
        """
        删除旧的活动记录
        
        Args:
            days: 保留天数
        
        Returns:
            删除的记录数
        """
        from datetime import timedelta

        cutoff_date = datetime.utcnow() - timedelta(days=days)

        # 先统计要删除的数量
        count_query = select(UserActivity).where(UserActivity.created_at < cutoff_date)
        count_result = await self.db.execute(count_query)
        activities_to_delete = count_result.scalars().all()
        deleted_count = len(activities_to_delete)

        # 执行删除
        from sqlalchemy import delete
        delete_stmt = delete(UserActivity).where(UserActivity.created_at < cutoff_date)
        await self.db.execute(delete_stmt)

        return deleted_count

    def format_activity_for_display(self, activity: UserActivity) -> Dict[str, Any]:
        """
        格式化活动记录用于显示
        
        Args:
            activity: 活动记录
        
        Returns:
            格式化的字典
        """
        # 解析详情
        details = {}
        if activity.details:
            try:
                details = json.loads(activity.details)
            except json.JSONDecodeError:
                details = {'raw': activity.details}

        return {
            'id': activity.id,
            'user_id': activity.user,
            'activity_type': activity.activity_type,
            'activity_type_label': self.ACTIVITY_TYPES.get(activity.activity_type, activity.activity_type),
            'target_type': activity.target_type,
            'target_type_label': self.TARGET_TYPES.get(activity.target_type,
                                                       activity.target_type) if activity.target_type else None,
            'target_id': activity.target_id,
            'details': details,
            'ip_address': activity.ip_address,
            'user_agent': activity.user_agent,
            'created_at': activity.created_at.isoformat() if activity.created_at else None,
        }


# 导出
__all__ = ['AuditLogService']
