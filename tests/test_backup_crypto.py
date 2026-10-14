"""备份加解密回归测试

覆盖点：往返一致、大文件分块、MAC 篡改检测、魔数识别、密钥错误时的 fail-closed。
"""
import os

import pytest

from shared.utils import backup_crypto

KEY = b"unit-test-key-material-0123456789"


def _write(path, payload: bytes):
    with open(path, "wb") as handle:
        handle.write(payload)
    return str(path)


class TestRoundTrip:
    def test_small_file(self, tmp_path):
        src = _write(tmp_path / "a.dump", b"hello fastblog backup")
        dst = str(tmp_path / "a.dump.enc")
        out = str(tmp_path / "a.out")

        backup_crypto.encrypt_file(src, dst, KEY)
        # 密文不应包含明文
        assert b"hello fastblog backup" not in open(dst, "rb").read()

        backup_crypto.decrypt_file(dst, out, KEY)
        assert open(out, "rb").read() == b"hello fastblog backup"

    def test_large_file_spanning_chunks(self, tmp_path):
        payload = os.urandom(3 * 1024 * 1024 + 12345)  # 跨多个 1MB 分块
        src = _write(tmp_path / "big.dump", payload)
        dst = str(tmp_path / "big.enc")
        out = str(tmp_path / "big.out")

        backup_crypto.encrypt_file(src, dst, KEY)
        backup_crypto.decrypt_file(dst, out, KEY)
        assert open(out, "rb").read() == payload

    def test_empty_file(self, tmp_path):
        src = _write(tmp_path / "empty.dump", b"")
        dst = str(tmp_path / "empty.enc")
        out = str(tmp_path / "empty.out")

        backup_crypto.encrypt_file(src, dst, KEY)
        backup_crypto.decrypt_file(dst, out, KEY)
        assert open(out, "rb").read() == b""


class TestDetection:
    def test_magic_detects_encrypted(self, tmp_path):
        src = _write(tmp_path / "x", b"plain")
        dst = str(tmp_path / "x.enc")
        backup_crypto.encrypt_file(src, dst, KEY)
        assert backup_crypto.is_encrypted(dst) is True

    def test_plain_file_is_not_encrypted(self, tmp_path):
        src = _write(tmp_path / "y", b"plain content")
        assert backup_crypto.is_encrypted(src) is False

    def test_missing_file_is_not_encrypted(self, tmp_path):
        assert backup_crypto.is_encrypted(str(tmp_path / "nope")) is False


class TestFailClosed:
    def test_tampered_ciphertext_is_rejected(self, tmp_path):
        src = _write(tmp_path / "t.dump", b"x" * 4096)
        dst = str(tmp_path / "t.enc")
        backup_crypto.encrypt_file(src, dst, KEY)

        raw = bytearray(open(dst, "rb").read())
        raw[-1] ^= 0xFF  # 翻转最后一个密文字节
        open(dst, "wb").write(bytes(raw))

        out = str(tmp_path / "t.out")
        with pytest.raises(ValueError, match="完整性校验失败|MAC"):
            backup_crypto.decrypt_file(dst, out, KEY)
        # 失败时不得留下半截明文
        assert not os.path.exists(out)

    def test_wrong_key_is_rejected(self, tmp_path):
        src = _write(tmp_path / "w.dump", b"secret payload")
        dst = str(tmp_path / "w.enc")
        backup_crypto.encrypt_file(src, dst, KEY)

        out = str(tmp_path / "w.out")
        with pytest.raises(ValueError):
            backup_crypto.decrypt_file(dst, out, b"a-completely-different-key")
        assert not os.path.exists(out)

    def test_non_backup_file_is_rejected(self, tmp_path):
        bogus = _write(tmp_path / "bogus", b"not-a-fastblog-backup" * 10)
        out = str(tmp_path / "bogus.out")
        with pytest.raises(ValueError, match="魔数"):
            backup_crypto.decrypt_file(bogus, out, KEY)
