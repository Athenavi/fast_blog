/** API 聚合入口：页面统一从这里导入（值 + 类型） */

export * from './types'
export {default as http, clearTokens, setUnauthorizedHandler} from './request'

// ---------------------------------------------------------------- auth
export {authApi} from './modules/auth'
export type {CurrentUser, LoginParams, TokenData} from './modules/auth'

// ---------------------------------------------------------------- system
export {userApi} from './modules/user'
export type {
  RoleBrief,
  UserCreatePayload,
  UserItem,
  UserQuery,
  UserUpdatePayload,
} from './modules/user'

export {roleApi} from './modules/role'
export type {
  RoleCreatePayload,
  RoleItem,
  RoleQuery,
  RoleUpdatePayload,
} from './modules/role'

export {permissionApi} from './modules/permission'
export type {CapabilityGroup, CapabilityItem, PermissionCheckResult} from './modules/permission'

export {menuApi} from './modules/menu'
export type {
  MenuCreatePayload,
  MenuItemCreatePayload,
  MenuItemNode,
  MenuItemUpdatePayload,
  MenuNode,
  MenuTreeOut,
  MenuUpdatePayload,
} from './modules/menu'

export {settingApi} from './modules/setting'
export type {SettingItem, SettingUpsert} from './modules/setting'

export {logApi} from './modules/log'
export type {AuditLogItem, AuditLogQuery} from './modules/log'

export {cacheApi} from './modules/cache'
export type {
  CacheLevelStats,
  CacheStats,
  CacheWarmupItem,
  MultiLevelCacheStats,
} from './modules/cache'

export {monitorApi} from './modules/monitor'
export type {
  CpuInfo,
  DiskInfo,
  MemoryInfo,
  MonitorOverview,
  OnlineSession,
  OnlineStats,
  ProcessInfo,
  ServerInfo,
} from './modules/monitor'

// ---------------------------------------------------------------- content
export {articleApi} from './modules/article'
export type {
  ArticleDetail,
  ArticleItem,
  ArticlePayload,
  ArticleQuery,
} from './modules/article'

export {categoryApi} from './modules/category'
export type {CategoryItem, CategoryPayload} from './modules/category'

export {tagApi} from './modules/tag'
export type {TagItem} from './modules/tag'

export {commentApi} from './modules/comment'
export type {CommentItem, CommentPublicItem, CommentQuery} from './modules/comment'

export {mediaApi} from './modules/media'
export type {MediaFolder, MediaItem, MediaQuery} from './modules/media'

export {pageApi} from './modules/page'
export type {PageDetail, PageItem, PagePayload} from './modules/page'

// ---------------------------------------------------------------- analytics
export {dashboardApi} from './modules/dashboard'
export type {
  DashboardOverview,
  RecentArticle,
  RecentComment,
  TopArticle,
  TrendPoint,
  TrendResult,
} from './modules/dashboard'

export {seoApi, searchAnalyticsApi} from './modules/seo'
export type {ArticleSeoItem, SeoAnalyzePayload, SeoAnalyzeResult, SeoMetrics} from './modules/seo'

// ---------------------------------------------------------------- extension
export {pluginApi} from './modules/plugin'
export type {PluginAction, PluginItem} from './modules/plugin'

export {themeApi} from './modules/theme'
export type {ThemeConfig, ThemeInfo} from './modules/theme'

export {widgetApi} from './modules/widget'
export type {WidgetItem, WidgetPayload} from './modules/widget'

// ---------------------------------------------------------------- ops
export {backupApi} from './modules/backup'
export type {BackupItem, BackupSchedule} from './modules/backup'

export {webhookApi} from './modules/webhook'
export type {WebhookItem, WebhookPayload} from './modules/webhook'

export {notificationApi} from './modules/notification'
export type {NotificationItem} from './modules/notification'

// ---------------------------------------------------------------- mobile（前台用户端）
export {mobileApi} from './modules/mobile'
export type {
  MobileArticleDetail,
  MobileArticleItem,
  MobileArticlePayload,
  MobileArticleQuery,
  MobileLoginPayload,
  MobileMediaFolder,
  MobileMediaItem,
  MobileMediaQuery,
  MobileMediaStats,
  MobileMediaUpdate,
  MobileProfile,
  MobileProfileUpdate,
  MobileTokenData,
  MobileUserStats,
  RegisterPayload,
} from './modules/mobile'
