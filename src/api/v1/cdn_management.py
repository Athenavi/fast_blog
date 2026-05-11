"""
CDN集成 API

提供CDN配置、缓存管理、统计查询等功能
"""

from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, Body

from shared.services.cdn_integration import cdn_service
from src.api.v1.responses import ApiResponse
from src.auth.auth_deps import jwt_required_dependency as jwt_required

router = APIRouter()


@router.post("/configure/cloudflare", summary="配置Cloudflare", description="配置Cloudflare CDN")
async def configure_cloudflare(
        api_token: str = Body(..., description="Cloudflare API Token"),
        zone_id: str = Body(..., description="Zone ID"),
        domain: str = Body(..., description="域名"),
        enable_cache: bool = Body(True, description="启用缓存"),
        enable_minification: bool = Body(True, description="启用代码压缩"),
        enable_brotli: bool = Body(True, description="启用Brotli压缩"),
        cache_ttl: int = Body(86400, description="缓存TTL（秒）"),
        current_user=Depends(jwt_required),
):
    """配置Cloudflare"""
    # 检查权限
    is_admin = getattr(current_user, 'is_superuser', False) or getattr(current_user, 'is_staff', False)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Permission denied")

    result = cdn_service.configure_cloudflare(
        api_token=api_token,
        zone_id=zone_id,
        domain=domain,
        enable_cache=enable_cache,
        enable_minification=enable_minification,
        enable_brotli=enable_brotli,
        cache_ttl=cache_ttl,
    )

    return ApiResponse(
        success=result['success'],
        message=result.get('message'),
        data=result.get('config')
    )


@router.post("/configure/aws-cloudfront", summary="配置AWS CloudFront", description="配置AWS CloudFront CDN")
async def configure_aws_cloudfront(
        access_key_id: str = Body(..., description="AWS Access Key ID"),
        secret_access_key: str = Body(..., description="AWS Secret Access Key"),
        distribution_id: str = Body(..., description="Distribution ID"),
        domain: str = Body(..., description="CDN域名"),
        origin_domain: str = Body(..., description="源站域名"),
        enable_compression: bool = Body(True, description="启用压缩"),
        cache_ttl: int = Body(86400, description="缓存TTL（秒）"),
        current_user=Depends(jwt_required),
):
    """配置AWS CloudFront"""
    # 检查权限
    is_admin = getattr(current_user, 'is_superuser', False) or getattr(current_user, 'is_staff', False)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Permission denied")

    result = cdn_service.configure_aws_cloudfront(
        access_key_id=access_key_id,
        secret_access_key=secret_access_key,
        distribution_id=distribution_id,
        domain=domain,
        origin_domain=origin_domain,
        enable_compression=enable_compression,
        cache_ttl=cache_ttl,
    )

    return ApiResponse(
        success=result['success'],
        message=result.get('message'),
        data=result.get('config')
    )


@router.post("/configure/aliyun", summary="配置阿里云CDN", description="配置阿里云CDN")
async def configure_aliyun_cdn(
        access_key_id: str = Body(..., description="阿里云Access Key ID"),
        access_key_secret: str = Body(..., description="阿里云Access Key Secret"),
        domain: str = Body(..., description="CDN域名"),
        source_domain: str = Body(..., description="源站域名"),
        enable_https: bool = Body(True, description="启用HTTPS"),
        cache_ttl: int = Body(86400, description="缓存TTL（秒）"),
        current_user=Depends(jwt_required),
):
    """配置阿里云CDN"""
    # 检查权限
    is_admin = getattr(current_user, 'is_superuser', False) or getattr(current_user, 'is_staff', False)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Permission denied")

    result = cdn_service.configure_aliyun_cdn(
        access_key_id=access_key_id,
        access_key_secret=access_key_secret,
        domain=domain,
        source_domain=source_domain,
        enable_https=enable_https,
        cache_ttl=cache_ttl,
    )

    return ApiResponse(
        success=result['success'],
        message=result.get('message'),
        data=result.get('config')
    )


@router.post("/configure/custom", summary="配置自定义CDN", description="配置自定义CDN")
async def configure_custom_cdn(
        name: str = Body(..., description="CDN名称"),
        cdn_url: str = Body(..., description="CDN URL"),
        api_endpoint: Optional[str] = Body(None, description="API端点"),
        api_key: Optional[str] = Body(None, description="API密钥"),
        settings: Optional[dict] = Body(None, description="自定义设置"),
        current_user=Depends(jwt_required),
):
    """配置自定义CDN"""
    # 检查权限
    is_admin = getattr(current_user, 'is_superuser', False) or getattr(current_user, 'is_staff', False)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Permission denied")

    result = cdn_service.configure_custom_cdn(
        name=name,
        cdn_url=cdn_url,
        api_endpoint=api_endpoint,
        api_key=api_key,
        settings=settings,
    )

    return ApiResponse(
        success=result['success'],
        message=result.get('message'),
        data=result.get('config')
    )


@router.get("/config", summary="获取配置", description="获取CDN配置")
async def get_cdn_config(
        provider: Optional[str] = Query(None, description="CDN提供商"),
        current_user=Depends(jwt_required),
):
    """获取配置"""
    # 检查权限
    is_admin = getattr(current_user, 'is_superuser', False) or getattr(current_user, 'is_staff', False)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Permission denied")

    result = cdn_service.get_cdn_config(provider=provider)

    return ApiResponse(
        success=result['success'],
        data=result.get('config') or result.get('configs')
    )


