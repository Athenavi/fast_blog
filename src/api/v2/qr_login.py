"""
FastBlog API v2 二维码登录

在 v2 注册表中注册本模块即可启用 QR 登录。

注册方式（在 src/api/v2/__init__.py 的 ROUTE_REGISTRY_V2 中添加）：
    ("src.api.v2.qr_login", "/api/v2/auth/qr", ["qr-login"], False),
"""

from fastapi import APIRouter, Request
from fastapi.logger import logger

from src.extensions import cache

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
async def v2_phone_confirm(request: Request):
    """手机端扫码后确认登录"""
    from src.api.v1.user_utils.qrlogin_utils import phone_scan_back
    from src.auth import get_current_user
    from fastapi import HTTPException

    db = request.state.db if hasattr(request.state, 'db') else None
    try:
        current_user = await get_current_user(request, db)
    except HTTPException as e:
        if e.status_code == 401:
            return {"success": False, "requires_auth": True, "message": "请先登录后再扫码"}
        raise e
    try:
        return await phone_scan_back(request, current_user, cache)
    except Exception as e:
        logger.error(f"Phone confirm failed: {e}")
        return {"success": False, "message": "确认失败"}


"""
   # === QR Login endpoints (direct mount, bypasses router issues) ===
    @app.get('/api/v1/qr/generate')
    async def qr_generate_direct(request: Request):
        from src.api.v1.user_utils.qrlogin_utils import qr_login
        from src.setting import app_config
        try:
            sv = app_config.SYSTEM.SYS_VERSION
            ge = app_config.SYSTEM.GLOBAL_ENCODING
            domain = request.query_params.get('callback_domain', '')
            return await qr_login(request, sv, ge, domain, cache)
        except Exception as e:
            from fastapi.logger import logger
            logger.error(f'QR gen failed: {e}')
            return {'success': False, 'message': str(e)}

    @app.get('/api/v1/qr/status')
    async def qr_status_direct(request: Request):
        from src.api.v1.user_utils.qrlogin_utils import check_qr_login_back
        try:
            return await check_qr_login_back(request, cache)
        except Exception as e:
            return {'success': False, 'message': str(e)}

    @app.post('/api/v1/qr/confirm')
    async def qr_confirm_direct(request: Request):
        from src.api.v1.user_utils.qrlogin_utils import phone_scan_back
        from src.auth import get_current_user
        try:
            data = await request.json()
            from fastapi import Request as FastAPIRequest
            current_user = await get_current_user(request, None)
            return await phone_scan_back(request, current_user, cache)
        except Exception as e:
            return {'success': False, 'requires_auth': True, 'message': '请先登录'}
"""
