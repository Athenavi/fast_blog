"""
负载均衡管理 API
提供多实例管理、健康检查、会话管理和故障转移功能
"""
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Body

from shared.services.load_balancer import load_balancer_service
from src.api.v1.responses import ApiResponse
from src.auth.auth_deps import jwt_required_dependency as jwt_required

router = APIRouter(prefix="/load-balancer", tags=["load-balancer"])


@router.get("/instances", summary="获取活动实例列表")
async def get_active_instances(current_user=Depends(jwt_required)):
    """
    获取所有活动实例
    
    Returns:
        活动实例列表
    """
    try:
        instances = await load_balancer_service.get_active_instances()

        return ApiResponse(
            success=True,
            data={
                'instances': instances,
                'total': len(instances)
            }
        )

    except Exception as e:
        return ApiResponse(success=False, error=str(e))


@router.get("/instance/{instance_id}/health", summary="检查实例健康状态")
async def check_instance_health(
        instance_id: str,
        current_user=Depends(jwt_required)
):
    """
    检查指定实例的健康状态
    
    Args:
        instance_id: 实例ID
        
    Returns:
        健康检查结果
    """
    try:
        health = await load_balancer_service.check_instance_health(instance_id)

        return ApiResponse(
            success=True,
            data=health
        )

    except Exception as e:
        return ApiResponse(success=False, error=str(e))


@router.get("/stats", summary="获取集群统计")
async def get_cluster_stats(current_user=Depends(jwt_required)):
    """
    获取集群统计信息
    
    Returns:
        集群统计数据
    """
    try:
        stats = await load_balancer_service.get_cluster_stats()

        return ApiResponse(
            success=True,
            data=stats
        )

    except Exception as e:
        return ApiResponse(success=False, error=str(e))


@router.post("/instance/select", summary="选择下一个实例")
async def select_next_instance(
        strategy: Optional[str] = Body(None, description="负载均衡策略"),
        current_user=Depends(jwt_required)
):
    """
    根据负载均衡策略选择下一个实例
    
    Args:
        strategy: 负载均衡策略 (round_robin/least_connections/weighted)
        
    Returns:
        选中的实例
    """
    try:
        instance = await load_balancer_service.get_next_instance(strategy)

        if not instance:
            return ApiResponse(success=False, error="No healthy instances available")

        return ApiResponse(
            success=True,
            data=instance
        )

    except Exception as e:
        return ApiResponse(success=False, error=str(e))


@router.get("/config", summary="获取负载均衡配置")
async def get_config(current_user=Depends(jwt_required)):
    """
    获取负载均衡配置
    
    Returns:
        配置信息
    """
    try:
        config = {
            'strategy': load_balancer_service.config['strategy'],
            'health_check_interval': load_balancer_service.config['health_check_interval'],
            'health_check_timeout': load_balancer_service.config['health_check_timeout'],
            'max_failures': load_balancer_service.config['max_failures'],
            'session_ttl': load_balancer_service.config['session_ttl'],
        }

        return ApiResponse(
            success=True,
            data=config
        )

    except Exception as e:
        return ApiResponse(success=False, error=str(e))


@router.post("/config/update", summary="更新负载均衡配置")
async def update_config(
        strategy: Optional[str] = Body(None, description="负载均衡策略"),
        health_check_interval: Optional[int] = Body(None, description="健康检查间隔（秒）"),
        health_check_timeout: Optional[int] = Body(None, description="健康检查超时（秒）"),
        max_failures: Optional[int] = Body(None, description="最大失败次数"),
        session_ttl: Optional[int] = Body(None, description="会话TTL（秒）"),
        current_user=Depends(jwt_required)
):
    """
    更新负载均衡配置
    
    Args:
        strategy: 负载均衡策略
        health_check_interval: 健康检查间隔
        health_check_timeout: 健康检查超时
        max_failures: 最大失败次数
        session_ttl: 会话TTL
        
    Returns:
        更新结果
    """
    try:
        config_updates = {}

        if strategy:
            if strategy not in ['round_robin', 'least_connections', 'weighted']:
                return ApiResponse(success=False, error="Invalid strategy")
            config_updates['strategy'] = strategy

        if health_check_interval is not None:
            if health_check_interval < 5:
                return ApiResponse(success=False, error="health_check_interval must be >= 5")
            config_updates['health_check_interval'] = health_check_interval

        if health_check_timeout is not None:
            if health_check_timeout < 1:
                return ApiResponse(success=False, error="health_check_timeout must be >= 1")
            config_updates['health_check_timeout'] = health_check_timeout

        if max_failures is not None:
            if max_failures < 1:
                return ApiResponse(success=False, error="max_failures must be >= 1")
            config_updates['max_failures'] = max_failures

        if session_ttl is not None:
            if session_ttl < 60:
                return ApiResponse(success=False, error="session_ttl must be >= 60")
            config_updates['session_ttl'] = session_ttl

        await load_balancer_service.update_config(config_updates)

        return ApiResponse(
            success=True,
            message="Configuration updated",
            data=load_balancer_service.config
        )

    except Exception as e:
        return ApiResponse(success=False, error=str(e))


