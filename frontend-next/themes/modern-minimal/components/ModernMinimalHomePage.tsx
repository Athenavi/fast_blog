/**
 * Modern Minimal Theme HomePage Component
 * 现代简约主题首页组件
 */
'use client';

import React from 'react';
import Link from 'next/link';
import {useTheme} from '@/hooks/useTheme';
import {useThemeStyles} from '@/hooks/useThemeStyles';
import ModernMinimalArticleCard from './ModernMinimalArticleCard';

interface Article {
    id: number;
    title: string;
    slug: string;
    excerpt?: string;
    cover_image?: string;
    created_at: string;
    views?: number;
}

interface ModernMinimalHomePageProps {
    featuredArticles?: Article[];
    recentArticles?: Article[];
    popularArticles?: Article[];
}

const ModernMinimalHomePage: React.FC<ModernMinimalHomePageProps> = ({
                                                                         featuredArticles = [],
                                                                         recentArticles = [],
                                                                         popularArticles = [],
                                                                     }) => {
    const {config} = useTheme();
    const themeConfig = config?.config || {};
    const colors = (themeConfig as any).colors || {};
    const features = (themeConfig as any).features || {};

    return (
        <div className="min-h-screen">
            {/* Hero Section */}
            <section
                className="py-16 text-center"
                style={{
                    backgroundColor: colors.muted || '#f3f4f6',
                }}
            >
                <h1
                    className="text-4xl md:text-5xl font-bold mb-4"
                    style={{color: colors.primary || '#3b82f6'}}
                >
                    {config?.metadata?.name || 'Modern Minimal'}
                </h1>
                <p
                    className="text-lg max-w-2xl mx-auto"
                    style={{color: colors.secondary || '#64748b'}}
                >
                    {config?.metadata?.description || '现代简约博客主题'}
                </p>
            </section>

            {/* Featured Articles */}
            {featuredArticles.length > 0 && (
                <section className="py-12 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto">
                    <h2
                        className="text-2xl font-bold mb-8 pb-2 border-b"
                        style={{
                            color: colors.foreground || '#1f2937',
                            borderColor: colors.border || '#e5e7eb',
                        }}
                    >
                        特色文章
                    </h2>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {featuredArticles.map((article, idx) => (
                            article && <ModernMinimalArticleCard key={article.id || idx} article={article}/>
                        ))}
                    </div>
                </section>
            )}

            {/* Recent Articles */}
            {recentArticles.length > 0 && (
                <section className="py-12 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto">
                    <h2
                        className="text-2xl font-bold mb-8 pb-2 border-b"
                        style={{
                            color: colors.foreground || '#1f2937',
                            borderColor: colors.border || '#e5e7eb',
                        }}
                    >
                        最新文章
                    </h2>
                    <div className="space-y-6">
                        {recentArticles.slice(0, 5).map((article, idx) => (
                            article &&
                            <ModernMinimalArticleCard key={article.id || idx} article={article} layout="list"/>
                        ))}
                    </div>

                    {recentArticles.length > 5 && (
                        <div className="mt-8 text-center">
                            <Link
                                href="/articles"
                                className="inline-block px-6 py-3 rounded-lg transition-opacity hover:opacity-80"
                                style={{
                                    backgroundColor: colors.primary || '#3b82f6',
                                    color: '#ffffff',
                                }}
                            >
                                查看更多
                            </Link>
                        </div>
                    )}
                </section>
            )}

            {/* Popular Articles */}
            {popularArticles.length > 0 && (
                <section className="py-12 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto">
                    <h2
                        className="text-2xl font-bold mb-8 pb-2 border-b"
                        style={{
                            color: colors.foreground || '#1f2937',
                            borderColor: colors.border || '#e5e7eb',
                        }}
                    >
                        热门文章
                    </h2>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        {popularArticles.slice(0, 4).map((article, idx) => (
                            article && <ModernMinimalArticleCard key={article.id || idx} article={article}/>
                        ))}
                    </div>
                </section>
            )}
        </div>
    );
};

export default ModernMinimalHomePage;
