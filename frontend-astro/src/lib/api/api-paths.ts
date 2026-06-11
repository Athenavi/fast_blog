// ============================================================================
// FastBlog API 路径常量映射表
//
// 单一路径真相源（Single Source of Truth）
// 所有前端 service 文件应当引用此文件中的常量，而非直接硬编码路径字符串。
// 如需修改 API 路径，只改此处一处即可。
//
// buildUrl() 规则（参见 base-client.ts）：
//   - 以 "/api/" 开头的路径 → 原样使用（完整路径）
//   - 其他路径 → 自动添加 "/api/v2" 前缀（相对路径）
// ============================================================================

// ─── Auth 认证 ─────────────────────────────────
export const AUTH = {
  LOGIN: '/auth/login',
  LOGOUT: '/auth/logout',
  REGISTER: '/auth/register',
  REFRESH_TOKEN: '/auth/token/refresh',
  REFRESH_TOKEN_FULL: '/api/v2/auth/token/refresh', // XHR/fetch 直连用
  CHECK_USERNAME: '/auth/check-username',
  CHECK_EMAIL: '/auth/check-email',
  QR_GENERATE: '/auth/qr/generate',
  QR_STATUS: '/auth/qr/status',
  QR_CONFIRM: '/auth/qr/confirm',
  QR_MOBILE_LOGIN_PAGE: '/auth/qr/mobile-login-page',
  ME: '/users/me',                        // 获取当前用户
  ME_AVATAR: (base: string) => `${base}/api/v2/static/avatar`, // 头像
  ME_AVATAR_UPLOAD: '/users/me/avatar',
  ME_CHANGE_PASSWORD: '/users/me/change-password',
} as const;

// ─── Articles 文章 ──────────────────────────────
export const ARTICLES = {
  LIST: '/articles',
  CREATE: '/articles',
  DETAIL: (id: number | string) => `/articles/${id}`,
  UPDATE: (id: number | string) => `/articles/${id}`,
  DELETE: (id: number | string) => `/articles/${id}`,
  BY_SLUG: (slug: string) => `/articles/p/${slug}`,
  EDIT: (id: number | string) => `/articles/edit/${id}`,
  NEW: '/articles/new',
  CONTRIBUTE: (id: number | string) => `/articles/contribute/${id}`,
  HOME: '/home/articles',
  FEATURED: '/articles/featured',
  SEARCH: '/articles/search',
  TAG: (tag: string) => `/articles/tag/${tag}`,
  USER: (userId: number) => `/articles/user/${userId}`,
  POPULAR: '/articles/popular',
  RECENT: '/articles/recent',
  HOME_SLUG: (slug: string) => `/articles/p/${slug}`,       // buildUrl → /api/v2/articles/p/${slug}
  HOME_SLUG_FULL: (slug: string) => `/api/v2/articles/p/${slug}`, // 直连
  HOME_LIST: '/articles/home',             // 首页文章列表
  SLUG: (slug: string) => `/articles/slug/${slug}`,
  REVISIONS_COMPARE: '/articles/revisions/compare',
} as const;

// ─── Comments 评论 ──────────────────────────────
export const COMMENTS = {
  LIST: (articleId: number) => `/comments/enhanced/article/${articleId}`,
  CREATE: '/comments/',
  DETAIL: (id: number) => `/comments/${id}`,
  UPDATE: (id: number) => `/comments/${id}`,
  DELETE: (id: number) => `/comments/${id}`,
  PENDING: '/comments/pending',
  APPROVE: (id: number) => `/comments/${id}/approve`,
  REJECT: (id: number) => `/comments/${id}/reject`,
  LIKE: (id: number) => `/comments/enhanced/${id}/like`,
  VOTE: (id: number) => `/comments/enhanced/${id}/vote`,
  VOTE_LIKE: (id: number) => `/comments/enhanced/${id}/vote/like`,
  VOTE_DISLIKE: (id: number) => `/comments/enhanced/${id}/vote/dislike`,
  SUBSCRIPTIONS: '/comments/subscriptions/my-subscriptions',
  SUBSCRIBE: '/comments/subscriptions/subscribe',
  UNSUBSCRIBE: '/comments/subscriptions/unsubscribe',
} as const;

