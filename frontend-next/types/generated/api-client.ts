/**
 * API 客户端
 * 由 routes.yaml 自动生成 - 请勿手动修改
 * 生成时间：2026-04-26 19:54:29
 */

import {ApiResponse} from './api-types';

// API 基础配置
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:9421';
const API_PREFIX = '/api/{api_version}';

/**
 * 获取存储的 token
 */
function getToken(): string | null {
    if (typeof window === 'undefined') return null;
    return localStorage.getItem('access_token');
}

/**
 * 通用请求函数
 */
async function request<T>(
    endpoint: string,
    method: string,
    data?: any,
    params?: URLSearchParams
): Promise<ApiResponse<T>> {
    const url = new URL(`${API_BASE_URL}${API_PREFIX}${endpoint}`);

    if (params) {
        url.search = params.toString();
    }

    const options: RequestInit = {
        method,
        headers: {
            'Content-Type': 'application/json',
        },
    };

    // 添加认证 token
    const token = getToken();
    if (token) {
        (options.headers as Record<string, string>)['Authorization'] = `Bearer ${token}`;
    }

    // 处理请求体
    if (data) {
        if (method === 'GET' || method === 'HEAD') {
            // GET 请求将数据作为查询参数
            Object.keys(data).forEach(key => {
                if (data[key] !== undefined && data[key] !== null) {
                    url.searchParams.append(key, String(data[key]));
                }
            });
        } else {
            // POST/PUT/PATCH 请求将数据作为 JSON body
            options.body = JSON.stringify(data);
        }
    }

    try {
        const response = await fetch(url.toString(), options);

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const result = await response.json();
        return result as ApiResponse<T>;
    } catch (error) {
        console.error('API request failed:', error);
        return {
            success: false,
            error: error instanceof Error ? error.message : 'Unknown error',
        };
    }
}

/**
 * 表单提交请求函数 (使用 FormData)
 */
async function submitForm<T>(
    endpoint: string,
    method: string,
    formData: Record<string, any>
): Promise<ApiResponse<T>> {
    const url = `${API_BASE_URL}${API_PREFIX}${endpoint}`;

    const options: RequestInit = {
        method,
        body: new URLSearchParams(formData).toString(),
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
        },
    };

    // 添加认证 token
    const token = getToken();
    if (token) {
        (options.headers as Record<string, string>)['Authorization'] = `Bearer ${token}`;
    }

    try {
        const response = await fetch(url, options);

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const result = await response.json();
        return result as ApiResponse<T>;
    } catch (error) {
        console.error('API request failed:', error);
        return {
            success: false,
            error: error instanceof Error ? error.message : 'Unknown error',
        };
    }
}

// ==================== API 调用函数 ====================

// ==========  模块 ==========

/**
 * 获取用户列表
 * 
 */
export async function get_users_list_api(
                    params: {
                        page?: number;
                        per_page?: number;
                        search?: string;
                    },
): Promise<ApiResponse<any>> {
    return request(
        "/",
        "GET",
        params
)

}

// ========== Admin 模块 ==========

/**
 * 
 * 
 */
export async function get_settings(
): Promise<ApiResponse<any>> {
    return request(
        "/admin-settings/",
        "GET",
    undefined
)

}

/**
 * 
 * 
 */
export async function update_settings(
): Promise<ApiResponse<any>> {
    return request(
        "/admin-settings/",
        "POST",
    undefined
)

}

/**
 * 
 * 
 */
export async function create_menu(
): Promise<ApiResponse<any>> {
    return request(
        "/admin-settings/menus",
        "POST",
    undefined
)

}

/**
 * 
 * 
 */
export async function update_menu(
                    params: {
                        menu_id: number;
                    },
): Promise<ApiResponse<any>> {
    return request(
        "/admin-settings/menus/{menu_id}",
        "PUT",
        params
)

}

/**
 * 
 * 
 */
export async function delete_menu(
                    params: {
                        menu_id: number;
                    },
): Promise<ApiResponse<any>> {
    return request(
        "/admin-settings/menus/{menu_id}",
        "DELETE",
        params
)

}

/**
 * 
 * 
 */
export async function create_page(
): Promise<ApiResponse<any>> {
    return request(
        "/admin-settings/pages",
        "POST",
    undefined
)

}

/**
 * 
 * 
 */
export async function update_page(
                    params: {
                        page_id: number;
                    },
): Promise<ApiResponse<any>> {
    return request(
        "/admin-settings/pages/{page_id}",
        "PUT",
        params
)

}

/**
 * 
 * 
 */
export async function delete_page(
                    params: {
                        page_id: number;
                    },
): Promise<ApiResponse<any>> {
    return request(
        "/admin-settings/pages/{page_id}",
        "DELETE",
        params
)

}

/**
 * 
 * 
 */
export async function create_menu_item(
): Promise<ApiResponse<any>> {
    return request(
        "/admin-settings/menu-items",
        "POST",
    undefined
)

}

/**
 * 
 * 
 */
export async function update_menu_item(
                    params: {
                        menu_item_id: number;
                    },
): Promise<ApiResponse<any>> {
    return request(
        "/admin-settings/menu-items/{menu_item_id}",
        "PUT",
        params
)

}

/**
 * 
 * 
 */
export async function delete_menu_item(
                    params: {
                        menu_item_id: number;
                    },
): Promise<ApiResponse<any>> {
    return request(
        "/admin-settings/menu-items/{menu_item_id}",
        "DELETE",
        params
)

}

/**
 * 
 * 
 */
export async function admin_dashboard(
): Promise<ApiResponse<any>> {
    return request(
        "/admin/dashboard",
        "GET",
    undefined
)

}

/**
 * 
 * 
 */
export async function list_backups(
): Promise<ApiResponse<any>> {
    return request(
        "/backup/list",
        "GET",
    undefined
)

}

/**
 * 
 * 
 */
export async function create_backup(
): Promise<ApiResponse<any>> {
    return request(
        "/backup/create",
        "POST",
    undefined
)

}

/**
 * 
 * 
 */
export async function delete_backup(
): Promise<ApiResponse<any>> {
    return request(
        "/backup/delete",
        "POST",
    undefined
)

}

/**
 * 
 * 
 */
export async function download_backup(
                    params: {
                        filename: string;
                    },
): Promise<ApiResponse<any>> {
    return request(
        "/backup/download/{filename}",
        "GET",
        params
)

}

/**
 * 
 * 
 */
export async function admin_roles_search(
                    params: {
                        page?: number;
                        per_page?: number;
                        search?: string;
                    },
): Promise<ApiResponse<any>> {
    return request(
        "/admin/role/search",
        "GET",
        params
)

}

/**
 * 
 * 
 */
export async function create_role(
): Promise<ApiResponse<any>> {
    return request(
        "/admin/role",
        "POST",
    undefined
)

}

/**
 * 
 * 
 */
export async function admin_role_detail(
                    params: {
                        role_id: number;
                    },
): Promise<ApiResponse<any>> {
    return request(
        "/admin/role/{role_id}",
        "GET",
        params
)

}

/**
 * 
 * 
 */
export async function update_role(
                    params: {
                        role_id: number;
                    },
): Promise<ApiResponse<any>> {
    return request(
        "/admin/role/{role_id}",
        "PUT",
        params
)

}

