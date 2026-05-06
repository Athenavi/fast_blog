/**
 * 本地草稿服务
 * 提供离线草稿保存和恢复功能
 */

interface DraftData {
    [key: string]: any;
}

interface SavedDraft {
    data: DraftData;
    savedAt: string;
    articleId?: number;
}

const DRAFT_STORAGE_KEY = 'fastblog_drafts';

class DraftService {
    /**
     * 保存草稿到本地存储
     * @param articleId - 文章ID（可选，新建文章时可不传）
     * @param data - 草稿数据
     */
    saveDraft(articleId: number | string, data: DraftData): void {
        try {
            const drafts = this.getAllDrafts();
            const key = articleId.toString();

            drafts[key] = {
                data,
                savedAt: new Date().toISOString(),
                articleId: typeof articleId === 'number' ? articleId : undefined,
            };

            localStorage.setItem(DRAFT_STORAGE_KEY, JSON.stringify(drafts));
            console.log('[DraftService] Draft saved:', key);
        } catch (error) {
            console.error('[DraftService] Failed to save draft:', error);
        }
    }

    /**
     * 获取草稿
     * @param articleId - 文章ID
     * @returns 草稿数据，如果不存在则返回 null
     */
    getDraft(articleId: number | string): SavedDraft | null {
        try {
            const drafts = this.getAllDrafts();
            const key = articleId.toString();
            return drafts[key] || null;
        } catch (error) {
            console.error('[DraftService] Failed to get draft:', error);
            return null;
        }
    }

    /**
     * 删除草稿
     * @param articleId - 文章ID
     */
    deleteDraft(articleId: number | string): void {
        try {
            const drafts = this.getAllDrafts();
            const key = articleId.toString();
            delete drafts[key];
            localStorage.setItem(DRAFT_STORAGE_KEY, JSON.stringify(drafts));
            console.log('[DraftService] Draft deleted:', key);
        } catch (error) {
            console.error('[DraftService] Failed to delete draft:', error);
    }
    }

    /**
     * 获取所有草稿
     * @returns 所有草稿的键值对
     */
    getAllDrafts(): Record<string, SavedDraft> {
        try {
            const stored = localStorage.getItem(DRAFT_STORAGE_KEY);
            return stored ? JSON.parse(stored) : {};
        } catch (error) {
            console.error('[DraftService] Failed to get all drafts:', error);
            return {};
        }
    }

    /**
     * 检查是否存在草稿
     * @param articleId - 文章ID
     * @returns 是否存在草稿
     */
    hasDraft(articleId: number | string): boolean {
        const draft = this.getDraft(articleId);
        return draft !== null;
    }

    /**
     * 获取草稿的最后保存时间
     * @param articleId - 文章ID
     * @returns 最后保存时间，如果不存在则返回 null
     */
    getLastSavedTime(articleId: number | string): Date | null {
        const draft = this.getDraft(articleId);
        return draft ? new Date(draft.savedAt) : null;
    }

    /**
     * 清理过期草稿（超过7天）
     */
    cleanupExpiredDrafts(): void {
        try {
            const drafts = this.getAllDrafts();
            const now = new Date();
            const sevenDaysMs = 7 * 24 * 60 * 60 * 1000;

            const cleanedDrafts: Record<string, SavedDraft> = {};

            Object.entries(drafts).forEach(([key, draft]) => {
                const savedAt = new Date(draft.savedAt);
                const diff = now.getTime() - savedAt.getTime();

                // 保留7天内的草稿
                if (diff < sevenDaysMs) {
                    cleanedDrafts[key] = draft;
                }
            });

            localStorage.setItem(DRAFT_STORAGE_KEY, JSON.stringify(cleanedDrafts));
            console.log('[DraftService] Expired drafts cleaned up');
        } catch (error) {
            console.error('[DraftService] Failed to cleanup drafts:', error);
        }
    }

    /**
     * 清空所有草稿
     */
    clearAllDrafts(): void {
        try {
            localStorage.removeItem(DRAFT_STORAGE_KEY);
            console.log('[DraftService] All drafts cleared');
        } catch (error) {
            console.error('[DraftService] Failed to clear drafts:', error);
        }
    }

    /**
     * 获取草稿数量
     * @returns 草稿数量
     */
    getDraftCount(): number {
        const drafts = this.getAllDrafts();
        return Object.keys(drafts).length;
    }
}

// 导出单例实例
export const draftService = new DraftService();
export default draftService;
