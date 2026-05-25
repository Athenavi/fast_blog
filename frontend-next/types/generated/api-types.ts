/**
 * API 类型定义
 * 由 routes.yaml 自动生成 - 请勿手动修改
 * 生成时间：2026-05-25 10:58:31
 */

export interface AuditLog {
    id: any;
    user_id?: any;
    action: string;
    resource_type?: string;
    resource_id?: any;
    ip_address?: string;
    user_agent?: any;
    request_data?: any;
    status: string;
    error_message?: any;
    created_at: string;
}

export interface AIWorkflow {
    id: any;
    user_id: any;
    task_type: string;
    input_data: any;
    output_data?: any;
    model_used?: string;
    tokens_used: number;
    status: string;
    error_message?: any;
    created_at: string;
    completed_at?: string;
}

export interface PageBuilder {
    id: any;
    title: string;
    slug: string;
    blocks_data: any;
    template_name?: string;
    is_published: boolean;
    created_at: string;
    updated_at: string;
}

export interface GlobalStyle {
    id: any;
    theme_name: string;
    variables_json: any;
    is_active: boolean;
    created_at: string;
}

export interface FieldPermission {
    id: any;
    role_id: any;
    model_name: string;
    field_name: string;
    can_read: boolean;
    can_write: boolean;
    created_at: string;
}

export interface SubscriptionPlan {
    id: any;
    name: string;
    slug: string;
    price: number;
    interval: string;
    features_json: any;
    is_active: boolean;
    stripe_price_id?: string;
    created_at: string;
}

export interface UserSubscription {
    id: any;
    user_id: any;
    plan_id: any;
    status: string;
    current_period_end: string;
    stripe_subscription_id?: string;
    created_at: string;
}

export interface ThemePackage {
    id: any;
    name: string;
    slug: string;
    version: string;
    author?: string;
    config_data: any;
    is_active: boolean;
    created_at: string;
}

export interface User {
    id: any;
    username: string;
    email: string;
    password: string;
    profile_picture?: string;
    bio?: string;
    profile_private: boolean;
    vip_level: any;
    vip_expires_at?: string;
    is_active: boolean;
    is_superuser: boolean;
    date_joined: string;
    last_login_at?: string;
    locale: string;
    is_staff: boolean;
    last_login_ip?: string;
    register_ip?: string;
    is_2fa_enabled: boolean;
    totp_secret?: string;
    backup_codes?: any;
}

export interface UserCreate {
    username: string;
    email: string;
    password: string;
    password_confirm: string;
}

export interface UserUpdate {
    username: string;
    email: string;
    profile_picture?: string;
    bio?: string;
    locale: string;
    profile_private: boolean;
}

export interface ProfileUpdateRequest {
    username?: string;
    email?: string;
    bio?: string;
    profile_private?: boolean;
    locale?: string;
}

export interface PasswordChange {
    old_password: string;
    new_password: string;
    new_password_confirm: string;
}

export interface Article {
    id: any;
    title: string;
    slug: string;
    excerpt?: string;
    cover_image?: string;
    category?: any;
    tags_list: any[];
    views: any;
    user: any;
    likes: any;
    status: number;
    hidden: boolean;
    is_featured: boolean;
    is_vip_only: boolean;
    required_vip_level: number;
    article_ad?: string;
    scheduled_publish_at?: string;
    post_type: string;
    is_sticky: boolean;
    sticky_until?: string;
    sort_order: any;
    created_at: string;
    updated_at: string;
}

export interface ArticleList {
    id: any;
    title: string;
    slug: string;
    excerpt?: string;
    cover_image?: string;
    category_id?: any;
    tags_list: any[];
    views: any;
    likes: any;
    status: number;
    is_featured: boolean;
    is_vip_only: boolean;
    required_vip_level: number;
    is_sticky: boolean;
    created_at: string;
    updated_at: string;
}

export interface AuthorSimple {
    id: any;
    username: string;
}

export interface ArticleCreateUpdate {
    title: string;
    slug: string;
    excerpt?: string;
    cover_image?: string;
    category_id?: any;
    tags?: string;
    status: any;
    hidden: boolean;
    is_featured: boolean;
    is_vip_only: boolean;
    required_vip_level: any;
    article_ad?: string;
    scheduled_publish_at?: string;
    is_sticky: boolean;
    sticky_until?: string;
}

export interface Category {
    id: any;
    name: string;
    slug?: string;
    description?: string;
    parent_id?: any;
    sort_order: any;
    icon?: string;
    color?: string;
    is_visible: boolean;
    articles_count: any;
    created_at: string;
    updated_at: string;
}

export interface CategoryCreateUpdate {
    name: string;
    slug?: string;
    description?: string;
    parent_id?: any;
    sort_order: any;
    icon?: string;
    color?: string;
    is_visible: boolean;
}

export interface CategorySubscription {
    id: any;
    category: any;
    subscriber: any;
    created_at: string;
}

export interface Media {
    id: any;
    user: any;
    hash: string;
    filename: string;
    original_filename?: string;
    file_path: string;
    file_url: string;
    file_size: any;
    file_type: string;
    mime_type?: string;
    width?: any;
    height?: any;
    duration?: any;
    thumbnail_path?: string;
    thumbnail_url?: string;
    description?: string;
    alt_text?: string;
    is_public: boolean;
    download_count: any;
    category?: string;
    tags?: string;
    folder_id?: any;
    created_at: string;
    updated_at: string;
}

