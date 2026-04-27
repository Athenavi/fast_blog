/**
 * 最新评论 Widget
 * 显示最近的评论列表
 */

'use client';

import React, {useEffect, useState} from 'react';
import Link from 'next/link';
import {Card, CardContent, CardHeader, CardTitle} from '@/components/ui/card';
import apiClient from '@/lib/api-client';
import {MessageCircle} from 'lucide-react';

interface Comment {
    id: number;
    author_name: string;
    avatar_url?: string;
    content: string;
    created_at: string;
    article_id: number;
    article_title: string;
}

interface RecentCommentsWidgetProps {
    widgetId: number;
    title: string;
    config: {
        count?: number;
        show_avatar?: boolean;
        show_article?: boolean;
        excerpt_length?: number;
    };
}

const RecentCommentsWidget: React.FC<RecentCommentsWidgetProps> = ({title, config}) => {
    const [comments, setComments] = useState<Comment[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        loadComments();
    }, []);

    const loadComments = async () => {
        try {
            const response = await apiClient.get(
                `/api/v1/widgets/data/recent-comments?count=${config.count || 5}&show_avatar=${config.show_avatar !== false}`
            );

            if (response.success && response.data) {
                setComments((response.data as any).comments || []);
            }
        } catch (error) {
            console.error('Failed to load recent comments:', error);
        } finally {
            setLoading(false);
        }
    };

    const formatDate = (dateString: string): string => {
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

    if (loading) {
        return (
            <Card>
                <CardContent className="p-4">
                    <div className="animate-pulse space-y-3">
                        {[...Array(config.count || 5)].map((_, i) => (
                            <div key={i} className="flex gap-3">
                                <div className="h-10 w-10 bg-gray-200 dark:bg-gray-700 rounded-full"/>
                                <div className="flex-1 space-y-2">
                                    <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-1/3"/>
                                    <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-full"/>
                                </div>
                            </div>
                        ))}
                    </div>
                </CardContent>
            </Card>
        );
    }

    if (!comments.length) {
        return null;
    }

    return (
        <Card>
            <CardHeader className="pb-3">
                <CardTitle className="text-lg flex items-center gap-2">
                    <MessageCircle className="w-5 h-5 text-blue-500"/>
                    {title || '最新评论'}
                </CardTitle>
            </CardHeader>
            <CardContent>
                <div className="space-y-3">
                    {comments.map((comment) => (
                        <div key={comment.id} className="flex gap-3 p-2 hover:bg-gray-50 dark:hover:bg-gray-800 rounded transition-colors">
                            {/* 头像 */}
                            {config.show_avatar !== false && (
                                <div className="flex-shrink-0">
                                    {comment.avatar_url ? (
                                        <img
                                            src={comment.avatar_url}
                                            alt={comment.author_name}
                                            className="w-10 h-10 rounded-full object-cover"
                                        />
                                    ) : (
                                        <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-400 to-purple-500 flex items-center justify-center text-white font-bold">
                                            {comment.author_name.charAt(0).toUpperCase()}
                                        </div>
                                    )}
                                </div>
                            )}

                            {/* 评论内容 */}
                            <div className="flex-1 min-w-0">
                                {/* 作者名和时间 */}
                                <div className="flex items-center gap-2 mb-1">
                                    <span className="text-sm font-medium text-gray-900 dark:text-white">
                                        {comment.author_name}
                                    </span>
                                    <span className="text-xs text-gray-500">
                                        {formatDate(comment.created_at)}
                                    </span>
                                </div>

                                {/* 评论摘要 */}
                                <p className="text-sm text-gray-600 dark:text-gray-400 line-clamp-2 mb-1">
                                    {comment.content}
                                </p>

                                {/* 文章标题 */}
                                {config.show_article !== false && (
                                    <Link
                                        href={`/article/${comment.article_id}`}
                                        className="text-xs text-blue-600 hover:underline truncate block"
                                    >
                                        发表在：{comment.article_title}
                                    </Link>
                                )}
                            </div>
                        </div>
                    ))}
                </div>
            </CardContent>
        </Card>
    );
};

export default RecentCommentsWidget;