// ─── Categories 分类 ────────────────────────────
export const CATEGORIES = {
  LIST: '/cms/categories/',
  CREATE: '/cms/categories/',
  DETAIL: (name: string) => `/cms/categories/${name}`,
  UPDATE: (id: number) => `/cms/categories/${id}`,
  DELETE: (id: number) => `/cms/categories/${id}`,
  REORDER: '/cms/categories/reorder',
  HOME: '/home/categories',
  BY_NAME: (name: string) => `/cms/categories/name/${name}`,
  POPULAR: '/cms/categories/popular',
} as const;

// ─── Media 媒体 ─────────────────────────────────
export const MEDIA = {
  LIST: '/media/files',
  LIST_FULL: '/api/v2/media/files',
  FILES_LIST: '/media/files/list',          // 别名（后端同时支持 /files 和 /files/list）
  UPLOAD: '/media/upload',
  UPLOAD_FULL: '/api/v2/media/upload', // XHR 直连用完整路径
  DETAIL: (id: number) => `/media/detail/${id}`,
  DELETE: (id: number) => `/media/?file-id-list=${id}`,
  BATCH_DELETE: '/media/batch-delete',
  TAGS: (id: number) => `/media/${id}/tags`,
  FOLDERS_LIST: '/media/folders/list',
  FOLDERS_TREE: '/media/folders/tree',
  FOLDERS_MOVE: '/media/folders/move-media',
  FOLDERS_CREATE: '/media/folders/',
  FOLDERS_DELETE: (id: number) => `/media/folders/${id}`,
  CHUNK_INIT: '/media/upload/chunked/init',
  CHUNK_UPLOAD: '/media/upload/chunked/chunk',
  CHUNK_COMPLETE: '/media/upload/chunked/complete',
  CHUNK_CANCEL: '/media/upload/chunked/cancel',
  COVER_UPLOAD: '/api/v2/media/cover',
  TAGS_LIST: '/media/tags',
  CATEGORIES: '/media/categories',
  BATCH_CATEGORIZE: '/media/batch-categorize',
  BATCH_TAGS: '/media/batch-tags',
  SETTINGS_UPLOAD: '/api/v2/media/settings/upload',
  // VIP 离线下载
  OFFLINE_DOWNLOAD_LIMITS: '/media/offline-download/limits',
  OFFLINE_DOWNLOAD_TASKS: '/media/offline-download/tasks',
  OFFLINE_DOWNLOAD_TASK: (id: number) => `/media/offline-download/tasks/${id}`,
  OFFLINE_DOWNLOAD_CANCEL: (id: number) => `/media/offline-download/tasks/${id}/cancel`,
  OFFLINE_DOWNLOAD_RETRY: (id: number) => `/media/offline-download/tasks/${id}/retry`,
} as const;

// ─── Home 首页 ──────────────────────────────────
export const HOME = {
  DATA: '/home/data',
  CONFIG: '/home/config',
  FEATURED: '/home/featured',
  RECENT: '/home/recent',
  POPULAR: '/home/popular',
  CATEGORIES: '/home/categories',
  STATS: '/home/stats',
  SEARCH: '/home/search',
} as const;

