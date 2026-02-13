"use client";

import React, {Suspense} from 'react';
import {useRouter, useSearchParams} from 'next/navigation';
import {
    FaChartLine,
    FaClock,
    FaEdit,
    FaFileAlt,
    FaPlus,
    FaRegFileAlt,
    FaSave,
    FaSearch,
    FaTimes,
    FaTrash
} from 'react-icons/fa';
import {
    type Article,
    ArticleManagementService,
    ArticleService,
    type ArticleStats,
    type Category,
    CategoryService,
    UserManagementService
} from '@/lib/api/index';

interface Author {
  id: number;
  username: string;
  email: string;
}

const ArticleManagementContent = () => {
  const router = useRouter();
  const searchParams = useSearchParams();
  
  const [articles, setArticles] = React.useState<Article[]>([]);
  const [categories, setCategories] = React.useState<Category[]>([]);
  const [authors, setAuthors] = React.useState<Author[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [currentPage, setCurrentPage] = React.useState(1);
  const [perPage, setPerPage] = React.useState(10);
  const [searchQuery, setSearchQuery] = React.useState('');
  const [statusFilter, setStatusFilter] = React.useState('');
  const [categoryFilter, setCategoryFilter] = React.useState('');
  const [authorFilter, setAuthorFilter] = React.useState('');
  const [totalPages, setTotalPages] = React.useState(1);
  const [stats, setStats] = React.useState<ArticleStats>({ 
    total_articles: 0,
    published_articles: 0,
    draft_articles: 0,
    total_views: 0
  });
  
  const [showModal, setShowModal] = React.useState(false);
  const [isEditing, setIsEditing] = React.useState(false);
  const [currentArticle, setCurrentArticle] = React.useState<Article | null>(null);
  
  // State for article form
  const [formData, setFormData] = React.useState({
    title: '',
    content: '',
    excerpt: '',
    cover_image: '',
    category_id: '',
    tags: '',
    status: 'Draft', // 默认为草稿
    hidden: false,
    is_vip_only: false,
    required_vip_level: 0,
    article_ad: '',
    is_featured: false,
  });
  
  const [formErrors, setFormErrors] = React.useState<Record<string, string>>({});
  const [formLoading, setFormLoading] = React.useState(false);
  
  const [showDeleteModal, setShowDeleteModal] = React.useState(false);
  const [deleteArticleId, setDeleteArticleId] = React.useState<number | null>(null);
  const [deleteArticleTitle, setDeleteArticleTitle] = React.useState('');

  // 处理状态筛选变化
  const handleStatusFilterChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setStatusFilter(e.target.value);
    setCurrentPage(1); // 重置到第一页
  };

  // 处理分类筛选变化
  const handleCategoryFilterChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setCategoryFilter(e.target.value);
    setCurrentPage(1); // 重置到第一页
  };

  // 处理作者筛选变化
  const handleAuthorFilterChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setAuthorFilter(e.target.value);
    setCurrentPage(1); // 重置到第一页
  };

  // 处理搜索变化
  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchQuery(e.target.value);
    setCurrentPage(1); // 重置到第一页
  };

  // 处理每页显示数量变化
  const handlePerPageChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setPerPage(Number(e.target.value));
    setCurrentPage(1); // 重置到第一页
  };

  // 跳转到指定页面
  const goToPage = (page: number) => {
    if (page >= 1 && page <= totalPages) {
      setCurrentPage(page);
    }
  };

  // 加载文章列表
  const loadArticles = async () => {
    setLoading(true);
    try {
      // 构建查询参数
      const params: Record<string, string> = {
        page: currentPage.toString(),
        per_page: perPage.toString(),
      };
      
      if (searchQuery) params.search = searchQuery;
      if (statusFilter) params.status = statusFilter;
      if (categoryFilter) params.category_id = categoryFilter;
      if (authorFilter) params.author_id = authorFilter;
      
      const response = await ArticleManagementService.getArticles(params);
      
      if (response.success) {
        // 确保response.data有正确的结构
        if (response.data && typeof response.data === 'object' && 'articles' in response.data) {
          setArticles(response.data.articles || []);
          setTotalPages(response.data.pagination?.pages || response.data.pagination?.total_pages || 1);
        } else {
          // 如果没有按预期格式返回，则直接使用数据
          setArticles(Array.isArray(response.data) ? response.data : []);
          setTotalPages(1); // 默认为1页
        }
      } else {
        console.error('Failed to load articles:', response.error);
        setArticles([]); // 在失败时设置为空数组
        setTotalPages(1);
      }
    } catch (error) {
      console.error('Failed to load articles:', error);
      setArticles([]); // 在异常时设置为空数组
      setTotalPages(1);
    } finally {
      setLoading(false);
    }
  };

  // 加载文章统计数据
  const loadArticleStats = async () => {
    try {
      const response = await ArticleManagementService.getArticleStats();
      if (response.success) {
        setStats(response.data || { 
          total_articles: 0,
          published_articles: 0,
          draft_articles: 0,
          total_views: 0
        });
      }
    } catch (error) {
      console.error('Failed to load article stats:', error);
    }
  };

  // 加载分类列表
  const loadCategories = async () => {
    try {
      // 使用管理API获取所有分类
      const response = await CategoryService.getCategories();
      if (response.success) {
        // 确保response.data有正确的结构
        if (response.data && typeof response.data === 'object' && 'categories' in response.data) {
          setCategories(response.data.categories || []);
        } else {
          // 如果没有按预期格式返回，则直接使用数据
          setCategories(Array.isArray(response.data) ? response.data : []);
        }
      } else {
        setCategories([]); // 在失败时设置为空数组
      }
    } catch (error) {
      console.error('Failed to load categories:', error);
      setCategories([]); // 在异常时设置为空数组
    }
  };

  // 加载作者列表
  const loadAuthors = async () => {
    try {
      const response = await UserManagementService.getUsers();
      if (response.success) {
        // 确保response.data有正确的结构
        if (response.data && typeof response.data === 'object' && 'users' in response.data) {
          setAuthors(response.data.users || []);
        } else {
          // 如果没有按预期格式返回，则直接使用数据
          setAuthors(Array.isArray(response.data) ? response.data : []);
        }
      } else {
        setAuthors([]); // 在失败时设置为空数组
      }
    } catch (error) {
      console.error('Failed to load authors:', error);
      setAuthors([]); // 在异常时设置为空数组
    }
  };

  // 初始化加载数据
  React.useEffect(() => {
    loadArticles();
    loadArticleStats();
    loadCategories();
    loadAuthors();
    
    // 检查URL参数是否要求自动执行某个功能
    const autoRun = searchParams.get('autoRun');
    if (autoRun) {
      // 等待数据加载完成后执行相应功能
      setTimeout(() => {
        executeAutoRun(autoRun);
      }, 100);
    }
  }, [currentPage, perPage, searchQuery, statusFilter, categoryFilter, authorFilter]);
  
  // 根据autoRun参数执行相应功能
  const executeAutoRun = (action: string) => {
    switch (action.toLowerCase()) {
      case 'showarticlemodal':
      case 'show_article_modal':
        handleAddArticle();
        break;
      // 可以在这里扩展更多功能
      default:
        console.log(`Unknown autoRun action: ${action}`);
        break;
    }
  };

  const handleAddArticle = () => {
    // 重置表单数据
    setFormData({
      title: '',
      content: '',
      excerpt: '',
      cover_image: '',
      category_id: '',
      tags: '',
      status: 'Draft', // 默认为草稿
      hidden: false,
      is_vip_only: false,
      required_vip_level: 0,
      article_ad: '',
      is_featured: false,
    });
    setFormErrors({});
    setCurrentArticle(null);
    setIsEditing(false);
    setShowModal(true);
  };

  const handleEditArticle = (article: Article) => {
    // 设置表单数据为当前文章数据
    setFormData({
      title: article.title || '',
      content: article.content || '',
      excerpt: article.excerpt || '',
      cover_image: article.cover_image || '',
      category_id: article.category_id ? article.category_id.toString() : '',
      tags: Array.isArray(article.tags) ? article.tags.join(',') : '',
      status: article.status === '1' || article.status === 'Published' ? 'Published' : 'Draft',
      hidden: !!article.hidden,
      is_vip_only: !!article.is_vip_only,
      required_vip_level: article.required_vip_level || 0,
      article_ad: article.article_ad || '',
      is_featured: !!article.is_featured,
    });
    setFormErrors({});
    setCurrentArticle(article);
    setIsEditing(true);
    setShowModal(true);
  };

  const handleDeleteClick = (id: number, title: string) => {
    setDeleteArticleId(id);
    setDeleteArticleTitle(title);
    setShowDeleteModal(true);
  };

  const confirmDeleteArticle = async () => {
    if (deleteArticleId) {
      try {
        // 使用ArticleManagementService删除文章
        const response = await ArticleManagementService.deleteArticle(deleteArticleId);
        
        if (response.success) {
          // Refresh the articles list
          await loadArticles();
          await loadArticleStats();
          setShowDeleteModal(false);
        } else {
          console.error('Failed to delete article:', response.error);
        }
      } catch (error) {
        console.error('Failed to delete article:', error);
      }
    }
  };

  // 处理表单输入变化
  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    const { name, value, type } = e.target;
    const checked = type === 'checkbox' ? (e.target as HTMLInputElement).checked : undefined;
    
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }));
  };

  // 处理数字输入
  const handleNumberChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: Number(value)
    }));
  };

  // 提交表单
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormLoading(true);
    setFormErrors({});
    
    try {
      // 验证必填字段
      const errors: Record<string, string> = {};
      if (!formData.title.trim()) {
        errors.title = '标题不能为空';
      }
      if (!formData.content.trim()) {
        errors.content = '内容不能为空';
      }
      
      if (Object.keys(errors).length > 0) {
        setFormErrors(errors);
        setFormLoading(false);
        return;
      }
      
      // 准备表单数据
      const articleData = new FormData();
      articleData.append('title', formData.title);
      articleData.append('content', formData.content);
      articleData.append('excerpt', formData.excerpt);
      articleData.append('cover_image', formData.cover_image);
      if (formData.category_id) {
        articleData.append('category_id', formData.category_id);
      }
      articleData.append('tags', formData.tags);
      articleData.append('status', formData.status === 'Published' ? '1' : '0');
      articleData.append('hidden', formData.hidden ? '1' : '0');
      articleData.append('is_vip_only', formData.is_vip_only ? '1' : '0');
      articleData.append('required_vip_level', formData.required_vip_level.toString());
      articleData.append('article_ad', formData.article_ad);
      articleData.append('is_featured', formData.is_featured ? '1' : '0');
      
      let response;
      if (isEditing && currentArticle) {
        // 更新现有文章
        response = await ArticleService.updateArticle(currentArticle.id, articleData);
      } else {
        // 创建新文章
        response = await ArticleService.createArticle(articleData);
      }
      
      if (response.success) {
        // 刷新文章列表
        await loadArticles();
        await loadArticleStats();
        
        // 关闭模态框
        setShowModal(false);
        
        // 重置表单
        setFormData({
          title: '',
          content: '',
          excerpt: '',
          cover_image: '',
          category_id: '',
          tags: '',
          status: 'Draft',
          hidden: false,
          is_vip_only: false,
          required_vip_level: 0,
          article_ad: '',
          is_featured: false,
        });
      } else {
        setFormErrors({ submit: response.error || '操作失败' });
      }
    } catch (error) {
      console.error('Failed to save article:', error);
      setFormErrors({ submit: '保存文章时发生错误' });
    } finally {
      setFormLoading(false);
    }
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit'
    });
  };

  const getStatusBadgeColor = (status: number | string) => {
    let statusStr: string;
    if (typeof status === 'number') {
      statusStr = status === 1 ? 'Published' : 'Draft';
    } else {
      statusStr = status;
    }

    switch (statusStr) {
      case 'Published':
        return 'bg-green-100 text-green-800';
      case 'Draft':
        return 'bg-yellow-100 text-yellow-800';
      case 'Deleted':
        return 'bg-gray-100 text-gray-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getStatusText = (status: number | string) => {
    let statusStr: string;
    if (typeof status === 'number') {
      statusStr = status === 1 ? 'Published' : 'Draft';
    } else {
      statusStr = status;
    }

    switch (statusStr) {
      case 'Published':
        return '已发布';
      case 'Draft':
        return '草稿';
      case 'Deleted':
        return '已删除';
      default:
        return typeof status === 'number' ? (status === 1 ? '已发布' : '草稿') : status;
    }
  };

  return (
    <div className="space-y-6">
      {/* 文章统计卡片 */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 lg:gap-6 mb-6">
        <div className="bg-white rounded-lg p-4 lg:p-6 shadow-sm border border-gray-200">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">总文章数</p>
              <p className="text-2xl font-bold">{stats.total_articles}</p>
            </div>
            <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center">
              <FaFileAlt className="w-6 h-6 text-blue-600" />
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg p-4 lg:p-6 shadow-sm border border-gray-200">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">已发布</p>
              <p className="text-2xl font-bold">{stats.published_articles}</p>
            </div>
            <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center">
              <FaRegFileAlt className="w-6 h-6 text-green-600" />
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg p-4 lg:p-6 shadow-sm border border-gray-200">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">草稿</p>
              <p className="text-2xl font-bold">{stats.draft_articles}</p>
            </div>
            <div className="w-12 h-12 bg-yellow-100 rounded-lg flex items-center justify-center">
              <FaClock className="w-6 h-6 text-yellow-600" />
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg p-4 lg:p-6 shadow-sm border border-gray-200">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">总浏览量</p>
              <p className="text-2xl font-bold">{stats.total_views}</p>
            </div>
            <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center">
              <FaChartLine className="w-6 h-6 text-purple-600" />
            </div>
          </div>
        </div>
      </div>

      {/* 筛选器 */}
      <div className="bg-white rounded-lg p-4 lg:p-6 shadow-sm border border-gray-200 mb-6">
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="flex-1">
            <label className="block text-sm font-medium text-gray-700 mb-1">状态筛选</label>
            <select 
              value={statusFilter}
              onChange={handleStatusFilterChange}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">全部状态</option>
              <option value="Published">已发布</option>
              <option value="Draft">草稿</option>
              <option value="Deleted">已删除</option>
            </select>
          </div>

          <div className="flex-1">
            <label className="block text-sm font-medium text-gray-700 mb-1">分类筛选</label>
            <select 
              value={categoryFilter}
              onChange={handleCategoryFilterChange}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">全部分类</option>
              {Array.isArray(categories) && categories.map(category => (
                <option key={category.id} value={category.id.toString()}>
                  {category.name}
                </option>
              ))}
            </select>
          </div>

          <div className="flex-1">
            <label className="block text-sm font-medium text-gray-700 mb-1">作者筛选</label>
            <select 
              value={authorFilter}
              onChange={handleAuthorFilterChange}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">全部作者</option>
              {Array.isArray(authors) && authors.map(author => (
                <option key={author.id} value={author.id.toString()}>
                  {author.username}
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-end">
            <button 
              onClick={() => {
                setSearchQuery('');
                setStatusFilter('');
                setCategoryFilter('');
                setAuthorFilter('');
                setCurrentPage(1);
              }}
              className="px-4 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50"
            >
              清除筛选
            </button>
          </div>
        </div>
      </div>

      {/* 顶部控制栏 */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200">
        <div className="p-4 lg:p-6 border-b border-gray-200">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <h3 className="text-lg font-semibold">文章列表</h3>
            <div className="flex items-center space-x-2">
              <div className="relative">
                <input 
                  type="text" 
                  placeholder="搜索文章..."
                  value={searchQuery}
                  onChange={handleSearchChange}
                  className="border border-gray-300 rounded-lg pl-10 pr-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 w-32 sm:w-48 lg:w-64"
                />
                <FaSearch className="w-4 h-4 absolute left-3 top-3 text-gray-400" />
              </div>
              
              <button 
                onClick={handleAddArticle}
                className="bg-blue-600 text-white px-3 lg:px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors flex items-center space-x-2"
              >
                <FaPlus className="w-4 h-4" />
                <span className="hidden sm:inline">添加文章</span>
              </button>
              
              <select 
                value={perPage}
                onChange={handlePerPageChange}
                className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="10">每页 10 条</option>
                <option value="25">每页 25 条</option>
                <option value="50">每页 50 条</option>
              </select>
            </div>
          </div>
        </div>

        {/* 加载状态 */}
        {loading ? (
          <div className="p-8 text-center">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            <p className="mt-2 text-gray-500">加载中...</p>
          </div>
        ) : (
          <>
            {/* 文章表格 */}
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-3 lg:px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      标题
                    </th>
                    <th className="px-3 lg:px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider hidden sm:table-cell">
                      作者
                    </th>
                    <th className="px-3 lg:px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider hidden md:table-cell">
                      分类
                    </th>
                    <th className="px-3 lg:px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      状态
                    </th>
                    <th className="px-3 lg:px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider hidden lg:table-cell">
                      浏览量
                    </th>
                    <th className="px-3 lg:px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider hidden md:table-cell">
                      创建时间
                    </th>
                    <th className="px-3 lg:px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      操作
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {articles.length > 0 ? (
                    articles.map(article => (
                      <tr key={article.id}>
                        <td className="px-3 lg:px-6 py-4">
                          <div className="flex items-start space-x-3">
                            {article.cover_image ? (
                              <img 
                                src={article.cover_image} 
                                alt={article.title} 
                                className="w-12 h-12 rounded-lg object-cover flex-shrink-0" 
                              />
                            ) : (
                              <div className="w-12 h-12 bg-gray-200 rounded-lg flex items-center justify-center flex-shrink-0">
                                <FaFileAlt className="w-6 h-6 text-gray-400" />
                              </div>
                            )}
                            <div className="min-w-0 flex-1">
                              <div className="text-sm font-medium text-gray-900 truncate">{article.title}</div>
                              {article.summary && (
                                <div className="text-xs text-gray-500">
                                  {article.summary}
                                </div>
                              )}
                              {article.tags && Array.isArray(article.tags) && article.tags.length > 0 && (
                                <div className="flex flex-wrap gap-1 mt-2">
                                  {article.tags.slice(0, 3).map((tag: string, idx: number) => (
                                    <span 
                                      key={idx} 
                                      className="inline-block px-2 py-1 text-xs bg-gray-100 text-gray-600 rounded"
                                    >
                                      {tag}
                                    </span>
                                  ))}
                                  {article.tags.length > 3 && (
                                    <span className="text-xs text-gray-400">+{article.tags.length - 3}</span>
                                  )}
                                </div>
                              )}
                            </div>
                          </div>
                        </td>
                        <td className="px-3 lg:px-6 py-4 whitespace-nowrap text-sm text-gray-500 hidden sm:table-cell">
                          {article.author ? article.author.username : '-'}
                        </td>
                        <td className="px-3 lg:px-6 py-4 whitespace-nowrap text-sm text-gray-500 hidden md:table-cell">
                          {article.category ? article.category.name : '-'}
                        </td>
                        <td className="px-3 lg:px-6 py-4 whitespace-nowrap">
                          <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusBadgeColor(article.status)}`}>
                            {getStatusText(article.status)}
                          </span>
                        </td>
                        <td className="px-3 lg:px-6 py-4 whitespace-nowrap text-sm text-gray-500 hidden lg:table-cell">
                          {article.views_count || 0}
                        </td>
                        <td className="px-3 lg:px-6 py-4 whitespace-nowrap text-sm text-gray-500 hidden md:table-cell">
                          {formatDate(article.created_at)}
                        </td>
                        <td className="px-3 lg:px-6 py-4 whitespace-nowrap text-sm font-medium">
                          <div className="flex space-x-2">
                            <button 
                              onClick={() => handleEditArticle(article)}
                              className="text-blue-600 hover:text-blue-900"
                            >
                              <FaEdit className="w-4 h-4" />
                            </button>
                            <button 
                              onClick={() => handleDeleteClick(article.id, article.title)}
                              className="text-red-600 hover:text-red-900"
                            >
                              <FaTrash className="w-4 h-4" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={7} className="px-3 lg:px-6 py-8 text-center text-gray-500">
                        没有找到文章
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>

            {/* 分页 */}
            <div className="px-4 lg:px-6 py-4 border-t border-gray-200">
              <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
                <div className="text-sm text-gray-500">
                  显示第 {(currentPage - 1) * perPage + 1}-{Math.min(currentPage * perPage, stats.total_articles)} 条，共 {stats.total_articles} 条记录
                </div>
                <div className="flex items-center space-x-2">
                  <button
                    onClick={() => goToPage(currentPage - 1)}
                    disabled={currentPage === 1}
                    className="px-3 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    上一页
                  </button>
                  <div className="flex items-center space-x-1">
                    {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                      let pageNum;
                      if (totalPages <= 5) {
                        pageNum = i + 1;
                      } else if (currentPage <= 3) {
                        pageNum = i + 1;
                      } else if (currentPage >= totalPages - 2) {
                        pageNum = totalPages - 4 + i;
                      } else {
                        pageNum = currentPage - 2 + i;
                      }
                      
                      return (
                        <button
                          key={pageNum}
                          onClick={() => goToPage(pageNum)}
                          className={`px-2 lg:px-3 py-2 text-sm border rounded-lg ${
                            currentPage === pageNum
                              ? 'bg-blue-600 text-white border-blue-600'
                              : 'border-gray-300 hover:bg-gray-50'
                          }`}
                        >
                          {pageNum}
                        </button>
                      );
                    })}
                  </div>
                  <button
                    onClick={() => goToPage(currentPage + 1)}
                    disabled={currentPage === totalPages}
                    className="px-3 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    下一页
                  </button>
                </div>
              </div>
            </div>
          </>
        )}
      </div>

      {/* 删除确认模态框 */}
      {showDeleteModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-sm w-full transform transition-all">
            <div className="p-4 lg:p-6">
              <div className="flex items-center space-x-3 mb-4">
                <div className="w-10 h-10 bg-red-100 rounded-full flex items-center justify-center">
                  <FaTrash className="w-5 h-5 text-red-600" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold">确认删除</h3>
                  <p className="text-sm text-gray-500">此操作无法撤销</p>
                </div>
              </div>

              <p className="text-gray-700 mb-6">
                确定要删除文章 &#34;<span className="font-medium">{deleteArticleTitle}</span>&#34; 吗？
              </p>

              <div className="flex items-center justify-end space-x-3">
                <button
                  onClick={() => setShowDeleteModal(false)}
                  className="px-4 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50"
                >
                  取消
                </button>
                <button
                  onClick={confirmDeleteArticle}
                  className="bg-red-600 text-white px-4 py-2 text-sm rounded-lg hover:bg-red-700"
                >
                  删除
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 文章创建/编辑模态框 */}
      {showModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4 overflow-y-auto">
          <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6 border-b border-gray-200">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-semibold">
                  {isEditing ? '编辑文章' : '添加文章'}
                </h3>
                <button 
                  onClick={() => setShowModal(false)}
                  className="text-gray-400 hover:text-gray-600"
                >
                  <FaTimes className="w-5 h-5" />
                </button>
              </div>
            </div>

            <form onSubmit={handleSubmit} className="p-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="md:col-span-2">
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    标题 *
                  </label>
                  <input
                    type="text"
                    name="title"
                    value={formData.title}
                    onChange={handleInputChange}
                    className={`w-full border rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 ${formErrors.title ? 'border-red-500' : 'border-gray-300'}`}
                    placeholder="请输入文章标题"
                  />
                  {formErrors.title && <p className="text-red-500 text-sm mt-1">{formErrors.title}</p>}
                </div>

                <div className="md:col-span-2">
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    内容 *
                  </label>
                  <textarea
                    name="content"
                    value={formData.content}
                    onChange={handleInputChange}
                    rows={8}
                    className={`w-full border rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 ${formErrors.content ? 'border-red-500' : 'border-gray-300'}`}
                    placeholder="请输入文章内容"
                  />
                  {formErrors.content && <p className="text-red-500 text-sm mt-1">{formErrors.content}</p>}
                </div>

                <div className="md:col-span-2">
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    摘要
                  </label>
                  <textarea
                    name="excerpt"
                    value={formData.excerpt}
                    onChange={handleInputChange}
                    rows={3}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="请输入文章摘要"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    封面图片URL
                  </label>
                  <input
                    type="text"
                    name="cover_image"
                    value={formData.cover_image}
                    onChange={handleInputChange}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="封面图片URL"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    分类
                  </label>
                  <select
                    name="category_id"
                    value={formData.category_id}
                    onChange={handleInputChange}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="">请选择分类</option>
                    {categories.map(category => (
                      <option key={category.id} value={category.id.toString()}>
                        {category.name}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    标签
                  </label>
                  <input
                    type="text"
                    name="tags"
                    value={formData.tags}
                    onChange={handleInputChange}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="多个标签用逗号分隔"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    状态
                  </label>
                  <select
                    name="status"
                    value={formData.status}
                    onChange={handleInputChange}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="Draft">草稿</option>
                    <option value="Published">已发布</option>
                  </select>
                </div>

                <div className="md:col-span-2">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="flex items-center">
                        <input
                          type="checkbox"
                          name="hidden"
                          checked={formData.hidden}
                          onChange={handleInputChange}
                          className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                        />
                        <span className="ml-2 text-sm text-gray-700">隐藏</span>
                      </label>
                    </div>
                    <div>
                      <label className="flex items-center">
                        <input
                          type="checkbox"
                          name="is_vip_only"
                          checked={formData.is_vip_only}
                          onChange={handleInputChange}
                          className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                        />
                        <span className="ml-2 text-sm text-gray-700">仅VIP可访问</span>
                      </label>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        所需VIP等级
                      </label>
                      <input
                        type="number"
                        name="required_vip_level"
                        value={formData.required_vip_level}
                        onChange={handleNumberChange}
                        min="0"
                        max="3"
                        className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                      />
                    </div>
                    <div>
                      <label className="flex items-center">
                        <input
                          type="checkbox"
                          name="is_featured"
                          checked={formData.is_featured}
                          onChange={handleInputChange}
                          className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                        />
                        <span className="ml-2 text-sm text-gray-700">特色文章</span>
                      </label>
                    </div>
                  </div>
                </div>
              </div>

              <div className="mt-6 flex justify-end space-x-3">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="px-4 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50"
                >
                  取消
                </button>
                <button
                  type="submit"
                  disabled={formLoading}
                  className="bg-blue-600 text-white px-4 py-2 text-sm rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
                >
                  {formLoading ? (
                    <>
                      <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                      保存中...
                    </>
                  ) : (
                    <>{isEditing ? <><FaSave className="mr-2" /> 更新</> : <><FaPlus className="mr-2" /> 创建</>}</>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

const ArticleManagement = () => {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <ArticleManagementContent />
    </Suspense>
  );
};

export default ArticleManagement;