"""
密码验证模块
提供密码验证功能，避免循环导入问题
"""
import bcrypt


def _get_crypt_context():
    """获取密码加密上下文，处理passlib和bcrypt兼容性问题"""
    try:
        from passlib.context import CryptContext
        # 尝试创建CryptContext实例
        ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
        # 尝试使用一次以确保其正常工作
        ctx.hash("test")
        return ctx
    except (AttributeError, TypeError, ValueError):
        # 如果passlib有问题，返回一个使用bcrypt直接实现的类
        class SafeCryptContext:
            def hash(self, secret):
                # 确保密码不超过72字节限制
                if len(secret.encode('utf-8')) > 72:
                    secret = secret.encode('utf-8')[:72].decode('utf-8', errors='ignore')
                return bcrypt.hashpw(secret.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            
            def verify(self, secret, hash):
                try:
                    return bcrypt.checkpw(secret.encode('utf-8'), hash.encode('utf-8'))
                except Exception:
                    # 处理各种可能的错误情况
                    try:
                        return bcrypt.checkpw(secret.encode('utf-8'), hash.encode('utf-8'))
                    except Exception:
                        return False
        
        return SafeCryptContext()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    验证明文密码与哈希密码是否匹配
    
    Args:
        plain_password: 明文密码
        hashed_password: 哈希后的密码
    
    Returns:
        bool: 验证成功返回True，否则返回False
    """
    try:
        ctx = _get_crypt_context()
        return ctx.verify(plain_password, hashed_password)
    except Exception:
        # 如果上下文初始化失败，直接使用bcrypt
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