export interface MediaFolder {
    id: any;
    name: string;
    parent_id?: any;
    user: any;
    description?: string;
    sort_order: any;
    is_public: boolean;
    media_count: any;
    created_at: string;
    updated_at: string;
}

export interface MediaOptimization {
    id: any;
    media_id: any;
    webp_url?: string;
    sizes_json?: any;
    cdn_url?: string;
    optimization_status: string;
    created_at: string;
    updated_at: string;
}

export interface ArticleRevisionNote {
    id: any;
    revision_id: any;
    user_id: any;
    note_content: any;
    created_at: string;
}

export interface SystemSettings {
    id: number;
    setting_key: string;
    setting_value: string;
    setting_type: string;
    description?: string;
    is_public: boolean;
    created_at: string;
    updated_at: string;
}

export interface AdminSettings {
    id: any;
    user: any;
    settings_data: Record<string, any>;
    created_at: string;
    updated_at: string;
}

export interface ArticleContent {
    id: any;
    article: any;
    passwd?: string;
    content: any;
    created_at: string;
    updated_at: string;
    language_code: string;
}

export interface ArticleLike {
    id: any;
    user: any;
    article: any;
    created_at: string;
}

export interface FileHash {
    id: any;
    hash: string;
    filename: string;
    created_at: string;
    updated_at: string;
    reference_count: any;
    file_size: any;
    mime_type: string;
    storage_path: string;
}

export interface Menus {
    id: number;
    name: string;
    slug: string;
    description?: string;
    is_active: boolean;
    created_at: string;
    updated_at: string;
}

export interface MenuItems {
    id: number;
    menu_id: number;
    parent_id?: number;
    title: string;
    url: string;
    target: string;
    order_index: number;
    is_active: boolean;
    created_at: string;
}

export interface MenuLocation {
    id: number;
    name: string;
    slug: string;
    description?: string;
    theme_supports?: string;
    created_at: string;
    updated_at: string;
}

export interface MenuLocationAssignment {
    id: any;
    menu_id: any;
    location_id: any;
    created_at: string;
}

export interface Pages {
    id: any;
    title: string;
    slug: string;
    content: string;
    excerpt?: string;
    template?: string;
    status: any;
    author_id?: any;
    parent_id?: any;
    order_index: number;
    meta_title?: string;
    meta_description?: string;
    meta_keywords?: string;
    created_at: string;
    updated_at: string;
    published_at?: string;
}

export interface UploadTask {
    id: string;
    user_id: any;
    filename: string;
    total_size: any;
    total_chunks: any;
    uploaded_chunks: any;
    file_hash?: string;
    status: string;
    created_at: string;
    updated_at: string;
}

export interface UploadChunk {
    id: any;
    upload_id: string;
    chunk_index: any;
    chunk_hash: string;
    chunk_size: any;
    chunk_path: string;
    created_at: string;
}

export interface DownloadTask {
    id: any;
    user_id: any;
    source_url: string;
    resource_type: string;
    filename?: string;
    total_size?: any;
    downloaded_size: any;
    progress: number;
    status: string;
    error_message?: any;
    media_id?: any;
    retry_count: any;
    max_retries: any;
    priority: any;
    created_at: string;
    updated_at: string;
    started_at?: string;
    completed_at?: string;
}

export interface Notification {
    id: any;
    recipient: any;
    type: string;
    title: string;
    message: string;
    is_read: boolean;
    read_at?: string;
    created_at: string;
    updated_at: string;
}

export interface PrivateMessage {
    id: any;
    sender: any;
    recipient: any;
    content: any;
    message_type: string;
    attachment_url?: string;
    is_read: boolean;
    read_at?: string;
    is_deleted_by_sender: boolean;
    is_deleted_by_recipient: boolean;
    parent_message?: any;
    created_at: string;
    updated_at: string;
}

export interface UserBlock {
    id: any;
    blocker: any;
    blocked_user: any;
    reason?: string;
    created_at: string;
}

export interface SearchHistory {
    id: any;
    user: any;
    keyword: string;
    results_count: any;
    created_at: string;
}

export interface SearchIndex {
    id: any;
    article_id: any;
    indexed: boolean;
    last_indexed_at?: string;
    index_hash?: string;
    created_at: string;
    updated_at: string;
}

export interface PageView {
    id: any;
    user?: any;
    session_id?: string;
    page_url: string;
    page_title?: string;
    referrer?: string;
    user_agent?: string;
    ip_address?: string;
    device_type?: string;
    browser?: string;
    platform?: string;
    country?: string;
    city?: string;
    created_at: string;
}

export interface UserActivity {
    id: any;
    user: any;
    activity_type: string;
    target_type: string;
    target_id: any;
    details?: string;
    ip_address?: string;
    user_agent?: string;
    created_at: string;
}

export interface VIPPlan {
    id: any;
    name: string;
    description?: string;
    price: any;
    original_price?: any;
    duration_days: number;
    level: any;
    features?: string;
    is_active: boolean;
    created_at: string;
    updated_at: string;
}