/**
 * 
 * 
 */
export async function delete_role(
                    params: {
                        role_id: number;
                    },
): Promise<ApiResponse<any>> {
    return request(
        "/admin/role/{role_id}",
        "DELETE",
        params
)

}

/**
 * 
 * 
 */
export async function get_permissions(
                    params: {
                        page?: number;
                        per_page?: number;
                        search?: string;
                    },
): Promise<ApiResponse<any>> {
    return request(
        "/admin/permission",
        "GET",
        params
)

}

/**
 * 
 * 
 */
export async function create_permission(
): Promise<ApiResponse<any>> {
    return request(
        "/admin/permission",
        "POST",
    undefined
)

}

/**
 * 
 * 
 */
export async function update_permission(
                    params: {
                        permission_id: number;
                    },
): Promise<ApiResponse<any>> {
    return request(
        "/admin/permission/{permission_id}",
        "PUT",
        params
)

}

/**
 * 
 * 
 */
export async function delete_permission(
                    params: {
                        permission_id: number;
                    },
): Promise<ApiResponse<any>> {
    return request(
        "/admin/permission/{permission_id}",
        "DELETE",
        params
)

}

/**
 * 
 * 
 */
export async function get_user_roles(
                    params: {
                        user_id: number;
                    },
): Promise<ApiResponse<any>> {
    return request(
        "/admin/user/{user_id}/roles",
        "GET",
        params
)

}

/**
 * 
 * 
 */
export async function update_user_roles(
                    params: {
                        user_id: number;
                    },
): Promise<ApiResponse<any>> {
    return request(
        "/admin/user/{user_id}/roles",
        "PUT",
        params
)

}

/**
 * 
 * 
 */
export async function get_admin_role_permission_stats(
): Promise<ApiResponse<any>> {
    return request(
        "/admin/role-permission/stats",
        "GET",
    undefined
)

}

/**
 * 
 * 
 */
export async function get_system_settings(
): Promise<ApiResponse<any>> {
    return request(
        "/system-settings",
        "GET",
    undefined
)

}

/**
 * 
 * 
 */
export async function update_system_settings(
): Promise<ApiResponse<any>> {
    return request(
        "/system-settings",
        "POST",
    undefined
)

}

// ========== Article 模块 ==========

/**
 * 
 * 
 */
export async function update_article_status(
                    params: {
                        article_id: number;
                        current_user_obj?: string;
                    },
): Promise<ApiResponse<any>> {
    return request(
        "/article/{article_id}/status",
        "POST",
        params
)

}

/**
 * 
 * 
 */
export async function get_password_form(
    aid: number,
): Promise<ApiResponse<any>> {
    return request(
        "/article/password-form/{aid}",
        "GET",
    undefined
)

}

/**
 * 
 * 
 */
export async function api_update_article_password(
    aid: number,
): Promise<ApiResponse<any>> {
    return request(
        "/article/password/{aid}",
        "POST",
    undefined
)

}

/**
 * 
 * 
 */
export async function like_article(
                    params: {
                        article_id: number;
                        current_user_obj?: string;
                    },
): Promise<ApiResponse<any>> {
    return request(
        "/article/{article_id}/like",
        "POST",
        params
)

}

/**
 * 
 * 
 */
export async function record_article_view(
                    params: {
                        article_id: number;
                    },
): Promise<ApiResponse<any>> {
    return request(
        "/article/{article_id}/view",
        "POST",
        params
)

}

// ========== Article_revisions 模块 ==========

/**
 * 创建文章修订版本
 * 手动保存文章的修订版本
 */
export async function create_article_revision(
    article_id: number,
                    params: {
                        change_summary?: string;
                    },
): Promise<ApiResponse<any>> {
    return request(
        "/articles/{article_id}/revisions",
        "POST",
        params
)

}

/**
 * 获取文章修订历史列表
 * 获取指定文章的修订历史，支持分页
 */
export async function list_article_revisions(
    article_id: number,
                    params: {
                        page?: number;
                        per_page?: number;
                    },
): Promise<ApiResponse<any>> {
    return request(
        "/articles/{article_id}/revisions",
        "GET",
        params
)

}

/**
 * 获取修订版本详情
 * 获取特定修订版本的详细信息
 */
export async function get_revision(
    revision_id: number,
): Promise<ApiResponse<any>> {
    return request(
        "/articles/revisions/{revision_id}",
        "GET",
    undefined
)

}

/**
 * 回滚到指定修订版本
 * 将文章恢复到指定的历史版本
 */
export async function rollback_article(
    article_id: number,
    revision_id: number,
): Promise<ApiResponse<any>> {
    return request(
        "/articles/{article_id}/revisions/{revision_id}/rollback",
        "POST",
    undefined
)

}

/**
 * 比较两个修订版本
 * 对比两个修订版本的差异
 */
export async function compare_article_revisions(
                    params: {
                        revision1_id: number;
                        revision2_id: number;
                    },
): Promise<ApiResponse<any>> {
    return request(
        "/articles/revisions/compare",
        "GET",
        params
)

}

// ========== Articles 模块 ==========

/**
 * 获取文章列表
 * 
 */
export async function get_articles_api(
                    params: {
                        page?: number;
                        per_page?: number;
                        search?: string;
                        category_id?: number;
                        user_id?: number;
                        status?: string;
                    },
): Promise<ApiResponse<any>> {
    return request(
        "/articles",
        "GET",
        params
)

}

/**
 * 获取文章详情
 * 
 */
export async function get_article_detail_api(
                    params: {
                        article_id: number;
                    },
): Promise<ApiResponse<any>> {
    return request(
        "/articles/{article_id}",
        "GET",
        params
)

}

/**
 * 获取文章原始内容
 * 
 */
export async function get_article_raw_content_api(
                    params: {
                        article_id: number;
                    },
): Promise<ApiResponse<any>> {
    return request(
        "/articles/{article_id}/raw",
        "GET",
        params
)

}

/**
 * 创建文章
 * 
 */
export async function create_article_api(
): Promise<ApiResponse<any>> {
    return request(
        "/articles",
        "POST",
    undefined
)

}

/**
 * 更新文章
 * 
 */
export async function update_article_api(
                    params: {
                        article_id: number;
                    },
): Promise<ApiResponse<any>> {
    return request(
        "/articles/{article_id}",
        "PUT",
        params
)

}

/**
 * 删除文章
 * 
 */
export async function delete_article_api(
                    params: {
                        article_id: number;
                    },
): Promise<ApiResponse<any>> {
    return request(
        "/articles/{article_id}",
        "DELETE",
        params
)

}

/**
 * 获取用户文章列表
 * 
 */
export async function get_user_articles_api(
                    params: {
                        user_id: number;
                        page?: number;
                        per_page?: number;
                    },
): Promise<ApiResponse<any>> {
    return request(
        "/articles/user/{user_id}",
        "GET",
        params
)

}

/**
 * 获取用户统计信息
 * 
 */
export async function get_user_articles_stats_api(
                    params: {
                        user_id: number;
                    },
): Promise<ApiResponse<any>> {
    return request(
        "/articles/user/{user_id}/stats",
        "GET",
        params
)

}

/**
 * 
 * 
 */
