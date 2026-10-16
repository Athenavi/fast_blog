"""对称加密工具：AES-256-GCM + SECRET_KEY 派生密钥（**全仓唯一实现**）

密文格式：``base64(nonce(12B) + ciphertext + tag)``，密钥 = ``SHA256(SECRET_KEY)``
（与 ``shared/utils/crypto.EncryptedField`` 的格式一致）。

用途是"存了但**永不回传**"的凭据：

  - ``ops/cdn`` 的 ``api_token``
  - ``ai/config`` 的 ``api_key``
  - ``content/third_party_publish`` 的渠道凭据

这三处此前各抄了一份（``ai/config`` 只加密、``ops/cdn`` 另有自己的副本）；
2026-09-21 批次 18 收敛到这里，避免第三、第四份继续复制。

**SECRET_KEY 轮换**会让既有密文解不开（只能重新填写凭据）。这是刻意接受的代价：
密文只用于服务端自己调用外部 API，从不回传给前端。
"""

import base64
import hashlib
import json
import os
from typing import Any

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

#: GCM nonce 长度（字节）
NONCE_SIZE = 12


def _key() -> bytes:
    from shared.config.settings import settings

    return hashlib.sha256(settings.SECRET_KEY.encode("utf-8")).digest()


def encrypt_secret(raw: str) -> str:
    """加密明文凭据；空串返回空串（调用方据此判断"留空保持原值"）"""
    if not raw:
        return ""
    nonce = os.urandom(NONCE_SIZE)
    ciphertext = AESGCM(_key()).encrypt(nonce, raw.encode("utf-8"), None)
    return base64.b64encode(nonce + ciphertext).decode("utf-8")


def decrypt_secret(token: str) -> str:
    """解密凭据；空串返回空串，格式错误 / 密钥不符抛 ``ValueError``"""
    if not token:
        return ""
    try:
        blob = base64.b64decode(token)
        nonce, ciphertext = blob[:NONCE_SIZE], blob[NONCE_SIZE:]
        return AESGCM(_key()).decrypt(nonce, ciphertext, None).decode("utf-8")
    except Exception as exc:  # noqa: BLE001 - 统一成 ValueError，调用方按"凭据失效"处理
        raise ValueError("凭据解密失败（SECRET_KEY 变更或数据损坏）") from exc


def encrypt_json(data: dict[str, Any] | None) -> str:
    """把凭据字典加密成密文（``None`` / 空字典 → 空串）"""
    if not data:
        return ""
    return encrypt_secret(json.dumps(data, ensure_ascii=False, sort_keys=True))


def decrypt_json(token: str) -> dict[str, Any]:
    """解密成字典；空串 → 空字典，内容不是 JSON 对象时抛 ``ValueError``"""
    if not token:
        return {}
    try:
        data = json.loads(decrypt_secret(token))
    except ValueError:
        raise
    except Exception as exc:  # noqa: BLE001 - JSON 损坏同样按"凭据失效"处理
        raise ValueError("凭据内容不是合法 JSON") from exc
    if not isinstance(data, dict):
        raise ValueError("凭据内容必须是 JSON 对象")
    return data
