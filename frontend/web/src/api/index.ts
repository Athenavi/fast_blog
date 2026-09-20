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

export {sensitiveWordApi} from './modules/sensitiveWord'
export type {
  SensitiveWordItem,
  SensitiveWordPayload,
  SensitiveWordQuery,
} from './modules/sensitiveWord'

// ---------------------------------------------------------------- system 安全与集成（T5-11 批次 3）
export {gdprApi} from './modules/gdpr'
export type {GdprConsentItem, GdprConsentQuery, GdprStats} from './modules/gdpr'

export {integrationApi} from './modules/integration'
export type {
  LdapConfigItem,
  LdapConfigPayload,
  SsoProviderItem,
  SsoProviderPayload,
} from './modules/integration'

export {socialApi} from './modules/social'
export type {SocialAccountItem, SocialAccountQuery} from './modules/social'

export {securityApi} from './modules/security'
export type {
  BlacklistItem,
  LoginAttemptItem,
  LoginAttemptQuery,
  SecurityOverview,
} from './modules/security'

export {siteApi} from './modules/site'
export type {SiteItem, SitePayload, SiteQuery} from './modules/site'

// ---------------------------------------------------------------- 批次 4（ai / chat / cdn）
export {aiApi} from './modules/ai'
export type {
  AiConfigItem,
  AiConfigPayload,
  AiConfigQuery,
  AiWorkflowItem,
  AiWorkflowQuery,
} from './modules/ai'

export {chatApi} from './modules/chat'
export type {
  ChatGroupItem,
  ChatGroupPayload,
  ChatGroupQuery,
  ChatMemberAddPayload,
  ChatMemberItem,
  ChatMemberUpdatePayload,
} from './modules/chat'

export {cdnApi} from './modules/cdn'
export type {CdnConfig, CdnConfigPayload} from './modules/cdn'

// ---------------------------------------------------------------- 批次 5（upgrade / shortcode）
export {upgradeApi} from './modules/upgrade'
export type {
  UpgradeApplyCheck,
  UpgradeApplyResult,
  UpgradeCheckResult,
  UpgradeHistoryItem,
  UpgradeStatus,
} from './modules/upgrade'

export {shortcodeApi} from './modules/shortcode'
export type {ShortcodeItem, ShortcodePayload, ShortcodeQuery} from './modules/shortcode'

// ---------------------------------------------------------------- marketing（T5-11 批次 1）
export {adApi} from './modules/ad'
export type {
  AdItem,
  AdPayload,
  AdPlacementItem,
  AdPlacementPayload,
  AdQuery,
  AdStats,
} from './modules/ad'

export {vipApi} from './modules/vip'
export type {
  VipFeatureItem,
  VipFeaturePayload,
  VipPlanItem,
  VipPlanPayload,
  VipSubscriptionItem,
  VipSubscriptionPayload,
} from './modules/vip'

export {blockPatternApi} from './modules/blockPattern'
export type {BlockPatternItem, BlockPatternPayload} from './modules/blockPattern'

export {customPostTypeApi} from './modules/customPostType'
export type {CustomPostTypeItem, CustomPostTypePayload} from './modules/customPostType'

// ---------------------------------------------------------------- 批次 2
export {approvalApi} from './modules/approval'
export type {
  ApprovalRecordItem,
  ApprovalRecordQuery,
  ApprovalStepItem,
} from './modules/approval'

export {formApi} from './modules/form'
export type {
  FormFieldItem,
  FormFieldPayload,
  FormItem,
  FormPayload,
  FormSubmissionItem,
} from './modules/form'

export {migrationApi} from './modules/migration'
export type {MigrationLogItem, MigrationTaskItem, MigrationTaskPayload} from './modules/migration'

export {emailApi} from './modules/email'
export type {EmailConfigItem, EmailConfigPayload, EmailSubscriptionItem} from './modules/email'

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

// ---------------------------------------------------------------- 批次 6（page-builder / message / enterprise / deployment）
export {pageBuilderApi} from './modules/pageBuilder'
export type {PageBuilderItem, PageBuilderPayload, PageBuilderQuery} from './modules/pageBuilder'

export {messageApi} from './modules/message'
export type {
  MessageContact,
  MessageDirection,
  MessageItem,
  MessageListQuery,
  MessagePayload,
} from './modules/message'

