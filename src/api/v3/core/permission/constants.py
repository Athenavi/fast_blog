"""V3 权限常量（唯一真相）

设计要点：

  - **不做任何分隔符转换**。历史实现曾把 `:` 统一替换为 `.` 再比较，而权限码的权威来源
    （`scripts/seed_rbac.py`）写入的是冒号，导致校验永不匹配 —— 归一化本身就是那处
    P0 缺陷的根因。此处只做"去空白 + 拒绝空段"的规范化。
  - 数据范围档位与方案 §7.7.5 定死的 4 档一致（避免官方那种三处注释打架）。
"""

from typing import Final

# ---------------------------------------------------------------- 数据范围（roles.data_scope）
DATA_SCOPE_SELF: Final[int] = 1
"""仅本人数据"""

DATA_SCOPE_GROUP_AND_CHILD: Final[int] = 2
"""本权限组及以下（子组）数据"""

DATA_SCOPE_ALL: Final[int] = 3
"""全部数据"""

DATA_SCOPE_CUSTOM: Final[int] = 5
"""自定义：由 role_groups 指定的权限组范围"""

VALID_DATA_SCOPES: Final[frozenset[int]] = frozenset(
    {DATA_SCOPE_SELF, DATA_SCOPE_GROUP_AND_CHILD, DATA_SCOPE_ALL, DATA_SCOPE_CUSTOM}
)

DATA_SCOPE_LABELS: Final[dict[int, str]] = {
    DATA_SCOPE_SELF: "仅本人",
    DATA_SCOPE_GROUP_AND_CHILD: "本组及以下",
    DATA_SCOPE_ALL: "全部",
    DATA_SCOPE_CUSTOM: "自定义组",
}

# ---------------------------------------------------------------- 通配符（对齐 FastApiAdmin）
WILDCARD_CODES: Final[frozenset[str]] = frozenset({"*", "*:*:*"})
"""持有其中任意一个即视为拥有全部权限"""


def normalize_code(code: str) -> str:
    """规范化权限码：去空白、统一段内空白、拒绝空段

    **刻意不做 `:` ↔ `.` 的转换**（见模块 docstring）。
    """
    if code is None:
        raise ValueError("权限码不能为空")
    value = str(code).strip()
    if not value:
        raise ValueError("权限码不能为空")

    segments = [segment.strip() for segment in value.split(":")]
    if any(not segment for segment in segments):
        raise ValueError(f"权限码包含空段: {value!r}")
    return ":".join(segments)


__all__ = [
    "DATA_SCOPE_SELF",
    "DATA_SCOPE_GROUP_AND_CHILD",
    "DATA_SCOPE_ALL",
    "DATA_SCOPE_CUSTOM",
    "VALID_DATA_SCOPES",
    "DATA_SCOPE_LABELS",
    "WILDCARD_CODES",
    "normalize_code",
]
