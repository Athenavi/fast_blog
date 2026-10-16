# -*- coding: utf-8 -*-
"""P2-3 字段级权限（读侧隐藏）测试（纯函数，不依赖数据库）。

钉住三条行为：

  1. 他人记录的敏感字段**被移除**（不是置空、不是打码）—— 置空会让前端误判为"未填写"；
  2. 本人与超级管理员**不做任何裁剪**；
  3. 非敏感字段与非 dict 输入原样返回，调用方可无条件套用。
"""

from src.api.v3.core.permission.field_policy import (
    SENSITIVE_FIELDS,
    redact,
    redact_many,
    redact_user,
    visible_sensitive_fields,
)


class FakeUser:
    def __init__(self, user_id: int, is_superuser: bool = False) -> None:
        self.id = user_id
        self.is_superuser = is_superuser


def _record(user_id: int = 7) -> dict:
    return {
        "id": user_id,
        "username": "alice",
        "email": "alice@example.com",
        "last_login_at": "2026-10-12T10:00:00",
        "is_active": True,
    }


class TestRedaction:
    def test_other_user_sensitive_fields_are_removed(self):
        out = redact_user(_record(7), FakeUser(1))
        assert "email" not in out, "他人的邮箱必须被移除"
        assert "last_login_at" not in out
        # 非敏感字段必须完整保留
        assert out["username"] == "alice" and out["is_active"] is True

    def test_removed_not_blanked(self):
        """关键：不能置空串/None，否则前端误以为"用户没填邮箱"。"""
        out = redact_user(_record(7), FakeUser(1))
        assert "email" not in out
        assert out.get("email") is None, "移除后取值应为 None（键不存在），而不是空串"

    def test_self_sees_own_fields(self):
        out = redact_user(_record(7), FakeUser(7))
        assert out["email"] == "alice@example.com"
        assert out["last_login_at"] is not None

    def test_superuser_sees_everything(self):
        out = redact_user(_record(7), FakeUser(1, is_superuser=True))
        assert out["email"] == "alice@example.com"

    def test_viewer_none_is_treated_as_other(self):
        """匿名/无身份时按"他人"处理（fail-closed），而不是全放行。"""
        out = redact_user(_record(7), None)
        assert "email" not in out

    def test_id_type_tolerance(self):
        record = _record(7)
        record["id"] = "7"  # 字符串 id 也应识别为"自己"
        out = redact_user(record, FakeUser(7))
        assert out["email"] == "alice@example.com"

    def test_non_dict_input_passes_through(self):
        assert redact("user", None) is None
        assert redact("user", [1, 2]) == [1, 2]

    def test_unknown_resource_is_untouched(self):
        data = _record()
        assert redact("article", data) == data

    def test_original_dict_not_mutated(self):
        data = _record()
        redact_user(data, FakeUser(1))
        assert "email" in data, "裁剪不应原地修改传入对象"

    def test_redact_many_keeps_list_semantics(self):
        out = redact_many("user", [_record(7), _record(8)], viewer=FakeUser(1))
        assert isinstance(out, list) and len(out) == 2
        assert all("email" not in item for item in out)


class TestVisibilityHelper:
    def test_visible_for_self_and_superuser(self):
        assert visible_sensitive_fields("user", _record(7), FakeUser(7)) is True
        assert visible_sensitive_fields("user", _record(7), FakeUser(1, True)) is True

    def test_hidden_for_others(self):
        assert visible_sensitive_fields("user", _record(7), FakeUser(1)) is False

    def test_unknown_resource_is_visible(self):
        assert visible_sensitive_fields("article", {"id": 1}, FakeUser(1)) is True

    def test_policy_table_registers_user_fields(self):
        assert set(SENSITIVE_FIELDS["user"]) == {"email", "last_login_at"}
