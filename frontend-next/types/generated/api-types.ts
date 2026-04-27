/**
 * API 类型定义
 * 由 routes.yaml 自动生成 - 请勿手动修改
 * 生成时间：2026-04-26 19:54:29
 */

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
    backup_codes?: string;
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

export interface ArticleI18n {
    i18n_id: any;
    article: any;
    language_id: string;
    title: string;
    slug: string;
    content: any;
    excerpt?: string;
    created_at: string;
    updated_at: string;
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

export interface SearchHistory {
    id: any;
    user: any;
    keyword: string;
    results_count: any;
    created_at: string;
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

export interface Role {
    id: any;
    name: string;
    slug: string;
    description?: string;
    permissions?: string;
    is_system: boolean;
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

export interface UserRole {
    id: any;
    user_id: any;
    role_id: any;
    assigned_by?: any;
    created_at: string;
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