export {enterpriseApi} from './modules/enterprise'
export type {
  DataRetentionPolicyItem,
  DataRetentionPolicyPayload,
  DataRetentionPolicyQuery,
  EnterpriseLicenseItem,
  EnterpriseLicensePayload,
  EnterpriseLicenseQuery,
} from './modules/enterprise'

export {deploymentApi} from './modules/deployment'
export type {
  DeploymentLogItem,
  DeploymentLogQuery,
  DeploymentScriptItem,
  DeploymentScriptPayload,
  DeploymentScriptQuery,
} from './modules/deployment'

// ---------------------------------------------------------------- 批次 7（commerce 域：payment / revenue）
export {paymentApi} from './modules/payment'
export type {
  CryptoPaymentItem,
  CryptoPaymentPayload,
  CryptoPaymentQuery,
  PaymentGatewayItem,
  PaymentGatewayPayload,
  PaymentGatewayQuery,
  PaymentInitiatePayload,
  PaymentTransactionItem,
  PaymentTransactionPayload,
  PaymentTransactionQuery,
  TaxConfigItem,
  TaxConfigPayload,
  TaxConfigQuery,
} from './modules/payment'

export {revenueApi, revenueMineApi} from './modules/revenue'
export type {
  MyPayoutPayload,
  PayoutRequestItem,
  PayoutRequestQuery,
  PlatformRevenueStats,
  RevenueRecordItem,
  RevenueRecordPayload,
  RevenueRecordQuery,
  SharingConfigItem,
  SharingConfigPayload,
  UserRevenueStatsSnapshot,
  UserRevenueSummary,
} from './modules/revenue'

// ---------------------------------------------------------------- 批次 8（analytics 报表）
export {reportApi} from './modules/report'
export type {
  ContentReport,
  CustomMetric,
  CustomReport,
  ReportFormat,
  ReportFrequency,
  ReportHistoryItem,
  ReportHistoryQuery,
  ReportPeriod,
  ReportTemplate,
  ReportType,
  ScheduledReportItem,
  ScheduledReportPayload,
  ScheduledReportQuery,
  TrafficReport,
  UserActivityReport,
} from './modules/report'

// ---------------------------------------------------------------- 批次 9（content 协作域）
export {collaborationApi} from './modules/collaboration'
export type {
  CommentPayload,
  InviteItem,
  InvitePayload,
  InviteTarget,
  MemberItem,
  MemberRole,
  TaskItem,
  TaskPayload,
  TaskPriority,
  TaskStatus,
  TeamCommentItem,
  WorkspaceItem,
  WorkspacePayload,
  WorkspaceRoom,
} from './modules/collaboration'

// ---------------------------------------------------------------- 批次 10（system 监控中心：告警 / 指标 / SLA）
export {monitoringApi} from './modules/monitoring'
export type {
  AlertItem,
  AlertPayload,
  AlertQuery,
  AlertSeverity,
  AlertStats,
  MetricBucket,
  MetricItem,
  MetricPayload,
  MetricQuery,
  MetricSeriesPoint,
  MetricSeriesResult,
  SLAComputePayload,
  SLAItem,
  SLAPayload,
  SLAQuery,
  SLAStats,
} from './modules/monitoring'

// ---------------------------------------------------------------- 批次 11（前台关注）
export {followApi} from './modules/follow'
export type {FollowItem, FollowStats, FollowUserBrief} from './modules/follow'

// ---------------------------------------------------------------- 批次 11（安装自检）
export {installApi} from './modules/install'
export type {
  InstallDatabaseCheck,
  InstallMigrationCheck,
  InstallStatus,
} from './modules/install'

// ---------------------------------------------------------------- 批次 12（积分与勋章）
export {pointsApi} from './modules/points'
export type {
  CheckinResult,
  ExchangeResult,
  ExchangeRule,
  LeaderboardItem,
  PointsAccount,
  PointsLedger,
  PointsRule,
  PointsStats,
  PointsTransaction,
} from './modules/points'

export {badgeApi} from './modules/badges'
export type {
  BadgeCategory,
  BadgeCheckResult,
  BadgeDefinition,
  BadgeProgress,
  BadgeStats,
  UserBadge,
} from './modules/badges'
