"""
Webhook 管理 API 端点
"""

import secrets

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import jwt_required_dependency as jwt_required
from src.extensions import get_async_db_session as get_async_db

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.get("")
async def list_webhooks(
        current_user_id: int = Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """
    获取所有Webhook订阅
    
    Returns:
        Webhook订阅列表
    """
    try:
        from shared.services.webhook_service import webhook_service

        subscriptions = []
        for sub_id, sub in webhook_service.subscriptions.items():
            stats = webhook_service.get_subscription_stats(sub_id)
            subscriptions.append({
                'id': sub.id,
                'url': sub.url,
                'events': sub.events,
                'active': sub.active,
                'created_at': sub.created_at.isoformat() if sub.created_at else None,
                'last_delivery_at': sub.last_delivery_at.isoformat() if sub.last_delivery_at else None,
                'stats': stats,
            })

        return {
            'success': True,
            'data': subscriptions,
        }

    except Exception as e:
        import traceback
        print(f"Error listing webhooks: {str(e)}")
        print(traceback.format_exc())
        return {
            'success': False,
            'error': str(e)
        }


@router.post("")
async def create_webhook(
        request: Request,
        current_user_id: int = Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """
    创建Webhook订阅
    
    Body参数:
        url: 回调URL
        events: 事件类型列表
        secret: 签名密钥(可选,不传则自动生成)
        
    Returns:
        创建的订阅信息
    """
    try:
        from shared.services.webhook_service import WebhookSubscription, webhook_service

        body = await request.json()
        url = body.get('url')
        events = body.get('events', [])
        secret = body.get('secret', secrets.token_hex(32))

        if not url or not events:
            return {
                'success': False,
                'error': 'url and events are required',
            }

        subscription = WebhookSubscription(
            id=0,  # 将由服务分配
            url=url,
            events=events,
            secret=secret,
            active=True,
        )

        sub_id = webhook_service.register_subscription(subscription)

        return {
            'success': True,
            'data': {
                'id': sub_id,
                'url': url,
                'events': events,
                'secret': secret,  # 只在创建时返回一次
                'message': '请妥善保存secret,后续无法再次查看',
            }
        }

    except Exception as e:
        import traceback
        print(f"Error creating webhook: {str(e)}")
        print(traceback.format_exc())
        return {
            'success': False,
            'error': str(e)
        }


@router.put("/{subscription_id}")
async def update_webhook(
        subscription_id: int,
        request: Request,
        current_user_id: int = Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """
    更新Webhook订阅
    
    Args:
        subscription_id: 订阅ID
        
    Body参数:
        url: 回调URL(可选)
        events: 事件类型列表(可选)
        active: 是否激活(可选)
        
    Returns:
        更新后的订阅信息
    """
    try:
        from shared.services.webhook_service import webhook_service

        body = await request.json()

        subscription = webhook_service.subscriptions.get(subscription_id)
        if not subscription:
            return {
                'success': False,
                'error': 'Subscription not found',
            }

        # 更新字段
        if 'url' in body:
            subscription.url = body['url']
        if 'events' in body:
            subscription.events = body['events']
        if 'active' in body:
            subscription.active = body['active']

        return {
            'success': True,
            'data': {
                'id': subscription.id,
                'url': subscription.url,
                'events': subscription.events,
                'active': subscription.active,
            }
        }

    except Exception as e:
        import traceback
        print(f"Error updating webhook: {str(e)}")
        print(traceback.format_exc())
        return {
            'success': False,
            'error': str(e)
        }


@router.delete("/{subscription_id}")
async def delete_webhook(
        subscription_id: int,
        current_user_id: int = Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """
    删除Webhook订阅
    
    Args:
        subscription_id: 订阅ID
        
    Returns:
        删除结果
    """
    try:
        from shared.services.webhook_service import webhook_service

        success = webhook_service.unregister_subscription(subscription_id)

        if not success:
            return {
                'success': False,
                'error': 'Subscription not found',
            }

        return {
            'success': True,
            'data': {
                'message': 'Webhook subscription deleted',
            }
        }

    except Exception as e:
        import traceback
        print(f"Error deleting webhook: {str(e)}")
        print(traceback.format_exc())
        return {
            'success': False,
            'error': str(e)
        }


@router.get("/{subscription_id}/stats")
async def get_webhook_stats(
        subscription_id: int,
        current_user_id: int = Depends(jwt_required)
):
    """
    获取Webhook订阅统计信息
    
    Args:
        subscription_id: 订阅ID
        
    Returns:
        统计信息
    """
    try:
        from shared.services.webhook_service import webhook_service

        stats = webhook_service.get_subscription_stats(subscription_id)

        if not stats:
            return {
                'success': False,
                'error': 'Subscription not found',
            }

        return {
            'success': True,
            'data': stats,
        }

    except Exception as e:
        import traceback
        print(f"Error getting webhook stats: {str(e)}")
        print(traceback.format_exc())
        return {
            'success': False,
            'error': str(e)
        }


@router.get("/logs")
async def get_delivery_logs(
        delivery_id: str = None,
        limit: int = 100,
        current_user_id: int = Depends(jwt_required)
):
    """
    获取投递日志
    
    Args:
        delivery_id: 投递ID(可选)
        limit: 返回数量限制
        
    Returns:
        投递日志列表
    """
    try:
        from shared.services.webhook_service import webhook_service

        logs = webhook_service.get_delivery_logs(delivery_id=delivery_id, limit=limit)

        return {
            'success': True,
            'data': logs,
        }

    except Exception as e:
        import traceback
        print(f"Error getting delivery logs: {str(e)}")
        print(traceback.format_exc())
        return {
            'success': False,
            'error': str(e)
        }


@router.get("/event-types")
async def get_event_types():
    """
    获取支持的事件类型列表
    
    Returns:
        事件类型列表及说明
    """
    event_types = {
        'article.published': {
            'description': '文章发布时触发',
            'payload_example': {
                'article_id': 123,
                'title': '文章标题',
                'slug': 'article-slug',
                'author_id': 1,
            }
        },
        'article.updated': {
            'description': '文章更新时触发',
            'payload_example': {
                'article_id': 123,
                'title': '文章标题',
                'updated_fields': ['title', 'content'],
            }
        },
        'article.deleted': {
            'description': '文章删除时触发',
            'payload_example': {
                'article_id': 123,
                'title': '文章标题',
            }
        },
        'comment.created': {
            'description': '评论创建时触发',
            'payload_example': {
                'comment_id': 456,
                'article_id': 123,
                'author_id': 2,
                'content': '评论内容',
            }
        },
        'user.registered': {
            'description': '用户注册时触发',
            'payload_example': {
                'user_id': 789,
                'username': '用户名',
                'email': 'user@example.com',
            }
        },
        'media.uploaded': {
            'description': '媒体文件上传时触发',
            'payload_example': {
                'media_id': 101,
                'filename': 'image.jpg',
                'file_type': 'image/jpeg',
                'file_size': 102400,
            }
        },
    }

    return {
        'success': True,
        'data': event_types,
    }


@router.post("/test/{subscription_id}")
async def test_webhook(
        subscription_id: int,
        current_user_id: int = Depends(jwt_required)
):
    """
    测试Webhook订阅
    
    Args:
        subscription_id: 订阅ID
        
    Returns:
        测试结果
    """
    try:
        from shared.services.webhook_service import webhook_service

        subscription = webhook_service.subscriptions.get(subscription_id)
        if not subscription:
            return {
                'success': False,
                'error': 'Subscription not found',
            }

        # 触发测试事件
        delivery_id = webhook_service.trigger_event(
            'webhook.test',
            {
                'message': 'This is a test webhook',
                'timestamp': 'now',
            }
        )

        return {
            'success': True,
            'data': {
                'delivery_id': delivery_id,
                'message': 'Test webhook triggered. Check delivery logs for results.',
            }
        }

    except Exception as e:
        import traceback
        print(f"Error testing webhook: {str(e)}")
        print(traceback.format_exc())
        return {
            'success': False,
            'error': str(e)
        }
