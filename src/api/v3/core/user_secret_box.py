"""按用户派生的凭据加密：**密钥与「该用户的密码哈希 + SECRET_KEY」双因子挂钩**

与 `core/secret_box.py`（全局密钥 = `SHA256(SECRET_KEY)`）的区别，正是这个模块存在的理由：

  - **保密性叠加**：`SECRET_KEY` 在环境/配置文件里（不在数据库），用户的密码哈希在库里 ——
    只拿到数据库（或只拿到配置）都**解不开**；
  - **按用户隔离**：每个用户的密钥不同，无法用一个用户的密钥去解另一个用户的密文；
  - **改密码即轮换**：密码哈希变了，该用户的既有密文就失效（`ops` 侧会如实报"需重新填写"，
    而不是静默返回空值）；
  - **服务端不需要明文密码**：派生只用库里已有的 `users.password`（哈希）→
    后台任务/定时执行也能解密，不必等用户登录。

密钥派生：``HKDF-SHA256(ikm=SECRET_KEY, salt=用户密码哈希, info="fastblog:user-credential:v1")``。
密文格式与 `secret_box` 一致（``base64(nonce(12B) + ciphertext + tag)``），便于两者互操作。
"""

import base64
import hashlib
import os
from typing import Optional

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from src.api.v3.core import secret_box

#: GCM nonce 长度（字节）
NONCE_SIZE = 12

#: HKDF 的 info（加域隔离，避免与其它用途的派生密钥撞车）
HKDF_INFO = b"fastblog:user-credential:v1"

#: 用户没有密码（如纯 SSO 账号）时的占位盐
NO_PASSWORD_SALT = "no-password"


def derive_key(password_hash: Optional[str]) -> bytes:
    """按用户派生 32 字节 AES 密钥（纯函数，便于单测）"""
    from shared.config.settings import settings

    salt = (password_hash or NO_PASSWORD_SALT).encode("utf-8")
    hkdf = HKDF(algorithm=hashes.SHA256(), length=32, salt=salt, info=HKDF_INFO)
    return hkdf.derive(settings.SECRET_KEY.encode("utf-8"))


def encrypt_for_user(raw: str, password_hash: Optional[str]) -> str:
    """加密某个用户的凭据；空串返回空串（调用方据此判断"留空保持原值"）"""
    if not raw:
        return ""
    nonce = os.urandom(NONCE_SIZE)
    ciphertext = AESGCM(derive_key(password_hash)).encrypt(nonce, raw.encode("utf-8"), None)
    return base64.b64encode(nonce + ciphertext).decode("utf-8")


def decrypt_for_user(token: str, password_hash: Optional[str]) -> str:
    """解密某个用户的凭据

    解不开时先**回退**老格式（全局 `secret_box`，即本模块上线前用 `SECRET_KEY` 直接加密的密文），
    这样历史数据不用重录；两者都失败才抛 ``ValueError``（调用方按"凭据失效"处理）。
    """
    if not token:
        return ""
    try:
        blob = base64.b64decode(token)
        nonce, ciphertext = blob[:NONCE_SIZE], blob[NONCE_SIZE:]
        return AESGCM(derive_key(password_hash)).decrypt(nonce, ciphertext, None).decode("utf-8")
    except Exception:  # noqa: BLE001 - 统一按"凭据失效"处理，见下面的回退
        pass

    # 回退：老密文（全局 SECRET_KEY 派生）
    try:
        return secret_box.decrypt_secret(token)
    except ValueError as exc:
        raise ValueError(
            "凭据解密失败（SECRET_KEY 变更、用户密码已修改，或数据损坏）；请重新填写 API Key"
        ) from exc


def fingerprint(password_hash: Optional[str]) -> str:
    """密钥指纹（不含明文，可用于"这条密文是用哪把密钥加的"的诊断）"""
    return hashlib.sha256(derive_key(password_hash)).hexdigest()[:16]