export interface VIPSubscription {
    id: any;
    user: any;
    plan: number;
    starts_at: string;
    expires_at: string;
    status: any;
    payment_amount?: any;
    transaction_id?: string;
    created_at: string;
}

export interface VIPFeature {
    id: any;
    code: string;
    name: string;
    description?: string;
    required_level: number;
    is_active: boolean;
    created_at: string;
}

export interface CustomField {
    id: any;
    user: any;
    field_name: string;
    field_value: string;
}

export interface EmailSubscription {
    id: any;
    user: any;
    subscribed: boolean;
    created_at: string;
}

export interface ArticleRevision {
    id: any;
    article_id: any;
    revision_number: any;
    title: string;
    excerpt?: string;
    content: any;
    cover_image?: string;
    tags_list?: string;
    category_id?: any;
    status: any;
    hidden: boolean;
    is_featured: boolean;
    is_vip_only: boolean;
    required_vip_level: any;
    author_id?: any;
    change_summary?: string;
    hash_code?: string;
    created_at: string;
}

export interface Plugin {
    id: any;
    name: string;
    slug: string;
    version: string;
    description?: string;
    author?: string;
    author_url?: string;
    plugin_url?: string;
    is_active: boolean;
    is_installed: boolean;
    settings?: any;
    priority: number;
    created_at: string;
    updated_at: string;
}

export interface Theme {
    id: any;
    name: string;
    slug: string;
    version: string;
    description?: string;
    author?: string;
    author_url?: string;
    theme_url?: string;
    screenshot?: string;
    tags?: string;
    requires?: string;
    settings_schema?: string;
    theme_path?: string;
    is_active: boolean;
    is_installed: boolean;
    settings?: string;
    supports?: string;
    created_at: string;
    updated_at: string;
}

export interface Form {
    id: any;
    title: string;
    slug: string;
    description?: string;
    status: string;
    submit_message?: string;
    email_notification: boolean;
    notification_email?: string;
    store_submissions: boolean;
    created_at: string;
    updated_at: string;
    published_at?: string;
}

export interface FormField {
    id: any;
    form_id: any;
    label: string;
    field_type: string;
    placeholder?: string;
    help_text?: string;
    required: boolean;
    options?: string;
    validation_rules?: string;
    default_value?: string;
    order_index: any;
    is_active: boolean;
    created_at: string;
    updated_at: string;
}

export interface FormSubmission {
    id: any;
    form_id: any;
    data: string;
    ip_address?: string;
    user_agent?: string;
    user_id?: any;
    status: string;
    created_at: string;
}

export interface WidgetInstance {
    id: any;
    widget_type: string;
    area: string;
    title?: string;
    config: string;
    order_index: any;
    is_active: boolean;
    conditions?: string;
    created_at: string;
    updated_at: string;
}

export interface BlockPattern {
    id: any;
    name: string;
    title: string;
    description?: any;
    category: string;
    blocks: any;
    keywords?: any;
    thumbnail?: string;
    is_public: boolean;
    user_id?: any;
    viewport_width: any;
    created_at: string;
    updated_at: string;
}

export interface CustomPostType {
    id: any;
    name: string;
    slug: string;
    description?: string;
    supports?: string;
    has_archive: boolean;
    menu_icon?: string;
    menu_position: number;
    is_active: boolean;
    created_at: string;
    updated_at: string;
}

export interface CommentVote {
    id: any;
    comment_id: any;
    user?: any;
    vote_type: number;
    ip_address?: string;
    created_at: string;
}

export interface CommentSubscription {
    id: any;
    article_id: any;
    user_id?: any;
    email: string;
    notify_type: string;
    is_active: boolean;
    confirm_token?: string;
    confirmed_at?: string;
    created_at: string;
    updated_at: string;
}

export interface Comment {
    id: any;
    article_id: any;
    user_id?: any;
    parent_id?: any;
    content: any;
    author_name?: string;
    author_email?: string;
    author_url?: string;
    author_ip?: string;
    user_agent?: string;
    is_approved: boolean;
    likes: any;
    spam_score?: number;
    spam_reasons?: string;
    created_at: string;
    updated_at: string;
}

export interface OAuthAccount {
    id: any;
    user_id: any;
    provider: string;
    provider_user_id: string;
    access_token?: string;
    refresh_token?: string;
    token_expires_at?: string;
    extra_data?: string;
    created_at: string;
    updated_at: string;
}

export interface ArticleSEO {
    id: any;
    article_id: any;
    seo_title?: string;
    seo_description?: any;
    seo_keywords?: string;
    og_title?: string;
    og_description?: any;
    og_image?: string;
    og_type: string;
    twitter_title?: string;
    twitter_description?: any;
    twitter_image?: string;
    twitter_card: string;
    canonical_url?: string;
    robots_meta: string;
    schema_org_enabled: boolean;
    schema_org_type: string;
    created_at: string;
    updated_at: string;
}

export interface ShareStat {
    id: any;
    article_id: any;
    platform: string;
    shared_by?: any;
    ip_address?: string;
    user_agent?: string;
    created_at: string;
}

