# -*- coding: utf-8 -*-
"""图片解码上限（防解压炸弹，`src/utils/image/limits.py`）。"""

import io

import pytest
from PIL import Image

from src.utils.image.limits import MAX_PIXELS, install_image_limits, open_image_checked


def _png(width: int, height: int) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (width, height)).save(buffer, format="PNG")
    return buffer.getvalue()


class TestImageLimits:
    def test_normal_image_is_accepted(self):
        with open_image_checked(io.BytesIO(_png(32, 32))) as img:
            assert img.size == (32, 32)

    def test_oversized_image_is_rejected(self):
        """尺寸从文件头就能读到：超限在解码整张位图之前就报错。"""
        import src.utils.image.limits as limits

        original = limits.MAX_PIXELS
        limits.MAX_PIXELS = 100  # 32x32 = 1024 像素，刚好超过
        try:
            with pytest.raises(ValueError, match="像素过大"):
                open_image_checked(io.BytesIO(_png(32, 32)))
        finally:
            limits.MAX_PIXELS = original

    def test_install_sets_global_cap(self):
        install_image_limits()
        assert Image.MAX_IMAGE_PIXELS == MAX_PIXELS