// ─── Dashboard 仪表盘 ──────────────────────────
export const DASHBOARD = {
  STATS: '/dashboard/stats',
  RECENT_ARTICLES: '/dashboard/recent-articles',
  ANALYTICS_OVERVIEW: '/dashboard/analytics/overview',
  ARTICLE_VIEWS_TREND: '/dashboard/analytics/article-views-trend',
  POPULAR_ARTICLES: '/dashboard/analytics/popular-articles',
  CATEGORY_DISTRIBUTION: '/dashboard/analytics/category-distribution',
  TRAFFIC_SOURCES: '/dashboard/analytics/traffic-sources',
  DEVICE_STATS: '/dashboard/analytics/device-stats',
  USER_ACTIVITY: '/dashboard/analytics/user-activity',
  CONTENT_PERFORMANCE: '/dashboard/analytics/content-performance',
  BLOG_MGMT_ARTICLES: '/dashboard/blog-management/articles',
  BLOG_MGMT_ARTICLE_STATS: '/dashboard/blog-management/articles/stats',
  BLOG_MGMT_ARTICLE: (id: number) => `/dashboard/blog-management/articles/${id}`,
  USER_MGMT_USERS: '/dashboard/user-management/users',
  USER_MGMT_USER_ACTION: (id: number, action: string) => `/dashboard/user-management/users/${id}/${action}`,
  MEDIA_MGMT_FILES: '/api/v2/dashboard/media-management/files',
  MEDIA_MGMT_UPLOAD_TASKS: '/api/v2/dashboard/media-management/upload-tasks',
  ACTIVITIES: '/dashboard/activities',
  VIP_MANAGEMENT: '/dashboard/vip-management',
  VIP_FEATURES: '/dashboard/vip/features',
  VIP_PLANS: '/dashboard/vip/plans',
  MY_ARTICLES: '/dashboard/my/articles',
} as const;

// ─── Users 用户 ─────────────────────────────────
export const USERS = {
  LIST: '/users/',
  ME: '/users/me',
  DETAIL: (id: number) => `/users/${id}`,
  UPDATE: (id: number) => `/users/${id}`,
  RECOMMENDATIONS: '/users/recommendations',
  ME_FOLLOWERS: '/users/me/followers',
  ME_FOLLOWING: '/users/me/following',
  FOLLOW: (id: number) => `/users/${id}/follow`,
  UNFOLLOW: (id: number) => `/users/${id}/follow`,
  // User security sub-features
  SECURITY_EMAIL_SUBSCRIPTIONS: '/users/security/email-subscriptions',
  SECURITY_FIELD_PERMISSIONS: '/users/security/field-permissions',
  SECURITY_SESSIONS: '/users/security/sessions',
} as const;

// ─── RBAC / Security 权限安全 ───────────────────
export const RBAC = {
  ROLES: '/security/rbac/roles',
  ROLE: (id: number) => `/security/rbac/roles/${id}`,
  ROLE_PERMISSIONS: (id: number) => `/security/rbac/roles/${id}/permissions`,
  PERMISSIONS: '/security/rbac/permissions',
  USER_ROLES: (userId: number) => `/security/rbac/users/${userId}/roles`,
} as const;

// ─── Enterprise 企业 ────────────────────────────
export const ENTERPRISE = {
  LICENSES: '/enterprise/admin/licenses',
  LICENSE: (id: number) => `/enterprise/admin/licenses/${id}`,
  TICKETS: '/enterprise/admin/tickets',
  TICKET: (id: number) => `/enterprise/admin/tickets/${id}`,
  TICKET_REPLY: (ticketId: number) => `/enterprise/support/ticket/${ticketId}/reply`,
  SCRIPTS: '/enterprise/admin/scripts',
  SCRIPT: (id: number) => `/enterprise/admin/scripts/${id}`,
  DEPLOY_SCRIPT: '/enterprise/deployment/script',
  EXECUTE_SCRIPT: (scriptId: number) => `/enterprise/deployment/script/${scriptId}/execute`,
  LOGS: '/enterprise/admin/logs',
  ALERTS: '/enterprise/admin/alerts',
  ALERT: (id: number) => `/enterprise/admin/alerts/${id}`,
  ALERT_RESOLVE: (id: number) => `/enterprise/admin/alerts/${id}/resolve`,
  METRICS: '/enterprise/admin/metrics',
  OVERVIEW: '/enterprise/admin/overview',
} as const;