export interface Product {
    id: any;
    name: string;
    slug: string;
    description?: any;
    price: any;
    original_price?: any;
    stock: number;
    sku?: string;
    images?: any;
    category_id?: any;
    is_active: boolean;
    is_featured: boolean;
    weight?: any;
    dimensions?: any;
    attributes?: any;
    created_at: string;
    updated_at: string;
}

export interface Cart {
    id: any;
    user_id?: any;
    session_id?: string;
    created_at: string;
    updated_at: string;
}

export interface CartItem {
    id: any;
    cart_id: any;
    product_id: any;
    quantity: number;
    price: any;
    created_at: string;
    updated_at: string;
}

export interface Order {
    id: any;
    order_number: string;
    user_id: any;
    status: string;
    total_amount: any;
    shipping_amount: any;
    discount_amount: any;
    payment_method?: string;
    payment_status: string;
    transaction_id?: string;
    shipping_address: string;
    billing_address?: string;
    notes?: any;
    created_at: string;
    updated_at: string;
    paid_at?: string;
    shipped_at?: string;
    delivered_at?: string;
}

export interface SensitiveWord {
    id: any;
    word: string;
    level: number;
    action: string;
    replacement?: string;
    category?: string;
    is_active: boolean;
    created_by?: any;
    created_at: string;
    updated_at: string;
}

export interface UserSession {
    id: any;
    user_id: any;
    access_token: string;
    refresh_token: string;
    device_info?: string;
    ip_address?: string;
    location?: string;
    is_active: boolean;
    last_activity: string;
    expires_at: string;
    created_at: string;
}

export interface LoginAttempt {
    id: any;
    username: string;
    ip_address: string;
    user_agent?: string;
    is_success: boolean;
    failure_reason?: string;
    created_at: string;
}

export interface TokenBlacklist {
    id: any;
    token_identifier: string;
    token_hash?: string;
    expires_at: string;
    created_at: string;
    reason?: string;
}

export interface AdPlacement {
    id: any;
    name: string;
    code: string;
    description?: any;
    position: string;
    width?: number;
    height?: number;
    is_active: boolean;
    created_at: string;
    updated_at: string;
}

export interface Ad {
    id: any;
    title: string;
    content?: any;
    image_url?: string;
    link_url?: string;
    alt_text?: string;
    ad_type: string;
    placement_id?: any;
    start_date?: string;
    end_date?: string;
    click_count: any;
    impression_count: any;
    budget?: any;
    cost_per_click?: any;
    cost_per_impression?: any;
    is_active: boolean;
    priority: number;
    target_audience: string;
    device_targeting: string;
    geo_targeting?: string;
    created_at: string;
    updated_at: string;
}

export interface AdClick {
    id: any;
    ad_id: any;
    user_id?: any;
    ip_address?: string;
    user_agent?: any;
    referrer?: string;
    clicked_at: string;
}

export interface AdImpression {
    id: any;
    ad_id: any;
    user_id?: any;
    ip_address?: string;
    user_agent?: any;
    page_url?: string;
    displayed_at: string;
}

export interface RevenueRecord {
    id: any;
    user_id: any;
    revenue_type: string;
    amount: any;
    platform_fee: any;
    creator_earnings: any;
    description?: any;
    reference_id?: any;
    reference_type?: string;
    status: string;
    created_at: string;
    updated_at: string;
}

export interface RevenueSharingConfig {
    id: any;
    revenue_type: string;
    platform_percentage: any;
    creator_percentage: any;
    min_payout_amount: any;
    is_active: boolean;
    description?: any;
    created_at: string;
    updated_at: string;
}

export interface PayoutRequest {
    id: any;
    user_id: any;
    amount: any;
    payment_method: string;
    payment_account: string;
    account_name?: string;
    status: string;
    admin_notes?: any;
    processed_by?: any;
    processed_at?: string;
    created_at: string;
    updated_at: string;
}

export interface UserRevenueStats {
    id: any;
    user_id: any;
    total_earnings: any;
    total_paid: any;
    pending_earnings: any;
    available_balance: any;
    last_payout_at?: string;
    updated_at: string;
}

export interface ChatGroup {
    id: any;
    name: string;
    description?: string;
    avatar?: string;
    creator: any;
    member_count: any;
    last_message_at?: string;
    is_active: boolean;
    created_at: string;
    updated_at: string;
}

export interface ChatGroupMember {
    id: any;
    group: any;
    user: any;
    role: string;
    joined_at: string;
    last_read_at?: string;
    is_muted: boolean;
}

export interface ChatGroupInvite {
    id: any;
    group: any;
    invite_code: string;
    created_by: any;
    expires_at?: string;
    max_uses?: any;
    use_count: any;
    is_active: boolean;
    created_at: string;
}

export interface ScheduledReport {
    id: any;
    name: string;
    report_type: string;
    frequency: string;
    metrics?: any;
    days: number;
    export_format: string;
    is_active: boolean;
    last_run_at?: string;
    next_run_at?: string;
    created_at: string;
    updated_at: string;
}

export interface ReportHistory {
    id: any;
    scheduled_report_id?: any;
    report_name: string;
    report_type: string;
    content: any;
    format: string;
    generated_at: string;
}