@router.post("/purge-cache", summary="清除缓存", description="清除CDN缓存")
async def purge_cache(
        provider: str = Body(..., description="CDN提供商"),
        urls: Optional[List[str]] = Body(None, description="要清除的URL列表"),
        purge_all: bool = Body(False, description="是否清除所有缓存"),
        current_user=Depends(jwt_required),
):
    """清除缓存"""
    # 检查权限
    is_admin = getattr(current_user, 'is_superuser', False) or getattr(current_user, 'is_staff', False)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Permission denied")

    result = cdn_service.purge_cache(
        provider=provider,
        urls=urls,
        purge_all=purge_all,
    )

    return ApiResponse(
        success=result['success'],
        message=result.get('message'),
        data=result
    )


@router.get("/stats", summary="获取统计", description="获取CDN统计信息")
async def get_cdn_stats(
        provider: str = Query(..., description="CDN提供商"),
        hours: int = Query(24, ge=1, le=168, description="统计最近多少小时"),
        current_user=Depends(jwt_required),
):
    """获取统计"""
    # 检查权限
    is_admin = getattr(current_user, 'is_superuser', False) or getattr(current_user, 'is_staff', False)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Permission denied")

    result = cdn_service.get_cdn_stats(provider=provider, hours=hours)

    return ApiResponse(
        success=result['success'],
        data=result.get('stats')
    )


@router.get("/integration-code", summary="集成代码", description="获取CDN集成代码示例")
async def get_integration_code(
        provider: str = Query(..., description="CDN提供商"),
        framework: str = Query('html', pattern='^(html|react|vue|django)$', description="框架类型"),
        current_user=Depends(jwt_required),
):
    """获取集成代码"""
    code = cdn_service.generate_integration_code(provider=provider, framework=framework)

    return ApiResponse(
        success=True,
        data={
            'provider': provider,
            'framework': framework,
            'code': code,
        }
    )


@router.get("/providers", summary="支持的提供商", description="获取支持的CDN提供商列表")
async def get_supported_providers():
    """获取支持的提供商"""
    providers = {
        'cloudflare': {
            'name': 'Cloudflare',
            'description': '全球领先的CDN和安全服务提供商',
            'features': [
                '全球200+数据中心',
                '自动SSL/TLS',
                'DDoS保护',
                '代码压缩',
                '图片优化',
            ],
            'pricing': '免费套餐可用，付费套餐从$20/月起',
            'website': 'https://www.cloudflare.com',
        },
        'aws_cloudfront': {
            'name': 'AWS CloudFront',
            'description': '亚马逊AWS的内容分发网络',
            'features': [
                '与AWS服务深度集成',
                '全球边缘位置',
                '按需定价',
                '实时日志',
                'Lambda@Edge',
            ],
            'pricing': '按使用量付费，前10TB $0.085/GB',
            'website': 'https://aws.amazon.com/cloudfront/',
        },
        'aliyun_cdn': {
            'name': '阿里云CDN',
            'description': '阿里巴巴云的CDN服务',
            'features': [
                '中国大陆优化',
                '智能路由',
                'HTTPS加速',
                '视频点播加速',
                '动态加速',
            ],
            'pricing': '按流量计费，约¥0.24/GB',
            'website': 'https://www.aliyun.com/product/cdn',
        },
        'tencent_cdn': {
            'name': '腾讯云CDN',
            'description': '腾讯云的CDN服务',
            'features': [
                '中国大陆覆盖',
                '游戏加速',
                '直播加速',
                '安全防护',
                '智能调度',
            ],
            'pricing': '按流量计费，约¥0.28/GB',
            'website': 'https://cloud.tencent.com/product/cdn',
        },
        'custom': {
            'name': '自定义CDN',
            'description': '支持其他CDN提供商或自建CDN',
            'features': [
                '灵活配置',
                '自定义API集成',
                '适配任何CDN',
            ],
            'pricing': '取决于具体提供商',
            'website': '',
        },
    }

    return ApiResponse(
        success=True,
        data=providers
    )


@router.get("/examples", summary="使用示例", description="获取CDN集成使用示例")
async def get_usage_examples():
    """获取使用示例"""
    examples = {
        "configuration_flow": {
            'description': '配置流程',
            'steps': [
                '1. 选择CDN提供商并注册账号',
                '2. 添加域名并配置DNS',
                '3. 在系统中配置CDN参数',
                '4. 更新资源URL为CDN URL',
                '5. 测试CDN是否正常工作',
                '6. 监控CDN性能和成本',
            ]
        },
        "best_practices": {
            'description': '最佳实践',
            'practices': [
                '使用CDN分发静态资源（CSS、JS、图片）',
                '设置合理的缓存策略',
                '启用HTTPS确保安全',
                '定期清除过时资源的缓存',
                '监控CDN命中率和带宽使用',
                '使用版本化URL管理缓存失效',
                '考虑多CDN策略提高可靠性',
                '评估成本和性能平衡',
            ]
        },
        "cache_strategy": {
            'description': '缓存策略建议',
            'strategies': {
                'static_assets': {
                    'files': ['CSS', 'JS', '字体', '图标'],
                    'ttl': '1年（31536000秒）',
                    'note': '使用版本化URL，文件名包含哈希值',
                },
                'images': {
                    'files': ['图片', '缩略图'],
                    'ttl': '1个月（2592000秒）',
                    'note': '根据更新频率调整',
                },
                'dynamic_content': {
                    'files': ['API响应', '动态页面'],
                    'ttl': '几分钟到几小时',
                    'note': '根据内容更新频率设置',
                },
            }
        }
    }

    return ApiResponse(
        success=True,
        data=examples
    )
