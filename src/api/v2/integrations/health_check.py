"""
集成健康检查 API - 检查所有集成的连接状态
"""
from functools import wraps
from fastapi import APIRouter, Depends
from src.api.v2._helpers import ok, fail
from src.auth import jwt_required_dependency as jwt_required


def _catch(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try: return await func(*args, **kwargs)
        except Exception as e: return fail(str(e))
    return wrapper


router = APIRouter(tags=["integration-health"])

INTEGRATIONS = {
    "ai": {"name": "AI 服务", "type": "external", "needs_config": True, "config_key": "OPENAI_API_KEY"},
    "meilisearch": {"name": "Meilisearch 搜索", "type": "internal", "needs_config": False},
    "redis": {"name": "Redis 缓存", "type": "internal", "needs_config": False},
    "ipfs": {"name": "IPFS 存储", "type": "external", "needs_config": True, "config_key": "IPFS_API_ENDPOINT"},
    "email": {"name": "邮件服务", "type": "external", "needs_config": True, "config_key": "EMAIL_HOST"},
    "cdn": {"name": "CDN 分发", "type": "external", "needs_config": True, "config_key": "CDN_PROVIDER"},
    "oauth": {"name": "OAuth 登录", "type": "external", "needs_config": True, "config_key": "OAUTH_CLIENT_ID"},
    "nft": {"name": "NFT 集成", "type": "external", "needs_config": True, "config_key": "WEB3_PROVIDER_URL"},
}


@router.get("/status")
@_catch
async def get_integration_status(current_user=Depends(jwt_required)):
    """获取所有集成的连接状态"""
    import os
    
    results = []
    for key, info in INTEGRATIONS.items():
        config_key = info.get("config_key", "")
        is_configured = bool(os.environ.get(config_key)) if config_key else True
        
        status = "configured" if is_configured else "not_configured"
        if not info["needs_config"]:
            status = "active"
        
        results.append({
            "key": key,
            "name": info["name"],
            "type": info["type"],
            "status": status,
            "needs_config": info["needs_config"],
            "config_key": config_key if info["needs_config"] else None,
        })
    
    return ok(data={"integrations": results, "total": len(results), "configured": sum(1 for r in results if r["status"] != "not_configured")})
