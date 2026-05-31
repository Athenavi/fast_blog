# ORM 模型 - 前端页面映射文档

> 最后更新：2026-05-31
> 模型总数：117 个（111 active + 6 planned）
> 前端 Admin 页面：42 个

---

## 目录

1. [映射总览](#映射总览)
2. [按功能域映射](#按功能域映射)
3. [无前端页面的模型](#无前端页面的模型)
4. [前端服务层映射](#前端服务层映射)
5. [维护指南](#维护指南)

---

## 映射总览

| 功能域      | 模型数     | 有前端页面  | 无前端页面  | 覆盖率     |
|----------|---------|--------|--------|---------|
| 内容管理     | 16      | 12     | 4      | 75%     |
| 媒体管理     | 6       | 3      | 3      | 50%     |
| 用户与权限    | 12      | 8      | 4      | 67%     |
| 评论互动     | 3       | 3      | 0      | 100%    |
| VIP / 会员 | 3       | 3      | 0      | 100%    |
| 电商       | 5       | 3      | 2      | 60%     |
| 广告系统     | 4       | 4      | 0      | 100%    |
| 收益分成     | 4       | 4      | 0      | 100%    |
| 群聊       | 3       | 3      | 0      | 100%    |
| 支付系统     | 4       | 4      | 0      | 100%    |
| SEO / 搜索 | 6       | 3      | 3      | 50%     |
| 通知       | 3       | 3      | 0      | 100%    |
| 安全       | 8       | 6      | 2      | 75%     |
| 系统设置     | 7       | 4      | 3      | 57%     |
| 集成 / SSO | 7       | 7      | 0      | 100%    |
| 多站点      | 3       | 3      | 0      | 100%    |
| 企业版      | 7       | 7      | 0      | 100%    |
| 迁移       | 2       | 2      | 0      | 100%    |
| 插件 / 主题  | 4       | 4      | 0      | 100%    |
| 审批流程     | 4       | 2      | 2      | 50%     |
| 其他       | 7       | 0      | 7      | 0%      |
| **合计**   | **117** | **88** | **31** | **75%** |

---

## 按功能域映射

### 1. 内容管理

| ORM 模型                   | 状态       | 前端页面   | 前端路由                  | 组件                                                                                                            |
|--------------------------|----------|--------|-----------------------|---------------------------------------------------------------------------------------------------------------|
| `Article`                | ✅ active | 文章管理   | `/admin/articles`     | [`AdminArticles.tsx`](../frontend-astro/src/components/pages/admin/AdminArticles.tsx)                         |
| `ArticleContent`         | ✅ active | 文章管理   | `/admin/articles`     | `AdminArticles.tsx`（内嵌）                                                                                       |
| `ArticleRevision`        | ✅ active | 文章管理   | `/admin/articles`     | `AdminArticles.tsx`（版本历史）                                                                                     |
| `ArticleRevisionNote`    | ✅ active | 内容扩展   | `/admin/content-ext`  | [`AdminContentManagementExt.tsx`](../frontend-astro/src/components/pages/admin/AdminContentManagementExt.tsx) |
| `ArticleAnnotation`      | ✅ active | 文章管理   | `/admin/articles`     | `AdminArticles.tsx`（注释）                                                                                       |
| `ArticleSEO`             | ✅ active | SEO 管理 | `/admin/seo`          | [`AdminSEOManagement.tsx`](../frontend-astro/src/components/pages/admin/AdminSEOManagement.tsx)               |
| `ArticleLike`            | ✅ active | 文章管理   | `/admin/articles`     | `AdminArticles.tsx`（点赞统计）                                                                                     |
| `Category`               | ✅ active | 分类管理   | `/admin/categories`   | [`AdminCategories.tsx`](../frontend-astro/src/components/pages/admin/AdminCategories.tsx)                     |
| `CategorySubscription`   | ✅ active | 分类管理   | `/admin/categories`   | `AdminCategories.tsx`（订阅）                                                                                     |
| `CustomPostType`         | ✅ active | 内容扩展   | `/admin/content-ext`  | [`AdminContentManagementExt.tsx`](../frontend-astro/src/components/pages/admin/AdminContentManagementExt.tsx) |
| `Menus`                  | ✅ active | 系统设置   | `/admin/settings`     | [`AdminSettings.tsx`](../frontend-astro/src/components/pages/admin/AdminSettings.tsx)（菜单 Tab）                 |
| `MenuItems`              | ✅ active | 系统设置   | `/admin/settings`     | `AdminSettings.tsx`（菜单项）                                                                                      |
| `MenuLocation`           | ✅ active | 内容扩展   | `/admin/content-ext`  | `AdminContentManagementExt.tsx`（菜单位置 Tab）                                                                     |
| `MenuLocationAssignment` | ✅ active | 内容扩展   | `/admin/content-ext`  | `AdminContentManagementExt.tsx`（菜单位置分配）                                                                       |
| `Pages`                  | ✅ active | 系统设置   | `/admin/settings`     | `AdminSettings.tsx`（页面 Tab）                                                                                   |
| `PageBuilder`            | ✅ active | 页面构建器  | `/admin/page-builder` | [`PageBuilder.tsx`](../frontend-astro/src/components/pages/admin/PageBuilder.tsx)                             |

### 2. 媒体管理

| ORM 模型              | 状态       | 前端页面  | 前端路由                  | 组件                                                                                                              |
|---------------------|----------|-------|-----------------------|-----------------------------------------------------------------------------------------------------------------|
| `Media`             | ✅ active | 媒体管理  | `/admin/media`        | [`AdminMedia.tsx`](../frontend-astro/src/components/pages/admin/AdminMedia.tsx)                                 |
| `MediaFolder`       | ✅ active | 媒体管理  | `/admin/media`        | `AdminMedia.tsx`（文件夹 Tab）                                                                                       |
| `MediaOptimization` | ✅ active | 搜索与媒体 | `/admin/search-media` | [`AdminSearchMediaManagement.tsx`](../frontend-astro/src/components/pages/admin/AdminSearchMediaManagement.tsx) |
| `UploadTask`        | ✅ active | 媒体管理  | `/admin/media`        | `AdminMedia.tsx`（上传任务 Tab）                                                                                      |
| `UploadChunk`       | ✅ active | 媒体管理  | `/admin/media`        | `AdminMedia.tsx`（分块上传）                                                                                          |
| `DownloadTask`      | ✅ active | 媒体管理  | `/admin/media`        | `AdminMedia.tsx`（下载任务 Tab）                                                                                      |
| `FileHash`          | ✅ active | 媒体管理  | `/admin/media`        | `AdminMedia.tsx`（文件去重）                                                                                          |

### 3. 用户与权限

| ORM 模型               | 状态       | 前端页面 | 前端路由                   | 组件                                                                                                                |
|----------------------|----------|------|------------------------|-------------------------------------------------------------------------------------------------------------------|
| `User`               | ✅ active | 用户管理 | `/admin/users`         | [`AdminUsers.tsx`](../frontend-astro/src/components/pages/admin/AdminUsers.tsx)                                   |
| `Role`               | ✅ active | 角色管理 | `/admin/roles`         | [`AdminRoles.tsx`](../frontend-astro/src/components/pages/admin/AdminRoles.tsx)                                   |
| `Capability`         | ✅ active | 角色管理 | `/admin/roles`         | `AdminRoles.tsx`（权限列表）                                                                                            |
| `RoleCapability`     | ✅ active | 角色管理 | `/admin/roles`         | `AdminRoles.tsx`（角色-权限映射）                                                                                         |
| `UserRole`           | ✅ active | 用户管理 | `/admin/users`         | `AdminUsers.tsx`（角色分配）                                                                                            |
| `PermissionAuditLog` | ✅ active | 角色管理 | `/admin/roles`         | `AdminRoles.tsx`（权限审计）                                                                                            |
| `UserSession`        | ✅ active | 用户安全 | `/admin/user-security` | [`AdminUserSecurityManagement.tsx`](../frontend-astro/src/components/pages/admin/AdminUserSecurityManagement.tsx) |
| `UserBlock`          | ✅ active | 用户管理 | `/admin/users`         | `AdminUsers.tsx`（黑名单）                                                                                             |
| `UserActivity`       | ✅ active | 仪表盘  | `/admin`               | [`AdminDashboard.tsx`](../frontend-astro/src/components/pages/admin/AdminDashboard.tsx)                           |
| `FieldPermission`    | ✅ active | 用户安全 | `/admin/user-security` | `AdminUserSecurityManagement.tsx`（字段权限 Tab）                                                                       |
| `Workspace`          | ✅ active | 协作管理 | `/admin/collaboration` | [`AdminCollaboration.tsx`](../frontend-astro/src/components/pages/admin/AdminCollaboration.tsx)                   |
| `WorkspaceMember`    | ✅ active | 协作管理 | `/admin/collaboration` | `AdminCollaboration.tsx`（成员管理）                                                                                    |

### 4. 评论互动

| ORM 模型                | 状态       | 前端页面 | 前端路由              | 组件                                                                                    |
|-----------------------|----------|------|-------------------|---------------------------------------------------------------------------------------|
| `Comment`             | ✅ active | 评论管理 | `/admin/comments` | [`AdminComments.tsx`](../frontend-astro/src/components/pages/admin/AdminComments.tsx) |
| `CommentVote`         | ✅ active | 评论管理 | `/admin/comments` | `AdminComments.tsx`（投票统计）                                                             |
| `CommentSubscription` | ✅ active | 评论管理 | `/admin/comments` | `AdminComments.tsx`（订阅管理 Tab）                                                         |

### 5. VIP / 会员

| ORM 模型            | 状态       | 前端页面   | 前端路由         | 组件                                                                                  |
|-------------------|----------|--------|--------------|-------------------------------------------------------------------------------------|
| `VIPPlan`         | ✅ active | VIP 管理 | `/admin/vip` | [`AdminVip.tsx`](../frontend-astro/src/components/pages/admin/AdminVip.tsx)（计划 Tab） |
| `VIPSubscription` | ✅ active | VIP 管理 | `/admin/vip` | `AdminVip.tsx`（会员 Tab）                                                              |
| `VIPFeature`      | ✅ active | VIP 管理 | `/admin/vip` | `AdminVip.tsx`（功能 Tab）                                                              |

### 6. 电商系统

| ORM 模型      | 状态       | 前端页面 | 前端路由               | 组件                                                                                                                  |
|-------------|----------|------|--------------------|---------------------------------------------------------------------------------------------------------------------|
| `Product`   | ✅ active | 电商管理 | `/admin/ecommerce` | [`AdminEcommerceManagement.tsx`](../frontend-astro/src/components/pages/admin/AdminEcommerceManagement.tsx)（商品 Tab） |
| `Order`     | ✅ active | 电商管理 | `/admin/ecommerce` | `AdminEcommerceManagement.tsx`（订单 Tab）                                                                              |
| `OrderItem` | ✅ active | 电商管理 | `/admin/ecommerce` | `AdminEcommerceManagement.tsx`（订单明细）                                                                                |
| `Cart`      | ✅ active | —    | —                  | 仅后端 API                                                                                                             |
| `CartItem`  | ✅ active | —    | —                  | 仅后端 API                                                                                                             |

### 7. 广告系统

| ORM 模型         | 状态       | 前端页面 | 前端路由         | 组件                                                                                   |
|----------------|----------|------|--------------|--------------------------------------------------------------------------------------|
| `AdPlacement`  | ✅ active | 广告管理 | `/admin/ads` | [`AdminAds.tsx`](../frontend-astro/src/components/pages/admin/AdminAds.tsx)（广告位 Tab） |
| `Ad`           | ✅ active | 广告管理 | `/admin/ads` | `AdminAds.tsx`（广告 Tab）                                                               |
| `AdClick`      | ✅ active | 广告管理 | `/admin/ads` | `AdminAds.tsx`（点击统计）                                                                 |
| `AdImpression` | ✅ active | 广告管理 | `/admin/ads` | `AdminAds.tsx`（展示统计）                                                                 |

### 8. 收益分成

| ORM 模型                 | 状态       | 前端页面 | 前端路由             | 组件                                                                                                              |
|------------------------|----------|------|------------------|-----------------------------------------------------------------------------------------------------------------|
| `RevenueRecord`        | ✅ active | 收益管理 | `/admin/revenue` | [`AdminRevenueManagement.tsx`](../frontend-astro/src/components/pages/admin/AdminRevenueManagement.tsx)（记录 Tab） |
| `RevenueSharingConfig` | ✅ active | 收益管理 | `/admin/revenue` | `AdminRevenueManagement.tsx`（配置 Tab）                                                                            |
| `PayoutRequest`        | ✅ active | 收益管理 | `/admin/revenue` | `AdminRevenueManagement.tsx`（提现 Tab）                                                                            |
| `UserRevenueStats`     | ✅ active | 收益管理 | `/admin/revenue` | `AdminRevenueManagement.tsx`（统计 Tab）                                                                            |

### 9. 群聊系统

| ORM 模型            | 状态       | 前端页面 | 前端路由                 | 组件                                                                                                            |
|-------------------|----------|------|----------------------|---------------------------------------------------------------------------------------------------------------|
| `ChatGroup`       | ✅ active | 群聊管理 | `/admin/chat-groups` | [`AdminChatGroupsManagement.tsx`](../frontend-astro/src/components/pages/admin/AdminChatGroupsManagement.tsx) |
| `ChatGroupMember` | ✅ active | 群聊管理 | `/admin/chat-groups` | `AdminChatGroupsManagement.tsx`（成员 Tab）                                                                       |
| `ChatGroupInvite` | ✅ active | 群聊管理 | `/admin/chat-groups` | `AdminChatGroupsManagement.tsx`（邀请 Tab）                                                                       |

### 10. 支付系统

| ORM 模型               | 状态       | 前端页面 | 前端路由             | 组件                                                                                                              |
|----------------------|----------|------|------------------|-----------------------------------------------------------------------------------------------------------------|
| `PaymentGateway`     | ✅ active | 支付管理 | `/admin/payment` | [`AdminPaymentManagement.tsx`](../frontend-astro/src/components/pages/admin/AdminPaymentManagement.tsx)（网关 Tab） |
| `PaymentTransaction` | ✅ active | 支付管理 | `/admin/payment` | `AdminPaymentManagement.tsx`（交易 Tab）                                                                            |
| `CryptoPayment`      | ✅ active | 支付管理 | `/admin/payment` | `AdminPaymentManagement.tsx`（加密支付 Tab）                                                                          |
| `TaxConfig`          | ✅ active | 支付管理 | `/admin/payment` | `AdminPaymentManagement.tsx`（税务配置 Tab）                                                                          |

### 11. SEO / 搜索

| ORM 模型          | 状态       | 前端页面   | 前端路由                       | 组件                                                                                                                      |
|-----------------|----------|--------|----------------------------|-------------------------------------------------------------------------------------------------------------------------|
| `ArticleSEO`    | ✅ active | SEO 管理 | `/admin/seo`               | [`AdminSEOManagement.tsx`](../frontend-astro/src/components/pages/admin/AdminSEOManagement.tsx)                         |
| `ShareStat`     | ✅ active | SEO 管理 | `/admin/seo`               | `AdminSEOManagement.tsx`（分享统计 Tab）                                                                                      |
| `SearchHistory` | ✅ active | SEO 管理 | `/admin/seo`               | `AdminSEOManagement.tsx`（搜索历史 Tab）                                                                                      |
| `SearchIndex`   | ✅ active | 搜索与媒体  | `/admin/search-media`      | [`AdminSearchMediaManagement.tsx`](../frontend-astro/src/components/pages/admin/AdminSearchMediaManagement.tsx)（索引 Tab） |
| `PageView`      | ✅ active | 仪表盘    | `/admin`                   | `AdminDashboard.tsx`（PV 统计）                                                                                             |
| `GlobalStyle`   | ✅ active | 主题市场   | `/admin/theme-marketplace` | [`AdminThemeMarketplace.tsx`](../frontend-astro/src/components/pages/admin/AdminThemeMarketplace.tsx)                   |

### 12. 通知系统

| ORM 模型                    | 状态       | 前端页面 | 前端路由                   | 组件                                                                                              |
|---------------------------|----------|------|------------------------|-------------------------------------------------------------------------------------------------|
| `Notification`            | ✅ active | 通知管理 | `/admin/notifications` | [`AdminNotifications.tsx`](../frontend-astro/src/components/pages/admin/AdminNotifications.tsx) |
| `NotificationIntegration` | ✅ active | 集成管理 | `/admin/integrations`  | [`AdminIntegrations.tsx`](../frontend-astro/src/components/pages/admin/AdminIntegrations.tsx)   |
| `EmailServiceConfig`      | ✅ active | 系统设置 | `/admin/settings`      | `AdminSettings.tsx`（邮件配置）                                                                       |
| `EmailSubscription`       | ✅ active | 用户安全 | `/admin/user-security` | `AdminUserSecurityManagement.tsx`（订阅 Tab）                                                       |

### 13. 安全审计

| ORM 模型            | 状态       | 前端页面       | 前端路由                     | 组件                                                                                                      |
|-------------------|----------|------------|--------------------------|---------------------------------------------------------------------------------------------------------|
| `AuditLog`        | ✅ active | 审计日志       | `/admin/audit-logs`      | [`AdminAuditLogs.tsx`](../frontend-astro/src/components/pages/admin/AdminAuditLogs.tsx)                 |
| `LoginAttempt`    | ✅ active | 安全仪表盘      | `/admin/security`        | [`AdminSecurityDashboard.tsx`](../frontend-astro/src/components/pages/admin/AdminSecurityDashboard.tsx) |
| `TokenBlacklist`  | ✅ active | 安全仪表盘      | `/admin/security`        | `AdminSecurityDashboard.tsx`（Token 管理）                                                                  |
| `SensitiveWord`   | ✅ active | 敏感词管理      | `/admin/sensitive-words` | [`AdminSensitiveWords.tsx`](../frontend-astro/src/components/pages/admin/AdminSensitiveWords.tsx)       |
| `ReportHistory`   | ✅ active | 安全仪表盘      | `/admin/security`        | `AdminSecurityDashboard.tsx`（报告历史）                                                                      |
| `ScheduledReport` | ✅ active | 安全仪表盘      | `/admin/security`        | `AdminSecurityDashboard.tsx`（定时报告）                                                                      |
| `Webhook`         | ✅ active | Webhook 管理 | `/admin/webhooks`        | [`AdminWebhooks.tsx`](../frontend-astro/src/components/pages/admin/AdminWebhooks.tsx)                   |
| `WebhookDelivery` | ✅ active | Webhook 管理 | `/admin/webhooks`        | `AdminWebhooks.tsx`（投递记录）                                                                               |

### 14. 系统配置

| ORM 模型              | 状态       | 前端页面  | 前端路由                       | 组件                                                                                                    |
|---------------------|----------|-------|----------------------------|-------------------------------------------------------------------------------------------------------|
| `SystemSettings`    | ✅ active | 系统设置  | `/admin/settings`          | [`AdminSettings.tsx`](../frontend-astro/src/components/pages/admin/AdminSettings.tsx)                 |
| `GlobalStyleConfig` | ✅ active | 全局样式  | `/admin/theme-marketplace` | [`GlobalStyleManager.tsx`](../frontend-astro/src/components/pages/admin/GlobalStyleManager.tsx)       |
| `BlockPattern`      | ✅ active | 页面构建器 | `/admin/page-builder`      | [`PageBuilder.tsx`](../frontend-astro/src/components/pages/admin/PageBuilder.tsx)                     |
| `Plugin`            | ✅ active | 插件管理  | `/admin/plugins`           | [`AdminPlugins.tsx`](../frontend-astro/src/components/pages/admin/AdminPlugins.tsx)                   |
| `Theme`             | ✅ active | 主题市场  | `/admin/theme-marketplace` | [`AdminThemeMarketplace.tsx`](../frontend-astro/src/components/pages/admin/AdminThemeMarketplace.tsx) |
| `Form`              | ✅ active | —     | —                          | 仅后端 API                                                                                               |
| `FormField`         | ✅ active | —     | —                          | 仅后端 API                                                                                               |
| `FormSubmission`    | ✅ active | —     | —                          | 仅后端 API                                                                                               |
| `WidgetInstance`    | ✅ active | —     | —                          | 仅后端 API                                                                                               |

### 15. 集成 / SSO / 分析

| ORM 模型                  | 状态       | 前端页面 | 前端路由                  | 组件                                                                                                       |
|-------------------------|----------|------|-----------------------|----------------------------------------------------------------------------------------------------------|
| `OAuthAccount`          | ✅ active | 集成管理 | `/admin/integrations` | [`AdminIntegrations.tsx`](../frontend-astro/src/components/pages/admin/AdminIntegrations.tsx)（OAuth Tab） |
| `SSOProvider`           | ✅ active | 集成管理 | `/admin/integrations` | `AdminIntegrations.tsx`（SSO Tab）                                                                         |
| `SAMLConfig`            | ✅ active | 集成管理 | `/admin/integrations` | `AdminIntegrations.tsx`（SAML 配置）                                                                         |
| `LDAPConfig`            | ✅ active | 集成管理 | `/admin/integrations` | `AdminIntegrations.tsx`（LDAP 配置）                                                                         |
| `GoogleAnalyticsConfig` | ✅ active | 分析管理 | `/admin/analytics`    | [`AdminAnalytics.tsx`](../frontend-astro/src/components/pages/admin/AdminAnalytics.tsx)                  |
| `BaiduAnalyticsConfig`  | ✅ active | 分析管理 | `/admin/analytics`    | `AdminAnalytics.tsx`（百度统计）                                                                               |
| `CustomField`           | ✅ active | 集成管理 | `/admin/integrations` | `AdminIntegrations.tsx`（自定义字段）                                                                           |

### 16. 多站点

| ORM 模型           | 状态       | 前端页面  | 前端路由               | 组件                                                                                                                  |
|------------------|----------|-------|--------------------|---------------------------------------------------------------------------------------------------------------------|
| `Site`           | ✅ active | 多站点管理 | `/admin/multisite` | [`AdminMultisiteManagement.tsx`](../frontend-astro/src/components/pages/admin/AdminMultisiteManagement.tsx)（站点 Tab） |
| `SiteUser`       | ✅ active | 多站点管理 | `/admin/multisite` | `AdminMultisiteManagement.tsx`（站点用户）                                                                                |
| `ContentMapping` | ✅ active | 多站点管理 | `/admin/multisite` | `AdminMultisiteManagement.tsx`（内容映射 Tab）                                                                            |

### 17. 企业版管理

| ORM 模型               | 状态       | 前端页面 | 前端路由                | 组件                                                                                                 |
|----------------------|----------|------|---------------------|----------------------------------------------------------------------------------------------------|
| `EnterpriseLicense`  | ✅ active | 企业管理 | `/admin/enterprise` | [`AdminEnterprise.tsx`](../frontend-astro/src/components/pages/admin/AdminEnterprise.tsx)（许可证 Tab） |
| `SupportTicket`      | ✅ active | 企业管理 | `/admin/enterprise` | `AdminEnterprise.tsx`（工单 Tab）                                                                      |
| `SupportTicketReply` | ✅ active | 企业管理 | `/admin/enterprise` | `AdminEnterprise.tsx`（工单回复）                                                                        |
| `DeploymentScript`   | ✅ active | 企业管理 | `/admin/enterprise` | `AdminEnterprise.tsx`（脚本 Tab）                                                                      |
| `DeploymentLog`      | ✅ active | 企业管理 | `/admin/enterprise` | `AdminEnterprise.tsx`（日志 Tab）                                                                      |
| `MonitoringAlert`    | ✅ active | 企业管理 | `/admin/enterprise` | `AdminEnterprise.tsx`（告警 Tab）                                                                      |
| `MonitoringMetric`   | ✅ active | 企业管理 | `/admin/enterprise` | `AdminEnterprise.tsx`（指标 Tab）                                                                      |

### 18. 迁移工具

| ORM 模型          | 状态       | 前端页面 | 前端路由               | 组件                                                                                                                  |
|-----------------|----------|------|--------------------|---------------------------------------------------------------------------------------------------------------------|
| `MigrationTask` | ✅ active | 迁移管理 | `/admin/migration` | [`AdminMigrationManagement.tsx`](../frontend-astro/src/components/pages/admin/AdminMigrationManagement.tsx)（任务 Tab） |
| `MigrationLog`  | ✅ active | 迁移管理 | `/admin/migration` | `AdminMigrationManagement.tsx`（日志 Tab）                                                                              |

### 19. 审批流程

| ORM 模型           | 状态       | 前端页面  | 前端路由              | 组件                                                                                                  |
|------------------|----------|-------|-------------------|-----------------------------------------------------------------------------------------------------|
| `ApprovalRecord` | ✅ active | 内容审批  | `/admin/approval` | [`AdminContentApproval.tsx`](../frontend-astro/src/components/pages/admin/AdminContentApproval.tsx) |
| `ApprovalStep`   | ✅ active | 内容审批  | `/admin/approval` | `AdminContentApproval.tsx`（步骤配置）                                                                    |
| `Task`           | ✅ active | —     | —                 | 仅后端 API（内部任务调度）                                                                                     |
| `AIWorkflow`     | ✅ active | AI 管理 | `/admin/ai`       | [`AdminAI.tsx`](../frontend-astro/src/components/pages/admin/AdminAI.tsx)                           |

---

## 无前端页面的模型

以下模型仅在后端使用，无独立的前端管理页面：

| ORM 模型           | 状态       | 说明        | 使用位置                       |
|------------------|----------|-----------|----------------------------|
| `Cart`           | ✅ active | 用户购物车     | `shared/services/payment/` |
| `CartItem`       | ✅ active | 购物车商品项    | `shared/services/payment/` |
| `Form`           | ✅ active | 表单定义      | `shared/services/`         |
| `FormField`      | ✅ active | 表单字段定义    | `shared/services/`         |
| `FormSubmission` | ✅ active | 表单提交记录    | `shared/services/`         |
| `WidgetInstance` | ✅ active | Widget 实例 | `shared/services/`         |
| `Task`           | ✅ active | 内部任务调度    | `shared/services/`         |
| `PageView`       | ✅ active | 页面访问统计    | 统计聚合数据，通过 Dashboard 间接展示   |
| `UserActivity`   | ✅ active | 用户活动记录    | 统计聚合数据，通过 Dashboard 间接展示   |

---

## 前端服务层映射

前端 API 服务文件与后端 API 的对应关系：

| 前端服务文件                                                                         | 后端 API 模块             | 关联模型                                                                |
|--------------------------------------------------------------------------------|-----------------------|---------------------------------------------------------------------|
| [`base-client.ts`](../frontend-astro/src/lib/api/base-client.ts)               | 全局 HTTP 客户端           | —                                                                   |
| [`comment-service.ts`](../frontend-astro/src/lib/api/comment-service.ts)       | `/api/v1/comments/`   | Comment, CommentVote, CommentSubscription                           |
| [`enterprise-service.ts`](../frontend-astro/src/lib/api/enterprise-service.ts) | `/api/v2/enterprise/` | EnterpriseLicense, SupportTicket, DeploymentScript, MonitoringAlert |

---

## 维护指南

### 添加新模型时的检查清单

1. **在 [`config/models.yaml`](../config/models.yaml) 中添加 `frontend_page` 字段**
    - 有对应 admin 页面：`frontend_page: /admin/xxx`
    - 仅后端使用：`frontend_page: null`

2. **在 [`shared/models/__init__.py`](../shared/models/__init__.py) 中添加导入**

3. **创建前端页面时**
    - 在 `frontend-astro/src/components/pages/admin/` 下创建组件
    - 在 `frontend-astro/src/pages/admin/` 下创建 `.astro` 路由页面
    - 在 [`AdminSidebar.tsx`](../frontend-astro/src/components/admin/AdminSidebar.tsx) 的 `navConfig` 中添加导航项
    - 在 [`zh-CN.json`](../frontend-astro/src/locales/zh-CN.json) 和 [`en.json`](../frontend-astro/src/locales/en.json)
      中添加 i18n 翻译

4. **运行 CI 检查**
   ```bash
   python scripts/model_lifecycle_check.py check
   ```

### CI 自动提醒机制

[`scripts/model_lifecycle_check.py`](../scripts/model_lifecycle_check.py) 支持以下检查：

- **`check` 子命令**：检查所有 active 模型是否在代码中被引用
- **`report` 子命令**：生成详细的模型使用率审计报告
- **`add-status` 子命令**：为缺少 `status` 字段的模型批量添加

新增模型如果没有对应的前端页面（`frontend_page: null`），CI 检查会输出提醒：

```
[WARN] 模型 XXX 没有对应的前端页面（frontend_page: null）
```

---

## 前端 Admin 页面完整列表

| 路由                           | 组件                                | 说明         |
|------------------------------|-----------------------------------|------------|
| `/admin`                     | `AdminDashboard.tsx`              | 仪表盘        |
| `/admin/articles`            | `AdminArticles.tsx`               | 文章管理       |
| `/admin/categories`          | `AdminCategories.tsx`             | 分类管理       |
| `/admin/comments`            | `AdminComments.tsx`               | 评论管理       |
| `/admin/media`               | `AdminMedia.tsx`                  | 媒体管理       |
| `/admin/users`               | `AdminUsers.tsx`                  | 用户管理       |
| `/admin/roles`               | `AdminRoles.tsx`                  | 角色管理       |
| `/admin/settings`            | `AdminSettings.tsx`               | 系统设置       |
| `/admin/seo`                 | `AdminSEOManagement.tsx`          | SEO 管理     |
| `/admin/analytics`           | `AdminAnalytics.tsx`              | 分析管理       |
| `/admin/plugins`             | `AdminPlugins.tsx`                | 插件管理       |
| `/admin/theme-marketplace`   | `AdminThemeMarketplace.tsx`       | 主题市场       |
| `/admin/ai`                  | `AdminAI.tsx`                     | AI 管理      |
| `/admin/ai-workflows`        | `AdminAIWorkflows.tsx`            | AI 工作流     |
| `/admin/notifications`       | `AdminNotifications.tsx`          | 通知管理       |
| `/admin/security`            | `AdminSecurityDashboard.tsx`      | 安全仪表盘      |
| `/admin/sensitive-words`     | `AdminSensitiveWords.tsx`         | 敏感词管理      |
| `/admin/gdpr`                | `AdminGDPR.tsx`                   | GDPR 管理    |
| `/admin/audit-logs`          | `AdminAuditLogs.tsx`              | 审计日志       |
| `/admin/backup`              | `AdminBackup.tsx`                 | 备份管理       |
| `/admin/cdn`                 | `AdminCDN.tsx`                    | CDN 管理     |
| `/admin/system`              | `AdminSystem.tsx`                 | 系统信息       |
| `/admin/webhooks`            | `AdminWebhooks.tsx`               | Webhook 管理 |
| `/admin/templates`           | `AdminTemplates.tsx`              | 模板管理       |
| `/admin/integrations`        | `AdminIntegrations.tsx`           | 集成管理       |
| `/admin/payment`             | `AdminPaymentManagement.tsx`      | 支付管理       |
| `/admin/revenue`             | `AdminRevenueManagement.tsx`      | 收益管理       |
| `/admin/vip`                 | `AdminVip.tsx`                    | VIP 管理     |
| `/admin/ads`                 | `AdminAds.tsx`                    | 广告管理       |
| `/admin/ecommerce`           | `AdminEcommerceManagement.tsx`    | 电商管理       |
| `/admin/multisite`           | `AdminMultisiteManagement.tsx`    | 多站点管理      |
| `/admin/chat-groups`         | `AdminChatGroupsManagement.tsx`   | 群聊管理       |
| `/admin/approval`            | `AdminContentApproval.tsx`        | 内容审批       |
| `/admin/collaboration`       | `AdminCollaboration.tsx`          | 协作管理       |
| `/admin/content-ext`         | `AdminContentManagementExt.tsx`   | 内容扩展       |
| `/admin/migration`           | `AdminMigrationManagement.tsx`    | 迁移管理       |
| `/admin/search-media`        | `AdminSearchMediaManagement.tsx`  | 搜索与媒体      |
| `/admin/user-security`       | `AdminUserSecurityManagement.tsx` | 用户安全       |
| `/admin/accessibility`       | `AdminAccessibility.tsx`          | 无障碍管理      |
| `/admin/enterprise`          | `AdminEnterprise.tsx`             | 企业管理       |
| `/admin/page-builder`        | `PageBuilder.tsx`                 | 页面构建器      |
| `/admin/third-party-publish` | `AdminThirdPartyPublish.tsx`      | 第三方发布      |
| `/admin/editor`              | `ArticleEditor.tsx`               | 文章编辑器      |
