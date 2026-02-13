// Article management service for Next.js frontend
import {apiClient} from './base-client';
import type {ApiResponse, Article, Pagination} from '@/lib/api/base-types';

// Article management types
export interface ArticleStats {
  total_articles: number;
  published_articles: number;
  draft_articles: number;
  total_views: number;
}

// Article management service
export class ArticleManagementService {
  static async getArticleStats(): Promise<ApiResponse<ArticleStats>> {
    return apiClient.get('/blog-management/articles/stats');
  }

  static async getArticles(
    params?: { page?: number; per_page?: number; status?: string; search?: string; category_id?: number }
  ): Promise<ApiResponse<{ articles: Article[]; pagination: Pagination }>> {
    const response = await apiClient.get('/blog-management/articles', params);
    
    // 确保返回正确的格式
    if (response.success && response.data && typeof response.data === 'object') {
      // 如果响应数据已经是期望格式
      if ('articles' in response.data && 'pagination' in response.data) {
        return response as ApiResponse<{ articles: Article[]; pagination: Pagination }>;
      } else {
        // 如果响应数据是纯数组或不同格式，构造期望的格式
        return {
          ...response,
          data: {
            articles: Array.isArray(response.data) ? response.data : [],
            pagination: ('pagination' in (response.data || {}) && (response.data as any)?.pagination) ? (response.data as any).pagination : {
              current_page: params?.page || 1,
              per_page: params?.per_page || 10,
              total: Array.isArray(response.data) ? response.data.length : 0,
              total_pages: 1,
              has_next: false,
              has_prev: false
            }
          }
        } as ApiResponse<{ articles: Article[]; pagination: Pagination }>;
      }
    }
    
    return {
      ...response,
      data: {
        articles: [],
        pagination: {
          current_page: params?.page || 1,
          per_page: params?.per_page || 10,
          total: 0,
          total_pages: 1,
          has_next: false,
          has_prev: false
        }
      }
    } as ApiResponse<{ articles: Article[]; pagination: Pagination }>;
  }
  
  static async deleteArticle(id: number): Promise<ApiResponse<any>> {
    return apiClient.delete(`/blog-management/articles/${id}`);
  }
}