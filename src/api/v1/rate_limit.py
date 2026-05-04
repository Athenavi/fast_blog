"""
速率限制管理 API

提供速率限制的配置和监控功能
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Body

from shared.services.rate_limiter import rate_limiter
from src.api.v1.responses import ApiResponse
from src.auth.auth_deps import jwt_required_dependency as jwt_required

router = APIRouter()


@router.get("/config", summary="获取配置", description="获取当前速率限制配置")
async def get_config(
        current_user=Depends(jwt_required),
):
    """获取配置"""
    # 检查权限
    is_admin = getattr(current_user, 'is_superuser', False) or getattr(current_user, 'is_staff', False)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Permission denied")

    config = {
        'default': rate_limiter.default_config,
        'endpoints': rate_limiter.endpoint_configs,
    }

    return ApiResponse(
        success=True,
        data=config
    )


@router.post("/config/endpoint", summary="配置端点限制", description="为特定端点配置速率限制")
async def configure_endpoint(
        endpoint: str = Body(..., description="API端点路径"),
        user_rate: Optional[float] = Body(None, description="用户速率限制（每秒请求数）"),
        user_capacity: Optional[int] = Body(None, description="用户桶容量"),
        ip_rate: Optional[float] = Body(None, description="IP速率限制（每秒请求数）"),
        ip_capacity: Optional[int] = Body(None, description="IP桶容量"),
        current_user=Depends(jwt_required),
):
    """配置端点限制"""
    # 检查权限
    is_admin = getattr(current_user, 'is_superuser', False) or getattr(current_user, 'is_staff', False)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Permission denied")

    rate_limiter.configure_endpoint(
        endpoint=endpoint,
        user_rate=user_rate,
        user_capacity=user_capacity,
        ip_rate=ip_rate,
        ip_capacity=ip_capacity,
    )

    return ApiResponse(
        success=True,
        message=f"Endpoint '{endpoint}' configured"
    )


@router.get("/usage/user/{user_id}", summary="获取用户使用情况", description="获取用户的速率限制使用情况")
async def get_user_usage(
        user_id: int,
        current_user=Depends(jwt_required),
):
    """获取用户使用情况"""
    # 检查权限
    is_admin = getattr(current_user, 'is_superuser', False) or getattr(current_user, 'is_staff', False)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Permission denied")

    usage = rate_limiter.get_user_usage(user_id)

    return ApiResponse(
        success=True,
        data=usage
    )


@router.get("/usage/ip/{ip_address}", summary="获取IP使用情况", description="获取IP的速率限制使用情况")
async def get_ip_usage(
        ip_address: str,
        current_user=Depends(jwt_required),
):
    """获取IP使用情况"""
    # 检查权限
    is_admin = getattr(current_user, 'is_superuser', False) or getattr(current_user, 'is_staff', False)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Permission denied")

    usage = rate_limiter.get_ip_usage(ip_address)

    return ApiResponse(
        success=True,
        data=usage
    )


@router.post("/reset/user/{user_id}", summary="重置用户限制", description="重置用户的速率限制")
async def reset_user_limit(
        user_id: int,
        current_user=Depends(jwt_required),
):
    """重置用户限制"""
    # 检查权限
    is_admin = getattr(current_user, 'is_superuser', False) or getattr(current_user, 'is_staff', False)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Permission denied")

    rate_limiter.reset_user_limit(user_id)

    return ApiResponse(
        success=True,
        message=f"User {user_id} rate limit reset"
    )


@router.post("/reset/ip/{ip_address}", summary="重置IP限制", description="重置IP的速率限制")
async def reset_ip_limit(
        ip_address: str,
        current_user=Depends(jwt_required),
):
    """重置IP限制"""
    # 检查权限
    is_admin = getattr(current_user, 'is_superuser', False) or getattr(current_user, 'is_staff', False)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Permission denied")

    rate_limiter.reset_ip_limit(ip_address)

    return ApiResponse(
        success=True,
        message=f"IP {ip_address} rate limit reset"
    )


@router.post("/cleanup", summary="清理过期数据", description="清理过期的速率限制桶")
async def cleanup_expired(
        max_age: int = Body(3600, ge=60, le=86400, description="最大年龄（秒）"),
        current_user=Depends(jwt_required),
):
    """清理过期数据"""
    # 检查权限
    is_admin = getattr(current_user, 'is_superuser', False) or getattr(current_user, 'is_staff', False)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Permission denied")

    rate_limiter.cleanup_expired_buckets(max_age=max_age)

    return ApiResponse(
        success=True,
        message=f"Cleaned up buckets older than {max_age} seconds"
    )


@router.get("/examples", summary="使用示例", description="获取速率限制使用示例")
async def get_usage_examples():
    """获取使用示例"""
    examples = {
        "default_limits": {
            'description': '默认限制',
            'limits': {
                'user': '10 requests/second, capacity 100',
                'ip': '5 requests/second, capacity 50',
                'global': '100 requests/second, capacity 1000',
            }
        },
        "custom_endpoint": {
            'description': '自定义端点限制',
            'example': '''
# 为登录接口设置更严格的限制
POST /api/v1/rate-limit/config/endpoint
{
  "endpoint": "/api/v1/auth/login",
  "user_rate": 2,
  "user_capacity": 10,
  "ip_rate": 1,
  "ip_capacity": 5
}

# 为搜索接口设置宽松的限制
POST /api/v1/rate-limit/config/endpoint
{
  "endpoint": "/api/v1/search",
  "user_rate": 20,
  "user_capacity": 200,
  "ip_rate": 10,
  "ip_capacity": 100
}
            '''.strip()
        },
        "response_headers": {
            'description': '响应头信息',
            'headers': {
                'X-RateLimit-Limit': '总请求数限制',
                'X-RateLimit-Remaining': '剩余请求数',
                'X-RateLimit-Reset': '限制重置时间戳',
                'Retry-After': '重试等待时间（仅在429响应中）',
            }
        },
        "429_response": {
            'description': '429 Too Many Requests 响应',
            'example': {
                'success': False,
                'error': 'Rate limit exceeded',
                'retry_after': 5.2,
                'limit': {
                    'user': {
                        'limit': 100,
                        'remaining': 0,
                        'reset': 1234567890.0,
                    }
                }
            }
        },
        "best_practices": {
            'description': '最佳实践',
            'practices': [
                '为认证相关接口设置更严格的限制',
                '为公开API设置IP级限制',
                '为已认证用户设置用户级限制',
                '监控速率限制触发情况，调整配置',
                '定期清理过期的限制桶以释放内存',
                '在文档中明确说明速率限制策略',
            ]
        }
    }

    return ApiResponse(
        success=True,
        data=examples
    )
