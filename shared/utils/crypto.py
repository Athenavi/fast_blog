"""
Encryption Utilities - AI Configuration API Key Encryption/Decryption & Model Field Transparent Encryption

Method: AES-256-GCM
- Key = SHA256(user_password_hash[:32] + app_secret_key)[:32]
- Each encryption generates a random nonce (12 bytes), stored together with ciphertext
- Ciphertext format: base64(nonce + ciphertext + tag)
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
    """SQLAlchemy TypeDecorator - Transparent AES-256-GCM encrypt/decrypt field
    Uses app SECRET_KEY to derive the encryption key (independent of user password),
    suitable for TOTP Secret, backup codes, etc., that need decryption without user session.
    Usage::

        totp_secret = Column(EncryptedField(Text(32)), nullable=True)

    Storage format: base64(nonce(12B) + ciphertext)
    """

    impl = Text
    cache_ok = True

    def __init__(self, inner_type=None, **kwargs):
        super().__init__(**kwargs)
        self.inner_type = inner_type

    def _get_secret_key(self) -> str:
        """Lazy load app SECRET_KEY to avoid circular import at startup"""
        try:
            from shared.config.settings import settings
            return settings.SECRET_KEY
        except (ImportError, AttributeError) as exc:
            logger.error("Unable to get SECRET_KEY: [redacted]", exc)
            return ''

    def process_bind_param(self, value: Optional[str], dialect) -> Optional[str]:
        """Encrypt on storage"""
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
            logger.error("Encryption failed: %s", exc)
            return value

    def process_result_value(self, value: Optional[str], dialect) -> Optional[str]:
        """Decrypt on read"""
        if value is None:
            return None
        try:
            data = base64.b64decode(value)
            if len(data) < 13:  # nonce(12) + at least 1 byte ciphertext
                return value  # Not encrypted format, return as-is
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
            # Decryption failed, return original value (may be unencrypted old data)
            return value


def _derive_key(password_hash: str, app_secret_key: str) -> bytes:
    """Derive AES-256 key"""
    raw = (password_hash[:32] + app_secret_key).encode('utf-8')
    return hashlib.sha256(raw).digest()  # 32 bytes


def encrypt_api_key(api_key: str, password_hash: str, app_secret_key: str) -> str:
    """
    Encrypt API Key

    Args:
        api_key: API Key (sk-...)
        password_hash: User password hash
        app_secret_key: App SECRET_KEY

    Returns:
        base64 encoded ciphertext
    """
    key = _derive_key(password_hash, app_secret_key)
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)  # 96-bit nonce
    ciphertext = aesgcm.encrypt(nonce, api_key.encode('utf-8'), None)
    # Storage format: nonce + ciphertext (includes tag)
    return base64.b64encode(nonce + ciphertext).decode('utf-8')


def decrypt_api_key(encrypted: str, password_hash: str, app_secret_key: str) -> Optional[str]:
    """
    Decrypt API Key

    Args:
        encrypted: base64 encoded ciphertext
        password_hash: User password hash
        app_secret_key: App SECRET_KEY

    Returns:
        Plaintext API Key, returns None on decryption failure
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
