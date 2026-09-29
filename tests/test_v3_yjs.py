"""_pending_test_yjs.py —— 待迁入 ``tests/`` 的**纯函数**单测

本任务的环境**禁止写 ``tests/`` 目录、禁止执行 shell**，因此把 ``content/yjs`` 模块的纯函数
单测临时放在模块目录内（文件名以下划线开头，不会被当作业务模块导入）。恢复后应移动到
``tests/test_v3_yjs.py``（父代理负责搬运）。

只覆盖**不依赖 DB / 网络 / FastAPI / 时钟**的纯函数：

  - ``content_hash``          正文 sha256（写入 ``article_revisions.hash_code``）
  - ``html_stats``            正文规模统计
  - ``next_revision_number``  下一个版本号（含 bool / None / 空集合边界）
  - ``content_changed``       变更检测（``hash_code`` 优先、正文回退）
  - ``room_state``            房间状态（empty / active / crowded）
  - ``pick_room``             从进程内房间快照里挑文档
  - ``invite_is_usable``      邀请可用性（``now`` 由调用方传入，测试里用固定时间构造）
  - ``diff_summary``          变更摘要

运行（在仓库根目录，确保可 ``import src.*``）::

    python -m pytest src/api/v3/modules/content/yjs/_pending_test_yjs.py -q

**本文件尚未运行**：本任务执行环境不允许跑 pytest，故断言全部来自逐行读过的实现。
"""

from datetime import datetime
from types import SimpleNamespace

from src.api.v3.modules.content.yjs.schema import CROWDED_ROOM_CLIENTS, MAX_CONTENT_CHARS
from src.api.v3.modules.content.yjs.service import (
    content_changed,
    content_hash,
    diff_summary,
    html_stats,
    invite_is_usable,
    next_revision_number,
    pick_room,
    room_state,
)


# --------------------------------------------------------------------- 正文摘要
def test_content_hash_is_sha256_hex_and_stable():
    digest = content_hash("")
    assert len(digest) == 64
    assert all(char in "0123456789abcdef" for char in digest)
    # 相同输入 → 相同摘要；不同输入 → 不同摘要
    assert content_hash("") == digest
    assert content_hash("<p>a</p>") == content_hash("<p>a</p>")
    assert content_hash("a") != content_hash("b")


def test_content_hash_handles_none_like_text():
    # 实现里 ``(html or "")``：None 与空串等价（防御尚未初始化的快照）
    assert content_hash(None) == content_hash("")


def test_html_stats_basics():
    empty = html_stats("")
    assert empty == {
        "chars": 0,
        "lines": 0,
        "is_empty": True,
        "has_markup": False,
        "exceeds_limit": False,
    }
    single = html_stats("abc")
    assert single["chars"] == 3
    assert single["lines"] == 1
    assert single["is_empty"] is False
    assert single["has_markup"] is False
    # 两个换行 + 结尾换行 → 3 行
    assert html_stats("a\nb\n")["lines"] == 3
    assert html_stats("<p>x</p>")["has_markup"] is True
    # 只有空白视为"空"
    assert html_stats("   \n ")["is_empty"] is True


def test_html_stats_limit_boundary():
    assert html_stats("x" * MAX_CONTENT_CHARS)["exceeds_limit"] is False
    assert html_stats("x" * (MAX_CONTENT_CHARS + 1))["exceeds_limit"] is True


# --------------------------------------------------------------------- 版本号
def test_next_revision_number_empty_and_normal():
    assert next_revision_number([]) == 1
    assert next_revision_number([1]) == 2
    assert next_revision_number([3, 1, 2]) == 4
    assert next_revision_number([0]) == 1


def test_next_revision_number_ignores_non_int_and_bool():
    # None / 字符串被忽略；布尔被显式排除（True 在 Python 里也是 int，不拦会算成 2）
    assert next_revision_number([None]) == 1
    assert next_revision_number([True]) == 1
    assert next_revision_number([5, True]) == 6
    assert next_revision_number([2, "9"]) == 3


# --------------------------------------------------------------------- 变更检测
def test_content_changed_without_history_is_true():
    assert content_changed(None, None, "abc") is True
    assert content_changed(None, None, "") is True


