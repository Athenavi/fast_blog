'use client';

import React, {useEffect, useState, useCallback} from 'react';
import {useRouter} from 'next/navigation';
import Image from 'next/image';
import {CategoryService} from '@/lib/api';
import type {Category} from '@/lib/api/base-types';
import Link from 'next/link';
import {
    Bell,
    BellOff,
    Search,
    Filter,
    ChevronRight,
    FileText,
    Users,
    TrendingUp,
    Loader2
} from 'lucide-react';

interface CategoryWithStats extends Category {
    subscription_count: number;
    article_count?: number;
    cover_image?: string;
    color?: string;
}

interface Pagination {
    has_prev: boolean;
    has_next: boolean;
    current_page: number;
    total_pages: number;
    per_page: number;
    total: number;
}

// 骨架屏组件
const CategoryCardSkeleton = () => (
    <div
        className="bg-white dark:bg-gray-800 rounded-2xl shadow-sm border border-gray-100 dark:border-gray-700 overflow-hidden animate-pulse">
        <div className="h-48 bg-gray-200 dark:bg-gray-700"/>
        <div className="p-6 space-y-4">
            <div className="h-6 bg-gray-200 dark:bg-gray-700 rounded w-3/4"/>
            <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-full"/>
            <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-2/3"/>
            <div className="flex justify-between pt-4">
                <div className="h-10 bg-gray-200 dark:bg-gray-700 rounded-lg w-24"/>
                <div className="h-10 bg-gray-200 dark:bg-gray-700 rounded-lg w-20"/>
            </div>
        </div>
    </div>
);

// 分类卡片组件
const CategoryCard: React.FC<{
    category: CategoryWithStats;
    isSubscribed: boolean;
    onSubscribe: (id: number) => void;
    onUnsubscribe: (id: number) => void;
    processing: boolean;
}> = React.memo(({category, isSubscribed, onSubscribe, onUnsubscribe, processing}) => {
    const router = useRouter();

    // 生成渐变色（如果没有预设颜色）
    const getGradientColor = (name: string) => {
        const colors = [
            'from-blue-500 to-cyan-500',
            'from-purple-500 to-pink-500',
            'from-green-500 to-emerald-500',
            'from-orange-500 to-red-500',
            'from-indigo-500 to-purple-500',
            'from-teal-500 to-blue-500',
        ];
        const index = name.length % colors.length;
        return colors[index];
    };

    const gradientColor = category.color || getGradientColor(category.name);

    return (
        <div
            className="group bg-white dark:bg-gray-800 rounded-2xl shadow-sm hover:shadow-xl transition-all duration-300 border border-gray-100 dark:border-gray-700 overflow-hidden cursor-pointer"
            onClick={() => router.push(`/category/detail?name=${encodeURIComponent(category.name)}`)}
        >
            {/* 封面图或渐变色背景 */}
            <div className="relative h-48 overflow-hidden">
                {category.cover_image ? (
                    <Image
                        src={category.cover_image}
                        alt={category.name}
                        fill
                        className="object-cover group-hover:scale-110 transition-transform duration-500"
                        sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw"
                    />
                ) : (
                    <div
                        className={`w-full h-full bg-gradient-to-br ${gradientColor} flex items-center justify-center`}>
                        <FileText className="w-16 h-16 text-white/80"/>
                    </div>
                )}

                {/* 悬浮遮罩 */}
                <div className="absolute inset-0 bg-black/0 group-hover:bg-black/20 transition-colors duration-300"/>
            </div>

            {/* 内容区 */}
            <div className="p-6">
                {/* 分类名称 */}
                <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-2 line-clamp-1 group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">
                    {category.name}
                </h3>

                {/* 描述 */}
                {category.description && (
                    <p className="text-gray-600 dark:text-gray-400 text-sm mb-4 line-clamp-2">
                        {category.description}
                    </p>
                )}

                {/* 统计信息 */}
                <div className="flex items-center gap-4 text-sm text-gray-500 dark:text-gray-400 mb-5">
                    <Link href="/my/posts"
                          className="flex items-center gap-1.5 hover:text-blue-600 dark:hover:text-blue-400 transition-colors">
                        <FileText className="w-4 h-4"/>
                        <span>{category.article_count || 0} 文章</span>
                    </Link>
                    <div className="flex items-center gap-1.5">
                        <Users className="w-4 h-4"/>
                        <span>{category.subscription_count || 0} 订阅</span>
                    </div>
                </div>

                {/* 操作按钮 */}
                <div className="flex items-center justify-between pt-4 border-t border-gray-100 dark:border-gray-700">
                    {isSubscribed ? (
                        <button
                            onClick={(e) => {
                                e.stopPropagation();
                                onUnsubscribe(category.id!);
                            }}
                            disabled={processing}
                            className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors disabled:opacity-50"
                        >
                            {processing ? (
                                <Loader2 className="w-4 h-4 animate-spin"/>
                            ) : (
                                <BellOff className="w-4 h-4"/>
                            )}
                            <span className="hidden sm:inline">取消订阅</span>
                        </button>
                    ) : (
                        <button
                            onClick={(e) => {
                                e.stopPropagation();
                                onSubscribe(category.id!);
                            }}
                            disabled={processing}
                            className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-blue-600 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded-lg transition-colors disabled:opacity-50"
                        >
                            {processing ? (
                                <Loader2 className="w-4 h-4 animate-spin"/>
                            ) : (
                                <Bell className="w-4 h-4"/>
                            )}
                            <span className="hidden sm:inline">订阅</span>
                        </button>
                    )}

                    <div
                        className="flex items-center gap-1 text-blue-600 dark:text-blue-400 opacity-0 group-hover:opacity-100 transition-opacity">
                        <span className="text-sm font-medium">查看详情</span>
                        <ChevronRight className="w-4 h-4 group-hover:translate-x-1 transition-transform"/>
                    </div>
                </div>
            </div>
        </div>
    );
});

