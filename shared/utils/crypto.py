"""
加密工具 �?AI 配置 API Key 加密/解密 & 模型字段透明加密

方案：AES-256-GCM
- 密钥 = SHA256(user_password_hash[:32] + app_secret_key)[:32]
- 每次加密生成随机 nonce�?2 字节），与密文一起存�?- 密文格式: base64(nonce + ciphertext + tag)
"""
import base64
import hashlib
import logging
import os
from typing import Optional, Any

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy import TypeDecorator, Text

logger = logging.getLogger(__name__)


class EncryptedField(TypeDecorator):
    """SQLAlchemy TypeDecorator �?透明 AES-256-GCM 加解密字�?
    使用 app SECRET_KEY 派生密钥（不依赖用户密码），适用�?TOTP Secret�?    备份码等需要在无用户会话时解密的字段�?
    用法::

        totp_secret = Column(EncryptedField(String(32)), nullable=True)

    存储格式: base64(nonce(12B) + ciphertext)
    """

    impl = Text
    cache_ok = True

    def __init__(self, inner_type=None, **kwargs):
        super().__init__(**kwargs)
        self.inner_type = inner_type

    def _get_secret_key(self) -> str:
        """懒加�?app SECRET_KEY，避免启动时循环导入"""
        try:
            from shared.config.settings import settings
            return settings.SECRET_KEY
        except (ImportError, AttributeError) as exc:
            logger.error("无法获取 SECRET_KEY: %s", exc)
            return ''

    def process_bind_param(self, value: Optional[str], dialect) -> Optional[str]:
        """存储时加�?""
        if value is None:
            return None
        secret = self._get_secret_key()
        if not secret:
            return value
        try:
            raw = secret.encode('utf-8')
            key = hashlib.sha256(raw).digest()
            aesgcm = AESGCM(key)
            nonce = os.urandom(12)
            ciphertext = aesgcm.encrypt(nonce, str(value).encode('utf-8'), None)
            return base64.b64encode(nonce + ciphertext).decode('utf-8')
        except Exception as exc:
            logger.error("加密失败: %s", exc)
            return value

    def process_result_value(self, value: Optional[str], dialect) -> Optional[str]:
        """读取时解�?""
        if value is None:
            return None
        try:
            data = base64.b64decode(value)
            if len(data) < 13:  # nonce(12) + 至少1字节密文
                return value  # 非加密格式，原样返回
            secret = self._get_secret_key()
            if not secret:
                return value
            key = hashlib.sha256(secret.encode('utf-8')).digest()
            aesgcm = AESGCM(key)
            nonce = data[:12]
            ciphertext = data[12:]
            plaintext = aesgcm.decrypt(nonce, ciphertext, None)
            return plaintext.decode('utf-8')
        except Exception:
            # 解密失败返回原值（可能是未加密的旧数据�?            return value


def _derive_key(password_hash: str, app_secret_key: str) -> bytes:
    """派生 AES-256 密钥"""
    raw = (password_hash[:32] + app_secret_key).encode('utf-8')
    return hashlib.sha256(raw).digest()  # 32 bytes


def encrypt_api_key(api_key: str, password_hash: str, app_secret_key: str) -> str:
    """
    加密 API Key

    Args:
        api_key: 明文 API Key（sk-...�?        password_hash: 用户的密码哈希�?        app_secret_key: 应用�?SECRET_KEY

    Returns:
        base64 编码的密�?    """
    key = _derive_key(password_hash, app_secret_key)
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)  # 96-bit nonce
    ciphertext = aesgcm.encrypt(nonce, api_key.encode('utf-8'), None)
    # 存储格式: nonce + ciphertext（含 tag�?    return base64.b64encode(nonce + ciphertext).decode('utf-8')


def decrypt_api_key(encrypted: str, password_hash: str, app_secret_key: str) -> Optional[str]:
    """
    解密 API Key

    Args:
        encrypted: base64 编码的密�?        password_hash: 用户的密码哈希�?        app_secret_key: 应用�?SECRET_KEY

    Returns:
        明文 API Key，解密失败返�?None
    """
    try:
        key = _derive_key(password_hash, app_secret_key)
        aesgcm = AESGCM(key)
        data = base64.b64decode(encrypted)
        nonce = data[:12]
        ciphertext = data[12:]
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)
        return plaintext.decode('utf-8')
    except Exception:
        return None
