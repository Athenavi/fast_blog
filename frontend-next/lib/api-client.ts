/**
 * API Client - 向后兼容的导出
 * 从 base-client 重新导出以保持向后兼容性
 */

export type {ApiResponse, Pagination} from './api/base-types';

// 默认导出以保持向后兼容性
import {apiClient as client} from './api/base-client';

export default client;

// 命名导出
export const apiClient = client;
