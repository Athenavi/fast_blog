'use client';

import React, {useEffect, useState} from 'react';
import {useParams, useRouter} from 'next/navigation';
import {CategoryService} from '@/lib/api';
import type {Article, Category} from '@/lib/api/base-types';
import Link from 'next/link';
import {
    AlertCircle,
    ArrowLeft,
    Bell,
    BellOff,
    Calendar,
    CheckCircle,
    ChevronLeft,
    ChevronRight,
    Clock,
    Eye,
    FileText,
    Filter,
    Heart,
    Search,
    Tag,
    User,
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
    prev_page?: number;
    next_page?: number;
  };
  total_articles: number;
  description?: string;
  keywords?: string;
}

const CategoryDetailPage = () => {
  const params = useParams<{ name: string }>();
  const router = useRouter();
  const categoryName = decodeURIComponent(params.name || '');

  const [categoryDetail, setCategoryDetail] = useState<CategoryDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [notification, setNotification] = useState<{type: 'success' | 'error', message: string} | null>(null);
  const [subscribedIds, setSubscribedIds] = useState<number[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [sortBy, setSortBy] = useState('newest');

  // 显示通知
  const showNotification = (type: 'success' | 'error', message: string) => {
    setNotification({type, message});
    setTimeout(() => setNotification(null), 4000);
  };

  // 检查是否已订阅分类
  const isSubscribed = (categoryId: number) => {
    return subscribedIds.includes(categoryId);
  };

  // 加载分类详情
  useEffect(() => {
    loadCategoryDetail(currentPage);
  }, [categoryName, currentPage]);

  const loadCategoryDetail = async (page: number) => {
    setLoading(true);
    setError(null);

    try {
      const response = await CategoryService.getCategoryByName(categoryName);

      if (response.success && response.data) {
        setCategoryDetail(response.data as CategoryDetail);

        // 获取用户的订阅状态
        if (response.data.subscribed_ids) {
          setSubscribedIds(response.data.subscribed_ids);
        }
      } else {
        console.error('获取分类详情失败:', response.error);
        setError(response.error || '获取分类详情失败');
      }
    } catch (err) {
      console.error('加载分类详情时出错:', err);
      setError(err instanceof Error ? err.message : '加载分类详情时发生错误');
    } finally {
      setLoading(false);
    }
  };

  const subscribeCategory = async () => {
    if (!categoryDetail?.category?.id) return;

    try {
      const response = await CategoryService.subscribeToCategory(categoryDetail.category.id);

      if (response.success) {
        showNotification('success', '订阅成功！');
        setSubscribedIds(prev => [...prev, categoryDetail.category.id!]);
        // 更新订阅数
        setCategoryDetail(prev => prev ? {
          ...prev,
          category: {
            ...prev.category,
            subscription_count: (prev.category.subscription_count || 0) + 1
          }
        } : null);
      } else {
        if (response.error && response.error.includes('您已经订阅了该分类')) {
          showNotification('error', '您已经订阅了该分类');
        } else {
          showNotification('error', response.error || '订阅失败');
        }
      }
    } catch (err) {
      console.error('订阅分类失败:', err);
      showNotification('error', '订阅分类失败，请稍后再试');
    }
  };

  const unsubscribeCategory = async () => {
    if (!categoryDetail?.category?.id) return;

    try {
      const response = await CategoryService.unsubscribeFromCategory(categoryDetail.category.id);

      if (response.success) {
        showNotification('success', '取消订阅成功！');
        setSubscribedIds(prev => prev.filter(id => id !== categoryDetail.category!.id));
        // 更新订阅数
        setCategoryDetail(prev => prev ? {
          ...prev,
          category: {
            ...prev.category,
            subscription_count: Math.max(0, (prev.category.subscription_count || 1) - 1)
          }
        } : null);
      } else {
        showNotification('error', response.error || '取消订阅失败');
      }
    } catch (err) {
      console.error('取消订阅分类失败:', err);
      showNotification('error', '取消订阅分类失败，请稍后再试');
    }
  };

  const formatDate = (dateString?: string) => {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    const now = new Date();
    const diffTime = Math.abs(now.getTime() - date.getTime());
    const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24));

    if (diffDays === 0) {
      return '今天';
    } else if (diffDays === 1) {
      return '昨天';
    } else if (diffDays < 7) {
      return `${diffDays}天前`;
    } else {
      return date.toLocaleDateString('zh-CN', {
        month: '2-digit',
        day: '2-digit'
      });
    }
  };

  const getFullDate = (dateString?: string) => {
    if (!dateString) return '';
    const date = new Date(dateString);
    return date.toLocaleDateString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const handlePageChange = (newPage: number) => {
    if (newPage >= 1 && newPage <= (categoryDetail?.pagination.total_pages || 1)) {
      setCurrentPage(newPage);
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  };

  const getPageNumbers = () => {
    const pages = [];
    const totalPages = categoryDetail?.pagination.total_pages || 1;
    const currentPageNum = currentPage;
    const maxVisiblePages = 5;

    if (totalPages <= maxVisiblePages) {
      for (let i = 1; i <= totalPages; i++) {
        pages.push(i);
      }
    } else {
      const startPage = Math.max(1, currentPageNum - Math.floor(maxVisiblePages / 2));
      const endPage = Math.min(totalPages, startPage + maxVisiblePages - 1);

      const adjustedStartPage = Math.max(1, endPage - maxVisiblePages + 1);

      if (adjustedStartPage > 1) {
        pages.push(1);
        if (adjustedStartPage > 2) {
          pages.push(null);
        }
      }

      for (let i = adjustedStartPage; i <= endPage; i++) {
        pages.push(i);
      }

      if (endPage < totalPages) {
        if (endPage < totalPages - 1) {
          pages.push(null);
        }
        pages.push(totalPages);
      }
    }

    return pages;
  };

  const handleSortChange = (value: string) => {
    setSortBy(value);
    // 在实际应用中，这里应该重新加载排序后的数据
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800 py-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col items-center justify-center py-20">
            <div className="relative">
              <div className="w-16 h-16 border-4 border-blue-200 rounded-full"></div>
              <div className="absolute top-0 left-0 w-16 h-16 border-4 border-blue-600 rounded-full animate-spin border-t-transparent"></div>
            </div>
            <p className="mt-4 text-gray-600 dark:text-gray-400">加载分类详情中...</p>
          </div>
        </div>
      </div>
    );
  }

  if (error || !categoryDetail) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800 py-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-lg p-8 max-w-2xl mx-auto">
            <div className="text-center">
              <div className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-br from-red-50 to-rose-50 dark:from-red-900/20 dark:to-rose-900/20 rounded-2xl mb-6">
                <AlertCircle className="w-8 h-8 text-red-600 dark:text-red-400" />
              </div>
              <h2 className="text-2xl font-bold text-red-600 dark:text-red-400 mb-4">加载失败</h2>
              <p className="text-gray-600 dark:text-gray-400 mb-6">{error || '未找到该分类'}</p>
              <div className="flex justify-center gap-4">
                <Link
                  href={{ pathname: '/categories' }}
                  className="inline-flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white font-medium rounded-xl transition-all duration-200 hover:shadow-lg hover:-translate-y-0.5 active:translate-y-0"
                >
                  <ArrowLeft className="w-4 h-4" />
                  返回分类列表
                </Link>
                <button
                  onClick={() => loadCategoryDetail(currentPage)}
                  className="px-6 py-3 bg-gradient-to-r from-gray-50 to-gray-100 dark:from-gray-800 dark:to-gray-700 hover:from-gray-100 hover:to-gray-200 dark:hover:from-gray-700 dark:hover:to-gray-600 text-gray-700 dark:text-gray-300 font-medium rounded-xl transition-all duration-200"
                >
                  重新加载
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  const { category, articles, pagination, total_articles } = categoryDetail;
  const isCategorySubscribed = isSubscribed(category.id);

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800 py-8 px-4 sm:px-6 lg:px-8">
      {/* 通知组件 */}
      {notification && (
        <div className={`fixed top-6 right-6 z-50 px-6 py-4 rounded-xl shadow-lg backdrop-blur-sm ${
          notification.type === 'success' 
            ? 'bg-gradient-to-r from-green-500/90 to-emerald-500/90 border border-green-400/20' 
            : 'bg-gradient-to-r from-red-500/90 to-rose-500/90 border border-red-400/20'
        }`}>
          <div className="flex items-center gap-3">
            {notification.type === 'success' ? (
              <CheckCircle className="w-5 h-5 text-white" />
            ) : (
              <AlertCircle className="w-5 h-5 text-white" />
            )}
            <span className="text-white font-medium">{notification.message}</span>
          </div>
        </div>
      )}

      <div className="max-w-7xl mx-auto">
        {/* 返回按钮 */}
        <div className="mb-6">
          <Link
            href={{ pathname: '/categories' }}
            className="inline-flex items-center gap-2 text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-white transition-colors group"
          >
            <ChevronLeft className="w-4 h-4 group-hover:-translate-x-1 transition-transform" />
            返回分类列表
          </Link>
        </div>

        {/* 分类头部信息 */}
        <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-lg p-6 mb-8">
          <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-6">
            <div className="flex-1">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-12 h-12 bg-gradient-to-br from-blue-100 to-indigo-100 dark:from-blue-900/30 dark:to-indigo-900/30 rounded-xl flex items-center justify-center">
                  <FileText className="w-6 h-6 text-blue-600 dark:text-blue-400" />
                </div>
                <div>
                  <h1 className="text-3xl font-bold text-gray-900 dark:text-white">{category.name}</h1>
                  <p className="text-gray-600 dark:text-gray-400 mt-1">
                    {category.description || '暂无描述'}
                  </p>
                </div>
              </div>

              <div className="flex flex-wrap items-center gap-4 text-sm">
                <div className="flex items-center gap-1.5 text-gray-600 dark:text-gray-400">
                  <Calendar className="w-4 h-4" />
                  <span>创建于 {getFullDate(category.created_at)}</span>
                </div>
                <div className="flex items-center gap-1.5 text-gray-600 dark:text-gray-400">
                  <FileText className="w-4 h-4" />
                  <span>{total_articles} 篇文章</span>
                </div>
                <div className="flex items-center gap-1.5 text-gray-600 dark:text-gray-400">
                  <Users className="w-4 h-4" />
                  <span>{category.subscription_count || 0} 人订阅</span>
                </div>
              </div>
            </div>

            <div className="flex items-center gap-3">
              {isCategorySubscribed ? (
                <button
                  onClick={unsubscribeCategory}
                  className="flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-red-50 to-rose-50 dark:from-red-900/20 dark:to-rose-900/20 hover:from-red-100 hover:to-rose-100 dark:hover:from-red-900/30 dark:hover:to-rose-900/30 text-red-700 dark:text-red-300 font-medium rounded-xl transition-all duration-200 hover:shadow-lg hover:-translate-y-0.5 active:translate-y-0"
                >
                  <BellOff className="w-5 h-5" />
                  取消订阅
                </button>
              ) : (
                <button
                  onClick={subscribeCategory}
                  className="flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-green-50 to-emerald-50 dark:from-green-900/20 dark:to-emerald-900/20 hover:from-green-100 hover:to-emerald-100 dark:hover:from-green-900/30 dark:hover:to-emerald-900/30 text-green-700 dark:text-green-300 font-medium rounded-xl transition-all duration-200 hover:shadow-lg hover:-translate-y-0.5 active:translate-y-0"
                >
                  <Bell className="w-5 h-5" />
                  订阅分类
                </button>
              )}
            </div>
          </div>
        </div>

        {/* 搜索和筛选栏 */}
        <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-lg p-6 mb-8">
          <div className="flex flex-col md:flex-row gap-4">
            <div className="flex-1 relative">
              <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="搜索分类内的文章..."
                className="w-full pl-12 pr-4 py-3 border border-gray-200 dark:border-gray-700 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-900 dark:text-white transition-all duration-200"
              />
            </div>
            <div className="flex items-center gap-3">
              <div className="relative">
                <Filter className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
                <select
                  value={sortBy}
                  onChange={(e) => handleSortChange(e.target.value)}
                  className="pl-10 pr-8 py-3 border border-gray-200 dark:border-gray-700 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-900 dark:text-white appearance-none transition-all duration-200"
                >
                  <option value="newest">最新发布</option>
                  <option value="popular">最受欢迎</option>
                  <option value="views">最多浏览</option>
                  <option value="likes">最多点赞</option>
                </select>
                <ChevronRight className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5 rotate-90" />
              </div>
              <button className="px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-xl transition-all duration-200 hover:shadow-lg hover:-translate-y-0.5 active:translate-y-0">
                搜索
              </button>
            </div>
          </div>
        </div>

        {/* 文章列表 */}
        <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-lg overflow-hidden">
          <div className="p-6 border-b border-gray-100 dark:border-gray-700">
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
              分类文章 <span className="text-gray-500 dark:text-gray-400">({total_articles})</span>
            </h2>
          </div>

          {articles && articles.length > 0 ? (
            <>
              <div className="divide-y divide-gray-100 dark:divide-gray-700">
                {articles.map((article) => (
                  <div
                    key={`${article.id}-${article.slug}`}
                    className="group p-6 hover:bg-gradient-to-r hover:from-gray-50 hover:to-gray-100 dark:hover:from-gray-800 dark:hover:to-gray-900 transition-all duration-300 cursor-pointer"
                    onClick={() => router.push({ pathname: '/blog', query: { slug: article.slug } } as any)}
                  >
                    <div className="flex flex-col lg:flex-row gap-6">
                      {/* 封面图片 */}
                      {article.cover_image && (
                        <div className="lg:w-1/4">
                          <div className="relative overflow-hidden rounded-xl aspect-video lg:aspect-[4/3]">
                            <img
                              src={article.cover_image}
                              alt={article.title}
                              className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                            />
                            <div className="absolute inset-0 bg-gradient-to-t from-black/20 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
                          </div>
                        </div>
                      )}

                      {/* 文章内容 */}
                      <div className={`flex-1 ${article.cover_image ? 'lg:w-3/4' : ''}`}>
                        <h3 className="text-xl font-semibold text-gray-900 dark:text-white group-hover:text-blue-600 dark:group-hover:text-blue-400 mb-3 transition-colors line-clamp-2">
                          {article.title}
                        </h3>

                        <p className="text-gray-600 dark:text-gray-400 mb-4 line-clamp-2">
                          {article.excerpt || article.summary || '暂无文章摘要'}
                        </p>

                        <div className="flex flex-wrap items-center gap-4 text-sm text-gray-500 dark:text-gray-400">
                          {/* 作者信息 */}
                          <div className="flex items-center gap-1.5">
                            <User className="w-4 h-4" />
                            <span>{article.author?.username || '匿名作者'}</span>
                          </div>

                          {/* 发布时间 */}
                          <div className="flex items-center gap-1.5">
                            <Clock className="w-4 h-4" />
                            <span>{formatDate(article.created_at)}</span>
                          </div>

                          {/* 统计数据 */}
                          <div className="flex items-center gap-1.5">
                            <Eye className="w-4 h-4" />
                            <span>{article.views}</span>
                          </div>

                          <div className="flex items-center gap-1.5">
                            <Heart className="w-4 h-4" />
                            <span>{article.likes}</span>
                          </div>

                          {/* 标签 */}
                          {article.tags && article.tags.length > 0 && (
                            <div className="flex items-center gap-2">
                              <Tag className="w-4 h-4" />
                              <div className="flex flex-wrap gap-1">
                                {article.tags.slice(0, 3).map((tag, index) => (
                                  <span
                                    key={index}
                                    className="inline-block px-2 py-1 bg-gradient-to-r from-gray-50 to-gray-100 dark:from-gray-800 dark:to-gray-700 text-gray-700 dark:text-gray-300 text-xs rounded-full"
                                  >
                                    {tag}
                                  </span>
                                ))}
                                {article.tags.length > 3 && (
                                  <span className="text-gray-400 text-xs">+{article.tags.length - 3}</span>
                                )}
                              </div>
                            </div>
                          )}
                        </div>

                        {/* 阅读更多提示 */}
                        <div className="mt-4 flex items-center gap-1 text-blue-600 dark:text-blue-400 opacity-0 group-hover:opacity-100 transition-opacity duration-300">
                          <span className="text-sm font-medium">阅读全文</span>
                          <ChevronRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>

              {/* 分页 */}
              {(pagination.total_pages && (pagination.total_pages as number) > 1) && (
                <div className="border-t border-gray-100 dark:border-gray-700 p-6">
                  <div className="flex items-center justify-between">
                    <div className="text-sm text-gray-600 dark:text-gray-400">
                      第 {currentPage} 页，共 {pagination.total_pages as number} 页
                    </div>

                    <nav className="flex items-center gap-1">
                      <button
                        onClick={() => handlePageChange(currentPage - 1)}
                        disabled={!pagination.has_prev}
                        className="px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                      >
                        <ChevronLeft className="w-4 h-4" />
                      </button>

                      {getPageNumbers().map((page_num, index) => (
                        page_num === null ? (
                          <span
                            key={`ellipsis-${index}`}
                            className="px-3 py-2 text-gray-400"
                          >
                            ...
                          </span>
                        ) : page_num === currentPage ? (
                          <button
                            key={page_num}
                            className="px-3.5 py-2 bg-blue-600 text-white rounded-lg font-medium min-w-[40px]"
                          >
                            {page_num}
                          </button>
                        ) : (
                          <button
                            key={page_num}
                            onClick={() => handlePageChange(page_num)}
                            className="px-3.5 py-2 rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors min-w-[40px]"
                          >
                            {page_num}
                          </button>
                        )
                      ))}

                      <button
                        onClick={() => handlePageChange(currentPage + 1)}
                        disabled={!pagination.has_next}
                        className="px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                      >
                        <ChevronRight className="w-4 h-4" />
                      </button>
                    </nav>
                  </div>
                </div>
              )}
            </>
          ) : (
            /* 空状态 */
            <div className="py-20 text-center">
              <div className="inline-flex items-center justify-center w-24 h-24 bg-gradient-to-br from-gray-100 to-gray-200 dark:from-gray-800 dark:to-gray-700 rounded-2xl mb-6">
                <FileText className="w-12 h-12 text-gray-400 dark:text-gray-500" />
              </div>
              <h3 className="text-2xl font-semibold text-gray-900 dark:text-white mb-3">暂无文章</h3>
              <p className="text-gray-600 dark:text-gray-400 mb-8 max-w-md mx-auto">
                这个分类下还没有任何文章。成为第一个在此分类下发布文章的人吧！
              </p>
              <button
                onClick={() => router.push('/my/posts/create')}
                className="inline-flex items-center gap-2 px-8 py-3 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white font-medium rounded-xl transition-all duration-200 hover:shadow-lg hover:-translate-y-0.5 active:translate-y-0"
              >
                <FileText className="w-5 h-5" />
                创建新文章
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default CategoryDetailPage;