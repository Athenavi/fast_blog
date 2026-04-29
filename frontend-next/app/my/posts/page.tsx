'use client';

import React, {useEffect, useState, useCallback, useMemo} from 'react';
import {useRouter} from 'next/navigation';
import Image from 'next/image';
import {apiClient, Article} from '@/lib/api';
import WithAuthProtection from '@/components/WithAuthProtection';
import {
    AlertCircle,
    Calendar,
    ChevronRight,
    Edit,
    Eye,
    FileText,
    Filter,
    Heart,
    Key,
    Plus,
    Search,
    Tag,
    Trash2,
    X,
    MoreVertical,
    Lock
} from 'lucide-react';

const MyArticlesPage = () => {
    const router = useRouter();
    const [articles, setArticles] = useState<Article[]>([]);
    const [loading, setLoading] = useState(true);
    const [currentPage, setCurrentPage] = useState(1);
    const [searchQuery, setSearchQuery] = useState('');
    const pageSize = 12;
    const [total, setTotal] = useState(0);
    const [filterStatus, setFilterStatus] = useState<string | null>(null);
    const [filterHidden, setFilterHidden] = useState<boolean | null>(null);
    const [notification, setNotification] = useState<{type: 'success' | 'error', message: string} | null>(null);
    const [passwordModal, setPasswordModal] = useState<{open: boolean; articleId: number | null; currentPassword: string | null}>({open: false, articleId: null, currentPassword: null});
    const [newPassword, setNewPassword] = useState('');
    const [activeMenu, setActiveMenu] = useState<number | null>(null);

    // 显示通知
    const showNotification = useCallback((type: 'success' | 'error', message: string) => {
        setNotification({type, message});
        setTimeout(() => setNotification(null), 4000);
    }, []);

    // 打开密码设置对话框
    const openPasswordModal = useCallback(async (articleId: number) => {
        try {
            const response = await apiClient.get(`/articles/${articleId}`);
            let hasPassword = false;
            
            if (response.success && response.data) {
                const articleData = response.data as any;
                hasPassword = articleData.has_password || false;
            }
            
            setPasswordModal({open: true, articleId, currentPassword: hasPassword ? '******' : null});
            setNewPassword('');
            setActiveMenu(null);
        } catch (error) {
            console.error('获取文章信息失败:', error);
            setPasswordModal({open: true, articleId, currentPassword: null});
            setNewPassword('');
            setActiveMenu(null);
        }
    }, []);

    // 关闭密码设置对话框
    const closePasswordModal = useCallback(() => {
        setPasswordModal({open: false, articleId: null, currentPassword: null});
        setNewPassword('');
    }, []);

    // 设置文章密码
    const setPassword = useCallback(async () => {
        if (!passwordModal.articleId) return;

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
                fetchArticles();
            } else {
                showNotification('error', response.error || '设置密码失败');
            }
        } catch (error) {
            console.error('设置密码时发生错误:', error);
            showNotification('error', '设置密码失败');
        }
    }, [passwordModal.articleId, newPassword, showNotification, closePasswordModal]);

    // 获取我的文章列表
    const fetchArticles = useCallback(async () => {
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

            if (filterHidden !== null) {
                params.hidden = filterHidden;
            }

            const response = await apiClient.get('/my/articles', params);

            if (response.success && response.data) {
                let articlesData: Article[] = [];
                let total = 0;

                if ('pagination' in response && response.pagination) {
                    const paginationData = response.pagination as any;
                    total = paginationData.total || 0;

                    if (Array.isArray(response.data)) {
                        articlesData = response.data as Article[];
                    }
                } else if (response.data && typeof response.data === 'object') {
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
    }, [currentPage, filterStatus, filterHidden, searchQuery]);

    // 页面加载时获取文章
    useEffect(() => {
        fetchArticles();
    }, [fetchArticles]);

    // 状态相关辅助函数
    const getStatusBadge = useCallback((status: string | number) => {
        const statusNum = typeof status === 'string' ?
            (status === '1' || status.toLowerCase() === 'published' ? 1 :
                status === '0' || status.toLowerCase() === 'draft' ? 0 : -1) : status;

        const config = {
            1: {
                color: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400',
                label: '已发布',
                dot: 'bg-emerald-500'
            },
            0: {
                color: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400',
                label: '草稿',
                dot: 'bg-amber-500'
            },
            '-1': {
                color: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
                label: '已删除',
                dot: 'bg-red-500'
            }
        };

        const badgeConfig = config[statusNum as keyof typeof config] || config['-1'];

        return (
            <span
                className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${badgeConfig.color}`}>
                <span className={`w-1.5 h-1.5 rounded-full ${badgeConfig.dot}`}/>
                {badgeConfig.label}
            </span>
        );
    }, []);

    const formatDate = useCallback((dateString: string) => {
        const date = new Date(dateString);
        const now = new Date();
        const diffMs = now.getTime() - date.getTime();
        const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

        if (diffDays === 0) {
            return '今天';
        } else if (diffDays === 1) {
            return '昨天';
        } else if (diffDays < 7) {
            return `${diffDays}天前`;
        } else {
            return date.toLocaleDateString('zh-CN', {
                year: 'numeric',
                month: '2-digit',
                day: '2-digit'
            });
        }
    }, []);

    const getTags = useCallback((tagsStr: string | string[] | undefined) => {
        if (!tagsStr) return [];

        if (Array.isArray(tagsStr)) {
            return tagsStr.filter(tag => typeof tag === 'string' && tag.trim() !== '');
        }

        if (typeof tagsStr === 'string') {
            return tagsStr.split(';').filter(tag => tag.trim() !== '');
        }

        return [];
    }, []);

    // 文章操作
    const createNewArticle = useCallback(() => {
        router.push('/my/posts/create');
    }, [router]);

    const editArticle = useCallback((id: number) => {
        router.push(`/my/posts/edit?id=${id}`);
        setActiveMenu(null);
    }, [router]);

    const viewArticle = useCallback((article: Article) => {
        if (article.slug) {
            window.open(`/blog/detail?slug=${article.slug}`, '_blank');
        } else {
            window.open(`/articles/detail?id=${article.id}`, '_blank');
        }
        setActiveMenu(null);
    }, []);

    const deleteArticle = useCallback(async (id: number) => {
        if (window.confirm('确定要删除这篇文章吗？此操作不可撤销。')) {
            try {
                const response = await apiClient.delete(`/articles/${id}`);

                if (response.success) {
                    showNotification('success', '文章删除成功');
                    fetchArticles();
                } else {
                    showNotification('error', response.error || '删除文章失败');
                }
            } catch (error) {
                console.error('删除文章时发生错误:', error);
                showNotification('error', '删除文章时发生错误');
            }
        }
        setActiveMenu(null);
    }, [showNotification, fetchArticles]);

    const handleSearchSubmit = useCallback((e: React.FormEvent) => {
        e.preventDefault();
        setCurrentPage(1);
    }, []);

    const handleSearchClear = useCallback(() => {
        setSearchQuery('');
        setCurrentPage(1);
    }, []);

    const pageCount = Math.ceil(total / pageSize);

    // 获取封面图URL
    const getCoverImageUrl = useCallback((coverImage: string | undefined) => {
        if (!coverImage) return null;

        // 如果已经是完整URL，直接返回
        if (coverImage.startsWith('http://') || coverImage.startsWith('https://')) {
            return coverImage;
        }

        // 否则拼接API基础URL
        const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:9421';
        return `${baseUrl}${coverImage.startsWith('/') ? '' : '/'}${coverImage}`;
    }, []);

    return (
        <WithAuthProtection loadingMessage="正在加载我的文章...">
            <div
                className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-blue-50 dark:from-gray-950 dark:via-gray-900 dark:to-slate-950">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                    {/* 通知组件 */}
                    {notification && (
                        <div
                            className={`fixed top-6 right-6 z-50 px-6 py-4 rounded-xl shadow-2xl backdrop-blur-md border animate-in slide-in-from-top-2 ${
                            notification.type === 'success'
                                ? 'bg-gradient-to-r from-emerald-500/95 to-green-500/95 border-emerald-400/30'
                                : 'bg-gradient-to-r from-red-500/95 to-rose-500/95 border-red-400/30'
                        }`}>
                            <div className="flex items-center gap-3">
                                <AlertCircle className="w-5 h-5 text-white"/>
                                <span className="text-white font-medium">{notification.message}</span>
                            </div>
                        </div>
                    )}

                    {/* 头部区域 */}
                    <div className="mb-8">
                        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
                            <div>
                                <h1 className="text-4xl font-bold bg-gradient-to-r from-blue-600 via-indigo-600 to-purple-600 bg-clip-text text-transparent">
                                    我的文章
                                </h1>
                                <p className="mt-2 text-gray-600 dark:text-gray-400">
                                    管理和组织您的创作内容
                                </p>
                            </div>
                            <button
                                onClick={createNewArticle}
                                className="group flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white font-semibold rounded-xl transition-all duration-300 hover:shadow-xl hover:-translate-y-0.5 active:translate-y-0"
                            >
                                <Plus className="w-5 h-5 group-hover:rotate-90 transition-transform duration-300"/>
                                创建新文章
                            </button>
                        </div>

                        {/* 搜索和筛选栏 */}
                        <div
                            className="bg-white/80 dark:bg-gray-800/80 backdrop-blur-xl rounded-2xl shadow-lg border border-gray-200/50 dark:border-gray-700/50 p-4 mb-6">
                            <div className="flex flex-col lg:flex-row gap-3">
                                <div className="flex-1">
                                    <form onSubmit={handleSearchSubmit} className="relative">
                                        <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
                                        <input
                                            type="text"
                                            value={searchQuery}
                                            onChange={(e) => setSearchQuery(e.target.value)}
                                            placeholder="搜索文章标题、内容或标签..."
                                            className="w-full pl-12 pr-10 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 dark:bg-gray-900/50 dark:text-white transition-all duration-200"
                                        />
                                        {searchQuery && (
                                            <button
                                                type="button"
                                                onClick={handleSearchClear}
                                                className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
                                            >
                                                <X className="w-4 h-4"/>
                                            </button>
                                        )}
                                    </form>
                                </div>
                                <div className="flex items-center gap-2">
                                    <div className="relative">
                                        <Filter
                                            className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4"/>
                                        <select
                                            value={filterStatus || 'all'}
                                            onChange={(e) => {
                                                const newFilter = e.target.value === 'all' ? null : e.target.value;
                                                setFilterStatus(newFilter);
                                                setCurrentPage(1);
                                            }}
                                            className="pl-9 pr-8 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500/50 dark:bg-gray-900/50 dark:text-white appearance-none transition-all duration-200 text-sm"
                                        >
                                            <option value="all">全部状态</option>
                                            <option value="draft">草稿</option>
                                            <option value="published">已发布</option>
                                            <option value="deleted">已删除</option>
                                        </select>
                                    </div>
                                    <div className="relative">
                                        <Eye
                                            className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4"/>
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
                                            className="pl-9 pr-8 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500/50 dark:bg-gray-900/50 dark:text-white appearance-none transition-all duration-200 text-sm"
                                        >
                                            <option value="all">全部可见性</option>
                                            <option value="visible">公开</option>
                                            <option value="hidden">隐藏</option>
                                        </select>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* 主内容区域 - 卡片网格布局 */}
                    {loading ? (
                        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                            {[...Array(6)].map((_, i) => (
                                <div key={i}
                                     className="bg-white dark:bg-gray-800 rounded-xl shadow-lg overflow-hidden animate-pulse">
                                    <div className="h-40 sm:h-48 bg-gray-200 dark:bg-gray-700"/>
                                    <div className="p-4 space-y-2">
                                        <div className="h-5 bg-gray-200 dark:bg-gray-700 rounded w-3/4"/>
                                        <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-full"/>
                                        <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-2/3"/>
                                    </div>
                                </div>
                            ))}
                        </div>
                    ) : articles.length > 0 ? (
                        <>
                            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                                {articles.map((article) => {
                                    const coverUrl = getCoverImageUrl(article.cover_image);

                                    return (
                                        <div
                                            key={article.id}
                                            className="group bg-white dark:bg-gray-800 rounded-xl shadow-md hover:shadow-xl transition-all duration-300 overflow-hidden border border-gray-200/50 dark:border-gray-700/50 hover:-translate-y-0.5"
                                        >
                                            {/* 封面图 */}
                                            <div
                                                className="relative h-40 sm:h-48 overflow-hidden bg-gradient-to-br from-blue-100 to-purple-100 dark:from-blue-900/20 dark:to-purple-900/20">
                                                {coverUrl ? (
                                                    <Image
                                                        src={coverUrl}
                                                        alt={article.title}
                                                        fill
                                                        className="object-cover group-hover:scale-110 transition-transform duration-500"
                                                        sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw"
                                                        onError={(e) => {
                                                            // 图片加载失败时隐藏
                                                            (e.target as HTMLImageElement).style.display = 'none';
                                                        }}
                                                    />
                                                ) : (
                                                    <div className="w-full h-full flex items-center justify-center">
                                                        <FileText
                                                            className="w-16 h-16 text-gray-300 dark:text-gray-600"/>
                                                    </div>
                                                )}

                                                {/* 状态徽章 */}
                                                <div className="absolute top-3 left-3">
                                                    {getStatusBadge(article.status)}
                                                </div>

                                                {/* 隐藏标识 */}
                                                {article.hidden && (
                                                    <div className="absolute top-3 right-3">
                                                        <span
                                                            className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-purple-100 text-purple-700 dark:bg-purple-900/50 dark:text-purple-300">
                                                            <Lock className="w-3 h-3"/>
                                                            隐藏
                                                        </span>
                                                    </div>
                                                )}

                                                {/* 渐变遮罩 */}
                                                <div
                                                    className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300"/>
                                            </div>

                                            {/* 内容区域 */}
                                            <div className="p-4">
                                                {/* 标题 */}
                                                <h3 className="text-base sm:text-lg font-bold text-gray-900 dark:text-white mb-2 line-clamp-2 group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">
                                                    {article.title}
                                                </h3>

                                                {/* 摘要 */}
                                                {article.excerpt && (
                                                    <p className="text-xs sm:text-sm text-gray-600 dark:text-gray-400 mb-3 line-clamp-2">
                                                        {article.excerpt}
                                                    </p>
                                                )}

                                                {/* 元数据 */}
                                                <div
                                                    className="flex items-center gap-3 text-xs text-gray-500 dark:text-gray-400 mb-3">
                                                    <span className="flex items-center gap-1">
                                                        <Calendar className="w-3 h-3"/>
                                                        {formatDate(article.created_at)}
                                                    </span>
                                                    <span className="flex items-center gap-1">
                                                        <Eye className="w-3 h-3"/>
                                                        {article.views || 0}
                                                    </span>
                                                    <span className="flex items-center gap-1">
                                                        <Heart className="w-3 h-3"/>
                                                        {article.likes || 0}
                                                    </span>
                                                </div>

                                                {/* 标签 */}
                                                {getTags(article.tags).length > 0 && (
                                                    <div className="flex flex-wrap gap-1 mb-3">
                                                        {getTags(article.tags).slice(0, 2).map((tag: string, idx: number) => (
                                                            <span
                                                                key={idx}
                                                                className="inline-flex items-center gap-1 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 text-xs font-medium rounded-full px-2 py-0.5"
                                                            >
                                                                <Tag className="w-2.5 h-2.5"/>
                                                                {tag}
                                                            </span>
                                                        ))}
                                                        {getTags(article.tags).length > 2 && (
                                                            <span className="text-xs text-gray-500 dark:text-gray-400">
                                                                +{getTags(article.tags).length - 2}
                                                            </span>
                                                        )}
                                                    </div>
                                                )}

                                                {/* 操作按钮 */}
                                                <div
                                                    className="flex items-center justify-between pt-3 border-t border-gray-100 dark:border-gray-700">
                                                    <button
                                                        onClick={() => viewArticle(article)}
                                                        className="flex items-center gap-1 text-xs sm:text-sm text-gray-600 dark:text-gray-400 hover:text-blue-600 dark:hover:text-blue-400 transition-colors"
                                                    >
                                                        <Eye className="w-3.5 h-3.5"/>
                                                        查看
                                                    </button>

                                                    <div className="relative">
                                                        <button
                                                            onClick={() => setActiveMenu(activeMenu === article.id ? null : article.id)}
                                                            className="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                                                        >
                                                            <MoreVertical
                                                                className="w-4 h-4 text-gray-600 dark:text-gray-400"/>
                                                        </button>

                                                        {/* 下拉菜单 */}
                                                        {activeMenu === article.id && (
                                                            <>
                                                                <div
                                                                    className="fixed inset-0 z-10"
                                                                    onClick={() => setActiveMenu(null)}
                                                                />
                                                                <div
                                                                    className="absolute right-0 bottom-full mb-2 w-40 sm:w-48 bg-white dark:bg-gray-800 rounded-xl shadow-xl border border-gray-200 dark:border-gray-700 py-1.5 z-20 animate-in fade-in zoom-in-95 duration-200">
                                                                    <button
                                                                        onClick={() => editArticle(article.id)}
                                                                        className="w-full px-3 sm:px-4 py-2 text-left text-xs sm:text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 flex items-center gap-2"
                                                                    >
                                                                        <Edit className="w-3.5 h-3.5"/>
                                                                        编辑
                                                                    </button>
                                                                    <button
                                                                        onClick={() => openPasswordModal(article.id)}
                                                                        className="w-full px-3 sm:px-4 py-2 text-left text-xs sm:text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 flex items-center gap-2"
                                                                    >
                                                                        <Key className="w-3.5 h-3.5"/>
                                                                        {(article as any).has_password ? '修改密码' : '设置密码'}
                                                                    </button>
                                                                    <button
                                                                        onClick={() => deleteArticle(article.id)}
                                                                        className="w-full px-3 sm:px-4 py-2 text-left text-xs sm:text-sm text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 flex items-center gap-2"
                                                                    >
                                                                        <Trash2 className="w-3.5 h-3.5"/>
                                                                        删除
                                                                    </button>
                                                                </div>
                                                            </>
                                                        )}
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>

                            {/* 分页 */}
                            {pageCount > 1 && (
                                <div className="mt-8 flex items-center justify-center gap-2">
                                    <button
                                        onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                                        disabled={currentPage === 1}
                                        className="px-4 py-2 rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-white dark:hover:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                                    >
                                        上一页
                                    </button>

                                    <span className="px-4 py-2 text-sm text-gray-600 dark:text-gray-400">
                                        第 {currentPage} / {pageCount} 页
                                    </span>

                                    <button
                                        onClick={() => setCurrentPage(p => Math.min(pageCount, p + 1))}
                                        disabled={currentPage === pageCount}
                                        className="px-4 py-2 rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-white dark:hover:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                                    >
                                        下一页
                                    </button>
                                </div>
                            )}
                        </>
                    ) : (
                        /* 空状态 */
                        <div className="py-20 text-center">
                            <div
                                className="inline-flex items-center justify-center w-24 h-24 bg-gradient-to-br from-blue-100 to-purple-100 dark:from-blue-900/20 dark:to-purple-900/20 rounded-3xl mb-6">
                                <FileText className="w-12 h-12 text-blue-400 dark:text-blue-500"/>
                            </div>
                            <h3 className="text-2xl font-bold text-gray-900 dark:text-white mb-3">暂无文章</h3>
                            <p className="text-gray-600 dark:text-gray-400 mb-8 max-w-md mx-auto">
                                开始您的创作之旅，点击下方的按钮创建第一篇文章
                            </p>
                            <button
                                onClick={createNewArticle}
                                className="inline-flex items-center gap-2 px-8 py-3 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white font-semibold rounded-xl transition-all duration-300 hover:shadow-xl hover:-translate-y-0.5 active:translate-y-0"
                            >
                                <Plus className="w-5 h-5"/>
                                创建第一篇文章
                            </button>
                        </div>
                    )}
                </div>

                {/* 密码设置对话框 */}
                {passwordModal.open && (
                    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
                        <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-2xl max-w-md w-full overflow-hidden animate-in fade-in zoom-in duration-200">
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

                            <div className="px-6 py-6">
                                <div className="mb-4">
                                    <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">
                                        为文章设置访问密码，访客需要输入密码才能查看文章内容。
                                    </p>
                                    {passwordModal.currentPassword && (
                                        <div className="mt-3 p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
                                            <p className="text-xs text-blue-700 dark:text-blue-300">
                                                <span className="font-medium">当前状态：</span>
                                                已设置密码
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