export interface ArticleAnnotation {
    id: any;
    article: any;
    user: any;
    parent?: any;
    content: any;
    position?: any;
    selection_text?: string;
    is_resolved: boolean;
    created_at: string;
    updated_at: string;
}

export interface Webhook {
    id: any;
    name: string;
    url: string;
    secret?: string;
    events: any;
    is_active: boolean;
    created_at: string;
    updated_at: string;
}

export interface WebhookDelivery {
    id: any;
    webhook: any;
    event: string;
    payload: any;
    response_status?: number;
    response_body?: any;
    success: boolean;
    retry_count: number;
    next_retry_at?: string;
    created_at: string;
}

export interface Role {
    id: any;
    name: string;
    slug: string;
    description?: string;
    is_system: boolean;
    parent_id?: any;
    is_active: boolean;
    created_at: string;
    updated_at: string;
}

export interface Capability {
    id: any;
    code: string;
    name: string;
    description?: string;
    resource_type?: string;
    action?: string;
    is_active: boolean;
    created_at: string;
    updated_at: string;
}

export interface RoleCapability {
    id: any;
    role_id: any;
    capability_id: any;
    created_at: string;
}

export interface UserRole {
    id: any;
    user_id: any;
    role_id: any;
    assigned_by?: any;
    created_at: string;
}

export interface PermissionAuditLog {
    id: any;
    user_id?: any;
    action: string;
    resource_type?: string;
    resource_id?: any;
    details?: any;
    ip_address?: string;
    created_at: string;
}

export interface Workspace {
    id: any;
    name: string;
    slug: string;
    description?: any;
    owner_id: any;
    is_active: boolean;
    settings?: any;
    created_at: string;
    updated_at: string;
}

export interface WorkspaceMember {
    id: any;
    workspace_id: any;
    user_id: any;
    role: string;
    joined_at: string;
    is_active: boolean;
}

export interface Task {
    id: any;
    workspace_id: any;
    title: string;
    description?: any;
    status: string;
    priority: string;
    assigned_to?: any;
    created_by: any;
    due_date?: string;
    completed_at?: string;
    created_at: string;
    updated_at: string;
}

export interface ApprovalRecord {
    id: any;
    content_type: string;
    content_id: any;
    applicant_id: any;
    current_level: number;
    max_level: number;
    status: string;
    created_at: string;
    updated_at: string;
    completed_at?: string;
}

export interface ApprovalStep {
    id: any;
    record_id: any;
    level: number;
    approver_id?: any;
    action?: string;
    comment?: any;
    reviewed_at?: string;
    created_at: string;
}

export interface Site {
    id: any;
    name: string;
    slug: string;
    domain: string;
    additional_domains?: any;
    description?: any;
    logo_url?: string;
    favicon_url?: string;
    theme: string;
    language: string;
    timezone: string;
    settings?: any;
    is_active: boolean;
    is_default: boolean;
    created_at: string;
    updated_at: string;
}

export interface SiteUser {
    id: any;
    site_id: any;
    user_id: any;
    role: string;
    is_active: boolean;
    joined_at: string;
}

export interface ContentMapping {
    id: any;
    source_site_id: any;
    target_site_id: any;
    content_type: string;
    source_content_id: any;
    target_content_id?: any;
    sync_mode: string;
    last_synced_at?: string;
    created_at: string;
}

export interface GoogleAnalyticsConfig {
    id: any;
    site_id?: any;
    tracking_id: string;
    measurement_id?: string;
    api_secret?: string;
    enable_page_view_tracking: boolean;
    enable_event_tracking: boolean;
    enable_user_behavior_analysis: boolean;
    anonymize_ip: boolean;
    sample_rate: number;
    is_active: boolean;
    created_at: string;
    updated_at: string;
}

export interface BaiduAnalyticsConfig {
    id: any;
    site_id?: any;
    site_token: string;
    api_key?: string;
    enable_tracking: boolean;
    enable_data_sync: boolean;
    is_active: boolean;
    created_at: string;
    updated_at: string;
}

export interface NotificationIntegration {
    id: any;
    site_id?: any;
    platform: string;
    webhook_url: string;
    bot_token?: string;
    channel_id?: string;
    enable_new_article_notification: boolean;
    enable_comment_notification: boolean;
    enable_system_alert: boolean;
    notification_template?: any;
    is_active: boolean;
    created_at: string;
    updated_at: string;
}

export interface EmailServiceConfig {
    id: any;
    site_id?: any;
    provider: string;
    api_key?: string;
    smtp_host?: string;
    smtp_port?: number;
    smtp_username?: string;
    smtp_password?: string;
    from_email: string;
    from_name?: string;
    enable_batch_sending: boolean;
    batch_size: number;
    daily_limit?: number;
    is_active: boolean;
    created_at: string;
    updated_at: string;
}

export interface SAMLConfig {
    id: any;
    site_id?: any;
    entity_id: string;
    acs_url: string;
    slo_url?: string;
    idp_entity_id: string;
    idp_sso_url: string;
    idp_slo_url?: string;
    idp_certificate: any;
    sp_private_key?: any;
    sp_certificate?: any;
    attribute_mapping?: any;
    enable_slo: boolean;
    auto_provision_users: boolean;
    default_role: string;
    is_active: boolean;
    created_at: string;
    updated_at: string;
}