// ─── Ads 广告 ───────────────────────────────────
export const ADS = {
  SLOTS: '/ads/slots',
  CREATE: '/ads/create',
  LIST: '/ads/list',
  PAUSE: (id: number) => `/ads/${id}/pause`,
  ACTIVATE: (id: number) => `/ads/${id}/activate`,
  DELETE: (id: number) => `/ads/${id}`,
  STATS: (id: number) => `/ads/${id}/stats`,
  NETWORK_CONFIGURE: '/ads/network/configure',
  NETWORK_CONFIG: (network: string) => `/ads/network/${network}/config`,
  ADSENSE_CODE: '/ads/network/adsense/code',
  BAIDU_CODE: '/ads/network/baidu/code',
  REVENUE_REPORT: '/ads/revenue/report',
} as const;

// ─── Admin / Batch 管理 ─────────────────────────
export const ADMIN_BATCH = {
  DELETE_ARTICLES: '/admin/batch/articles/delete',
  UPDATE_ARTICLE_STATUS: '/admin/batch/articles/update-status',
  UPDATE_ARTICLE_SORT: '/admin/batch/articles/update-sort',
  SETTINGS: '/admin/settings/',
  SETTINGS_MENUS: '/admin/settings/menus',
  SETTINGS_MENU: (id: number) => `/admin/settings/menus/${id}`,
  SETTINGS_PAGES: '/admin/settings/pages',
  SETTINGS_PAGE: (id: number) => `/admin/settings/pages/${id}`,
  SETTINGS_MENU_ITEMS: '/admin/settings/menu-items',
  SETTINGS_MENU_ITEM: (id: number) => `/admin/settings/menu-items/${id}`,
} as const;

// ─── Search 搜索 ────────────────────────────────
export const SEARCH = {
  SEARCH: '/home/search',
  QUICK: '/api/v2/search',
  HISTORY: '/search/history',
  SUGGESTIONS: '/search/suggestions',
  STATS: '/search/stats',
  MEDIA_OPTIMIZATION: '/search/management/media-optimization',
  SEARCH_INDEX: '/search/management/search-index',
  SEARCH_INDEX_BATCH_REINDEX: '/search/management/search-index/batch-reindex',
} as const; 

// ─── Feed 订阅 ──────────────────────────────────
export const FEED = {
  RSS: '/api/v2/feed/rss',
  ATOM: '/api/v2/feed/atom',
} as const;

// ─── Backup 备份 ────────────────────────────────
export const BACKUP = {
  LIST: '/backup/list',
  FULL: '/backup/full',
  DATABASE: '/backup/database',
  FILES: '/backup/files',
  DELETE: (filename: string) => `/backup/delete?filename=${filename}`,
} as const;

// ─── Membership / VIP ──────────────────────────
export const MEMBERSHIP = {
  PLANS: '/membership/plans',
  FEATURES: '/membership/features',
  MY_SUBSCRIPTION: '/membership/my-subscription',
  PREMIUM_CONTENT: '/membership/premium-content',
  SUBSCRIBE: '/membership/subscribe',
  STATUS: '/membership/status',
} as const;

// ─── Tipping 打赏 ──────────────────────────────
export const TIPPING = {
  TIP: '/ext/tipping/tip-article',
  ARTICLE: (id: number) => `/ext/tipping/article/${id}`,
  MY_RECEIVED: '/ext/tipping/my-received',
  MY_STATS: '/ext/tipping/my-stats',
  LEADERBOARD: '/ext/tipping/leaderboard',
  PRESET_AMOUNTS: '/ext/tipping/preset-amounts',
  RECENT: '/ext/tipping/recent',
  BALANCE: '/ext/tipping/balance',
  WITHDRAW: '/ext/tipping/withdraw',
  MY_WITHDRAWALS: '/ext/tipping/my-withdrawals',
  CANCEL_WITHDRAWAL: (id: number) => `/ext/tipping/cancel-withdrawal/${id}`,
  ADMIN_PROCESS: '/ext/tipping/admin/process-withdrawal',
} as const;

