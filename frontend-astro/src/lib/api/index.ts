import {apiClient} from "@/lib/api/base-client";

import {getConfig} from '@/lib/config';
import {MEDIA} from '@/lib/api/api-paths';

export {apiClient} from "@/lib/api/base-client";
export {ArticleService} from './article-service';
export type {Article, Category, ApiResponse, Pagination} from './base-types';

export interface MediaFile {
    filename: string;
    id: number;
    user?: number;
    original_filename: string;
    hash?: string;
    mime_type?: string;
    file_size?: number;
    url?: string;
    folder_name?: string;
    category?: string;
    tags?: string;
    created_at?: string;
    updated_at?: string;
}

export interface MediaResponse {
    files: MediaFile[];
    total: number;
    page?: number;
    per_page?: number;
}

export {CategoryService} from './category-service';

// V3 管理端 API（带 V3→V2 自动降级）
export {adminService, adminUserService, adminArticleService, adminMediaService, adminSystemService, adminRoleService, adminDashboardService, adminCommentService, adminPluginService, adminThemeService, adminSeoService, adminBackupService, adminPermissionService, adminCategoryService, adminAnalyticsService, adminNotificationService, adminWebhookService} from './admin-service';
export {adminApi} from './admin-api-client';

export const MediaService = {
    async getMediaFiles(params: Record<string, any> = {}) {
        return apiClient.get(MEDIA.LIST, params);
    },
    async deleteMediaFile(ids: number[]) {
        return apiClient.post(MEDIA.BATCH_DELETE, {media_ids: ids});
    },
    async uploadMediaFileWithProgress(file: File, onProgress?: (pct: number) => void): Promise<any> {
        const form = new FormData();
        form.append('file', file);
        const xhr = new XMLHttpRequest();
        return new Promise((resolve, reject) => {
            xhr.open('POST', `${getConfig().API_BASE_URL}/api/v2/media/upload`);
            xhr.withCredentials = true;
            if (onProgress) {
                xhr.upload.onprogress = (e) => {
                    if (e.lengthComputable) onProgress(Math.round((e.loaded / e.total) * 100));
                };
            }
            xhr.onload = () => {
                try {
                    resolve(JSON.parse(xhr.responseText));
                } catch {
                    resolve({success: false, error: xhr.responseText});
                }
            };
            xhr.onerror = () => reject(new Error('上传失败'));
            xhr.send(form);
        });
    },
};
