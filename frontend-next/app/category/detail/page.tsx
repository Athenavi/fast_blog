'use client';

import React, {Suspense, useEffect, useState, useCallback} from 'react';
import {useRouter, useSearchParams} from 'next/navigation';
import Image from 'next/image';
import {CategoryService} from '@/lib/api';
import type {Article, Category} from '@/lib/api/base-types';
import Link from 'next/link';
import {
    ArrowLeft,
    Bell,
    BellOff,
    Calendar,
    Clock,
    Eye,
    Heart,
    Search,
    Filter,
    ChevronRight,
    Loader2,
    FileText,
    Users
} from 'lucide-react';

interface CategoryDetail {
    category: Category;
    articles: Article[];
    pagination: {
        current_page: number;
        total_pages: number;
        has_next: boolean;
        has_prev: boolean;
    };
    total_articles: number;
    subscribed_ids?: number[];
}

// 文章卡片骨架屏
const ArticleCardSkeleton = () => (
    <div
        className="bg-white dark:bg-gray-800 rounded-2xl shadow-sm border border-gray-100 dark:border-gray-700 overflow-hidden animate-pulse">
        <div className="flex flex-col md:flex-row">
            <div className="md:w-64 h-48 md:h-auto bg-gray-200 dark:bg-gray-700"/>
            <div className="flex-1 p-6 space-y-4">
                <div className="h-6 bg-gray-200 dark:bg-gray-700 rounded w-3/4"/>
                <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-full"/>
                <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-2/3"/>
                <div className="flex gap-4 pt-2">
                    <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-24"/>
                    <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-24"/>
                </div>
            </div>
        </div>
    </div>
);

// 文章卡片组件
const ArticleCard: React.FC<{ article: Article }> = React.memo(({article}) => {
    const router = useRouter();

    const formatDate = (dateString?: string) => {
        if (!dateString) return '';
        const date = new Date(dateString);
        const now = new Date();
        const diffDays = Math.floor(Math.abs(now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24));

        if (diffDays === 0) return '今天';
        if (diffDays === 1) return '昨天';
        if (diffDays < 7) return `${diffDays}天前`;
        return date.toLocaleDateString('zh-CN', {month: '2-digit', day: '2-digit'});
    };

    return (
        <article
            className="group bg-white dark:bg-gray-800 rounded-2xl shadow-sm hover:shadow-lg transition-all duration-300 border border-gray-100 dark:border-gray-700 overflow-hidden cursor-pointer"
            onClick={() => router.push(`/blog/detail?slug=${article.slug}`)}
        >
            <div className="flex flex-col md:flex-row">
                {/* 封面图 */}
                {article.cover_image && (
                    <div className="md:w-64 relative overflow-hidden">
                        <Image
                            src={article.cover_image}
                            alt={article.title}
                            width={400}
                            height={300}
                            className="w-full h-48 md:h-full object-cover group-hover:scale-105 transition-transform duration-500"
                        />
                    </div>
                )}

                {/* 内容区 */}
                <div className="flex-1 p-6">
                    <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-3 line-clamp-2 group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">
                        {article.title}
                    </h3>

                    <p className="text-gray-600 dark:text-gray-400 text-sm mb-4 line-clamp-2">
                        {article.excerpt || article.summary || '暂无摘要'}
                    </p>

                    {/* 元数据 */}
                    <div className="flex flex-wrap items-center gap-4 text-sm text-gray-500 dark:text-gray-400">
                        <div className="flex items-center gap-1.5">
                            <Calendar className="w-4 h-4"/>
                            <span>{formatDate(article.created_at)}</span>
                        </div>

                        <div className="flex items-center gap-1.5">
                            <Eye className="w-4 h-4"/>
                            <span>{article.views || 0}</span>
                        </div>

                        <div className="flex items-center gap-1.5">
                            <Heart className="w-4 h-4"/>
                            <span>{article.likes || 0}</span>
                        </div>

                        {article.tags && article.tags.length > 0 && (
                            <div className="flex items-center gap-2">
                                <span
                                    className="px-2 py-1 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 text-xs rounded-full">
                                    {article.tags[0]}
                                </span>
                                {article.tags.length > 1 && (
                                    <span className="text-xs text-gray-400">+{article.tags.length - 1}</span>
                                )}
                            </div>
                        )}
                    </div>

                    {/* 阅读更多提示 */}
                    <div
                        className="mt-4 flex items-center gap-1 text-blue-600 dark:text-blue-400 opacity-0 group-hover:opacity-100 transition-opacity">
                        <span className="text-sm font-medium">阅读全文</span>
                        <ChevronRight className="w-4 h-4 group-hover:translate-x-1 transition-transform"/>
                    </div>
                </div>
            </div>
        </article>
    );
});

