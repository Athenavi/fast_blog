from sqlalchemy.orm import declarative_base

Base = declarative_base()


from .audit_log import AuditLog
from .ai_workflow import AIWorkflow
from .page_builder import PageBuilder
from .global_style import GlobalStyle
from .field_permission import FieldPermission
from .subscription_plan import SubscriptionPlan
from .user_subscription import UserSubscription
from .theme_package import ThemePackage
from .user import User
from .article import Article
from .category import Category
from .category_subscription import CategorySubscription
from .media import Media
from .media_folder import MediaFolder
from .media_optimization import MediaOptimization
from .article_revision_note import ArticleRevisionNote
from .system_settings import SystemSettings
from .article_content import ArticleContent
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
from .o_auth_account import OAuthAccount
from .article_seo import ArticleSEO
from .share_stat import ShareStat
from .product import Product
from .cart import Cart
from .cart_item import CartItem
from .order import Order
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
from .chat_group import ChatGroup
from .chat_group_member import ChatGroupMember
from .chat_group_invite import ChatGroupInvite
from .scheduled_report import ScheduledReport
from .report_history import ReportHistory
from .article_annotation import ArticleAnnotation
from .webhook import Webhook
from .webhook_delivery import WebhookDelivery
from .role import Role
from .capability import Capability
from .role_capability import RoleCapability
from .user_role import UserRole
from .permission_audit_log import PermissionAuditLog
from .workspace import Workspace
from .workspace_member import WorkspaceMember
from .task import Task
from .approval_record import ApprovalRecord
from .approval_step import ApprovalStep
from .site import Site
from .site_user import SiteUser
from .content_mapping import ContentMapping
from .google_analytics_config import GoogleAnalyticsConfig
from .baidu_analytics_config import BaiduAnalyticsConfig
from .notification_integration import NotificationIntegration
from .email_service_config import EmailServiceConfig
from .saml_config import SAMLConfig
from .ldap_config import LDAPConfig
from .sso_provider import SSOProvider
from .payment_gateway import PaymentGateway
from .payment_transaction import PaymentTransaction
from .crypto_payment import CryptoPayment
from .tax_config import TaxConfig
from .order_item import OrderItem
from .enterprise_license import EnterpriseLicense
from .support_ticket import SupportTicket
from .support_ticket_reply import SupportTicketReply
from .deployment_script import DeploymentScript
from .deployment_log import DeploymentLog
from .monitoring_alert import MonitoringAlert
from .monitoring_metric import MonitoringMetric
from .migration_task import MigrationTask
from .migration_log import MigrationLog
from .global_style_config import GlobalStyleConfig

# ==================== 自动生成的导入 - 由 routes.yaml 管理 ====================
# 此部分由脚本自动生成 - 请勿手动修改

__all__ = [
    'Base',
    'AuditLog',
    'AIWorkflow',
    'PageBuilder',
    'GlobalStyle',
    'FieldPermission',
    'SubscriptionPlan',
    'UserSubscription',
    'ThemePackage',
    'User',
    'Article',
    'Category',
    'CategorySubscription',
    'Media',
    'MediaFolder',
    'MediaOptimization',
    'ArticleRevisionNote',
    'SystemSettings',
    'ArticleContent',
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
    'OAuthAccount',
    'ArticleSEO',
    'ShareStat',
    'Product',
    'Cart',
    'CartItem',
    'Order',
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
    'UserRevenueStats',
    'ChatGroup',
    'ChatGroupMember',
    'ChatGroupInvite',
    'ScheduledReport',
    'ReportHistory',
    'ArticleAnnotation',
    'Webhook',
    'WebhookDelivery',
    'Role',
    'Capability',
    'RoleCapability',
    'UserRole',
    'PermissionAuditLog',
    'Workspace',
    'WorkspaceMember',
    'Task',
    'ApprovalRecord',
    'ApprovalStep',
    'Site',
    'SiteUser',
    'ContentMapping',
    'GoogleAnalyticsConfig',
    'BaiduAnalyticsConfig',
    'NotificationIntegration',
    'EmailServiceConfig',
    'SAMLConfig',
    'LDAPConfig',
    'SSOProvider',
    'PaymentGateway',
    'PaymentTransaction',
    'CryptoPayment',
    'TaxConfig',
    'OrderItem',
    'EnterpriseLicense',
    'SupportTicket',
    'SupportTicketReply',
    'DeploymentScript',
    'DeploymentLog',
    'MonitoringAlert',
    'MonitoringMetric',
    'MigrationTask',
    'MigrationLog',
    'GlobalStyleConfig'
]
# ============================================================================
