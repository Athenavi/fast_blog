"""
安全事件告警 API

提供告警配置、发送和查看功能
"""

from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, Body

from shared.services.security.security_alert import security_alert_service, EmailAlertChannel, \
    WebhookAlertChannel
from api.v1.core.responses import ApiResponse
from src.auth.auth_deps import jwt_required_dependency as jwt_required

router = APIRouter()


@router.post("/send", summary="发送告警", description="手动发送安全告警")
async def send_alert(
        alert_type: str = Body(..., description="告警类型"),
        title: str = Body(..., description="标题"),
        message: str = Body(..., description="消息内容"),
        severity: str = Body('medium', description="严重程度 (low, medium, high, critical)"),
        details: Optional[dict] = Body(None, description="详细信息"),
        force_send: bool = Body(False, description="强制发送（忽略频率限制）"),
        current_user=Depends(jwt_required),
):
    """发送告警"""
    # 检查权限
    is_admin = getattr(current_user, 'is_superuser', False) or getattr(current_user, 'is_staff', False)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Permission denied")

    result = await security_alert_service.send_alert(
        alert_type=alert_type,
        title=title,
        message=message,
        severity=severity,
        details=details,
        force_send=force_send,
    )

    return ApiResponse(
        success=result['success'],
        data=result
    )


@router.get("/history", summary="获取告警历史", description="获取告警历史记录")
async def get_alert_history(
        hours: int = Query(24, ge=1, le=168, description="最近多少小时"),
        alert_type: Optional[str] = Query(None, description="告警类型过滤"),
        severity: Optional[str] = Query(None, description="严重程度过滤"),
        current_user=Depends(jwt_required),
):
    """获取告警历史"""
    # 检查权限
    is_admin = getattr(current_user, 'is_superuser', False) or getattr(current_user, 'is_staff', False)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Permission denied")

    history = security_alert_service.get_alert_history(
        hours=hours,
        alert_type=alert_type,
        severity=severity,
    )

    return ApiResponse(
        success=True,
        data={
            'alerts': history,
            'count': len(history),
        }
    )


@router.get("/statistics", summary="获取统计信息", description="获取告警统计信息")
async def get_statistics(
        hours: int = Query(24, ge=1, le=168, description="统计最近多少小时"),
        current_user=Depends(jwt_required),
):
    """获取统计信息"""
    # 检查权限
    is_admin = getattr(current_user, 'is_superuser', False) or getattr(current_user, 'is_staff', False)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Permission denied")

    stats = security_alert_service.get_statistics(hours=hours)

    return ApiResponse(
        success=True,
        data=stats
    )


@router.post("/channel/email", summary="添加邮件渠道", description="添加邮件告警渠道")
async def add_email_channel(
        channel_id: str = Body(..., description="渠道ID"),
        smtp_server: str = Body(..., description="SMTP服务器"),
        smtp_port: int = Body(587, description="SMTP端口"),
        username: str = Body(..., description="用户名"),
        password: str = Body(..., description="密码"),
        from_email: str = Body(..., description="发件人邮箱"),
        to_emails: List[str] = Body(..., description="收件人邮箱列表"),
        use_tls: bool = Body(True, description="使用TLS"),
        current_user=Depends(jwt_required),
):
    """添加邮件渠道"""
    # 检查权限
    is_admin = getattr(current_user, 'is_superuser', False) or getattr(current_user, 'is_staff', False)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Permission denied")

    channel = EmailAlertChannel(
        smtp_server=smtp_server,
        smtp_port=smtp_port,
        username=username,
        password=password,
        from_email=from_email,
        to_emails=to_emails,
        use_tls=use_tls,
    )

    security_alert_service.add_channel(channel_id, channel)

    return ApiResponse(
        success=True,
        message=f"Email channel '{channel_id}' added"
    )


@router.post("/channel/webhook", summary="添加Webhook渠道", description="添加Webhook告警渠道")
async def add_webhook_channel(
        channel_id: str = Body(..., description="渠道ID"),
        webhook_url: str = Body(..., description="Webhook URL"),
        headers: Optional[dict] = Body(None, description="自定义请求头"),
        current_user=Depends(jwt_required),
):
    """添加Webhook渠道"""
    # 检查权限
    is_admin = getattr(current_user, 'is_superuser', False) or getattr(current_user, 'is_staff', False)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Permission denied")

    channel = WebhookAlertChannel(
        webhook_url=webhook_url,
        headers=headers,
    )

    security_alert_service.add_channel(channel_id, channel)

    return ApiResponse(
        success=True,
        message=f"Webhook channel '{channel_id}' added"
    )


