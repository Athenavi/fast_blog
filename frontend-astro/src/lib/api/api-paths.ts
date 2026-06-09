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
  CHECK_USERNAME: '/auth/check-username',
  CHECK_EMAIL: '/auth/check-email',
  QR_GENERATE: '/auth/qr/generate',
  QR_STATUS: '/auth/qr/status',
  QR_CONFIRM: '/auth/qr/confirm',
  QR_MOBILE_LOGIN_PAGE: '/auth/qr/mobile-login-page',
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
  LIST: '/categories/',
  CREATE: '/categories/',
  DETAIL: (name: string) => `/categories/${name}`,
  UPDATE: (id: number) => `/categories/${id}`,
  DELETE: (id: number) => `/categories/${id}`,
  REORDER: '/categories/reorder',
  HOME: '/home/categories',
} as const;

// ─── Media 媒体 ─────────────────────────────────
export const MEDIA = {
  LIST: '/media/files',
  UPLOAD: '/media/upload',
  UPLOAD_FULL: '/api/v2/media/upload', // XHR 直连用完整路径
  DETAIL: (id: number) => `/media/detail/${id}`,
  DELETE: (id: number) => `/media/?file-id-list=${id}`,
  BATCH_DELETE: '/media/batch-delete',
  TAGS: (id: number) => `/media/${id}/tags`,
  FOLDERS_LIST: '/media/folders/list',
  FOLDERS_MOVE: '/media/folders/move-media',
  CHUNK_INIT: '/media/upload/chunked/init',
  CHUNK_UPLOAD: '/media/upload/chunked/chunk',
  CHUNK_COMPLETE: '/media/upload/chunked/complete',
  CHUNK_CANCEL: '/media/upload/chunked/cancel',
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
  MEDIA_MGMT_FILES: '/api/v2/dashboard/media-management/files',
  MEDIA_MGMT_UPLOAD_TASKS: '/api/v2/dashboard/media-management/upload-tasks',
} as const;

// ─── Users 用户 ─────────────────────────────────
export const USERS = {
  LIST: '/users/',
  DETAIL: (id: number) => `/users/${id}`,
  UPDATE: (id: number) => `/users/${id}`,
  RECOMMENDATIONS: '/users/recommendations',
  ME_FOLLOWERS: '/users/me/followers',
  ME_FOLLOWING: '/users/me/following',
  FOLLOW: (id: number) => `/users/${id}/follow`,
  UNFOLLOW: (id: number) => `/users/${id}/follow`,
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
  HISTORY: '/search/history',
  SUGGESTIONS: '/search/suggestions',
  STATS: '/search/stats',
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
} as const;

// ─── MCP / AI 聊天 ────────────────────────────
export const MCP_CHAT = {
  CHAT: '/api/v2/mcp/chat',
  STREAM: '/api/v2/mcp/chat/stream',
  TOOLS: '/api/v2/mcp/tools',
  INFO: '/api/v2/mcp/info',
} as const;