export interface LDAPConfig {
    id: any;
    site_id?: any;
    server_url: string;
    bind_dn: string;
    bind_password: string;
    base_dn: string;
    user_filter: string;
    username_attribute: string;
    email_attribute: string;
    first_name_attribute: string;
    last_name_attribute: string;
    use_ssl: boolean;
    verify_certificates: boolean;
    auto_sync_users: boolean;
    sync_interval: number;
    default_role: string;
    is_active: boolean;
    created_at: string;
    updated_at: string;
}

export interface SSOProvider {
    id: any;
    site_id?: any;
    provider_type: string;
    name: string;
    client_id: string;
    client_secret: string;
    authorization_url?: string;
    token_url?: string;
    userinfo_url?: string;
    scope: string;
    redirect_uri: string;
    attribute_mapping?: any;
    auto_provision_users: boolean;
    default_role: string;
    is_active: boolean;
    created_at: string;
    updated_at: string;
}

export interface PaymentGateway {
    id: any;
    name: string;
    provider: string;
    config_data?: any;
    is_active: boolean;
    supported_currencies: string;
    created_at: string;
    updated_at: string;
}

export interface PaymentTransaction {
    id: any;
    user: any;
    order_id: string;
    gateway: any;
    amount: any;
    currency: string;
    status: string;
    transaction_id?: string;
    payment_method?: string;
    metadata?: any;
    created_at: string;
    updated_at: string;
}

export interface CryptoPayment {
    id: any;
    transaction: any;
    wallet_address: string;
    blockchain: string;
    token_symbol: string;
    tx_hash?: string;
    confirmations: number;
    required_confirmations: number;
    exchange_rate?: any;
    crypto_amount?: any;
    status: string;
    expires_at?: string;
    created_at: string;
    updated_at: string;
}

export interface TaxConfig {
    id: any;
    country: string;
    region?: string;
    tax_type: string;
    rate: any;
    description?: string;
    is_active: boolean;
    effective_from: string;
    effective_to?: string;
    created_at: string;
    updated_at: string;
}

export interface OrderItem {
    id: any;
    order: any;
    product_id?: any;
    product_name: string;
    quantity: number;
    unit_price: any;
    total_price: any;
    metadata?: any;
    created_at: string;
    updated_at: string;
}

export interface EnterpriseLicense {
    id: any;
    license_key: string;
    license_type: string;
    company_name: string;
    contact_email: string;
    max_sites: number;
    features?: any;
    valid_from: string;
    valid_until?: string;
    is_active: boolean;
    support_level: string;
    sla_enabled: boolean;
    sla_uptime_guarantee?: number;
    created_at: string;
    updated_at: string;
}

export interface SupportTicket {
    id: any;
    ticket_number: string;
    user_id: any;
    license_id?: any;
    subject: string;
    description: any;
    priority: string;
    status: string;
    category: string;
    assigned_to?: any;
    resolved_at?: string;
    closed_at?: string;
    created_at: string;
    updated_at: string;
}

export interface SupportTicketReply {
    id: any;
    ticket_id: any;
    user_id: any;
    content: any;
    is_staff: boolean;
    attachments?: any;
    created_at: string;
}

export interface DeploymentScript {
    id: any;
    name: string;
    script_type: string;
    content: any;
    version: string;
    description?: any;
    parameters?: any;
    is_active: boolean;
    created_by?: any;
    created_at: string;
    updated_at: string;
}

export interface DeploymentLog {
    id: any;
    script_id: any;
    user_id?: any;
    status: string;
    output?: any;
    error_message?: any;
    started_at?: string;
    completed_at?: string;
    created_at: string;
}

export interface MonitoringAlert {
    id: any;
    alert_type: string;
    severity: string;
    title: string;
    message: any;
    source?: string;
    metric_name?: string;
    metric_value?: any;
    threshold?: any;
    is_resolved: boolean;
    resolved_at?: string;
    notified_users?: any;
    created_at: string;
    updated_at: string;
}

export interface MonitoringMetric {
    id: any;
    metric_name: string;
    metric_value: any;
    metric_type: string;
    labels?: any;
    timestamp: string;
    site_id?: any;
}

export interface MigrationTask {
    id: any;
    task_name: string;
    source_platform: string;
    status: string;
    config?: any;
    progress: number;
    total_items: any;
    migrated_items: any;
    error_message?: any;
    started_at?: string;
    completed_at?: string;
    created_by: any;
    created_at: string;
    updated_at: string;
}

export interface MigrationLog {
    id: any;
    task_id: any;
    log_level: string;
    message: any;
    item_type?: string;
    item_id?: any;
    created_at: string;
}

export interface GlobalStyleConfig {
    id: any;
    name: string;
    slug: string;
    is_active: boolean;
    theme_type: string;
    color_scheme: any;
    typography: any;
    spacing: any;
    border_radius: any;
    shadows?: any;
    breakpoints?: any;
    css_variables?: any;
    preview_image?: string;
    created_by?: any;
    created_at: string;
    updated_at: string;
}