export async function get_article_by_slug_api(
                    params: {
                        slug: string;
                    },
): Promise<ApiResponse<any>> {
    return request(
        "/blog/p/{slug}",
        "GET",
        params
)

}

/**
 * 
 * 
 */
export async function get_article_by_id_api(
                    params: {
                        article_id: number;
                    },
): Promise<ApiResponse<any>> {
    return request(
        "/blog/{article_id}.html",
        "GET",
        params
)

}

/**
 * 
 * 
 */
export async function get_articles_by_tag_api(
                    params: {
                        tag_name: string;
                    },
): Promise<ApiResponse<any>> {
    return request(
        "/blog/tag/{tag_name}",
        "GET",
        params
)

}

/**
 * 
 * 
 */
export async function get_featured_articles_api(
): Promise<ApiResponse<any>> {
    return request(
        "/blog/featured",
        "GET",
    undefined
)

}

/**
 * 
 * 
 */
export async function get_contribute_info_api(
                    params: {
                        article_id: number;
                    },
): Promise<ApiResponse<any>> {
    return request(
        "/blog/contribute/{article_id}",
        "GET",
        params
)

}

/**
 * 
 * 
 */
export async function submit_contribution_api(
                    params: {
                        article_id: number;
                    },
): Promise<ApiResponse<any>> {
    return request(
        "/blog/contribute/{article_id}",
        "POST",
        params
)

}

/**
 * 
 * 
 */
export async function get_edit_article_api(
                    params: {
                        article_id: number;
                    },
): Promise<ApiResponse<any>> {
    return request(
        "/blog/edit/{article_id}",
        "GET",
        params
)

}

/**
 * 
 * 
 */
export async function get_new_article_form_api(
): Promise<ApiResponse<any>> {
    return request(
        "/blog/new",
        "GET",
    undefined
)

}

/**
 * 
 * 
 */
export async function update_article_via_blog_api(
                    params: {
                        article_id: number;
                    },
): Promise<ApiResponse<any>> {
    return request(
        "/blog/edit/{article_id}",
        "POST",
        params
)

}

/**
 * 
 * 
 */
export async function create_article_via_blog_api(
): Promise<ApiResponse<any>> {
    return request(
        "/blog/new",
        "POST",
    undefined
)

}

/**
 * 
 * 
 */
export async function api_blog_i18n_content(
    aid: number,
                    params: {
                        iso: string;
                    },
): Promise<ApiResponse<any>> {
    return request(
        "/blog/{aid}/i18n/{iso}",
        "GET",
        params
)

}

// ========== Auth 模块 ==========

/**
 * 
 * 
 */
export async function update_avatar_api(
                    params: {
                        file: string;
                    },
): Promise<ApiResponse<any>> {
    return request(
        "/user-settings/profile/avatar",
        "PUT",
        params
)

}

/**
 * 
 * 
 */
export async function update_user_setting_profiles(
): Promise<ApiResponse<any>> {
    return request(
        "/user-settings/profiles",
        "PUT",
    undefined
)

}

/**
 * 用户登录
 * 
 */
export async function login_api(
                    params: {
                        username: string;
                        password: string;
                        remember_me?: boolean;
                    },
): Promise<ApiResponse<any>> {
    return submitForm(
        "/auth/login",
        "POST",
        params || {}
    );
}

/**
 * 用户注册
 * 
 */
export async function register_api(
                    params: {
                        username: string;
                        email: string;
                        password: string;
                    },
): Promise<ApiResponse<any>> {
    return request(
        "/auth/register",
        "POST",
        params
)

}

/**
 * 用户登出
 * 
 */
export async function logout_api(
): Promise<ApiResponse<any>> {
    return request(
        "/auth/logout",
        "POST",
    undefined
)

}

/**
 * 
 * 
 */
export async function get_user_management_users(
                    params: {
                        page?: number;
                        per_page?: number;
                        role?: string;
                        search?: string;
                    },
): Promise<ApiResponse<any>> {
    return request(
        "/user-management/users",
        "GET",
        params
)

}

// ========== Backup_management 模块 ==========

/**
 * 恢复备份
 * 从备份文件恢复数据
 */
export async function restore_backup(
): Promise<ApiResponse<any>> {
    return request(
        "/backup/restore",
        "POST",
    undefined
)

}

/**
 * 删除备份
 * 删除指定的备份文件
 */
export async function delete_backup_file(
    backup_filename: string,
): Promise<ApiResponse<any>> {
    return request(
        "/backup/{backup_filename}",
        "DELETE",
    undefined
)

}

/**
 * 获取数据库统计
 * 获取数据库各项数据统计
 */
export async function get_db_stats(
): Promise<ApiResponse<any>> {
    return request(
        "/backup/stats",
        "GET",
    undefined
)

}

/**
 * 导出数据
 * 导出数据为JSON格式
 */
export async function export_data(
): Promise<ApiResponse<any>> {
    return request(
        "/backup/export",
        "POST",
    undefined
)

}

// ========== Blog-Management 模块 ==========

/**
 * 
 * 
 */
export async function get_blog_management_articles(
                    params: {
                        page?: number;
                        per_page?: number;
                        status?: string;
                        search?: string;
                        category_id?: number;
                    },
): Promise<ApiResponse<any>> {
    return request(
        "/blog-management/articles",
        "GET",
        params
)

}

/**
 * 
 * 
 */
export async function get_blog_management_articles_stats(
): Promise<ApiResponse<any>> {
    return request(
        "/blog-management/articles/stats",
        "GET",
    undefined
)

}

/**
 * 
 * 
 */
export async function delete_blog_management_article(
                    params: {
                        article_id: number;
                    },
): Promise<ApiResponse<any>> {
    return request(
        "/blog-management/articles/{article_id}",
        "DELETE",
        params
)

}

// ========== Categories 模块 ==========

/**
 * 
 * 
 */
export async function get_all_categories_api(
                    params: {
                        page?: number;
                    },
): Promise<ApiResponse<any>> {
    return request(
        "/category/all",
        "GET",
        params
)

}

/**
 * 
 * 
 */
export async function get_public_categories_api(
                    params: {
                        page?: number;
                    },
): Promise<ApiResponse<any>> {
    return request(
        "/category/public",
        "GET",
        params
)

}

/**
 * 
 * 
 */
export async function get_category_by_name_api(
                    params: {
                        name: string;
                        page?: number;
                    },
): Promise<ApiResponse<any>> {
    return request(
        "/category/{name}",
        "GET",
        params
)

}

/**
 * 
 * 
 */
export async function get_all_categories_root_api(
                    params: {
                        page?: number;
                    },
): Promise<ApiResponse<any>> {
    return request(
        "/category/",
        "GET",
        params
)

}

/**
 * 
 * 
 */
export async function subscribe_category_api(
): Promise<ApiResponse<any>> {
    return request(
        "/category/subscribe",
        "POST",
    undefined
)

}

/**
 * 
 * 
 */
export async function unsubscribe_category_api(
): Promise<ApiResponse<any>> {
    return request(
        "/category/unsubscribe",
        "POST",
    undefined
)

}

/**
 * 
 * 
 */
export async function create_category_api(
): Promise<ApiResponse<any>> {
    return request(
        "/category-management/",
        "POST",
    undefined
)

}

