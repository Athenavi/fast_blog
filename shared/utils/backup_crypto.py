"""备份文件加密（AES-256-CTR + HMAC-SHA256，Encrypt-then-MAC）

## 为什么需要

备份里是**整个数据库的 dump**（用户表、密文凭据、私信、订单…）。默认以
``.sql.gz`` 明文落在 ``backups/`` 卷上，任何能读到该卷或拿到云存储副本的人
都能直接读全部数据。企业场景下这属于"备份介质未加密"。

## 文件格式（v1）

::

    offset  size  field
    0       7     magic  b"FBBAK1\\x00"
    7       16    salt   HKDF salt
    23      16    iv     AES-CTR 初始计数器
    39      32    mac    HMAC-SHA256(header ‖ ciphertext)
    71      ...   ciphertext

密钥由 ``SECRET_KEY`` 经 HKDF-SHA256 派生（info 绑定用途，length=64），
前 32 字节为加密密钥、后 32 字节为 MAC 密钥 —— 与项目既有的
``secret_box``（AES-256-GCM，SHA256(SECRET_KEY)）同源不同用途，互不影响。

## 注意

**SECRET_KEY 轮换后旧备份将无法解密**。这是刻意的 fail-closed 设计：
解密失败会明确报错，而不是产出半截损坏的数据。轮换密钥前请先解密归档旧备份。
"""

from __future__ import annotations

import hashlib
import hmac
import os
from typing import Tuple

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

MAGIC = b"FBBAK1\x00"
SALT_LEN = 16
IV_LEN = 16
MAC_LEN = 32
HEADER_LEN = len(MAGIC) + SALT_LEN + IV_LEN
_CHUNK = 1024 * 1024
_HKDF_INFO = b"fastblog-backup-v1"


def backup_key_material() -> bytes:
    """取派生密钥的根材料（``SECRET_KEY``）"""
    from shared.config.settings import settings

    secret = getattr(settings, "SECRET_KEY", None) or os.environ.get("SECRET_KEY") or ""
    if isinstance(secret, str):
        secret = secret.encode("utf-8")
    if not secret:
        raise ValueError("SECRET_KEY 未配置，无法加解密备份")
    return secret


def _derive(key_material: bytes, salt: bytes) -> Tuple[bytes, bytes]:
    okm = HKDF(
        algorithm=hashes.SHA256(), length=64, salt=salt, info=_HKDF_INFO
    ).derive(key_material)
    return okm[:32], okm[32:]


def is_encrypted(path: str) -> bool:
    """按魔数判断（比扩展名可靠：改名后仍可识别）"""
    try:
        with open(path, "rb") as handle:
            head = handle.read(len(MAGIC))
    except OSError:
        return False
    return head == MAGIC


def encrypt_file(src: str, dst: str, key_material: bytes) -> None:
    """把 ``src`` 加密写入 ``dst``（流式，可处理大于内存的备份）"""
    salt = os.urandom(SALT_LEN)
    iv = os.urandom(IV_LEN)
    enc_key, mac_key = _derive(key_material, salt)
    header = MAGIC + salt + iv

    encryptor = Cipher(algorithms.AES(enc_key), modes.CTR(iv)).encryptor()
    mac = hmac.new(mac_key, digestmod=hashlib.sha256)
    mac.update(header)

    with open(src, "rb") as fin, open(dst, "wb") as fout:
        fout.write(header)
        fout.write(b"\x00" * MAC_LEN)  # 占位，末尾回填
        for chunk in iter(lambda: fin.read(_CHUNK), b""):
            ciphertext = encryptor.update(chunk)
            mac.update(ciphertext)
            fout.write(ciphertext)
        tail = encryptor.finalize()
        if tail:
            mac.update(tail)
            fout.write(tail)
        fout.seek(HEADER_LEN)
        fout.write(mac.digest())


def decrypt_file(src: str, dst: str, key_material: bytes) -> None:
    """解密 ``src`` 到 ``dst``；MAC 不匹配时删除输出并抛错（fail-closed）"""
    with open(src, "rb") as fin:
        header = fin.read(HEADER_LEN)
        if not header.startswith(MAGIC) or len(header) != HEADER_LEN:
            raise ValueError("不是本系统生成的加密备份（魔数不匹配）")
        salt = header[len(MAGIC):len(MAGIC) + SALT_LEN]
        iv = header[len(MAGIC) + SALT_LEN:]
        stored_mac = fin.read(MAC_LEN)

        enc_key, mac_key = _derive(key_material, salt)
        decryptor = Cipher(algorithms.AES(enc_key), modes.CTR(iv)).decryptor()
        mac = hmac.new(mac_key, digestmod=hashlib.sha256)
        mac.update(header)

        with open(dst, "wb") as fout:
            for chunk in iter(lambda: fin.read(_CHUNK), b""):
                mac.update(chunk)
                fout.write(decryptor.update(chunk))
            fout.write(decryptor.finalize())

    if not hmac.compare_digest(mac.digest(), stored_mac):
        os.remove(dst)
        raise ValueError("备份完整性校验失败（MAC 不匹配）：文件被篡改或 SECRET_KEY 已变更")


__all__ = [
    "MAGIC",
    "backup_key_material",
    "decrypt_file",
    "encrypt_file",
    "is_encrypted",
]
