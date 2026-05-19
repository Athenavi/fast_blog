"""
慢查询日志 API

提供慢查询的查看、分析和优化建议
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Body

from shared.services.performance.slow_query_logger import slow_query_logger
from src.api.v1.core.responses import ApiResponse
from src.auth.auth_deps import jwt_required_dependency as jwt_required

router = APIRouter()


@router.get("/logs", summary="获取慢查询日志", description="获取数据库慢查询列表")
async def get_slow_query_logs(
        limit: int = Query(50, ge=1, le=200, description="返回数量限制"),
        hours: int = Query(24, ge=1, le=168, description="统计最近多少小时"),
        table: Optional[str] = Query(None, description="表名过滤"),
        query_type: Optional[str] = Query(None, description="查询类型过滤"),
        current_user=Depends(jwt_required),
):
    """获取慢查询日志"""
    # 检查权限
    is_admin = getattr(current_user, 'is_superuser', False) or getattr(current_user, 'is_staff', False)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Permission denied")

    queries = slow_query_logger.get_slow_queries(
        limit=limit,
        hours=hours,
        table=table,
        query_type=query_type,
    )

    return ApiResponse(
        success=True,
        data={
            'queries': queries,
            'count': len(queries),
        }
    )


@router.get("/statistics", summary="获取统计信息", description="获取慢查询统计信息")
async def get_statistics(
        hours: int = Query(24, ge=1, le=168, description="统计最近多少小时"),
        current_user=Depends(jwt_required),
):
    """获取统计信息"""
    # 检查权限
    is_admin = getattr(current_user, 'is_superuser', False) or getattr(current_user, 'is_staff', False)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Permission denied")

    stats = slow_query_logger.get_statistics(hours=hours)

    return ApiResponse(
        success=True,
        data=stats
    )


@router.get("/suggestions", summary="获取优化建议", description="获取查询优化建议")
async def get_optimization_suggestions(
        current_user=Depends(jwt_required),
):
    """获取优化建议"""
    # 检查权限
    is_admin = getattr(current_user, 'is_superuser', False) or getattr(current_user, 'is_staff', False)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Permission denied")

    suggestions = slow_query_logger.get_optimization_suggestions()

    return ApiResponse(
        success=True,
        data={
            'suggestions': suggestions,
            'count': len(suggestions),
        }
    )


@router.post("/config", summary="更新配置", description="更新慢查询日志配置")
async def update_config(
        threshold: float = Body(..., ge=0.01, le=10.0, description="慢查询阈值(秒)"),
        current_user=Depends(jwt_required),
):
    """更新配置"""
    # 检查权限
    is_admin = getattr(current_user, 'is_superuser', False) or getattr(current_user, 'is_staff', False)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Permission denied")

    slow_query_logger.update_threshold(threshold)

    return ApiResponse(
        success=True,
        message=f"Threshold updated to {threshold}s",
        data={'threshold': threshold}
    )


@router.post("/clear", summary="清空日志", description="清空所有慢查询日志")
async def clear_logs(
        current_user=Depends(jwt_required),
):
    """清空日志"""
    # 检查权限
    is_admin = getattr(current_user, 'is_superuser', False) or getattr(current_user, 'is_staff', False)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Permission denied")

    slow_query_logger.clear_logs()

    return ApiResponse(
        success=True,
        message="All slow query logs cleared"
    )


@router.post("/record", summary="记录查询", description="手动记录查询（用于测试）")
async def record_query(
        sql: str = Body(..., description="SQL语句"),
        duration: float = Body(..., ge=0, description="执行时间(秒)"),
        table: Optional[str] = Body(None, description="表名"),
        query_type: Optional[str] = Body(None, description="查询类型"),
        current_user=Depends(jwt_required),
):
    """记录查询"""
    # 检查权限
    is_admin = getattr(current_user, 'is_superuser', False) or getattr(current_user, 'is_staff', False)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Permission denied")

    slow_query_logger.log_query(
        sql=sql,
        duration=duration,
        table=table,
        query_type=query_type,
    )

    return ApiResponse(
        success=True,
        message="Query recorded"
    )


@router.get("/examples", summary="使用示例", description="获取慢查询日志使用示例")
async def get_usage_examples():
    """获取使用示例"""
    examples = {
        "middleware_integration": {
            "description": "中间件集成 - 自动记录慢查询",
            "code": '''
from shared.services.slow_query_logger import slow_query_logger
import time

@app.middleware("http")
async def query_monitor_middleware(request: Request, call_next):
    start_time = time.time()
    
    response = await call_next(request)
    
    duration = time.time() - start_time
    
    # 如果响应时间超过阈值，记录为慢查询
    if duration > slow_query_logger.threshold:
        slow_query_logger.log_query(
            sql=f"HTTP {request.method} {request.url.path}",
            duration=duration,
            table='http_request',
            query_type='HTTP'
        )
    
    return response
            '''.strip()
        },
        "database_integration": {
            "description": "数据库集成 - 记录SQL慢查询",
            "code": '''
from shared.services.slow_query_logger import slow_query_logger
from sqlalchemy import event
from sqlalchemy.engine import Engine

# SQLAlchemy事件监听
@event.listens_for(Engine, "before_cursor_execute")
def receive_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    conn.info.setdefault('query_start_time', []).append(time.time())

@event.listens_for(Engine, "after_cursor_execute")
def receive_after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    total = time.time() - conn.info['query_start_time'].pop(-1)
    
    # 记录慢查询
    if total > slow_query_logger.threshold:
        slow_query_logger.log_query(
            sql=statement,
            duration=total,
            query_type=statement.split()[0].upper() if statement else None
        )
            '''.strip()
        },
        "analyze_and_optimize": {
            "description": "分析和优化流程",
            "steps": [
                "1. 查看慢查询日志 (/api/v1/slow-query/logs)",
                "2. 获取统计信息 (/api/v1/slow-query/statistics)",
                "3. 查看优化建议 (/api/v1/slow-query/suggestions)",
                "4. 根据建议添加索引或优化查询",
                "5. 监控优化效果",
            ]
        },
        "common_optimizations": {
            "description": "常见优化方法",
            "optimizations": [
                {
                    'problem': '全表扫描',
                    'solution': '添加WHERE条件或使用LIMIT',
                },
                {
                    'problem': '缺少索引',
                    'solution': '为WHERE和JOIN字段添加索引',
                },
                {
                    'problem': 'SELECT *',
                    'solution': '明确指定需要的列',
                },
                {
                    'problem': 'N+1查询',
                    'solution': '使用预加载或批量查询',
                },
                {
                    'problem': '重复查询',
                    'solution': '使用缓存存储查询结果',
                },
            ]
        }
    }

    return ApiResponse(
        success=True,
        data=examples
    )