/**
 * 
 * 
 */
export async function update_category_api(
                    params: {
                        category_id: number;
                    },
): Promise<ApiResponse<any>> {
    return request(
        "/category-management/{category_id}",
        "PUT",
        params
)

}

/**
 * 
 * 
 */
export async function get_categories_with_stats_api(
                    params: {
                        page?: number;
                        per_page?: number;
                    },
): Promise<ApiResponse<any>> {
    return request(
        "/category-management/",
        "GET",
        params
)

}

/**
 * 
 * 
 */
export async function delete_category_api(
                    params: {
                        category_id: number;
                    },
): Promise<ApiResponse<any>> {
    return request(
        "/category-management/{category_id}",
        "DELETE",
        params
)

}

// ========== Change-Email 模块 ==========

/**
 * 
 * 
 */
export async function confirm_email_change(
                    params: {
                        token: string;
                        current_user_obj?: string;
                    },
): Promise<ApiResponse<any>> {
    return request(
        "/change-email/confirm/{token}",
        "GET",
        params
)

}

// ========== Check-Email 模块 ==========

/**
 * 
 * 
 */
export async function check_email(
                    params: {
                        email: string;
                    },
): Promise<ApiResponse<any>> {
    return request(
        "/check-email",
        "GET",
        params
)

}

/**
 * 检查邮箱可用性
 * 
 */
export async function api_check_email(
                    params: {
                        email: string;
                    },
): Promise<ApiResponse<any>> {
    return request(
        "/check-email",
        "GET",
        params
)

}

// ========== Check-Username 模块 ==========

/**
 * 
 * 
 */
export async function check_username(
                    params: {
                        username: string;
                    },
): Promise<ApiResponse<any>> {
    return request(
        "/check-username",
        "GET",
        params
)

}

/**
 * 检查用户名可用性
 * 
 */
export async function api_check_username(
                    params: {
                        username: string;
                    },
): Promise<ApiResponse<any>> {
    return request(
        "/check-username",
        "GET",
        params
)

}

// ========== Dashboard 模块 ==========

/**
 * 获取首页文章列表
 * 
 */
export async function get_home_articles_api(
                    params: {
                        page?: number;
                        per_page?: number;
                    },
): Promise<ApiResponse<any>> {
    return request(
        "/home/articles",
        "GET",
        params
)

}

/**
 * 
 * 
 */
export async function get_home_data(
                    params: {
                        limit_featured?: number;
                        limit_popular?: number;
                        limit_recent?: number;
                        limit_categories?: number;
                    },
): Promise<ApiResponse<any>> {
    return request(
        "/home/data",
        "GET",
        params
)

}

/**
 * 
 * 
 */
export async function get_home_config(
): Promise<ApiResponse<any>> {
    return request(
        "/home/config",
        "GET",
    undefined
)

}

/**
 * 
 * 
 */
export async function get_featured_articles(
                    params: {
                        limit?: number;
                    },
): Promise<ApiResponse<any>> {
    return request(
        "/home/featured",
        "GET",
        params
)

}

/**
 * 
 * 
 */
export async function get_recent_articles(
                    params: {
                        page?: number;
                        per_page?: number;
                        category_id?: number;
                    },
): Promise<ApiResponse<any>> {
    return request(
        "/home/recent",
        "GET",
        params
)

}

/**
 * 
 * 
 */
export async function get_popular_articles(
                    params: {
                        limit?: number;
                        days?: number;
                    },
): Promise<ApiResponse<any>> {
    return request(
        "/home/popular",
        "GET",
        params
)

}

/**
 * 
 * 
 */
export async function get_home_categories(
                    params: {
                        limit?: number;
                    },
): Promise<ApiResponse<any>> {
    return request(
        "/home/categories",
        "GET",
        params
)

}

/**
 * 
 * 
 */
export async function get_home_stats(
): Promise<ApiResponse<any>> {
    return request(
        "/home/stats",
        "GET",
    undefined
)

}

/**
 * 
 * 
 */
export async function get_home_menus(
): Promise<ApiResponse<any>> {
    return request(
        "/home/menus",
        "GET",
    undefined
)

}

/**
 * 
 * 
 */
export async function subscribe_email(
                    params: {
                        email: string;
                    },
): Promise<ApiResponse<any>> {
    return request(
        "/home/subscribe",
        "POST",
        params
)

}

/**
 * 
 * 
 */
export async function search_home_articles(
                    params: {
                        q: string;
                        page?: number;
                        per_page?: number;
                    },
): Promise<ApiResponse<any>> {
    return request(
        "/home/search",
        "GET",
        params
)

}

/**
 * 
 * 
 */
export async function get_comment_config(
): Promise<ApiResponse<any>> {
    return request(
        "/dashboard/comment_config",
        "GET",
    undefined
)

}

/**
 * 
 * 
 */
export async function update_comment_config(
): Promise<ApiResponse<any>> {
    return request(
        "/dashboard/comment_config",
        "POST",
    undefined
)

}

/**
 * 
 * 
 */
export async function get_dashboard_stats(
): Promise<ApiResponse<any>> {
    return request(
        "/dashboard/stats",
        "GET",
    undefined
)

}

/**
 * 
 * 
 */
export async function __get_recent_articles(
): Promise<ApiResponse<any>> {
    return request(
        "/dashboard/recent-articles",
        "GET",
    undefined
)

}

/**
 * 
 * 
 */
export async function get_traffic_data(
): Promise<ApiResponse<any>> {
    return request(
        "/dashboard/traffic",
        "GET",
    undefined
)

}

// ========== Email-Exists 模块 ==========

/**
 * 
 * 
 */
export async function email_exists_back(
                    params: {
                        email: string;
                    },
): Promise<ApiResponse<any>> {
    return request(
        "/email-exists",
        "GET",
        params
)

}

// ========== Feed 模块 ==========

/**
 * 获取RSS订阅
 * 获取RSS 2.0格式的Feed订阅
 */
export async function get_rss_feed(
                    params: {
                        limit?: number;
                        category_id?: number;
                    },
): Promise<ApiResponse<any>> {
    return request(
        "/feed/rss",
        "GET",
        params
)

}

/**
 * 获取Atom订阅
 * 获取Atom 1.0格式的Feed订阅
 */
export async function get_atom_feed(
                    params: {
                        limit?: number;
                        category_id?: number;
                    },
): Promise<ApiResponse<any>> {
    return request(
        "/feed/atom",
        "GET",
        params
)

}

/**
 * 获取Feed元数据
 * 获取Feed的统计信息和URL
 */
export async function get_feed_meta(
): Promise<ApiResponse<any>> {
    return request(
        "/feed/metadata",
        "GET",
    undefined
)

}

/**
 * Feed重定向
 * 兼容旧版路径，重定向到RSS
 */
export async function legacy_feed_redirect(
): Promise<ApiResponse<any>> {
    return request(
        "/feed",
        "GET",
    undefined
)

}

// ========== Management 模块 ==========

/**
 * 用户登录（兼容 Django 认证方式）
 * 
 */
export async function login_management_api(
                    params: {
                        username: string;
                        password: string;
                        remember_me?: boolean;
                    },
): Promise<ApiResponse<any>> {
    return submitForm(
        "/management/auth/login",
        "POST",
        params || {}
    );
}