// ─── Misc 杂项 ──────────────────────────────────
export const MISC = {
  VERSION: '/misc/version',
  VERSION_SUMMARY: '/misc/version-summary',
  CHECK_UPDATE: '/misc/check-update',
} as const;

// ─── System 系统 ────────────────────────────────
export const SYSTEM = {
  TRANSFER_TASKS: '/api/v2/system/transfer/tasks',
  BACKUP_MGMT: '/api/v2/system/backup',
  BACKUP_LIST: '/api/v2/system/backup/list',
  BACKUP_STATS: '/api/v2/system/backup/stats',
  BACKUP_CREATE: (type: string) => `/api/v2/system/backup/${type}`,
  BACKUP_DELETE: (filename: string) => `/api/v2/system/backup/${encodeURIComponent(filename)}`,
  BACKUP_CLEANUP: '/api/v2/system/backup/cleanup',
  BACKUP_DOWNLOAD: (filename: string) => `/api/v2/system/backup/download/${filename}`,
  SETTINGS: '/system/settings/',
  SETTINGS_MENUS: '/system/settings/menus',
  SETTINGS_MENU_ITEMS: '/system/settings/menu-items',
  SETTINGS_PAGES: '/system/settings/pages',
  INFO: '/system/info',
  HEALTH: '/system/health',
  VERSION_FULL: '/system/version/full',
  ACCESSIBILITY_CONFIG: '/system/accessibility/config',
  MULTISITE: '/system/multisite',
  MULTISITE_USERS: '/system/multisite/users',
} as const;

// ─── Notifications 通知 ─────────────────────────
export const NOTIFICATIONS = {
  MESSAGES: '/notifications/messages',
  EMAIL_SEND: '/notifications/email/send',
  READ_ALL: '/notifications/read-all',
  MESSAGES_CLEAN: '/notifications/messages/clean',
  MESSAGES_READ_ALL: '/notifications/messages/read_all',
} as const;

// ─── Security 安全（2FA / 会话 / 审计）────────
export const SECURITY = {
  TWO_FA_VERIFY_LOGIN: '/security/2fa/verify-login',
  TWO_FA_STATUS: '/security/2fa/status',
  TWO_FA_SETUP: '/security/2fa/setup',
  TWO_FA_ENABLE: '/security/2fa/enable',
  TWO_FA_DISABLE: '/security/2fa/disable',
  MY_SESSIONS: '/security/admin/session/my-sessions',
  REVOKE_SESSION: '/security/admin/session/revoke',
  REVOKE_ALL_SESSIONS: '/security/admin/session/revoke-all',
  AUDIT_LOG_LOGS: '/security/audit-log/logs',
  AUDIT_LOG_STATS: '/security/audit-log/stats',
  AUDIT_LOG_EXPORT: '/security/audit-log/export',
  AUDIT_LOG_CLEANUP: '/security/audit-log/cleanup',
  AUDIT_LOGS: '/security/audit/logs',
  DASHBOARD_SUMMARY: '/security/dashboard/summary',
  SENSITIVE_WORDS: '/api/v2/security/sensitive-words/',
  SENSITIVE_WORDS_STATS: '/api/v2/security/sensitive-words/statistics',
  SENSITIVE_WORDS_DETAIL: (id: number) => `/api/v2/security/sensitive-words/${id}`,
  SENSITIVE_WORDS_REFRESH_CACHE: '/api/v2/security/sensitive-words/refresh-cache',
  SENSITIVE_WORDS_BATCH_IMPORT: '/api/v2/security/sensitive-words/batch-import',
  CONTENT_APPROVAL_STATS: '/security/content-approval/stats',
  CONTENT_APPROVAL_MY_REQUESTS: '/security/content-approval/my-requests',
  CONTENT_APPROVAL_PENDING: '/security/content-approval/pending',
} as const;