CategoryCard.displayName = 'CategoryCard';

// 主页面组件
const CategoriesPage: React.FC = () => {
    const router = useRouter();
    const [categories, setCategories] = useState<CategoryWithStats[]>([]);
    const [pagination, setPagination] = useState<Pagination>({
        has_prev: false,
        has_next: false,
        current_page: 1,
        total_pages: 1,
        per_page: 12,
        total: 0
    });
    const [searchQuery, setSearchQuery] = useState('');
    const [sortBy, setSortBy] = useState('name');
    const [subscribedIds, setSubscribedIds] = useState<number[]>([]);
    const [processingIds, setProcessingIds] = useState<Set<number>>(new Set());
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    // 加载分类数据
    const loadCategories = useCallback(async (page = 1) => {
        setLoading(true);
        setError(null);

        try {
            const response = await CategoryService.getCategories({
                page,
                per_page: 12,
                search: searchQuery,
                sort_by: sortBy
            });

            if (response.success && response.data) {
                const categoriesWithStats: CategoryWithStats[] = (response.data.categories || []).map((cat: Category) => ({
                    ...cat,
                    subscription_count: cat.subscription_count ?? 0,
                    article_count: cat.article_count ?? 0
                }));
                setCategories(categoriesWithStats);

                if ((response.data as any).subscribed_ids) {
                    setSubscribedIds((response.data as any).subscribed_ids);
                }

                setPagination({
                    has_prev: (response.data as any).pagination?.has_prev || page > 1,
                    has_next: (response.data as any).pagination?.has_next || false,
                    current_page: (response.data as any).pagination?.current_page || page,
                    total_pages: (response.data as any).pagination?.total_pages || 1,
                    per_page: (response.data as any).pagination?.per_page || 12,
                    total: (response.data as any).pagination?.total || 0
                });
            } else {
                setError(response.error || '获取分类列表失败');
                setCategories([]);
            }
        } catch (err) {
            console.error('加载分类时出错:', err);
            setError(err instanceof Error ? err.message : '加载分类时发生错误');
        } finally {
            setLoading(false);
        }
    }, [searchQuery, sortBy]);

    useEffect(() => {
        loadCategories(1);
    }, [loadCategories]);

    // 订阅分类
    const handleSubscribe = async (categoryId: number) => {
        setProcessingIds(prev => new Set(prev).add(categoryId));

        try {
            const response = await CategoryService.subscribeToCategory(categoryId);

            if (response.success) {
                setSubscribedIds(prev => [...prev, categoryId]);
                setCategories(prev =>
                    prev.map(cat =>
                        cat.id === categoryId
                            ? {...cat, subscription_count: (cat.subscription_count || 0) + 1}
                            : cat
                    )
                );
            }
        } catch (err) {
            console.error('订阅失败:', err);
        } finally {
            setProcessingIds(prev => {
                const next = new Set(prev);
                next.delete(categoryId);
                return next;
            });
        }
    };

    // 取消订阅
    const handleUnsubscribe = async (categoryId: number) => {
        setProcessingIds(prev => new Set(prev).add(categoryId));

        try {
            const response = await CategoryService.unsubscribeFromCategory(categoryId);

            if (response.success) {
                setSubscribedIds(prev => prev.filter(id => id !== categoryId));
                setCategories(prev =>
                    prev.map(cat =>
                        cat.id === categoryId
                            ? {...cat, subscription_count: Math.max(0, (cat.subscription_count || 1) - 1)}
                            : cat
                    )
                );
            }
        } catch (err) {
            console.error('取消订阅失败:', err);
        } finally {
            setProcessingIds(prev => {
                const next = new Set(prev);
                next.delete(categoryId);
                return next;
            });
        }
    };

    // 搜索处理
    const handleSearch = (e: React.FormEvent) => {
        e.preventDefault();
        loadCategories(1);
    };

    return (
        <div className="min-h-screen bg-gray-50 dark:bg-gray-950">
            {/* 头部区域 */}
            <header className="bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-800">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
                    <div className="text-center max-w-3xl mx-auto">
                        <h1 className="text-4xl sm:text-5xl font-bold text-gray-900 dark:text-white mb-4">
                            探索分类
                        </h1>
                        <p className="text-lg text-gray-600 dark:text-gray-400">
                            发现你感兴趣的内容，订阅喜欢的分类，不错过任何精彩文章
                        </p>
                    </div>
                </div>
            </header>

            <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                {/* 搜索和筛选栏 */}
                <div
                    className="mb-8 bg-white dark:bg-gray-900 rounded-2xl shadow-sm border border-gray-200 dark:border-gray-800 p-6">
                    <form onSubmit={handleSearch} className="flex flex-col sm:flex-row gap-4">
                        <div className="flex-1 relative">
                            <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400 w-5 h-5"/>
                            <input
                                type="text"
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                                placeholder="搜索分类..."
                                className="w-full pl-12 pr-4 py-3 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white transition-all"
                            />
                        </div>

                        <div className="flex gap-3">
                            <div className="relative">
                                <Filter className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 w-5 h-5"/>
                                <select
                                    value={sortBy}
                                    onChange={(e) => setSortBy(e.target.value)}
                                    className="pl-10 pr-10 py-3 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white appearance-none cursor-pointer"
                                >
                                    <option value="name">按名称</option>
                                    <option value="subscriptions">按订阅数</option>
                                    <option value="articles">按文章数</option>
                                    <option value="created_at">按创建时间</option>
                                </select>
                                <ChevronRight
                                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 w-4 h-4 rotate-90 pointer-events-none"/>
                            </div>

                            <button
                                type="submit"
                                className="px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-xl transition-colors"
                            >
                                搜索
                            </button>
                        </div>
                    </form>
                </div>

                {/* 统计信息 */}
                {!loading && !error && (
                    <div className="mb-6 flex items-center justify-between text-sm text-gray-600 dark:text-gray-400">
                        <span>共 {pagination.total} 个分类</span>
                        {subscribedIds.length > 0 && (
                            <span className="flex items-center gap-1.5">
                                <TrendingUp className="w-4 h-4"/>
                                已订阅 {subscribedIds.length} 个
                            </span>
                        )}
                    </div>
                )}

                {/* 错误提示 */}
                {error && (
                    <div
                        className="mb-6 p-6 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-2xl">
                        <p className="text-red-600 dark:text-red-400">{error}</p>
                        <button
                            onClick={() => loadCategories(pagination.current_page)}
                            className="mt-3 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors"
                        >
                            重试
                        </button>
                    </div>
                )}

                {/* 分类网格 */}
                {loading ? (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
                        {Array.from({length: 8}).map((_, i) => (
                            <CategoryCardSkeleton key={i}/>
                        ))}
                    </div>
                ) : categories.length > 0 ? (
                    <>
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
                            {categories.map((category) => (
                                <CategoryCard
                                    key={category.id}
                                    category={category}
                                    isSubscribed={subscribedIds.includes(category.id!)}
                                    onSubscribe={handleSubscribe}
                                    onUnsubscribe={handleUnsubscribe}
                                    processing={processingIds.has(category.id!)}
                                />
                            ))}
                        </div>

                        {/* 分页 */}
                        {pagination.total_pages > 1 && (
                            <div className="mt-12 flex items-center justify-center gap-2">
                                <button
                                    onClick={() => loadCategories(pagination.current_page - 1)}
                                    disabled={!pagination.has_prev}
                                    className="px-4 py-2 border border-gray-200 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                                >
                                    上一页
                                </button>

                                <span className="px-4 py-2 text-sm text-gray-600 dark:text-gray-400">
                                    第 {pagination.current_page} / {pagination.total_pages} 页
                                </span>

                                <button
                                    onClick={() => loadCategories(pagination.current_page + 1)}
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
                    <div className="text-center py-20">
                        <div
                            className="inline-flex items-center justify-center w-20 h-20 bg-gray-100 dark:bg-gray-800 rounded-2xl mb-6">
                            <FileText className="w-10 h-10 text-gray-400"/>
                        </div>
                        <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">暂无分类</h3>
                        <p className="text-gray-600 dark:text-gray-400 mb-6">当前还没有可用的分类</p>
                        <button
                            onClick={() => loadCategories(1)}
                            className="px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-xl transition-colors"
                        >
                            刷新
                        </button>
                    </div>
                )}
            </main>
        </div>
    );
};

export default CategoriesPage;
