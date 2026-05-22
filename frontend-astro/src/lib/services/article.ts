/**
 * 文章服务
 */

import {apiClient} from '../api';
import type {ApiResponse, Article, PaginatedResponse} from './types';

export class ArticleService {
    /**
     * 获取首页文章
     */
    static async getHomeArticles(params?: { page?: number; per_page?: number }) {
        return apiClient.get<ApiResponse<PaginatedResponse<Article>>>('/api/v2/articles/home', params);
    }

    /**
     * 获取文章列表
     */
    static async getArticles(params?: {
        page?: number;
        per_page?: number;
        search?: string;
        category_id?: number;
    }) {
        return apiClient.get<ApiResponse<PaginatedResponse<Article>>>('/api/v2/articles', params);
    }

    /**
     * 获取文章详情
     */
    static async getArticleBySlug(slug: string) {
        return apiClient.get<ApiResponse<Article>>(`/api/v2/articles/slug/${slug}`);
    }

    /**
     * 获取热门文章
     */
    static async getPopularArticles(limit = 10) {
        return apiClient.get<ApiResponse<Article[]>>('/api/v2/articles/popular', {limit});
    }

    /**
     * 获取最新文章
     */
    static async getRecentArticles(limit = 10) {
        return apiClient.get<ApiResponse<Article[]>>('/api/v2/articles/recent', {limit});
    }
}
