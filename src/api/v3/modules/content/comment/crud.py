"""comment 模块的数据访问层（唯一 DB 访问点）"""

from shared.models.comment.comment import Comment
from src.api.v3.core.base_crud import CRUDBase


class CommentCRUD(CRUDBase[Comment, dict, dict]):
    model = Comment
    keyword_fields = ("content", "author_name", "author_email")
    default_order_by = "id"


comment_crud = CommentCRUD()
