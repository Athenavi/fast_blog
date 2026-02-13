// Main API module export - Re-export all API services
export { apiClient } from '@/lib/api/base-client';

// Types
export type {
  ApiResponse,
  Article,
  Category,
  MediaFile,
  Pagination,
} from '@/lib/api/base-types';

// Services
export {
  ArticleService,
} from '@/lib/api/article-service';

export {
  CategoryService,
} from '@/lib/api/category-service';

export {
  MediaService,
} from '@/lib/api/media-service';

export {
  DashboardService,
  type DashboardStats,
  type RecentArticle,
  type Activity,
  type AnalyticsData,
} from '@/lib/api/dashboard-service';

export {
  ArticleManagementService,
  type ArticleStats,
} from '@/lib/api/article-management-service';

export {
  UserManagementService,
  type UserWithRoles,
  type UserManagementData,
} from '@/lib/api/user-management-service';

export {
  RoleManagementService,
} from '@/lib/api/role-management-service';

export {
  AdminSettingsService,
  type Setting,
  type Menu,
  type MenuItem,
  type Page,
  type AdminSettingsData,
} from '@/lib/api/admin-settings-service';

// Utils
export {
  normalizeApiResponse,
} from '@/lib/api/utils';