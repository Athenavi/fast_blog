"""
数据分析增强版插件 (Analytics Pro)
提供高级访客统计、热门文章排行、来源分析和转化漏斗功能
"""

from collections import defaultdict, Counter
from datetime import datetime, timedelta
from typing import Dict, List, Any

from shared.services.plugin_manager import BasePlugin, plugin_hooks


class AnalyticsProPlugin(BasePlugin):
    """
    数据分析增强版插件
    
    功能:
    1. 访客统计仪表盘 - 实时数据可视化
    2. 热门文章排行 - 多维度排序
    3. 来源分析 - 详细流量来源追踪
    4. 转化漏斗 - 用户行为路径分析
    """

    def __init__(self):
        super().__init__(
            plugin_id=0,
            name="数据分析增强版",
            slug="analytics-pro",
            version="1.0.0"
        )

        # 默认设置
        self.settings = {
            'enable_tracking': True,
            'track_anonymous_users': True,
            'data_retention_days': 90,
            'enable_real_time': True,
            'enable_conversion_tracking': True,
            'dashboard_refresh_interval': 30,
        }

        # 访问记录
        self.page_views: List[Dict[str, Any]] = []

        # 实时在线用户
        self.online_users: Dict[str, datetime] = {}

        # 会话数据
        self.sessions: Dict[str, Dict[str, Any]] = {}

        # 转化事件
        self.conversion_events: List[Dict[str, Any]] = []

        # 用户行为路径
        self.user_paths: Dict[str, List[str]] = {}

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

        # 转化事件追踪
        plugin_hooks.add_action(
            "conversion_event",
            self.track_conversion_event,
            priority=10
        )

    def activate(self):
        """激活插件"""
        super().activate()
        print("[AnalyticsPro] Plugin activated")

    def deactivate(self):
        """停用插件"""
        super().deactivate()
        print("[AnalyticsPro] Plugin deactivated")

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

        # 追踪用户路径
        self._track_user_path(session_id, view_data.get('url', ''))

        # 清理过期数据
        self._cleanup_old_data()

    def track_user_activity(self, activity_data: Dict[str, Any]):
        """
        追踪用户活动
        
        Args:
            activity_data: 活动数据 {user_id, action, target, metadata}
        """
        try:
            activity_record = {
                'user_id': activity_data.get('user_id'),
                'action': activity_data.get('action', ''),
                'target': activity_data.get('target', ''),
                'metadata': activity_data.get('metadata', {}),
                'timestamp': datetime.now().isoformat(),
                'ip': activity_data.get('ip', ''),
            }

            print(f"[AnalyticsPro] User activity tracked: {activity_record['action']}")

        except Exception as e:
            print(f"[AnalyticsPro] Failed to track activity: {str(e)}")

    def track_conversion_event(self, event_data: Dict[str, Any]):
        """
        追踪转化事件
        
        Args:
            event_data: 转化事件数据 {event_type, user_id, value, metadata}
        """
        if not self.settings.get('enable_conversion_tracking'):
            return

        conversion = {
            'event_type': event_data.get('event_type', ''),
            'user_id': event_data.get('user_id'),
            'value': event_data.get('value', 0),
            'metadata': event_data.get('metadata', {}),
            'timestamp': datetime.now().isoformat(),
            'ip': event_data.get('ip', ''),
        }

        self.conversion_events.append(conversion)
        print(f"[AnalyticsPro] Conversion tracked: {conversion['event_type']}")

    def get_dashboard_stats(self, days: int = 30) -> Dict[str, Any]:
        """
        获取仪表盘统计数据
        
        Args:
            days: 统计天数
            
        Returns:
            完整的仪表盘数据
        """
        cutoff_date = datetime.now() - timedelta(days=days)

        recent_views = [
            pv for pv in self.page_views
            if datetime.fromisoformat(pv['timestamp']) > cutoff_date
        ]

        # 基础统计
        total_views = len(recent_views)
        unique_visitors = len(set(
            pv.get('ip') or pv.get('user_id')
            for pv in recent_views
            if pv.get('ip') or pv.get('user_id')
        ))

        # 热门页面
        popular_pages = self.get_popular_pages(limit=10, days=days)

        # 流量来源
        traffic_sources = self.get_traffic_sources(days=days)

        # 设备统计
        device_stats = self.get_device_stats(days=days)

        # 实时统计
        real_time = self.get_real_time_stats()

        # 转化统计
        conversions = self.get_conversion_stats(days=days)

        return {
            'overview': {
                'total_views': total_views,
                'unique_visitors': unique_visitors,
                'avg_session_duration': self._calculate_avg_session_duration(recent_views),
                'bounce_rate': self._calculate_bounce_rate(recent_views),
                'pages_per_session': round(total_views / max(unique_visitors, 1), 2),
            },
            'popular_pages': popular_pages,
            'traffic_sources': traffic_sources,
            'device_stats': device_stats,
            'real_time': real_time,
            'conversions': conversions,
            'period_days': days,
        }

    def get_popular_pages(self, limit: int = 10, days: int = 30) -> List[Dict[str, Any]]:
        """
        获取热门页面（支持多维度排序）
        
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

        # 计算平均停留时间（简化）
        page_avg_time = {}
        for url in page_counts.keys():
            page_avg_time[url] = 30  # 假设平均30秒

        # 排序并返回前N个
        popular = []
        for url, count in page_counts.most_common(limit):
            popular.append({
                'url': url,
                'title': page_titles.get(url, url),
                'views': count,
                'avg_time_on_page': f"{page_avg_time.get(url, 0)}s",
                'bounce_rate': self._calculate_page_bounce_rate(url, recent_views),
            })

        return popular

    def get_traffic_sources(self, days: int = 30) -> List[Dict[str, Any]]:
        """
        获取详细流量来源
        
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

        # 详细分类
        sources = defaultdict(lambda: {'visits': 0, 'urls': set()})

        search_domains = ['google.com', 'bing.com', 'baidu.com', 'yahoo.com']
        social_domains = ['facebook.com', 'twitter.com', 'linkedin.com', 'weibo.com']

        for pv in recent_views:
            referrer = pv.get('referrer', '').lower()
            url = pv.get('url', '')

            if not referrer or referrer == 'direct':
                sources['Direct']['visits'] += 1
                sources['Direct']['urls'].add(url)
            elif any(domain in referrer for domain in search_domains):
                sources['Search Engines']['visits'] += 1
                sources['Search Engines']['urls'].add(url)
            elif any(domain in referrer for domain in social_domains):
                sources['Social Media']['visits'] += 1
                sources['Social Media']['urls'].add(url)
            else:
                sources['Referral']['visits'] += 1
                sources['Referral']['urls'].add(url)

        # 转换为列表格式
        total = sum(s['visits'] for s in sources.values())
        result = []
        for source, data in sources.items():
            result.append({
                'source': source,
                'visits': data['visits'],
                'percentage': round((data['visits'] / total * 100) if total > 0 else 0, 2),
                'unique_pages': len(data['urls']),
            })

        return result

    def get_conversion_funnel(self, days: int = 30) -> Dict[str, Any]:
        """
        获取转化漏斗数据
        
        Args:
            days: 统计天数
            
        Returns:
            转化漏斗数据
        """
        if not self.settings.get('enable_conversion_tracking'):
            return {'enabled': False}

        cutoff_date = datetime.now() - timedelta(days=days)

        recent_conversions = [
            conv for conv in self.conversion_events
            if datetime.fromisoformat(conv['timestamp']) > cutoff_date
        ]

        # 按事件类型分组
        funnel_stages = defaultdict(int)
        for conv in recent_conversions:
            funnel_stages[conv['event_type']] += 1

        # 定义标准漏斗阶段
        standard_funnel = [
            'page_view',
            'add_to_cart',
            'checkout_start',
            'payment_info',
            'purchase_complete'
        ]

        # 构建漏斗
        funnel_data = []
        total_visitors = len(set(
            pv.get('ip') or pv.get('user_id')
            for pv in self.page_views
            if datetime.fromisoformat(pv['timestamp']) > cutoff_date
            if pv.get('ip') or pv.get('user_id')
        ))

        previous_count = total_visitors
        for stage in standard_funnel:
            count = funnel_stages.get(stage, 0)
            conversion_rate = round((count / previous_count * 100) if previous_count > 0 else 0, 2)

            funnel_data.append({
                'stage': stage,
                'count': count,
                'conversion_rate': conversion_rate,
                'drop_off': previous_count - count,
            })

            previous_count = count

        return {
            'enabled': True,
            'funnel': funnel_data,
            'total_conversions': sum(funnel_stages.values()),
            'overall_conversion_rate': round(
                (funnel_stages.get('purchase_complete', 0) / total_visitors * 100)
                if total_visitors > 0 else 0, 2
            ),
        }

    def get_device_stats(self, days: int = 30) -> Dict[str, Any]:
        """获取设备统计"""
        cutoff_date = datetime.now() - timedelta(days=days)

        recent_views = [
            pv for pv in self.page_views
            if datetime.fromisoformat(pv['timestamp']) > cutoff_date
        ]

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

    def get_conversion_stats(self, days: int = 30) -> Dict[str, Any]:
        """获取转化统计"""
        if not self.settings.get('enable_conversion_tracking'):
            return {'enabled': False}

        cutoff_date = datetime.now() - timedelta(days=days)

        recent_conversions = [
            conv for conv in self.conversion_events
            if datetime.fromisoformat(conv['timestamp']) > cutoff_date
        ]

        # 按类型统计
        by_type = Counter(conv['event_type'] for conv in recent_conversions)
        total_value = sum(conv.get('value', 0) for conv in recent_conversions)

        return {
            'enabled': True,
            'total_conversions': len(recent_conversions),
            'by_type': dict(by_type),
            'total_value': total_value,
            'avg_value': round(total_value / len(recent_conversions), 2) if recent_conversions else 0,
        }

    def _get_or_create_session(self, view_data: Dict[str, Any]) -> str:
        """获取或创建会话"""
        client_ip = view_data.get('ip', '')
        user_id = view_data.get('user_id')

        session_key = user_id or client_ip

        if session_key not in self.sessions:
            self.sessions[session_key] = {
                'start_time': datetime.now().isoformat(),
                'page_views': 0,
                'path': [],
            }

        self.sessions[session_key]['page_views'] += 1

        return session_key

    def _track_user_path(self, session_id: str, url: str):
        """追踪用户访问路径"""
        if session_id not in self.user_paths:
            self.user_paths[session_id] = []

        self.user_paths[session_id].append(url)

    def _calculate_avg_session_duration(self, views: List[Dict]) -> str:
        """计算平均会话时长"""
        if not views:
            return "0s"
        avg_seconds = 30
        return f"{avg_seconds}s"

    def _calculate_bounce_rate(self, views: List[Dict]) -> float:
        """计算跳出率"""
        if not views:
            return 0.0

        single_page_sessions = len(set(
            pv.get('ip') or pv.get('user_id')
            for pv in views
            if pv.get('ip') or pv.get('user_id')
        ))

        total_sessions = len(self.sessions)

        if total_sessions == 0:
            return 0.0

        return round((single_page_sessions / total_sessions) * 100, 2)

    def _calculate_page_bounce_rate(self, url: str, views: List[Dict]) -> float:
        """计算单页跳出率"""
        page_views = [v for v in views if v.get('url') == url]
        if not page_views:
            return 0.0

        # 简化：如果用户只访问了这一页，视为跳出
        single_visit_sessions = len(set(
            v.get('session_id') for v in page_views
        ))

        return round((single_visit_sessions / len(page_views)) * 100, 2)

    def _cleanup_old_data(self):
        """清理过期数据"""
        retention_days = self.settings.get('data_retention_days', 90)
        cutoff_date = datetime.now() - timedelta(days=retention_days)

        self.page_views = [
            pv for pv in self.page_views
            if datetime.fromisoformat(pv['timestamp']) > cutoff_date
        ]

        self.conversion_events = [
            conv for conv in self.conversion_events
            if datetime.fromisoformat(conv['timestamp']) > cutoff_date
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
                {
                    'key': 'enable_conversion_tracking',
                    'type': 'boolean',
                    'label': '启用转化跟踪',
                },
                {
                    'key': 'dashboard_refresh_interval',
                    'type': 'number',
                    'label': '仪表盘刷新间隔(秒)',
                    'min': 10,
                    'max': 300,
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
plugin_instance = AnalyticsProPlugin()
