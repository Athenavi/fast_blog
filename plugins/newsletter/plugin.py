"""
邮件通讯插件 (Newsletter)
提供订阅者管理、邮件模板编辑器、定时发送和打开率统计功能
"""

import json
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional

from shared.services.plugin_manager import BasePlugin, plugin_hooks


class NewsletterPlugin(BasePlugin):
    """
    邮件通讯插件
    
    功能:
    1. 订阅者管理 - 添加/删除/导出订阅者
    2. 邮件模板编辑器 - 可视化邮件设计
    3. 定时发送 - 计划邮件发送时间
    4. 打开率统计 - 追踪邮件打开和点击
    """

    def __init__(self):
        super().__init__(
            plugin_id=0,
            name="邮件通讯",
            slug="newsletter",
            version="1.0.0"
        )

        # 默认设置
        self.settings = {
            'smtp_host': '',
            'smtp_port': 587,
            'smtp_username': '',
            'smtp_password': '',
            'from_email': '',
            'from_name': 'FastBlog',
            'enable_double_optin': True,
            'welcome_email': True,
        }

        # 订阅者列表
        self.subscribers: List[Dict[str, Any]] = []

        # 邮件模板
        self.email_templates: List[Dict[str, Any]] = [
            {
                'id': 'welcome',
                'name': '欢迎邮件',
                'subject': '欢迎订阅我们的通讯!',
                'content': '<h1>欢迎!</h1><p>感谢您的订阅。</p>',
                'type': 'welcome',
            },
            {
                'id': 'weekly_digest',
                'name': '每周摘要',
                'subject': '本周精彩内容',
                'content': '<h1>本周摘要</h1><p>{{articles}}</p>',
                'type': 'digest',
            },
        ]

        # 已发送邮件
        self.sent_emails: List[Dict[str, Any]] = []

        # 邮件统计
        self.email_stats = {
            'total_sent': 0,
            'total_opened': 0,
            'total_clicked': 0,
            'by_campaign': {},
        }

    def register_hooks(self):
        """注册钩子"""
        # 新用户注册时添加订阅选项
        plugin_hooks.add_action(
            "user_registered",
            self.on_user_registered,
            priority=10
        )

    def activate(self):
        """激活插件"""
        super().activate()
        print("[Newsletter] Plugin activated")

    def deactivate(self):
        """停用插件"""
        super().deactivate()
        print("[Newsletter] Plugin deactivated")

    def subscribe(self, email: str, name: str = '', metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        添加订阅者
        
        Args:
            email: 邮箱地址
            name: 姓名
            metadata: 额外元数据
            
        Returns:
            订阅结果
        """
        # 检查是否已订阅
        existing = next((s for s in self.subscribers if s['email'] == email), None)
        if existing:
            return {'success': False, 'error': 'Already subscribed'}

        # 创建订阅者记录
        subscriber = {
            'id': str(uuid.uuid4())[:8],
            'email': email,
            'name': name,
            'status': 'pending' if self.settings.get('enable_double_optin') else 'active',
            'subscribed_at': datetime.now().isoformat(),
            'metadata': metadata or {},
            'tags': [],
        }

        self.subscribers.append(subscriber)

        # 发送确认邮件(双重确认)
        if self.settings.get('enable_double_optin'):
            self._send_confirmation_email(subscriber)
        elif self.settings.get('welcome_email'):
            # 直接发送欢迎邮件
            self._send_welcome_email(subscriber)

        print(f"[Newsletter] New subscriber: {email}")
        return {'success': True, 'subscriber_id': subscriber['id']}

    def unsubscribe(self, email: str) -> bool:
        """
        取消订阅
        
        Args:
            email: 邮箱地址
            
        Returns:
            是否成功
        """
        for subscriber in self.subscribers:
            if subscriber['email'] == email:
                subscriber['status'] = 'unsubscribed'
                subscriber['unsubscribed_at'] = datetime.now().isoformat()
                print(f"[Newsletter] Unsubscribed: {email}")
                return True
        return False

    def confirm_subscription(self, token: str) -> bool:
        """
        确认订阅(双重确认)
        
        Args:
            token: 确认令牌
            
        Returns:
            是否成功
        """
        for subscriber in self.subscribers:
            if subscriber.get('confirmation_token') == token:
                subscriber['status'] = 'active'
                subscriber['confirmed_at'] = datetime.now().isoformat()

                # 发送欢迎邮件
                if self.settings.get('welcome_email'):
                    self._send_welcome_email(subscriber)

                print(f"[Newsletter] Subscription confirmed: {subscriber['email']}")
                return True
        return False

    def get_subscribers(self, status: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """
        获取订阅者列表
        
        Args:
            status: 状态过滤 (active, pending, unsubscribed)
            limit: 返回数量限制
            
        Returns:
            订阅者列表
        """
        filtered = self.subscribers

        if status:
            filtered = [s for s in filtered if s['status'] == status]

        # 按订阅时间倒序
        sorted_subs = sorted(
            filtered,
            key=lambda x: x['subscribed_at'],
            reverse=True
        )

        return sorted_subs[:limit]

    def get_subscriber_stats(self) -> Dict[str, Any]:
        """获取订阅者统计"""
        total = len(self.subscribers)
        active = len([s for s in self.subscribers if s['status'] == 'active'])
        pending = len([s for s in self.subscribers if s['status'] == 'pending'])
        unsubscribed = len([s for s in self.subscribers if s['status'] == 'unsubscribed'])

        # 按月统计新增订阅者
        by_month = {}
        for sub in self.subscribers:
            month = sub['subscribed_at'][:7]  # YYYY-MM
            by_month[month] = by_month.get(month, 0) + 1

        return {
            'total_subscribers': total,
            'active': active,
            'pending': pending,
            'unsubscribed': unsubscribed,
            'growth_rate': round((active / total * 100) if total > 0 else 0, 2),
            'by_month': by_month,
        }

    def create_template(self, name: str, subject: str, content: str, template_type: str = 'custom') -> Dict[str, Any]:
        """
        创建邮件模板
        
        Args:
            name: 模板名称
            subject: 邮件主题
            content: 邮件内容(HTML)
            template_type: 模板类型
            
        Returns:
            创建的模板
        """
        template = {
            'id': str(uuid.uuid4())[:8],
            'name': name,
            'subject': subject,
            'content': content,
            'type': template_type,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
        }

        self.email_templates.append(template)
        print(f"[Newsletter] Template created: {name}")
        return template

    def send_campaign(self, template_id: str, recipient_list: List[str], scheduled_time: Optional[str] = None) -> Dict[
        str, Any]:
        """
        发送邮件活动
        
        Args:
            template_id: 模板ID
            recipient_list: 收件人列表
            scheduled_time: 计划发送时间(ISO格式)
            
        Returns:
            发送结果
        """
        # 查找模板
        template = next((t for t in self.email_templates if t['id'] == template_id), None)
        if not template:
            return {'success': False, 'error': 'Template not found'}

        campaign = {
            'id': str(uuid.uuid4())[:8],
            'template_id': template_id,
            'template_name': template['name'],
            'subject': template['subject'],
            'recipients': recipient_list,
            'total_recipients': len(recipient_list),
            'status': 'scheduled' if scheduled_time else 'sending',
            'scheduled_time': scheduled_time,
            'sent_at': datetime.now().isoformat() if not scheduled_time else None,
            'stats': {
                'sent': 0,
                'opened': 0,
                'clicked': 0,
                'bounced': 0,
            },
        }

        self.sent_emails.append(campaign)

        # 立即发送或计划发送
        if scheduled_time:
            print(f"[Newsletter] Campaign scheduled: {campaign['id']} at {scheduled_time}")
        else:
            # 模拟发送邮件
            self._execute_send(campaign)

        return {'success': True, 'campaign_id': campaign['id']}

    def _execute_send(self, campaign: Dict[str, Any]):
        """执行邮件发送"""
        try:
            # 这里应该集成实际的SMTP发送
            # 简化实现：模拟发送成功

            campaign['status'] = 'sent'
            campaign['stats']['sent'] = campaign['total_recipients']

            # 更新全局统计
            self.email_stats['total_sent'] += campaign['total_recipients']
            self.email_stats['by_campaign'][campaign['id']] = campaign['stats']

            print(f"[Newsletter] Campaign sent: {campaign['id']} to {campaign['total_recipients']} recipients")

        except Exception as e:
            campaign['status'] = 'failed'
            print(f"[Newsletter] Campaign failed: {str(e)}")

    def track_email_open(self, campaign_id: str, subscriber_email: str):
        """
        追踪邮件打开
        
        Args:
            campaign_id: 活动ID
            subscriber_email: 订阅者邮箱
        """
        campaign = next((c for c in self.sent_emails if c['id'] == campaign_id), None)
        if campaign:
            campaign['stats']['opened'] += 1
            self.email_stats['total_opened'] += 1
            print(f"[Newsletter] Email opened: {subscriber_email}")

    def track_email_click(self, campaign_id: str, subscriber_email: str, link_url: str):
        """
        追踪邮件点击
        
        Args:
            campaign_id: 活动ID
            subscriber_email: 订阅者邮箱
            link_url: 点击的链接
        """
        campaign = next((c for c in self.sent_emails if c['id'] == campaign_id), None)
        if campaign:
            campaign['stats']['clicked'] += 1
            self.email_stats['total_clicked'] += 1
            print(f"[Newsletter] Link clicked: {subscriber_email} -> {link_url}")

    def get_campaign_stats(self, campaign_id: str) -> Dict[str, Any]:
        """
        获取活动统计
        
        Args:
            campaign_id: 活动ID
            
        Returns:
            统计数据
        """
        campaign = next((c for c in self.sent_emails if c['id'] == campaign_id), None)
        if not campaign:
            return {'error': 'Campaign not found'}

        stats = campaign['stats']
        total_sent = stats['sent']

        return {
            'campaign_id': campaign_id,
            'subject': campaign['subject'],
            'total_sent': total_sent,
            'opened': stats['opened'],
            'clicked': stats['clicked'],
            'bounced': stats['bounced'],
            'open_rate': round((stats['opened'] / total_sent * 100) if total_sent > 0 else 0, 2),
            'click_rate': round((stats['clicked'] / total_sent * 100) if total_sent > 0 else 0, 2),
            'bounce_rate': round((stats['bounced'] / total_sent * 100) if total_sent > 0 else 0, 2),
        }

    def get_overall_stats(self) -> Dict[str, Any]:
        """获取整体统计"""
        total_sent = self.email_stats['total_sent']
        total_opened = self.email_stats['total_opened']
        total_clicked = self.email_stats['total_clicked']

        return {
            'total_campaigns': len(self.sent_emails),
            'total_emails_sent': total_sent,
            'total_opens': total_opened,
            'total_clicks': total_clicked,
            'avg_open_rate': round((total_opened / total_sent * 100) if total_sent > 0 else 0, 2),
            'avg_click_rate': round((total_clicked / total_sent * 100) if total_sent > 0 else 0, 2),
        }

    def export_subscribers(self, format: str = 'csv') -> str:
        """
        导出订阅者列表
        
        Args:
            format: 导出格式 (csv, json)
            
        Returns:
            导出的数据
        """
        if format == 'json':
            return json.dumps(self.subscribers, indent=2, ensure_ascii=False)

        elif format == 'csv':
            import csv
            import io

            if not self.subscribers:
                return ""

            output = io.StringIO()
            fieldnames = ['id', 'email', 'name', 'status', 'subscribed_at']

            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()

            for subscriber in self.subscribers:
                writer.writerow({
                    'id': subscriber['id'],
                    'email': subscriber['email'],
                    'name': subscriber.get('name', ''),
                    'status': subscriber['status'],
                    'subscribed_at': subscriber['subscribed_at'],
                })

            return output.getvalue()

        return ""

    def _send_confirmation_email(self, subscriber: Dict[str, Any]):
        """发送确认邮件"""
        # 生成确认令牌
        token = str(uuid.uuid4())
        subscriber['confirmation_token'] = token

        # 构建确认链接
        confirmation_url = f"https://example.com/confirm?token={token}"

        print(f"[Newsletter] Confirmation email would be sent to: {subscriber['email']}")
        print(f"  Confirmation URL: {confirmation_url}")

    def _send_welcome_email(self, subscriber: Dict[str, Any]):
        """发送欢迎邮件"""
        print(f"[Newsletter] Welcome email would be sent to: {subscriber['email']}")

    def on_user_registered(self, user_data: Dict[str, Any]):
        """用户注册时触发"""
        # 如果用户选择订阅，自动添加
        if user_data.get('subscribe_newsletter'):
            self.subscribe(
                email=user_data.get('email', ''),
                name=user_data.get('username', ''),
            )

    def get_settings_ui(self) -> Dict[str, Any]:
        """返回设置界面配置"""
        return {
            'fields': [
                {
                    'key': 'smtp_host',
                    'type': 'text',
                    'label': 'SMTP服务器',
                },
                {
                    'key': 'smtp_port',
                    'type': 'number',
                    'label': 'SMTP端口',
                },
                {
                    'key': 'smtp_username',
                    'type': 'text',
                    'label': 'SMTP用户名',
                },
                {
                    'key': 'smtp_password',
                    'type': 'password',
                    'label': 'SMTP密码',
                },
                {
                    'key': 'from_email',
                    'type': 'text',
                    'label': '发件人邮箱',
                },
                {
                    'key': 'from_name',
                    'type': 'text',
                    'label': '发件人名称',
                },
                {
                    'key': 'enable_double_optin',
                    'type': 'boolean',
                    'label': '启用双重确认',
                },
                {
                    'key': 'welcome_email',
                    'type': 'boolean',
                    'label': '发送欢迎邮件',
                },
            ],
            'actions': [
                {
                    'type': 'button',
                    'label': '测试SMTP配置',
                    'action': 'test_smtp',
                    'variant': 'outline',
                },
                {
                    'type': 'button',
                    'label': '导出订阅者',
                    'action': 'export_subscribers',
                    'variant': 'default',
                },
            ]
        }


# 插件实例
plugin_instance = NewsletterPlugin()