def test_content_changed_prefers_hash():
    assert content_changed(content_hash("abc"), None, "abc") is False
    assert content_changed(content_hash("abc"), None, "abcd") is True
    # hash 存在时不看 previous_content（省去逐字比较）
    assert content_changed(content_hash("abc"), "完全不同的旧正文", "abc") is False


def test_content_changed_falls_back_to_content_compare():
    # hash_code 缺失（v2 与 collaboration 早期写入的修订都没有这一列）
    assert content_changed(None, "abc", "abc") is False
    assert content_changed(None, "abc", "abcd") is True
    assert content_changed("", "", "") is False


# --------------------------------------------------------------------- 房间状态
def test_room_state_boundaries():
    assert room_state(0) == "empty"
    assert room_state(-3) == "empty"
    assert room_state(1) == "active"
    assert room_state(CROWDED_ROOM_CLIENTS) == "active"
    assert room_state(CROWDED_ROOM_CLIENTS + 1) == "crowded"


def test_room_state_rejects_non_int():
    # 布尔不是合法连接数；None / 字符串按 0 处理
    assert room_state(True) == "empty"
    assert room_state(None) == "empty"
    assert room_state("4") == "empty"


def test_pick_room():
    rooms = [
        {"document_id": 1, "clients": 2},
        {"document_id": 7, "clients": 0},
    ]
    picked = pick_room(rooms, 7)
    assert picked is not None
    assert picked["clients"] == 0
    assert pick_room(rooms, 99) is None
    assert pick_room([], 1) is None
    assert pick_room(None, 1) is None


# --------------------------------------------------------------------- 邀请可用性
def _invite(**overrides):
    base = {"is_active": True, "expires_at": None, "max_uses": 0, "use_count": 0}
    base.update(overrides)
    return SimpleNamespace(**base)


def test_invite_is_usable_inactive_or_missing():
    now = datetime(2026, 1, 1, 12, 0, 0)
    assert invite_is_usable(None, now=now) is False
    assert invite_is_usable(_invite(is_active=False), now=now) is False


def test_invite_is_usable_expiry_boundary():
    now = datetime(2026, 1, 1, 12, 0, 0)
    assert invite_is_usable(_invite(expires_at=None), now=now) is True
    assert invite_is_usable(_invite(expires_at=now), now=now) is True  # 恰好到期仍可用
    assert invite_is_usable(_invite(expires_at=datetime(2025, 12, 31)), now=now) is False
    assert invite_is_usable(_invite(expires_at=datetime(2026, 1, 2)), now=now) is True


def test_invite_is_usable_use_count():
    now = datetime(2026, 1, 1, 12, 0, 0)
    # max_uses=0 表示不限次数
    assert invite_is_usable(_invite(max_uses=0, use_count=99), now=now) is True
    assert invite_is_usable(_invite(max_uses=2, use_count=1), now=now) is True
    assert invite_is_usable(_invite(max_uses=2, use_count=2), now=now) is False
    assert invite_is_usable(_invite(max_uses=2, use_count=3), now=now) is False
    # None 的 use_count 按 0 处理
    assert invite_is_usable(_invite(max_uses=2, use_count=None), now=now) is True


# --------------------------------------------------------------------- 变更摘要
def test_diff_summary_create_and_same():
    created = diff_summary(None, "abc")
    assert created["chars_before"] == 0
    assert created["chars_after"] == 3
    assert created["chars_delta"] == 3
    assert created["created"] is True
    assert created["cleared"] is False
    assert created["is_same"] is False

    same = diff_summary("abc", "abc")
    assert same["chars_delta"] == 0
    assert same["is_same"] is True
    assert same["created"] is False
    assert same["cleared"] is False


def test_diff_summary_clear_and_empty():
    cleared = diff_summary("abc", "")
    assert cleared["chars_delta"] == -3
    assert cleared["cleared"] is True
    assert cleared["created"] is False
    assert cleared["is_same"] is False

    both_empty = diff_summary("", "")
    assert both_empty["is_same"] is True
    assert both_empty["created"] is False
    assert both_empty["cleared"] is False
