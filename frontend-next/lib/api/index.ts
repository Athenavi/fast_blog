// API入口文件 - 导出所有API相关的类型和服务

// 导入基础类型
import type {Article, Category, MediaFile, Pagination} from './base-types';

// Services
export {ArticleService, type ArticleStats} from './article-service';
export {CategoryService} from './category-service';
export {DashboardService} from './dashboard-service';
export {AdminSettingsService} from './admin-settings-service';
export {RoleManagementService, type Permission, type Role} from './role-management-service';
export {UserManagementService, type UserWithRoles} from './user-management-service';
export {ArticleManagementService} from './article-management-service';
export {BackupService} from './backup-service';
export {HomeService, DEFAULT_HOME_CONFIG, DEFAULT_HOME_DATA} from './home-service';
export {
    type VIPFeature,
    type VIPSubscription,
    type PremiumArticle, type CreatePaymentRequest, PaymentService, type VIPPlan, VIPService
} from './vip-services';
export {MediaService, type MediaResponse} from './media-service';

// Export UserProfileResponse type
export type { UserProfileResponse } from './base-types';
// Client
export {apiClient} from './base-client';

export interface Activity {
    id: number;
    user_name: string;
    activity_type: string;
    target_type: string;
    target_id: number;
    details: string;
    created_at: string;
    icon: string;
}

// Types
export type {
    Article,
    Category,
    MediaFile,
    Pagination,
    Stats,
    UserRole,
    // ApiResponse,  // 移除重复导出
} from './base-types';

// Utils
export {normalizeApiResponse} from './utils';