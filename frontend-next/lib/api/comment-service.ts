/**
 * 评论服务
 * 提供评论相关的API调用
 */

import apiClient from '../api-client';

export interface Comment {
    id: number;
    article_id: number;
    user_id: number | null;
    username?: string;
    author_name: string | null;
    author_email: string | null;
    author_url: string | null;
    content: string;
    is_approved: boolean;
    created_at: string;
    updated_at?: string;
    likes: number;
    parent_id: number | null;
    avatar_url?: string;
    replies?: Comment[];
}

export interface CommentListResponse {
    success: boolean;
    data: {
        comments: Comment[];
        total: number;
        page: number;
        per_page: number;
    };
    error?: string;
}

export interface LikeCommentResponse {
    success: boolean;
    data: {
        action: 'liked' | 'unliked';
        likes: number;
    };
    error?: string;
}

class CommentService {
    /**
     * 获取文章评论列表
     * @param articleId - 文章ID
     * @param page - 页码
     * @param perPage - 每页数量
     * @param sortBy - 排序方式 (created_at, likes)
     * @param order - 排序方向 (asc, desc)
     */
    async getComments(
        articleId: number,
        page: number = 1,
        perPage: number = 20,
        sortBy: string = 'created_at',
        order: string = 'desc'
    ): Promise<CommentListResponse> {
        try {
            // 使用 /comments/enhanced/article/{article_id} 端点
            const response = await apiClient.get<{
                comments: Comment[];
                total: number;
                page: number;
                per_page: number
            }>(
                `/comments/enhanced/article/${articleId}`,
                {page, per_page: perPage, sort_by: sortBy, order}
            );

            return response as CommentListResponse;
        } catch (error) {
            console.error('[CommentService] Failed to get comments:', error);
            return {
                success: false,
                data: {comments: [], total: 0, page, per_page: perPage},
                error: error instanceof Error ? error.message : '获取评论失败',
            };
        }
    }

    /**
     * 创建评论
     * @param articleId - 文章ID
     * @param content - 评论内容
     * @param parentId - 父评论ID（回复时使用）
     * @param authorName - 作者名称（访客评论）
     * @param authorEmail - 作者邮箱（访客评论）
     */
    async createComment(
        articleId: number,
        content: string,
        parentId?: number,
        authorName?: string,
        authorEmail?: string
    ): Promise<{ success: boolean; data?: Comment; error?: string }> {
        try {
            // 后端可能没有直接的创建评论端点，需要确认
            // 暂时使用 /comments/enhanced/article/{article_id} POST 方法
            const response = await apiClient.post<Comment>(`/comments/enhanced/article/${articleId}`, {
                content,
                parent_id: parentId,
                author_name: authorName,
                author_email: authorEmail,
            });

            return response as { success: boolean; data?: Comment; error?: string };
        } catch (error) {
            console.error('[CommentService] Failed to create comment:', error);
            return {
                success: false,
                error: error instanceof Error ? error.message : '发表评论失败',
            };
        }
    }

    /**
     * 点赞评论
     * @param commentId - 评论ID
     */
    async likeComment(commentId: number): Promise<LikeCommentResponse> {
        try {
            // 使用 /comments/enhanced/{comment_id}/like
            const response = await apiClient.post<{ action: 'liked' | 'unliked'; likes: number }>(
                `/comments/enhanced/${commentId}/like`
            );
            return response as LikeCommentResponse;
        } catch (error) {
            console.error('[CommentService] Failed to like comment:', error);
            return {
                success: false,
                data: {action: 'unliked', likes: 0},
                error: error instanceof Error ? error.message : '点赞失败',
            };
        }
    }

    /**
     * 取消点赞评论
     * @param commentId - 评论ID
     */
    async unlikeComment(commentId: number): Promise<LikeCommentResponse> {
        try {
            // 后端使用 toggle 机制，再次调用即可取消点赞
            const response = await apiClient.post<{ action: 'liked' | 'unliked'; likes: number }>(
                `/comments/enhanced/${commentId}/like`
            );
            return response as LikeCommentResponse;
        } catch (error) {
            console.error('[CommentService] Failed to unlike comment:', error);
            return {
                success: false,
                data: {action: 'liked', likes: 0},
                error: error instanceof Error ? error.message : '取消点赞失败',
            };
        }
    }

    /**
     * 获取用户对评论的投票状态
     * @param commentId - 评论ID
     */
    async getUserVote(commentId: number): Promise<{
        success: boolean;
        data?: { vote_type: 'like' | 'dislike' | null };
        error?: string;
    }> {
        try {
            // 使用 /comments/enhanced/{comment_id}/vote
            const response = await apiClient.get<{ vote_type: 'like' | 'dislike' | null }>(
                `/comments/enhanced/${commentId}/vote`
            );
            return response as { success: boolean; data?: { vote_type: 'like' | 'dislike' | null }; error?: string };
        } catch (error) {
            console.error('[CommentService] Failed to get user vote:', error);
            return {
                success: false,
                data: {vote_type: null},
                error: error instanceof Error ? error.message : '获取投票状态失败',
            };
        }
    }

    /**
     * 删除评论（仅管理员或评论作者）
     * @param commentId - 评论ID
     */
    async deleteComment(commentId: number): Promise<{
        success: boolean;
        error?: string;
    }> {
        try {
            const response = await apiClient.delete(`/comments/${commentId}`);
            return response as { success: boolean; error?: string };
        } catch (error) {
            console.error('[CommentService] Failed to delete comment:', error);
            return {
                success: false,
                error: error instanceof Error ? error.message : '删除评论失败',
            };
        }
    }

    /**
     * 更新评论（仅评论作者）
     * @param commentId - 评论ID
     * @param content - 新的评论内容
     */
    async updateComment(
        commentId: number,
        content: string
    ): Promise<{ success: boolean; data?: Comment; error?: string }> {
        try {
            const response = await apiClient.put<Comment>(`/comments/${commentId}`, {
                content,
            });
            return response as { success: boolean; data?: Comment; error?: string };
        } catch (error) {
            console.error('[CommentService] Failed to update comment:', error);
            return {
                success: false,
                error: error instanceof Error ? error.message : '更新评论失败',
            };
        }
    }
}

// 导出单例实例
export const commentService = new CommentService();
export default commentService;
