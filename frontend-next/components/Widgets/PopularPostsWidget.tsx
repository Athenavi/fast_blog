/**
 * 热门文章 Widget
 * 显示浏览量最高的文章
 */

'use client';

import React, {useEffect, useState} from 'react';
import Link from 'next/link';
import Image from 'next/image';
import {Card, CardContent, CardHeader, CardTitle} from '@/components/ui/card';
import apiClient from '@/lib/api-client';
import {Flame} from 'lucide-react';

interface Article {
    id: number;
    title: string;
    slug: string;
    cover_image?: string;
    views: number;
    created_at: string;
}

interface PopularPostsWidgetProps {
    widgetId: number;
    title: string;
    config: {
        count?: number;
        period?: 'day' | 'week' | 'month' | 'all';
        show_thumbnail?: boolean;
        show_views?: boolean;
    };
}

const PopularPostsWidget: React.FC<PopularPostsWidgetProps> = ({title, config}) => {
    const [articles, setArticles] = useState<Article[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        loadArticles();
    }, []);

    const loadArticles = async () => {
        try {
            const response = await apiClient.get(
                `/api/v1/widgets/data/popular-posts?count=${config.count || 5}&period=${config.period || 'week'}`
            );

            if (response.success && response.data) {
                setArticles((response.data as any).posts || []);
            }
        } catch (error) {
            console.error('Failed to load popular posts:', error);
        } finally {
            setLoading(false);
        }
    };

    const formatViews = (views: number): string => {
        if (views >= 10000) {
            return `${(views / 10000).toFixed(1)}w`;
        }
        if (views >= 1000) {
            return `${(views / 1000).toFixed(1)}k`;
        }
        return views.toString();
    };

    if (loading) {
        return (
            <Card>
                <CardContent className="p-4">
                    <div className="animate-pulse space-y-3">
                        {[...Array(config.count || 5)].map((_, i) => (
                            <div key={i} className="flex gap-3">
                                <div className="h-16 w-16 bg-gray-200 dark:bg-gray-700 rounded"/>
                                <div className="flex-1 space-y-2">
                                    <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-3/4"/>
                                    <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-1/2"/>
                                </div>
                            </div>
                        ))}
                    </div>
                </CardContent>
            </Card>
        );
    }

    if (!articles.length) {
        return null;
    }

    return (
        <Card>
            <CardHeader className="pb-3">
                <CardTitle className="text-lg flex items-center gap-2">
                    <Flame className="w-5 h-5 text-orange-500"/>
                    {title || '热门文章'}
                </CardTitle>
            </CardHeader>
            <CardContent>
                <div className="space-y-3">
                    {articles.map((article, index) => (
                        <Link
                            key={article.id}
                            href={`/article/${article.slug}`}
                            className="group flex gap-3 hover:bg-gray-50 dark:hover:bg-gray-800 p-2 rounded transition-colors"
                        >
                            {/* 排名 */}
                            <div className="flex-shrink-0 w-6 h-6 flex items-center justify-center">
                                <span className={`text-sm font-bold ${
                                    index === 0 ? 'text-red-500' :
                                    index === 1 ? 'text-orange-500' :
                                    index === 2 ? 'text-yellow-500' :
                                    'text-gray-400'
                                }`}>
                                    {index + 1}
                                </span>
                            </div>

                            {/* 缩略图 */}
                            {config.show_thumbnail !== false && article.cover_image && (
                                <div className="flex-shrink-0 w-16 h-16 relative rounded overflow-hidden">
                                    <Image
                                        src={article.cover_image}
                                        alt={article.title}
                                        fill
                                        className="object-cover group-hover:scale-110 transition-transform"
                                    />
                                </div>
                            )}

                            {/* 文章信息 */}
                            <div className="flex-1 min-w-0">
                                <h3 className="font-medium text-gray-900 dark:text-white group-hover:text-blue-600 line-clamp-2 mb-1">
                                    {article.title}
                                </h3>

                                {/* 浏览量 */}
                                {config.show_views !== false && (
                                    <div className="text-xs text-gray-500 flex items-center gap-1">
                                        <Flame className="w-3 h-3"/>
                                        {formatViews(article.views)} 次浏览
                                    </div>
                                )}
                            </div>
                        </Link>
                    ))}
                </div>
            </CardContent>
        </Card>
    );
};

export default PopularPostsWidget;
