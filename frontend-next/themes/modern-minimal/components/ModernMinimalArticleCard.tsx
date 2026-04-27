/**
 * Modern Minimal Theme Article Card Component
 * 现代简约主题文章卡片组件
 */
'use client';

import React from 'react';
import Link from 'next/link';
import {useTheme} from '@/hooks/useTheme';

interface Article {
    id: number;
    title: string;
    slug: string;
    excerpt?: string;
    cover_image?: string;
    created_at: string;
    views?: number;
}

interface ModernMinimalArticleCardProps {
    article: Article;
    layout?: 'card' | 'list';
}

const ModernMinimalArticleCard: React.FC<ModernMinimalArticleCardProps> = ({
                                                                               article,
                                                                               layout = 'card',
                                                                           }) => {
    const {config} = useTheme();
    const themeConfig = config?.config || {};
    const colors = (themeConfig as any).colors || {};
    const features = (themeConfig as any).features || {};

    const formatDate = (dateString: string) => {
        return new Date(dateString).toLocaleDateString('zh-CN', {
            year: 'numeric',
            month: 'long',
            day: 'numeric',
        });
    };

    if (layout === 'list') {
        return (
            <article
                className="border-b pb-6 transition-colors duration-300"
                style={{borderColor: colors.border || '#e5e7eb'}}
            >
                <Link href={`/articles/${article.slug}`} className="group">
                    <h2
                        className="text-xl font-bold mb-2 group-hover:opacity-80 transition-opacity"
                        style={{color: colors.primary || '#3b82f6'}}
                    >
                        {article.title}
                    </h2>
                </Link>

                {article.excerpt && (
                    <p
                        className="mb-3 line-clamp-2"
                        style={{color: colors.foreground || '#1f2937'}}
                    >
                        {article.excerpt}
                    </p>
                )}

                <div
                    className="flex items-center space-x-4 text-sm"
                    style={{color: colors.secondary || '#64748b'}}
                >
                    <time>{formatDate(article.created_at)}</time>
                    {features.showReadingTime && article.views !== undefined && (
                        <>
                            <span>•</span>
                            <span>{article.views} 次阅读</span>
                        </>
                    )}
                </div>
            </article>
        );
    }

    // Card layout
    return (
        <article
            className="rounded-lg overflow-hidden shadow-md hover:shadow-lg transition-all duration-300"
            style={{backgroundColor: colors.background || '#ffffff'}}
        >
            {article.cover_image && (
                <div className="aspect-video overflow-hidden">
                    <img
                        src={article.cover_image}
                        alt={article.title}
                        className="w-full h-full object-cover hover:scale-105 transition-transform duration-300"
                    />
                </div>
            )}

            <div className="p-6">
                <Link href={`/articles/${article.slug}`} className="group">
                    <h2
                        className="text-xl font-bold mb-3 group-hover:opacity-80 transition-opacity line-clamp-2"
                        style={{color: colors.primary || '#3b82f6'}}
                    >
                        {article.title}
                    </h2>
                </Link>

                {article.excerpt && (
                    <p
                        className="mb-4 line-clamp-3"
                        style={{color: colors.foreground || '#1f2937'}}
                    >
                        {article.excerpt}
                    </p>
                )}

                <div
                    className="flex items-center justify-between text-sm"
                    style={{color: colors.secondary || '#64748b'}}
                >
                    <time>{formatDate(article.created_at)}</time>
                    {features.showReadingTime && article.views !== undefined && (
                        <span>{article.views} 次阅读</span>
                    )}
                </div>
            </div>
        </article>
    );
};

export default ModernMinimalArticleCard;
