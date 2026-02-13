'use client';

import React, {useEffect, useState} from 'react';
import {useRouter} from 'next/navigation';
import {Category, CategoryService} from '@/lib/api';
import {
    AlertCircle,
    Bell,
    BellOff,
    Calendar,
    CheckCircle,
    ChevronRight,
    Filter,
    FolderOpen,
    Loader2,
    Search,
    Users,
    X
} from 'lucide-react';

interface CategoryWithStats extends Category {
  subscription_count: number;
  created_at: string;
}

interface Pagination {
  has_prev: boolean;
  has_next: boolean;
  current_page: number;
  total_pages: number;
  per_page: number;
  total: number;
}

const CategoryListPage = () => {
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
  const [isProcessing, setIsProcessing] = useState<Record<number, boolean>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notification, setNotification] = useState<{type: 'success' | 'error', message: string} | null>(null);

  // 显示通知
  const showNotification = (type: 'success' | 'error', message: string) => {
    setNotification({type, message});
    setTimeout(() => setNotification(null), 4000);
  };

  // 加载分类数据
  useEffect(() => {
    loadCategories(1);
  }, [searchQuery, sortBy]);

  const loadCategories = async (page = 1) => {
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
          created_at: cat.created_at || new Date().toISOString()
        }));
        setCategories(categoriesWithStats);

        if (response.data.subscribed_ids) {
          setSubscribedIds(response.data.subscribed_ids);
        }

        setPagination({
          has_prev: response.data.pagination?.has_prev || page > 1,
          has_next: response.data.pagination?.has_next || page < Math.ceil((response.data.pagination?.total || 0) / 12),
          current_page: response.data.pagination?.current_page || page,
          total_pages: response.data.pagination?.total_pages || Math.ceil((response.data.pagination?.total || 0) / 12),
          per_page: response.data.pagination?.per_page || 12,
          total: response.data.pagination?.total || 0
        });
      } else {
        console.error('API call failed:', response.error);
        setError(response.error || '获取分类列表失败');
        setCategories([]);
      }
    } catch (error: unknown) {
      console.error('加载分类时出错:', error);
      setError(error instanceof Error ? error.message : '加载分类时发生错误');
    } finally {
      setLoading(false);
    }
  };

  const isSubscribed = (categoryId: number) => {
    return subscribedIds.includes(categoryId);
  };

  const subscribeCategory = async (categoryId: number) => {
    setIsProcessing(prev => ({ ...prev, [categoryId]: true }));

    try {
      const response = await CategoryService.subscribeToCategory(categoryId);

      if (response.success) {
        setSubscribedIds(prev => [...prev, categoryId]);
        setCategories(prev =>
          prev.map(cat =>
            cat.id === categoryId
              ? { ...cat, subscription_count: (cat.subscription_count || 0) + 1 }
              : cat
          )
        );
        showNotification('success', '订阅成功！');
      } else {
        if (response.error && response.error.includes('您已经订阅了该分类')) {
          showNotification('error', '您已经订阅了该分类');
        } else {
          console.error('订阅失败:', response.error);
          showNotification('error', response.error || '订阅失败');
        }
      }
    } catch (error) {
      console.error('订阅分类失败:', error);
      showNotification('error', '订阅分类失败，请稍后再试');
    } finally {
      setIsProcessing(prev => ({ ...prev, [categoryId]: false }));
    }
  };

  const unsubscribeCategory = async (categoryId: number) => {
    setIsProcessing(prev => ({ ...prev, [categoryId]: true }));

    try {
      const response = await CategoryService.unsubscribeFromCategory(categoryId);

      if (response.success) {
        setSubscribedIds(prev => prev.filter(id => id !== categoryId));
        setCategories(prev =>
          prev.map(cat =>
            cat.id === categoryId
              ? { ...cat, subscription_count: Math.max(0, (cat.subscription_count || 1) - 1) }
              : cat
          )
        );
        showNotification('success', '取消订阅成功！');
      } else {
        console.error('取消订阅失败:', response.error);
        showNotification('error', response.error || '取消订阅失败');
      }
    } catch (error) {
      console.error('取消订阅分类失败:', error);
      showNotification('error', '取消订阅分类失败，请稍后再试');
    } finally {
      setIsProcessing(prev => ({ ...prev, [categoryId]: false }));
    }
  };

  const changePage = (newPage: number) => {
    if (newPage >= 1 && newPage <= pagination.total_pages) {
      loadCategories(newPage);
    }
  };

  const goToCategory = (categoryName: string) => {
    router.push(`/category/${encodeURIComponent(categoryName)}`);
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit' });
  };

  const getPageNumbers = () => {
    const pages = [];
    const totalPages = pagination.total_pages;
    const currentPage = pagination.current_page;
    const maxVisiblePages = 5;

    if (totalPages <= maxVisiblePages) {
      for (let i = 1; i <= totalPages; i++) {
        pages.push(i);
      }
    } else {
      const startPage = Math.max(1, currentPage - Math.floor(maxVisiblePages / 2));
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

  const handleSortChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setSortBy(e.target.value);
    loadCategories(1);
  };

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchQuery(e.target.value);
  };

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    loadCategories(1);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800 py-8 px-4 sm:px-6 lg:px-8">
      <div className="max-w-7xl mx-auto">
        {/* 头部 */}
        <div className="mb-10">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
            <div>
              <h1 className="text-3xl font-bold text-gray-900 dark:text-white">分类管理</h1>
              <p className="mt-2 text-gray-600 dark:text-gray-400">
                浏览和管理所有分类，订阅你感兴趣的内容
              </p>
            </div>
            <div className="flex items-center gap-3">
              <span className="text-sm text-gray-500 dark:text-gray-400">
                共 {pagination.total} 个分类
              </span>
            </div>
          </div>

          {/* 搜索和筛选 */}
          <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-lg p-6">
            <form onSubmit={handleSearchSubmit} className="space-y-4">
              <div className="flex flex-col lg:flex-row gap-4">
                <div className="flex-1 relative">
                  <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={handleSearchChange}
                    placeholder="搜索分类名称..."
                    className="w-full pl-12 pr-4 py-3 border border-gray-200 dark:border-gray-700 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-900 dark:text-white transition-all duration-200"
                  />
                </div>
                <div className="flex gap-3">
                  <div className="relative">
                    <Filter className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
                    <select
                      value={sortBy}
                      onChange={handleSortChange}
                      className="pl-10 pr-8 py-3 border border-gray-200 dark:border-gray-700 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-900 dark:text-white appearance-none transition-all duration-200"
                    >
                      <option value="name">按名称排序</option>
                      <option value="subscriptions">按订阅数排序</option>
                      <option value="created_at">按创建时间排序</option>
                    </select>
                    <ChevronRight className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5 rotate-90" />
                  </div>
                  <button
                    type="submit"
                    className="px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-xl transition-all duration-200 hover:shadow-lg hover:-translate-y-0.5 active:translate-y-0"
                  >
                    搜索
                  </button>
                </div>
              </div>
            </form>
          </div>
        </div>

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
              <button
                onClick={() => setNotification(null)}
                className="ml-4 text-white/80 hover:text-white"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}

        {/* 错误信息显示 */}
        {error && (
          <div className="mb-6 p-6 bg-gradient-to-r from-red-50 to-rose-50 dark:from-red-900/20 dark:to-rose-900/20 border border-red-200 dark:border-red-800 rounded-2xl">
            <div className="flex items-start gap-3">
              <AlertCircle className="w-6 h-6 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
              <div className="flex-1">
                <h3 className="font-medium text-red-800 dark:text-red-300 mb-1">加载失败</h3>
                <p className="text-red-600 dark:text-red-400 mb-3">{error}</p>
                <button
                  onClick={() => loadCategories(pagination.current_page)}
                  className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors"
                >
                  重试加载
                </button>
              </div>
            </div>
          </div>
        )}

        {/* 加载状态 */}
        {loading ? (
          <div className="flex flex-col items-center justify-center py-20">
            <div className="relative">
              <div className="w-16 h-16 border-4 border-blue-200 rounded-full"></div>
              <div className="absolute top-0 left-0 w-16 h-16 border-4 border-blue-600 rounded-full animate-spin border-t-transparent"></div>
            </div>
            <p className="mt-4 text-gray-600 dark:text-gray-400">加载分类中...</p>
          </div>
        ) : categories && categories.length > 0 ? (
          <>
            {/* 分类网格 */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6 mb-10">
              {categories.map((category) => (
                <div
                  key={category.id}
                  className="group bg-white dark:bg-gray-800 rounded-2xl shadow-md hover:shadow-xl transition-all duration-300 hover:-translate-y-1 border border-gray-100 dark:border-gray-700"
                >
                  <div className="p-6">
                    {/* 分类头部 */}
                    <div className="flex justify-between items-start mb-5">
                      <div className="flex-1 min-w-0">
                        <h3 className="text-lg font-semibold text-gray-900 dark:text-white truncate mb-1">
                          {category.name}
                        </h3>
                        <div className="flex items-center gap-3 text-sm">
                          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300">
                            <Users className="w-3.5 h-3.5" />
                            <span className="font-medium">{category.subscription_count || 0}</span>
                            <span className="hidden sm:inline">订阅</span>
                          </span>
                          <span className="inline-flex items-center gap-1 text-gray-500 dark:text-gray-400">
                            <Calendar className="w-3.5 h-3.5" />
                            {formatDate(category.created_at || new Date().toISOString())}
                          </span>
                        </div>
                      </div>
                    </div>

                    {/* 描述（如果有的话） */}
                    {category.description && (
                      <p className="text-gray-600 dark:text-gray-400 text-sm mb-5 line-clamp-2">
                        {category.description}
                      </p>
                    )}

                    {/* 按钮组 */}
                    <div className="flex justify-between items-center pt-5 border-t border-gray-100 dark:border-gray-700">
                      {isSubscribed(category.id) ? (
                        <button
                          onClick={() => unsubscribeCategory(category.id)}
                          disabled={isProcessing[category.id]}
                          className="flex items-center gap-2 px-4 py-2.5 bg-gradient-to-r from-red-50 to-rose-50 dark:from-red-900/20 dark:to-rose-900/20 hover:from-red-100 hover:to-rose-100 dark:hover:from-red-900/30 dark:hover:to-rose-900/30 text-red-700 dark:text-red-300 rounded-lg transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                          {isProcessing[category.id] ? (
                            <>
                              <Loader2 className="w-4 h-4 animate-spin" />
                              处理中
                            </>
                          ) : (
                            <>
                              <BellOff className="w-4 h-4" />
                              取消订阅
                            </>
                          )}
                        </button>
                      ) : (
                        <button
                          onClick={() => subscribeCategory(category.id)}
                          disabled={isProcessing[category.id]}
                          className="flex items-center gap-2 px-4 py-2.5 bg-gradient-to-r from-green-50 to-emerald-50 dark:from-green-900/20 dark:to-emerald-900/20 hover:from-green-100 hover:to-emerald-100 dark:hover:from-green-900/30 dark:hover:to-emerald-900/30 text-green-700 dark:text-green-300 rounded-lg transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                          {isProcessing[category.id] ? (
                            <>
                              <Loader2 className="w-4 h-4 animate-spin" />
                              处理中
                            </>
                          ) : (
                            <>
                              <Bell className="w-4 h-4" />
                              订阅
                            </>
                          )}
                        </button>
                      )}

                      <button
                        onClick={() => goToCategory(category.name)}
                        className="flex items-center gap-1 text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300 text-sm font-medium group/link"
                      >
                        查看详情
                        <ChevronRight className="w-4 h-4 group-hover/link:translate-x-1 transition-transform duration-200" />
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {/* 分页 */}
            {pagination.total_pages > 1 && (
              <div className="mt-8">
                <div className="flex items-center justify-between">
                  <div className="text-sm text-gray-600 dark:text-gray-400">
                    显示第 {(pagination.current_page - 1) * pagination.per_page + 1} 到 {Math.min(pagination.current_page * pagination.per_page, pagination.total)} 条，共 {pagination.total} 条
                  </div>

                  <nav className="flex items-center gap-1">
                    <button
                      onClick={() => changePage(pagination.current_page - 1)}
                      disabled={!pagination.has_prev}
                      className="px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    >
                      <ChevronRight className="w-4 h-4 rotate-180" />
                    </button>

                    {getPageNumbers().map((page_num, index) => (
                      page_num === null ? (
                        <span
                          key={`ellipsis-${index}`}
                          className="px-3 py-2 text-gray-400"
                        >
                          ...
                        </span>
                      ) : page_num === pagination.current_page ? (
                        <button
                          key={page_num}
                          className="px-3.5 py-2 bg-blue-600 text-white rounded-lg font-medium min-w-[40px]"
                        >
                          {page_num}
                        </button>
                      ) : (
                        <button
                          key={page_num}
                          onClick={() => changePage(page_num)}
                          className="px-3.5 py-2 rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors min-w-[40px]"
                        >
                          {page_num}
                        </button>
                      )
                    ))}

                    <button
                      onClick={() => changePage(pagination.current_page + 1)}
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
          <div className="text-center py-20">
            <div className="inline-flex items-center justify-center w-20 h-20 bg-gradient-to-br from-gray-100 to-gray-200 dark:from-gray-800 dark:to-gray-700 rounded-2xl mb-6">
              <FolderOpen className="w-10 h-10 text-gray-400 dark:text-gray-500" />
            </div>
            <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">暂无分类</h3>
            <p className="text-gray-600 dark:text-gray-400 mb-8 max-w-md mx-auto">
              当前还没有可用的分类。你可以稍后再来查看，或者创建新的分类。
            </p>
            <button
              onClick={() => loadCategories(1)}
              className="px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-xl transition-all duration-200 hover:shadow-lg hover:-translate-y-0.5 active:translate-y-0"
            >
              刷新页面
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default CategoryListPage;