// 通用响应类型
export interface ApiResponse<T = any> {
    success: boolean;
    data?: T;
    error?: string;
    message?: string;
}

// 请求参数类型
export interface Get_users_list_apiParams {
    page?: number;
    per_page?: number;
    search?: string;
}
export interface Update_menuParams {
    menu_id: number;
}
export interface Delete_menuParams {
    menu_id: number;
}
export interface Update_pageParams {
    page_id: number;
}
export interface Delete_pageParams {
    page_id: number;
}
export interface Update_menu_itemParams {
    menu_item_id: number;
}
export interface Delete_menu_itemParams {
    menu_item_id: number;
}
export interface Download_backupParams {
    filename: string;
}
export interface Admin_roles_searchParams {
    page?: number;
    per_page?: number;
    search?: string;
}
export interface Admin_role_detailParams {
    role_id: number;
}
export interface Update_roleParams {
    role_id: number;
}
export interface Delete_roleParams {
    role_id: number;
}
export interface Get_permissionsParams {
    page?: number;
    per_page?: number;
    search?: string;
}
export interface Update_permissionParams {
    permission_id: number;
}
export interface Delete_permissionParams {
    permission_id: number;
}
export interface Get_user_rolesParams {
    user_id: number;
}
export interface Update_user_rolesParams {
    user_id: number;
}
export interface Update_article_statusParams {
    article_id: number;
    current_user_obj?: string;
}
export interface Get_password_formParams {
    aid: number;
}
export interface Api_update_article_passwordParams {
    aid: number;
}
export interface Like_articleParams {
    article_id: number;
    current_user_obj?: string;
}
export interface Record_article_viewParams {
    article_id: number;
}
export interface Create_article_revisionParams {
    article_id: number;
    change_summary?: string;
}
export interface List_article_revisionsParams {
    article_id: number;
    page?: number;
    per_page?: number;
}
export interface Get_revisionParams {
    revision_id: number;
}
export interface Rollback_articleParams {
    article_id: number;
    revision_id: number;
}
export interface Compare_article_revisionsParams {
    revision1_id: number;
    revision2_id: number;
}
export interface Save_article_draftParams {
    article_id: number;
}
export interface Sync_article_revisionsParams {
    article_id: number;
}
export interface Delete_article_revisionParams {
    article_id: number;
    revision_id: number;
}
export interface Create_article_revisionParams {
    article_id: number;
}
export interface List_article_revisionsParams {
    article_id: number;
    page?: number;
    per_page?: number;
}
export interface Get_revisionParams {
    revision_id: number;
}
export interface Rollback_articleParams {
    article_id: number;
    revision_id: number;
}
export interface Compare_article_revisionsParams {
    revision1_id: number;
    revision2_id: number;
}
export interface Sync_article_revisionsParams {
    article_id: number;
}
export interface Delete_article_revisionParams {
    article_id: number;
    revision_id: number;
}
export interface Get_articles_apiParams {
    page?: number;
    per_page?: number;
    search?: string;
    category_id?: number;
    user_id?: number;
    status?: string;
}
export interface Get_article_detail_apiParams {
    article_id: number;
}
export interface Get_article_raw_content_apiParams {
    article_id: number;
}
export interface Update_article_apiParams {
    article_id: number;
}
export interface Delete_article_apiParams {
    article_id: number;
}
export interface Get_user_articles_apiParams {
    user_id: number;
    page?: number;
    per_page?: number;
}
export interface Get_user_articles_stats_apiParams {
    user_id: number;
}
export interface Get_article_by_slug_apiParams {
    slug: string;
}
export interface Get_article_by_id_apiParams {
    article_id: number;
}
export interface Get_articles_by_tag_apiParams {
    tag_name: string;
}
export interface Get_contribute_info_apiParams {
    article_id: number;
}
export interface Submit_contribution_apiParams {
    article_id: number;
}
export interface Get_edit_article_apiParams {
    article_id: number;
}
export interface Update_article_via_blog_apiParams {
    article_id: number;
}
export interface Api_blog_i18n_contentParams {
    aid: number;
    iso: string;
}
export interface Update_avatar_apiParams {
    file: string;
}
export interface Login_apiParams {
    username: string;
    password: string;
    remember_me?: boolean;
}
export interface Register_apiParams {
    username: string;
    email: string;
    password: string;
}
export interface Get_user_management_usersParams {
    page?: number;
    per_page?: number;
    role?: string;
    search?: string;
}
export interface Delete_backup_fileParams {
    backup_filename: string;
}
export interface Get_blog_management_articlesParams {
    page?: number;
    per_page?: number;
    status?: string;
    search?: string;
    category_id?: number;
}
export interface Delete_blog_management_articleParams {
    article_id: number;
}
export interface Get_all_categories_apiParams {
    page?: number;
}
export interface Get_public_categories_apiParams {
    page?: number;
}
export interface Get_category_by_name_apiParams {
    name: string;
    page?: number;
}
export interface Get_all_categories_root_apiParams {
    page?: number;
}
export interface Update_category_apiParams {
    category_id: number;
}
export interface Get_categories_with_stats_apiParams {
    page?: number;
    per_page?: number;
}
export interface Delete_category_apiParams {
    category_id: number;
}
export interface Confirm_email_changeParams {
    token: string;
    current_user_obj?: string;
}
export interface Check_emailParams {
    email: string;
}
export interface Api_check_emailParams {
    email: string;
}
export interface Check_usernameParams {
    username: string;
}
export interface Api_check_usernameParams {
    username: string;
}
export interface Get_home_articles_apiParams {
    page?: number;
    per_page?: number;
}
export interface Get_home_dataParams {
    limit_featured?: number;
    limit_popular?: number;
    limit_recent?: number;
    limit_categories?: number;
}
export interface Get_featured_articlesParams {
    limit?: number;
}
export interface Get_recent_articlesParams {
    page?: number;
    per_page?: number;
    category_id?: number;
}
export interface Get_popular_articlesParams {
    limit?: number;
    days?: number;
}
export interface Get_home_categoriesParams {
    limit?: number;
}
export interface Subscribe_emailParams {
    email: string;
}
export interface Search_home_articlesParams {
    q: string;
    page?: number;
    per_page?: number;
}
export interface Email_exists_backParams {
    email: string;
}
export interface Get_rss_feedParams {
    limit?: number;
    category_id?: number;
}
export interface Get_atom_feedParams {
    limit?: number;
    category_id?: number;
}
export interface Login_management_apiParams {
    username: string;
    password: string;
    remember_me?: boolean;
}
export interface Register_management_apiParams {
    username: string;
    email: string;
    password: string;
}
export interface Get_user_profile_apiParams {
    user_id: number;
}
export interface Get_usersParams {
    page?: number;
    per_page?: number;
    search?: string;
}
export interface Get_user_media_apiParams {
    current_user_obj?: string;
    media_type?: string;
    page?: number;
}
export interface Get_media_file_by_idParams {
    media_id: number;
    range_header?: string;
    current_user_obj?: string;
}
export interface Delete_user_media_apiParams {
    current_user_obj?: string;
    file_id_list: string;
}
export interface Upload_media_fileParams {
    current_user_obj?: string;
}
export interface Chunked_upload_initParams {
    current_user_obj?: string;
}
export interface Chunked_upload_chunkParams {
    current_user_obj?: string;
}
export interface Chunked_upload_completeParams {
    current_user_obj?: string;
}
export interface Chunked_upload_progressParams {
    current_user_obj?: string;
}
export interface Chunked_upload_chunksParams {
    current_user_obj?: string;
}
export interface Chunked_upload_cancelParams {
    current_user_obj?: string;
}
export interface Get_media_management_filesParams {
    page?: number;
    per_page?: number;
    file_type?: string;
}
export interface Get_menu_detailParams {
    menu_id: number;
}
export interface Update_existing_menuParams {
    menu_id: number;
}
export interface Delete_existing_menuParams {
    menu_id: number;
}
export interface Add_item_to_menuParams {
    menu_id: number;
}
export interface Update_menu_item_detailParams {
    item_id: number;
}
export interface Delete_menu_item_detailParams {
    item_id: number;
}
export interface Reorder_menuParams {
    menu_id: number;
}
export interface Get_my_articlesParams {
    page?: number;
    per_page?: number;
    status?: string;
}
export interface Read_notification_apiParams {
    nid: number;
}
export interface Clean_notification_apiParams {
    nid?: string;
}
export interface Mark_notification_as_read_apiParams {
    notification_id: number;
}
export interface Delete_notification_apiParams {
    notification_id: number;
}
export interface List_pagesParams {
    page?: number;
    per_page?: number;
    status?: number;
}
export interface Get_page_detailParams {
    slug: string;
}
export interface Update_existing_pageParams {
    page_id: number;
}
export interface Delete_existing_pageParams {
    page_id: number;
}
export interface Assign_user_roleParams {
    user_id: number;
}
export interface Get_user_permissionsParams {
    user_id: number;
}
export interface Activate_pluginParams {
    plugin_id: number;
}
export interface Deactivate_pluginParams {
    plugin_id: number;
}
export interface Uninstall_pluginParams {
    plugin_id: number;
}
export interface Update_plugin_settingsParams {
    plugin_id: number;
}
export interface Update_role_for_managementParams {
    role_id: number;
}
export interface Delete_role_for_managementParams {
    role_id: number;
}
export interface Update_permission_for_managementParams {
    permission_id: number;
}
export interface Delete_permission_for_managementParams {
    permission_id: number;
}
export interface List_scheduled_articlesParams {
    page?: number;
    per_page?: number;
}
export interface Cancel_article_scheduleParams {
    article_id: number;
}
export interface Suggest_tagsParams {
    query?: string;
}
export interface Activate_themeParams {
    theme_id: number;
}
export interface Preview_themeParams {
    theme_id: number;
}
export interface Update_theme_settingsParams {
    theme_id: number;
}
export interface Uninstall_themeParams {
    theme_id: number;
}
export interface Public_media_thumbnailParams {
    data: string;
}
export interface Upload_coverParams {
    current_user_obj?: string;
}
export interface Api_user_avatarParams {
    user_id?: number;
}
export interface Api_user_bioParams {
    user_id: number;
}
export interface Api_user_profile_endpointParams {
    user_id: number;
}
export interface Username_existsParams {
    username: string;
}
