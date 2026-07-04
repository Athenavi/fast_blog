"""
加密工具 — AI 配置 API Key 加密/解密

方案：AES-256-GCM
- 密钥 = SHA256(user_password_hash[:32] + app_secret_key)[:32]
- 每次加密生成随机 nonce（12 字节），与密文一起存储
- 密文格式: base64(nonce + ciphertext + tag)
"""
import base64
import hashlib
import os
from typing import Optional

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def _derive_key(password_hash: str, app_secret_key: str) -> bytes:
    """派生 AES-256 密钥"""
    raw = (password_hash[:32] + app_secret_key).encode('utf-8')
    return hashlib.sha256(raw).digest()  # 32 bytes


def encrypt_api_key(api_key: str, password_hash: str, app_secret_key: str) -> str:
    """
    加密 API Key

    Args:
        api_key: 明文 API Key（sk-...）
        password_hash: 用户的密码哈希值
        app_secret_key: 应用的 SECRET_KEY

    Returns:
        base64 编码的密文
    """
    key = _derive_key(password_hash, app_secret_key)
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)  # 96-bit nonce
    ciphertext = aesgcm.encrypt(nonce, api_key.encode('utf-8'), None)
    # 存储格式: nonce + ciphertext（含 tag）
    return base64.b64encode(nonce + ciphertext).decode('utf-8')


def decrypt_api_key(encrypted: str, password_hash: str, app_secret_key: str) -> Optional[str]:
    """
    解密 API Key

    Args:
        encrypted: base64 编码的密文
        password_hash: 用户的密码哈希值
        app_secret_key: 应用的 SECRET_KEY

    Returns:
        明文 API Key，解密失败返回 None
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
