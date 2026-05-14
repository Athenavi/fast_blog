/**
 * API 类型辅助工具
 * 用于简化 API 响应的类型处理
 */

import type {ApiResponse} from '@/lib/api/base-types';

/**
 * 安全地访问 API 响应数据
 * @param response API 响应
 * @param defaultValue 默认值（当 response.data 为 undefined 时返回）
 * @returns 数据或默认值
 */
export function safeAccessData<T>(response: ApiResponse<T>, defaultValue?: T): T | undefined {
    return response.data ?? defaultValue;
}

/**
 * 检查 API 响应是否成功且有数据
 * @param response API 响应
 * @returns boolean
 */
export function hasSuccessData<T>(response: ApiResponse<T>): response is ApiResponse<T> & { data: T } {
    return response.success && response.data !== undefined;
}

/**
 * 从 API 响应中提取数据，如果失败则抛出错误
 * @param response API 响应
 * @param errorMessage 自定义错误消息
 * @returns 数据
 */
export function extractData<T>(response: ApiResponse<T>, errorMessage?: string): T {
    if (!response.success) {
        throw new Error(errorMessage || response.error || 'API 请求失败');
    }
    if (response.data === undefined) {
        throw new Error(errorMessage || 'API 响应中没有数据');
    }
    return response.data;
}

/**
 * 类型守卫：检查值是否为 ApiResponse 类型
 */
export function isApiResponse<T>(value: unknown): value is ApiResponse<T> {
    return (
        typeof value === 'object' &&
        value !== null &&
        'success' in value &&
        typeof (value as any).success === 'boolean'
    );
}
