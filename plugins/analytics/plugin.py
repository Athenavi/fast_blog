"""
综合数据分析插件
整合访问统计、用户行为分析、流量来源追踪、热门文章排行、转化漏斗、实时仪表盘等功能

功能模块:
1. 页面访问统计 - PV、UV、会话追踪
2. 用户行为分析 - 活动追踪、路径分析
3. 流量来源分析 - Referrer、搜索引擎、社交媒体
4. 热门内容排行 - 多维度排序
5. 转化漏斗 - 事件追踪、转化率分析
6. 实时仪表盘 - 在线用户、实时数据
"""

from collections import defaultdict, Counter
from datetime import datetime, timedelta
from typing import Dict, List, Any

from shared.services.plugin_manager import BasePlugin, plugin_hooks


class AnalyticsPlugin(BasePlugin):
    """
    综合数据分析插件
    
    整合了以下原有插件的功能:
    - analytics: 基础数据分析
    - analytics-pro: 高级数据分析
    """

    def __init__(self):
        super().__init__(
            plugin_id=0,
            name="数据分析中心",
            slug="analytics",
            version="2.0.0"
        )

        # ==================== 全局设置 ====================
        self.settings = {
            'enable_tracking': True,
            'track_anonymous_users': True,
            'data_retention_days': 90,
            'enable_real_time': True,
            'enable_conversion_tracking': True,
            'dashboard_refresh_interval': 30,
        }

        # ==================== 访问记录 ====================
        self.page_views: List[Dict[str, Any]] = []

        # ==================== 实时在线用户 ====================
        self.online_users: Dict[str, datetime] = {}

        # ==================== 会话数据 ====================
        self.sessions: Dict[str, Dict[str, Any]] = {}

        # ==================== 转化事件 ====================
        self.conversion_events: List[Dict[str, Any]] = []

        # ==================== 用户行为路径 ====================
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
        if self.settings.get('enable_conversion_tracking'):
            plugin_hooks.add_action(
                "conversion_event",
                self.track_conversion_event,
                priority=10
            )

    def activate(self):
        """激活插件"""
        super().activate()
        print("[Analytics] Plugin activated - All analytics modules initialized")

    def deactivate(self):
        """停用插件"""
        super().deactivate()
        print("[Analytics] Plugin deactivated")

    # ==================== 页面访问追踪 ====================

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

            print(f"[Analytics] User activity tracked: {activity_record['action']}")

        except Exception as e:
            print(f"[Analytics] Failed to track activity: {e}")

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
        print(f"[Analytics] Conversion tracked: {conversion['event_type']}")

    # ==================== 统计分析 ====================

    def get_overview_stats(self, days: int = 30) -> Dict[str, Any]:
        """
        获取概览统计
        
        Args:
            days: 统计天数
            
        Returns:
            统计数据
        """
        cutoff_date = datetime.now() - timedelta(days=days)

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

        # 平均停留时间
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

        # 转换为列表并排序
        popular = [
            {
                'url': url,
                'title': page_titles.get(url, url),
                'views': count,
            }
            for url, count in page_counts.most_common(limit)
        ]

        return popular

    def get_traffic_sources(self, days: int = 30) -> Dict[str, Any]:
        """
        获取流量来源分析
        
        Args:
            days: 统计天数
            
        Returns:
            流量来源数据
        """
        cutoff_date = datetime.now() - timedelta(days=days)

        recent_views = [
            pv for pv in self.page_views
            if datetime.fromisoformat(pv['timestamp']) > cutoff_date
        ]

        sources = {
            'direct': 0,
            'search': 0,
            'social': 0,
            'referral': 0,
            'other': 0,
        }

        search_engines = ['google', 'baidu', 'bing', 'yahoo', 'sogou']
        social_platforms = ['facebook', 'twitter', 'weibo', 'wechat', 'linkedin']

        for pv in recent_views:
            referrer = pv.get('referrer', '').lower()

            if not referrer or referrer == '':
                sources['direct'] += 1
            elif any(se in referrer for se in search_engines):
                sources['search'] += 1
            elif any(sp in referrer for sp in social_platforms):
                sources['social'] += 1
            elif 'http' in referrer:
                sources['referral'] += 1
            else:
                sources['other'] += 1

        total = sum(sources.values())

        # 计算百分比
        sources_percentage = {
            key: round((value / total * 100) if total > 0 else 0, 2)
            for key, value in sources.items()
        }

        return {
            'sources': sources,
            'percentage': sources_percentage,
            'total': total,
        }

    def get_conversion_funnel(self) -> Dict[str, Any]:
        """
        获取转化漏斗
        
        Returns:
            转化漏斗数据
        """
        if not self.conversion_events:
            return {'funnel': [], 'total_conversions': 0}

        # 按事件类型分组
        events_by_type = defaultdict(list)
        for event in self.conversion_events:
            events_by_type[event['event_type']].append(event)

        funnel = []
        for event_type, events in events_by_type.items():
            funnel.append({
                'event_type': event_type,
                'count': len(events),
                'total_value': sum(e.get('value', 0) for e in events),
                'avg_value': round(sum(e.get('value', 0) for e in events) / len(events), 2),
            })

        # 按数量排序
        funnel.sort(key=lambda x: x['count'], reverse=True)

        return {
            'funnel': funnel,
            'total_conversions': len(self.conversion_events),
        }

    def get_realtime_stats(self) -> Dict[str, Any]:
        """
        获取实时统计
        
        Returns:
            实时数据
        """
        # 清理过期的在线用户（5分钟无活动视为离线）
        now = datetime.now()
        active_users = {
            ip: last_seen
            for ip, last_seen in self.online_users.items()
            if (now - last_seen).total_seconds() < 300
        }

        # 更新在线用户列表
        self.online_users = active_users

        # 最近5分钟的访问量
        five_min_ago = now - timedelta(minutes=5)
        recent_views = [
            pv for pv in self.page_views
            if datetime.fromisoformat(pv['timestamp']) > five_min_ago
        ]

        return {
            'online_users': len(active_users),
            'views_last_5min': len(recent_views),
            'timestamp': now.isoformat(),
        }

    # ==================== 辅助方法 ====================

    def _get_or_create_session(self, view_data: Dict[str, Any]) -> str:
        """获取或创建会话ID"""
        # 简化实现：使用IP作为会话标识
        client_ip = view_data.get('ip', '')
        if not client_ip:
            return 'unknown'

        # 如果会话存在且未过期，返回现有会话
        if client_ip in self.sessions:
            session = self.sessions[client_ip]
            last_activity = datetime.fromisoformat(session['last_activity'])
            if (datetime.now() - last_activity).total_seconds() < 1800:  # 30分钟
                session['last_activity'] = datetime.now().isoformat()
                session['page_views'] += 1
                return client_ip

        # 创建新会话
        self.sessions[client_ip] = {
            'session_id': client_ip,
            'start_time': datetime.now().isoformat(),
            'last_activity': datetime.now().isoformat(),
            'page_views': 1,
            'user_id': view_data.get('user_id'),
        }

        return client_ip

    def _track_user_path(self, session_id: str, url: str):
        """追踪用户访问路径"""
        if session_id not in self.user_paths:
            self.user_paths[session_id] = []

        self.user_paths[session_id].append({
            'url': url,
            'timestamp': datetime.now().isoformat(),
        })

        # 限制路径长度（最多保留50步）
        if len(self.user_paths[session_id]) > 50:
            self.user_paths[session_id] = self.user_paths[session_id][-50:]

    def _calculate_avg_session_duration(self, views: List[Dict[str, Any]]) -> float:
        """计算平均会话时长（秒）"""
        if not views:
            return 0

        # 简化计算：假设每个会话平均浏览3个页面，每个页面停留30秒
        sessions = defaultdict(list)
        for view in views:
            sessions[view['session_id']].append(
                datetime.fromisoformat(view['timestamp'])
            )

        durations = []
        for session_id, timestamps in sessions.items():
            if len(timestamps) > 1:
                timestamps.sort()
                duration = (timestamps[-1] - timestamps[0]).total_seconds()
                durations.append(duration)

        return round(sum(durations) / len(durations), 2) if durations else 0

    def _calculate_bounce_rate(self, views: List[Dict[str, Any]]) -> float:
        """计算跳出率"""
        if not views:
            return 0

        # 统计单页会话数
        session_page_counts = defaultdict(int)
        for view in views:
            session_page_counts[view['session_id']] += 1

        single_page_sessions = sum(
            1 for count in session_page_counts.values()
            if count == 1
        )

        total_sessions = len(session_page_counts)
        return round((single_page_sessions / total_sessions * 100) if total_sessions > 0 else 0, 2)

    def _cleanup_old_data(self):
        """清理过期数据"""
        retention_days = self.settings.get('data_retention_days', 90)
        cutoff_date = datetime.now() - timedelta(days=retention_days)

        # 清理页面访问记录
        self.page_views = [
            pv for pv in self.page_views
            if datetime.fromisoformat(pv['timestamp']) > cutoff_date
        ]

        # 清理转化事件
        self.conversion_events = [
            ce for ce in self.conversion_events
            if datetime.fromisoformat(ce['timestamp']) > cutoff_date
        ]

        # 清理用户路径
        expired_sessions = [
            session_id for session_id, path in self.user_paths.items()
            if not path or datetime.fromisoformat(path[-1]['timestamp']) < cutoff_date
        ]
        for session_id in expired_sessions:
            del self.user_paths[session_id]

    # ==================== 管理API ====================

    def get_dashboard_data(self) -> Dict[str, Any]:
        """获取仪表板数据"""
        overview = self.get_overview_stats(days=30)
        realtime = self.get_realtime_stats()
        sources = self.get_traffic_sources(days=30)
        conversions = self.get_conversion_funnel()

        return {
            'overview': overview,
            'realtime': realtime,
            'traffic_sources': sources,
            'conversions': conversions,
            'popular_pages': self.get_popular_pages(limit=10),
        }

    def get_admin_ui_config(self) -> Dict[str, Any]:
        """获取管理界面配置"""
        return {
            'title': '数据分析中心',
            'icon': '📊',
            'sections': [
                {
                    'title': '数据概览',
                    'widgets': [
                        {'type': 'stat', 'label': '总访问量', 'value': self.get_overview_stats()['total_views']},
                        {'type': 'stat', 'label': '独立访客', 'value': self.get_overview_stats()['unique_visitors']},
                        {'type': 'stat', 'label': '在线用户', 'value': self.get_realtime_stats()['online_users']},
                        {'type': 'stat', 'label': '转化事件', 'value': len(self.conversion_events)},
                    ],
                },
                {
                    'title': '跟踪设置',
                    'fields': [
                        {
                            'key': 'enable_tracking',
                            'label': '启用跟踪',
                            'type': 'boolean',
                        },
                        {
                            'key': 'track_anonymous_users',
                            'label': '跟踪匿名用户',
                            'type': 'boolean',
                        },
                        {
                            'key': 'data_retention_days',
                            'label': '数据保留天数',
                            'type': 'number',
                            'min': 7,
                            'max': 365,
                        },
                    ],
                },
                {
                    'title': '高级功能',
                    'fields': [
                        {
                            'key': 'enable_conversion_tracking',
                            'label': '启用转化跟踪',
                            'type': 'boolean',
                        },
                        {
                            'key': 'dashboard_refresh_interval',
                            'label': '仪表盘刷新间隔（秒）',
                            'type': 'number',
                            'min': 10,
                            'max': 300,
                        },
                    ],
                },
            ],
        }


# 导出插件实例
plugin = AnalyticsPlugin()
