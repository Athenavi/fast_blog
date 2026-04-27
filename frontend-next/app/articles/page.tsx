'use client';

import React, {Suspense, useEffect, useState} from 'react';
import {useRouter, useSearchParams} from 'next/navigation';
import type {Article, Pagination} from '@/lib/api';
import {ArticleService} from '@/lib/api';
import Link from 'next/link';
import {
    BookOpen,
    Calendar,
    ChevronLeft,
    ChevronRight,
    Eye,
    FileText,
    Grid3x3,
    Heart,
    List,
    Search,
    Tag
} from 'lucide-react';

interface ArticlesPageData {
    articles: Article[];
    pagination: Pagination;
    total: number;
}

// 文章内容组件 - 使用 useSearchParams
const ArticlesContent = () => {
    const router = useRouter();
    const searchParams = useSearchParams();

    // 从 URL 参数获取分页和筛选信息
    const page = parseInt(searchParams.get('page') || '1');
    const perPage = parseInt(searchParams.get('per_page') || '12');
    const searchQuery = searchParams.get('search') || '';
    const categoryId = searchParams.get('category_id');
    const viewModeParam = searchParams.get('view');
    const viewMode: 'grid' | 'list' = (viewModeParam === 'list' ? 'list' : 'grid'); // grid or list

    const [data, setData] = useState<ArticlesPageData | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    // 获取文章列表
    useEffect(() => {
        const fetchArticles = async () => {
            setLoading(true);
            setError(null);

            try {
                const params: Record<string, string | number> = {
                    page,
                    per_page: perPage,
                };

                if (searchQuery) {
                    params.search = searchQuery;
                }

                if (categoryId) {
                    params.category_id = parseInt(categoryId);
                }

                console.log('🚀 请求参数:', params);
                const result = await ArticleService.getArticles(params);
                console.log('📦 API 返回结果:', result);
                console.log('🔍 result.data:', result.data);
                console.log('🔍 result.pagination:', result.pagination);

                // 判断数据格式：可能是 { data: [], pagination: {} } 或者 data 字段包含所有
                let articlesData: Article[] = [];
                let paginationData: any;

                if (result.data && Array.isArray(result.data)) {
                    // 情况 1: result.data 直接是数组（后端标准格式）
                    console.log('✅ 使用格式 1: result.data 是数组');
                    articlesData = result.data;
                    paginationData = result.pagination;
                } else if (result.data && typeof result.data === 'object' && 'data' in result.data) {
                    // 情况 2: result.data.data 是数组（嵌套格式）
                    console.log('⚠️ 使用格式 2: result.data.data 是数组');
                    articlesData = (result.data as any).data || [];
                    paginationData = (result.data as any).pagination || result.pagination;
                }

                console.log('📄 文章数据:', articlesData);
                console.log('📊 分页数据:', paginationData);

                if (result.success && articlesData) {
                    console.log('✅ 准备设置的文章数量:', articlesData.length);

                    setData({
                        articles: articlesData,
                        pagination: paginationData || {
                            current_page: page,
                            total_pages: 1,
                            has_next: false,
                            has_prev: false,
                            per_page: perPage,
                            total: 0
                        },
                        total: paginationData?.total || 0
                    });
                } else {
                    console.error('❌ API 返回失败:', result);
                    setError(result.error || '获取文章列表失败');
                }
            } catch (err) {
                console.error('获取文章列表失败:', err);
                setError('加载失败，请刷新重试');
            } finally {
                setLoading(false);
            }
        };

        fetchArticles();
    }, [page, perPage, searchQuery, categoryId]);

    // 更新 URL 参数
    const updateUrlParams = (newParams: Record<string, string | number | null>) => {
        const params = new URLSearchParams(searchParams.toString());

        Object.entries(newParams).forEach(([key, value]) => {
            if (value === null || value === undefined) {
                params.delete(key);
            } else {
                params.set(key, String(value));
            }
        });

        router.push(`/articles?${params.toString()}`, {scroll: false});
    };

    // 处理分页
    const handlePageChange = (newPage: number) => {
        updateUrlParams({page: newPage});
        window.scrollTo({top: 0, behavior: 'smooth'});
    };

    // 处理搜索
    const handleSearch = (e: React.FormEvent<HTMLFormElement>) => {
        e.preventDefault();
        const formData = new FormData(e.currentTarget);
        const search = formData.get('search') as string;
        updateUrlParams({search: search || null, page: 1});
    };

    // 切换视图模式
    const toggleViewMode = () => {
        updateUrlParams({view: viewMode === 'grid' ? 'list' : 'grid'});
    };

    // 渲染加载中状态
    if (loading) {
        return (
            <div
                className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800 flex items-center justify-center">
                <div className="text-center">
                    <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-blue-600 mx-auto mb-4"></div>
                    <p className="text-gray-600 dark:text-gray-400">加载文章中...</p>
                </div>
            </div>
        );
    }

    // 渲染错误状态
    if (error) {
        return (
            <div
                className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800 flex items-center justify-center">
                <div className="text-center max-w-md px-4">
                    <div className="text-6xl mb-4">⚠️</div>
                    <h2 className="text-2xl font-bold text-gray-800 dark:text-gray-200 mb-2">加载失败</h2>
                    <p className="text-gray-600 dark:text-gray-400 mb-6">{error}</p>
                    <button
                        onClick={() => router.refresh()}
                        className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                    >
                        重新加载
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800">
            {/* 顶部导航栏 */}
            <header className="bg-white dark:bg-gray-800 shadow-sm sticky top-0 z-50">
                <div className="container mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="flex items-center justify-between h-16">
                        <Link href="/"
                              className="flex items-center gap-2 text-xl font-bold text-blue-600 dark:text-blue-400">
                            <BookOpen className="w-6 h-6"/>
                            <span>FastBlog</span>
                        </Link>

                        <nav className="flex items-center gap-6">
                            <Link href="/"
                                  className="text-gray-600 dark:text-gray-300 hover:text-blue-600 dark:hover:text-blue-400 transition-colors">
                                首页
                            </Link>
                            <Link href="/categories"
                                  className="text-gray-600 dark:text-gray-300 hover:text-blue-600 dark:hover:text-blue-400 transition-colors">
                                分类
                            </Link>
                            <Link href="/about"
                                  className="text-gray-600 dark:text-gray-300 hover:text-blue-600 dark:hover:text-blue-400 transition-colors">
                                关于
                            </Link>
                        </nav>
                    </div>
                </div>
            </header>

            {/* 主要内容区域 */}
            <main className="container mx-auto px-4 sm:px-6 lg:px-8 py-8">
                {/* 页面标题和统计 */}
                <div className="mb-8">
                    <h1 className="text-4xl font-bold text-gray-900 dark:text-white mb-2">
                        文章列表
                    </h1>
                    <p className="text-gray-600 dark:text-gray-400">
                        共 {data?.total || 0} 篇文章
                    </p>
                </div>

                {/* 搜索和筛选工具栏 */}
                <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm p-6 mb-8">
                    <div className="flex flex-col md:flex-row gap-4 items-center justify-between">
                        {/* 搜索表单 */}
                        <form onSubmit={handleSearch} className="flex-1 w-full md:max-w-xl">
                            <div className="relative">
                                <input
                                    type="text"
                                    name="search"
                                    defaultValue={searchQuery}
                                    placeholder="搜索文章标题或摘要..."
                                    className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                                />
                                <Search
                                    className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400"/>
                            </div>
                        </form>

                        {/* 视图切换按钮 */}
                        <div className="flex items-center gap-2">
                            <button
                                onClick={toggleViewMode}
                                className="p-2 rounded-lg border border-gray-300 dark:border-gray-600 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                                title={viewMode === 'grid' ? '切换到列表视图' : '切换到网格视图'}
                            >
                                {viewMode === 'grid' ? (
                                    <List className="w-5 h-5 text-gray-600 dark:text-gray-400"/>
                                ) : (
                                    <Grid3x3 className="w-5 h-5 text-gray-600 dark:text-gray-400"/>
                                )}
                            </button>
                        </div>
                    </div>
                </div>

                {/* 文章列表 */}
                {data && data.articles.length === 0 ? (
                    <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm p-12 text-center">
                        <FileText className="w-16 h-16 text-gray-400 mx-auto mb-4"/>
                        <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
                            暂无文章
                        </h3>
                        <p className="text-gray-600 dark:text-gray-400 mb-6">
                            还没有符合条件的文章
                        </p>
                        <button
                            onClick={() => updateUrlParams({search: null, category_id: null, page: 1})}
                            className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                        >
                            清除筛选条件
                        </button>
                    </div>
                ) : (
                    <>
                        {/* 网格视图 */}
                        {viewMode === 'grid' && (
                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                                {data!.articles.map((article, index) => (
                                    <article
                                        key={article.id}
                                        className="bg-white dark:bg-gray-800 rounded-xl shadow-sm overflow-hidden hover:shadow-lg transition-all duration-300 group"
                                    >
                                        {/* 封面图片 */}
                                        {article.cover_image ? (
                                            <Link href={`/blog/detail?slug=${article.slug}`}
                                                  className="block overflow-hidden">
                                                <div className="relative aspect-video">
                                                    <img
                                                        src={article.cover_image}
                                                        alt={article.title}
                                                        className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                                                        onError={(e) => {
                                                            const target = e.target as HTMLImageElement;
                                                            // 隐藏失败的图片
                                                            target.style.display = 'none';
                                                            // 显示占位符
                                                            const placeholder = target.nextElementSibling as HTMLElement;
                                                            if (placeholder) {
                                                                placeholder.style.display = 'flex';
                                                            }
                                                        }}
                                                    />
                                                    {/* 占位符 - 默认隐藏，图片加载失败时显示 */}
                                                    <div
                                                        className="absolute inset-0 bg-gradient-to-br from-blue-100 to-indigo-100 dark:from-gray-700 dark:to-gray-800 flex items-center justify-center"
                                                        style={{display: 'none'}}
                                                    >
                                                        <FileText className="w-16 h-16 text-gray-400"/>
                                                    </div>
                                                </div>
                                            </Link>
                                        ) : (
                                            /* 没有封面图时显示占位图 */
                                            <Link href={`/blog/detail?slug=${article.slug}`}
                                                  className="block overflow-hidden">
                                                <div
                                                    className="relative aspect-video bg-gradient-to-br from-blue-100 to-indigo-100 dark:from-gray-700 dark:to-gray-800 flex items-center justify-center">
                                                    <FileText className="w-16 h-16 text-gray-400"/>
                                                </div>
                                            </Link>
                                        )}

                                        {/* 文章内容 */}
                                        <div className="p-6">
                                            <Link href={`/blog/detail?slug=${article.slug}`}>
                                                <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-3 line-clamp-2 group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">
                                                    {article.title}
                                                </h2>
                                            </Link>

                                            <p className="text-gray-600 dark:text-gray-400 mb-4 line-clamp-3">
                                                {article.excerpt || '暂无摘要'}
                                            </p>

                                            {/* 元信息 */}
                                            <div
                                                className="flex items-center gap-4 text-sm text-gray-500 dark:text-gray-400 mb-4">
                                                <div className="flex items-center gap-1">
                                                    <Calendar className="w-4 h-4"/>
                                                    <span>
                            {new Date(article.created_at || '').toLocaleDateString('zh-CN')}
                          </span>
                                                </div>
                                                <div className="flex items-center gap-1">
                                                    <Eye className="w-4 h-4"/>
                                                    <span>{article.views || 0}</span>
                                                </div>
                                                <div className="flex items-center gap-1">
                                                    <Heart className="w-4 h-4"/>
                                                    <span>{article.likes || 0}</span>
                                                </div>
                                            </div>

                                            {/* 标签和分类 */}
                                            {article.tags && Array.isArray(article.tags) && article.tags.length > 0 && (
                                                <div className="flex flex-wrap gap-2">
                                                    {article.tags.slice(0, 3).map((tag, idx) => (
                                                        <span
                                                            key={idx}
                                                            className="px-2 py-1 bg-blue-100 dark:bg-blue-900 text-blue-600 dark:text-blue-300 text-xs rounded-md"
                                                        >
                              #{tag.trim()}
                            </span>
                                                    ))}
                                                </div>
                                            )}
                                        </div>
                                    </article>
                                ))}
                            </div>
                        )}

                        {/* 列表视图 */}
                        {viewMode === 'list' && (
                            <div className="space-y-4">
                                {data!.articles.map((article) => (
                                    <article
                                        key={article.id}
                                        className="bg-white dark:bg-gray-800 rounded-xl shadow-sm overflow-hidden hover:shadow-md transition-all duration-300 group"
                                    >
                                        <div className="flex flex-col md:flex-row gap-6 p-6">
                                            {/* 封面图片 */}
                                            {article.cover_image ? (
                                                <Link href={`/blog/detail?slug=${article.slug}`}
                                                      className="md:w-64 flex-shrink-0">
                                                    <div
                                                        className="relative aspect-video md:aspect-[4/3] overflow-hidden rounded-lg">
                                                        <img
                                                            src={article.cover_image}
                                                            alt={article.title}
                                                            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                                                            onError={(e) => {
                                                                const target = e.target as HTMLImageElement;
                                                                // 隐藏失败的图片
                                                                target.style.display = 'none';
                                                                // 显示占位符
                                                                const placeholder = target.nextElementSibling as HTMLElement;
                                                                if (placeholder) {
                                                                    placeholder.style.display = 'flex';
                                                                }
                                                            }}
                                                        />
                                                        {/* 占位符 - 默认隐藏，图片加载失败时显示 */}
                                                        <div
                                                            className="absolute inset-0 bg-gradient-to-br from-blue-100 to-indigo-100 dark:from-gray-700 dark:to-gray-800 flex items-center justify-center"
                                                            style={{display: 'none'}}
                                                        >
                                                            <FileText className="w-12 h-12 text-gray-400"/>
                                                        </div>
                                                    </div>
                                                </Link>
                                            ) : (
                                                /* 没有封面图时显示占位图 */
                                                <div className="md:w-64 flex-shrink-0">
                                                    <div
                                                        className="relative aspect-video md:aspect-[4/3] bg-gradient-to-br from-blue-100 to-indigo-100 dark:from-gray-700 dark:to-gray-800 rounded-lg flex items-center justify-center">
                                                        <FileText className="w-12 h-12 text-gray-400"/>
                                                    </div>
                                                </div>
                                            )}

                                            {/* 文章内容 */}
                                            <div className="flex-1">
                                                <Link href={`/blog/detail?slug=${article.slug}`}>
                                                    <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-3 group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">
                                                        {article.title}
                                                    </h2>
                                                </Link>

                                                <p className="text-gray-600 dark:text-gray-400 mb-4 line-clamp-2">
                                                    {article.excerpt || '暂无摘要'}
                                                </p>

                                                {/* 元信息 */}
                                                <div
                                                    className="flex items-center gap-6 text-sm text-gray-500 dark:text-gray-400">
                                                    <div className="flex items-center gap-1">
                                                        <Calendar className="w-4 h-4"/>
                                                        <span>
                              {new Date(article.created_at || '').toLocaleDateString('zh-CN')}
                            </span>
                                                    </div>
                                                    <div className="flex items-center gap-1">
                                                        <Eye className="w-4 h-4"/>
                                                        <span>{article.views || 0} 阅读</span>
                                                    </div>
                                                    <div className="flex items-center gap-1">
                                                        <Heart className="w-4 h-4"/>
                                                        <span>{article.likes || 0} 点赞</span>
                                                    </div>
                                                    {article.tags && Array.isArray(article.tags) && (
                                                        <div className="flex items-center gap-1">
                                                            <Tag className="w-4 h-4"/>
                                                            <span>{article.tags.length} 标签</span>
                                                        </div>
                                                    )}
                                                </div>
                                            </div>
                                        </div>
                                    </article>
                                ))}
                            </div>
                        )}

                        {/* 分页 */}
                        {data && (data.pagination.total_pages ?? 1) > 1 && (
                            <div className="mt-12 flex justify-center">
                                <nav className="flex items-center gap-2">
                                    <button
                                        onClick={() => handlePageChange(page - 1)}
                                        disabled={!data.pagination.has_prev}
                                        className="px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                                    >
                                        <ChevronLeft className="w-5 h-5"/>
                                    </button>

                                    {Array.from({length: Math.min(5, data.pagination.total_pages ?? 1)}, (_, i) => {
                                        let pageNum;
                                        const totalPages = data.pagination.total_pages ?? 1;
                                        if (totalPages <= 5) {
                                            pageNum = i + 1;
                                        } else if (page <= 3) {
                                            pageNum = i + 1;
                                        } else if (page >= totalPages - 2) {
                                            pageNum = totalPages - 4 + i;
                                        } else {
                                            pageNum = page - 2 + i;
                                        }

                                        return (
                                            <button
                                                key={pageNum}
                                                onClick={() => handlePageChange(pageNum)}
                                                className={`px-4 py-2 rounded-lg transition-colors ${
                                                    pageNum === page
                                                        ? 'bg-blue-600 text-white'
                                                        : 'border border-gray-300 dark:border-gray-600 hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300'
                                                }`}
                                            >
                                                {pageNum}
                                            </button>
                                        );
                                    })}

                                    <button
                                        onClick={() => handlePageChange(page + 1)}
                                        disabled={!data.pagination.has_next}
                                        className="px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                                    >
                                        <ChevronRight className="w-5 h-5"/>
                                    </button>
                                </nav>
                            </div>
                        )}
                    </>
                )}
            </main>
        </div>
    );
};

// 主页面组件 - 包裹 Suspense boundary
const ArticlesPage = () => {
    return (
        <Suspense fallback={
            <div
                className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800 flex items-center justify-center">
                <div className="text-center">
                    <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-blue-600 mx-auto mb-4"></div>
                    <p className="text-gray-600 dark:text-gray-400">加载中...</p>
                </div>
            </div>
        }>
            <ArticlesContent/>
        </Suspense>
    );
};

export default ArticlesPage;