ArticleCard.displayName = 'ArticleCard';

// 主内容组件
const CategoryDetailContent: React.FC = () => {
    const searchParams = useSearchParams();
    const router = useRouter();
    const categoryName = searchParams?.get('name') || '';

    const [categoryDetail, setCategoryDetail] = useState<CategoryDetail | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [currentPage, setCurrentPage] = useState(1);
    const [subscribedIds, setSubscribedIds] = useState<number[]>([]);
    const [searchQuery, setSearchQuery] = useState('');
    const [processing, setProcessing] = useState(false);

    // 加载分类详情
    const loadCategoryDetail = useCallback(async (page: number) => {
        setLoading(true);
        setError(null);

        try {
            const response = await CategoryService.getCategoryByName(categoryName);

            if (response.success && response.data) {
                setCategoryDetail(response.data as CategoryDetail);

                if ((response.data as any).subscribed_ids) {
                    setSubscribedIds((response.data as any).subscribed_ids);
                }
            } else {
                setError(response.error || '获取分类详情失败');
            }
        } catch (err) {
            console.error('加载分类详情时出错:', err);
            setError(err instanceof Error ? err.message : '加载失败');
        } finally {
            setLoading(false);
        }
    }, [categoryName]);

    useEffect(() => {
        loadCategoryDetail(currentPage);
    }, [loadCategoryDetail, currentPage]);

    // 订阅/取消订阅
    const handleSubscribe = async () => {
        if (!categoryDetail?.category?.id) return;

        setProcessing(true);
        try {
            const response = await CategoryService.subscribeToCategory(categoryDetail.category.id);

            if (response.success) {
                setSubscribedIds(prev => [...prev, categoryDetail.category.id!]);
                setCategoryDetail(prev => prev ? {
                    ...prev,
                    category: {
                        ...prev.category,
                        subscription_count: (prev.category.subscription_count || 0) + 1
                    }
                } : null);
            }
        } catch (err) {
            console.error('订阅失败:', err);
        } finally {
            setProcessing(false);
        }
    };

    const handleUnsubscribe = async () => {
        if (!categoryDetail?.category?.id) return;

        setProcessing(true);
        try {
            const response = await CategoryService.unsubscribeFromCategory(categoryDetail.category.id);

            if (response.success) {
                setSubscribedIds(prev => prev.filter(id => id !== categoryDetail.category!.id));
                setCategoryDetail(prev => prev ? {
                    ...prev,
                    category: {
                        ...prev.category,
                        subscription_count: Math.max(0, (prev.category.subscription_count || 1) - 1)
                    }
                } : null);
            }
        } catch (err) {
            console.error('取消订阅失败:', err);
        } finally {
            setProcessing(false);
        }
    };

    const isSubscribed = categoryDetail?.category?.id ? subscribedIds.includes(categoryDetail.category.id) : false;

    if (loading) {
        return (
            <div className="min-h-screen bg-gray-50 dark:bg-gray-950 py-12">
                <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
                    {/* 头部骨架屏 */}
                    <div
                        className="bg-white dark:bg-gray-900 rounded-2xl shadow-sm border border-gray-200 dark:border-gray-800 p-8 mb-8 animate-pulse">
                        <div className="h-8 bg-gray-200 dark:bg-gray-700 rounded w-1/3 mb-4"/>
                        <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-2/3 mb-6"/>
                        <div className="flex gap-4">
                            <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-24"/>
                            <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-24"/>
                            <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-24"/>
                        </div>
                    </div>

                    {/* 文章列表骨架屏 */}
                    <div className="space-y-6">
                        {Array.from({length: 3}).map((_, i) => (
                            <ArticleCardSkeleton key={i}/>
                        ))}
                    </div>
                </div>
            </div>
        );
    }

    if (error || !categoryDetail) {
        return (
            <div className="min-h-screen bg-gray-50 dark:bg-gray-950 py-20">
                <div className="max-w-2xl mx-auto px-4 text-center">
                    <div
                        className="bg-white dark:bg-gray-900 rounded-2xl shadow-sm border border-gray-200 dark:border-gray-800 p-12">
                        <FileText className="w-16 h-16 text-gray-400 mx-auto mb-6"/>
                        <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">
                            {error || '未找到该分类'}
                        </h2>
                        <div className="flex justify-center gap-4">
                            <Link
                                href="/categories"
                                className="inline-flex items-center gap-2 px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-xl transition-colors"
                            >
                                <ArrowLeft className="w-4 h-4"/>
                                返回分类列表
                            </Link>
                            <button
                                onClick={() => loadCategoryDetail(currentPage)}
                                className="px-6 py-3 border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800 rounded-xl transition-colors"
                            >
                                重试
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        );
    }

    const {category, articles, pagination, total_articles} = categoryDetail;

    return (
        <div className="min-h-screen bg-gray-50 dark:bg-gray-950">
            {/* 头部区域 */}
            <header className="bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-800">
                <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
                    {/* 返回按钮 */}
                    <Link
                        href="/categories"
                        className="inline-flex items-center gap-2 text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white mb-6 transition-colors group"
                    >
                        <ArrowLeft className="w-4 h-4 group-hover:-translate-x-1 transition-transform"/>
                        返回分类列表
                    </Link>

                    {/* 分类信息 */}
                    <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-6">
                        <div className="flex-1">
                            <h1 className="text-4xl font-bold text-gray-900 dark:text-white mb-4">
                                {category.name}
                            </h1>

                            {category.description && (
                                <p className="text-lg text-gray-600 dark:text-gray-400 mb-6">
                                    {category.description}
                                </p>
                            )}

                            {/* 统计信息 */}
                            <div className="flex flex-wrap items-center gap-6 text-sm">
                                <div className="flex items-center gap-2 text-gray-600 dark:text-gray-400">
                                    <FileText className="w-5 h-5"/>
                                    <span className="font-medium">{total_articles} 篇文章</span>
                                </div>
                                <div className="flex items-center gap-2 text-gray-600 dark:text-gray-400">
                                    <Users className="w-5 h-5"/>
                                    <span className="font-medium">{category.subscription_count || 0} 人订阅</span>
                                </div>
                                {category.created_at && (
                                    <div className="flex items-center gap-2 text-gray-600 dark:text-gray-400">
                                        <Calendar className="w-5 h-5"/>
                                        <span>创建于 {new Date(category.created_at).toLocaleDateString('zh-CN')}</span>
                                    </div>
                                )}
                            </div>
                        </div>

                        {/* 订阅按钮 */}
                        <div>
                            {isSubscribed ? (
                                <button
                                    onClick={handleUnsubscribe}
                                    disabled={processing}
                                    className="flex items-center gap-2 px-6 py-3 bg-red-50 dark:bg-red-900/20 hover:bg-red-100 dark:hover:bg-red-900/30 text-red-600 dark:text-red-400 font-medium rounded-xl transition-colors disabled:opacity-50"
                                >
                                    {processing ? (
                                        <Loader2 className="w-5 h-5 animate-spin"/>
                                    ) : (
                                        <BellOff className="w-5 h-5"/>
                                    )}
                                    取消订阅
                                </button>
                            ) : (
                                <button
                                    onClick={handleSubscribe}
                                    disabled={processing}
                                    className="flex items-center gap-2 px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-xl transition-colors disabled:opacity-50"
                                >
                                    {processing ? (
                                        <Loader2 className="w-5 h-5 animate-spin"/>
                                    ) : (
                                        <Bell className="w-5 h-5"/>
                                    )}
                                    订阅分类
                                </button>
                            )}
                        </div>
                    </div>
                </div>
            </header>

            <main className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                {/* 搜索栏 */}
                <div
                    className="mb-8 bg-white dark:bg-gray-900 rounded-2xl shadow-sm border border-gray-200 dark:border-gray-800 p-6">
                    <div className="flex flex-col sm:flex-row gap-4">
                        <div className="flex-1 relative">
                            <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400 w-5 h-5"/>
                            <input
                                type="text"
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                                placeholder="搜索文章..."
                                className="w-full pl-12 pr-4 py-3 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white transition-all"
                            />
                        </div>

                        <div className="relative">
                            <Filter className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 w-5 h-5"/>
                            <select
                                className="pl-10 pr-10 py-3 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white appearance-none cursor-pointer">
                                <option value="newest">最新发布</option>
                                <option value="popular">最受欢迎</option>
                                <option value="views">最多浏览</option>
                            </select>
                            <ChevronRight
                                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 w-4 h-4 rotate-90 pointer-events-none"/>
                        </div>
                    </div>
                </div>

                {/* 文章列表 */}
                <div className="space-y-6">
                    {articles && articles.length > 0 ? (
                        <>
                            {articles.map((article) => (
                                <ArticleCard key={article.id} article={article}/>
                            ))}

                            {/* 分页 */}
                            {pagination.total_pages > 1 && (
                                <div className="mt-12 flex items-center justify-center gap-2">
                                    <button
                                        onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                                        disabled={!pagination.has_prev}
                                        className="px-4 py-2 border border-gray-200 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                                    >
                                        上一页
                                    </button>

                                    <span className="px-4 py-2 text-sm text-gray-600 dark:text-gray-400">
                                        第 {pagination.current_page} / {pagination.total_pages} 页
                                    </span>

                                    <button
                                        onClick={() => setCurrentPage(p => Math.min(pagination.total_pages, p + 1))}
                                        disabled={!pagination.has_next}
                                        className="px-4 py-2 border border-gray-200 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                                    >
                                        下一页
                                    </button>
                                </div>
                            )}
                        </>
                    ) : (
                        /* 空状态 */
                        <div
                            className="text-center py-20 bg-white dark:bg-gray-900 rounded-2xl shadow-sm border border-gray-200 dark:border-gray-800">
                            <FileText className="w-16 h-16 text-gray-400 mx-auto mb-6"/>
                            <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">暂无文章</h3>
                            <p className="text-gray-600 dark:text-gray-400 mb-6">这个分类下还没有任何文章</p>
                            <Link
                                href="/my/posts/create"
                                className="inline-flex items-center gap-2 px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-xl transition-colors"
                            >
                                创建第一篇文章
                            </Link>
                        </div>
                    )}
                </div>
            </main>
        </div>
    );
};

// 主页面组件 - 用 Suspense 包装
const CategoryDetailPage: React.FC = () => {
    return (
        <Suspense fallback={
            <div className="min-h-screen bg-gray-50 dark:bg-gray-950 py-20">
                <div className="max-w-5xl mx-auto px-4 text-center">
                    <Loader2 className="w-12 h-12 animate-spin text-blue-600 mx-auto mb-4"/>
                    <p className="text-gray-600 dark:text-gray-400">加载中...</p>
                </div>
            </div>
        }>
            <CategoryDetailContent/>
        </Suspense>
    );
};

export default CategoryDetailPage;
