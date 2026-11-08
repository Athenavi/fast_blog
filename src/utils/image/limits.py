"""图片解码的像素上限（防解压炸弹）。

一张 30000×30000 的 PNG 压缩后可能只有几百 KB，解码后是 3.6GB 的位图 ——
上传接口只要放行一次就足以把进程打挂。PIL 默认阈值是 89M 像素且**只告警**，
这里把上限降到可配置的 40M，并把告警升级为异常，再提供 `open_image_checked`
在头部信息（解码前即可拿到）阶段就拒绝。
"""

from __future__ import annotations

import os
import warnings
from typing import Any

from PIL import Image

MAX_PIXELS = int(os.environ.get("IMAGE_MAX_PIXELS", "") or 40_000_000)


def install_image_limits() -> None:
    """进程级兜底：超过上限的解码直接抛错，而不是只打一条 warning。"""
    Image.MAX_IMAGE_PIXELS = MAX_PIXELS
    warnings.simplefilter("error", Image.DecompressionBombWarning)


def open_image_checked(source: Any) -> Image.Image:
    """`Image.open` 的安全替代：解码前按头部尺寸拒绝超大图。

    调用方仍需自行 `close()`（与 `Image.open` 语义一致）。
    """
    img = Image.open(source)
    width, height = img.size
    if width * height > MAX_PIXELS:
        img.close()
        raise ValueError(
            f"图片像素过大（{width}x{height}），上限 {MAX_PIXELS} 像素"
        )
    return img