/**
 * 用户注册
 * 
 */
export async function register_management_api(
                    params: {
                        username: string;
                        email: string;
                        password: string;
                    },
): Promise<ApiResponse<any>> {
    return request(
        "/management/auth/register",
        "POST",
        params
)

}

/**
 * 用户登出
 * 
 */
export async function logout_management_api(
): Promise<ApiResponse<any>> {
    return request(
        "/management/auth/logout",
        "POST",
    undefined
)

}

/**
 * 
 * 
 */
export async function get_management_me_profile_api(
): Promise<ApiResponse<any>> {
    return request(
        "/management/me/profile",
        "GET",
    undefined
)

}

/**
 * 
 * 
 */
export async function get_user_profile_api(
                    params: {
                        user_id: number;
                    },
): Promise<ApiResponse<any>> {
    return request(
        "/management/{user_id}/profile",
        "GET",
        params
)

}

/**
 * 
 * 
 */
export async function update_management_me_profile_api(
): Promise<ApiResponse<any>> {
    return request(
        "/management/me/profile",
        "PUT",
    undefined
)

}

/**
 * 
 * 
 */
export async function confirm_password_form_api(
): Promise<ApiResponse<any>> {
    return request(
        "/management/me/security/confirm-password",
        "GET",
    undefined
)

}

/**
 * 
 * 
 */
export async function confirm_password_api(
): Promise<ApiResponse<any>> {
    return request(
        "/management/me/security/confirm-password",
        "POST",
    undefined
)

}

/**
 * 
 * 
 */
export async function change_password_form_api(
): Promise<ApiResponse<any>> {
    return request(
        "/management/me/security/change-password",
        "GET",
    undefined
)

}

/**
 * 
 * 
 */
export async function change_password_api(
): Promise<ApiResponse<any>> {
    return request(
        "/management/me/security/change-password",
        "PUT",
    undefined
)

}

/**
 * 
 * 
 */
export async function update_setting_profiles(
): Promise<ApiResponse<any>> {
    return request(
        "/management/setting/profiles",
        "PUT",
    undefined
)

}

/**
 * 
 * 
 */
export async function get_users(
                    params: {
                        page?: number;
                        per_page?: number;
                        search?: string;
                    },
): Promise<ApiResponse<any>> {
    return request(
        "/management",
        "GET",
        params
)

}

// ========== Me 模块 ==========

/**
 * 获取当前用户信息
 * 
 */
export async function get_current_user_api(
): Promise<ApiResponse<any>> {
    return request(
        "/me",
        "GET",
    undefined
)

}

// ========== Media 模块 ==========

/**
 * 
 * 
 */
export async function get_user_media_api(
                    params: {
                        current_user_obj?: string;
                        media_type?: string;
                        page?: number;
                    },
): Promise<ApiResponse<any>> {
    return request(
        "/media/",
        "GET",
        params
)

}

/**
 * 
 * 
 */
export async function get_media_file_by_id(
                    params: {
                        media_id: number;
                        range_header?: string;
                        current_user_obj?: string;
                    },
): Promise<ApiResponse<any>> {
    return request(
        "/media/{media_id}",
        "GET",
        params
)

}

/**
 * 
 * 
 */
export async function delete_user_media_api(
                    params: {
                        current_user_obj?: string;
                        file_id_list: string;
                    },
): Promise<ApiResponse<any>> {
    return request(
        "/media/",
        "DELETE",
        params
)

}

/**
 * 
 * 
 */
export async function upload_media_file(
                    params: {
                        current_user_obj?: string;
                    },
): Promise<ApiResponse<any>> {
    return request(
        "/media/upload",
        "POST",
        params
)

}

/**
 * 
 * 
 */
export async function chunked_upload_init(
                    params: {
                        current_user_obj?: string;
                    },
): Promise<ApiResponse<any>> {
    return request(
        "/media/upload/chunked/init",
        "POST",
        params
)

}

/**
 * 
 * 
 */
export async function chunked_upload_chunk(
                    params: {
                        current_user_obj?: string;
                    },
): Promise<ApiResponse<any>> {
    return request(
        "/media/upload/chunked/chunk",
        "POST",
        params
)

}

/**
 * 
 * 
 */
export async function chunked_upload_complete(
                    params: {
                        current_user_obj?: string;
                    },
): Promise<ApiResponse<any>> {
    return request(
        "/media/upload/chunked/complete",
        "POST",
        params
)

}

/**
 * 
 * 
 */
export async function chunked_upload_progress(
                    params: {
                        current_user_obj?: string;
                    },
): Promise<ApiResponse<any>> {
    return request(
        "/media/upload/chunked/progress",
        "GET",
        params
)

}

/**
 * 
 * 
 */
export async function chunked_upload_chunks(
                    params: {
                        current_user_obj?: string;
                    },
): Promise<ApiResponse<any>> {
    return request(
        "/media/upload/chunked/chunks",
        "GET",
        params
)

}

/**
 * 
 * 
 */
export async function chunked_upload_cancel(
                    params: {
                        current_user_obj?: string;
                    },
): Promise<ApiResponse<any>> {
    return request(
        "/media/upload/chunked/cancel",
        "POST",
        params
)

}

/**
 * 
 * 
 */
export async function get_media_management_files(
                    params: {
                        page?: number;
                        per_page?: number;
                        file_type?: string;
                    },
): Promise<ApiResponse<any>> {
    return request(
        "/media-management/files",
        "GET",
        params
)

}

// ========== Menu_management 模块 ==========

/**
 * 获取菜单列表
 * 获取所有菜单的列表
 */
export async function list_menus(
): Promise<ApiResponse<any>> {
    return request(
        "/menus",
        "GET",
    undefined
)

}

/**
 * 获取菜单详情
 * 获取菜单及其菜单项树形结构
 */
export async function get_menu_detail(
    menu_id: number,
): Promise<ApiResponse<any>> {
    return request(
        "/menus/{menu_id}",
        "GET",
    undefined
)

}

/**
 * 创建菜单
 * 创建新的菜单
 */
export async function create_new_menu(
): Promise<ApiResponse<any>> {
    return request(
        "/menus",
        "POST",
    undefined
)

}

/**
 * 更新菜单
 * 更新菜单信息
 */
export async function update_existing_menu(
    menu_id: number,
): Promise<ApiResponse<any>> {
    return request(
        "/menus/{menu_id}",
        "PUT",
    undefined
)

}

/**
 * 删除菜单
 * 删除菜单及其所有菜单项
 */
export async function delete_existing_menu(
    menu_id: number,
): Promise<ApiResponse<any>> {
    return request(
        "/menus/{menu_id}",
        "DELETE",
    undefined
)

}

/**
 * 添加菜单项
 * 向菜单添加新的菜单项
 */
export async function add_item_to_menu(
    menu_id: number,
): Promise<ApiResponse<any>> {
    return request(
        "/menus/{menu_id}/items",
        "POST",
    undefined
)

}

/**
 * 更新菜单项
 * 更新菜单项信息
 */
export async function update_menu_item_detail(
    item_id: number,
): Promise<ApiResponse<any>> {
    return request(
        "/menus/items/{item_id}",
        "PUT",
    undefined
)

}

