"""
密码验证模块
提供密码验证功能，避免循环导入问题
"""
import bcrypt


def _get_crypt_context():
    """获取密码加密上下文，使用纯 bcrypt 实现以避免 passlib 兼容性问题"""

    # 直接使用 bcrypt 实现，避免 passlib 的兼容性问题
    class BcryptContext:
        def hash(self, secret):
            # 确保密码不超过 72 个字节限制
            if len(secret.encode('utf-8')) > 72:
                secret = secret.encode('utf-8')[:72].decode('utf-8', errors='ignore')
            return bcrypt.hashpw(secret.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        def verify(self, secret, hash):
            try:
                return bcrypt.checkpw(secret.encode('utf-8'), hash.encode('utf-8'))
            except Exception:
                # 处理各种可能的错误情况
                try:
                    return bcrypt.checkpw(secret.encode('utf-8'), hash)
                except Exception:
                    return False

    return BcryptContext()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    验证明文密码与哈希密码是否匹配
    支持 Django 的 PBKDF2 和 bcrypt 两种格式
    
    Args:
        plain_password: 明文密码
        hashed_password: 哈希后的密码
    
    Returns:
        bool: 验证成功返回 True，否则返回 False
    """
    # 检查是否是 Django 的 PBKDF2 格式 (pbkdf2_sha256$...)
    if hashed_password.startswith('pbkdf2_'):
        # 使用 Django 的密码验证
        try:
            from django.contrib.auth.hashers import check_password as django_check_password
            return django_check_password(plain_password, hashed_password)
        except ImportError:
            # 如果无法导入 Django，返回 False
            return False
    else:
        # 使用 bcrypt 验证
        try:
            ctx = _get_crypt_context()
            return ctx.verify(plain_password, hashed_password)
        except Exception:
            # 如果上下文初始化失败，直接使用 bcrypt
            try:
                return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
            except Exception:
                try:
                    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password)
                except Exception:
                    return False


def hash_password(password: str) -> str:
    """
    对密码进行哈希处理
    
    Args:
        password: 明文密码
    
    Returns:
        str: 哈希后的密码
    """
    try:
        ctx = _get_crypt_context()
        return ctx.hash(password)
    except Exception:
        # 如果上下文初始化失败，直接使用bcrypt
        if len(password.encode('utf-8')) > 72:
            password = password.encode('utf-8')[:72].decode('utf-8', errors='ignore')
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
