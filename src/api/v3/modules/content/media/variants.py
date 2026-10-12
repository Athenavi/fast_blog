"""图片变体：多尺寸 + 现代格式协商。

设计要点
========

- **内容寻址落盘**：变体放在原图同级的子目录 ``storage/{hash[:2]}/{hash}/{name}.{ext}``，
  同一原图天然去重（hash 即内容指纹），不会因重复上传而重复生成。
- **懒生成**：首次请求某个变体时才生成，之后直接命中文件（幂等，靠 ``exists()`` 短路）。
- **格式协商**：解析 ``Accept``，在 ``avif / webp / original`` 中择优；AVIF 是否可用
  **运行时探测**（Pillow 未编译 AVIF 时自动回落 webp），不因环境缺能力而报错。
- **只处理图片**：非图片 MIME 不提供变体（调用方据此返回 404）。

生成刻意用 ``asyncio.to_thread`` 在调用方包装：PIL 的缩放/编码是 CPU 密集且阻塞的，
直接在大图请求里同步跑会拖住整个事件循环（项目在其它地方已吃过这类亏）。
"""

import io
from pathlib import Path
from typing import List, Optional, Tuple

from PIL import Image

from src.api.v3.core.logger import get_logger

logger = get_logger("content.media.variants")

#: 变体档位（名称 → 最大宽度）。宽高比保持不变，只缩不放（小图不会被人为放大）。
SIZES: Tuple[Tuple[str, int], ...] = (
    ("thumb", 200),
    ("small", 480),
    ("medium", 800),
    ("large", 1600),
)

SIZE_MAP = dict(SIZES)

#: 可派生变体的 MIME（SVG 是矢量，无需栅格变体）
RASTER_IMAGE_MIMES = frozenset({"image/jpeg", "image/png", "image/webp", "image/gif", "image/avif"})

#: 允许的输出格式
SUPPORTED_FORMATS = ("avif", "webp", "original")

#: AVIF 可用性探测结果缓存（None = 尚未探测）
_AVIF_SUPPORTED: Optional[bool] = None


def is_image(mime: Optional[str]) -> bool:
    """该 MIME 是否可派生栅格变体"""
    return (mime or "").lower() in RASTER_IMAGE_MIMES


def supports_avif() -> bool:
    """运行时探测 Pillow 是否支持 AVIF（结果缓存）"""
    global _AVIF_SUPPORTED
    if _AVIF_SUPPORTED is None:
        try:
            Image.init()
            _AVIF_SUPPORTED = "AVIF" in Image.registered_extensions().values() or "AVIF" in getattr(
                Image, "OPEN", {}
            )
        except Exception:  # noqa: BLE001 - 探测失败一律视为不支持
            _AVIF_SUPPORTED = False
    return bool(_AVIF_SUPPORTED)


def pick_format(accept: str, *, avif_ok: Optional[bool] = None) -> str:
    """按 ``Accept`` 选输出格式。

    规则（够用且可预测，不实现完整 q 值排序）：

      1. 客户端接受 ``image/avif`` 且环境支持 → ``avif``；
      2. 否则接受 ``image/webp`` → ``webp``；
      3. 否则 ``original``（保持原格式）。
    """
    header = (accept or "").lower()
    if not header or header.strip() == "*/*":
        return "webp" if "webp" not in header else "webp"
    if "image/avif" in header and (supports_avif() if avif_ok is None else avif_ok):
        return "avif"
    if "image/webp" in header:
        return "webp"
    return "original"


def variant_dir(media_hash: str) -> Path:
    """变体目录（与原图同级的子目录，避免与既有路径布局冲突）"""
    return Path(f"storage/{media_hash[:2]}/{media_hash}")


def variant_file(media_hash: str, name: str, fmt: str, *, source_suffix: str = "") -> Path:
    """变体文件路径；``original`` 格式沿用原图扩展名"""
    suffix = source_suffix if (fmt == "original" and source_suffix) else f".{fmt}"
    return variant_dir(media_hash) / f"{name}{suffix}"


def _encode(image: Image.Image, fmt: str, target: Path) -> None:
    """按目标格式编码并落盘（webp/avif 用有损高质量；original 保持原格式）"""
    target.parent.mkdir(parents=True, exist_ok=True)
    if fmt == "avif":
        image.save(target, format="AVIF", quality=82)
    elif fmt == "webp":
        image.save(target, format="WEBP", quality=82)
    else:
        image.save(target)
    logger.info("已生成图片变体 %s", target)


def generate(source: Path, media_hash: str, name: str, fmt: str) -> Optional[Path]:
    """生成（或复用）一个变体，返回其路径；失败返回 ``None``（调用方回落到原图）。

    - 目标已存在 → 直接返回（幂等）；
    - **只缩不放**：原图宽度小于档位时不放大，仅在需要时重编码为现代格式；
    - 动图（GIF）只做缩略不重编码为 webp/avif，避免丢失动画语义外的行为差异。
    """
    if name not in SIZE_MAP:
        return None
    max_width = SIZE_MAP[name]
    suffix = source.suffix.lower() if source.suffix else ""
    target = variant_file(media_hash, name, fmt, source_suffix=suffix)
    if target.exists():
        return target

    try:
        with Image.open(source) as img:
            animated = bool(getattr(img, "is_animated", False))
            effective_fmt = "original" if animated and fmt != "original" else fmt
            if animated and effective_fmt == "original":
                target = variant_file(media_hash, name, "original", source_suffix=suffix)

            width, height = img.size
            if width > max_width:
                ratio = max_width / float(width)
                img = img.resize((max_width, max(1, int(height * ratio))), Image.LANCZOS)
            if effective_fmt in ("webp", "avif") and img.mode not in ("RGB", "RGBA"):
                img = img.convert("RGBA" if "A" in img.getbands() else "RGB")
            if effective_fmt == "original":
                # 原格式重存：保留扩展名，避免与源文件同名覆盖
                target = variant_dir(media_hash) / f"{name}{suffix or '.img'}"
            _encode(img, effective_fmt, target)
    except Exception as exc:  # noqa: BLE001 - 生成失败不应让请求 500，回落原图
        logger.warning("生成变体失败 %s/%s: %s", media_hash[:8], name, exc)
        return None
    return target


def encode_bytes(source: Path, max_width: int, fmt: str) -> Optional[bytes]:
    """内存版生成（测试与一次性场景用）"""
    try:
        with Image.open(source) as img:
            width, height = img.size
            if width > max_width:
                ratio = max_width / float(width)
                img = img.resize((max_width, max(1, int(height * ratio))), Image.LANCZOS)
            buffer = io.BytesIO()
            if fmt == "webp":
                img.save(buffer, format="WEBP", quality=82)
            elif fmt == "avif":
                img.save(buffer, format="AVIF", quality=82)
            else:
                img.save(buffer)
            return buffer.getvalue()
    except Exception as exc:  # noqa: BLE001
        logger.warning("内存生成变体失败: %s", exc)
        return None


def variant_names() -> List[str]:
    return [name for name, _ in SIZES]


__all__ = [
    "SIZES",
    "SIZE_MAP",
    "SUPPORTED_FORMATS",
    "generate",
    "is_image",
    "pick_format",
    "supports_avif",
    "variant_dir",
    "variant_file",
    "variant_names",
]
