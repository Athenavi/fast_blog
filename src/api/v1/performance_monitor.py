"""
性能监控 API
提供实时性能指标查询、分析和告警功能
"""

from typing import Optional

from fastapi import APIRouter, Depends

from shared.services.performance_monitor import performance_monitor
from src.api.v1.responses import ApiResponse
from src.auth.auth_deps import admin_required_api as admin_required

router = APIRouter(tags=["performance-monitoring"])


@router.get("/metrics/global")
async def get_global_metrics(current_user=Depends(admin_required)):
    """
    获取全局性能指标
    
    Returns:
        全局统计数据 (QPS、响应时间、错误率等)
    """
    try:
        stats = performance_monitor.get_global_stats()

        return ApiResponse(
            success=True,
            data={
                'global': stats,
            }
        )
    except Exception as e:
        return ApiResponse(success=False, error=str(e))


@router.get("/metrics/endpoints")
async def get_endpoint_metrics(
        endpoint: Optional[str] = None,
        current_user=Depends(admin_required)
):
    """
    获取端点性能指标
    
    Args:
        endpoint: 可选，指定端点路径
        
    Returns:
        端点性能统计
    """
    try:
        if endpoint:
            stats = performance_monitor.get_endpoint_stats(endpoint)
            return ApiResponse(success=True, data={'endpoint': stats})
        else:
            stats = performance_monitor.get_all_endpoints_stats()
            return ApiResponse(success=True, data={'endpoints': stats})
    except Exception as e:
        return ApiResponse(success=False, error=str(e))


@router.get("/metrics/database")
async def get_database_metrics(current_user=Depends(admin_required)):
    """
    获取数据库性能指标
    
    Returns:
        数据库查询统计 (慢查询、执行时间等)
    """
    try:
        stats = performance_monitor.get_db_query_stats()

        return ApiResponse(
            success=True,
            data={
                'database': stats,
            }
        )
    except Exception as e:
        return ApiResponse(success=False, error=str(e))


@router.get("/metrics/system")
async def get_system_metrics(current_user=Depends(admin_required)):
    """
    获取系统资源指标
    
    Returns:
        系统资源使用情况 (CPU、内存、磁盘等)
    """
    try:
        # 先记录当前系统状态
        performance_monitor.record_system_metrics()

        stats = performance_monitor.get_system_stats()

        return ApiResponse(
            success=True,
            data={
                'system': stats,
            }
        )
    except Exception as e:
        return ApiResponse(success=False, error=str(e))


@router.get("/metrics/alerts")
async def get_performance_alerts(
        limit: int = 10,
        current_user=Depends(admin_required)
):
    """
    获取性能告警
    
    Args:
        limit: 返回告警数量限制
        
    Returns:
        最近的性能告警列表
    """
    try:
        # 检查新的告警
        new_alerts = performance_monitor.check_alerts()

        # 获取历史告警
        recent_alerts = performance_monitor.get_recent_alerts(limit)

        return ApiResponse(
            success=True,
            data={
                'alerts': recent_alerts,
                'new_alerts_count': len(new_alerts),
            }
        )
    except Exception as e:
        return ApiResponse(success=False, error=str(e))


@router.get("/metrics/report")
async def get_performance_report(current_user=Depends(admin_required)):
    """
    生成综合性能报告
    
    Returns:
        完整的性能分析报告，包含优化建议
    """
    try:
        report = performance_monitor.generate_report()

        return ApiResponse(
            success=True,
            data={
                'report': report,
            }
        )
    except Exception as e:
        return ApiResponse(success=False, error=str(e))


@router.post("/metrics/reset")
async def reset_performance_metrics(current_user=Depends(admin_required)):
    """
    重置性能监控数据
    
    Note: 仅管理员可用，谨慎使用
    """
    try:
        performance_monitor.reset()

        return ApiResponse(
            success=True,
            message="性能监控数据已重置"
        )
    except Exception as e:
        return ApiResponse(success=False, error=str(e))


@router.get("/metrics/config")
async def get_monitoring_config(current_user=Depends(admin_required)):
    """
    获取监控配置
    
    Returns:
        当前监控配置和阈值设置
    """
    try:
        config = {
            'window_size': performance_monitor.window_size,
            'slow_query_threshold': performance_monitor.slow_query_threshold,
            'alert_thresholds': performance_monitor.alert_thresholds,
        }

        return ApiResponse(
            success=True,
            data={
                'config': config,
            }
        )
    except Exception as e:
        return ApiResponse(success=False, error=str(e))


@router.post("/metrics/config/thresholds")
async def update_alert_thresholds(
        thresholds: dict,
        current_user=Depends(admin_required)
):
    """
    更新告警阈值配置
    
    Args:
        thresholds: 阈值配置字典
        
    Example:
        {
            "response_time_p95": 2.0,
            "error_rate": 0.05,
            "cpu_usage": 80.0,
            "memory_usage": 85.0
        }
    """
    try:
        valid_keys = [
            'response_time_p95',
            'error_rate',
            'slow_query_count',
            'cpu_usage',
            'memory_usage'
        ]

        for key, value in thresholds.items():
            if key in valid_keys:
                performance_monitor.alert_thresholds[key] = value

        return ApiResponse(
            success=True,
            message="告警阈值已更新",
            data={
                'thresholds': performance_monitor.alert_thresholds,
            }
        )
    except Exception as e:
        return ApiResponse(success=False, error=str(e))
