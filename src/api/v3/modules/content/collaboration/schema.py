"""collaboration 模块的请求 / 响应模型

五块：工作区（workspace）/ 成员（member）/ 任务（task）/ 团队评论（comment）/ 邀请（invite）。

``role`` / ``status`` / ``priority`` / ``target_type`` 的合法值在这里集中声明，
由 ``service`` 做白名单校验（与 v2 的 ``TeamRole`` 层级一致：
``viewer < editor < admin < owner``）。
"""

from datetime import datetime
from typing import Optional

from pydantic import Field

from src.api.v3.core.base_schema import SchemaBase

#: 邀请目标类型（泛化：文章协作编辑 / 工作区邀请）
TARGET_TYPES: tuple[str, ...] = ("article", "workspace")
#: 邀请授予的权限
INVITE_PERMISSIONS: tuple[str, ...] = ("view", "edit")

#: 工作区成员角色与层级（层级用于权限判定）
MEMBER_ROLES: tuple[str, ...] = ("viewer", "editor", "admin", "owner")
ROLE_LEVELS: dict[str, int] = {"viewer": 1, "editor": 2, "admin": 3, "owner": 4}

#: 任务状态 / 优先级
TASK_STATUSES: tuple[str, ...] = ("pending", "in_progress", "completed", "cancelled")
TASK_PRIORITIES: tuple[str, ...] = ("low", "medium", "high", "urgent")


# ---------------------------------------------------------------- 工作区
class WorkspaceCreate(SchemaBase):
    name: str = Field(min_length=1, max_length=255)
    slug: Optional[str] = Field(default=None, max_length=255, description="留空则按 name 生成")
    description: Optional[str] = None


class WorkspaceUpdate(SchemaBase):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = None
    is_active: Optional[bool] = None


class WorkspaceOut(SchemaBase):
    id: int
    name: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    owner_id: Optional[int] = None
    is_active: bool = True
    member_count: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# ---------------------------------------------------------------- 成员
class MemberAdd(SchemaBase):
    user_id: int
    role: str = Field(default="viewer", max_length=20)


class MemberRoleUpdate(SchemaBase):
    role: str = Field(max_length=20)


class MemberOut(SchemaBase):
    id: int
    workspace_id: Optional[int] = None
    user_id: Optional[int] = None
    role: Optional[str] = None
    joined_at: Optional[datetime] = None
    is_active: bool = True
    username: Optional[str] = None
    email: Optional[str] = None


# ---------------------------------------------------------------- 任务
class TaskCreate(SchemaBase):
    title: str = Field(min_length=1, max_length=255)
    description: Optional[str] = None
    assigned_to: Optional[int] = None
    priority: str = Field(default="medium", max_length=20)
    due_date: Optional[datetime] = None


class TaskUpdate(SchemaBase):
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = None
    status: Optional[str] = Field(default=None, max_length=20)
    priority: Optional[str] = Field(default=None, max_length=20)
    assigned_to: Optional[int] = None
    due_date: Optional[datetime] = None


class TaskOut(SchemaBase):
    id: int
    workspace_id: Optional[int] = None
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    assigned_to: Optional[int] = None
    created_by: Optional[int] = None
    due_date: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# ---------------------------------------------------------------- 团队评论
class CommentCreate(SchemaBase):
    content_type: str = Field(min_length=1, max_length=50, description="如 article / page")
    content_id: int
    text: str = Field(min_length=1, description="评论正文（入库前 HTML 转义）")
    parent_id: Optional[int] = Field(default=None, description="父评论 ID（支持嵌套回复）")
    mentions: Optional[list[int]] = Field(default=None, description="@ 到的用户 ID 列表")


class CommentUpdate(SchemaBase):
    text: str = Field(min_length=1)


class CommentOut(SchemaBase):
    id: int
    content_type: Optional[str] = None
    content_id: Optional[int] = None
    author_id: Optional[int] = None
    author_name: Optional[str] = None
    parent_id: Optional[int] = None
    text: Optional[str] = None
    mentions: Optional[list[int]] = None
    is_resolved: bool = False
    resolved_by: Optional[int] = None
    resolved_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# ---------------------------------------------------------------- 邀请
class InviteCreate(SchemaBase):
    target_type: str = Field(min_length=1, max_length=50, description="article / workspace")
    target_id: int
    permission: str = Field(default="edit", max_length=20)
    expire_hours: int = Field(default=24, ge=1, le=24 * 30, description="有效小时数")
    max_uses: int = Field(default=0, ge=0, description="最大使用次数，0 = 不限")


class InviteOut(SchemaBase):
    id: int
    invite_code: Optional[str] = None
    target_type: Optional[str] = None
    target_id: Optional[int] = None
    permission: Optional[str] = None
    creator_id: Optional[int] = None
    expires_at: Optional[datetime] = None
    max_uses: int = 0
    use_count: int = 0
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class InviteAcceptRequest(SchemaBase):
    invite_code: str = Field(min_length=1, max_length=64)


# ---------------------------------------------------------------- 协同文档
class DocumentSaveRequest(SchemaBase):
    """把前端上报的 HTML 快照落库（CRDT 二进制状态走 Redis，见 yjs_service）"""

    html: str = Field(min_length=1, description="富文本正文的 HTML 快照")
    change_summary: Optional[str] = Field(default=None, max_length=255)
