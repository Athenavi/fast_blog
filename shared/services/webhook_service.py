"""
Webhook 系统
提供事件驱动的通知机制,允许外部服务订阅系统事件
"""

import asyncio
import hashlib
import hmac
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Any, Optional

import aiohttp


@dataclass
class WebhookEvent:
    """Webhook 事件"""
    event_type: str  # 事件类型,如 'article.published'
    payload: Dict[str, Any]  # 事件数据
    timestamp: datetime  # 事件时间戳
    delivery_id: str  # 投递ID(用于追踪)


@dataclass
class WebhookSubscription:
    """Webhook 订阅"""
    id: int
    url: str  # 回调URL
    events: List[str]  # 订阅的事件类型列表
    secret: str  # 签名密钥
    active: bool = True  # 是否激活
    created_at: Optional[datetime] = None
    last_delivery_at: Optional[datetime] = None
    failure_count: int = 0  # 连续失败次数


class WebhookService:
    """
    Webhook 服务
    
    功能:
    1. 事件注册和触发
    2. Webhook订阅管理
    3. 异步事件投递
    4. 重试机制
    5. 签名验证
    6. 投递日志
    """

    def __init__(self):
        # 注册的订阅
        self.subscriptions: Dict[int, WebhookSubscription] = {}

        # 事件处理器映射
        self.event_handlers: Dict[str, List] = {}

        # 投递日志
        self.delivery_logs: List[Dict[str, Any]] = []

        # 最大重试次数
        self.max_retries = 3

        # 重试间隔(秒)
        self.retry_delay = 60

    def register_subscription(self, subscription: WebhookSubscription) -> int:
        """
        注册Webhook订阅
        
        Args:
            subscription: 订阅对象
            
        Returns:
            订阅ID
        """
        sub_id = subscription.id or len(self.subscriptions) + 1
        subscription.id = sub_id
        subscription.created_at = datetime.now()
        self.subscriptions[sub_id] = subscription

        return sub_id

    def unregister_subscription(self, subscription_id: int) -> bool:
        """
        取消Webhook订阅
        
        Args:
            subscription_id: 订阅ID
            
        Returns:
            是否成功
        """
        if subscription_id in self.subscriptions:
            del self.subscriptions[subscription_id]
            return True
        return False

    def trigger_event(self, event_type: str, payload: Dict[str, Any]) -> str:
        """
        触发事件
        
        Args:
            event_type: 事件类型
            payload: 事件数据
            
        Returns:
            投递ID
        """
        import uuid

        delivery_id = str(uuid.uuid4())
        event = WebhookEvent(
            event_type=event_type,
            payload=payload,
            timestamp=datetime.now(),
            delivery_id=delivery_id,
        )

        # 异步投递 - 检查事件循环是否可用
        try:
            loop = asyncio.get_running_loop()
            asyncio.create_task(self._deliver_event(event))
        except RuntimeError:
            # 没有运行的事件循环，跳过投递
            import logging
            logger = logging.getLogger(__name__)
            logger.debug("No running event loop, skipping webhook delivery")

        return delivery_id

    async def _deliver_event(self, event: WebhookEvent):
        """
        投递事件到所有匹配的订阅
        
        Args:
            event: 事件对象
        """
        # 找到匹配该事件的订阅
        matching_subscriptions = [
            sub for sub in self.subscriptions.values()
            if sub.active and event.event_type in sub.events
        ]

        if not matching_subscriptions:
            return

        # 并行投递到所有订阅
        tasks = [
            self._deliver_to_subscription(event, sub)
            for sub in matching_subscriptions
        ]

        await asyncio.gather(*tasks, return_exceptions=True)

    async def _deliver_to_subscription(self, event: WebhookEvent, subscription: WebhookSubscription):
        """
        投递事件到单个订阅
        
        Args:
            event: 事件对象
            subscription: 订阅对象
        """
        delivery_attempt = {
            'delivery_id': event.delivery_id,
            'subscription_id': subscription.id,
            'event_type': event.event_type,
            'url': subscription.url,
            'timestamp': event.timestamp.isoformat(),
            'success': False,
            'attempts': 0,
            'error': None,
        }

        for attempt in range(1, self.max_retries + 1):
            try:
                delivery_attempt['attempts'] = attempt

                # 准备请求数据
                payload = {
                    'event': event.event_type,
                    'timestamp': event.timestamp.isoformat(),
                    'delivery_id': event.delivery_id,
                    'data': event.payload,
                }

                # 生成签名
                signature = self._generate_signature(
                    json.dumps(payload, separators=(',', ':')),
                    subscription.secret
                )

                # 发送HTTP请求
                async with aiohttp.ClientSession() as session:
                    headers = {
                        'Content-Type': 'application/json',
                        'X-Webhook-Signature': signature,
                        'X-Webhook-Event': event.event_type,
                        'X-Webhook-Delivery-ID': event.delivery_id,
                    }

                    timeout = aiohttp.ClientTimeout(total=30)
                    async with session.post(
                            subscription.url,
                            json=payload,
                            headers=headers,
                            timeout=timeout
                    ) as response:
                        if response.status == 200:
                            delivery_attempt['success'] = True
                            delivery_attempt['response_status'] = response.status
                            subscription.last_delivery_at = datetime.now()
                            subscription.failure_count = 0

                            print(f"[Webhook] Delivered {event.event_type} to {subscription.url}")
                            break
                        else:
                            delivery_attempt['error'] = f"HTTP {response.status}"
                            print(f"[Webhook] Failed to deliver: HTTP {response.status}")

            except Exception as e:
                delivery_attempt['error'] = str(e)
                print(f"[Webhook] Delivery error: {str(e)}")

            # 如果不是最后一次尝试,等待后重试
            if attempt < self.max_retries and not delivery_attempt['success']:
                await asyncio.sleep(self.retry_delay)

        # 记录投递日志
        if not delivery_attempt['success']:
            subscription.failure_count += 1

            # 如果连续失败太多,禁用订阅
            if subscription.failure_count >= 10:
                subscription.active = False
                print(f"[Webhook] Disabled subscription {subscription.id} due to too many failures")

        self.delivery_logs.append(delivery_attempt)

    def _generate_signature(self, payload: str, secret: str) -> str:
        """
        生成HMAC签名
        
        Args:
            payload: 请求体
            secret: 密钥
            
        Returns:
            HMAC SHA256签名
        """
        return hmac.new(
            secret.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

    def verify_signature(self, payload: str, signature: str, secret: str) -> bool:
        """
        验证签名
        
        Args:
            payload: 请求体
            signature: 签名
            secret: 密钥
            
        Returns:
            签名是否有效
        """
        expected_signature = self._generate_signature(payload, secret)
        return hmac.compare_digest(signature, expected_signature)

    def get_delivery_logs(self, delivery_id: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """
        获取投递日志
        
        Args:
            delivery_id: 投递ID(可选)
            limit: 返回数量限制
            
        Returns:
            投递日志列表
        """
        logs = self.delivery_logs

        if delivery_id:
            logs = [log for log in logs if log['delivery_id'] == delivery_id]

        # 按时间倒序
        logs = sorted(logs, key=lambda x: x['timestamp'], reverse=True)

        return logs[:limit]

    def get_subscription_stats(self, subscription_id: int) -> Dict[str, Any]:
        """
        获取订阅统计信息
        
        Args:
            subscription_id: 订阅ID
            
        Returns:
            统计信息
        """
        subscription = self.subscriptions.get(subscription_id)
        if not subscription:
            return {}

        # 计算统计数据
        logs = [
            log for log in self.delivery_logs
            if log['subscription_id'] == subscription_id
        ]

        total_deliveries = len(logs)
        successful_deliveries = sum(1 for log in logs if log['success'])
        failed_deliveries = total_deliveries - successful_deliveries

        return {
            'subscription_id': subscription_id,
            'url': subscription.url,
            'active': subscription.active,
            'events': subscription.events,
            'total_deliveries': total_deliveries,
            'successful_deliveries': successful_deliveries,
            'failed_deliveries': failed_deliveries,
            'failure_count': subscription.failure_count,
            'last_delivery_at': subscription.last_delivery_at.isoformat() if subscription.last_delivery_at else None,
        }


# 全局Webhook服务实例
webhook_service = WebhookService()


# 便捷函数
def trigger_webhook(event_type: str, payload: Dict[str, Any]) -> str:
    """
    触发Webhook事件(便捷函数)
    
    Args:
        event_type: 事件类型
        payload: 事件数据
        
    Returns:
        投递ID
    """
    return webhook_service.trigger_event(event_type, payload)
