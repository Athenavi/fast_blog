# -*- coding: utf-8 -*-
"""P2-2 图片变体测试：格式协商、生成幂等、尺寸正确、路径不越界。

生成类用例把工作目录切到临时目录（``monkeypatch.chdir``），因为变体路径是
相对 ``storage/`` 的 —— 这样测试不会往仓库里写文件。
"""

from pathlib import Path

import pytest
from PIL import Image

from src.api.v3.modules.content.media import variants as V


class TestFormatNegotiation:
    def test_avif_preferred_when_supported(self):
        assert V.pick_format("image/avif,image/webp,*/*", avif_ok=True) == "avif"

    def test_falls_back_to_webp_when_avif_unsupported(self):
        assert V.pick_format("image/avif,image/webp,*/*", avif_ok=False) == "webp"

    def test_webp_only(self):
        assert V.pick_format("image/webp,image/png", avif_ok=False) == "webp"

    def test_no_modern_format_keeps_original(self):
        assert V.pick_format("image/jpeg", avif_ok=False) == "original"

    def test_empty_or_wildcard_accept(self):
        assert V.pick_format("", avif_ok=False) == "webp"
        assert V.pick_format("*/*", avif_ok=False) == "webp"

    def test_supports_avif_returns_bool(self):
        assert isinstance(V.supports_avif(), bool)


class TestImageDetection:
    @pytest.mark.parametrize(
        "mime", ["image/jpeg", "image/png", "image/webp", "image/gif", "IMAGE/PNG"]
    )
    def test_raster_images_supported(self, mime):
        assert V.is_image(mime) is True

    @pytest.mark.parametrize("mime", ["image/svg+xml", "video/mp4", "application/pdf", None, ""])
    def test_non_raster_rejected(self, mime):
        assert V.is_image(mime) is False


class TestVariantNaming:
    def test_sizes_are_ascending_and_unique(self):
        widths = [w for _, w in V.SIZES]
        assert widths == sorted(widths)
        assert len(set(widths)) == len(widths)
        assert set(V.variant_names()) == {"thumb", "small", "medium", "large"}

    def test_variant_path_is_under_content_addressed_dir(self):
        path = V.variant_file("ab12cd34", "thumb", "webp")
        assert str(path).replace("\\", "/") == "storage/ab/ab12cd34/thumb.webp"

    def test_original_format_keeps_source_suffix(self):
        path = V.variant_file("ab12cd34", "small", "original", source_suffix=".png")
        assert str(path).endswith("small.png")


class TestGeneration:
    def _make_source(self, tmp_path: Path, width: int = 1200, height: int = 800) -> Path:
        source_dir = tmp_path / "storage" / "ab"
        source_dir.mkdir(parents=True, exist_ok=True)
        source = source_dir / "ab12cd34.png"
        Image.new("RGB", (width, height), (120, 40, 200)).save(source, format="PNG")
        return source

    def test_generate_resizes_and_is_idempotent(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        source = self._make_source(tmp_path)

        target = V.generate(source, "ab12cd34", "thumb", "webp")
        assert target is not None and target.exists()
        with Image.open(target) as img:
            assert img.width == 200, "应按档位宽度缩放"
            assert img.height == 133, "应保持宽高比（800/1200*200）"

        first_mtime = target.stat().st_mtime_ns
        again = V.generate(source, "ab12cd34", "thumb", "webp")
        assert again == target
        assert target.stat().st_mtime_ns == first_mtime, "已存在时不应重复生成（幂等）"

    def test_small_image_is_not_upscaled(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        source = self._make_source(tmp_path, width=150, height=100)

        target = V.generate(source, "ab12cd34", "large", "webp")
        assert target is not None
        with Image.open(target) as img:
            assert img.width == 150, "小图不得被放大"

    def test_unknown_variant_name_returns_none(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        source = self._make_source(tmp_path)
        assert V.generate(source, "ab12cd34", "huge", "webp") is None

    def test_missing_source_is_handled(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        assert V.generate(tmp_path / "nope.png", "ab12cd34", "thumb", "webp") is None

    def test_original_format_output_exists(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        source = self._make_source(tmp_path)
        target = V.generate(source, "ab12cd34", "small", "original")
        assert target is not None and target.exists()
        assert target.suffix == ".png", "original 保持原扩展名"


class TestVariantUrls:
    def test_non_image_media_has_no_variants(self):
        from src.api.v3.modules.content.media.service import _variant_urls

        class FakeMedia:
            id = 5
            mime_type = "application/pdf"

        assert _variant_urls(FakeMedia()) == []

    def test_image_media_lists_all_sizes(self):
        from src.api.v3.modules.content.media.service import _variant_urls

        class FakeMedia:
            id = 7
            mime_type = "image/jpeg"

        urls = _variant_urls(FakeMedia())
        assert len(urls) == len(V.SIZES)
        assert all(u.startswith("/api/v3/content/media/7/variant/") for u in urls)
