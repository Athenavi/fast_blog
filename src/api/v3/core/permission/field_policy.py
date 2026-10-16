"""字段级权限（**读侧隐藏**）。

与 ``data_scope`` 的分工：

  - ``data_scope``（行级）：能看到**哪些行**；
  - 本模块（字段级）：同一行里**哪些字段**可见。

当前策略（默认生效，属**有意的行为收紧**）：

  - ``user.email`` / ``user.last_login_at``：**仅本人或超级管理员**可见。
    管理员在用户列表里不再默认拿到他人的邮箱与登录时间，其余字段不受影响。
  - 不可见的字段一律**移除**（而不是置空或打码）—— 置空串会让前端误以为
    "用户没填邮箱"，``***`` 则会被误当作真实值写入表单。

接入点：``src/api/v3/modules/system/user/controller.py`` 的列表 / 详情响应。
新增字段策略时只需在 :data:`SENSITIVE_FIELDS` 里登记，并确保该端点的序列化路径
调用 :func:`redact`。
"""

from typing import Any, Dict, Iterable, Mapping

#: 资源 → 仅本人/超管可见的字段
SENSITIVE_FIELDS: Dict[str, Iterable[str]] = {
    "user": ("email", "last_login_at"),
}


def _is_superuser(viewer: Any) -> bool:
    return bool(getattr(viewer, "is_superuser", False))


def _is_self(data: Mapping[str, Any], viewer: Any) -> bool:
    """``data`` 是否是 ``viewer`` 自己的记录（id 比较，容忍类型差异）"""
    if viewer is None:
        return False
    try:
        return int(data.get("id")) == int(getattr(viewer, "id", -1))
    except (TypeError, ValueError):
        return False


def visible_sensitive_fields(resource: str, data: Any, viewer: Any) -> bool:
    """该查看者能否看到 ``resource`` 的敏感字段（便于路由/文档统一判断）"""
    fields = SENSITIVE_FIELDS.get(resource)
    if not fields:
        return True
    if _is_superuser(viewer):
        return True
    if isinstance(data, Mapping) and _is_self(data, viewer):
        return True
    return False


def redact(resource: str, data: Any, *, viewer: Any = None) -> Any:
    """按策略移除不可见字段。

    - 传入非 dict（``None``、列表等）原样返回，调用方可安全地无条件套用；
    - 本人与超管不做任何裁剪；
    - 其余情况只移除登记过的敏感字段，**保留全部其他字段**。
    """
    fields = SENSITIVE_FIELDS.get(resource)
    if not fields or not isinstance(data, dict):
        return data
    if _is_superuser(viewer) or _is_self(data, viewer):
        return data

    out = dict(data)
    for field in fields:
        out.pop(field, None)
    return out


def redact_many(resource: str, items: Iterable[Any], *, viewer: Any = None) -> list:
    """列表场景的便捷包装（``list`` 返回保持 list 语义）"""
    return [redact(resource, item, viewer=viewer) for item in items]


def redact_user(data: Any, viewer: Any = None) -> Any:
    """``user`` 资源的便捷包装（controller 里读起来更直白）"""
    return redact("user", data, viewer=viewer)
