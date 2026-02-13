'use client';

import React, {useEffect, useState} from 'react';
import {FaEdit, FaFolder, FaPlus, FaRedo, FaSearch, FaTrash} from 'react-icons/fa';
import {type Category, CategoryService} from '@/lib/api';

interface CategoryWithCounts {
    category: Category;
    article_count: number;
    subscriber_count: number;
}

const CategoryManagement = () => {
    const [categories, setCategories] = useState<CategoryWithCounts[]>([]);
    const [loading, setLoading] = useState(true);
    const [currentPage, setCurrentPage] = useState(1);
    const [searchQuery, setSearchQuery] = useState('');
    const [totalPages, setTotalPages] = useState(1);
    const [totalCategories, setTotalCategories] = useState(0);

    const [showModal, setShowModal] = useState(false);
    const [isEditing, setIsEditing] = useState(false);
    const [currentCategory, setCurrentCategory] = useState<Category | null>(null);

    const [showDeleteModal, setShowDeleteModal] = useState(false);
    const [deleteCategoryId, setDeleteCategoryId] = useState<number | null>(null);
    const [deleteCategoryName, setDeleteCategoryName] = useState('');

    const [errorMessage, setErrorMessage] = useState<string | null>(null);

    // 加载分类数据
    useEffect(() => {
        loadCategories();
    }, [currentPage, searchQuery]);

    const loadCategories = async () => {
        try {
            setLoading(true);

            const response = await CategoryService.getCategoriesWithStats({
                page: currentPage,
                per_page: 10 // 默认每页10条
            });

            if (response.success) {
                // 处理后端返回的实际数据结构
                if (response.data && typeof response.data === 'object' && 'categories' in response.data) {
                    // 新版API格式：{ categories: [], pagination: {} }
                    setCategories(response.data.categories || []);
                    const pagination = response.data.pagination;
                    setTotalPages(pagination?.total_pages || 1);
                    setTotalCategories(pagination?.total || 0);
                } else if (Array.isArray(response.data)) {
                    // 兼容旧版API格式：直接返回数组
                    const categoriesData = response.data as any[];
                    const categoriesWithCounts = categoriesData.map((category: any) => ({
                        category: category,
                        article_count: category.article_count || 0,
                        subscriber_count: category.subscriber_count || 0
                    }));
                    setCategories(categoriesWithCounts);
                    // 由于后端没有提供分页信息，暂时设置为1
                    setTotalPages(1);
                    setTotalCategories(categoriesWithCounts.length);
                } else {
                    // 其他情况
                    setCategories([]);
                    setTotalPages(1);
                    setTotalCategories(0);
                }
            } else {
                console.error('Failed to load categories:', response.error || response.message || 'Unknown error');
                setCategories([]);
                setTotalPages(1);
                setTotalCategories(0);
            }
        } catch (error) {
            console.error('Failed to load categories:', error);
            setCategories([]);
            setTotalPages(1);
            setTotalCategories(0);
        } finally {
            setLoading(false);
        }
    };

    const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        setSearchQuery(e.target.value);
        setCurrentPage(1); // Reset to first page when searching
    };

    const handleKeyPress = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter') {
            setCurrentPage(1);
        }
    };

    const handleReset = () => {
        setSearchQuery('');
        setCurrentPage(1);
    };

    const goToPage = (page: number) => {
        if (page >= 1 && page <= totalPages) {
            setCurrentPage(page);
        }
    };

    const handleCreateCategory = () => {
        setCurrentCategory({
            id: 0,
            name: '',
            description: '',
            created_at: new Date().toISOString()
        });
        setIsEditing(false);
        setShowModal(true);
    };

    const handleEditCategory = (category: Category) => {
        setCurrentCategory(category);
        setIsEditing(true);
        setShowModal(true);
    };

    const handleDeleteClick = (id: number, name: string) => {
        setDeleteCategoryId(id);
        setDeleteCategoryName(name);
        setShowDeleteModal(true);
    };

    const confirmDeleteCategory = async () => {
        if (deleteCategoryId) {
            try {
                // 使用真实的API删除分类
                const response = await CategoryService.deleteCategory(deleteCategoryId);

                if (response.success) {
                    // Refresh the categories list
                    loadCategories();
                    setShowDeleteModal(false);
                } else {
                    console.error('Failed to delete category:', response.error);
                }
            } catch (error) {
                console.error('Failed to delete category:', error);
            }
        }
    };

    const handleSubmitCategory = async (e: React.FormEvent) => {
        e.preventDefault();

        if (!currentCategory) return;

        try {
            if (isEditing) {
                // 更新分类
                const response = await CategoryService.updateCategory(currentCategory.id, {
                    name: currentCategory.name,
                    description: currentCategory.description
                });

                if (response.success) {
                    setShowModal(false);
                    setErrorMessage(null); // 清除错误信息
                    loadCategories();
                } else {
                    setErrorMessage(response.error || '更新分类失败');
                    console.error('Failed to update category:', response.error);
                }
            } else {
                // 创建新分类
                const response = await CategoryService.createCategory({
                    name: currentCategory.name,
                    description: currentCategory.description
                });

                if (response.success) {
                    setShowModal(false);
                    setErrorMessage(null); // 清除错误信息
                    loadCategories();
                } else {
                    setErrorMessage(response.error || response.message || '创建分类失败');
                    console.error('Failed to create category:', response.error || response.message || 'Unknown error');
                }
            }
        } catch (error) {
            setErrorMessage(error instanceof Error ? error.message : '保存分类时发生未知错误');
            console.error('Failed to save category:', error);
        }
    };

    const formatDate = (dateString?: string) => {
        if (!dateString) {
            return 'N/A';
        }
        const date = new Date(dateString);
        return date.toLocaleDateString('zh-CN', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit'
        });
    };

    // 生成页码数组
    const getPageNumbers = () => {
        const delta = 2;
        const range = [];
        const rangeWithDots = [];

        for (let i = Math.max(2, currentPage - delta); i <= Math.min(totalPages - 1, currentPage + delta); i++) {
            range.push(i);
        }

        if (currentPage - delta > 2) {
            rangeWithDots.push(1, '...');
        } else {
            rangeWithDots.push(1);
        }

        rangeWithDots.push(...range);

        if (currentPage + delta < totalPages - 1) {
            rangeWithDots.push('...', totalPages);
        } else if (totalPages > 1) {
            rangeWithDots.push(totalPages);
        }

        return rangeWithDots;
    };

    return (
        <div className="space-y-6">
            {/* 操作栏 */}
            <div className="bg-white rounded-xl shadow-sm p-6 mb-6">
                <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
                    <div className="flex items-center gap-4">
                        <button
                            onClick={handleCreateCategory}
                            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors flex items-center"
                        >
                            <FaPlus className="mr-2"/>
                            新建分类
                        </button>
                    </div>
                    <div className="flex items-center gap-4">
                        <div className="relative flex-1 md:w-64">
                            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                                <FaSearch className="text-gray-400"/>
                            </div>
                            <input
                                type="text"
                                value={searchQuery}
                                onChange={handleSearchChange}
                                onKeyPress={handleKeyPress}
                                className="block w-full pl-10 pr-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                                placeholder="搜索分类..."
                            />
                        </div>
                        <button
                            onClick={() => setCurrentPage(1)}
                            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors flex items-center"
                        >
                            <FaSearch className="mr-2"/>
                            搜索
                        </button>
                        <button
                            onClick={handleReset}
                            className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors flex items-center"
                        >
                            <FaRedo className="mr-2"/>
                            重置
                        </button>
                    </div>
                </div>
            </div>

            {/* 分类列表 */}
            <div className="bg-white rounded-xl shadow-sm overflow-hidden">
                {/* 表格头部 */}
                <div className="px-6 py-4 border-b border-gray-200 flex justify-between items-center">
                    <h2 className="text-lg font-semibold text-gray-800">分类列表</h2>
                    <div className="text-sm text-gray-500">
                        共 <span className="font-semibold">{totalCategories}</span> 个分类
                    </div>
                </div>

                {/* 分类表格 */}
                {loading ? (
                    <div className="p-8 text-center">
                        <div
                            className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                        <p className="mt-2 text-gray-500">加载中...</p>
                    </div>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="min-w-full divide-y divide-gray-200">
                            <thead className="bg-gray-50">
                            <tr>
                                <th scope="col"
                                    className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                    分类名称
                                </th>
                                <th scope="col"
                                    className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                    描述
                                </th>
                                <th scope="col"
                                    className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                    文章数量
                                </th>
                                <th scope="col"
                                    className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                    订阅数量
                                </th>
                                <th scope="col"
                                    className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                    创建时间
                                </th>
                                <th scope="col"
                                    className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                    操作
                                </th>
                            </tr>
                            </thead>
                            <tbody className="bg-white divide-y divide-gray-200">
                            {categories.length > 0 ? (
                                categories.map((item: CategoryWithCounts, index: number) => (
                                    <tr key={item.category.id} className="hover:bg-gray-50 transition-colors">
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <div className="flex items-center">
                                                <div
                                                    className="flex-shrink-0 h-10 w-10 rounded-full bg-blue-100 flex items-center justify-center text-blue-600">
                                                    <FaFolder/>
                                                </div>
                                                <div className="ml-4">
                                                    <div
                                                        className="text-sm font-medium text-gray-900">{item.category.name}</div>
                                                </div>
                                            </div>
                                        </td>
                                        <td className="px-6 py-4">
                                            <div className="text-sm text-gray-700 max-w-xs truncate">
                                                {item.category.description || '暂无描述'}
                                            </div>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <div className="text-sm text-gray-900">{item.article_count}</div>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <div className="text-sm text-gray-900">{item.subscriber_count}</div>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                            {item.category.created_at ? formatDate(item.category.created_at) : 'N/A'}
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                                            <div className="flex space-x-2">
                                                <button
                                                    onClick={() => handleEditCategory(item.category)}
                                                    className="text-blue-600 hover:text-blue-700"
                                                >
                                                    <FaEdit/>
                                                </button>
                                                <button
                                                    onClick={() => handleDeleteClick(item.category.id, item.category.name)}
                                                    className="text-red-600 hover:text-red-700"
                                                >
                                                    <FaTrash/>
                                                </button>
                                            </div>
                                        </td>
                                    </tr>
                                ))
                            ) : (
                                <tr>
                                    <td colSpan={6} className="px-6 py-8 text-center text-gray-500">
                                        没有找到分类
                                    </td>
                                </tr>
                            )}
                            </tbody>
                        </table>
                    </div>
                )}

                {/* 分页 */}
                <div
                    className="px-6 py-4 border-t border-gray-200 flex flex-col sm:flex-row items-center justify-between">
                    <div className="flex items-center space-x-2 mb-4 sm:mb-0">
                        {currentPage > 1 && (
                            <button
                                onClick={() => goToPage(currentPage - 1)}
                                className="px-3 py-1 rounded border border-gray-300 text-sm text-gray-700 hover:bg-gray-50"
                            >
                                上一页
                            </button>
                        )}

                        {getPageNumbers().map((page, index) => (
                            <React.Fragment key={index}>
                                {page === '...' ? (
                                    <span className="px-2 text-sm text-gray-500">...</span>
                                ) : (
                                    <button
                                        onClick={() => goToPage(Number(page))}
                                        className={`px-3 py-1 rounded ${
                                            currentPage === page
                                                ? 'bg-blue-600 text-white text-sm'
                                                : 'border border-gray-300 text-sm text-gray-700 hover:bg-gray-50'
                                        }`}
                                    >
                                        {page}
                                    </button>
                                )}
                            </React.Fragment>
                        ))}

                        {currentPage < totalPages && (
                            <button
                                onClick={() => goToPage(currentPage + 1)}
                                className="px-3 py-1 rounded border border-gray-300 text-sm text-gray-700 hover:bg-gray-50"
                            >
                                下一页
                            </button>
                        )}
                    </div>
                    <div className="text-sm text-gray-500">
                        显示 {categories.length} 个，共 {totalCategories} 个分类
                    </div>
                </div>
            </div>

            {/* 分类模态框 */}
            {showModal && currentCategory && (
                <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
                    <div className="bg-white rounded-lg shadow-xl max-w-md w-full transform transition-all">
                        <div className="p-6">
                            <h3 className="text-lg font-semibold text-gray-800 mb-4">
                                {isEditing ? '编辑分类' : '新建分类'}
                            </h3>

                            <form onSubmit={handleSubmitCategory} className="space-y-4">
                                <input
                                    type="hidden"
                                    id="categoryId"
                                    name="category_id"
                                    value={currentCategory.id}
                                />

                                {errorMessage && (
                                    <div className="rounded-md bg-red-50 p-4 mb-4">
                                        <div className="flex">
                                            <div className="flex-shrink-0">
                                                <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20"
                                                     fill="currentColor">
                                                    <path fillRule="evenodd"
                                                          d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                                                          clipRule="evenodd"/>
                                                </svg>
                                            </div>
                                            <div className="ml-3">
                                                <h3 className="text-sm font-medium text-red-800">{errorMessage}</h3>
                                            </div>
                                        </div>
                                    </div>
                                )}

                                <div>
                                    <label htmlFor="categoryName"
                                           className="block text-sm font-medium text-gray-700 mb-1">
                                        分类名称 *
                                    </label>
                                    <input
                                        type="text"
                                        id="categoryName"
                                        value={currentCategory.name}
                                        onChange={(e) => {
                                            setCurrentCategory({...currentCategory, name: e.target.value});
                                            if (errorMessage) setErrorMessage(null);
                                        }}
                                        required
                                        className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                                    />
                                </div>

                                <div>
                                    <label htmlFor="categoryDescription"
                                           className="block text-sm font-medium text-gray-700 mb-1">
                                        分类描述
                                    </label>
                                    <textarea
                                        id="categoryDescription"
                                        value={currentCategory.description || ''}
                                        onChange={(e) => {
                                            setCurrentCategory({...currentCategory, description: e.target.value});
                                            if (errorMessage) setErrorMessage(null);
                                        }}
                                        rows={3}
                                        className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                                    />
                                </div>

                                <div className="flex justify-end space-x-3 pt-4 border-t border-gray-200">
                                    <button
                                        type="button"
                                        onClick={() => {
                                            setShowModal(false);
                                            setErrorMessage(null); // 关闭模态框时清除错误信息
                                        }}
                                        className="px-4 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300 transition-colors"
                                    >
                                        取消
                                    </button>
                                    <button
                                        type="submit"
                                        className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
                                    >
                                        保存
                                    </button>
                                </div>
                            </form>
                        </div>
                    </div>
                </div>
            )}

            {/* 删除确认模态框 */}
            {showDeleteModal && (
                <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
                    <div className="bg-white rounded-lg shadow-xl max-w-sm w-full transform transition-all">
                        <div className="p-6">
                            <div className="flex items-center space-x-3 mb-4">
                                <div className="w-10 h-10 bg-red-100 rounded-full flex items-center justify-center">
                                    <FaTrash className="w-5 h-5 text-red-600"/>
                                </div>
                                <div>
                                    <h3 className="text-lg font-semibold">确认删除</h3>
                                    <p className="text-sm text-gray-500">此操作无法撤销</p>
                                </div>
                            </div>

                            <p className="text-gray-700 mb-6">
                                您确定要删除分类 &#34;<span
                                className="font-medium">{deleteCategoryName}</span>&#34; 吗？此操作不可撤销。
                            </p>

                            <div className="flex items-center justify-end space-x-3">
                                <button
                                    onClick={() => setShowDeleteModal(false)}
                                    className="px-4 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300 transition-colors"
                                >
                                    取消
                                </button>
                                <button
                                    onClick={confirmDeleteCategory}
                                    className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 transition-colors"
                                >
                                    删除
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default CategoryManagement;