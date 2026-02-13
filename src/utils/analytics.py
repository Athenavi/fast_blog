"""
访问统计和用户行为分析工具模块
实现页面访问统计、用户行为跟踪和数据分析功能
"""

from datetime import datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from src.models.misc import PageView, UserActivity
from src.models.user import User


def record_page_view(db: Session, user_id=None, page_url=None, page_title=None, referrer=None, session_id=None, user_agent='', ip_address=''):
    """
    记录页面访问
    
    :param db: 数据库会话
    :param user_id: 用户ID，可选
    :param page_url: 页面URL
    :param page_title: 页面标题
    :param referrer: 来源页面
    :param session_id: 会话ID
    :param user_agent: 用户代理字符串
    :param ip_address: IP地址
    """
    try:
        # 创建页面访问记录
        page_view = PageView(
            user_id=user_id,
            session_id=session_id,
            page_url=page_url,
            page_title=page_title,
            referrer=referrer,
            user_agent=user_agent,
            ip_address=ip_address
        )
        
        db.add(page_view)
        db.commit()
        db.refresh(page_view)
        
        return page_view
    except Exception as e:
        # 记录错误但不中断请求处理
        print(f"记录页面访问时出错: {str(e)}")
        db.rollback()
        return None


def record_user_activity(db: Session, user_id, activity_type, target_type, target_id, details=None, ip_address='', user_agent=''):
    """
    记录用户活动
    
    :param db: 数据库会话
    :param user_id: 用户ID
    :param activity_type: 活动类型 (e.g., 'view', 'like', 'comment', 'share')
    :param target_type: 目标类型 (e.g., 'article', 'comment')
    :param target_id: 目标ID
    :param details: 活动详细信息
    :param ip_address: IP地址
    :param user_agent: 用户代理字符串
    """
    try:
        activity = UserActivity(
            user_id=user_id,
            activity_type=activity_type,
            target_type=target_type,
            target_id=target_id,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        db.add(activity)
        db.commit()
        db.refresh(activity)
        
        return activity
    except Exception as e:
        print(f"记录用户活动时出错: {str(e)}")
        db.rollback()
        return None


def get_client_ip(request):
    """
    获取客户端IP地址
    """
    if not request:
        return None
    
    # 优先获取真实的客户端IP地址
    headers = getattr(request, 'headers', {})
    
    ip = (headers.get('X-Forwarded-For', '').split(',')[0].strip() or
          headers.get('X-Real-IP', '') or
          headers.get('X-Client-IP', '') or
          getattr(request, 'client', type('obj', (object,), {'host': '127.0.0.1'}))().host if hasattr(request, 'client') and request.client else '127.0.0.1' or  # FastAPI兼容
          '127.0.0.1')  # 默认值
    
    # 如果X-Forwarded-For包含多个IP，取第一个（最原始的客户端IP）
    if ip and ',' in ip:
        ip = ip.split(',')[0].strip()
    
    return ip


def parse_user_agent(user_agent):
    """
    解析用户代理字符串，提取设备类型、浏览器和平台信息
    """
    if not user_agent:
        return None, None, None
    
    user_agent_lower = user_agent.lower()
    
    # 设备类型检测
    device_type = 'desktop'
    if any(device in user_agent_lower for device in ['mobile', 'android', 'iphone', 'ipod', 'ipad']):
        device_type = 'mobile'
    elif any(device in user_agent_lower for device in ['tablet', 'ipad']):
        device_type = 'tablet'
    
    # 浏览器检测
    browser = 'Unknown'
    if 'chrome' in user_agent_lower and 'edge' not in user_agent_lower and 'opr' not in user_agent_lower:
        browser = 'Chrome'
    elif 'firefox' in user_agent_lower:
        browser = 'Firefox'
    elif 'safari' in user_agent_lower and 'chrome' not in user_agent_lower:
        browser = 'Safari'
    elif 'edge' in user_agent_lower:
        browser = 'Edge'
    elif 'opera' in user_agent_lower or 'opr' in user_agent_lower:
        browser = 'Opera'
    elif 'msie' in user_agent_lower or 'trident' in user_agent_lower:
        browser = 'Internet Explorer'
    
    # 平台检测
    platform = 'Unknown'
    if 'windows' in user_agent_lower:
        platform = 'Windows'
    elif 'mac' in user_agent_lower or 'darwin' in user_agent_lower:
        platform = 'macOS'
    elif 'linux' in user_agent_lower:
        platform = 'Linux'
    elif 'android' in user_agent_lower:
        platform = 'Android'
    elif 'iphone' in user_agent_lower or 'ipad' in user_agent_lower or 'ipod' in user_agent_lower:
        platform = 'iOS'
    
    return device_type, browser, platform


def get_page_views_stats(db: Session, start_date=None, end_date=None, page_url=None):
    """
    获取页面访问统计信息
    
    :param db: 数据库会话
    :param start_date: 开始日期
    :param end_date: 结束日期
    :param page_url: 特定页面URL
    :return: 统计信息字典
    """
    from sqlalchemy import select
    query = select(PageView)
    
    if start_date:
        query = query.filter(PageView.created_at >= start_date)
    if end_date:
        query = query.filter(PageView.created_at <= end_date)
    if page_url:
        query = query.filter(PageView.page_url == page_url)
    
    total_views = query.count()
    
    # 获取按日期分组的访问量
    from sqlalchemy import select
    daily_stats = select(
        func.date(PageView.created_at).label('date'),
        func.count(PageView.id).label('count')
    )
    
    if start_date:
        daily_stats = daily_stats.filter(PageView.created_at >= start_date)
    if end_date:
        daily_stats = daily_stats.filter(PageView.created_at <= end_date)
    if page_url:
        daily_stats = daily_stats.filter(PageView.page_url == page_url)
    
    daily_stats = daily_stats.group_by(func.date(PageView.created_at)).all()
    
    return {
        'total_views': total_views,
        'daily_stats': [{'date': str(row.date), 'count': row.count} for row in daily_stats]
    }


def get_user_activity_stats(db: Session, user_id, start_date=None, end_date=None):
    """
    获取用户活动统计信息
    
    :param db: 数据库会话
    :param user_id: 用户ID
    :param start_date: 开始日期
    :param end_date: 结束日期
    :return: 统计信息字典
    """
    from sqlalchemy import select
    query = select(UserActivity).where(UserActivity.user_id == user_id)
    
    if start_date:
        query = query.filter(UserActivity.created_at >= start_date)
    if end_date:
        query = query.filter(UserActivity.created_at <= end_date)
    
    activities = query.all()
    
    # 按活动类型统计
    activity_counts = {}
    for activity in activities:
        activity_type = activity.activity_type
        if activity_type in activity_counts:
            activity_counts[activity_type] += 1
        else:
            activity_counts[activity_type] = 1
    
    return {
        'total_activities': len(activities),
        'activity_counts': activity_counts,
        'activities': [activity.to_dict() if hasattr(activity, 'to_dict') else activity.__dict__ for activity in activities]
    }


def get_top_pages(db: Session, limit=10, start_date=None, end_date=None):
    """
    获取访问量最高的页面
    
    :param db: 数据库会话
    :param limit: 返回结果数量限制
    :param start_date: 开始日期
    :param end_date: 结束日期
    :return: 页面访问统计列表
    """
    from sqlalchemy import select
    query = select(
        PageView.page_url,
        PageView.page_title,
        func.count(PageView.id).label('view_count'),
        func.count(PageView.user_id.distinct()).label('unique_visitors')
    ).group_by(PageView.page_url, PageView.page_title)
    
    if start_date:
        query = query.filter(PageView.created_at >= start_date)
    if end_date:
        query = query.filter(PageView.created_at <= end_date)
    
    top_pages = query.order_by(func.count(PageView.id).desc()).limit(limit).all()
    
    return [{
        'page_url': page.page_url,
        'page_title': page.page_title,
        'view_count': page.view_count,
        'unique_visitors': page.unique_visitors
    } for page in top_pages]


def get_user_engagement_stats(db: Session, user_id):
    """
    获取用户参与度统计
    
    :param db: 数据库会话
    :param user_id: 用户ID
    :return: 参与度统计信息
    """
    from sqlalchemy import select
    user_query = select(User).where(User.id == user_id)
    user_result = db.execute(user_query)
    user = user_result.scalar_one_or_none()
    if not user:
        return None
    
    # 计算用户的各种活动
    from sqlalchemy import select
    total_activities_query = select(func.count(UserActivity.id)).where(UserActivity.user_id == user_id)
    total_activities_result = db.execute(total_activities_query)
    total_activities = total_activities_result.scalar()
    from sqlalchemy import select
    page_views_query = select(func.count(PageView.id)).where(PageView.user_id == user_id)
    page_views_result = db.execute(page_views_query)
    page_views = page_views_result.scalar()
    
    # 计算文章相关活动
    from sqlalchemy import select
    article_activities_query = select(func.count(UserActivity.id)).where(
        UserActivity.user_id == user_id,
        UserActivity.target_type == 'article'
    )
    article_activities_result = db.execute(article_activities_query)
    article_activities = article_activities_result.scalar()
    
    return {
        'user_id': user_id,
        'username': user.username,
        'total_activities': total_activities,
        'page_views': page_views,
        'article_activities': article_activities,
        'engagement_score': (total_activities + page_views + article_activities) / 3
    }


def analyze_user_behavior(db: Session, user_id, days=30):
    """
    分析用户行为模式
    
    :param db: 数据库会话
    :param user_id: 用户ID
    :param days: 分析的天数
    :return: 用户行为分析结果
    """
    start_date = datetime.now() - timedelta(days=days)
    
    # 获取用户活动
    from sqlalchemy import select
    user_activities_query = select(UserActivity).where(
        UserActivity.user_id == user_id,
        UserActivity.created_at >= start_date
    ).order_by(UserActivity.created_at.desc())
    user_activities_result = db.execute(user_activities_query)
    user_activities = user_activities_result.scalars().all()
    
    # 获取用户页面访问
    from sqlalchemy import select
    page_views_query = select(PageView).where(
        PageView.user_id == user_id,
        PageView.created_at >= start_date
    ).order_by(PageView.created_at.desc())
    page_views_result = db.execute(page_views_query)
    page_views = page_views_result.scalars().all()
    
    # 按活动类型统计
    activity_types = {}
    for activity in user_activities:
        activity_type = activity.activity_type
        activity_types[activity_type] = activity_types.get(activity_type, 0) + 1
    
    # 按时间分析活动模式
    hourly_activity = {}
    for activity in user_activities:
        hour = activity.created_at.hour
        hourly_activity[hour] = hourly_activity.get(hour, 0) + 1
    
    # 按天分析活动模式
    daily_activity = {}
    for activity in user_activities:
        day = activity.created_at.strftime('%Y-%m-%d')
        daily_activity[day] = daily_activity.get(day, 0) + 1
    
    # 获取最活跃的页面
    popular_pages = {}
    for view in page_views:
        page_url = view.page_url
        popular_pages[page_url] = popular_pages.get(page_url, 0) + 1
    
    # 获取最活跃的时间段
    most_active_hour = max(hourly_activity, key=hourly_activity.get) if hourly_activity else None
    most_active_day = max(daily_activity, key=daily_activity.get) if daily_activity else None
    
    return {
        'user_id': user_id,
        'analysis_period': f'Last {days} days',
        'total_activities': len(user_activities),
        'total_page_views': len(page_views),
        'activity_types': activity_types,
        'hourly_activity': hourly_activity,
        'daily_activity': daily_activity,
        'popular_pages': dict(sorted(popular_pages.items(), key=lambda item: item[1], reverse=True)[:10]),
        'most_active_hour': most_active_hour,
        'most_active_day': most_active_day,
        'activity_timeline': [
            {
                'date': activity.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'type': activity.activity_type,
                'target': f"{activity.target_type}:{activity.target_id}",
                'details': activity.details
            } for activity in user_activities[:20]  # 只返回最近20条活动
        ]
    }


def get_behavior_insights(db: Session):
    """
    获取系统用户行为洞察
    """
    def get_user_name(db, user_id):
        from sqlalchemy import select
        user_query = select(User).where(User.id == user_id)
        user_result = db.execute(user_query)
        user_obj = user_result.scalar_one_or_none()
        return user_obj.username if user_obj else 'Unknown'
    
    start_date = datetime.now() - timedelta(days=7)
    
    # 获取最活跃的用户
    from sqlalchemy import select
    active_users_query = select(
        UserActivity.user_id,
        func.count(UserActivity.id).label('activity_count')
    ).where(
        UserActivity.created_at >= start_date
    ).group_by(UserActivity.user_id).order_by(
        func.count(UserActivity.id).desc()
    ).limit(10)
    active_users_result = db.execute(active_users_query)
    active_users = active_users_result.all()
    
    # 获取最活跃的页面
    from sqlalchemy import select
    popular_pages_query = select(
        PageView.page_url,
        PageView.page_title,
        func.count(PageView.id).label('view_count')
    ).where(
        PageView.created_at >= start_date
    ).group_by(PageView.page_url, PageView.page_title).order_by(
        func.count(PageView.id).desc()
    ).limit(10)
    popular_pages_result = db.execute(popular_pages_query)
    popular_pages = popular_pages_result.all()
    
    # 获取最常见的活动类型
    from sqlalchemy import select
    common_activities_query = select(
        UserActivity.activity_type,
        func.count(UserActivity.id).label('count')
    ).where(
        UserActivity.created_at >= start_date
    ).group_by(UserActivity.activity_type).order_by(
        func.count(UserActivity.id).desc()
    )
    common_activities_result = db.execute(common_activities_query)
    common_activities = common_activities_result.all()
    
    # 按小时分析系统活动
    from sqlalchemy import select
    hourly_activity_query = select(
        func.hour(UserActivity.created_at).label('hour'),
        func.count(UserActivity.id).label('count')
    ).where(
        UserActivity.created_at >= start_date
    ).group_by(func.hour(UserActivity.created_at)).order_by('hour')
    hourly_activity_result = db.execute(hourly_activity_query)
    hourly_activity = hourly_activity_result.all()
    
    return {
        'most_active_users': [
            {
                'user_id': user.user_id,
                'activity_count': user.activity_count,
                'username': get_user_name(db, user.user_id)
            } for user in active_users
        ],
        'popular_pages': [
            {
                'page_url': page.page_url,
                'page_title': page.page_title,
                'view_count': page.view_count
            } for page in popular_pages
        ],
        'common_activities': [
            {
                'activity_type': activity.activity_type,
                'count': activity.count
            } for activity in common_activities
        ],
        'hourly_activity': [
            {
                'hour': activity.hour,
                'count': activity.count
            } for activity in hourly_activity
        ]
    }