/**
 * 删除菜单项
 * 删除菜单项及其子项
 */
export async function delete_menu_item_detail(
    item_id: number,
): Promise<ApiResponse<any>> {
    return request(
        "/menus/items/{item_id}",
        "DELETE",
    undefined
)

}

/**
 * 重新排序菜单项
 * 批量更新菜单项顺序（用于拖拽）
 */
export async function reorder_menu(
    menu_id: number,
): Promise<ApiResponse<any>> {
    return request(
        "/menus/{menu_id}/reorder",
        "POST",
    undefined
)

}

/**
 * 获取可用页面
 * 获取可添加到菜单的页面列表
 */
export async function get_available_pages(
): Promise<ApiResponse<any>> {
    return request(
        "/menus/available/pages",
        "GET",
    undefined
)

}

/**
 * 获取可用分类
 * 获取可添加到菜单的分类列表
 */
export async function get_available_categories(
): Promise<ApiResponse<any>> {
    return request(
        "/menus/available/categories",
        "GET",
    undefined
)

}

// ========== Misc 模块 ==========

/**
 * 
 * 
 */
export async function list_all_routes(
): Promise<ApiResponse<any>> {
    return request(
        "/routes",
        "GET",
    undefined
)

}

/**
 * 
 * 
 */
export async function get_version_info(
): Promise<ApiResponse<any>> {
    return request(
        "/version/info",
        "GET",
    undefined
)

}

/**
 * 
 * 
 */
export async function get_frontend_version(
): Promise<ApiResponse<any>> {
    return request(
        "/version/frontend",
        "GET",
    undefined
)

}

/**
 * 
 * 
 */
export async function get_backend_version(
): Promise<ApiResponse<any>> {
    return request(
        "/version/backend",
        "GET",
    undefined
)

}

// ========== My 模块 ==========

/**
 * 
 * 
 */
export async function get_my_articles(
                    params: {
                        page?: number;
                        per_page?: number;
                        status?: string;
                    },
): Promise<ApiResponse<any>> {
    return request(
        "/my/articles",
        "GET",
        params
)

}

/**
 * 
 * 
 */
export async function get_my_messages(
): Promise<ApiResponse<any>> {
    return request(
        "/my/messages",
        "GET",
    undefined
)

}

// ========== Notifications 模块 ==========

/**
 * 
 * 
 */
export async function read_notification_api(
                    params: {
                        nid: number;
                    },
): Promise<ApiResponse<any>> {
    return request(
        "/notifications/messages/read",
        "POST",
        params
)

}

/**
 * 
 * 
 */
export async function fetch_message_api(
): Promise<ApiResponse<any>> {
    return request(
        "/notifications/messages",
        "GET",
    undefined
)

}

/**
 * 
 * 
 */
export async function mark_all_as_read_api(
): Promise<ApiResponse<any>> {
    return request(
        "/notifications/messages/read_all",
        "POST",
    undefined
)

}

/**
 * 
 * 
 */
export async function clean_notification_api(
                    params: {
                        nid?: string;
                    },
): Promise<ApiResponse<any>> {
    return request(
        "/notifications/messages/clean",
        "DELETE",
        params
)

}

/**
 * 
 * 
 */
export async function mark_notification_as_read_api(
                    params: {
                        notification_id: number;
                    },
): Promise<ApiResponse<any>> {
    return request(
        "/notifications/{notification_id}/read",
        "PATCH",
        params
)

}

/**
 * 
 * 
 */
export async function delete_notification_api(
                    params: {
                        notification_id: number;
                    },
): Promise<ApiResponse<any>> {
    return request(
        "/notifications/{notification_id}",
        "DELETE",
        params
)

}

/**
 * 
 * 
 */
export async function get_notifications_api(
): Promise<ApiResponse<any>> {
    return request(
        "/notifications/",
        "GET",
    undefined
)

}

/**
 * 
 * 
 */
export async function mark_all_as_read_api_new(
): Promise<ApiResponse<any>> {
    return request(
        "/notifications/read_all",
        "POST",
    undefined
)

}

// ========== Pages 模块 ==========

/**
 * 获取页面列表
 * 获取所有页面的列表，支持分页和状态筛选
 */
export async function list_pages(
                    params: {
                        page?: number;
                        per_page?: number;
                        status?: number;
                    },
): Promise<ApiResponse<any>> {
    return request(
        "/pages",
        "GET",
        params
)

}

/**
 * 获取页面层级结构
 * 获取树形结构的页面层级
 */
export async function get_pages_tree(
): Promise<ApiResponse<any>> {
    return request(
        "/pages/hierarchy",
        "GET",
    undefined
)

}

/**
 * 获取页面详情
 * 根据slug获取页面详细信息
 */
export async function get_page_detail(
    slug: string,
): Promise<ApiResponse<any>> {
    return request(
        "/pages/{slug}",
        "GET",
    undefined
)

}

/**
 * 创建页面
 * 创建新的静态页面
 */
export async function create_new_page(
): Promise<ApiResponse<any>> {
    return request(
        "/pages",
        "POST",
    undefined
)

}

/**
 * 更新页面
 * 更新指定页面的信息
 */
export async function update_existing_page(
    page_id: number,
): Promise<ApiResponse<any>> {
    return request(
        "/pages/{page_id}",
        "PUT",
    undefined
)

}

/**
 * 删除页面
 * 删除指定的页面
 */
export async function delete_existing_page(
    page_id: number,
): Promise<ApiResponse<any>> {
    return request(
        "/pages/{page_id}",
        "DELETE",
    undefined
)

}

// ========== Permission_management 模块 ==========

/**
 * 获取所有权限
 * 获取系统所有可用权限列表
 */
export async function list_all_permissions(
): Promise<ApiResponse<any>> {
    return request(
        "/permissions/list",
        "GET",
    undefined
)

}

/**
 * 获取角色列表
 * 获取所有角色及其权限
 */
export async function list_roles(
): Promise<ApiResponse<any>> {
    return request(
        "/permissions/roles",
        "GET",
    undefined
)

}

/**
 * 分配用户角色
 * 为用户分配指定角色
 */
export async function assign_user_role(
    user_id: number,
): Promise<ApiResponse<any>> {
    return request(
        "/permissions/users/{user_id}/assign-role",
        "POST",
    undefined
)

}

/**
 * 获取用户权限
 * 获取用户的所有权限列表
 */
export async function get_user_permissions(
    user_id: number,
): Promise<ApiResponse<any>> {
    return request(
        "/permissions/users/{user_id}/permissions",
        "GET",
    undefined
)

}

/**
 * 检查权限
 * 检查用户是否有指定权限
 */
export async function check_permission(
): Promise<ApiResponse<any>> {
    return request(
        "/permissions/check",
        "POST",
    undefined
)

}

// ========== Phone 模块 ==========

/**
 * 手机扫码登录
 * 
 */
export async function api_phone_scan(
): Promise<ApiResponse<any>> {
    return request(
        "/phone/scan",
        "GET",
    undefined
)

}

// ========== Plugin_management 模块 ==========

/**
 * 获取插件列表
 * 获取所有已安装和可用的插件
 */
export async function list_plugins(
): Promise<ApiResponse<any>> {
    return request(
        "/plugins",
        "GET",
    undefined
)

}