// ─── Plugins 插件 ───────────────────────────────
export const PLUGINS = {
  ACTIVE: '/plugins/active',
  MARKETPLACE: '/plugins/marketplace',
  INSTALL: '/plugins/install',
} as const;

// ─── Templates 模板 ─────────────────────────────
export const TEMPLATES = {
  LIST: '/templates/templates/list',
  CATEGORIES: '/templates/templates/categories',
} as const;

// ─── Webhooks ───────────────────────────────────
export const WEBHOOKS = {
  DELIVERIES: '/webhooks/deliveries',
} as const;

// ─── AI（技能 / 内容 / 工作流）─────────────────
export const AI = {
  SKILLS_LIST: '/ai/skills/ai-skills/list',
  CONTENT_EXTRACT_KEYWORDS: '/ai/content/ai-content/extract-keywords',
  CONTENT_GENERATE_META: '/ai/content/ai-content/generate-meta-description',
  CONTENT_GENERATE_OUTLINE: '/ai/content/ai-content/generate-outline',
  WORKFLOWS: '/ai/workflows',
} as const;

// ─── AI 推荐（写作助手）────────────────────────
export const AI_RECOMMENDATIONS = {
  WRITING_POLISH: '/ext/ai-recommendations/writing/polish',
  WRITING_GRAMMAR: '/ext/ai-recommendations/writing/check-grammar',
  WRITING_GENERATE_TITLES: '/ext/ai-recommendations/writing/generate-titles',
  WRITING_CONTINUE: '/ext/ai-recommendations/writing/continue',
  WRITING_EXTRACT_SUMMARY: '/ext/ai-recommendations/extract-summary',
  WRITING_TRANSFORM_STYLE: '/ext/ai-recommendations/writing/transform-style',
  RECOMMEND_TAGS: '/ext/ai-recommendations/recommend-tags',
} as const;

// ─── Recommendations 推荐 ───────────────────────
export const RECOMMENDATIONS = {
  TRENDING: '/ext/recommendations/trending',
  RISING_STARS: '/ext/recommendations/rising-stars',
  PERSONALIZED: '/ext/recommendations/personalized',
} as const;

// ─── Collaboration 协作 ─────────────────────────
export const COLLABORATION = {
  WORKSPACES: '/collaboration/team/workspaces',
  COMMENTS_STATS: '/collaboration/comments/statistics',
} as const;

// ─── Badges / Certification / NFT / Points ─────
export const BADGES = {
  ADMIN_STATS: '/ext/badges/admin/stats',
  AVAILABLE: '/ext/badges/available',
} as const;

export const CERTIFICATION = {
  ADMIN_STATS: '/ext/expert-certification/admin/stats',
  FIELDS: '/ext/expert-certification/fields',
  PENDING_APPLICATIONS: '/ext/expert-certification/admin/pending-applications',
  EXPERTS: '/ext/expert-certification/experts',
  REVIEW: '/ext/expert-certification/admin/review',
  REVOKE: '/ext/expert-certification/admin/revoke',
} as const;

export const NFT = {
  MINT: '/ext/nft/mint',
} as const;

export const POINTS = {
  ADMIN_STATS: '/ext/points/admin/stats',
  POINTS_RULES: '/ext/points/points-rules',
  EXCHANGE_RULES: '/ext/points/exchange-rules',
  LEADERBOARD: '/ext/points/leaderboard',
  ADD_POINTS: '/ext/points/admin/add-points',
  DEDUCT_POINTS: '/ext/points/admin/deduct-points',
} as const;

// ─── MCP / AI 聊天 ────────────────────────────
export const MCP_CHAT = {
  CHAT: '/api/v2/mcp/chat',
  STREAM: '/api/v2/mcp/chat/stream',
  TOOLS: '/api/v2/mcp/tools',
  INFO: '/api/v2/mcp/info',
} as const;
