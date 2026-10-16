"""yjs 模块的请求 / 响应模型（Pydantic v2）

共享的**策略常量**也放在这里（``gamification/points`` 的同款做法：``CHECKIN_ACTION`` 就在
schema 里）：``service`` / ``controller`` 从本模块导入，避免 ``schema`` ←→ ``service``
循环导入。

两个**请求**模型显式声明 ``ConfigDict(extra="forbid")``：字段名拼错时直接 422，
而不是被静默丢弃（项目既有取舍：「不静默忽略未知字段」）。
"""

from datetime import datetime
from typing import Optional

from pydantic import ConfigDict, Field

from src.api.v3.core.base_schema import SchemaBase

#: 协作邀请里指向「文章」的目标类型（= 协同文档；见 ``collaboration_invites.target_type``）
ARTICLE_TARGET = "article"

#: 单次快照的正文上限（字符）：同时约束 pydantic 入参长度与 DB 写入，防止超大 payload
MAX_CONTENT_CHARS = 200_000

#: 房间「拥挤」阈值：连接数**大于**它标记为 ``crowded``（仅用于展示，不做任何限制）
CROWDED_ROOM_CLIENTS = 10

#: 默认修订说明（与 ``content/collaboration`` 的保存端点口径一致）
DEFAULT_SNAPSHOT_SUMMARY = "协同编辑保存"
#: 回滚产生的新修订说明模板（``{number}`` 为被恢复的版本号）
DEFAULT_RESTORE_SUMMARY = "恢复到版本 {number}"


# ---------------------------------------------------------------- 房间（进程内运行时状态）
class RoomOut(SchemaBase):
    """本进程的一个协同房间（**运行时状态**，不含文档内容）"""

    document_id: int
    clients: int = Field(default=0, description="本进程内该文档的 WebSocket 连接数")
    state: str = Field(default="empty", description="empty / active / crowded（room_state 纯函数）")
    active: bool = False


class RoomDetailOut(RoomOut):
    """单房间详情：连接数（进程内）+ 版本统计（真表 ``article_revisions`` / ``article_content``）"""

    revision_count: int = 0
    latest_revision_number: Optional[int] = None
    latest_revision_at: Optional[datetime] = None
    content_chars: int = Field(default=0, description="当前正文（``article_content.content``）字符数")
    has_content: bool = False


# ---------------------------------------------------------------- 访问权 / 协作者
class DocumentAccessOut(SchemaBase):
    """我在某份协同文档上的访问权（结构化返回，便于前端给出准确提示）"""

    document_id: int
    title: Optional[str] = None
    author_id: Optional[int] = None
    is_author: bool = False
    allowed: bool = Field(default=False, description="是否可进入该文档的协同编辑（读）")
    can_edit: bool = Field(default=False, description="是否可写入（作者或 permission=edit 的邀请）")
    via: Optional[str] = Field(default=None, description="author / invite；无权限时为 None")
    permission: Optional[str] = Field(default=None, description="邀请授予的权限：view / edit")
    reason: Optional[str] = Field(default=None, description="判定依据（人类可读）")


class AuthorOut(SchemaBase):
    """文档作者（协同关系的 owner）"""

    user_id: Optional[int] = None
    username: Optional[str] = None
    role: str = "owner"
    source: str = "author"
    can_edit: bool = True


class InviteCollaboratorOut(SchemaBase):
    """一条指向该文档的协作邀请（真表 ``collaboration_invites``）

    ``invite_code`` **只对文档作者回显**：拿到码就等于能进文档，非作者看不到它。
    """

    invite_id: int
    invite_code: Optional[str] = Field(
        default=None, description="邀请码（仅作者可见；非作者为 None）"
    )
    permission: Optional[str] = Field(default=None, description="view / edit")
    creator_id: Optional[int] = None
    expires_at: Optional[datetime] = None
    max_uses: int = 0
    use_count: int = 0
    usable: bool = Field(default=True, description="当前是否仍可用（激活 / 未过期 / 未超次数）")
    can_edit: bool = Field(default=False, description="是否授予写入权限（permission=edit）")


class CollaboratorsOut(SchemaBase):
    """文档的协作者来源：作者 + 仍有效的协作邀请"""

    document_id: int
    author: Optional[AuthorOut] = None
    invites: list[InviteCollaboratorOut] = Field(default_factory=list)
    invite_count: int = 0


# ---------------------------------------------------------------- 版本（article_revisions）
class RevisionOut(SchemaBase):
    """版本列表项（**不含正文**，避免列表接口返回几百 KB）"""

    id: int
    article_id: Optional[int] = None
    revision_number: Optional[int] = None
    title: Optional[str] = None
    author_id: Optional[int] = None
    author_name: Optional[str] = None
    change_summary: Optional[str] = None
    hash_code: Optional[str] = Field(default=None, description="正文 sha256（变更检测用）")
    content_chars: int = 0
    created_at: Optional[datetime] = None


class RevisionDetailOut(RevisionOut):
    """单个版本详情（含正文；超上限时截断返回并标记）"""

    content: Optional[str] = None
    content_is_truncated: bool = False
    stats: Optional[dict] = Field(default=None, description="html_stats 纯函数的结果")


# ---------------------------------------------------------------- 写：快照 / 回滚
class SnapshotRequest(SchemaBase):
    """保存前端上报的正文快照（CRDT 二进制状态不在这里，见 service 模块注释）"""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=False)

    html: str = Field(
        min_length=1,
        max_length=MAX_CONTENT_CHARS,
        description="富文本正文的 HTML 快照（完整入库，不做 v2 那样的 500 字符截断）",
    )
    change_summary: Optional[str] = Field(default=None, max_length=255)
    force: bool = Field(
        default=False, description="正文与最新修订一致时也强制新建一条修订（默认去重跳过）"
    )


class SnapshotResultOut(SchemaBase):
    """快照结果：``saved=False`` 表示因去重跳过了写入（不是失败）"""

    document_id: int
    saved: bool = False
    revision_number: Optional[int] = None
    content_hash: Optional[str] = None
    change: Optional[dict] = Field(default=None, description="diff_summary 纯函数的结果")
    reason: Optional[str] = None


class RestoreRequest(SchemaBase):
    """回滚请求：把某历史版本的正文恢复为当前正文，并**追加**一条新修订（不改写历史）"""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=False)

    change_summary: Optional[str] = Field(default=None, max_length=255)


class RestoreResultOut(SchemaBase):
    document_id: int
    restored_from: int = Field(description="被恢复的历史版本号")
    new_revision_number: int = Field(description="回滚产生的新版本号（= 现有最大 + 1）")
    content_hash: str = ""
