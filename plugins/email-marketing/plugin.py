"""
邮件营销插件
提供完整的邮件订阅、群发和统计分析功能
"""

import asyncio
import json
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Dict, List, Any

from shared.services.plugin_manager import BasePlugin, plugin_hooks
from shared.utils.plugin_database import plugin_db


class EmailMarketingPlugin(BasePlugin):
    """
    邮件营销插件
    
    功能:
    1. SMTP邮件服务配置
    2. 邮件订阅管理
    3. 邮件模板系统
    4. 批量发送邮件
    5. 发送统计和分析
    6. 退订管理
    """

    def __init__(self):
        super().__init__(
            plugin_id=0,
            name="邮件营销",
            slug="email-marketing",
            version="1.0.0"
        )

        # 默认设置
        self.settings = {
            'smtp_host': 'smtp.example.com',
            'smtp_port': 587,
            'smtp_user': '',
            'smtp_password': '',
            'from_email': 'noreply@example.com',
            'from_name': 'FastBlog',
            'use_tls': True,
        }

        # 订阅者列表(实际应存储在数据库)
        self.subscribers = []

        # 发送队列
        self.send_queue = []

    def register_hooks(self):
        """注册钩子"""
        # 新用户注册时发送欢迎邮件
        plugin_hooks.add_action(
            "user_registered",
            self.on_user_registered,
            priority=10
        )

        # 文章发布时通知订阅者
        plugin_hooks.add_action(
            "article_published",
            self.on_article_published,
            priority=20
        )

    def activate(self):
        """激活插件"""
        super().activate()
        self._init_database()
        self._load_subscribers()

    def deactivate(self):
        """停用插件"""
        super().deactivate()

    def _init_database(self):
        """初始化数据库表"""
        try:
            from shared.utils.plugin_db_init import init_email_marketing_db
            init_email_marketing_db()
        except Exception as e:
            print(f"[EmailMarketing] Failed to initialize database: {e}")

    def _load_subscribers(self):
        """从数据库加载订阅者列表"""
        try:
            subscribers = plugin_db.execute_query(
                'email-marketing',
                "SELECT * FROM subscribers WHERE active = 1"
            )
            # 转换datetime对象为字符串
            self.subscribers = []
            for sub in subscribers:
                sub_dict = dict(sub)
                # 处理JSON字段
                if sub_dict.get('metadata'):
                    try:
                        sub_dict['metadata'] = json.loads(sub_dict['metadata'])
                    except:
                        sub_dict['metadata'] = {}
                self.subscribers.append(sub_dict)

            print(f"[EmailMarketing] Loaded {len(self.subscribers)} subscribers from database")
        except Exception as e:
            print(f"[EmailMarketing] Failed to load subscribers: {e}")
            self.subscribers = []

    async def on_user_registered(self, user_data: Dict[str, Any]):
        """用户注册时发送欢迎邮件"""
        if not user_data.get('email'):
            return

        subject = f"欢迎加入 {self.settings['from_name']}"
        template = self._get_welcome_template(user_data)

        await self.send_email(
            to_email=user_data['email'],
            subject=subject,
            html_content=template,
        )

    async def on_article_published(self, article_data: Dict[str, Any]):
        """文章发布时通知订阅者"""
        if not self.subscribers:
            return

        subject = f"新文章发布: {article_data.get('title', '')}"
        template = self._get_article_notification_template(article_data)

        # 批量发送给所有订阅者
        for subscriber in self.subscribers:
            if subscriber.get('active', True):
                await self.send_email(
                    to_email=subscriber['email'],
                    subject=subject,
                    html_content=template,
                )

    async def send_email(
            self,
            to_email: str,
            subject: str,
            html_content: str,
            text_content: str = None,
            attachments: List[str] = None,
    ) -> Dict[str, Any]:
        """
        发送邮件
        
        Args:
            to_email: 收件人邮箱
            subject: 邮件主题
            html_content: HTML内容
            text_content: 纯文本内容(可选)
            attachments: 附件列表(可选)
            
        Returns:
            发送结果
        """
        try:
            # 创建邮件对象
            msg = MIMEMultipart('alternative')
            msg['From'] = f"{self.settings['from_name']} <{self.settings['from_email']}>"
            msg['To'] = to_email
            msg['Subject'] = subject

            # 添加纯文本版本
            if text_content:
                msg.attach(MIMEText(text_content, 'plain', 'utf-8'))

            # 添加HTML版本
            msg.attach(MIMEText(html_content, 'html', 'utf-8'))

            # 添加附件
            if attachments:
                from email.mime.base import MIMEBase
                from email import encoders
                
                for attachment_path in attachments:
                    try:
                        with open(attachment_path, 'rb') as f:
                            part = MIMEBase('application', 'octet-stream')
                            part.set_payload(f.read())
                            encoders.encode_base64(part)
                            part.add_header(
                                'Content-Disposition',
                                f'attachment; filename="{Path(attachment_path).name}"'
                            )
                            msg.attach(part)
                    except Exception as e:
                        print(f"[EmailMarketing] Failed to attach {attachment_path}: {e}")

            # 发送邮件
            if self.settings['use_tls']:
                server = smtplib.SMTP(self.settings['smtp_host'], self.settings['smtp_port'])
                server.ehlo()
                server.starttls()
                server.ehlo()
            else:
                server = smtplib.SMTP(self.settings['smtp_host'], self.settings['smtp_port'])

            server.login(self.settings['smtp_user'], self.settings['smtp_password'])
            server.sendmail(
                self.settings['from_email'],
                to_email,
                msg.as_string()
            )
            server.quit()

            # 记录发送日志
            self._log_email_sent(to_email, subject, True)

            return {
                'success': True,
                'message': 'Email sent successfully',
            }

        except Exception as e:
            print(f"[EmailMarketing] Failed to send email: {str(e)}")
            self._log_email_sent(to_email, subject, False, str(e))

            return {
                'success': False,
                'error': str(e),
            }

    async def send_bulk_emails(
            self,
            recipients: List[str],
            subject: str,
            html_content: str,
            batch_size: int = 50,
            delay_between_batches: int = 5,
    ) -> Dict[str, Any]:
        """
        批量发送邮件
        
        Args:
            recipients: 收件人列表
            subject: 邮件主题
            html_content: HTML内容
            batch_size: 每批发送数量
            delay_between_batches: 批次间延迟(秒)
            
        Returns:
            发送统计
        """
        total = len(recipients)
        sent = 0
        failed = 0
        errors = []

        # 分批发送
        for i in range(0, total, batch_size):
            batch = recipients[i:i + batch_size]

            # 并发发送当前批次
            tasks = [
                self.send_email(
                    to_email=email,
                    subject=subject,
                    html_content=html_content,
                )
                for email in batch
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 统计结果
            for result in results:
                if isinstance(result, Exception):
                    failed += 1
                    errors.append(str(result))
                elif result.get('success'):
                    sent += 1
                else:
                    failed += 1
                    errors.append(result.get('error', 'Unknown error'))

            # 批次间延迟,避免被判定为垃圾邮件
            if i + batch_size < total:
                await asyncio.sleep(delay_between_batches)

        return {
            'success': True,
            'data': {
                'total': total,
                'sent': sent,
                'failed': failed,
                'errors': errors[:10],  # 只返回前10个错误
            }
        }

    def subscribe(self, email: str, name: str = None, metadata: Dict = None) -> Dict[str, Any]:
        """
        订阅邮件
        
        Args:
            email: 邮箱地址
            name: 姓名(可选)
            metadata: 额外元数据(可选)
            
        Returns:
            订阅结果
        """
        # 检查是否已订阅
        for sub in self.subscribers:
            if sub['email'] == email:
                return {
                    'success': False,
                    'error': 'Already subscribed',
                }

        # 添加订阅者
        subscriber = {
            'email': email,
            'name': name,
            'metadata': metadata or {},
            'active': True,
            'subscribed_at': datetime.now().isoformat(),
            'confirmed': False,  # 需要双重确认
        }

        self.subscribers.append(subscriber)

        # 保存到数据库
        try:
            plugin_db.execute_update(
                'email-marketing',
                """INSERT INTO subscribers (email, name, active, confirmed, metadata, subscribed_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    subscriber['email'],
                    subscriber.get('name'),
                    1 if subscriber['active'] else 0,
                    1 if subscriber['confirmed'] else 0,
                    json.dumps(subscriber.get('metadata', {})),
                    subscriber['subscribed_at']
                )
            )
        except Exception as e:
            print(f"[EmailMarketing] Failed to save subscriber to database: {e}")

        # 发送确认邮件
        confirmation_link = self._generate_confirmation_link(email)
        confirmation_html = self._get_confirmation_template(confirmation_link)

        asyncio.create_task(
            self.send_email(
                to_email=email,
                subject='请确认您的订阅',
                html_content=confirmation_html,
            )
        )

        return {
            'success': True,
            'message': 'Subscription created. Please check your email to confirm.',
        }

    def unsubscribe(self, email: str) -> Dict[str, Any]:
        """
        取消订阅
        
        Args:
            email: 邮箱地址
            
        Returns:
            取消结果
        """
        for sub in self.subscribers:
            if sub['email'] == email:
                sub['active'] = False
                sub['unsubscribed_at'] = datetime.now().isoformat()

                # 更新数据库
                try:
                    plugin_db.execute_update(
                        'email-marketing',
                        "UPDATE subscribers SET active = 0, unsubscribed_at = ? WHERE email = ?",
                        (sub['unsubscribed_at'], email)
                    )
                except Exception as e:
                    print(f"[EmailMarketing] Failed to update subscriber: {e}")

                return {
                    'success': True,
                    'message': 'Successfully unsubscribed',
                }

        return {
            'success': False,
            'error': 'Subscriber not found',
        }

    def get_subscriber_stats(self) -> Dict[str, Any]:
        """获取订阅者统计"""
        total = len(self.subscribers)
        active = sum(1 for s in self.subscribers if s.get('active', False))
        confirmed = sum(1 for s in self.subscribers if s.get('confirmed', False))

        return {
            'total_subscribers': total,
            'active_subscribers': active,
            'confirmed_subscribers': confirmed,
            'unconfirmed_subscribers': total - confirmed,
        }

    def _get_welcome_template(self, user_data: Dict[str, Any]) -> str:
        """获取欢迎邮件模板"""
        name = user_data.get('name', '用户')
        return f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h1 style="color: #3b82f6;">欢迎加入 {self.settings['from_name']}!</h1>
            <p>亲爱的 {name},</p>
            <p>感谢您注册我们的平台。我们很高兴您成为我们社区的一员。</p>
            <p>您将定期收到:</p>
            <ul>
                <li>最新文章通知</li>
                <li>独家内容和资源</li>
                <li>特别优惠和活动信息</li>
            </ul>
            <p>如果您有任何问题,随时回复此邮件联系我们。</p>
            <p>祝好,<br>{self.settings['from_name']} 团队</p>
            <hr style="margin-top: 30px; border: none; border-top: 1px solid #e5e7eb;">
            <p style="font-size: 12px; color: #9ca3af;">
                不想再收到邮件? <a href="{{unsubscribe_link}}">点击退订</a>
            </p>
        </body>
        </html>
        """

    def _get_article_notification_template(self, article_data: Dict[str, Any]) -> str:
        """获取文章通知模板"""
        title = article_data.get('title', '新文章')
        excerpt = article_data.get('excerpt', '')
        url = article_data.get('url', '#')

        return f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #3b82f6;">{title}</h2>
            <p>{excerpt}</p>
            <a href="{url}" style="display: inline-block; padding: 10px 20px; background-color: #3b82f6; color: white; text-decoration: none; border-radius: 5px; margin-top: 10px;">
                阅读全文
            </a>
            <hr style="margin-top: 30px; border: none; border-top: 1px solid #e5e7eb;">
            <p style="font-size: 12px; color: #9ca3af;">
                不想再收到此类邮件? <a href="{{unsubscribe_link}}">管理订阅偏好</a>
            </p>
        </body>
        </html>
        """

    def _get_confirmation_template(self, confirmation_link: str) -> str:
        """获取确认订阅模板"""
        return f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2>请确认您的订阅</h2>
            <p>请点击下面的链接确认您的订阅:</p>
            <a href="{confirmation_link}" style="display: inline-block; padding: 10px 20px; background-color: #3b82f6; color: white; text-decoration: none; border-radius: 5px;">
                确认订阅
            </a>
            <p style="margin-top: 20px; font-size: 12px; color: #9ca3af;">
                如果不是您操作的,请忽略此邮件。
            </p>
        </body>
        </html>
        """

    def _generate_confirmation_link(self, email: str) -> str:
        """生成确认链接"""
        import base64
        token = base64.urlsafe_b64encode(email.encode()).decode()
        return f"https://example.com/confirm-subscription?token={token}"

    def _log_email_sent(self, to_email: str, subject: str, success: bool, error: str = None):
        """记录邮件发送日志到数据库"""
        try:
            plugin_db.execute_update(
                'email-marketing',
                """INSERT INTO email_logs (to_email, subject, success, error, sent_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    to_email,
                    subject,
                    1 if success else 0,
                    error,
                    datetime.now().isoformat()
                )
            )
        except Exception as e:
            print(f"[EmailMarketing] Failed to log email: {e}")

        # 同时打印到控制台
        print(f"[EmailMarketing] {'✓' if success else '✗'} {subject} -> {to_email}")

    def get_settings_ui(self) -> Dict[str, Any]:
        """返回设置界面配置"""
        return {
            'fields': [
                {
                    'key': 'smtp_host',
                    'type': 'text',
                    'label': 'SMTP服务器',
                    'placeholder': 'smtp.example.com',
                    'help': '您的邮件服务提供商的SMTP服务器地址',
                },
                {
                    'key': 'smtp_port',
                    'type': 'number',
                    'label': 'SMTP端口',
                    'placeholder': '587',
                    'help': '通常为587(TLS)或465(SSL)',
                },
                {
                    'key': 'smtp_user',
                    'type': 'text',
                    'label': 'SMTP用户名',
                    'placeholder': 'your-email@example.com',
                },
                {
                    'key': 'smtp_password',
                    'type': 'password',
                    'label': 'SMTP密码',
                    'placeholder': '输入密码',
                    'help': '建议使用应用专用密码',
                },
                {
                    'key': 'from_email',
                    'type': 'email',
                    'label': '发件人邮箱',
                    'placeholder': 'noreply@example.com',
                },
                {
                    'key': 'from_name',
                    'type': 'text',
                    'label': '发件人名称',
                    'placeholder': 'FastBlog',
                },
            ]
        }


# 插件实例
plugin_instance = EmailMarketingPlugin()
