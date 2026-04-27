/**
 * 最新文章Widget
 */

'use client';

import React, {useEffect, useState} from 'react';
import Link from 'next/link';
import Image from 'next/image';
import {Card, CardContent, CardHeader, CardTitle} from '@/components/ui/card';
import apiClient from '@/lib/api-client';

interface Article {
    id: number;
    title: string;
    slug: string;
    excerpt?: string;
    cover_image?: string;
    created_at: string;
}

interface RecentPostsWidgetProps {
    widgetId: number;
    title: string;
    config: {
        count?: number;
        show_thumbnail?: boolean;
        show_date?: boolean;
        show_excerpt?: boolean;
        excerpt_length?: number;
    };
}

const RecentPostsWidget: React.FC<RecentPostsWidgetProps> = ({title, config}) => {
    const [articles, setArticles] = useState<Article[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        loadArticles();
    }, []);

    const loadArticles = async () => {
        try {
            const response = await apiClient.get(
                `/api/v1/articles?page=1&per_page=${config.count || 5}&order_by=created_at&order=desc`
            );

            if (response.success && response.data) {
                const data = response.data as any;
                setArticles(data.articles || []);
            }
        } catch (error) {
            console.error('Failed to load recent articles:', error);
        } finally {
            setLoading(false);
        }
    };

    const formatDate = (dateString: string) => {
        const date = new Date(dateString);
        return date.toLocaleDateString('zh-CN');
    };

    const truncateText = (text: string, maxLength: number) => {
        if (text.length <= maxLength) return text;
        return text.substring(0, maxLength) + '...';
    };

    if (loading) {
        return (
            <Card>
                <CardContent className="py-4">
                    <div className="text-center text-gray-500">加载中...</div>
                </CardContent>
            </Card>
        );
    }

    if (articles.length === 0) {
        return null;
    }

    return (
        <Card>
            {title && (
                <CardHeader>
                    <CardTitle className="text-lg">{title}</CardTitle>
                </CardHeader>
            )}
            <CardContent>
                <div className="space-y-4">
                    {articles.map((article) => (
                        <Link
                            key={article.id}
                            href={`/articles/detail?id=${article.id}`}
                            className="block group"
                        >
                            <div className="flex gap-3">
                                {/* 缩略图 */}
                                {config.show_thumbnail && article.cover_image && (
                                    <div className="flex-shrink-0 w-20 h-20 rounded overflow-hidden">
                                        <Image
                                            src={article.cover_image}
                                            alt={article.title}
                                            width={80}
                                            height={80}
                                            className="w-full h-full object-cover group-hover:scale-110 transition-transform"
                                        />
                                    </div>
                                )}

                                {/* 文章信息 */}
                                <div className="flex-1 min-w-0">
                                    <h3 className="font-medium text-gray-900 dark:text-white group-hover:text-blue-600 line-clamp-2 mb-1">
                                        {article.title}
                                    </h3>

                                    {/* 日期 */}
                                    {config.show_date && (
                                        <div className="text-xs text-gray-500 mb-1">
                                            {formatDate(article.created_at)}
                                        </div>
                                    )}

                                    {/* 摘要 */}
                                    {config.show_excerpt && article.excerpt && (
                                        <p className="text-sm text-gray-600 dark:text-gray-400 line-clamp-2">
                                            {truncateText(article.excerpt, config.excerpt_length || 100)}
                                        </p>
                                    )}
                                </div>
                            </div>
                        </Link>
                    ))}
                </div>
            </CardContent>
        </Card>
    );
};

export default RecentPostsWidget;
