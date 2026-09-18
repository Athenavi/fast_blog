/** 全局常量 */

export const APP_TITLE = import.meta.env.VITE_APP_TITLE || 'FastBlog 管理后台'
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v3'

/** 与后端 code 对齐的响应码 */
export const CODE_SUCCESS = 200
export const CODE_UNAUTHORIZED = 401
export const CODE_FORBIDDEN = 403

/** 本地存储键 */
export const STORAGE_TOKEN = 'fastblog.token'
export const STORAGE_REFRESH_TOKEN = 'fastblog.refresh_token'
export const STORAGE_USER = 'fastblog.user'

/** 路由 */
export const LOGIN_PATH = '/login'
export const HOME_PATH = '/dashboard'

/** 无需登录即可访问的路由白名单 */
export const WHITE_LIST = ['/login', '/404', '/403']