@router.delete("/channel/{channel_id}", summary="删除告警渠道", description="删除告警渠道")
async def remove_channel(
        channel_id: str,
        current_user=Depends(jwt_required),
):
    """删除告警渠道"""
    # 检查权限
    is_admin = getattr(current_user, 'is_superuser', False) or getattr(current_user, 'is_staff', False)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Permission denied")

    security_alert_service.remove_channel(channel_id)

    return ApiResponse(
        success=True,
        message=f"Channel '{channel_id}' removed"
    )


@router.post("/rule", summary="添加告警规则", description="添加告警规则")
async def add_rule(
        rule_id: str = Body(..., description="规则ID"),
        alert_type: str = Body(..., description="告警类型"),
        severity: str = Body(..., description="严重程度"),
        channels: List[str] = Body(..., description="使用的渠道列表"),
        enabled: bool = Body(True, description="是否启用"),
        current_user=Depends(jwt_required),
):
    """添加告警规则"""
    # 检查权限
    is_admin = getattr(current_user, 'is_superuser', False) or getattr(current_user, 'is_staff', False)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Permission denied")

    security_alert_service.add_rule(
        rule_id=rule_id,
        alert_type=alert_type,
        severity=severity,
        channels=channels,
        enabled=enabled,
    )

    return ApiResponse(
        success=True,
        message=f"Rule '{rule_id}' added"
    )


@router.post("/config/rate-limit", summary="更新频率限制", description="更新告警频率限制")
async def update_rate_limit(
        minutes: int = Body(..., ge=1, le=60, description="最小间隔分钟数"),
        current_user=Depends(jwt_required),
):
    """更新频率限制"""
    # 检查权限
    is_admin = getattr(current_user, 'is_superuser', False) or getattr(current_user, 'is_staff', False)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Permission denied")

    security_alert_service.update_rate_limit(minutes)

    return ApiResponse(
        success=True,
        message=f"Rate limit updated to {minutes} minutes"
    )


@router.get("/examples", summary="使用示例", description="获取安全告警使用示例")
async def get_usage_examples():
    """获取使用示例"""
    examples = {
        "setup_email": {
            'description': '配置邮件告警',
            'code_example': '''
from shared.services.security_alert import security_alert_service, EmailAlertChannel

# 添加邮件渠道
channel = EmailAlertChannel(
    smtp_server='smtp.gmail.com',
    smtp_port=587,
    username='your-email@gmail.com',
    password='your-app-password',
    from_email='your-email@gmail.com',
    to_emails=['admin@example.com', 'security@example.com'],
    use_tls=True
)

security_alert_service.add_channel('email_primary', channel)

# 添加告警规则
security_alert_service.add_rule(
    rule_id='brute_force_email',
    alert_type='brute_force',
    severity='high',
    channels=['email_primary'],
    enabled=True
)
            '''.strip()
        },
        "setup_webhook": {
            'description': '配置Webhook告警（如Slack、钉钉）',
            'code_example': '''
from shared.services.security_alert import security_alert_service, WebhookAlertChannel

# Slack Webhook
slack_channel = WebhookAlertChannel(
    webhook_url='https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK',
    headers={'Content-Type': 'application/json'}
)

security_alert_service.add_channel('slack_security', slack_channel)

# 添加规则
security_alert_service.add_rule(
    rule_id='all_critical_slack',
    alert_type='*',  # 所有类型
    severity='critical',
    channels=['slack_security'],
    enabled=True
)
            '''.strip()
        },
        "integration_with_anomaly": {
            'description': '与异常检测集成',
            'code_example': '''
from shared.services.anomaly_detector import anomaly_detector
from shared.services.security_alert import security_alert_service

# 在检测到异常时自动发送告警
def on_anomaly_detected(anomaly):
    import asyncio
    
    asyncio.create_task(security_alert_service.send_alert(
        alert_type=anomaly['type'],
        title=anomaly['title'],
        message=anomaly['message'],
        severity=anomaly['severity'],
        details=anomaly.get('details', {})
    ))

# 注册回调
# （实际实现中需要在anomaly_detector中添加回调机制）
            '''.strip()
        },
        "best_practices": {
            'description': '最佳实践',
            'practices': [
                '为不同严重程度配置不同的告警渠道',
                'Critical级别同时发送邮件和短信',
                'High级别发送邮件和Webhook',
                'Medium级别只发送邮件',
                '设置合理的频率限制避免告警风暴',
                '定期审查告警历史，优化规则',
                '测试告警渠道确保正常工作',
            ]
        }
    }

    return ApiResponse(
        success=True,
        data=examples
    )
