from sqlalchemy.orm import declarative_base

Base = declarative_base()

from .user import User
from .article import Article
from .category import Category
from .category_subscription import CategorySubscription
from .media import Media
from .media_folder import MediaFolder
from .system_settings import SystemSettings
from .article_content import ArticleContent
from .article_i18n import ArticleI18n
from .article_like import ArticleLike
from .file_hash import FileHash
from .menus import Menus
from .menu_items import MenuItems
from .menu_location import MenuLocation
from .menu_location_assignment import MenuLocationAssignment
from .pages import Pages
from .upload_task import UploadTask
from .upload_chunk import UploadChunk
from .download_task import DownloadTask
from .notification import Notification
from .private_message import PrivateMessage
from .user_block import UserBlock
from .search_history import SearchHistory
from .search_index import SearchIndex
from .page_view import PageView
from .user_activity import UserActivity
from .vip_plan import VIPPlan
from .vip_subscription import VIPSubscription
from .vip_feature import VIPFeature
from .custom_field import CustomField
from .email_subscription import EmailSubscription
from .article_revision import ArticleRevision
from .plugin import Plugin
from .theme import Theme
from .form import Form
from .form_field import FormField
from .form_submission import FormSubmission
from .widget_instance import WidgetInstance
from .block_pattern import BlockPattern
from .custom_post_type import CustomPostType
from .comment_vote import CommentVote
from .comment_subscription import CommentSubscription
from .comment import Comment
from .role import Role
from .capability import Capability
from .user_role import UserRole
from .o_auth_account import OAuthAccount
from .article_seo import ArticleSEO
from .share_stat import ShareStat
from .product import Product
from .cart import Cart
from .cart_item import CartItem
from .order import Order
from .order_item import OrderItem
from .site import Site
from .sensitive_word import SensitiveWord
from .user_session import UserSession
from .login_attempt import LoginAttempt
from .token_blacklist import TokenBlacklist
from .ad_placement import AdPlacement
from .ad import Ad
from .ad_click import AdClick
from .ad_impression import AdImpression
from .revenue_record import RevenueRecord
from .revenue_sharing_config import RevenueSharingConfig
from .payout_request import PayoutRequest
from .user_revenue_stats import UserRevenueStats

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
    'DownloadTask',
    'Notification',
    'PrivateMessage',
    'UserBlock',
    'SearchHistory',
    'SearchIndex',
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
    'ArticleSEO',
    'ShareStat',
    'Product',
    'Cart',
    'CartItem',
    'Order',
    'OrderItem',
    'Site',
    'SensitiveWord',
    'UserSession',
    'LoginAttempt',
    'TokenBlacklist',
    'AdPlacement',
    'Ad',
    'AdClick',
    'AdImpression',
    'RevenueRecord',
    'RevenueSharingConfig',
    'PayoutRequest',
    'UserRevenueStats'
]
# ============================================================================
