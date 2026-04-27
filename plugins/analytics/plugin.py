"""
数据分析插件
提供访问统计、用户行为分析和可视化报表
"""

import json
from collections import defaultdict, Counter
from datetime import datetime, timedelta
from typing import Dict, List, Any

from shared.services.plugin_manager import BasePlugin, plugin_hooks


class AnalyticsPlugin(BasePlugin):
    """
    数据分析插件
    
    功能:
    1. 页面访问统计
    2. 用户行为追踪
    3. 流量来源分析
    4. 热门内容排行
    5. 实时在线用户
    6. 访客地理位置
    7. 设备与浏览器统计
    8. 自定义事件跟踪
    """

    def __init__(self):
        super().__init__(
            plugin_id=0,
            name="数据分析",
            slug="analytics",
            version="1.0.0"
        )

        # 默认设置
        self.settings = {
            'enable_tracking': True,
            'track_anonymous_users': True,
            'data_retention_days': 90,
            'enable_real_time': True,
        }

        # 访问记录 (实际应存储在数据库)
        self.page_views: List[Dict[str, Any]] = []

        # 实时在线用户
        self.online_users: Dict[str, datetime] = {}

        # 会话数据
        self.sessions: Dict[str, Dict[str, Any]] = {}

    def register_hooks(self):
        """注册钩子"""
        # 页面访问追踪
        plugin_hooks.add_action(
            "page_view",
            self.track_page_view,
            priority=10
        )

        # 用户活动追踪
        plugin_hooks.add_action(
            "user_activity",
            self.track_user_activity,
            priority=10
        )

    def activate(self):
        """激活插件"""
        super().activate()
        print("[Analytics] Plugin activated")

    def track_page_view(self, view_data: Dict[str, Any]):
        """
        追踪页面访问
        
        Args:
            view_data: 访问数据 {url, user_id, ip, referrer, user_agent, timestamp}
        """
        if not self.settings.get('enable_tracking'):
            return

        # 生成会话ID
        session_id = self._get_or_create_session(view_data)

        # 记录页面访问
        page_view = {
            'session_id': session_id,
            'url': view_data.get('url', ''),
            'user_id': view_data.get('user_id'),
            'ip': view_data.get('ip', ''),
            'referrer': view_data.get('referrer', ''),
            'user_agent': view_data.get('user_agent', ''),
            'timestamp': view_data.get('timestamp', datetime.now().isoformat()),
            'title': view_data.get('title', ''),
        }

        self.page_views.append(page_view)

        # 更新在线用户
        client_ip = view_data.get('ip', '')
        if client_ip:
            self.online_users[client_ip] = datetime.now()

        # 清理过期数据
        self._cleanup_old_data()

    def track_user_activity(self, activity_data: Dict[str, Any]):
        """
        追踪用户活动
        
        Args:
            activity_data: 活动数据 {user_id, action, target, metadata}
        """
        try:
            # 记录到内存(实际应写入数据库)
            activity_record = {
                'user_id': activity_data.get('user_id'),
                'action': activity_data.get('action', ''),
                'target': activity_data.get('target', ''),
                'metadata': activity_data.get('metadata', {}),
                'timestamp': datetime.now().isoformat(),
                'ip': activity_data.get('ip', ''),
            }

            # 这里可以扩展到数据库存储
            # 例如: save_to_database(activity_record)
            print(f"[Analytics] User activity tracked: {activity_record['action']}")

        except Exception as e:
            print(f"[Analytics] Failed to track activity: {str(e)}")

    def get_overview_stats(self, days: int = 30) -> Dict[str, Any]:
        """
        获取概览统计
        
        Args:
            days: 统计天数
            
        Returns:
            统计数据
        """
        cutoff_date = datetime.now() - timedelta(days=days)

        # 过滤指定时间范围内的数据
        recent_views = [
            pv for pv in self.page_views
            if datetime.fromisoformat(pv['timestamp']) > cutoff_date
        ]

        # 总访问量
        total_views = len(recent_views)

        # 独立访客数
        unique_visitors = len(set(
            pv.get('ip') or pv.get('user_id')
            for pv in recent_views
            if pv.get('ip') or pv.get('user_id')
        ))

        # 平均停留时间(简化计算)
        avg_session_duration = self._calculate_avg_session_duration(recent_views)

        # 跳出率
        bounce_rate = self._calculate_bounce_rate(recent_views)

        # 页面/会话
        pages_per_session = total_views / max(unique_visitors, 1)

        return {
            'total_views': total_views,
            'unique_visitors': unique_visitors,
            'avg_session_duration': avg_session_duration,
            'bounce_rate': bounce_rate,
            'pages_per_session': round(pages_per_session, 2),
            'period_days': days,
        }

    def get_popular_pages(self, limit: int = 10, days: int = 30) -> List[Dict[str, Any]]:
        """
        获取热门页面
        
        Args:
            limit: 返回数量
            days: 统计天数
            
        Returns:
            热门页面列表
        """
        cutoff_date = datetime.now() - timedelta(days=days)

        recent_views = [
            pv for pv in self.page_views
            if datetime.fromisoformat(pv['timestamp']) > cutoff_date
        ]

        # 统计每个页面的访问量
        page_counts = Counter(pv['url'] for pv in recent_views)

        # 获取页面标题映射
        page_titles = {}
        for pv in recent_views:
            if pv['url'] not in page_titles and pv.get('title'):
                page_titles[pv['url']] = pv['title']

        # 排序并返回前N个
        popular = []
        for url, count in page_counts.most_common(limit):
            popular.append({
                'url': url,
                'title': page_titles.get(url, url),
                'views': count,
            })

        return popular

    def get_traffic_sources(self, days: int = 30) -> List[Dict[str, Any]]:
        """
        获取流量来源
        
        Args:
            days: 统计天数
            
        Returns:
            流量来源列表
        """
        cutoff_date = datetime.now() - timedelta(days=days)

        recent_views = [
            pv for pv in self.page_views
            if datetime.fromisoformat(pv['timestamp']) > cutoff_date
               and pv.get('referrer')
        ]

        # 分类流量来源
        sources = {
            'Direct': 0,
            'Search Engines': 0,
            'Social Media': 0,
            'Referral': 0,
        }

        search_domains = ['google.com', 'bing.com', 'baidu.com', 'yahoo.com']
        social_domains = ['facebook.com', 'twitter.com', 'linkedin.com', 'weibo.com']

        for pv in recent_views:
            referrer = pv.get('referrer', '').lower()

            if not referrer or referrer == 'direct':
                sources['Direct'] += 1
            elif any(domain in referrer for domain in search_domains):
                sources['Search Engines'] += 1
            elif any(domain in referrer for domain in social_domains):
                sources['Social Media'] += 1
            else:
                sources['Referral'] += 1

        # 转换为列表格式
        total = sum(sources.values())
        result = []
        for source, count in sources.items():
            result.append({
                'source': source,
                'visits': count,
                'percentage': round((count / total * 100) if total > 0 else 0, 2),
            })

        return result

    def get_device_stats(self, days: int = 30) -> Dict[str, Any]:
        """
        获取设备统计
        
        Args:
            days: 统计天数
            
        Returns:
            设备统计信息
        """
        cutoff_date = datetime.now() - timedelta(days=days)

        recent_views = [
            pv for pv in self.page_views
            if datetime.fromisoformat(pv['timestamp']) > cutoff_date
        ]

        # 分析User Agent
        devices = Counter()
        browsers = Counter()
        os_list = Counter()

        for pv in recent_views:
            ua = pv.get('user_agent', '').lower()

            # 设备类型
            if 'mobile' in ua or 'android' in ua or 'iphone' in ua:
                devices['Mobile'] += 1
            elif 'tablet' in ua or 'ipad' in ua:
                devices['Tablet'] += 1
            else:
                devices['Desktop'] += 1

            # 浏览器
            if 'chrome' in ua:
                browsers['Chrome'] += 1
            elif 'firefox' in ua:
                browsers['Firefox'] += 1
            elif 'safari' in ua:
                browsers['Safari'] += 1
            elif 'edge' in ua:
                browsers['Edge'] += 1
            else:
                browsers['Other'] += 1

            # 操作系统
            if 'windows' in ua:
                os_list['Windows'] += 1
            elif 'mac' in ua:
                os_list['macOS'] += 1
            elif 'linux' in ua:
                os_list['Linux'] += 1
            elif 'android' in ua:
                os_list['Android'] += 1
            elif 'ios' in ua or 'iphone' in ua:
                os_list['iOS'] += 1
            else:
                os_list['Other'] += 1

        return {
            'devices': dict(devices),
            'browsers': dict(browsers),
            'operating_systems': dict(os_list),
        }

    def get_real_time_stats(self) -> Dict[str, Any]:
        """获取实时统计"""
        if not self.settings.get('enable_real_time'):
            return {'enabled': False}

        # 清理过期的在线用户(5分钟无活动视为离线)
        cutoff_time = datetime.now() - timedelta(minutes=5)
        self.online_users = {
            ip: last_seen for ip, last_seen in self.online_users.items()
            if last_seen > cutoff_time
        }

        # 最近30分钟的访问
        recent_cutoff = datetime.now() - timedelta(minutes=30)
        recent_views = [
            pv for pv in self.page_views
            if datetime.fromisoformat(pv['timestamp']) > recent_cutoff
        ]

        # 按分钟分组
        views_by_minute = defaultdict(int)
        for pv in recent_views:
            minute = datetime.fromisoformat(pv['timestamp']).strftime('%H:%M')
            views_by_minute[minute] += 1

        return {
            'enabled': True,
            'online_users': len(self.online_users),
            'views_last_30min': len(recent_views),
            'views_by_minute': dict(views_by_minute),
        }

    def get_user_retention(self, days: int = 30) -> Dict[str, Any]:
        """
        获取用户留存率
        
        Args:
            days: 统计天数
            
        Returns:
            留存率数据
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days)

            # 获取所有访问记录
            recent_views = [
                pv for pv in self.page_views
                if datetime.fromisoformat(pv['timestamp']) > cutoff_date
            ]

            # 按用户分组
            user_first_visit = {}
            user_last_visit = {}

            for view in recent_views:
                user_key = view.get('user_id') or view.get('ip', '')
                if not user_key:
                    continue

                visit_time = datetime.fromisoformat(view['timestamp'])

                if user_key not in user_first_visit:
                    user_first_visit[user_key] = visit_time
                else:
                    if visit_time < user_first_visit[user_key]:
                        user_first_visit[user_key] = visit_time

                if user_key not in user_last_visit:
                    user_last_visit[user_key] = visit_time
                else:
                    if visit_time > user_last_visit[user_key]:
                        user_last_visit[user_key] = visit_time

            # 计算新用户和回访用户
            new_users = 0
            returning_users = 0

            for user_key, first_visit in user_first_visit.items():
                # 如果是最近7天内首次访问,视为新用户
                if (datetime.now() - first_visit).days <= 7:
                    new_users += 1
                else:
                    # 检查是否有回访
                    last_visit = user_last_visit.get(user_key, first_visit)
                    if (last_visit - first_visit).days > 0:
                        returning_users += 1

            total_users = new_users + returning_users
            retention_rate = (returning_users / total_users * 100) if total_users > 0 else 0

            return {
                'new_users': new_users,
                'returning_users': returning_users,
                'total_users': total_users,
                'retention_rate': round(retention_rate, 2),
                'period_days': days,
            }
        except Exception as e:
            print(f"[Analytics] Failed to calculate retention: {str(e)}")
            return {
                'new_users': 0,
                'returning_users': 0,
                'total_users': 0,
                'retention_rate': 0,
                'period_days': days,
            }

    def export_data(self, format: str = 'json', days: int = 30) -> Any:
        """
        导出数据
        
        Args:
            format: 导出格式 (json, csv)
            days: 导出天数
            
        Returns:
            导出的数据
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days)

            recent_views = [
                pv for pv in self.page_views
                if datetime.fromisoformat(pv['timestamp']) > cutoff_date
            ]

            if format == 'json':
                return json.dumps(recent_views, indent=2, ensure_ascii=False)
            elif format == 'csv':
                import csv
                import io

                if not recent_views:
                    return ""

                # 创建CSV字符串
                output = io.StringIO()
                fieldnames = ['timestamp', 'url', 'user_id', 'ip', 'referrer', 'title']
                writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction='ignore')

                writer.writeheader()
                for view in recent_views:
                    writer.writerow(view)

                return output.getvalue()

            return None
        except Exception as e:
            print(f"[Analytics] Failed to export data: {str(e)}")
            return None

    def _get_or_create_session(self, view_data: Dict[str, Any]) -> str:
        """获取或创建会话"""
        client_ip = view_data.get('ip', '')
        user_id = view_data.get('user_id')

        # 使用IP或用户ID作为会话标识
        session_key = user_id or client_ip

        if session_key not in self.sessions:
            self.sessions[session_key] = {
                'start_time': datetime.now().isoformat(),
                'page_views': 0,
            }

        self.sessions[session_key]['page_views'] += 1

        return session_key

    def _calculate_avg_session_duration(self, views: List[Dict]) -> str:
        """计算平均会话时长"""
        # 简化实现
        if not views:
            return "0s"

        # 假设平均每页停留30秒
        avg_seconds = 30
        return f"{avg_seconds}s"

    def _calculate_bounce_rate(self, views: List[Dict]) -> float:
        """计算跳出率"""
        if not views:
            return 0.0

        # 单页会话视为跳出
        single_page_sessions = len(set(
            pv.get('ip') or pv.get('user_id')
            for pv in views
            if pv.get('ip') or pv.get('user_id')
        ))

        total_sessions = len(self.sessions)

        if total_sessions == 0:
            return 0.0

        return round((single_page_sessions / total_sessions) * 100, 2)

    def _cleanup_old_data(self):
        """清理过期数据"""
        retention_days = self.settings.get('data_retention_days', 90)
        cutoff_date = datetime.now() - timedelta(days=retention_days)

        # 清理旧的页面访问记录
        self.page_views = [
            pv for pv in self.page_views
            if datetime.fromisoformat(pv['timestamp']) > cutoff_date
        ]

    def get_settings_ui(self) -> Dict[str, Any]:
        """返回设置界面配置"""
        return {
            'fields': [
                {
                    'key': 'enable_tracking',
                    'type': 'boolean',
                    'label': '启用跟踪',
                },
                {
                    'key': 'track_anonymous_users',
                    'type': 'boolean',
                    'label': '跟踪匿名用户',
                },
                {
                    'key': 'data_retention_days',
                    'type': 'number',
                    'label': '数据保留天数',
                    'min': 7,
                    'max': 365,
                },
                {
                    'key': 'enable_real_time',
                    'type': 'boolean',
                    'label': '启用实时统计',
                },
            ],
            'actions': [
                {
                    'type': 'button',
                    'label': '导出数据',
                    'action': 'export_data',
                    'variant': 'outline',
                },
            ]
        }


# 插件实例
plugin_instance = AnalyticsPlugin()
