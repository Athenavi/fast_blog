import base64
import hashlib
import io
import secrets
import time
import uuid
from datetime import datetime, timezone

import jwt as pyjwt
import qrcode
from fastapi import Request
from sqlalchemy.orm import Session

from src.extensions import get_async_db_session as get_async_db
from src.models.user import User as UserModel
from src.setting import app_config


# 导入新的WebSocket管理器


def gen_qr_token(user_agent: str, timestamp: str, sys_version: str, encoding: str) -> str:
    """Generate QR code token based on user agent and timestamp"""
    data = f"{user_agent}{timestamp}{sys_version}{secrets.token_hex(16)}"
    return hashlib.sha256(data.encode(encoding)).hexdigest()


def validate_password_strength(password: str) -> tuple[bool, str]:
    """Validate password strength"""
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"

    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)

    if not (has_upper and has_lower and has_digit and has_special):
        return False, "Password must contain uppercase, lowercase, digit and special character"

    return True, "Password is strong"


async def qr_login(request: Request, sys_version: str, global_encoding: str, domain: str, cache_instance):
    try:
        import logging
        logger = logging.getLogger(__name__)

        logger.info("Starting qr_login function")

        ct = str(int(time.time()))
        user_agent = request.headers.get('User-Agent', 'Unknown')

        # 确保domain是完整URL
        if domain and not domain.startswith(('                 http://', 'https://')):
            # 尝试从请求中获取实际的主机信息
            host = request.headers.get('host', 'localhost:9421')
            scheme = request.url.scheme if hasattr(request.url, 'scheme') else 'http'
            full_domain = f"{scheme}://{host}/"
        else:
            full_domain = domain if domain else "http://localhost:9421/"

        logger.info(f"Full domain for QR: {full_domain}")

        token = gen_qr_token(user_agent, ct, sys_version, global_encoding)
        token_expire = str(int(time.time() + 180))
        # 修改二维码内容，指向移动登录页面而不是直接的API端点
        qr_data = f"{full_domain}mobile-login?login_token={token}"

        logger.info(f"QR data to encode: {qr_data}")

        # 生成二维码
        logger.info("Generating QR code...")
        qr_img = qrcode.make(qr_data)
        buffered = io.BytesIO()
        qr_img.save(buffered, format="PNG")
        qr_code_base64 = base64.b64encode(buffered.getvalue()).decode(global_encoding)

        # 存储二维码状态（可以根据需要扩展）
        token_json = {'status': 'pending', 'created_at': ct, 'expire_at': token_expire}

        logger.info(f"Saving token to cache: QR-token_{token}")

        # 存储到缓存
        # 检查缓存实例是否支持timeout参数
        try:
            cache_instance.set(f"QR-token_{token}", token_json, timeout=180)
        except TypeError:
            # 如果不支持timeout参数，则尝试使用ex参数
            try:
                cache_instance.set(f"QR-token_{token}", token_json, ex=180)
            except TypeError:
                # 如果都不支持，则直接存储（不带过期时间）
                cache_instance.set(f"QR-token_{token}", token_json)
        except Exception as e:
            logger.error(f"Error saving QR token to cache: {e}")
            # 如果缓存失败，仍然返回成功但记录错误
            pass

        logger.info("QR code generated successfully")

        return {
            'success': True,
            'qr_code': f"data:image/png;base64,{qr_code_base64}",
            'token': token,
            'expires_at': token_expire,
            'status': 'pending'
        }
    except Exception as e:
        import logging
        import traceback
        logger = logging.getLogger(__name__)
        logger.error(f"Error in qr_login: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        # 不抛出异常，而是返回错误信息
        return {
            'success': False,
            'message': f'Failed to generate QR code: {str(e)}'
        }


async def phone_scan_back(
        request: Request,
        current_user: UserModel,
        cache_instance=None
):
    # 用户扫码调用此接口
    token = request.query_params.get('login_token')
    refresh_token = request.cookies.get('refresh_token')

    if not token:
        return {'success': False, 'message': 'Missing login token'}

    if token:
        current_user_id = current_user.id
        cache_qr_token = cache_instance.get(f"QR-token_{token}")
        if cache_qr_token:
            # 当手机端用户确认授权时，先设置授权信息，然后更新二维码状态
            # 这样可以确保在PC端轮询时，授权信息已经可用
            try:
                # 生成新的访问令牌用于登录
                import jwt as pyjwt
                import uuid
                from datetime import datetime, timezone
                from src.setting import app_config

                # 生成新的访问令牌
                access_token = pyjwt.encode({
                    'user_id': current_user.id,
                    'email': current_user.email,
                    'exp': datetime.now(timezone.utc) + app_config.JWT_ACCESS_TOKEN_EXPIRES,
                    'jti': str(uuid.uuid4())
                }, app_config.JWT_SECRET_KEY, algorithm='HS256')

                allow_json = {
                    'status': 'success',
                    'refresh_token': refresh_token,
                    'user_id': current_user_id,
                    'access_token': access_token  # 添加access_token到授权信息
                }
                cache_instance.set(f"QR-allow_{token}", allow_json, timeout=180)
            except TypeError:
                # 如果不支持timeout参数，则尝试使用ex参数或直接存储
                try:
                    cache_instance.set(f"QR-allow_{token}", allow_json, ex=180)
                except TypeError:
                    cache_instance.set(f"QR-allow_{token}", allow_json)

            # 然后更新二维码状态为success，表示已完成授权
            success_json = {'status': 'success'}
            try:
                cache_instance.set(f"QR-token_{token}", success_json, timeout=180)
            except TypeError:
                try:
                    cache_instance.set(f"QR-token_{token}", success_json, ex=180)
                except TypeError:
                    cache_instance.set(f"QR-token_{token}", success_json)

            # 注意：由于我们移除了WebSocket，不再发送实时消息
            # PC端将通过轮询机制检测到状态变更

            return {
                "message": '授权成功，请在两分钟内完成登录',
                "success": True
            }
        return {'success': False, 'message': 'Invalid or expired token'}
    else:
        return {'success': False, 'status': 'failed', 'message': 'Token validation failed'}


async def check_qr_login_back(request: Request, cache_instance):
    token = request.query_params.get('token')
    next_url = request.query_params.get('next', '/profile')

    # 检查二维码本身的当前状态
    cache_qr_token = cache_instance.get(f"QR-token_{token}")
    # 检查是否有授权信息
    cache_qr_allowed = cache_instance.get(f"QR-allow_{token}")

    if not token:
        return {'success': False, 'status': 'error', 'message': 'Missing token parameter'}

    # 首先检查是否有授权信息（成功登录）
    if cache_qr_allowed:
        try:
            user_id = cache_qr_allowed.get('user_id')

            # 从数据库获取用户信息
            db_gen = get_async_db()
            db: Session = next(db_gen)
            try:
                from sqlalchemy import select
                scan_user_query = select(UserModel).where(UserModel.id == user_id)
                scan_user_result = await db.execute(scan_user_query)
                scan_user = scan_user_result.scalar_one_or_none()
                if not scan_user:
                    return {'success': False, 'status': 'error', 'message': '用户不存在'}

                # 生成新的访问令牌
                access_token = pyjwt.encode({
                    'user_id': scan_user.id,
                    'email': scan_user.email,
                    'exp': datetime.now(timezone.utc) + app_config.JWT_ACCESS_TOKEN_EXPIRES,
                    'jti': str(uuid.uuid4())
                }, app_config.JWT_SECRET_KEY, algorithm='HS256')

                # 返回字典而不是JSONResponse对象，保持一致性
                return {
                    'success': True,
                    'status': 'success',
                    'next_url': next_url,
                    'access_token': access_token
                }
            finally:
                db.close()
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"QR登录错误: {e}")
            return {'success': False, 'status': 'error', 'message': '登录失败'}

    # 没有授权信息，检查二维码本身的状态
    if not cache_qr_token:
        # 二维码token不存在或已过期
        import time
        current_time = int(time.time())
        expires_at = int(request.query_params.get('expires_at', current_time))
        if current_time > expires_at:
            return {'success': True, 'status': 'expired', 'message': 'QR code expired'}
        # 如果既没有二维码token也没有授权信息，且未过期，返回pending
        return {'success': True, 'status': 'pending'}

    # 二维码token存在，返回其当前状态
    status = cache_qr_token.get('status', 'pending')

    # 根据二维码的状态返回相应结果
    if status == 'success':
        # 这里表示手机端已确认，但授权信息还未写入（短暂状态）
        # 重新检查授权信息，因为可能存在时间差
        import time
        time.sleep(0.5)  # 短暂延迟，等待授权信息写入
        cache_qr_allowed_retry = cache_instance.get(f"QR-allow_{token}")
        if cache_qr_allowed_retry:
            try:
                user_id = cache_qr_allowed_retry.get('user_id')
                # 从数据库获取用户信息
                db_gen = get_async_db()
                db: Session = next(db_gen)
                from sqlalchemy import select
                scan_user_query = select(UserModel).where(UserModel.id == user_id)
                scan_user_result = await db.execute(scan_user_query)
                scan_user = scan_user_result.scalar_one_or_none()
                if not scan_user:
                    return {'success': False, 'status': 'error', 'message': '用户不存在'}
                # 生成新的访问令牌
                access_token = pyjwt.encode({
                    'user_id': scan_user.id,
                    'email': scan_user.email,
                    'exp': datetime.now(timezone.utc) + app_config.JWT_ACCESS_TOKEN_EXPIRES,
                    'jti': str(uuid.uuid4())
                }, app_config.JWT_SECRET_KEY, algorithm='HS256')
                return {
                    'success': True,
                    'status': 'success',
                    'next_url': next_url,
                    'access_token': access_token
                }
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"QR登录错误: {e}")
                return {'success': False, 'status': 'error', 'message': '登录失败'}
            finally:
                db.close()
    else:
        return {'success': True, 'status': status}
