/**
 * 本地草稿管理服务
 * 使用 localStorage 保存和加载文章草稿
 */

export interface LocalDraft {
    articleId: number;
    title: string;
    excerpt: string;
    content: string;
    cover_image: string;
    tags: string[];
    category_id: number | null;
    status: number;
    hidden: boolean;
    is_vip_only: boolean;
    required_vip_level: number;
    is_featured: boolean;
    savedAt: string; // ISO 格式时间戳
    autoSave?: boolean; // 是否为自动保存
}

export class DraftService {
    private static readonly DRAFT_PREFIX = 'article_draft_';
    private static readonly DRAFT_LIST_KEY = 'article_draft_list';

    /**
     * 保存草稿到本地
     */
    static saveDraft(articleId: number, draftData: Omit<LocalDraft, 'articleId' | 'savedAt'>): void {
        try {
            const draft: LocalDraft = {
                articleId,
                ...draftData,
                savedAt: new Date().toISOString()
            };

            // 保存单个草稿
            const draftKey = `${this.DRAFT_PREFIX}${articleId}`;
            localStorage.setItem(draftKey, JSON.stringify(draft));

            // 更新草稿列表
            this.addToDraftList(articleId);

            console.log('✅ 草稿已保存到本地', {articleId, savedAt: draft.savedAt});
        } catch (error) {
            console.error('❌ 保存草稿失败:', error);
            throw error;
        }
    }

    /**
     * 从本地加载草稿
     */
    static loadDraft(articleId: number): LocalDraft | null {
        try {
            const draftKey = `${this.DRAFT_PREFIX}${articleId}`;
            const draftJson = localStorage.getItem(draftKey);

            if (!draftJson) {
                return null;
            }

            const draft = JSON.parse(draftJson) as LocalDraft;
            console.log('✅ 已加载本地草稿', {articleId, savedAt: draft.savedAt});

            return draft;
        } catch (error) {
            console.error('❌ 加载草稿失败:', error);
            return null;
        }
    }

    /**
     * 删除本地草稿
     */
    static deleteDraft(articleId: number): void {
        try {
            const draftKey = `${this.DRAFT_PREFIX}${articleId}`;
            localStorage.removeItem(draftKey);

            // 从草稿列表中移除
            this.removeFromDraftList(articleId);

            console.log('✅ 已删除本地草稿', {articleId});
        } catch (error) {
            console.error('❌ 删除草稿失败:', error);
        }
    }

    /**
     * 检查是否存在本地草稿
     */
    static hasDraft(articleId: number): boolean {
        const draftKey = `${this.DRAFT_PREFIX}${articleId}`;
        return localStorage.getItem(draftKey) !== null;
    }

    /**
     * 获取所有草稿列表
     */
    static getDraftList(): LocalDraft[] {
        try {
            const draftListJson = localStorage.getItem(this.DRAFT_LIST_KEY);

            if (!draftListJson) {
                return [];
            }

            const articleIds: number[] = JSON.parse(draftListJson);
            const drafts: LocalDraft[] = [];

            articleIds.forEach(articleId => {
                const draft = this.loadDraft(articleId);
                if (draft) {
                    drafts.push(draft);
                }
            });

            // 按保存时间降序排列
            return drafts.sort((a, b) =>
                new Date(b.savedAt).getTime() - new Date(a.savedAt).getTime()
            );
        } catch (error) {
            console.error('❌ 获取草稿列表失败:', error);
            return [];
        }
    }

    /**
     * 获取草稿的最后保存时间
     */
    static getLastSavedTime(articleId: number): string | null {
        const draft = this.loadDraft(articleId);
        return draft ? draft.savedAt : null;
    }

    /**
     * 清除所有草稿
     */
    static clearAllDrafts(): void {
        try {
            const draftList = this.getDraftList();

            draftList.forEach(draft => {
                const draftKey = `${this.DRAFT_PREFIX}${draft.articleId}`;
                localStorage.removeItem(draftKey);
            });

            localStorage.removeItem(this.DRAFT_LIST_KEY);

            console.log('✅ 已清除所有本地草稿');
        } catch (error) {
            console.error('❌ 清除草稿失败:', error);
        }
    }

    /**
     * 比较草稿与服务器数据是否有变化
     */
    static hasChanges(
        draft: LocalDraft,
        serverData: {
            title: string;
            content: string;
            excerpt: string;
            cover_image: string;
            tags: string[];
            category_id: number | null;
        }
    ): boolean {
        return (
            draft.title !== serverData.title ||
            draft.content !== serverData.content ||
            draft.excerpt !== serverData.excerpt ||
            draft.cover_image !== serverData.cover_image ||
            JSON.stringify(draft.tags) !== JSON.stringify(serverData.tags) ||
            draft.category_id !== serverData.category_id
        );
    }

    /**
     * 添加文章ID到草稿列表
     */
    private static addToDraftList(articleId: number): void {
        try {
            const draftListJson = localStorage.getItem(this.DRAFT_LIST_KEY);
            const articleIds: number[] = draftListJson ? JSON.parse(draftListJson) : [];

            if (!articleIds.includes(articleId)) {
                articleIds.push(articleId);
                localStorage.setItem(this.DRAFT_LIST_KEY, JSON.stringify(articleIds));
            }
        } catch (error) {
            console.error('❌ 更新草稿列表失败:', error);
        }
    }

    /**
     * 从草稿列表中移除文章ID
     */
    private static removeFromDraftList(articleId: number): void {
        try {
            const draftListJson = localStorage.getItem(this.DRAFT_LIST_KEY);

            if (draftListJson) {
                const articleIds: number[] = JSON.parse(draftListJson);
                const filteredIds = articleIds.filter(id => id !== articleId);
                localStorage.setItem(this.DRAFT_LIST_KEY, JSON.stringify(filteredIds));
            }
        } catch (error) {
            console.error('❌ 更新草稿列表失败:', error);
        }
    }
}
