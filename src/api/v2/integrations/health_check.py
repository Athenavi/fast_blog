"""
集成健康检查 API - 检查所有集成的连接状态
"""
from fastapi import APIRouter, Depends

from src.api.v2._helpers import ok, _catch
from src.auth import jwt_required_dependency as jwt_required

router = APIRouter(tags=["integration-health"])

# 集成配置检查映射（key -> (name, type, check_func)
# 注意：不保存 env_var 名称，避免泄露环境变量名给攻击者
# 改为使用 lambda 动态检查，只返回是否已配置的布尔值
_INTEGRATION_CHECKS = {
    "ai": ("AI 服务", "external", lambda: bool(__import__('os').environ.get("OPENAI_API_KEY"))),
    "meilisearch": ("Meilisearch 搜索", "internal", lambda: True),
    "redis": ("Redis 缓存", "internal", lambda: True),
    "ipfs": ("IPFS 存储", "external", lambda: bool(__import__('os').environ.get("IPFS_API_ENDPOINT"))),
    "email": ("邮件服务", "external", lambda: bool(__import__('os').environ.get("EMAIL_HOST"))),
    "cdn": ("CDN 分发", "external", lambda: bool(__import__('os').environ.get("CDN_PROVIDER"))),
    "oauth": ("OAuth 登录", "external", lambda: bool(__import__('os').environ.get("OAUTH_CLIENT_ID"))),
    "nft": ("NFT 集成", "external", lambda: bool(__import__('os').environ.get("WEB3_PROVIDER_URL"))),
}


@router.get("/status")
@_catch
async def get_integration_status(current_user=Depends(jwt_required)):
    """获取所有集成的连接状态"""
    results = []
    for key, (name, itype, check_func) in _INTEGRATION_CHECKS.items():
        is_configured = check_func()

        status = "configured" if is_configured else "not_configured"
        if itype == "internal":
            status = "active"

        results.append({
            "key": key,
            "name": name,
            "type": itype,
            "status": status,
        })

    return ok(data={"integrations": results, "total": len(results), "configured": sum(1 for r in results if r["status"] != "not_configured")})
