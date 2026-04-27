from sqlalchemy.orm import declarative_base

Base = declarative_base()



from .article import Article
from .article_content import ArticleContent
from .article_i18n import ArticleI18n
from .article_like import ArticleLike
from .article_revision import ArticleRevision
from .article_seo import ArticleSEO
from .block_pattern import BlockPattern
from .capability import Capability
from .category import Category
from .category_subscription import CategorySubscription
from .comment import Comment
from .comment_subscription import CommentSubscription
from .comment_vote import CommentVote
from .custom_field import CustomField
from .custom_post_type import CustomPostType
from .email_subscription import EmailSubscription
from .file_hash import FileHash
from .form import Form
from .form_field import FormField
from .form_submission import FormSubmission
from .media import Media
from .media_folder import MediaFolder
from .menu_items import MenuItems
from .menu_location import MenuLocation
from .menu_location_assignment import MenuLocationAssignment
from .menus import Menus
from .notification import Notification
from .o_auth_account import OAuthAccount
from .page_view import PageView
from .pages import Pages
from .plugin import Plugin
from .role import Role
from .search_history import SearchHistory
from .system_settings import SystemSettings
from .theme import Theme
from .upload_chunk import UploadChunk
from .upload_task import UploadTask
from .user import User
from .user_activity import UserActivity
from .user_role import UserRole
from .vip_feature import VIPFeature
from .vip_plan import VIPPlan
from .vip_subscription import VIPSubscription
from .widget_instance import WidgetInstance

# ==================== 自动生成的导入 - 由 routes.yaml 管理 ====================
# 此部分由脚本自动生成 - 请勿手动修改

__all__ = [
    'Base',
    'User',
    'Article',
    'Category',
    'CategorySubscription',
    'Media',
    'MediaFolder',
    'SystemSettings',
    'ArticleContent',
    'ArticleI18n',
    'ArticleLike',
    'FileHash',
    'Menus',
    'MenuItems',
    'MenuLocation',
    'MenuLocationAssignment',
    'Pages',
    'UploadTask',
    'UploadChunk',
    'Notification',
    'SearchHistory',
    'PageView',
    'UserActivity',
    'VIPPlan',
    'VIPSubscription',
    'VIPFeature',
    'CustomField',
    'EmailSubscription',
    'ArticleRevision',
    'Plugin',
    'Theme',
    'Form',
    'FormField',
    'FormSubmission',
    'WidgetInstance',
    'BlockPattern',
    'CustomPostType',
    'CommentVote',
    'CommentSubscription',
    'Comment',
    'Role',
    'Capability',
    'UserRole',
    'OAuthAccount',
    'ArticleSEO'
]
# ============================================================================
