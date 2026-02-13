// 基础API响应类型定义

// 基础响应类型
export interface ApiResponse<T> {
  pagination?: Pagination;
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
  requires_auth?: boolean;
  new_access_token?: string;
}

// 分页信息类型
export interface Pagination {
  current_page: number;
  pages?: number;
  total_pages?: number;  // 后端返回的字段名
  total: number;
  has_prev: boolean;
  has_next: boolean;
  per_page: number;
}

// 媒体文件类型
export interface MediaFile {
  id: number;
  hash: string;
  original_filename: string;
  mime_type: string;
  file_size: number;
  created_at: string;
  user?: {
    username: string;
  };
}

// 用户角色类型
export interface UserRole {
  id: number;
  name: string;
  permissions: string[];
  description?: string;
}

// 文章类型
export interface Article {
  category_name: string | undefined;
  id: number;
  title: string;
  slug: string;
  excerpt?: string;
  summary?: string;
  cover_image?: string;
  tags?: string[];
  views: number;
  likes: number;
  status: string;
  hidden?: boolean;
  is_vip_only?: boolean;
  required_vip_level?: number;
  article_ad?: string;
  created_at: string;
  updated_at: string;
  user_id: number;
  category_id?: number;
  is_featured?: boolean;
  content?: string;
  author?: {
    id: number;
    username: string;
    email?: string;
  };
  category?: {
    id: number;
    name: string;
    description?: string;
  };
  views_count?: number;
}

// 分类类型
export interface Category {
  id: number;
  name: string;
  description?: string;
  created_at: string;
  updated_at?: string;
  subscription_count?: number;
}

// 角色统计类型
export interface Stats {
  total_roles: number;
  total_permissions: number;
  total_user_roles: number;
  total_role_permissions: number;
}

// 二维码登录相关类型
export interface QrCodeResponse {
  qr_code: string;
  token: string;
  expires_at: string | number;
  status: string;
}

export interface QrLoginSuccessResponse {
  status: 'pending' | 'scanned' | 'confirmed' | 'expired' | 'success' | string;
  access_token?: string;
  refresh_token?: string;
  next_url?: string;
}

// 用户资料相关类型
export interface UserProfile {
  id: number;
  username: string;
  display_name?: string;
  email: string;
  bio?: string;
  location?: string;
  website?: string;
  locale?: string;
  avatar?: string;
  profile_private: boolean;
  created_at: string;
  updated_at?: string;
}

export interface UserArticle {
  id: number;
  title: string;
  slug: string;
  excerpt?: string;
  cover_image?: string;
  views: number;
  likes: number;
  created_at: string;
  tags?: string[];
}

export interface UserStats {
  articles_count: number;
  followers_count: number;
  following_count: number;
}

export interface UserProfileResponse {
  user: UserProfile;
  recent_articles?: UserArticle[];
  stats: UserStats;
  is_following?: boolean;
  has_unread_message?: boolean;
}