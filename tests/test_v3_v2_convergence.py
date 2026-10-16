"""T5-10：v2 → v3 收敛的单测

覆盖三个新端点背后的纯逻辑（不连数据库、不依赖真实插件）：

1. ``mobile/media`` 音频元数据：LRC 解析、MIME 探测、组装、本人/公开读取规则
2. ``extension/theme`` 按 slug 配置：读取形状、保存写回、非主题插件拒绝
3. ``extension/plugin`` 自定义动作：kwargs 派发、能力校验、未知动作/插件
"""

import asyncio
from types import SimpleNamespace

import pytest

from src.api.v3.core.exceptions import BadRequestError, NotFoundError
from src.api.v3.modules.mobile.media import metadata as media_metadata
from src.api.v3.modules.mobile.media.service import mobile_media_service


# ---------------------------------------------------------------- 工具
class _FakeResult:
    def __init__(self, item):
        self._item = item

    def scalar_one_or_none(self):
        return self._item


class _FakeDB:
    def __init__(self, item):
        self._item = item

    async def execute(self, _query):
        return _FakeResult(self._item)


def _fake_manager(get_plugin):
    return type("M", (), {"get_plugin": staticmethod(get_plugin)})


# ---------------------------------------------------------------- 音频元数据
def test_parse_lrc_text():
    text = "[01:02.03]hello\n[00:00.50]hi\n\n[99:99.999]x"
    lyrics = media_metadata.parse_lrc_text(text)
    # 保持输入顺序（排序是调用方 extract_lyrics_from_audio 的职责）
    assert [item["text"] for item in lyrics] == ["hello", "hi", "x"]
    assert lyrics[0]["time"] == pytest.approx(62.03)
    assert lyrics[1]["time"] == pytest.approx(0.5)
    assert all({"time", "text"} == set(item) for item in lyrics)


def test_detect_image_mime_type():
    assert media_metadata.detect_image_mime_type(b"\xff\xd8\xffabc") == "image/jpeg"
    assert media_metadata.detect_image_mime_type(b"\x89PNG\r\n") == "image/png"
    assert media_metadata.detect_image_mime_type(b"RIFF____WEBP") == "image/webp"
    assert media_metadata.detect_image_mime_type(b"BMxx") == "image/bmp"
    assert media_metadata.detect_image_mime_type(b"??") == "image/jpeg"


def test_build_audio_metadata_shape(monkeypatch):
    monkeypatch.setattr(
        media_metadata, "extract_cover_from_audio", lambda media: b"\x89PNGdata"
    )
    monkeypatch.setattr(
        media_metadata,
        "extract_lyrics_from_audio",
        lambda media: [{"time": 1.5, "text": "a"}],
    )
    media = SimpleNamespace(id=1, original_filename="song.mp3", duration=120)

    result = media_metadata.build_audio_metadata(media)
    assert result["title"] == "song.mp3"
    assert result["duration"] == 120
    assert result["cover_image"].startswith("data:image/png;base64,")
    assert result["lyrics"] == [{"time": 1.5, "text": "a"}]


def test_audio_metadata_access_rules(monkeypatch):
    """本人/公开可读；他人私有 → 404（不泄露存在性）；非音频 → 400"""
    monkeypatch.setattr(
        "src.api.v3.modules.mobile.media.service.build_audio_metadata",
        lambda media: {"ok": True},
    )
    user = SimpleNamespace(id=7)
    own = SimpleNamespace(id=1, user=7, is_public=False, mime_type="audio/mpeg")
    other_public = SimpleNamespace(id=2, user=8, is_public=True, mime_type="audio/mpeg")
    other_private = SimpleNamespace(id=3, user=8, is_public=False, mime_type="audio/mpeg")
    not_audio = SimpleNamespace(id=4, user=7, is_public=True, mime_type="video/mp4")

    assert asyncio.run(mobile_media_service.audio_metadata(_FakeDB(own), user, 1)) == {"ok": True}
    assert asyncio.run(mobile_media_service.audio_metadata(_FakeDB(other_public), user, 2)) == {"ok": True}
    with pytest.raises(NotFoundError):
        asyncio.run(mobile_media_service.audio_metadata(_FakeDB(None), user, 99))
    with pytest.raises(NotFoundError):
        asyncio.run(mobile_media_service.audio_metadata(_FakeDB(other_private), user, 3))
    with pytest.raises(BadRequestError):
        asyncio.run(mobile_media_service.audio_metadata(_FakeDB(not_audio), user, 4))


