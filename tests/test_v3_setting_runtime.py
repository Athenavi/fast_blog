"""运行时配置刷新：后台改 SMTP 参数后无需重启即生效。

历史实现是 ``src/utils/config_manager.py``（同步 Session，且字段名与 SystemSettings
模型不符，一运行就 AttributeError）。这里验证按当前架构重写的版本：
  1. 约定的键会写入 EmailService 实例
  2. 历史 ``mail_*`` 键名映射到同一批属性
  3. 未约定的键与非法值被忽略（不影响落库）
  4. ``SettingService.upsert`` 会触发刷新
"""

import asyncio
from types import SimpleNamespace

from shared.services.notifications.email_service import email_service
from src.api.v3.modules.system.setting import service as setting_service_module
from src.api.v3.modules.system.setting.runtime_sync import apply_runtime_settings


def test_email_settings_applied_to_runtime_instance():
    snapshot = (email_service.smtp_host, email_service.smtp_port)
    try:
        applied = apply_runtime_settings(
            [("smtp_host", "smtp.example.com"), ("smtp_port", "2525")]
        )
        assert sorted(applied) == ["smtp_host", "smtp_port"]
        assert email_service.smtp_host == "smtp.example.com"
        # 端口必须转成 int：EmailService 会把它直接交给 smtplib
        assert email_service.smtp_port == 2525
    finally:
        email_service.smtp_host, email_service.smtp_port = snapshot


def test_legacy_mail_keys_map_to_email_service():
    snapshot = (email_service.smtp_host, email_service.smtp_user, email_service.from_email)
    try:
        apply_runtime_settings(
            [
                ("mail_server", "mail.legacy.com"),
                ("mail_username", "legacy-user"),
                ("mail_from_address", "noreply@legacy.com"),
            ]
        )
        assert email_service.smtp_host == "mail.legacy.com"
        assert email_service.smtp_user == "legacy-user"
        assert email_service.from_email == "noreply@legacy.com"
    finally:
        email_service.smtp_host, email_service.smtp_user, email_service.from_email = snapshot


def test_unknown_keys_and_bad_values_are_ignored():
    snapshot = email_service.smtp_port
    try:
        applied = apply_runtime_settings(
            [
                ("site_title", "标题"),          # 未约定：只落库，不动运行时
                ("smtp_port", "not-a-number"),   # 非法整数：忽略
                ("smtp_password", None),         # 空值：忽略
            ]
        )
        assert applied == []
        assert email_service.smtp_port == snapshot
    finally:
        email_service.smtp_port = snapshot


class _FakeCrud:
    """假的 CRUD：只覆盖 upsert 会走到的两个分支（不存在 → 新建）"""

    def __init__(self):
        self.created = []

    async def get_by(self, _db, **_filters):
        return None

    async def create(self, _db, data):
        self.created.append(data)
        return SimpleNamespace(
            id=1,
            setting_key=data["setting_key"],
            setting_value=data["setting_value"],
            setting_type=data["setting_type"],
            description=data.get("description"),
            is_public=data.get("is_public", False),
            created_at=None,
            updated_at=None,
        )


def test_upsert_triggers_runtime_sync(monkeypatch):
    synced = []
    fake_crud = _FakeCrud()
    monkeypatch.setattr(setting_service_module, "setting_crud", fake_crud)
    monkeypatch.setattr(
        setting_service_module,
        "apply_runtime_settings",
        lambda items: synced.extend(items) or [k for k, _ in items],
    )

    result = asyncio.run(
        setting_service_module.setting_service.upsert(
            None, "smtp_host", value="smtp.after-upsert.com"
        )
    )

    assert result["setting_key"] == "smtp_host"
    assert synced == [("smtp_host", "smtp.after-upsert.com")]
    assert fake_crud.created[0]["setting_value"] == "smtp.after-upsert.com"
