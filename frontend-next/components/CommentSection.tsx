/**
 * 评论区域组件 - 包含评论列表、表单、回复等功能
 */

'use client';

import React, {useEffect, useState} from 'react';
import {Card, CardContent, CardHeader, CardTitle} from '@/components/ui/card';
import {Button} from '@/components/ui/button';
import {Input} from '@/components/ui/input';
import {Label} from '@/components/ui/label';
import {Alert, AlertDescription} from '@/components/ui/alert';
import CommentItem from './CommentItem';
import {CommentInput} from './CommentInput';
import apiClient from '@/lib/api-client';
import {MessageSquare} from 'lucide-react';

interface Comment {
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
    likes: number;
    parent_id: number | null;
    avatar_url?: string;
    replies?: Comment[];
}

interface CommentSectionProps {
    articleId: number;
}

const CommentSection: React.FC<CommentSectionProps> = ({articleId}) => {
    const [comments, setComments] = useState<Comment[]>([]);
    const [totalComments, setTotalComments] = useState(0);
    const [loading, setLoading] = useState(true);
    const [submitting, setSubmitting] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // 分页
    const [page, setPage] = useState(1);
    const [perPage] = useState(20);
    const [hasMore, setHasMore] = useState(true);

    // 评论表单
    const [formData, setFormData] = useState({
        author_name: '',
        author_email: '',
        author_url: '',
        parent_id: null as number | null
    });

    // 检查是否登录
    const [isLoggedIn, setIsLoggedIn] = useState(false);
    
    // 评论订阅状态
    const [subscribeToComments, setSubscribeToComments] = useState(false);

    useEffect(() => {
        checkLoginStatus();
        loadComments();
    }, [articleId, page]);

    // 检查登录状态
    const checkLoginStatus = () => {
        if (typeof window !== 'undefined') {
            const token = document.cookie
                .split('; ')
                .find(row => row.startsWith('access_token='));
            setIsLoggedIn(!!token);

            // 如果已登录，从cookie或localStorage获取用户信息
            if (token) {
                try {
                    const userInfo = localStorage.getItem('user_info');
                    if (userInfo) {
                        const user = JSON.parse(userInfo);
                        setFormData(prev => ({
                            ...prev,
                            author_name: user.username || '',
                            author_email: user.email || ''
                        }));
                    }
                } catch (e) {
                    console.error('Failed to parse user info:', e);
                }
            }
        }
    };

    // 加载评论
    const loadComments = async (pageNum: number = 1, append: boolean = false) => {
        try {
            setLoading(true);
            const response = await apiClient.get(
                `/api/v1/articles/${articleId}/comments?page=${pageNum}&per_page=${perPage}`
            );

            if (response.success && response.data) {
                const data = response.data as any;
                const newComments = data.comments || [];
                const total = data.total || 0;

                if (append) {
                    setComments(prev => [...prev, ...newComments]);
                } else {
                    setComments(newComments);
                }

                setTotalComments(total);
                setHasMore(pageNum < data.total_pages);
            }
        } catch (err: any) {
            console.error('Failed to load comments:', err);
            setError('加载评论失败');
        } finally {
            setLoading(false);
        }
    };

    // 加载更多
    const handleLoadMore = () => {
        const nextPage = page + 1;
        setPage(nextPage);
        loadComments(nextPage, true);
    };

    // 提交评论
    const handleSubmit = async (content: string) => {
        if (!isLoggedIn && (!formData.author_name || !formData.author_email)) {
            setError('请先填写姓名和邮箱');
            // 滚动到表单顶部以显示错误
            const formElement = document.getElementById('comment-form-container');
            if (formElement) {
                formElement.scrollIntoView({behavior: 'smooth'});
            }
            return;
        }

        try {
            setSubmitting(true);
            setError(null);

            const response = await apiClient.post('/api/v1/comments', {
                article_id: articleId,
                content: content,
                parent_id: formData.parent_id,
                author_name: formData.author_name || undefined,
                author_email: formData.author_email || undefined,
                author_url: formData.author_url || undefined
            });

            if (response.success) {
                // 如果用户选择了订阅，调用订阅API
                if (subscribeToComments) {
                    const email = isLoggedIn ? formData.author_email : formData.author_email;
                    if (email) {
                        try {
                            await apiClient.post('/api/v1/comment-subscriptions/subscribe', {
                                article_id: articleId,
                                email: email,
                                notify_type: 'reply_to_me'
                            });
                        } catch (err) {
                            console.error('Failed to subscribe to comments:', err);
                            // 订阅失败不影响评论提交
                        }
                    }
                }
                
                // 清空回复状态
                setFormData(prev => ({
                    ...prev,
                    parent_id: null
                }));

                // 重新加载评论
                setPage(1);
                loadComments(1, false);

                // 显示成功消息
                alert(response.message || '评论提交成功');
            } else {
                setError(response.error || '提交失败');
            }
        } catch (err: any) {
            console.error('Failed to submit comment:', err);
            setError(err.message || '网络错误');
        } finally {
            setSubmitting(false);
        }
    };

    // 回复评论
    const handleReply = (commentId: number, authorName: string) => {
        setFormData(prev => ({
            ...prev,
            parent_id: commentId
        }));

        // 滚动到表单
        const formElement = document.getElementById('comment-form-container');
        if (formElement) {
            formElement.scrollIntoView({behavior: 'smooth'});
        }
    };

    // 取消回复
    const handleCancelReply = () => {
        setFormData(prev => ({
            ...prev,
            parent_id: null
        }));
    };

    // 点赞评论
    const handleLike = async (commentId: number) => {
        try {
            const response = await apiClient.post(`/api/v1/comments/${commentId}/like`);

            if (response.success) {
                // 更新本地状态
                setComments(prev => updateCommentLikes(prev, commentId, 1));
            }
        } catch (err: any) {
            console.error('Failed to like comment:', err);
        }
    };

    // 递归更新评论点赞数
    const updateCommentLikes = (comments: Comment[], commentId: number, increment: number): Comment[] => {
        return comments.map(comment => {
            if (comment.id === commentId) {
                return {...comment, likes: comment.likes + increment};
            }
            if (comment.replies && comment.replies.length > 0) {
                return {
                    ...comment,
                    replies: updateCommentLikes(comment.replies, commentId, increment)
                };
            }
            return comment;
        });
    };

    // 将平铺的评论转换为树形结构
    const buildCommentTree = (comments: Comment[]): Comment[] => {
        const commentMap = new Map<number, Comment>();
        const rootComments: Comment[] = [];

        // 创建映射
        comments.forEach(comment => {
            commentMap.set(comment.id, {...comment, replies: []});
        });

        // 构建树形结构
        comments.forEach(comment => {
            const commentNode = commentMap.get(comment.id)!;
            if (comment.parent_id && commentMap.has(comment.parent_id)) {
                const parent = commentMap.get(comment.parent_id)!;
                if (!parent.replies) {
                    parent.replies = [];
                }
                parent.replies.push(commentNode);
            } else {
                rootComments.push(commentNode);
            }
        });

        return rootComments;
    };

    // 格式化日期
    const formatDate = (dateString: string) => {
        const date = new Date(dateString);
        const now = new Date();
        const diff = now.getTime() - date.getTime();

        const minutes = Math.floor(diff / 60000);
        const hours = Math.floor(diff / 3600000);
        const days = Math.floor(diff / 86400000);

        if (minutes < 1) return '刚刚';
        if (minutes < 60) return `${minutes}分钟前`;
        if (hours < 24) return `${hours}小时前`;
        if (days < 7) return `${days}天前`;

        return date.toLocaleDateString('zh-CN');
    };

    const commentTree = buildCommentTree(comments);

    return (
        <div className="mt-12 space-y-6">
            {/* 评论标题 */}
            <div className="flex items-center gap-2">
                <MessageSquare className="w-6 h-6 text-blue-600"/>
                <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
                    评论 ({totalComments})
                </h2>
            </div>

            {/* 评论表单 */}
            <Card id="comment-form-container">
                <CardHeader>
                    <CardTitle>
                        {formData.parent_id ? '回复评论' : '发表评论'}
                    </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                    {/* 回复提示 */}
                    {formData.parent_id && (
                        <Alert className="bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800">
                            <AlertDescription>
                                正在回复评论
                                <Button
                                    variant="link"
                                    size="sm"
                                    onClick={handleCancelReply}
                                    className="px-2"
                                >
                                    取消回复
                                </Button>
                            </AlertDescription>
                        </Alert>
                    )}

                    {/* 访客信息（未登录用户） */}
                    {!isLoggedIn && (
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div>
                                <Label htmlFor="author_name">姓名 *</Label>
                                <Input
                                    id="author_name"
                                    value={formData.author_name}
                                    onChange={(e) => setFormData({...formData, author_name: e.target.value})}
                                    placeholder="你的名字"
                                    required={!isLoggedIn}
                                />
                            </div>
                            <div>
                                <Label htmlFor="author_email">邮箱 *</Label>
                                <Input
                                    id="author_email"
                                    type="email"
                                    value={formData.author_email}
                                    onChange={(e) => setFormData({...formData, author_email: e.target.value})}
                                    placeholder="your@email.com"
                                    required={!isLoggedIn}
                                />
                            </div>
                            <div className="md:col-span-2">
                                <Label htmlFor="author_url">网站（可选）</Label>
                                <Input
                                    id="author_url"
                                    type="url"
                                    value={formData.author_url}
                                    onChange={(e) => setFormData({...formData, author_url: e.target.value})}
                                    placeholder="https://your-website.com"
                                />
                            </div>
                        </div>
                    )}

                    {/* 错误提示 */}
                    {error && (
                        <Alert variant="destructive">
                            <AlertDescription>{error}</AlertDescription>
                        </Alert>
                    )}

                    {/* 评论输入框（带表情支持） */}
                    <CommentInput 
                        onSubmit={handleSubmit}
                        placeholder={formData.parent_id ? "输入回复内容..." : "写下你的想法..."}
                    />

                    {/* 评论订阅选项 */}
                    <div className="flex items-center space-x-2">
                        <input
                            type="checkbox"
                            id="subscribe-comments"
                            checked={subscribeToComments}
                            onChange={(e) => setSubscribeToComments(e.target.checked)}
                            className="w-4 h-4 text-blue-600 rounded focus:ring-blue-500 border-gray-300"
                        />
                        <label htmlFor="subscribe-comments" className="text-sm text-gray-700 dark:text-gray-300 cursor-pointer">
                            有人回复时邮件通知我
                        </label>
                    </div>
                </CardContent>
            </Card>

            {/* 评论列表 */}
            {loading && comments.length === 0 ? (
                <div className="text-center py-8 text-gray-500">加载中...</div>
            ) : comments.length === 0 ? (
                <Card>
                    <CardContent className="py-8 text-center text-gray-500">
                        <MessageSquare className="w-12 h-12 mx-auto mb-4 opacity-50"/>
                        <p>暂无评论，快来发表第一条评论吧！</p>
                    </CardContent>
                </Card>
            ) : (
                <div className="space-y-4">
                    {commentTree.map((comment) => (
                        <CommentItem
                            key={comment.id}
                            comment={comment}
                            onReply={handleReply}
                            onLike={handleLike}
                            formatDate={formatDate}
                            depth={0}
                        />
                    ))}

                    {/* 加载更多 */}
                    {hasMore && (
                        <div className="text-center">
                            <Button
                                variant="outline"
                                onClick={handleLoadMore}
                                disabled={loading}
                            >
                                {loading ? '加载中...' : '加载更多评论'}
                            </Button>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
};

export default CommentSection;