# ---------------------------------------------------------------- theme 按 slug 配置
class _FakeManifest:
    def __init__(self, category):
        self.category = category


class _FakeThemePlugin:
    def __init__(self, category="theme"):
        self.slug = "fake-theme"
        self.name = "Fake Theme"
        self.manifest = _FakeManifest(category)
        self.settings = {"a": 1}
        self.metadata = {"settings_schema": {"x": {"type": "text"}}}

    async def load_metadata(self):
        return None

    def get_theme_config(self):
        return {"settings": dict(self.settings), "supports": ["header"]}

    def get_theme_contract(self):
        return {"v": 1}

    def update_theme_settings(self, settings):
        self.settings.update(settings)
        return True

    def save_settings(self):
        return True

    def get_component_slots(self):
        return self.settings.get("_componentSlots", {})


def test_theme_slug_config_roundtrip(monkeypatch):
    from src.api.v3.modules.extension.theme.service import theme_ops_service

    fake = _FakeThemePlugin()
    monkeypatch.setattr(
        "shared.services.plugins.plugin_manager.core.plugin_manager",
        _fake_manager(lambda slug: fake),
    )

    config = asyncio.run(theme_ops_service.theme_config("fake-theme"))
    assert config["slug"] == "fake-theme"
    assert config["settings"] == {"a": 1}
    assert config["settings_schema"] == {"x": {"type": "text"}}
    assert config["supports"] == ["header"]
    assert config["contract"] == {"v": 1}

    result = asyncio.run(
        theme_ops_service.update_theme_config(
            "fake-theme", settings={"a": 2}, component_slots={"header": ["x"]}
        )
    )
    assert fake.settings["a"] == 2
    assert fake.settings["_componentSlots"] == {"header": ["x"]}
    assert result["componentSlots"] == {"header": ["x"]}


def test_theme_slug_config_rejects_non_theme(monkeypatch):
    from src.api.v3.modules.extension.theme.service import theme_ops_service

    monkeypatch.setattr(
        "shared.services.plugins.plugin_manager.core.plugin_manager",
        _fake_manager(lambda slug: _FakeThemePlugin(category="plugin")),
    )
    with pytest.raises(NotFoundError):
        asyncio.run(theme_ops_service.theme_config("not-a-theme"))
    with pytest.raises(NotFoundError):
        asyncio.run(theme_ops_service.update_theme_config("not-a-theme", settings={}))


# ---------------------------------------------------------------- 插件自定义动作
def test_plugin_action_dispatch(monkeypatch):
    from src.api.v3.modules.extension.plugin.service import plugin_ops_service

    class _FakePlugin:
        slug = "fake"
        name = "Fake"

        @staticmethod
        def greet(name, greeting="hi"):
            return {"success": True, "text": f"{greeting} {name}"}

    monkeypatch.setattr(
        "shared.services.plugins.plugin_manager.core.plugin_manager",
        _fake_manager(lambda slug: _FakePlugin()),
    )

    result = asyncio.run(plugin_ops_service.execute_action("fake", "greet", {"name": "世界"}))
    assert result == {"success": True, "text": "hi 世界"}


def test_plugin_action_capability_denied(monkeypatch):
    from src.api.v3.modules.extension.plugin.service import plugin_ops_service

    class _FakePlugin:
        slug = "fake"
        name = "Fake"

        @staticmethod
        def restricted():
            return {"success": True}

        def check_capability(self, cap, raise_error=False):
            if raise_error:
                raise PermissionError(cap)
            return False

    # 能力声明要落在「函数对象」上（staticmethod 包装体上设属性不会传播）
    _FakePlugin.restricted._capability = "write:fake"

    monkeypatch.setattr(
        "shared.services.plugins.plugin_manager.core.plugin_manager",
        _fake_manager(lambda slug: _FakePlugin()),
    )
    with pytest.raises(PermissionError):
        asyncio.run(plugin_ops_service.execute_action("fake", "restricted", {}))


def test_plugin_action_unknown(monkeypatch):
    from src.api.v3.modules.extension.plugin.service import plugin_ops_service

    monkeypatch.setattr(
        "shared.services.plugins.plugin_manager.core.plugin_manager",
        _fake_manager(lambda slug: None if slug == "ghost" else SimpleNamespace(slug="fake")),
    )
    with pytest.raises(NotFoundError):
        asyncio.run(plugin_ops_service.execute_action("ghost", "any", {}))
    with pytest.raises(BadRequestError):
        asyncio.run(plugin_ops_service.execute_action("fake", "missing_action", {}))
