'use client';

import React, {useEffect, useState} from 'react';
import {Card, CardContent, CardDescription, CardHeader, CardTitle} from '@/components/ui/card';
import {Button} from '@/components/ui/button';
import {Badge} from '@/components/ui/badge';
import {Label} from '@/components/ui/label';
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle
} from '@/components/ui/dialog';
import apiClient from '@/lib/api-client';
import {Calendar, CheckCircle2, Eye, MessageSquare, RefreshCw, Trash2, User, XCircle} from 'lucide-react';

interface Comment {
    id: number;
    article_id: number;
    article_title?: string;
    user_id: number | null;
    author_name: string | null;
    author_email: string | null;
    content: string;
    is_approved: boolean;
    created_at: string;
    updated_at: string;
    likes: number;
    parent_id: number | null;
    spam_score: number | null;
}

interface PaginationInfo {
    page: number;
    per_page: number;
    total: number;
    total_pages: number;
}

const CommentsManagement = () => {
    const [comments, setComments] = useState<Comment[]>([]);
    const [pagination, setPagination] = useState<PaginationInfo>({
        page: 1,
        per_page: 20,
        total: 0,
        total_pages: 1
    });
    const [loading, setLoading] = useState(true);
    const [filter, setFilter] = useState<'all' | 'pending' | 'approved'>('all');
    const [searchQuery, setSearchQuery] = useState('');
    const [selectedComments, setSelectedComments] = useState<number[]>([]);

    // 对话框状态
    const [showViewDialog, setShowViewDialog] = useState(false);
    const [showApproveDialog, setShowApproveDialog] = useState(false);
    const [showRejectDialog, setShowRejectDialog] = useState(false);
    const [showDeleteDialog, setShowDeleteDialog] = useState(false);
    const [currentComment, setCurrentComment] = useState<Comment | null>(null);

    // 加载评论列表
    const loadComments = async () => {
        setLoading(true);
        try {
            let url = '/api/v1/admin/comments/pending';

            if (filter === 'all') {
                url = `/api/v1/comments?page=${pagination.page}&per_page=${pagination.per_page}`;
            } else if (filter === 'approved') {
                url = `/api/v1/comments?page=${pagination.page}&per_page=${pagination.per_page}&approved=true`;
            }
            // pending 使用默认URL

            const response = await apiClient.get(url);

            if (response.success && response.data) {
                const data = response.data as any;
                // 处理不同的响应格式
                if (data.comments) {
                    setComments(data.comments);
                    if (data.pagination) {
                        setPagination(data.pagination);
                    }
                } else if (Array.isArray(data)) {
                    setComments(data);
                }
            }
        } catch (error: any) {
            console.error('Failed to load comments:', error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        loadComments();
    }, [pagination.page, filter]);

    // 批准评论
    const handleApprove = async (commentId: number) => {
        try {
            const response = await apiClient.post(`/api/v1/admin/comments/${commentId}/approve`);
            if (response.success) {
                loadComments();
                setShowApproveDialog(false);
            }
        } catch (error: any) {
            console.error('Failed to approve comment:', error);
        }
    };

    // 拒绝评论
    const handleReject = async (commentId: number) => {
        try {
            const response = await apiClient.post(`/api/v1/admin/comments/${commentId}/reject`);
            if (response.success) {
                loadComments();
                setShowRejectDialog(false);
            }
        } catch (error: any) {
            console.error('Failed to reject comment:', error);
        }
    };

    // 删除评论
    const handleDelete = async (commentId: number) => {
        try {
            const response = await apiClient.delete(`/api/v1/comments/${commentId}`);
            if (response.success) {
                loadComments();
                setShowDeleteDialog(false);
            }
        } catch (error: any) {
            console.error('Failed to delete comment:', error);
        }
    };

    // 批量操作
    const handleBatchApprove = async () => {
        for (const commentId of selectedComments) {
            await handleApprove(commentId);
        }
        setSelectedComments([]);
    };

    const handleBatchDelete = async () => {
        for (const commentId of selectedComments) {
            await handleDelete(commentId);
        }
        setSelectedComments([]);
    };

    // 选择/取消选择评论
    const toggleSelectComment = (commentId: number) => {
        if (selectedComments.includes(commentId)) {
            setSelectedComments(selectedComments.filter(id => id !== commentId));
        } else {
            setSelectedComments([...selectedComments, commentId]);
        }
    };

    // 全选/取消全选
    const toggleSelectAll = () => {
        if (selectedComments.length === comments.length) {
            setSelectedComments([]);
        } else {
            setSelectedComments(comments.map(c => c.id));
        }
    };

    // 格式化日期
    const formatDate = (dateString: string) => {
        return new Date(dateString).toLocaleString('zh-CN');
    };

    // 获取作者显示名称
    const getAuthorName = (comment: Comment) => {
        return comment.author_name || (comment.user_id ? `用户 #${comment.user_id}` : '匿名用户');
    };

    // 截断内容
    const truncateContent = (content: string, maxLength: number = 100) => {
        if (content.length <= maxLength) return content;
        return content.substring(0, maxLength) + '...';
    };

    return (
        <div className="container mx-auto px-4 py-8 max-w-7xl">
            <div className="mb-8">
                <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2 flex items-center">
                    <MessageSquare className="w-8 h-8 mr-3 text-blue-600"/>
                    评论管理
                </h1>
                <p className="text-gray-600 dark:text-gray-400">
                    审核、管理和回复用户评论
                </p>
            </div>

            {/* 筛选和操作栏 */}
            <Card className="mb-6">
                <CardContent className="pt-6">
                    <div className="flex flex-wrap gap-4 items-center justify-between">
                        <div className="flex gap-2">
                            <Button
                                variant={filter === 'all' ? 'default' : 'outline'}
                                onClick={() => setFilter('all')}
                            >
                                全部
                            </Button>
                            <Button
                                variant={filter === 'pending' ? 'default' : 'outline'}
                                onClick={() => setFilter('pending')}
                            >
                                待审核
                            </Button>
                            <Button
                                variant={filter === 'approved' ? 'default' : 'outline'}
                                onClick={() => setFilter('approved')}
                            >
                                已通过
                            </Button>
                        </div>

                        <div className="flex gap-2">
                            {selectedComments.length > 0 && (
                                <>
                                    <Button
                                        variant="outline"
                                        size="sm"
                                        onClick={handleBatchApprove}
                                    >
                                        <CheckCircle2 className="w-4 h-4 mr-2"/>
                                        批量批准 ({selectedComments.length})
                                    </Button>
                                    <Button
                                        variant="destructive"
                                        size="sm"
                                        onClick={handleBatchDelete}
                                    >
                                        <Trash2 className="w-4 h-4 mr-2"/>
                                        批量删除 ({selectedComments.length})
                                    </Button>
                                </>
                            )}
                            <Button
                                variant="outline"
                                size="sm"
                                onClick={loadComments}
                            >
                                <RefreshCw className="w-4 h-4 mr-2"/>
                                刷新
                            </Button>
                        </div>
                    </div>
                </CardContent>
            </Card>

            {/* 评论列表 */}
            <Card>
                <CardHeader>
                    <CardTitle>评论列表</CardTitle>
                    <CardDescription>
                        共 {pagination.total} 条评论
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    {loading ? (
                        <div className="text-center py-8 text-gray-500">加载中...</div>
                    ) : comments.length === 0 ? (
                        <div className="text-center py-8 text-gray-500">暂无评论</div>
                    ) : (
                        <div className="space-y-4">
                            {comments.map((comment) => (
                                <div
                                    key={comment.id}
                                    className={`p-4 rounded-lg border transition-all ${
                                        selectedComments.includes(comment.id)
                                            ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                                            : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'
                                    }`}
                                >
                                    <div className="flex items-start gap-4">
                                        {/* 复选框 */}
                                        <input
                                            type="checkbox"
                                            checked={selectedComments.includes(comment.id)}
                                            onChange={() => toggleSelectComment(comment.id)}
                                            className="mt-1 w-4 h-4 rounded border-gray-300"
                                        />

                                        {/* 评论内容 */}
                                        <div className="flex-1 min-w-0">
                                            <div className="flex items-center justify-between mb-2">
                                                <div className="flex items-center gap-2">
                                                    <User className="w-4 h-4 text-gray-500"/>
                                                    <span className="font-medium text-gray-900 dark:text-white">
                            {getAuthorName(comment)}
                          </span>
                                                    {comment.author_email && (
                                                        <span className="text-sm text-gray-500">
                              ({comment.author_email})
                            </span>
                                                    )}
                                                </div>
                                                <div className="flex items-center gap-2">
                                                    <Badge variant={comment.is_approved ? 'default' : 'secondary'}>
                                                        {comment.is_approved ? '已通过' : '待审核'}
                                                    </Badge>
                                                    {comment.spam_score && comment.spam_score > 0.5 && (
                                                        <Badge variant="destructive">
                                                            疑似垃圾
                                                        </Badge>
                                                    )}
                                                </div>
                                            </div>

                                            <div className="text-sm text-gray-700 dark:text-gray-300 mb-2">
                                                {truncateContent(comment.content, 200)}
                                            </div>

                                            <div className="flex items-center gap-4 text-xs text-gray-500">
                                                <div className="flex items-center gap-1">
                                                    <Calendar className="w-3 h-3"/>
                                                    {formatDate(comment.created_at)}
                                                </div>
                                                <div>文章ID: {comment.article_id}</div>
                                                <div>点赞: {comment.likes}</div>
                                                {comment.parent_id && (
                                                    <div>回复评论 #{comment.parent_id}</div>
                                                )}
                                            </div>
                                        </div>

                                        {/* 操作按钮 */}
                                        <div className="flex flex-col gap-2">
                                            <Button
                                                variant="outline"
                                                size="sm"
                                                onClick={() => {
                                                    setCurrentComment(comment);
                                                    setShowViewDialog(true);
                                                }}
                                            >
                                                <Eye className="w-4 h-4"/>
                                            </Button>

                                            {!comment.is_approved && (
                                                <>
                                                    <Button
                                                        variant="default"
                                                        size="sm"
                                                        onClick={() => {
                                                            setCurrentComment(comment);
                                                            setShowApproveDialog(true);
                                                        }}
                                                    >
                                                        <CheckCircle2 className="w-4 h-4"/>
                                                    </Button>
                                                    <Button
                                                        variant="destructive"
                                                        size="sm"
                                                        onClick={() => {
                                                            setCurrentComment(comment);
                                                            setShowRejectDialog(true);
                                                        }}
                                                    >
                                                        <XCircle className="w-4 h-4"/>
                                                    </Button>
                                                </>
                                            )}

                                            <Button
                                                variant="destructive"
                                                size="sm"
                                                onClick={() => {
                                                    setCurrentComment(comment);
                                                    setShowDeleteDialog(true);
                                                }}
                                            >
                                                <Trash2 className="w-4 h-4"/>
                                            </Button>
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}

                    {/* 分页 */}
                    {pagination.total_pages > 1 && (
                        <div className="flex justify-center gap-2 mt-6">
                            <Button
                                variant="outline"
                                size="sm"
                                onClick={() => setPagination({...pagination, page: pagination.page - 1})}
                                disabled={pagination.page === 1}
                            >
                                上一页
                            </Button>
                            <span className="px-4 py-2 text-sm">
                第 {pagination.page} / {pagination.total_pages} 页
              </span>
                            <Button
                                variant="outline"
                                size="sm"
                                onClick={() => setPagination({...pagination, page: pagination.page + 1})}
                                disabled={pagination.page === pagination.total_pages}
                            >
                                下一页
                            </Button>
                        </div>
                    )}
                </CardContent>
            </Card>

            {/* 查看评论对话框 */}
            <Dialog open={showViewDialog} onOpenChange={setShowViewDialog}>
                <DialogContent className="max-w-2xl">
                    <DialogHeader>
                        <DialogTitle>评论详情</DialogTitle>
                    </DialogHeader>
                    {currentComment && (
                        <div className="space-y-4">
                            <div>
                                <Label>作者</Label>
                                <div className="mt-1 p-3 bg-gray-50 dark:bg-gray-800 rounded">
                                    {getAuthorName(currentComment)}
                                    {currentComment.author_email && (
                                        <div className="text-sm text-gray-500">{currentComment.author_email}</div>
                                    )}
                                </div>
                            </div>

                            <div>
                                <Label>评论内容</Label>
                                <div className="mt-1 p-3 bg-gray-50 dark:bg-gray-800 rounded whitespace-pre-wrap">
                                    {currentComment.content}
                                </div>
                            </div>

                            <div className="grid grid-cols-2 gap-4 text-sm">
                                <div>
                                    <Label>状态</Label>
                                    <div className="mt-1">
                                        <Badge variant={currentComment.is_approved ? 'default' : 'secondary'}>
                                            {currentComment.is_approved ? '已通过' : '待审核'}
                                        </Badge>
                                    </div>
                                </div>
                                <div>
                                    <Label>点赞数</Label>
                                    <div className="mt-1">{currentComment.likes}</div>
                                </div>
                                <div>
                                    <Label>创建时间</Label>
                                    <div className="mt-1">{formatDate(currentComment.created_at)}</div>
                                </div>
                                <div>
                                    <Label>文章ID</Label>
                                    <div className="mt-1">{currentComment.article_id}</div>
                                </div>
                            </div>
                        </div>
                    )}
                </DialogContent>
            </Dialog>

            {/* 批准确认对话框 */}
            <Dialog open={showApproveDialog} onOpenChange={setShowApproveDialog}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>批准评论</DialogTitle>
                        <DialogDescription>
                            确定要批准这条评论吗？批准后将对所有用户可见。
                        </DialogDescription>
                    </DialogHeader>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setShowApproveDialog(false)}>
                            取消
                        </Button>
                        <Button onClick={() => currentComment && handleApprove(currentComment.id)}>
                            <CheckCircle2 className="w-4 h-4 mr-2"/>
                            批准
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* 拒绝确认对话框 */}
            <Dialog open={showRejectDialog} onOpenChange={setShowRejectDialog}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>拒绝评论</DialogTitle>
                        <DialogDescription>
                            确定要拒绝这条评论吗？拒绝后评论将被标记为未通过。
                        </DialogDescription>
                    </DialogHeader>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setShowRejectDialog(false)}>
                            取消
                        </Button>
                        <Button variant="destructive" onClick={() => currentComment && handleReject(currentComment.id)}>
                            <XCircle className="w-4 h-4 mr-2"/>
                            拒绝
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* 删除确认对话框 */}
            <Dialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>删除评论</DialogTitle>
                        <DialogDescription>
                            确定要删除这条评论吗？此操作不可恢复！
                        </DialogDescription>
                    </DialogHeader>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setShowDeleteDialog(false)}>
                            取消
                        </Button>
                        <Button variant="destructive" onClick={() => currentComment && handleDelete(currentComment.id)}>
                            <Trash2 className="w-4 h-4 mr-2"/>
                            删除
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    );
};

export default CommentsManagement;