/**
 * 安装插件
 * 安装新的插件
 */
export async function install_plugin(
): Promise<ApiResponse<any>> {
    return request(
        "/plugins/install",
        "POST",
    undefined
)

}

/**
 * 激活插件
 * 激活指定的插件
 */
export async function activate_plugin(
    plugin_id: number,
): Promise<ApiResponse<any>> {
    return request(
        "/plugins/{plugin_id}/activate",
        "POST",
    undefined
)

}

/**
 * 停用插件
 * 停用指定的插件
 */
export async function deactivate_plugin(
    plugin_id: number,
): Promise<ApiResponse<any>> {
    return request(
        "/plugins/{plugin_id}/deactivate",
        "POST",
    undefined
)

}

/**
 * 卸载插件
 * 卸载指定的插件
 */
export async function uninstall_plugin(
    plugin_id: number,
): Promise<ApiResponse<any>> {
    return request(
        "/plugins/{plugin_id}",
        "DELETE",
    undefined
)

}

/**
 * 更新插件设置
 * 更新插件的配置设置
 */
export async function update_plugin_settings(
    plugin_id: number,
): Promise<ApiResponse<any>> {
    return request(
        "/plugins/{plugin_id}/settings",
        "PUT",
    undefined
)

}

/**
 * 获取钩子列表
 * 获取所有已注册的钩子信息
 */
export async function list_hooks(
): Promise<ApiResponse<any>> {
    return request(
        "/plugins/hooks",
        "GET",
    undefined
)

}

// ========== Profile 模块 ==========

/**
 * 获取用户资料
 * 
 */
export async function get_my_profile_api(
): Promise<ApiResponse<any>> {
    return request(
        "/profile",
        "GET",
    undefined
)

}

/**
 * 更新用户资料
 * 
 */
export async function update_my_profile_api(
): Promise<ApiResponse<any>> {
    return request(
        "/profile",
        "PUT",
    undefined
)

}

// ========== Qr 模块 ==========

/**
 * 生成二维码
 * 
 */
export async function api_generate_qr(
): Promise<ApiResponse<any>> {
    return request(
        "/qr/generate",
        "GET",
    undefined
)

}

/**
 * 检查二维码状态
 * 
 */
export async function api_check_qr_status(
): Promise<ApiResponse<any>> {
    return request(
        "/qr/status",
        "GET",
    undefined
)

}

// ========== Roles 模块 ==========

/**
 * 
 * 
 */
export async function get_role_permission_stats(
): Promise<ApiResponse<any>> {
    return request(
        "/role-management/permission-stats",
        "GET",
    undefined
)

}

/**
 * 
 * 
 */
export async function get_role_management_roles(
): Promise<ApiResponse<any>> {
    return request(
        "/role-management/roles",
        "GET",
    undefined
)

}

/**
 * 
 * 
 */
export async function get_role_management_permissions(
): Promise<ApiResponse<any>> {
    return request(
        "/role-management/permissions",
        "GET",
    undefined
)

}

/**
 * 
 * 
 */
export async function create_role_for_management(
): Promise<ApiResponse<any>> {
    return request(
        "/role-management/roles",
        "POST",
    undefined
)

}

/**
 * 
 * 
 */
export async function update_role_for_management(
                    params: {
                        role_id: number;
                    },
): Promise<ApiResponse<any>> {
    return request(
        "/role-management/roles/{role_id}",
        "PUT",
        params
)

}

/**
 * 
 * 
 */
export async function delete_role_for_management(
                    params: {
                        role_id: number;
                    },
): Promise<ApiResponse<any>> {
    return request(
        "/role-management/roles/{role_id}",
        "DELETE",
        params
)

}

/**
 * 
 * 
 */
export async function create_permission_for_management(
): Promise<ApiResponse<any>> {
    return request(
        "/role-management/permissions",
        "POST",
    undefined
)

}

/**
 * 
 * 
 */
export async function update_permission_for_management(
                    params: {
                        permission_id: number;
                    },
): Promise<ApiResponse<any>> {
    return request(
        "/role-management/permissions/{permission_id}",
        "PUT",
        params
)

}

/**
 * 
 * 
 */
export async function delete_permission_for_management(
                    params: {
                        permission_id: number;
                    },
): Promise<ApiResponse<any>> {
    return request(
        "/role-management/permissions/{permission_id}",
        "DELETE",
        params
)

}

// ========== Scheduled_publish 模块 ==========

/**
 * 触发定时发布检查
 * 手动检查并发布到期的定时文章
 */
export async function trigger_scheduled_publish(
): Promise<ApiResponse<any>> {
    return request(
        "/articles/scheduled/check-and-publish",
        "POST",
    undefined
)

}

/**
 * 获取定时文章列表
 * 获取所有待发布的定时文章
 */
export async function list_scheduled_articles(
                    params: {
                        page?: number;
                        per_page?: number;
                    },
): Promise<ApiResponse<any>> {
    return request(
        "/articles/scheduled/list",
        "GET",
        params
)

}

/**
 * 取消定时发布
 * 取消文章的定时发布设置
 */
export async function cancel_article_schedule(
    article_id: number,
): Promise<ApiResponse<any>> {
    return request(
        "/articles/{article_id}/scheduled/cancel",
        "POST",
    undefined
)

}

// ========== Search 模块 ==========

/**
 * 
 * 
 */
export async function get_search_history(
): Promise<ApiResponse<any>> {
    return request(
        "/search/history",
        "GET",
    undefined
)

}

// ========== Tags 模块 ==========

/**
 * 
 * 
 */
export async function suggest_tags(
                    params: {
                        query?: string;
                    },
): Promise<ApiResponse<any>> {
    return request(
        "/tags/suggest",
        "GET",
        params
)

}

// ========== Theme_management 模块 ==========

/**
 * 获取主题列表
 * 获取所有已安装和可用的主题
 */
export async function list_themes(
): Promise<ApiResponse<any>> {
    return request(
        "/themes",
        "GET",
    undefined
)

}

/**
 * 安装主题
 * 安装新的主题
 */
export async function install_theme(
): Promise<ApiResponse<any>> {
    return request(
        "/themes/install",
        "POST",
    undefined
)

}

/**
 * 激活主题
 * 激活指定的主题
 */
export async function activate_theme(
    theme_id: number,
): Promise<ApiResponse<any>> {
    return request(
        "/themes/{theme_id}/activate",
        "POST",
    undefined
)

}

/**
 * 预览主题
 * 预览指定主题的效枟
 */
export async function preview_theme(
    theme_id: number,
): Promise<ApiResponse<any>> {
    return request(
        "/themes/{theme_id}/preview",
        "GET",
    undefined
)

}

/**
 * 更新主题设置
 * 更新主题的配置设置
 */
export async function update_theme_settings(
    theme_id: number,
): Promise<ApiResponse<any>> {
    return request(
        "/themes/{theme_id}/settings",
        "PUT",
    undefined
)

}

/**
 * 卸载主题
 * 卸载指定的主题
 */
export async function uninstall_theme(
    theme_id: number,
): Promise<ApiResponse<any>> {
    return request(
        "/themes/{theme_id}",
        "DELETE",
    undefined
)

}

/**
 * 获取当前激活主题
 * 获取当前正在使用的主题
 */
