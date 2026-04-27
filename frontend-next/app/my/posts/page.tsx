'use client';

import React, {useEffect, useState} from 'react';
import {useRouter} from 'next/navigation';
import {apiClient, Article} from '@/lib/api';
import WithAuthProtection from '@/components/WithAuthProtection';
import {
    AlertCircle,
    Calendar,
    ChevronRight,
    Edit,
    Eye,
    Eye as EyeIcon,
    FileText,
    Filter,
    Heart,
    Key,
    Plus,
    Search,
    Tag,
    Trash2,
    X
} from 'lucide-react';

const MyArticlesPage = () => {
    const router = useRouter();
    const [articles, setArticles] = useState<Article[]>([]);
    const [loading, setLoading] = useState(true);
    const [currentPage, setCurrentPage] = useState(1);
    const [searchQuery, setSearchQuery] = useState('');
    const pageSize = 10;
    const [total, setTotal] = useState(0);
    const [filterStatus, setFilterStatus] = useState<string | null>(null);
    const [filterHidden, setFilterHidden] = useState<boolean | null>(null);
    const [notification, setNotification] = useState<{type: 'success' | 'error', message: string} | null>(null);
    const [passwordModal, setPasswordModal] = useState<{open: boolean; articleId: number | null; currentPassword: string | null}>({open: false, articleId: null, currentPassword: null});
    const [newPassword, setNewPassword] = useState('');

    // 显示通知
    const showNotification = (type: 'success' | 'error', message: string) => {
        setNotification({type, message});
        setTimeout(() => setNotification(null), 4000);
    };

    // 打开密码设置对话框
    const openPasswordModal = async (articleId: number) => {
        try {
            // 获取文章当前密码状态
            const response = await apiClient.get(`/articles/${articleId}`);
            let hasPassword = false;
            
            if (response.success && response.data) {
                // 检查文章是否有密码（需要从完整详情中获取）
                const articleData = response.data as any;
                hasPassword = articleData.has_password || false;
            }
            
            setPasswordModal({open: true, articleId, currentPassword: hasPassword ? '******' : null});
            setNewPassword('');
        } catch (error) {
            console.error('获取文章信息失败:', error);
            setPasswordModal({open: true, articleId, currentPassword: null});
            setNewPassword('');
        }
    };

    // 关闭密码设置对话框
    const closePasswordModal = () => {
        setPasswordModal({open: false, articleId: null, currentPassword: null});
        setNewPassword('');
    };

    // 设置文章密码
    const setPassword = async () => {
        if (!passwordModal.articleId) return;

        // 验证密码
        if (newPassword.trim() && newPassword.length < 4) {
            showNotification('error', '密码长度至少为4位');
            return;
        }

        try {
            const passwordToSend = newPassword.trim() || null;
            const response = await apiClient.post(`/articles/${passwordModal.articleId}/password`, {
                password: passwordToSend
            });

            if (response.success) {
                showNotification('success', passwordToSend ? '密码设置成功' : '密码已清除');
                closePasswordModal();
                fetchArticles(); // 刷新列表
            } else {
                showNotification('error', response.error || '设置密码失败');
            }
        } catch (error) {
            console.error('设置密码时发生错误:', error);
            showNotification('error', '设置密码失败');
        }
    };

    // 获取我的文章列表
    const fetchArticles = async () => {
        setLoading(true);

        try {
            const params: Record<string, string | number | boolean> = {
                page: currentPage,
                per_page: pageSize,
            };

            if (filterStatus && filterStatus !== 'all') {
                params.status = filterStatus;
            }

            if (searchQuery) {
                params.search = searchQuery;
            }

            // 添加隐藏状态过滤
            if (filterHidden !== null) {
                params.hidden = filterHidden;
            }

            const response = await apiClient.get('/my/articles', params);

            if (response.success && response.data) {
                let articlesData: Article[] = [];
                let total = 0;

                // 检查是否有 pagination 字段（后端返回的结构）
                if ('pagination' in response && response.pagination) {
                    const paginationData = response.pagination as any;
                    total = paginationData.total || 0;

                    // data 字段是文章数组
                    if (Array.isArray(response.data)) {
                        articlesData = response.data as Article[];
                    }
                } else if (response.data && typeof response.data === 'object') {
                    // 兼容旧的数据结构
                    if ('data' in response.data && Array.isArray((response.data as any).data)) {
                        const responseData = response.data as { data: Article[], pagination?: any };
                        articlesData = responseData.data || [];
                        if (responseData.pagination && typeof responseData.pagination === 'object' && 'total' in responseData.pagination) {
                            total = responseData.pagination.total || articlesData.length;
                        } else {
                            total = articlesData.length;
                        }
                    } else if (Array.isArray(response.data)) {
                        articlesData = response.data as Article[];
                        total = response.data.length;
                    } else {
                        articlesData = Array.isArray(response.data) ? response.data as Article[] : [];
                        total = articlesData.length;
                    }
                } else {
                    articlesData = Array.isArray(response.data) ? response.data as Article[] : [];
                    total = articlesData.length;
                }

                setArticles(articlesData);
                setTotal(total);
            } else {
                console.error('获取我的文章列表失败:', response.error);
                setArticles([]);
                setTotal(0);
            }
        } catch (error) {
            console.error('获取我的文章列表时发生错误:', error);
            setArticles([]);
            setTotal(0);
        } finally {
            setLoading(false);
        }
    };

    // 页面加载时获取文章
    useEffect(() => {
        fetchArticles();
    }, [currentPage, filterStatus, filterHidden, searchQuery]);

    // 状态相关辅助函数
    const getStatusType = (status: string | number) => {
        const statusNum = typeof status === 'string' ? (status === '1' || status.toLowerCase() === 'published' ? 1 : status === '0' || status.toLowerCase() === 'draft' ? 0 : -1) : status;
        switch (statusNum) {
            case 1:
                return 'bg-gradient-to-r from-green-50 to-emerald-50 dark:from-green-900/20 dark:to-emerald-900/20 text-green-700 dark:text-green-300 border border-green-200 dark:border-green-800';
            case 0:
                return 'bg-gradient-to-r from-yellow-50 to-amber-50 dark:from-yellow-900/20 dark:to-amber-900/20 text-yellow-700 dark:text-yellow-300 border border-yellow-200 dark:border-yellow-800';
            case -1:
                return 'bg-gradient-to-r from-red-50 to-rose-50 dark:from-red-900/20 dark:to-rose-900/20 text-red-700 dark:text-red-300 border border-red-200 dark:border-red-800';
            default:
                return 'bg-gradient-to-r from-gray-50 to-gray-100 dark:from-gray-800 dark:to-gray-700 text-gray-700 dark:text-gray-300 border border-gray-200 dark:border-gray-700';
        }
    };

    const getStatusText = (status: string | number) => {
        const statusNum = typeof status === 'string' ? (status === '1' || status.toLowerCase() === 'published' ? 1 : status === '0' || status.toLowerCase() === 'draft' ? 0 : -1) : status;
        switch (statusNum) {
            case 1:
                return '已发布';
            case 0:
                return '草稿';
            case -1:
                return '已删除';
            default:
                return '未知';
        }
    };

    const getStatusIcon = (status: string | number) => {
        const statusNum = typeof status === 'string' ? (status === '1' || status.toLowerCase() === 'published' ? 1 : status === '0' || status.toLowerCase() === 'draft' ? 0 : -1) : status;
        switch (statusNum) {
            case 1:
                return 'text-green-500';
            case 0:
                return 'text-yellow-500';
            case -1:
                return 'text-red-500';
            default:
                return 'text-gray-500';
        }
    };

    const formatDate = (dateString: string) => {
        const date = new Date(dateString);
        return date.toLocaleDateString('zh-CN', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit'
        });
    };

    const getTags = (tagsStr: string | string[] | undefined) => {
        if (!tagsStr) return [];

        if (Array.isArray(tagsStr)) {
            return tagsStr.filter(tag => typeof tag === 'string' && tag.trim() !== '');
        }

        if (typeof tagsStr === 'string') {
            return tagsStr.split(';').filter(tag => tag.trim() !== '');
        }

        return [];
    };

    // 分页处理
    const handlePageChange = (page: number) => {
        setCurrentPage(page);
    };

    // 文章操作
    const createNewArticle = () => {
        router.push('/my/posts/create');
    };

    const editArticle = (id: number) => {
        router.push(`/my/posts/edit?id=${id}`);
    };

    const viewArticle = (id: number) => {
        const article = articles.find(a => a.id === id);
        if (article && article.slug) {
            window.open(`/blog/detail?slug=${article.slug}`, '_blank');
        } else {
            window.open(`/articles/detail?id=${id}`, '_blank');
        }
    };

    const deleteArticle = async (id: number) => {
        if (window.confirm('确定要删除这篇文章吗？此操作不可撤销。')) {
            try {
                const response = await apiClient.delete(`/articles/${id}`);

                if (response.success) {
                    showNotification('success', '文章删除成功');
                    fetchArticles();
                } else {
                    console.error('删除文章失败:', response.error);
                    showNotification('error', response.error || '删除文章失败');
                }
            } catch (error) {
                console.error('删除文章时发生错误:', error);
                showNotification('error', '删除文章时发生错误');
            }
        }
    };

    const handleSearchSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        setCurrentPage(1);
    };

    const handleSearchClear = () => {
        setSearchQuery('');
        setCurrentPage(1);
    };

    const pageCount = Math.ceil(total / pageSize);

    const getPageNumbers = () => {
        const pages: (number | null)[] = [];
        const maxVisiblePages = 5;

        if (pageCount <= maxVisiblePages) {
            for (let i = 1; i <= pageCount; i++) {
                pages.push(i);
            }
        } else {
            const startPage = Math.max(1, currentPage - Math.floor(maxVisiblePages / 2));
            const endPage = Math.min(pageCount, startPage + maxVisiblePages - 1);

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

            if (endPage < pageCount) {
                if (endPage < pageCount - 1) {
                    pages.push(null);
                }
                pages.push(pageCount);
            }
        }

        return pages;
    };

    return (
        <WithAuthProtection loadingMessage="正在加载我的文章...">
            <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800 py-8 px-4 sm:px-6 lg:px-8">
                <div className="max-w-7xl mx-auto">
                    {/* 通知组件 */}
                    {notification && (
                        <div className={`fixed top-6 right-6 z-50 px-6 py-4 rounded-xl shadow-lg backdrop-blur-sm ${
                            notification.type === 'success' 
                                ? 'bg-gradient-to-r from-green-500/90 to-emerald-500/90 border border-green-400/20' 
                                : 'bg-gradient-to-r from-red-500/90 to-rose-500/90 border border-red-400/20'
                        }`}>
                            <div className="flex items-center gap-3">
                                {notification.type === 'success' ? (
                                    <AlertCircle className="w-5 h-5 text-white" />
                                ) : (
                                    <AlertCircle className="w-5 h-5 text-white" />
                                )}
                                <span className="text-white font-medium">{notification.message}</span>
                            </div>
                        </div>
                    )}

                    {/* 头部区域 */}
                    <div className="mb-8">
                        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
                            <div>
                                <h1 className="text-3xl font-bold text-gray-900 dark:text-white">我的文章</h1>
                                <p className="mt-2 text-gray-600 dark:text-gray-400">
                                    管理您的文章，包括草稿、已发布和已删除的文章
                                </p>
                            </div>
                            <div className="flex items-center gap-3">
                                <span className="text-sm text-gray-500 dark:text-gray-400">
                                    总计: <span className="font-semibold">{total}</span> 篇文章
                                </span>
                                <button
                                    onClick={createNewArticle}
                                    className="flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white font-medium rounded-xl transition-all duration-200 hover:shadow-lg hover:-translate-y-0.5 active:translate-y-0"
                                >
                                    <Plus className="w-4 h-4" />
                                    创建新文章
                                </button>
                            </div>
                        </div>

                        {/* 搜索和筛选栏 */}
                        <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-lg p-6 mb-6">
                            <div className="flex flex-col lg:flex-row gap-4">
                                <div className="flex-1">
                                    <form onSubmit={handleSearchSubmit} className="relative">
                                        <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
                                        <input
                                            type="text"
                                            value={searchQuery}
                                            onChange={(e) => setSearchQuery(e.target.value)}
                                            placeholder="搜索文章标题、内容或标签..."
                                            className="w-full pl-12 pr-10 py-3 border border-gray-200 dark:border-gray-700 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-900 dark:text-white transition-all duration-200"
                                        />
                                        {searchQuery && (
                                            <button
                                                type="button"
                                                onClick={handleSearchClear}
                                                className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                                            >
                                                <Trash2 className="w-4 h-4" />
                                            </button>
                                        )}
                                    </form>
                                </div>
                                <div className="flex items-center gap-3">
                                    <div className="relative">
                                        <Filter className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
                                        <select
                                            value={filterStatus || 'all'}
                                            onChange={(e) => {
                                                const newFilter = e.target.value === 'all' ? null : e.target.value;
                                                setFilterStatus(newFilter);
                                                setCurrentPage(1);
                                            }}
                                            className="pl-10 pr-8 py-3 border border-gray-200 dark:border-gray-700 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-900 dark:text-white appearance-none transition-all duration-200"
                                        >
                                            <option value="all">全部状态</option>
                                            <option value="draft">草稿</option>
                                            <option value="published">已发布</option>
                                            <option value="deleted">已删除</option>
                                        </select>
                                        <ChevronRight className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5 rotate-90" />
                                    </div>
                                    <div className="relative">
                                        <EyeIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
                                        <select
                                            value={filterHidden === null ? 'all' : filterHidden ? 'hidden' : 'visible'}
                                            onChange={(e) => {
                                                const value = e.target.value;
                                                let newFilter: boolean | null = null;
                                                if (value === 'hidden') newFilter = true;
                                                else if (value === 'visible') newFilter = false;
                                                setFilterHidden(newFilter);
                                                setCurrentPage(1);
                                            }}
                                            className="pl-10 pr-8 py-3 border border-gray-200 dark:border-gray-700 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-900 dark:text-white appearance-none transition-all duration-200"
                                        >
                                            <option value="all">全部可见性</option>
                                            <option value="visible">公开</option>
                                            <option value="hidden">隐藏</option>
                                        </select>
                                        <ChevronRight className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5 rotate-90" />
                                    </div>
                                    <button
                                        onClick={handleSearchSubmit}
                                        className="px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-xl transition-all duration-200 hover:shadow-lg hover:-translate-y-0.5 active:translate-y-0"
                                    >
                                        搜索
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* 主内容区域 */}
                    <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-lg overflow-hidden">
                        {loading ? (
                            <div className="flex flex-col items-center justify-center py-20">
                                <div className="relative">
                                    <div className="w-16 h-16 border-4 border-blue-200 rounded-full"></div>
                                    <div className="absolute top-0 left-0 w-16 h-16 border-4 border-blue-600 rounded-full animate-spin border-t-transparent"></div>
                                </div>
                                <p className="mt-4 text-gray-600 dark:text-gray-400">加载文章中...</p>
                            </div>
                        ) : articles.length > 0 ? (
                            <>
                                {/* 文章列表 */}
                                <div className="divide-y divide-gray-100 dark:divide-gray-700">
                                    {articles.map((article) => (
                                        <div
                                            key={article.id}
                                            className="group p-6 hover:bg-gradient-to-r hover:from-gray-50 hover:to-gray-100 dark:hover:from-gray-800 dark:hover:to-gray-900 transition-all duration-300"
                                        >
                                            <div className="flex flex-col lg:flex-row lg:items-start gap-6">
                                                {/* 文章内容区域 */}
                                                <div className="flex-1 min-w-0">
                                                    <div className="flex items-start gap-3 mb-3">
                                                        <div className={`flex items-center gap-1.5 px-3 py-1 rounded-full text-sm font-medium ${getStatusType(article.status)}`}>
                                                            <div className={`w-2 h-2 rounded-full ${getStatusIcon(article.status)}`}></div>
                                                            {getStatusText(article.status)}
                                                        </div>
                                                        {article.hidden && (
                                                            <span className="flex items-center gap-1.5 px-3 py-1 rounded-full text-sm font-medium bg-gradient-to-r from-purple-50 to-violet-50 dark:from-purple-900/20 dark:to-violet-900/20 text-purple-700 dark:text-purple-300 border border-purple-200 dark:border-purple-800">
                                                                <EyeIcon className="w-3 h-3" />
                                                                隐藏
                                                            </span>
                                                        )}
                                                        <h3 className="text-xl font-semibold text-gray-900 dark:text-white group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors flex-1">
                                                            {article.title}
                                                        </h3>
                                                    </div>

                                                    {/* 摘要 */}
                                                    {article.summary && (
                                                        <p className="text-gray-600 dark:text-gray-400 mb-4 line-clamp-2">
                                                            {article.summary}
                                                        </p>
                                                    )}

                                                    {/* 元数据 */}
                                                    <div className="flex flex-wrap items-center gap-4 text-sm text-gray-500 dark:text-gray-400">
                                                        <span className="flex items-center gap-1.5">
                                                            <Calendar className="w-4 h-4" />
                                                            {formatDate(article.created_at)}
                                                        </span>
                                                        <span className="flex items-center gap-1.5">
                                                            <EyeIcon className="w-4 h-4" />
                                                            浏览: {article.views}
                                                        </span>
                                                        <span className="flex items-center gap-1.5">
                                                            <Heart className="w-4 h-4" />
                                                            点赞: {article.likes}
                                                        </span>
                                                        {/* 密码保护标识 */}
                                                        {(article as any).has_password && (
                                                            <span className="flex items-center gap-1.5 text-purple-600 dark:text-purple-400 font-medium">
                                                                <Key className="w-4 h-4" />
                                                                已加密
                                                            </span>
                                                        )}
                                                    </div>

                                                    {/* 标签 */}
                                                    {getTags(article.tags).length > 0 && (
                                                        <div className="flex flex-wrap gap-2 mt-3">
                                                            {getTags(article.tags).map((tag: string, idx: number) => (
                                                                <span
                                                                    key={idx}
                                                                    className="inline-flex items-center gap-1.5 bg-gradient-to-r from-gray-50 to-gray-100 dark:from-gray-800 dark:to-gray-700 hover:from-blue-50 hover:to-indigo-50 dark:hover:from-blue-900/20 dark:hover:to-indigo-900/20 text-gray-700 dark:text-gray-300 text-xs font-medium rounded-full px-3 py-1.5 transition-all duration-200"
                                                                >
                                                                    <Tag className="w-3 h-3" />
                                                                    {tag}
                                                                </span>
                                                            ))}
                                                        </div>
                                                    )}
                                                </div>

                                                {/* 操作按钮 */}
                                                <div className="flex items-center gap-2 lg:flex-col lg:items-end lg:gap-2">
                                                    <button
                                                        onClick={() => editArticle(article.id)}
                                                        className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 hover:from-blue-100 hover:to-indigo-100 dark:hover:from-blue-900/30 dark:hover:to-indigo-900/30 text-blue-700 dark:text-blue-300 rounded-lg transition-all duration-200 group/btn"
                                                    >
                                                        <Edit className="w-4 h-4" />
                                                        <span className="hidden lg:inline">编辑</span>
                                                    </button>
                                                    <button
                                                        onClick={() => openPasswordModal(article.id)}
                                                        className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-purple-50 to-violet-50 dark:from-purple-900/20 dark:to-violet-900/20 hover:from-purple-100 hover:to-violet-100 dark:hover:from-purple-900/30 dark:hover:to-violet-900/30 text-purple-700 dark:text-purple-300 rounded-lg transition-all duration-200 group/btn"
                                                    >
                                                        <Key className="w-4 h-4" />
                                                        <span className="hidden lg:inline">密码</span>
                                                    </button>
                                                    <button
                                                        onClick={() => viewArticle(article.id)}
                                                        className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-gray-50 to-gray-100 dark:from-gray-800 dark:to-gray-700 hover:from-gray-100 hover:to-gray-200 dark:hover:from-gray-700 dark:hover:to-gray-600 text-gray-700 dark:text-gray-300 rounded-lg transition-all duration-200 group/btn"
                                                    >
                                                        <Eye className="w-4 h-4" />
                                                        <span className="hidden lg:inline">查看</span>
                                                    </button>
                                                    <button
                                                        onClick={() => deleteArticle(article.id)}
                                                        className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-red-50 to-rose-50 dark:from-red-900/20 dark:to-rose-900/20 hover:from-red-100 hover:to-rose-100 dark:hover:from-red-900/30 dark:hover:to-rose-900/30 text-red-700 dark:text-red-300 rounded-lg transition-all duration-200 group/btn"
                                                    >
                                                        <Trash2 className="w-4 h-4" />
                                                        <span className="hidden lg:inline">删除</span>
                                                    </button>
                                                </div>
                                            </div>
                                        </div>
                                    ))}
                                </div>

                                {/* 分页 */}
                                {pageCount > 1 && (
                                    <div className="border-t border-gray-100 dark:border-gray-700 p-6">
                                        <div className="flex items-center justify-between">
                                            <div className="text-sm text-gray-600 dark:text-gray-400">
                                                显示第 {(currentPage - 1) * pageSize + 1} 到 {Math.min(currentPage * pageSize, total)} 条，共 {total} 条
                                            </div>

                                            <nav className="flex items-center gap-1">
                                                <button
                                                    onClick={() => handlePageChange(currentPage - 1)}
                                                    disabled={currentPage === 1}
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
                                                    disabled={currentPage === pageCount}
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
                                    您还没有创建任何文章。点击上方的&#34;创建新文章&#34;按钮开始写作吧！
                                </p>
                                <button
                                    onClick={createNewArticle}
                                    className="inline-flex items-center gap-2 px-8 py-3 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white font-medium rounded-xl transition-all duration-200 hover:shadow-lg hover:-translate-y-0.5 active:translate-y-0"
                                >
                                    <Plus className="w-5 h-5" />
                                    创建第一篇文章
                                </button>
                            </div>
                        )}
                    </div>
                </div>

                {/* 密码设置对话框 */}
                {passwordModal.open && (
                    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
                        <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-2xl max-w-md w-full overflow-hidden animate-in fade-in zoom-in duration-200">
                            {/* 对话框头部 */}
                            <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
                                <h3 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                                    <Key className="w-5 h-5 text-purple-600" />
                                    设置文章访问密码
                                </h3>
                                <button
                                    onClick={closePasswordModal}
                                    className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
                                >
                                    <X className="w-5 h-5" />
                                </button>
                            </div>

                            {/* 对话框内容 */}
                            <div className="px-6 py-6">
                                <div className="mb-4">
                                    <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">
                                        为文章设置访问密码，访客需要输入密码才能查看文章内容。
                                    </p>
                                    {passwordModal.currentPassword && (
                                        <div className="mt-3 p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
                                            <p className="text-xs text-blue-700 dark:text-blue-300">
                                                <span className="font-medium">当前状态：</span>
                                                已设置密码 {passwordModal.currentPassword}
                                            </p>
                                        </div>
                                    )}
                                </div>

                                <div className="space-y-4">
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                                            新密码（留空则清除密码）
                                        </label>
                                        <input
                                            type="password"
                                            value={newPassword}
                                            onChange={(e) => setNewPassword(e.target.value)}
                                            placeholder="输入新密码（至少4位）"
                                            className="w-full px-4 py-2.5 border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent dark:bg-gray-900 dark:text-white transition-all"
                                            onKeyDown={(e) => {
                                                if (e.key === 'Enter') {
                                                    setPassword();
                                                }
                                            }}
                                        />
                                        <p className="mt-1.5 text-xs text-gray-500 dark:text-gray-400">
                                            提示：输入空值将清除现有密码
                                        </p>
                                    </div>
                                </div>
                            </div>

                            {/* 对话框底部按钮 */}
                            <div className="px-6 py-4 border-t border-gray-200 dark:border-gray-700 flex justify-end gap-3 bg-gray-50 dark:bg-gray-900/50">
                                <button
                                    onClick={closePasswordModal}
                                    className="px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                                >
                                    取消
                                </button>
                                <button
                                    onClick={setPassword}
                                    className="px-4 py-2 bg-gradient-to-r from-purple-600 to-violet-600 hover:from-purple-700 hover:to-violet-700 text-white font-medium rounded-lg transition-all hover:shadow-lg"
                                >
                                    {newPassword.trim() ? '设置密码' : '清除密码'}
                                </button>
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </WithAuthProtection>
    );
};

export default MyArticlesPage;