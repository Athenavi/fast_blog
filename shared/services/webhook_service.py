"""
Webhook服务

功能：
1. Webhook配置管理
2. 事件触发和投递
3. HMAC签名验证
4. 重试机制
5. 投递记录追踪
"""
import asyncio
import hashlib
import hmac
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging

import aiohttp
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from shared.models.webhook import Webhook
from shared.models.webhook_delivery import WebhookDelivery

logger = logging.getLogger(__name__)


class WebhookService:
    """
    Webhook服务
    
    功能：
    1. 创建和管理Webhook配置
    2. 触发事件并投递到订阅的URL
    3. HMAC签名验证
    4. 自动重试失败的投递
    5. 投递历史记录
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.max_retries = 3
        self.retry_delay = 60  # 秒
        self.timeout = 30  # 请求超时（秒）

    async def create_webhook(self, name: str, url: str, events: List[str],
                             secret: Optional[str] = None) -> Webhook:
        """
        创建Webhook
        
        Args:
            name: Webhook名称
            url: Webhook URL
            events: 订阅的事件列表
            secret: 签名密钥（可选）
            
        Returns:
            创建的Webhook对象
        """
        webhook = Webhook(
            name=name,
            url=url,
            events=json.dumps(events),
            secret=secret,
            is_active=True,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

        self.db.add(webhook)
        await self.db.commit()
        await self.db.refresh(webhook)

        logger.info(f"Created webhook: {name} ({url})")
        return webhook

    async def update_webhook(self, webhook_id: int, **kwargs) -> Optional[Webhook]:
        """
        更新Webhook
        
        Args:
            webhook_id: Webhook ID
            **kwargs: 要更新的字段
            
        Returns:
            更新后的Webhook对象
        """
        result = await self.db.execute(
            select(Webhook).where(Webhook.id == webhook_id)
        )
        webhook = result.scalar_one_or_none()

        if not webhook:
            return None

        for key, value in kwargs.items():
            if hasattr(webhook, key):
                if key == 'events' and isinstance(value, list):
                    value = json.dumps(value)
                setattr(webhook, key, value)

        webhook.updated_at = datetime.now()
        await self.db.commit()
        await self.db.refresh(webhook)

        logger.info(f"Updated webhook: {webhook_id}")
        return webhook

    async def delete_webhook(self, webhook_id: int) -> bool:
        """
        删除Webhook
        
        Args:
            webhook_id: Webhook ID
            
        Returns:
            是否删除成功
        """
        result = await self.db.execute(
            select(Webhook).where(Webhook.id == webhook_id)
        )
        webhook = result.scalar_one_or_none()

        if not webhook:
            return False

        await self.db.delete(webhook)
        await self.db.commit()

        logger.info(f"Deleted webhook: {webhook_id}")
        return True

    async def trigger_event(self, event: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        触发事件并投递到所有订阅的Webhook
        
        Args:
            event: 事件类型
            payload: 事件数据
            
        Returns:
            投递结果统计
        """
        # 查询订阅了该事件的活跃Webhook
        result = await self.db.execute(
            select(Webhook).where(
                Webhook.is_active == True
            )
        )
        webhooks = result.scalars().all()

        matched_webhooks = []
        for webhook in webhooks:
            events = json.loads(webhook.events)
            if event in events or '*' in events:
                matched_webhooks.append(webhook)

        logger.info(f"Triggering event '{event}' to {len(matched_webhooks)} webhooks")

        # 异步投递到所有匹配的Webhook
        tasks = []
        for webhook in matched_webhooks:
            task = self._deliver_webhook(webhook, event, payload)
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        success_count = sum(1 for r in results if isinstance(r, dict) and r.get('success'))
        failed_count = len(results) - success_count

        return {
            'event': event,
            'total_webhooks': len(matched_webhooks),
            'success_count': success_count,
            'failed_count': failed_count
        }

    async def _deliver_webhook(self, webhook: Webhook, event: str,
                               payload: Dict[str, Any],
                               retry_count: int = 0) -> Dict[str, Any]:
        """
        投递Webhook
        
        Args:
            webhook: Webhook对象
            event: 事件类型
            payload: 事件数据
            retry_count: 当前重试次数
            
        Returns:
            投递结果
        """
        delivery = WebhookDelivery(
            webhook=webhook.id,
            event=event,
            payload=json.dumps(payload),
            retry_count=retry_count,
            created_at=datetime.now()
        )

        try:
            # 准备请求数据
            headers = {
                'Content-Type': 'application/json',
                'X-Webhook-Event': event,
                'X-Webhook-Delivery-ID': str(delivery.id),
            }

            # 添加HMAC签名
            if webhook.secret:
                signature = self._generate_signature(webhook.secret, payload)
                headers['X-Webhook-Signature'] = signature

            # 发送HTTP请求
            async with aiohttp.ClientSession() as session:
                async with session.post(
                        webhook.url,
                        json=payload,
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    response_body = await response.text()

                    delivery.response_status = response.status
                    delivery.response_body = response_body[:10000]  # 限制长度
                    delivery.success = 200 <= response.status < 300

            # 保存投递记录
            self.db.add(delivery)
            await self.db.commit()

            if delivery.success:
                logger.info(f"Webhook delivered successfully: {webhook.id} -> {webhook.url}")
            else:
                logger.warning(f"Webhook delivery failed: {webhook.id} (status: {delivery.response_status})")

                # 安排重试
                if retry_count < self.max_retries:
                    await self._schedule_retry(delivery, webhook, event, payload, retry_count)

            return {
                'success': delivery.success,
                'delivery_id': delivery.id,
                'status_code': delivery.response_status
            }

        except Exception as e:
            logger.error(f"Webhook delivery error: {webhook.id} - {str(e)}")

            delivery.success = False
            delivery.response_body = str(e)[:10000]

            self.db.add(delivery)
            await self.db.commit()

            # 安排重试
            if retry_count < self.max_retries:
                await self._schedule_retry(delivery, webhook, event, payload, retry_count)

            return {
                'success': False,
                'delivery_id': delivery.id,
                'error': str(e)
            }

    async def _schedule_retry(self, delivery: WebhookDelivery, webhook: Webhook,
                              event: str, payload: Dict[str, Any],
                              retry_count: int):
        """
        安排重试
        
        Args:
            delivery: 投递记录
            webhook: Webhook对象
            event: 事件类型
            payload: 事件数据
            retry_count: 当前重试次数
        """
        next_retry_at = datetime.now() + timedelta(seconds=self.retry_delay * (retry_count + 1))

        # 更新投递记录
        delivery.next_retry_at = next_retry_at
        await self.db.commit()

        logger.info(f"Scheduled retry for delivery {delivery.id} at {next_retry_at}")

        # 异步等待后重试
        async def delayed_retry():
            await asyncio.sleep(self.retry_delay * (retry_count + 1))
            await self._deliver_webhook(webhook, event, payload, retry_count + 1)

        asyncio.create_task(delayed_retry())

    def _generate_signature(self, secret: str, payload: Dict[str, Any]) -> str:
        """
        生成HMAC签名
        
        Args:
            secret: 密钥
            payload: 载荷数据
            
        Returns:
            HMAC签名字符串
        """
        payload_str = json.dumps(payload, separators=(',', ':'))
        signature = hmac.new(
            secret.encode('utf-8'),
            payload_str.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        return f"sha256={signature}"

    def verify_signature(self, secret: str, payload: Dict[str, Any],
                         signature: str) -> bool:
        """
        验证HMAC签名
        
        Args:
            secret: 密钥
            payload: 载荷数据
            signature: 签名字符串
            
        Returns:
            签名是否有效
        """
        expected_signature = self._generate_signature(secret, payload)
        return hmac.compare_digest(signature, expected_signature)

    async def get_webhook_deliveries(self, webhook_id: int,
                                     limit: int = 50,
                                     offset: int = 0) -> List[WebhookDelivery]:
        """
        获取Webhook投递记录
        
        Args:
            webhook_id: Webhook ID
            limit: 返回数量限制
            offset: 偏移量
            
        Returns:
            投递记录列表
        """
        result = await self.db.execute(
            select(WebhookDelivery)
            .where(WebhookDelivery.webhook == webhook_id)
            .order_by(WebhookDelivery.created_at.desc())
            .offset(offset)
            .limit(limit)
        )

        return result.scalars().all()

    async def get_delivery_stats(self, webhook_id: int) -> Dict[str, Any]:
        """
        获取Webhook投递统计
        
        Args:
            webhook_id: Webhook ID
            
        Returns:
            统计信息
        """
        result = await self.db.execute(
            select(WebhookDelivery).where(WebhookDelivery.webhook == webhook_id)
        )
        deliveries = result.scalars().all()

        total = len(deliveries)
        success = sum(1 for d in deliveries if d.success)
        failed = total - success
        
        return {
            'total': total,
            'success': success,
            'failed': failed,
            'success_rate': success / total if total > 0 else 0
        }


# 常见事件类型
WEBHOOK_EVENTS = {
    'article.published': '文章发布',
    'article.updated': '文章更新',
    'article.deleted': '文章删除',
    'comment.created': '评论创建',
    'comment.approved': '评论审核通过',
    'user.registered': '用户注册',
    'user.login': '用户登录',
    'media.uploaded': '媒体上传',
    'order.created': '订单创建',
    'order.completed': '订单完成',
    '*': '所有事件',
}