export async function get_active_theme(
): Promise<ApiResponse<any>> {
    return request(
        "/themes/active",
        "GET",
    undefined
)

}

// ========== Thumbnail 模块 ==========

/**
 * 
 * 
 */
export async function public_media_thumbnail(
                    params: {
                        data: string;
                    },
): Promise<ApiResponse<any>> {
    return request(
        "/thumbnail",
        "GET",
        params
)

}

// ========== Upload 模块 ==========

/**
 * 
 * 
 */
export async function upload_cover(
                    params: {
                        current_user_obj?: string;
                    },
): Promise<ApiResponse<any>> {
    return request(
        "/upload/cover",
        "POST",
        params
)

}

// ========== User 模块 ==========

/**
 * 
 * 
 */
export async function api_user_avatar(
                    params: {
                        user_id?: number;
                    },
): Promise<ApiResponse<any>> {
    return request(
        "/user/avatar",
        "GET",
        params
)

}

/**
 * 
 * 
 */
export async function api_user_bio(
                    params: {
                        user_id: number;
                    },
): Promise<ApiResponse<any>> {
    return request(
        "/user/bio/{user_id}",
        "GET",
        params
)

}

/**
 * 
 * 
 */
export async function api_user_profile_endpoint(
                    params: {
                        user_id: number;
                    },
): Promise<ApiResponse<any>> {
    return request(
        "/user/profile/{user_id}",
        "GET",
        params
)

}

/**
 * 
 * 
 */
export async function check_login_status(
): Promise<ApiResponse<any>> {
    return request(
        "/user/check-login",
        "GET",
    undefined
)

}

// ========== Username-Exists 模块 ==========

/**
 * 
 * 
 */
export async function username_exists(
                    params: {
                        username: string;
                    },
): Promise<ApiResponse<any>> {
    return request(
        "/username-exists/{username}",
        "GET",
        params
)

}

// ========== Vip-Management 模块 ==========

/**
 * 
 * 
 */
export async function get_vip_management_data(
): Promise<ApiResponse<any>> {
    return request(
        "/vip-management",
        "GET",
    undefined
)

}


// 导出所有 API 函数
export default {
    get_users_list_api,
    get_settings,
    update_settings,
    create_menu,
    update_menu,
    delete_menu,
    create_page,
    update_page,
    delete_page,
    create_menu_item,
    update_menu_item,
    delete_menu_item,
    admin_dashboard,
    list_backups,
    create_backup,
    delete_backup,
    download_backup,
    admin_roles_search,
    create_role,
    admin_role_detail,
    update_role,
    delete_role,
    get_permissions,
    create_permission,
    update_permission,
    delete_permission,
    get_user_roles,
    update_user_roles,
    get_admin_role_permission_stats,
    get_system_settings,
    update_system_settings,
    update_article_status,
    get_password_form,
    api_update_article_password,
    like_article,
    record_article_view,
    create_article_revision,
    list_article_revisions,
    get_revision,
    rollback_article,
    compare_article_revisions,
    get_articles_api,
    get_article_detail_api,
    get_article_raw_content_api,
    create_article_api,
    update_article_api,
    delete_article_api,
    get_user_articles_api,
    get_user_articles_stats_api,
    get_article_by_slug_api,
    get_article_by_id_api,
    get_articles_by_tag_api,
    get_featured_articles_api,
    get_contribute_info_api,
    submit_contribution_api,
    get_edit_article_api,
    get_new_article_form_api,
    update_article_via_blog_api,
    create_article_via_blog_api,
    api_blog_i18n_content,
    update_avatar_api,
    update_user_setting_profiles,
    login_api,
    register_api,
    logout_api,
    get_user_management_users,
    restore_backup,
    delete_backup_file,
    get_db_stats,
    export_data,
    get_blog_management_articles,
    get_blog_management_articles_stats,
    delete_blog_management_article,
    get_all_categories_api,
    get_public_categories_api,
    get_category_by_name_api,
    get_all_categories_root_api,
    subscribe_category_api,
    unsubscribe_category_api,
    create_category_api,
    update_category_api,
    get_categories_with_stats_api,
    delete_category_api,
    confirm_email_change,
    check_email,
    api_check_email,
    check_username,
    api_check_username,
    get_home_articles_api,
    get_home_data,
    get_home_config,
    get_featured_articles,
    get_recent_articles,
    get_popular_articles,
    get_home_categories,
    get_home_stats,
    get_home_menus,
    subscribe_email,
    search_home_articles,
    get_comment_config,
    update_comment_config,
    get_dashboard_stats,
    __get_recent_articles,
    get_traffic_data,
    email_exists_back,
    get_rss_feed,
    get_atom_feed,
    get_feed_meta,
    legacy_feed_redirect,
    login_management_api,
    register_management_api,
    logout_management_api,
    get_management_me_profile_api,
    get_user_profile_api,
    update_management_me_profile_api,
    confirm_password_form_api,
    confirm_password_api,
    change_password_form_api,
    change_password_api,
    update_setting_profiles,
    get_users,
    get_current_user_api,
    get_user_media_api,
    get_media_file_by_id,
    delete_user_media_api,
    upload_media_file,
    chunked_upload_init,
    chunked_upload_chunk,
    chunked_upload_complete,
    chunked_upload_progress,
    chunked_upload_chunks,
    chunked_upload_cancel,
    get_media_management_files,
    list_menus,
    get_menu_detail,
    create_new_menu,
    update_existing_menu,
    delete_existing_menu,
    add_item_to_menu,
    update_menu_item_detail,
    delete_menu_item_detail,
    reorder_menu,
    get_available_pages,
    get_available_categories,
    list_all_routes,
    get_version_info,
    get_frontend_version,
    get_backend_version,
    get_my_articles,
    get_my_messages,
    read_notification_api,
    fetch_message_api,
    mark_all_as_read_api,
    clean_notification_api,
    mark_notification_as_read_api,
    delete_notification_api,
    get_notifications_api,
    mark_all_as_read_api_new,
    list_pages,
    get_pages_tree,
    get_page_detail,
    create_new_page,
    update_existing_page,
    delete_existing_page,
    list_all_permissions,
    list_roles,
    assign_user_role,
    get_user_permissions,
    check_permission,
    api_phone_scan,
    list_plugins,
    install_plugin,
    activate_plugin,
    deactivate_plugin,
    uninstall_plugin,
    update_plugin_settings,
    list_hooks,
    get_my_profile_api,
    update_my_profile_api,
    api_generate_qr,
    api_check_qr_status,
    get_role_permission_stats,
    get_role_management_roles,
    get_role_management_permissions,
    create_role_for_management,
    update_role_for_management,
    delete_role_for_management,
    create_permission_for_management,
    update_permission_for_management,
    delete_permission_for_management,
    trigger_scheduled_publish,
    list_scheduled_articles,
    cancel_article_schedule,
    get_search_history,
    suggest_tags,
    list_themes,
    install_theme,
    activate_theme,
    preview_theme,
    update_theme_settings,
    uninstall_theme,
    get_active_theme,
    public_media_thumbnail,
    upload_cover,
    api_user_avatar,
    api_user_bio,
    api_user_profile_endpoint,
    check_login_status,
    username_exists,
    get_vip_management_data,
};