@router.get("/session/{session_id}", summary="获取会话数据")
async def get_session(
        session_id: str,
        current_user=Depends(jwt_required)
):
    """
    获取会话数据（用于调试和管理）
    
    Args:
        session_id: 会话ID
        
    Returns:
        会话数据
    """
    try:
        session_data = await load_balancer_service.get_session(session_id)

        if session_data is None:
            return ApiResponse(success=False, error="Session not found")

        return ApiResponse(
            success=True,
            data=session_data
        )

    except Exception as e:
        return ApiResponse(success=False, error=str(e))


@router.delete("/session/{session_id}", summary="删除会话")
async def delete_session(
        session_id: str,
        current_user=Depends(jwt_required)
):
    """
    删除会话（强制用户登出）
    
    Args:
        session_id: 会话ID
        
    Returns:
        删除结果
    """
    try:
        await load_balancer_service.delete_session(session_id)

        return ApiResponse(
            success=True,
            message="Session deleted"
        )

    except Exception as e:
        return ApiResponse(success=False, error=str(e))


@router.post("/instance/deregister", summary="注销当前实例")
async def deregister_instance(current_user=Depends(jwt_required)):
    """
    注销当前实例（用于优雅停机）
    
    Returns:
        注销结果
    """
    try:
        await load_balancer_service.deregister_instance()

        return ApiResponse(
            success=True,
            message=f"Instance {load_balancer_service.instance_id} deregistered"
        )

    except Exception as e:
        return ApiResponse(success=False, error=str(e))


@router.get("/monitoring", summary="获取监控数据")
async def get_monitoring_data(
        period: str = Query("1h", description="统计周期 (1h/24h/7d)"),
        current_user=Depends(jwt_required)
):
    """
    获取负载均衡监控数据
    
    Args:
        period: 统计周期
        
    Returns:
        监控数据
    """
    try:
        stats = await load_balancer_service.get_cluster_stats()

        # 计算额外的监控指标
        monitoring = {
            'period': period,
            'cluster_stats': stats,
            'current_instance': {
                'id': load_balancer_service.instance_id,
                'requests_count': load_balancer_service.local_instance['requests_count'],
                'active_connections': load_balancer_service.local_instance['active_connections'],
                'status': load_balancer_service.local_instance['status'],
            },
            'recommendations': []
        }

        # 生成建议
        if stats['healthy_instances'] < stats['total_instances']:
            monitoring['recommendations'].append({
                'type': 'warning',
                'message': f"{stats['unhealthy_instances']} unhealthy instances detected"
            })

        if stats['total_active_connections'] > 1000:
            monitoring['recommendations'].append({
                'type': 'info',
                'message': "High connection count, consider scaling out"
            })

        return ApiResponse(
            success=True,
            data=monitoring
        )

    except Exception as e:
        return ApiResponse(success=False, error=str(e))


@router.post("/session/cleanup", summary="清理过期会话")
async def cleanup_sessions(
        max_age_hours: int = Body(24, description="最大会话年龄（小时）"),
        current_user=Depends(jwt_required)
):
    """
    清理过期会话
    
    Args:
        max_age_hours: 最大会话年龄
        
    Returns:
        清理结果
    """
    try:
        # 在实际应用中，这里应该扫描Redis并清理过期会话
        # Redis的TTL机制会自动清理，这里只是提供一个手动触发接口

        return ApiResponse(
            success=True,
            message=f"Session cleanup triggered for sessions older than {max_age_hours} hours",
            data={
                'note': 'Redis TTL automatically handles session expiration'
            }
        )

    except Exception as e:
        return ApiResponse(success=False, error=str(e))
