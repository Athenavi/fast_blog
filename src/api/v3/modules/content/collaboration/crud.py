"""collaboration 模块的数据访问层（唯一 DB 访问点）

四张既有表（``workspaces`` / ``workspace_members`` / ``tasks`` / ``team_comments``）
+ 本批次新建的 ``collaboration_invites``。
"""

from shared.models.collaboration import (
    CollaborationInvite,
    Task,
    Workspace,
    WorkspaceMember,
)
from shared.models.comment.team_comment import TeamComment
from src.api.v3.core.base_crud import CRUDBase


class WorkspaceCRUD(CRUDBase[Workspace, dict, dict]):
    model = Workspace
    #: ``slug`` 是工作区的对外标识（唯一）
    keyword_fields = ("name", "slug", "description")
    default_order_by = "id"


class WorkspaceMemberCRUD(CRUDBase[WorkspaceMember, dict, dict]):
    model = WorkspaceMember
    default_order_by = "id"


class TaskCRUD(CRUDBase[Task, dict, dict]):
    model = Task
    keyword_fields = ("title", "description")
    #: 任务以创建时间为序（新在前）
    default_order_by = "created_at"


class TeamCommentCRUD(CRUDBase[TeamComment, dict, dict]):
    model = TeamComment
    keyword_fields = ("text",)
    default_order_by = "created_at"


class CollaborationInviteCRUD(CRUDBase[CollaborationInvite, dict, dict]):
    model = CollaborationInvite
    keyword_fields = ("invite_code", "target_type")
    default_order_by = "id"


workspace_crud = WorkspaceCRUD()
workspace_member_crud = WorkspaceMemberCRUD()
task_crud = TaskCRUD()
team_comment_crud = TeamCommentCRUD()
collaboration_invite_crud = CollaborationInviteCRUD()
