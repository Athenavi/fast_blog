"""
FastBlog API v2 二维码登录

在 v2 注册表中注册本模块即可启用 QR 登录。

注册方式（在 src/api/v2/__init__.py 的 ROUTE_REGISTRY_V2 中添加）：
    ("src.api.v2.qr_login", "/api/v2/auth/qr", ["qr-login"], False),
"""

from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.logger import logger
from sqlalchemy.ext.asyncio import AsyncSession

from src.extensions import cache
from src.auth import get_current_user
from src.extensions import get_async_db_session as get_async_db

router = APIRouter(tags=["qr-login"])


@router.get("/generate")
async def v2_generate_qr(request: Request):
    """生成登录二维码"""
    from src.api.v1.user_utils.qrlogin_utils import qr_login
    from src.setting import app_config
    try:
        sys_version = app_config.SYSTEM.SYS_VERSION
        global_encoding = app_config.SYSTEM.GLOBAL_ENCODING
        domain = request.query_params.get('callback_domain') or ""
        return await qr_login(request, sys_version, global_encoding, domain, cache)
    except Exception as e:
        logger.error(f"QR generation failed: {e}")
        return {"success": False, "message": "Failed to generate QR code"}


@router.get("/status")
async def v2_check_qr_status(request: Request):
    """PC 端轮询检查扫码状态"""
    from src.api.v1.user_utils.qrlogin_utils import check_qr_login_back
    try:
        return await check_qr_login_back(request, cache)
    except Exception as e:
        logger.error(f"QR status check failed: {e}")
        return {"success": False, "message": "Failed to check QR code status"}


@router.post("/confirm")
async def v2_phone_confirm(request: Request, db: AsyncSession = Depends(get_async_db)):
    """手机端扫码后确认登录（支持 JSON body 或 query params）"""
    from src.api.v1.user_utils.qrlogin_utils import phone_scan_back

    # 读取 login_token：优先从 JSON body，其次 query params
    login_token = None
    content_type = request.headers.get('content-type', '')
    if 'application/json' in content_type:
        try:
            body = await request.json()
            login_token = body.get('login_token') or body.get('token')
        except Exception:
            pass
    if not login_token:
        login_token = request.query_params.get('login_token') or request.query_params.get('token')

    if not login_token:
        return {"success": False, "message": "Missing login_token"}

    try:
        current_user = await get_current_user(request, db)
    except HTTPException as e:
        if e.status_code == 401:
            return {"success": False, "requires_auth": True, "message": "请先登录后再扫码"}
        raise e

    try:
        return await phone_scan_back(request, current_user, cache, login_token=login_token)
    except Exception as e:
        logger.error(f"Phone confirm failed: {e}")
        return {"success": False, "message": "确认失败"}
