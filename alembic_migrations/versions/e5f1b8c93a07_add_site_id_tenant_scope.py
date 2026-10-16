"""add site_id tenant scope

Revision ID: e5f1b8c93a07
Revises: d4e9a1c7f2b8
Create Date: 2026-10-14 00:00:00.000000

给**站点级**表补 ``site_id``：多租户隔离的落点。清单与判定原则见 ``config/tenancy.yaml``，
由 ``python -m scripts.apply_tenant_scope`` 生成。

隔离行为由 ``src/api/v3/core/tenancy.py`` + ``base_crud._apply_site_scope`` 实现：
有 ``site_id`` 列 + 上下文有站点 + 未显式跨站点，三者同时成立才收窄查询。

``nullable=True`` 且**不回填**：存量数据归属由部署者决定（通常是默认站点），
回填脚本用 ``UPDATE <table> SET site_id = <默认站点ID> WHERE site_id IS NULL``。
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'e5f1b8c93a07'
down_revision: Union[str, Sequence[str], None] = 'd4e9a1c7f2b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'ad_clicks',
        sa.Column('site_id', sa.BigInteger(), nullable=True, doc='所属站点 ID（多租户隔离键）'),
    )
    op.create_index('ix_ad_clicks_site_id', 'ad_clicks', ['site_id'])

    op.add_column(
        'ad_impressions',
        sa.Column('site_id', sa.BigInteger(), nullable=True, doc='所属站点 ID（多租户隔离键）'),
    )
    op.create_index('ix_ad_impressions_site_id', 'ad_impressions', ['site_id'])

    op.add_column(
        'ad_placements',
        sa.Column('site_id', sa.BigInteger(), nullable=True, doc='所属站点 ID（多租户隔离键）'),
    )
    op.create_index('ix_ad_placements_site_id', 'ad_placements', ['site_id'])

    op.add_column(
        'ads',
        sa.Column('site_id', sa.BigInteger(), nullable=True, doc='所属站点 ID（多租户隔离键）'),
    )
    op.create_index('ix_ads_site_id', 'ads', ['site_id'])

    op.add_column(
        'approval_records',
        sa.Column('site_id', sa.BigInteger(), nullable=True, doc='所属站点 ID（多租户隔离键）'),
    )
    op.create_index('ix_approval_records_site_id', 'approval_records', ['site_id'])

    op.add_column(
        'approval_steps',
        sa.Column('site_id', sa.BigInteger(), nullable=True, doc='所属站点 ID（多租户隔离键）'),
    )
    op.create_index('ix_approval_steps_site_id', 'approval_steps', ['site_id'])

    op.add_column(
        'article_annotations',
        sa.Column('site_id', sa.BigInteger(), nullable=True, doc='所属站点 ID（多租户隔离键）'),
    )
    op.create_index('ix_article_annotations_site_id', 'article_annotations', ['site_id'])

    op.add_column(
        'article_content',
        sa.Column('site_id', sa.BigInteger(), nullable=True, doc='所属站点 ID（多租户隔离键）'),
    )
    op.create_index('ix_article_content_site_id', 'article_content', ['site_id'])

    op.add_column(
        'article_likes',
        sa.Column('site_id', sa.BigInteger(), nullable=True, doc='所属站点 ID（多租户隔离键）'),
    )
    op.create_index('ix_article_likes_site_id', 'article_likes', ['site_id'])

    op.add_column(
        'article_preview_tokens',
        sa.Column('site_id', sa.BigInteger(), nullable=True, doc='所属站点 ID（多租户隔离键）'),
    )
    op.create_index('ix_article_preview_tokens_site_id', 'article_preview_tokens', ['site_id'])

    op.add_column(
        'article_revision_notes',
        sa.Column('site_id', sa.BigInteger(), nullable=True, doc='所属站点 ID（多租户隔离键）'),
    )
    op.create_index('ix_article_revision_notes_site_id', 'article_revision_notes', ['site_id'])

    op.add_column(
        'article_revisions',
        sa.Column('site_id', sa.BigInteger(), nullable=True, doc='所属站点 ID（多租户隔离键）'),
    )
    op.create_index('ix_article_revisions_site_id', 'article_revisions', ['site_id'])

    op.add_column(
        'article_seo',
        sa.Column('site_id', sa.BigInteger(), nullable=True, doc='所属站点 ID（多租户隔离键）'),
    )
    op.create_index('ix_article_seo_site_id', 'article_seo', ['site_id'])

    op.add_column(
        'articles',
        sa.Column('site_id', sa.BigInteger(), nullable=True, doc='所属站点 ID（多租户隔离键）'),
    )
    op.create_index('ix_articles_site_id', 'articles', ['site_id'])

    op.add_column(
        'badge_definitions',
        sa.Column('site_id', sa.BigInteger(), nullable=True, doc='所属站点 ID（多租户隔离键）'),
    )
    op.create_index('ix_badge_definitions_site_id', 'badge_definitions', ['site_id'])

    op.add_column(
        'block_patterns',
        sa.Column('site_id', sa.BigInteger(), nullable=True, doc='所属站点 ID（多租户隔离键）'),
    )
    op.create_index('ix_block_patterns_site_id', 'block_patterns', ['site_id'])

    op.add_column(
        'cart_items',
        sa.Column('site_id', sa.BigInteger(), nullable=True, doc='所属站点 ID（多租户隔离键）'),
    )
    op.create_index('ix_cart_items_site_id', 'cart_items', ['site_id'])

    op.add_column(
        'carts',
        sa.Column('site_id', sa.BigInteger(), nullable=True, doc='所属站点 ID（多租户隔离键）'),
    )
    op.create_index('ix_carts_site_id', 'carts', ['site_id'])

    op.add_column(
        'categories',
        sa.Column('site_id', sa.BigInteger(), nullable=True, doc='所属站点 ID（多租户隔离键）'),
    )
    op.create_index('ix_categories_site_id', 'categories', ['site_id'])

    op.add_column(
        'category_subscriptions',
        sa.Column('site_id', sa.BigInteger(), nullable=True, doc='所属站点 ID（多租户隔离键）'),
    )
    op.create_index('ix_category_subscriptions_site_id', 'category_subscriptions', ['site_id'])

    op.add_column(
        'certification_documents',
        sa.Column('site_id', sa.BigInteger(), nullable=True, doc='所属站点 ID（多租户隔离键）'),
    )
    op.create_index('ix_certification_documents_site_id', 'certification_documents', ['site_id'])

    op.add_column(
        'certification_reviews',
        sa.Column('site_id', sa.BigInteger(), nullable=True, doc='所属站点 ID（多租户隔离键）'),
    )
    op.create_index('ix_certification_reviews_site_id', 'certification_reviews', ['site_id'])

    op.add_column(
        'chat_group_invites',
        sa.Column('site_id', sa.BigInteger(), nullable=True, doc='所属站点 ID（多租户隔离键）'),
    )
    op.create_index('ix_chat_group_invites_site_id', 'chat_group_invites', ['site_id'])

    op.add_column(
        'chat_group_members',
        sa.Column('site_id', sa.BigInteger(), nullable=True, doc='所属站点 ID（多租户隔离键）'),
    )
    op.create_index('ix_chat_group_members_site_id', 'chat_group_members', ['site_id'])

    op.add_column(
        'chat_groups',
        sa.Column('site_id', sa.BigInteger(), nullable=True, doc='所属站点 ID（多租户隔离键）'),
    )
    op.create_index('ix_chat_groups_site_id', 'chat_groups', ['site_id'])

    op.add_column(
        'chat_messages',
        sa.Column('site_id', sa.BigInteger(), nullable=True, doc='所属站点 ID（多租户隔离键）'),
    )
    op.create_index('ix_chat_messages_site_id', 'chat_messages', ['site_id'])

    op.add_column(
        'collaboration_invites',
        sa.Column('site_id', sa.BigInteger(), nullable=True, doc='所属站点 ID（多租户隔离键）'),
    )
    op.create_index('ix_collaboration_invites_site_id', 'collaboration_invites', ['site_id'])

    op.add_column(
        'comment_subscriptions',
        sa.Column('site_id', sa.BigInteger(), nullable=True, doc='所属站点 ID（多租户隔离键）'),
    )
    op.create_index('ix_comment_subscriptions_site_id', 'comment_subscriptions', ['site_id'])

    op.add_column(
        'comment_votes',
        sa.Column('site_id', sa.BigInteger(), nullable=True, doc='所属站点 ID（多租户隔离键）'),
    )
    op.create_index('ix_comment_votes_site_id', 'comment_votes', ['site_id'])

    op.add_column(
        'comments',
        sa.Column('site_id', sa.BigInteger(), nullable=True, doc='所属站点 ID（多租户隔离键）'),
    )
    op.create_index('ix_comments_site_id', 'comments', ['site_id'])

    op.add_column(
        'crypto_payments',
        sa.Column('site_id', sa.BigInteger(), nullable=True, doc='所属站点 ID（多租户隔离键）'),
    )
    op.create_index('ix_crypto_payments_site_id', 'crypto_payments', ['site_id'])

    op.add_column(
        'custom_fields',
        sa.Column('site_id', sa.BigInteger(), nullable=True, doc='所属站点 ID（多租户隔离键）'),
    )
    op.create_index('ix_custom_fields_site_id', 'custom_fields', ['site_id'])

    op.add_column(
        'custom_post_contents',
        sa.Column('site_id', sa.BigInteger(), nullable=True, doc='所属站点 ID（多租户隔离键）'),
    )
    op.create_index('ix_custom_post_contents_site_id', 'custom_post_contents', ['site_id'])

    op.add_column(
        'custom_post_types',
        sa.Column('site_id', sa.BigInteger(), nullable=True, doc='所属站点 ID（多租户隔离键）'),
    )
    op.create_index('ix_custom_post_types_site_id', 'custom_post_types', ['site_id'])

    op.add_column(
        'deployment_logs',
        sa.Column('site_id', sa.BigInteger(), nullable=True, doc='所属站点 ID（多租户隔离键）'),
    )
    op.create_index('ix_deployment_logs_site_id', 'deployment_logs', ['site_id'])

    op.add_column(
        'download_tasks',
        sa.Column('site_id', sa.BigInteger(), nullable=True, doc='所属站点 ID（多租户隔离键）'),
    )
    op.create_index('ix_download_tasks_site_id', 'download_tasks', ['site_id'])

    op.add_column(
        'email_subscriptions',
        sa.Column('site_id', sa.BigInteger(), nullable=True, doc='所属站点 ID（多租户隔离键）'),
    )
    op.create_index('ix_email_subscriptions_site_id', 'email_subscriptions', ['site_id'])

    op.add_column(
        'enterprise_licenses',
        sa.Column('site_id', sa.BigInteger(), nullable=True, doc='所属站点 ID（多租户隔离键）'),
    )
    op.create_index('ix_enterprise_licenses_site_id', 'enterprise_licenses', ['site_id'])

    op.add_column(
        'expert_certifications',
        sa.Column('site_id', sa.BigInteger(), nullable=True, doc='所属站点 ID（多租户隔离键）'),
    )
    op.create_index('ix_expert_certifications_site_id', 'expert_certifications', ['site_id'])

    op.add_column(
        'file_hashs',
        sa.Column('site_id', sa.BigInteger(), nullable=True, doc='所属站点 ID（多租户隔离键）'),
    )
    op.create_index('ix_file_hashs_site_id', 'file_hashs', ['site_id'])

    op.add_column(
        'form_fields',
        sa.Column('site_id', sa.BigInteger(), nullable=True, doc='所属站点 ID（多租户隔离键）'),
    )
    op.create_index('ix_form_fields_site_id', 'form_fields', ['site_id'])

    op.add_column(
        'form_submissions',
        sa.Column('site_id', sa.BigInteger(), nullable=True, doc='所属站点 ID（多租户隔离键）'),
    )
    op.create_index('ix_form_submissions_site_id', 'form_submissions', ['site_id'])

    op.add_column(
        'forms',
        sa.Column('site_id', sa.BigInteger(), nullable=True, doc='所属站点 ID（多租户隔离键）'),
    )
    op.create_index('ix_forms_site_id', 'forms', ['site_id'])

    op.add_column(
        'global_style_configs',
        sa.Column('site_id', sa.BigInteger(), nullable=True, doc='所属站点 ID（多租户隔离键）'),
    )
    op.create_index('ix_global_style_configs_site_id', 'global_style_configs', ['site_id'])

    op.add_column(
        'global_styles',
        sa.Column('site_id', sa.BigInteger(), nullable=True, doc='所属站点 ID（多租户隔离键）'),
    )
    op.create_index('ix_global_styles_site_id', 'global_styles', ['site_id'])

    op.add_column(
        'media',
        sa.Column('site_id', sa.BigInteger(), nullable=True, doc='所属站点 ID（多租户隔离键）'),
    )
    op.create_index('ix_media_site_id', 'media', ['site_id'])

    op.add_column(
        'media_folders',
        sa.Column('site_id', sa.BigInteger(), nullable=True, doc='所属站点 ID（多租户隔离键）'),
    )
    op.create_index('ix_media_folders_site_id', 'media_folders', ['site_id'])

    op.add_column(
        'media_optimizations',
        sa.Column('site_id', sa.BigInteger(), nullable=True, doc='所属站点 ID（多租户隔离键）'),
    )
    op.create_index('ix_media_optimizations_site_id', 'media_optimizations', ['site_id'])

    op.add_column(
        'menu_items',
        sa.Column('site_id', sa.BigInteger(), nullable=True, doc='所属站点 ID（多租户隔离键）'),
    )
    op.create_index('ix_menu_items_site_id', 'menu_items', ['site_id'])

    op.add_column(
        'menu_location_assignments',
        sa.Column('site_id', sa.BigInteger(), nullable=True, doc='所属站点 ID（多租户隔离键）'),
    )
    op.create_index('ix_menu_location_assignments_site_id', 'menu_location_assignments', ['site_id'])

    op.add_column(
        'menu_locations',
        sa.Column('site_id', sa.BigInteger(), nullable=True, doc='所属站点 ID（多租户隔离键）'),
    )
    op.create_index('ix_menu_locations_site_id', 'menu_locations', ['site_id'])

    op.add_column(
        'menus',
        sa.Column('site_id', sa.BigInteger(), nullable=True, doc='所属站点 ID（多租户隔离键）'),
    )
    op.create_index('ix_menus_site_id', 'menus', ['site_id'])

    op.add_column(
        'migration_logs',
        sa.Column('site_id', sa.BigInteger(), nullable=True, doc='所属站点 ID（多租户隔离键）'),
    )
    op.create_index('ix_migration_logs_site_id', 'migration_logs', ['site_id'])

    op.add_column(
        'migration_tasks',
        sa.Column('site_id', sa.BigInteger(), nullable=True, doc='所属站点 ID（多租户隔离键）'),
    )
    op.create_index('ix_migration_tasks_site_id', 'migration_tasks', ['site_id'])

    op.add_column(
        'notifications',
        sa.Column('site_id', sa.BigInteger(), nullable=True, doc='所属站点 ID（多租户隔离键）'),
    )
    op.create_index('ix_notifications_site_id', 'notifications', ['site_id'])

    op.add_column(
        'order_items',
        sa.Column('site_id', sa.BigInteger(), nullable=True, doc='所属站点 ID（多租户隔离键）'),
    )
    op.create_index('ix_order_items_site_id', 'order_items', ['site_id'])

    op.add_column(
        'orders',
        sa.Column('site_id', sa.BigInteger(), nullable=True, doc='所属站点 ID（多租户隔离键）'),
    )
    op.create_index('ix_orders_site_id', 'orders', ['site_id'])

    op.add_column(
        'page_builder',
        sa.Column('site_id', sa.BigInteger(), nullable=True, doc='所属站点 ID（多租户隔离键）'),
    )
    op.create_index('ix_page_builder_site_id', 'page_builder', ['site_id'])

    op.add_column(
        'page_views',
        sa.Column('site_id', sa.BigInteger(), nullable=True, doc='所属站点 ID（多租户隔离键）'),
    )
    op.create_index('ix_page_views_site_id', 'page_views', ['site_id'])

    op.add_column(
        'pages',
        sa.Column('site_id', sa.BigInteger(), nullable=True, doc='所属站点 ID（多租户隔离键）'),
    )
    op.create_index('ix_pages_site_id', 'pages', ['site_id'])

    op.add_column(
        'payment_transactions',
        sa.Column('site_id', sa.BigInteger(), nullable=True, doc='所属站点 ID（多租户隔离键）'),
    )
    op.create_index('ix_payment_transactions_site_id', 'payment_transactions', ['site_id'])

    op.add_column(
        'payout_requests',
        sa.Column('site_id', sa.BigInteger(), nullable=True, doc='所属站点 ID（多租户隔离键）'),
    )
    op.create_index('ix_payout_requests_site_id', 'payout_requests', ['site_id'])

    op.add_column(
        'points_rules',
        sa.Column('site_id', sa.BigInteger(), nullable=True, doc='所属站点 ID（多租户隔离键）'),
    )
    op.create_index('ix_points_rules_site_id', 'points_rules', ['site_id'])

    op.add_column(
        'points_transactions',
        sa.Column('site_id', sa.BigInteger(), nullable=True, doc='所属站点 ID（多租户隔离键）'),
    )
    op.create_index('ix_points_transactions_site_id', 'points_transactions', ['site_id'])

    op.add_column(
        'private_messages',
        sa.Column('site_id', sa.BigInteger(), nullable=True, doc='所属站点 ID（多租户隔离键）'),
    )
    op.create_index('ix_private_messages_site_id', 'private_messages', ['site_id'])

    op.add_column(
        'products',
        sa.Column('site_id', sa.BigInteger(), nullable=True, doc='所属站点 ID（多租户隔离键）'),
    )
    op.create_index('ix_products_site_id', 'products', ['site_id'])

    op.add_column(
        'publish_channels',
        sa.Column('site_id', sa.BigInteger(), nullable=True, doc='所属站点 ID（多租户隔离键）'),
    )
    op.create_index('ix_publish_channels_site_id', 'publish_channels', ['site_id'])

    op.add_column(
        'publish_logs',
        sa.Column('site_id', sa.BigInteger(), nullable=True, doc='所属站点 ID（多租户隔离键）'),
    )
    op.create_index('ix_publish_logs_site_id', 'publish_logs', ['site_id'])

    op.add_column(
        'publish_tasks',
        sa.Column('site_id', sa.BigInteger(), nullable=True, doc='所属站点 ID（多租户隔离键）'),
    )
    op.create_index('ix_publish_tasks_site_id', 'publish_tasks', ['site_id'])

    op.add_column(
        'report_history',
        sa.Column('site_id', sa.BigInteger(), nullable=True, doc='所属站点 ID（多租户隔离键）'),
    )
    op.create_index('ix_report_history_site_id', 'report_history', ['site_id'])

    op.add_column(
        'revenue_records',
        sa.Column('site_id', sa.BigInteger(), nullable=True, doc='所属站点 ID（多租户隔离键）'),
    )
    op.create_index('ix_revenue_records_site_id', 'revenue_records', ['site_id'])

    op.add_column(
        'revenue_sharing_configs',
        sa.Column('site_id', sa.BigInteger(), nullable=True, doc='所属站点 ID（多租户隔离键）'),
    )
    op.create_index('ix_revenue_sharing_configs_site_id', 'revenue_sharing_configs', ['site_id'])

    op.add_column(
        'scheduled_reports',
        sa.Column('site_id', sa.BigInteger(), nullable=True, doc='所属站点 ID（多租户隔离键）'),
    )
    op.create_index('ix_scheduled_reports_site_id', 'scheduled_reports', ['site_id'])

    op.add_column(
        'search_history',
        sa.Column('site_id', sa.BigInteger(), nullable=True, doc='所属站点 ID（多租户隔离键）'),
    )
    op.create_index('ix_search_history_site_id', 'search_history', ['site_id'])

    op.add_column(
        'sensitive_words',
        sa.Column('site_id', sa.BigInteger(), nullable=True, doc='所属站点 ID（多租户隔离键）'),
    )
    op.create_index('ix_sensitive_words_site_id', 'sensitive_words', ['site_id'])

    op.add_column(
        'seo_redirects',
        sa.Column('site_id', sa.BigInteger(), nullable=True, doc='所属站点 ID（多租户隔离键）'),
    )
    op.create_index('ix_seo_redirects_site_id', 'seo_redirects', ['site_id'])

    op.add_column(
        'share_stats',
        sa.Column('site_id', sa.BigInteger(), nullable=True, doc='所属站点 ID（多租户隔离键）'),
    )
    op.create_index('ix_share_stats_site_id', 'share_stats', ['site_id'])

    op.add_column(
        'shortcodes',
        sa.Column('site_id', sa.BigInteger(), nullable=True, doc='所属站点 ID（多租户隔离键）'),
    )
    op.create_index('ix_shortcodes_site_id', 'shortcodes', ['site_id'])

    op.add_column(
        'sla_reports',
        sa.Column('site_id', sa.BigInteger(), nullable=True, doc='所属站点 ID（多租户隔离键）'),
    )
    op.create_index('ix_sla_reports_site_id', 'sla_reports', ['site_id'])

    op.add_column(
        'support_ticket_replies',
        sa.Column('site_id', sa.BigInteger(), nullable=True, doc='所属站点 ID（多租户隔离键）'),
    )
    op.create_index('ix_support_ticket_replies_site_id', 'support_ticket_replies', ['site_id'])

    op.add_column(
        'support_tickets',
        sa.Column('site_id', sa.BigInteger(), nullable=True, doc='所属站点 ID（多租户隔离键）'),
    )
    op.create_index('ix_support_tickets_site_id', 'support_tickets', ['site_id'])

    op.add_column(
        'tasks',
        sa.Column('site_id', sa.BigInteger(), nullable=True, doc='所属站点 ID（多租户隔离键）'),
    )
    op.create_index('ix_tasks_site_id', 'tasks', ['site_id'])

    op.add_column(
        'team_comments',
        sa.Column('site_id', sa.BigInteger(), nullable=True, doc='所属站点 ID（多租户隔离键）'),
    )
    op.create_index('ix_team_comments_site_id', 'team_comments', ['site_id'])

    op.add_column(
        'tip_withdrawals',
        sa.Column('site_id', sa.BigInteger(), nullable=True, doc='所属站点 ID（多租户隔离键）'),
    )
    op.create_index('ix_tip_withdrawals_site_id', 'tip_withdrawals', ['site_id'])

    op.add_column(
        'tips',
        sa.Column('site_id', sa.BigInteger(), nullable=True, doc='所属站点 ID（多租户隔离键）'),
    )
    op.create_index('ix_tips_site_id', 'tips', ['site_id'])

    op.add_column(
        'upload_chunks',
        sa.Column('site_id', sa.BigInteger(), nullable=True, doc='所属站点 ID（多租户隔离键）'),
    )
    op.create_index('ix_upload_chunks_site_id', 'upload_chunks', ['site_id'])

    op.add_column(
        'upload_tasks',
        sa.Column('site_id', sa.BigInteger(), nullable=True, doc='所属站点 ID（多租户隔离键）'),
    )
    op.create_index('ix_upload_tasks_site_id', 'upload_tasks', ['site_id'])

    op.add_column(
        'user_activities',
        sa.Column('site_id', sa.BigInteger(), nullable=True, doc='所属站点 ID（多租户隔离键）'),
    )
    op.create_index('ix_user_activities_site_id', 'user_activities', ['site_id'])

    op.add_column(
        'user_badges',
        sa.Column('site_id', sa.BigInteger(), nullable=True, doc='所属站点 ID（多租户隔离键）'),
    )
    op.create_index('ix_user_badges_site_id', 'user_badges', ['site_id'])

    op.add_column(
        'user_blocks',
        sa.Column('site_id', sa.BigInteger(), nullable=True, doc='所属站点 ID（多租户隔离键）'),
    )
    op.create_index('ix_user_blocks_site_id', 'user_blocks', ['site_id'])

    op.add_column(
        'user_follows',
        sa.Column('site_id', sa.BigInteger(), nullable=True, doc='所属站点 ID（多租户隔离键）'),
    )
    op.create_index('ix_user_follows_site_id', 'user_follows', ['site_id'])

    op.add_column(
        'user_points',
        sa.Column('site_id', sa.BigInteger(), nullable=True, doc='所属站点 ID（多租户隔离键）'),
    )
    op.create_index('ix_user_points_site_id', 'user_points', ['site_id'])

    op.add_column(
        'user_revenue_stats',
        sa.Column('site_id', sa.BigInteger(), nullable=True, doc='所属站点 ID（多租户隔离键）'),
    )
    op.create_index('ix_user_revenue_stats_site_id', 'user_revenue_stats', ['site_id'])

    op.add_column(
        'vip_features',
        sa.Column('site_id', sa.BigInteger(), nullable=True, doc='所属站点 ID（多租户隔离键）'),
    )
    op.create_index('ix_vip_features_site_id', 'vip_features', ['site_id'])

    op.add_column(
        'vip_payment_orders',
        sa.Column('site_id', sa.BigInteger(), nullable=True, doc='所属站点 ID（多租户隔离键）'),
    )
    op.create_index('ix_vip_payment_orders_site_id', 'vip_payment_orders', ['site_id'])

    op.add_column(
        'vip_plans',
        sa.Column('site_id', sa.BigInteger(), nullable=True, doc='所属站点 ID（多租户隔离键）'),
    )
    op.create_index('ix_vip_plans_site_id', 'vip_plans', ['site_id'])

    op.add_column(
        'vip_subscriptions',
        sa.Column('site_id', sa.BigInteger(), nullable=True, doc='所属站点 ID（多租户隔离键）'),
    )
    op.create_index('ix_vip_subscriptions_site_id', 'vip_subscriptions', ['site_id'])

    op.add_column(
        'webhook_deliveries',
        sa.Column('site_id', sa.BigInteger(), nullable=True, doc='所属站点 ID（多租户隔离键）'),
    )
    op.create_index('ix_webhook_deliveries_site_id', 'webhook_deliveries', ['site_id'])

    op.add_column(
        'webhooks',
        sa.Column('site_id', sa.BigInteger(), nullable=True, doc='所属站点 ID（多租户隔离键）'),
    )
    op.create_index('ix_webhooks_site_id', 'webhooks', ['site_id'])

    op.add_column(
        'widget_instances',
        sa.Column('site_id', sa.BigInteger(), nullable=True, doc='所属站点 ID（多租户隔离键）'),
    )
    op.create_index('ix_widget_instances_site_id', 'widget_instances', ['site_id'])

    op.add_column(
        'workspace_members',
        sa.Column('site_id', sa.BigInteger(), nullable=True, doc='所属站点 ID（多租户隔离键）'),
    )
    op.create_index('ix_workspace_members_site_id', 'workspace_members', ['site_id'])

    op.add_column(
        'workspaces',
        sa.Column('site_id', sa.BigInteger(), nullable=True, doc='所属站点 ID（多租户隔离键）'),
    )
    op.create_index('ix_workspaces_site_id', 'workspaces', ['site_id'])

    # ---- 存量数据回填 ----
    # 不回填的话，隔离上线后这些行（site_id IS NULL）对**所有**站点都不可见，
    # 表现为"升级后内容全没了"。这里统一归属默认站点（未标默认则取最早的一个）；
    # sites 表为空时 COALESCE 得到 NULL，UPDATE 成为空操作。
    op.execute(
        "UPDATE ad_clicks SET site_id = COALESCE((SELECT id FROM sites WHERE is_default = true AND is_active = true ORDER BY id LIMIT 1),(SELECT id FROM sites ORDER BY id LIMIT 1)) WHERE site_id IS NULL"
    )

    op.execute(
        "UPDATE ad_impressions SET site_id = COALESCE((SELECT id FROM sites WHERE is_default = true AND is_active = true ORDER BY id LIMIT 1),(SELECT id FROM sites ORDER BY id LIMIT 1)) WHERE site_id IS NULL"
    )

    op.execute(
        "UPDATE ad_placements SET site_id = COALESCE((SELECT id FROM sites WHERE is_default = true AND is_active = true ORDER BY id LIMIT 1),(SELECT id FROM sites ORDER BY id LIMIT 1)) WHERE site_id IS NULL"
    )

    op.execute(
        "UPDATE ads SET site_id = COALESCE((SELECT id FROM sites WHERE is_default = true AND is_active = true ORDER BY id LIMIT 1),(SELECT id FROM sites ORDER BY id LIMIT 1)) WHERE site_id IS NULL"
    )

    op.execute(
        "UPDATE approval_records SET site_id = COALESCE((SELECT id FROM sites WHERE is_default = true AND is_active = true ORDER BY id LIMIT 1),(SELECT id FROM sites ORDER BY id LIMIT 1)) WHERE site_id IS NULL"
    )

    op.execute(
        "UPDATE approval_steps SET site_id = COALESCE((SELECT id FROM sites WHERE is_default = true AND is_active = true ORDER BY id LIMIT 1),(SELECT id FROM sites ORDER BY id LIMIT 1)) WHERE site_id IS NULL"
    )

    op.execute(
        "UPDATE article_annotations SET site_id = COALESCE((SELECT id FROM sites WHERE is_default = true AND is_active = true ORDER BY id LIMIT 1),(SELECT id FROM sites ORDER BY id LIMIT 1)) WHERE site_id IS NULL"
    )

    op.execute(
        "UPDATE article_content SET site_id = COALESCE((SELECT id FROM sites WHERE is_default = true AND is_active = true ORDER BY id LIMIT 1),(SELECT id FROM sites ORDER BY id LIMIT 1)) WHERE site_id IS NULL"
    )

    op.execute(
        "UPDATE article_likes SET site_id = COALESCE((SELECT id FROM sites WHERE is_default = true AND is_active = true ORDER BY id LIMIT 1),(SELECT id FROM sites ORDER BY id LIMIT 1)) WHERE site_id IS NULL"
    )

    op.execute(
        "UPDATE article_preview_tokens SET site_id = COALESCE((SELECT id FROM sites WHERE is_default = true AND is_active = true ORDER BY id LIMIT 1),(SELECT id FROM sites ORDER BY id LIMIT 1)) WHERE site_id IS NULL"
    )

    op.execute(
        "UPDATE article_revision_notes SET site_id = COALESCE((SELECT id FROM sites WHERE is_default = true AND is_active = true ORDER BY id LIMIT 1),(SELECT id FROM sites ORDER BY id LIMIT 1)) WHERE site_id IS NULL"
    )

    op.execute(
        "UPDATE article_revisions SET site_id = COALESCE((SELECT id FROM sites WHERE is_default = true AND is_active = true ORDER BY id LIMIT 1),(SELECT id FROM sites ORDER BY id LIMIT 1)) WHERE site_id IS NULL"
    )

    op.execute(
        "UPDATE article_seo SET site_id = COALESCE((SELECT id FROM sites WHERE is_default = true AND is_active = true ORDER BY id LIMIT 1),(SELECT id FROM sites ORDER BY id LIMIT 1)) WHERE site_id IS NULL"
    )

    op.execute(
        "UPDATE articles SET site_id = COALESCE((SELECT id FROM sites WHERE is_default = true AND is_active = true ORDER BY id LIMIT 1),(SELECT id FROM sites ORDER BY id LIMIT 1)) WHERE site_id IS NULL"
    )

    op.execute(
        "UPDATE badge_definitions SET site_id = COALESCE((SELECT id FROM sites WHERE is_default = true AND is_active = true ORDER BY id LIMIT 1),(SELECT id FROM sites ORDER BY id LIMIT 1)) WHERE site_id IS NULL"
    )

    op.execute(
        "UPDATE block_patterns SET site_id = COALESCE((SELECT id FROM sites WHERE is_default = true AND is_active = true ORDER BY id LIMIT 1),(SELECT id FROM sites ORDER BY id LIMIT 1)) WHERE site_id IS NULL"
    )

    op.execute(
        "UPDATE cart_items SET site_id = COALESCE((SELECT id FROM sites WHERE is_default = true AND is_active = true ORDER BY id LIMIT 1),(SELECT id FROM sites ORDER BY id LIMIT 1)) WHERE site_id IS NULL"
    )

    op.execute(
        "UPDATE carts SET site_id = COALESCE((SELECT id FROM sites WHERE is_default = true AND is_active = true ORDER BY id LIMIT 1),(SELECT id FROM sites ORDER BY id LIMIT 1)) WHERE site_id IS NULL"
    )

    op.execute(
        "UPDATE categories SET site_id = COALESCE((SELECT id FROM sites WHERE is_default = true AND is_active = true ORDER BY id LIMIT 1),(SELECT id FROM sites ORDER BY id LIMIT 1)) WHERE site_id IS NULL"
    )

    op.execute(
        "UPDATE category_subscriptions SET site_id = COALESCE((SELECT id FROM sites WHERE is_default = true AND is_active = true ORDER BY id LIMIT 1),(SELECT id FROM sites ORDER BY id LIMIT 1)) WHERE site_id IS NULL"
    )

    op.execute(
        "UPDATE certification_documents SET site_id = COALESCE((SELECT id FROM sites WHERE is_default = true AND is_active = true ORDER BY id LIMIT 1),(SELECT id FROM sites ORDER BY id LIMIT 1)) WHERE site_id IS NULL"
    )

    op.execute(
        "UPDATE certification_reviews SET site_id = COALESCE((SELECT id FROM sites WHERE is_default = true AND is_active = true ORDER BY id LIMIT 1),(SELECT id FROM sites ORDER BY id LIMIT 1)) WHERE site_id IS NULL"
    )

    op.execute(
        "UPDATE chat_group_invites SET site_id = COALESCE((SELECT id FROM sites WHERE is_default = true AND is_active = true ORDER BY id LIMIT 1),(SELECT id FROM sites ORDER BY id LIMIT 1)) WHERE site_id IS NULL"
    )

    op.execute(
        "UPDATE chat_group_members SET site_id = COALESCE((SELECT id FROM sites WHERE is_default = true AND is_active = true ORDER BY id LIMIT 1),(SELECT id FROM sites ORDER BY id LIMIT 1)) WHERE site_id IS NULL"
    )

    op.execute(
        "UPDATE chat_groups SET site_id = COALESCE((SELECT id FROM sites WHERE is_default = true AND is_active = true ORDER BY id LIMIT 1),(SELECT id FROM sites ORDER BY id LIMIT 1)) WHERE site_id IS NULL"
    )

    op.execute(
        "UPDATE chat_messages SET site_id = COALESCE((SELECT id FROM sites WHERE is_default = true AND is_active = true ORDER BY id LIMIT 1),(SELECT id FROM sites ORDER BY id LIMIT 1)) WHERE site_id IS NULL"
    )

    op.execute(
        "UPDATE collaboration_invites SET site_id = COALESCE((SELECT id FROM sites WHERE is_default = true AND is_active = true ORDER BY id LIMIT 1),(SELECT id FROM sites ORDER BY id LIMIT 1)) WHERE site_id IS NULL"
    )

    op.execute(
        "UPDATE comment_subscriptions SET site_id = COALESCE((SELECT id FROM sites WHERE is_default = true AND is_active = true ORDER BY id LIMIT 1),(SELECT id FROM sites ORDER BY id LIMIT 1)) WHERE site_id IS NULL"
    )

    op.execute(
        "UPDATE comment_votes SET site_id = COALESCE((SELECT id FROM sites WHERE is_default = true AND is_active = true ORDER BY id LIMIT 1),(SELECT id FROM sites ORDER BY id LIMIT 1)) WHERE site_id IS NULL"
    )

    op.execute(
        "UPDATE comments SET site_id = COALESCE((SELECT id FROM sites WHERE is_default = true AND is_active = true ORDER BY id LIMIT 1),(SELECT id FROM sites ORDER BY id LIMIT 1)) WHERE site_id IS NULL"
    )

    op.execute(
        "UPDATE crypto_payments SET site_id = COALESCE((SELECT id FROM sites WHERE is_default = true AND is_active = true ORDER BY id LIMIT 1),(SELECT id FROM sites ORDER BY id LIMIT 1)) WHERE site_id IS NULL"
    )

    op.execute(
        "UPDATE custom_fields SET site_id = COALESCE((SELECT id FROM sites WHERE is_default = true AND is_active = true ORDER BY id LIMIT 1),(SELECT id FROM sites ORDER BY id LIMIT 1)) WHERE site_id IS NULL"
    )

    op.execute(
        "UPDATE custom_post_contents SET site_id = COALESCE((SELECT id FROM sites WHERE is_default = true AND is_active = true ORDER BY id LIMIT 1),(SELECT id FROM sites ORDER BY id LIMIT 1)) WHERE site_id IS NULL"
    )

    op.execute(
        "UPDATE custom_post_types SET site_id = COALESCE((SELECT id FROM sites WHERE is_default = true AND is_active = true ORDER BY id LIMIT 1),(SELECT id FROM sites ORDER BY id LIMIT 1)) WHERE site_id IS NULL"
    )

    op.execute(
        "UPDATE deployment_logs SET site_id = COALESCE((SELECT id FROM sites WHERE is_default = true AND is_active = true ORDER BY id LIMIT 1),(SELECT id FROM sites ORDER BY id LIMIT 1)) WHERE site_id IS NULL"
    )

    op.execute(
        "UPDATE download_tasks SET site_id = COALESCE((SELECT id FROM sites WHERE is_default = true AND is_active = true ORDER BY id LIMIT 1),(SELECT id FROM sites ORDER BY id LIMIT 1)) WHERE site_id IS NULL"
    )

    op.execute(
        "UPDATE email_subscriptions SET site_id = COALESCE((SELECT id FROM sites WHERE is_default = true AND is_active = true ORDER BY id LIMIT 1),(SELECT id FROM sites ORDER BY id LIMIT 1)) WHERE site_id IS NULL"
    )

    op.execute(
        "UPDATE enterprise_licenses SET site_id = COALESCE((SELECT id FROM sites WHERE is_default = true AND is_active = true ORDER BY id LIMIT 1),(SELECT id FROM sites ORDER BY id LIMIT 1)) WHERE site_id IS NULL"
    )

    op.execute(
        "UPDATE expert_certifications SET site_id = COALESCE((SELECT id FROM sites WHERE is_default = true AND is_active = true ORDER BY id LIMIT 1),(SELECT id FROM sites ORDER BY id LIMIT 1)) WHERE site_id IS NULL"
    )

    op.execute(
        "UPDATE file_hashs SET site_id = COALESCE((SELECT id FROM sites WHERE is_default = true AND is_active = true ORDER BY id LIMIT 1),(SELECT id FROM sites ORDER BY id LIMIT 1)) WHERE site_id IS NULL"
    )

    op.execute(
        "UPDATE form_fields SET site_id = COALESCE((SELECT id FROM sites WHERE is_default = true AND is_active = true ORDER BY id LIMIT 1),(SELECT id FROM sites ORDER BY id LIMIT 1)) WHERE site_id IS NULL"
    )

    op.execute(
        "UPDATE form_submissions SET site_id = COALESCE((SELECT id FROM sites WHERE is_default = true AND is_active = true ORDER BY id LIMIT 1),(SELECT id FROM sites ORDER BY id LIMIT 1)) WHERE site_id IS NULL"
    )

    op.execute(
        "UPDATE forms SET site_id = COALESCE((SELECT id FROM sites WHERE is_default = true AND is_active = true ORDER BY id LIMIT 1),(SELECT id FROM sites ORDER BY id LIMIT 1)) WHERE site_id IS NULL"
    )

    op.execute(
        "UPDATE global_style_configs SET site_id = COALESCE((SELECT id FROM sites WHERE is_default = true AND is_active = true ORDER BY id LIMIT 1),(SELECT id FROM sites ORDER BY id LIMIT 1)) WHERE site_id IS NULL"
    )

    op.execute(
        "UPDATE global_styles SET site_id = COALESCE((SELECT id FROM sites WHERE is_default = true AND is_active = true ORDER BY id LIMIT 1),(SELECT id FROM sites ORDER BY id LIMIT 1)) WHERE site_id IS NULL"
    )

    op.execute(
        "UPDATE media SET site_id = COALESCE((SELECT id FROM sites WHERE is_default = true AND is_active = true ORDER BY id LIMIT 1),(SELECT id FROM sites ORDER BY id LIMIT 1)) WHERE site_id IS NULL"
    )

    op.execute(
        "UPDATE media_folders SET site_id = COALESCE((SELECT id FROM sites WHERE is_default = true AND is_active = true ORDER BY id LIMIT 1),(SELECT id FROM sites ORDER BY id LIMIT 1)) WHERE site_id IS NULL"
    )

    op.execute(
        "UPDATE media_optimizations SET site_id = COALESCE((SELECT id FROM sites WHERE is_default = true AND is_active = true ORDER BY id LIMIT 1),(SELECT id FROM sites ORDER BY id LIMIT 1)) WHERE site_id IS NULL"
    )

    op.execute(
        "UPDATE menu_items SET site_id = COALESCE((SELECT id FROM sites WHERE is_default = true AND is_active = true ORDER BY id LIMIT 1),(SELECT id FROM sites ORDER BY id LIMIT 1)) WHERE site_id IS NULL"
    )

    op.execute(
        "UPDATE menu_location_assignments SET site_id = COALESCE((SELECT id FROM sites WHERE is_default = true AND is_active = true ORDER BY id LIMIT 1),(SELECT id FROM sites ORDER BY id LIMIT 1)) WHERE site_id IS NULL"
    )

    op.execute(
        "UPDATE menu_locations SET site_id = COALESCE((SELECT id FROM sites WHERE is_default = true AND is_active = true ORDER BY id LIMIT 1),(SELECT id FROM sites ORDER BY id LIMIT 1)) WHERE site_id IS NULL"
    )

    op.execute(
        "UPDATE menus SET site_id = COALESCE((SELECT id FROM sites WHERE is_default = true AND is_active = true ORDER BY id LIMIT 1),(SELECT id FROM sites ORDER BY id LIMIT 1)) WHERE site_id IS NULL"
    )

    op.execute(
        "UPDATE migration_logs SET site_id = COALESCE((SELECT id FROM sites WHERE is_default = true AND is_active = true ORDER BY id LIMIT 1),(SELECT id FROM sites ORDER BY id LIMIT 1)) WHERE site_id IS NULL"
    )

    op.execute(
        "UPDATE migration_tasks SET site_id = COALESCE((SELECT id FROM sites WHERE is_default = true AND is_active = true ORDER BY id LIMIT 1),(SELECT id FROM sites ORDER BY id LIMIT 1)) WHERE site_id IS NULL"
    )

    op.execute(
        "UPDATE notifications SET site_id = COALESCE((SELECT id FROM sites WHERE is_default = true AND is_active = true ORDER BY id LIMIT 1),(SELECT id FROM sites ORDER BY id LIMIT 1)) WHERE site_id IS NULL"
    )

    op.execute(
        "UPDATE order_items SET site_id = COALESCE((SELECT id FROM sites WHERE is_default = true AND is_active = true ORDER BY id LIMIT 1),(SELECT id FROM sites ORDER BY id LIMIT 1)) WHERE site_id IS NULL"
    )

    op.execute(
        "UPDATE orders SET site_id = COALESCE((SELECT id FROM sites WHERE is_default = true AND is_active = true ORDER BY id LIMIT 1),(SELECT id FROM sites ORDER BY id LIMIT 1)) WHERE site_id IS NULL"
    )

    op.execute(
        "UPDATE page_builder SET site_id = COALESCE((SELECT id FROM sites WHERE is_default = true AND is_active = true ORDER BY id LIMIT 1),(SELECT id FROM sites ORDER BY id LIMIT 1)) WHERE site_id IS NULL"
    )

    op.execute(
        "UPDATE page_views SET site_id = COALESCE((SELECT id FROM sites WHERE is_default = true AND is_active = true ORDER BY id LIMIT 1),(SELECT id FROM sites ORDER BY id LIMIT 1)) WHERE site_id IS NULL"
    )

    op.execute(
        "UPDATE pages SET site_id = COALESCE((SELECT id FROM sites WHERE is_default = true AND is_active = true ORDER BY id LIMIT 1),(SELECT id FROM sites ORDER BY id LIMIT 1)) WHERE site_id IS NULL"
    )

    op.execute(
        "UPDATE payment_transactions SET site_id = COALESCE((SELECT id FROM sites WHERE is_default = true AND is_active = true ORDER BY id LIMIT 1),(SELECT id FROM sites ORDER BY id LIMIT 1)) WHERE site_id IS NULL"
    )

    op.execute(
        "UPDATE payout_requests SET site_id = COALESCE((SELECT id FROM sites WHERE is_default = true AND is_active = true ORDER BY id LIMIT 1),(SELECT id FROM sites ORDER BY id LIMIT 1)) WHERE site_id IS NULL"
    )

    op.execute(
        "UPDATE points_rules SET site_id = COALESCE((SELECT id FROM sites WHERE is_default = true AND is_active = true ORDER BY id LIMIT 1),(SELECT id FROM sites ORDER BY id LIMIT 1)) WHERE site_id IS NULL"
    )

    op.execute(
        "UPDATE points_transactions SET site_id = COALESCE((SELECT id FROM sites WHERE is_default = true AND is_active = true ORDER BY id LIMIT 1),(SELECT id FROM sites ORDER BY id LIMIT 1)) WHERE site_id IS NULL"
    )

    op.execute(
        "UPDATE private_messages SET site_id = COALESCE((SELECT id FROM sites WHERE is_default = true AND is_active = true ORDER BY id LIMIT 1),(SELECT id FROM sites ORDER BY id LIMIT 1)) WHERE site_id IS NULL"
    )

    op.execute(
        "UPDATE products SET site_id = COALESCE((SELECT id FROM sites WHERE is_default = true AND is_active = true ORDER BY id LIMIT 1),(SELECT id FROM sites ORDER BY id LIMIT 1)) WHERE site_id IS NULL"
    )

    op.execute(
        "UPDATE publish_channels SET site_id = COALESCE((SELECT id FROM sites WHERE is_default = true AND is_active = true ORDER BY id LIMIT 1),(SELECT id FROM sites ORDER BY id LIMIT 1)) WHERE site_id IS NULL"
    )

    op.execute(
        "UPDATE publish_logs SET site_id = COALESCE((SELECT id FROM sites WHERE is_default = true AND is_active = true ORDER BY id LIMIT 1),(SELECT id FROM sites ORDER BY id LIMIT 1)) WHERE site_id IS NULL"
    )

    op.execute(
        "UPDATE publish_tasks SET site_id = COALESCE((SELECT id FROM sites WHERE is_default = true AND is_active = true ORDER BY id LIMIT 1),(SELECT id FROM sites ORDER BY id LIMIT 1)) WHERE site_id IS NULL"
    )

    op.execute(
        "UPDATE report_history SET site_id = COALESCE((SELECT id FROM sites WHERE is_default = true AND is_active = true ORDER BY id LIMIT 1),(SELECT id FROM sites ORDER BY id LIMIT 1)) WHERE site_id IS NULL"
    )

    op.execute(
        "UPDATE revenue_records SET site_id = COALESCE((SELECT id FROM sites WHERE is_default = true AND is_active = true ORDER BY id LIMIT 1),(SELECT id FROM sites ORDER BY id LIMIT 1)) WHERE site_id IS NULL"
    )

    op.execute(
        "UPDATE revenue_sharing_configs SET site_id = COALESCE((SELECT id FROM sites WHERE is_default = true AND is_active = true ORDER BY id LIMIT 1),(SELECT id FROM sites ORDER BY id LIMIT 1)) WHERE site_id IS NULL"
    )

    op.execute(
        "UPDATE scheduled_reports SET site_id = COALESCE((SELECT id FROM sites WHERE is_default = true AND is_active = true ORDER BY id LIMIT 1),(SELECT id FROM sites ORDER BY id LIMIT 1)) WHERE site_id IS NULL"
    )

    op.execute(
        "UPDATE search_history SET site_id = COALESCE((SELECT id FROM sites WHERE is_default = true AND is_active = true ORDER BY id LIMIT 1),(SELECT id FROM sites ORDER BY id LIMIT 1)) WHERE site_id IS NULL"
    )

    op.execute(
        "UPDATE sensitive_words SET site_id = COALESCE((SELECT id FROM sites WHERE is_default = true AND is_active = true ORDER BY id LIMIT 1),(SELECT id FROM sites ORDER BY id LIMIT 1)) WHERE site_id IS NULL"
    )

    op.execute(
        "UPDATE seo_redirects SET site_id = COALESCE((SELECT id FROM sites WHERE is_default = true AND is_active = true ORDER BY id LIMIT 1),(SELECT id FROM sites ORDER BY id LIMIT 1)) WHERE site_id IS NULL"
    )

    op.execute(
        "UPDATE share_stats SET site_id = COALESCE((SELECT id FROM sites WHERE is_default = true AND is_active = true ORDER BY id LIMIT 1),(SELECT id FROM sites ORDER BY id LIMIT 1)) WHERE site_id IS NULL"
    )

    op.execute(
        "UPDATE shortcodes SET site_id = COALESCE((SELECT id FROM sites WHERE is_default = true AND is_active = true ORDER BY id LIMIT 1),(SELECT id FROM sites ORDER BY id LIMIT 1)) WHERE site_id IS NULL"
    )

    op.execute(
        "UPDATE sla_reports SET site_id = COALESCE((SELECT id FROM sites WHERE is_default = true AND is_active = true ORDER BY id LIMIT 1),(SELECT id FROM sites ORDER BY id LIMIT 1)) WHERE site_id IS NULL"
    )

    op.execute(
        "UPDATE support_ticket_replies SET site_id = COALESCE((SELECT id FROM sites WHERE is_default = true AND is_active = true ORDER BY id LIMIT 1),(SELECT id FROM sites ORDER BY id LIMIT 1)) WHERE site_id IS NULL"
    )

    op.execute(
        "UPDATE support_tickets SET site_id = COALESCE((SELECT id FROM sites WHERE is_default = true AND is_active = true ORDER BY id LIMIT 1),(SELECT id FROM sites ORDER BY id LIMIT 1)) WHERE site_id IS NULL"
    )

    op.execute(
        "UPDATE tasks SET site_id = COALESCE((SELECT id FROM sites WHERE is_default = true AND is_active = true ORDER BY id LIMIT 1),(SELECT id FROM sites ORDER BY id LIMIT 1)) WHERE site_id IS NULL"
    )

    op.execute(
        "UPDATE team_comments SET site_id = COALESCE((SELECT id FROM sites WHERE is_default = true AND is_active = true ORDER BY id LIMIT 1),(SELECT id FROM sites ORDER BY id LIMIT 1)) WHERE site_id IS NULL"
    )

    op.execute(
        "UPDATE tip_withdrawals SET site_id = COALESCE((SELECT id FROM sites WHERE is_default = true AND is_active = true ORDER BY id LIMIT 1),(SELECT id FROM sites ORDER BY id LIMIT 1)) WHERE site_id IS NULL"
    )

    op.execute(
        "UPDATE tips SET site_id = COALESCE((SELECT id FROM sites WHERE is_default = true AND is_active = true ORDER BY id LIMIT 1),(SELECT id FROM sites ORDER BY id LIMIT 1)) WHERE site_id IS NULL"
    )

    op.execute(
        "UPDATE upload_chunks SET site_id = COALESCE((SELECT id FROM sites WHERE is_default = true AND is_active = true ORDER BY id LIMIT 1),(SELECT id FROM sites ORDER BY id LIMIT 1)) WHERE site_id IS NULL"
    )

    op.execute(
        "UPDATE upload_tasks SET site_id = COALESCE((SELECT id FROM sites WHERE is_default = true AND is_active = true ORDER BY id LIMIT 1),(SELECT id FROM sites ORDER BY id LIMIT 1)) WHERE site_id IS NULL"
    )

    op.execute(
        "UPDATE user_activities SET site_id = COALESCE((SELECT id FROM sites WHERE is_default = true AND is_active = true ORDER BY id LIMIT 1),(SELECT id FROM sites ORDER BY id LIMIT 1)) WHERE site_id IS NULL"
    )

    op.execute(
        "UPDATE user_badges SET site_id = COALESCE((SELECT id FROM sites WHERE is_default = true AND is_active = true ORDER BY id LIMIT 1),(SELECT id FROM sites ORDER BY id LIMIT 1)) WHERE site_id IS NULL"
    )

    op.execute(
        "UPDATE user_blocks SET site_id = COALESCE((SELECT id FROM sites WHERE is_default = true AND is_active = true ORDER BY id LIMIT 1),(SELECT id FROM sites ORDER BY id LIMIT 1)) WHERE site_id IS NULL"
    )

    op.execute(
        "UPDATE user_follows SET site_id = COALESCE((SELECT id FROM sites WHERE is_default = true AND is_active = true ORDER BY id LIMIT 1),(SELECT id FROM sites ORDER BY id LIMIT 1)) WHERE site_id IS NULL"
    )

    op.execute(
        "UPDATE user_points SET site_id = COALESCE((SELECT id FROM sites WHERE is_default = true AND is_active = true ORDER BY id LIMIT 1),(SELECT id FROM sites ORDER BY id LIMIT 1)) WHERE site_id IS NULL"
    )

    op.execute(
        "UPDATE user_revenue_stats SET site_id = COALESCE((SELECT id FROM sites WHERE is_default = true AND is_active = true ORDER BY id LIMIT 1),(SELECT id FROM sites ORDER BY id LIMIT 1)) WHERE site_id IS NULL"
    )

    op.execute(
        "UPDATE vip_features SET site_id = COALESCE((SELECT id FROM sites WHERE is_default = true AND is_active = true ORDER BY id LIMIT 1),(SELECT id FROM sites ORDER BY id LIMIT 1)) WHERE site_id IS NULL"
    )

    op.execute(
        "UPDATE vip_payment_orders SET site_id = COALESCE((SELECT id FROM sites WHERE is_default = true AND is_active = true ORDER BY id LIMIT 1),(SELECT id FROM sites ORDER BY id LIMIT 1)) WHERE site_id IS NULL"
    )

    op.execute(
        "UPDATE vip_plans SET site_id = COALESCE((SELECT id FROM sites WHERE is_default = true AND is_active = true ORDER BY id LIMIT 1),(SELECT id FROM sites ORDER BY id LIMIT 1)) WHERE site_id IS NULL"
    )

    op.execute(
        "UPDATE vip_subscriptions SET site_id = COALESCE((SELECT id FROM sites WHERE is_default = true AND is_active = true ORDER BY id LIMIT 1),(SELECT id FROM sites ORDER BY id LIMIT 1)) WHERE site_id IS NULL"
    )

    op.execute(
        "UPDATE webhook_deliveries SET site_id = COALESCE((SELECT id FROM sites WHERE is_default = true AND is_active = true ORDER BY id LIMIT 1),(SELECT id FROM sites ORDER BY id LIMIT 1)) WHERE site_id IS NULL"
    )

    op.execute(
        "UPDATE webhooks SET site_id = COALESCE((SELECT id FROM sites WHERE is_default = true AND is_active = true ORDER BY id LIMIT 1),(SELECT id FROM sites ORDER BY id LIMIT 1)) WHERE site_id IS NULL"
    )

    op.execute(
        "UPDATE widget_instances SET site_id = COALESCE((SELECT id FROM sites WHERE is_default = true AND is_active = true ORDER BY id LIMIT 1),(SELECT id FROM sites ORDER BY id LIMIT 1)) WHERE site_id IS NULL"
    )

    op.execute(
        "UPDATE workspace_members SET site_id = COALESCE((SELECT id FROM sites WHERE is_default = true AND is_active = true ORDER BY id LIMIT 1),(SELECT id FROM sites ORDER BY id LIMIT 1)) WHERE site_id IS NULL"
    )

    op.execute(
        "UPDATE workspaces SET site_id = COALESCE((SELECT id FROM sites WHERE is_default = true AND is_active = true ORDER BY id LIMIT 1),(SELECT id FROM sites ORDER BY id LIMIT 1)) WHERE site_id IS NULL"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_workspaces_site_id', table_name='workspaces')
    op.drop_column('workspaces', 'site_id')

    op.drop_index('ix_workspace_members_site_id', table_name='workspace_members')
    op.drop_column('workspace_members', 'site_id')

    op.drop_index('ix_widget_instances_site_id', table_name='widget_instances')
    op.drop_column('widget_instances', 'site_id')

    op.drop_index('ix_webhooks_site_id', table_name='webhooks')
    op.drop_column('webhooks', 'site_id')

    op.drop_index('ix_webhook_deliveries_site_id', table_name='webhook_deliveries')
    op.drop_column('webhook_deliveries', 'site_id')

    op.drop_index('ix_vip_subscriptions_site_id', table_name='vip_subscriptions')
    op.drop_column('vip_subscriptions', 'site_id')

    op.drop_index('ix_vip_plans_site_id', table_name='vip_plans')
    op.drop_column('vip_plans', 'site_id')

    op.drop_index('ix_vip_payment_orders_site_id', table_name='vip_payment_orders')
    op.drop_column('vip_payment_orders', 'site_id')

    op.drop_index('ix_vip_features_site_id', table_name='vip_features')
    op.drop_column('vip_features', 'site_id')

    op.drop_index('ix_user_revenue_stats_site_id', table_name='user_revenue_stats')
    op.drop_column('user_revenue_stats', 'site_id')

    op.drop_index('ix_user_points_site_id', table_name='user_points')
    op.drop_column('user_points', 'site_id')

    op.drop_index('ix_user_follows_site_id', table_name='user_follows')
    op.drop_column('user_follows', 'site_id')

    op.drop_index('ix_user_blocks_site_id', table_name='user_blocks')
    op.drop_column('user_blocks', 'site_id')

    op.drop_index('ix_user_badges_site_id', table_name='user_badges')
    op.drop_column('user_badges', 'site_id')

    op.drop_index('ix_user_activities_site_id', table_name='user_activities')
    op.drop_column('user_activities', 'site_id')

    op.drop_index('ix_upload_tasks_site_id', table_name='upload_tasks')
    op.drop_column('upload_tasks', 'site_id')

    op.drop_index('ix_upload_chunks_site_id', table_name='upload_chunks')
    op.drop_column('upload_chunks', 'site_id')

    op.drop_index('ix_tips_site_id', table_name='tips')
    op.drop_column('tips', 'site_id')

    op.drop_index('ix_tip_withdrawals_site_id', table_name='tip_withdrawals')
    op.drop_column('tip_withdrawals', 'site_id')

    op.drop_index('ix_team_comments_site_id', table_name='team_comments')
    op.drop_column('team_comments', 'site_id')

    op.drop_index('ix_tasks_site_id', table_name='tasks')
    op.drop_column('tasks', 'site_id')

    op.drop_index('ix_support_tickets_site_id', table_name='support_tickets')
    op.drop_column('support_tickets', 'site_id')

    op.drop_index('ix_support_ticket_replies_site_id', table_name='support_ticket_replies')
    op.drop_column('support_ticket_replies', 'site_id')

    op.drop_index('ix_sla_reports_site_id', table_name='sla_reports')
    op.drop_column('sla_reports', 'site_id')

    op.drop_index('ix_shortcodes_site_id', table_name='shortcodes')
    op.drop_column('shortcodes', 'site_id')

    op.drop_index('ix_share_stats_site_id', table_name='share_stats')
    op.drop_column('share_stats', 'site_id')

    op.drop_index('ix_seo_redirects_site_id', table_name='seo_redirects')
    op.drop_column('seo_redirects', 'site_id')

    op.drop_index('ix_sensitive_words_site_id', table_name='sensitive_words')
    op.drop_column('sensitive_words', 'site_id')

    op.drop_index('ix_search_history_site_id', table_name='search_history')
    op.drop_column('search_history', 'site_id')

    op.drop_index('ix_scheduled_reports_site_id', table_name='scheduled_reports')
    op.drop_column('scheduled_reports', 'site_id')

    op.drop_index('ix_revenue_sharing_configs_site_id', table_name='revenue_sharing_configs')
    op.drop_column('revenue_sharing_configs', 'site_id')

    op.drop_index('ix_revenue_records_site_id', table_name='revenue_records')
    op.drop_column('revenue_records', 'site_id')

    op.drop_index('ix_report_history_site_id', table_name='report_history')
    op.drop_column('report_history', 'site_id')

    op.drop_index('ix_publish_tasks_site_id', table_name='publish_tasks')
    op.drop_column('publish_tasks', 'site_id')

    op.drop_index('ix_publish_logs_site_id', table_name='publish_logs')
    op.drop_column('publish_logs', 'site_id')

    op.drop_index('ix_publish_channels_site_id', table_name='publish_channels')
    op.drop_column('publish_channels', 'site_id')

    op.drop_index('ix_products_site_id', table_name='products')
    op.drop_column('products', 'site_id')

    op.drop_index('ix_private_messages_site_id', table_name='private_messages')
    op.drop_column('private_messages', 'site_id')

    op.drop_index('ix_points_transactions_site_id', table_name='points_transactions')
    op.drop_column('points_transactions', 'site_id')

    op.drop_index('ix_points_rules_site_id', table_name='points_rules')
    op.drop_column('points_rules', 'site_id')

    op.drop_index('ix_payout_requests_site_id', table_name='payout_requests')
    op.drop_column('payout_requests', 'site_id')

    op.drop_index('ix_payment_transactions_site_id', table_name='payment_transactions')
    op.drop_column('payment_transactions', 'site_id')

    op.drop_index('ix_pages_site_id', table_name='pages')
    op.drop_column('pages', 'site_id')

    op.drop_index('ix_page_views_site_id', table_name='page_views')
    op.drop_column('page_views', 'site_id')

    op.drop_index('ix_page_builder_site_id', table_name='page_builder')
    op.drop_column('page_builder', 'site_id')

    op.drop_index('ix_orders_site_id', table_name='orders')
    op.drop_column('orders', 'site_id')

    op.drop_index('ix_order_items_site_id', table_name='order_items')
    op.drop_column('order_items', 'site_id')

    op.drop_index('ix_notifications_site_id', table_name='notifications')
    op.drop_column('notifications', 'site_id')

    op.drop_index('ix_migration_tasks_site_id', table_name='migration_tasks')
    op.drop_column('migration_tasks', 'site_id')

    op.drop_index('ix_migration_logs_site_id', table_name='migration_logs')
    op.drop_column('migration_logs', 'site_id')

    op.drop_index('ix_menus_site_id', table_name='menus')
    op.drop_column('menus', 'site_id')

    op.drop_index('ix_menu_locations_site_id', table_name='menu_locations')
    op.drop_column('menu_locations', 'site_id')

    op.drop_index('ix_menu_location_assignments_site_id', table_name='menu_location_assignments')
    op.drop_column('menu_location_assignments', 'site_id')

    op.drop_index('ix_menu_items_site_id', table_name='menu_items')
    op.drop_column('menu_items', 'site_id')

    op.drop_index('ix_media_optimizations_site_id', table_name='media_optimizations')
    op.drop_column('media_optimizations', 'site_id')

    op.drop_index('ix_media_folders_site_id', table_name='media_folders')
    op.drop_column('media_folders', 'site_id')

    op.drop_index('ix_media_site_id', table_name='media')
    op.drop_column('media', 'site_id')

    op.drop_index('ix_global_styles_site_id', table_name='global_styles')
    op.drop_column('global_styles', 'site_id')

    op.drop_index('ix_global_style_configs_site_id', table_name='global_style_configs')
    op.drop_column('global_style_configs', 'site_id')

    op.drop_index('ix_forms_site_id', table_name='forms')
    op.drop_column('forms', 'site_id')

    op.drop_index('ix_form_submissions_site_id', table_name='form_submissions')
    op.drop_column('form_submissions', 'site_id')

    op.drop_index('ix_form_fields_site_id', table_name='form_fields')
    op.drop_column('form_fields', 'site_id')

    op.drop_index('ix_file_hashs_site_id', table_name='file_hashs')
    op.drop_column('file_hashs', 'site_id')

    op.drop_index('ix_expert_certifications_site_id', table_name='expert_certifications')
    op.drop_column('expert_certifications', 'site_id')

    op.drop_index('ix_enterprise_licenses_site_id', table_name='enterprise_licenses')
    op.drop_column('enterprise_licenses', 'site_id')

    op.drop_index('ix_email_subscriptions_site_id', table_name='email_subscriptions')
    op.drop_column('email_subscriptions', 'site_id')

    op.drop_index('ix_download_tasks_site_id', table_name='download_tasks')
    op.drop_column('download_tasks', 'site_id')

    op.drop_index('ix_deployment_logs_site_id', table_name='deployment_logs')
    op.drop_column('deployment_logs', 'site_id')

    op.drop_index('ix_custom_post_types_site_id', table_name='custom_post_types')
    op.drop_column('custom_post_types', 'site_id')

    op.drop_index('ix_custom_post_contents_site_id', table_name='custom_post_contents')
    op.drop_column('custom_post_contents', 'site_id')

    op.drop_index('ix_custom_fields_site_id', table_name='custom_fields')
    op.drop_column('custom_fields', 'site_id')

    op.drop_index('ix_crypto_payments_site_id', table_name='crypto_payments')
    op.drop_column('crypto_payments', 'site_id')

    op.drop_index('ix_comments_site_id', table_name='comments')
    op.drop_column('comments', 'site_id')

    op.drop_index('ix_comment_votes_site_id', table_name='comment_votes')
    op.drop_column('comment_votes', 'site_id')

    op.drop_index('ix_comment_subscriptions_site_id', table_name='comment_subscriptions')
    op.drop_column('comment_subscriptions', 'site_id')

    op.drop_index('ix_collaboration_invites_site_id', table_name='collaboration_invites')
    op.drop_column('collaboration_invites', 'site_id')

    op.drop_index('ix_chat_messages_site_id', table_name='chat_messages')
    op.drop_column('chat_messages', 'site_id')

    op.drop_index('ix_chat_groups_site_id', table_name='chat_groups')
    op.drop_column('chat_groups', 'site_id')

    op.drop_index('ix_chat_group_members_site_id', table_name='chat_group_members')
    op.drop_column('chat_group_members', 'site_id')

    op.drop_index('ix_chat_group_invites_site_id', table_name='chat_group_invites')
    op.drop_column('chat_group_invites', 'site_id')

    op.drop_index('ix_certification_reviews_site_id', table_name='certification_reviews')
    op.drop_column('certification_reviews', 'site_id')

    op.drop_index('ix_certification_documents_site_id', table_name='certification_documents')
    op.drop_column('certification_documents', 'site_id')

    op.drop_index('ix_category_subscriptions_site_id', table_name='category_subscriptions')
    op.drop_column('category_subscriptions', 'site_id')

    op.drop_index('ix_categories_site_id', table_name='categories')
    op.drop_column('categories', 'site_id')

    op.drop_index('ix_carts_site_id', table_name='carts')
    op.drop_column('carts', 'site_id')

    op.drop_index('ix_cart_items_site_id', table_name='cart_items')
    op.drop_column('cart_items', 'site_id')

    op.drop_index('ix_block_patterns_site_id', table_name='block_patterns')
    op.drop_column('block_patterns', 'site_id')

    op.drop_index('ix_badge_definitions_site_id', table_name='badge_definitions')
    op.drop_column('badge_definitions', 'site_id')

    op.drop_index('ix_articles_site_id', table_name='articles')
    op.drop_column('articles', 'site_id')

    op.drop_index('ix_article_seo_site_id', table_name='article_seo')
    op.drop_column('article_seo', 'site_id')

    op.drop_index('ix_article_revisions_site_id', table_name='article_revisions')
    op.drop_column('article_revisions', 'site_id')

    op.drop_index('ix_article_revision_notes_site_id', table_name='article_revision_notes')
    op.drop_column('article_revision_notes', 'site_id')

    op.drop_index('ix_article_preview_tokens_site_id', table_name='article_preview_tokens')
    op.drop_column('article_preview_tokens', 'site_id')

    op.drop_index('ix_article_likes_site_id', table_name='article_likes')
    op.drop_column('article_likes', 'site_id')

    op.drop_index('ix_article_content_site_id', table_name='article_content')
    op.drop_column('article_content', 'site_id')

    op.drop_index('ix_article_annotations_site_id', table_name='article_annotations')
    op.drop_column('article_annotations', 'site_id')

    op.drop_index('ix_approval_steps_site_id', table_name='approval_steps')
    op.drop_column('approval_steps', 'site_id')

    op.drop_index('ix_approval_records_site_id', table_name='approval_records')
    op.drop_column('approval_records', 'site_id')

    op.drop_index('ix_ads_site_id', table_name='ads')
    op.drop_column('ads', 'site_id')

    op.drop_index('ix_ad_placements_site_id', table_name='ad_placements')
    op.drop_column('ad_placements', 'site_id')

    op.drop_index('ix_ad_impressions_site_id', table_name='ad_impressions')
    op.drop_column('ad_impressions', 'site_id')

    op.drop_index('ix_ad_clicks_site_id', table_name='ad_clicks')
    op.drop_column('ad_clicks', 'site_id')
