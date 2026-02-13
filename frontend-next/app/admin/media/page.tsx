'use client';

import React, {useEffect, useState} from 'react';
import {
    FaDownload,
    FaFile,
    FaFileAlt,
    FaFileArchive,
    FaFileAudio,
    FaFileExcel,
    FaFileImage,
    FaFilePdf,
    FaFilePowerpoint,
    FaFileVideo,
    FaFileWord,
    FaFilter,
    FaRedo,
    FaSearch,
    FaSpinner,
    FaTimes,
    FaTrash
} from 'react-icons/fa';
import {type MediaFile, MediaService} from '@/lib/api';

interface User {
    id: number;
    username: string;
}

interface Pagination {
    current_page: number;
    total_pages: number;
    total: number;
    has_prev: boolean;
    has_next: boolean;
    per_page: number;
}

const MediaManagement = () => {
    const [mediaItems, setMediaItems] = useState<MediaFile[]>([]);
    const [users, setUsers] = useState<User[]>([]);
    const [loading, setLoading] = useState(true);
    const [currentPage, setCurrentPage] = useState(1);
    const [totalPages, setTotalPages] = useState(1);
    const [totalItems, setTotalItems] = useState(0);
    const [searchQuery, setSearchQuery] = useState('');
    const [mimeTypeFilter, setMimeTypeFilter] = useState('');
    const [userIdFilter, setUserIdFilter] = useState('');
    const [dateFrom, setDateFrom] = useState('');
    const [dateTo, setDateTo] = useState('');

    const [showPreviewModal, setShowPreviewModal] = useState(false);
    const [previewMedia, setPreviewMedia] = useState<MediaFile | null>(null);
    const [previewLoading, setPreviewLoading] = useState(false);
    const [previewContent, setPreviewContent] = useState<string | null>(null);
    const [previewInfo, setPreviewInfo] = useState('');

    const [showDeleteModal, setShowDeleteModal] = useState(false);
    const [deleteMediaId, setDeleteMediaId] = useState('');
    const [deleteFilename, setDeleteFilename] = useState('');

    // 加载媒体文件数据
    useEffect(() => {
        loadMediaData();
    }, [currentPage, searchQuery, mimeTypeFilter, userIdFilter, dateFrom, dateTo]);

    const loadMediaData = async () => {
        try {
            setLoading(true);

            // 使用真实的媒体API获取数据
            const response = await MediaService.getMediaFiles({
                page: currentPage,
                media_type: mimeTypeFilter || 'all'  // 媒体类型过滤
            });

            if (response.success && response.data) {
                // 将API返回的数据格式转换为组件使用的格式
                const mediaItems = response.data.media_items.map((mediaFile: MediaFile) => ({
                    id: mediaFile.id,
                    hash: mediaFile.hash,
                    original_filename: mediaFile.original_filename,
                    mime_type: mediaFile.mime_type,
                    file_size: mediaFile.file_size,
                    user: {
                        username: 'Current User' // 当前用户信息需要从auth context获取
                    },
                    created_at: mediaFile.created_at
                }));

                setMediaItems(mediaItems);
                setUsers([]); // 在管理页面中不需要用户列表
                const pagination = response.data.pagination;
                setTotalPages(pagination.pages || 1);
                setTotalItems(pagination.total || 0);
            } else {
                console.error('Failed to load media data:', response.error || response.message || 'Unknown error');
                setMediaItems([]);
                setUsers([]);
                setTotalPages(1);
                setTotalItems(0);
            }
        } catch (error) {
            console.error('Failed to load media data:', error);
            setMediaItems([]);
            setUsers([]);
            setTotalPages(1);
            setTotalItems(0);
        } finally {
            setLoading(false);
        }
    };

    const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        setSearchQuery(e.target.value);
        setCurrentPage(1); // Reset to first page when searching
    };

    const handleMimeTypeChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
        setMimeTypeFilter(e.target.value);
        setCurrentPage(1);
    };

    const handleUserIdChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
        setUserIdFilter(e.target.value);
        setCurrentPage(1);
    };

    const handleDateFromChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        setDateFrom(e.target.value);
        setCurrentPage(1);
    };

    const handleDateToChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        setDateTo(e.target.value);
        setCurrentPage(1);
    };

    const handleApplyFilters = () => {
        setCurrentPage(1);
    };

    const handleResetFilters = () => {
        setSearchQuery('');
        setMimeTypeFilter('');
        setUserIdFilter('');
        setDateFrom('');
        setDateTo('');
        setCurrentPage(1);
    };

    const goToPage = (page: number) => {
        if (page >= 1 && page <= totalPages) {
            setCurrentPage(page);
        }
    };

    const getFileIcon = (mimeType: string) => {
        if (mimeType.startsWith('image/')) {
            return <FaFileImage className="text-4xl text-blue-500"/>;
        } else if (mimeType.startsWith('video/')) {
            return <FaFileVideo className="text-4xl text-red-500"/>;
        } else if (mimeType.startsWith('audio/')) {
            return <FaFileAudio className="text-4xl text-green-500"/>;
        } else if (mimeType === 'application/pdf') {
            return <FaFilePdf className="text-4xl text-red-600"/>;
        } else if (mimeType === 'application/msword' || mimeType === 'application/vnd.openxmlformats-officedocument.wordprocessingml.document') {
            return <FaFileWord className="text-4xl text-blue-600"/>;
        } else if (mimeType === 'application/vnd.ms-excel' || mimeType === 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet') {
            return <FaFileExcel className="text-4xl text-green-600"/>;
        } else if (mimeType === 'application/vnd.ms-powerpoint' || mimeType === 'application/vnd.openxmlformats-officedocument.presentationml.presentation') {
            return <FaFilePowerpoint className="text-4xl text-orange-500"/>;
        } else if (mimeType.startsWith('text/')) {
            return <FaFileAlt className="text-4xl text-gray-600"/>;
        } else if (mimeType === 'application/zip' || mimeType === 'application/x-rar-compressed') {
            return <FaFileArchive className="text-4xl text-yellow-600"/>;
        } else {
            return <FaFile className="text-4xl text-gray-500"/>;
        }
    };

    const getFileExtension = (mimeType: string) => {
        if (mimeType.startsWith('image/')) {
            return mimeType.split('/')[1].toUpperCase();
        } else if (mimeType.startsWith('video/')) {
            return mimeType.split('/')[1].toUpperCase();
        } else if (mimeType.startsWith('audio/')) {
            return mimeType.split('/')[1].toUpperCase();
        } else if (mimeType === 'application/pdf') {
            return 'PDF';
        } else if (mimeType === 'application/msword') {
            return 'DOC';
        } else if (mimeType === 'application/vnd.openxmlformats-officedocument.wordprocessingml.document') {
            return 'DOCX';
        } else if (mimeType === 'application/vnd.ms-excel') {
            return 'XLS';
        } else if (mimeType === 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet') {
            return 'XLSX';
        } else if (mimeType === 'application/vnd.ms-powerpoint') {
            return 'PPT';
        } else if (mimeType === 'application/vnd.openxmlformats-officedocument.presentationml.presentation') {
            return 'PPTX';
        } else if (mimeType === 'application/zip') {
            return 'ZIP';
        } else if (mimeType === 'application/x-rar-compressed') {
            return 'RAR';
        } else if (mimeType.startsWith('text/')) {
            return mimeType.split('/')[1].toUpperCase();
        } else {
            return mimeType.split('/')[1]?.toUpperCase() || mimeType.toUpperCase();
        }
    };

    const formatFileSize = (bytes: number): string => {
        if (bytes < 1024) return bytes + ' B';
        else if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
        else return (bytes / 1048576).toFixed(1) + ' MB';
    };

    const formatDate = (dateString: string) => {
        const date = new Date(dateString);
        return date.toLocaleDateString('zh-CN', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit'
        });
    };

    const handlePreview = (media: MediaFile) => {
        setPreviewMedia(media);
        setPreviewContent(null);
        setPreviewInfo(`文件大小: ${formatFileSize(media.file_size)} | 类型: ${media.mime_type}`);
        setPreviewLoading(true);
        setShowPreviewModal(true);

        // In a real implementation, we would fetch the actual preview content
        // For now, we'll simulate loading and show the appropriate preview based on file type
        setTimeout(() => {
            if (media.mime_type.startsWith('image/')) {
                setPreviewContent(`/api/v1/thumbnail?data=${media.hash}`);
                setPreviewLoading(false);
            } else {
                setPreviewContent(null);
                setPreviewLoading(false);
            }
        }, 1000);
    };

    const handleDownload = (hash: string, filename: string) => {
        // In a real implementation, we would trigger the actual download
        window.open(`/api/media/download?hash=${hash}&filename=${encodeURIComponent(filename)}`);
    };

    const handleDeleteClick = (id: number, filename: string) => {
        setDeleteMediaId(id.toString());
        setDeleteFilename(filename);
        setShowDeleteModal(true);
    };

    const confirmDelete = async () => {
        if (deleteMediaId) {
            try {
                // 使用真实的API删除媒体文件
                const response = await MediaService.deleteMediaFile(deleteMediaId);

                if (response.success) {
                    // Refresh the media list
                    loadMediaData();
                    setShowDeleteModal(false);
                } else {
                    console.error('Failed to delete media:', response.error || response.message || 'Unknown error');
                }
            } catch (error) {
                console.error('Failed to delete media:', error);
            }
        }
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
            {/* 筛选和搜索 */}
            <div className="bg-white rounded-xl shadow-sm p-6 mb-6">
                <form onSubmit={(e) => {
                    e.preventDefault();
                    handleApplyFilters();
                }}>
                    <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
                        <div className="flex flex-col sm:flex-row gap-4">
                            <div className="relative">
                                <select
                                    value={mimeTypeFilter}
                                    onChange={handleMimeTypeChange}
                                    className="block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-blue-500 focus:border-blue-500 rounded-lg"
                                >
                                    <option value="">所有类型</option>
                                    <option value="image">图片</option>
                                    <option value="video">视频</option>
                                    <option value="audio">音频</option>
                                    <option value="document">文档</option>
                                    <option value="application/pdf">PDF</option>
                                    <option value="application/zip">压缩包</option>
                                </select>
                            </div>
                            <div className="relative">
                                <select
                                    value={userIdFilter}
                                    onChange={handleUserIdChange}
                                    className="block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-blue-500 focus:border-blue-500 rounded-lg"
                                >
                                    <option value="">所有用户</option>
                                    {users.map(user => (
                                        <option key={user.id} value={user.id}>
                                            {user.username}
                                        </option>
                                    ))}
                                </select>
                            </div>
                            <div className="relative">
                                <input
                                    type="date"
                                    value={dateFrom}
                                    onChange={handleDateFromChange}
                                    className="block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-blue-500 focus:border-blue-500 rounded-lg"
                                    placeholder="开始日期"
                                />
                            </div>
                            <div className="relative">
                                <input
                                    type="date"
                                    value={dateTo}
                                    onChange={handleDateToChange}
                                    className="block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-blue-500 focus:border-blue-500 rounded-lg"
                                    placeholder="结束日期"
                                />
                            </div>
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
                                    className="block w-full pl-10 pr-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                                    placeholder="搜索文件名..."
                                />
                            </div>
                            <button
                                type="submit"
                                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors flex items-center"
                            >
                                <FaFilter className="mr-2"/>
                                筛选
                            </button>
                            <button
                                type="button"
                                onClick={handleResetFilters}
                                className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors flex items-center"
                            >
                                <FaRedo className="mr-2"/>
                                重置
                            </button>
                        </div>
                    </div>
                </form>
            </div>

            {/* 附件列表 */}
            <div className="bg-white rounded-xl shadow-sm overflow-hidden">
                {/* 表格头部 */}
                <div className="px-6 py-4 border-b border-gray-200 flex justify-between items-center">
                    <h2 className="text-lg font-semibold text-gray-800">附件列表</h2>
                    <div className="text-sm text-gray-500">
                        共 <span className="font-semibold">{totalItems}</span> 个附件
                    </div>
                </div>

                <div className="p-6">
                    {loading ? (
                        <div className="text-center py-12">
                            <FaSpinner className="animate-spin mx-auto text-3xl text-blue-500"/>
                            <p className="mt-2 text-gray-500">加载中...</p>
                        </div>
                    ) : mediaItems.length > 0 ? (
                        <div
                            className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-6">
                            {mediaItems.map(media => (
                                <div
                                    key={media.id}
                                    className="bg-white border border-gray-200 rounded-lg overflow-hidden hover:shadow-md transition-shadow duration-200"
                                >
                                    {/* 预览区域 */}
                                    <div
                                        className="h-40 flex items-center justify-center bg-gray-50 cursor-pointer hover:bg-gray-100"
                                        onClick={() => handlePreview(media)}
                                    >
                                        {media.mime_type.startsWith('image/') || media.mime_type.startsWith('video/') ? (
                                            <img
                                                src={`/api/v1/thumbnail?data=${media.hash}`}
                                                alt={media.original_filename}
                                                className="max-h-full max-w-full object-contain"
                                            />
                                        ) : (
                                            <div className="flex flex-col items-center justify-center">
                                                {getFileIcon(media.mime_type)}
                                            </div>
                                        )}
                                    </div>

                                    {/* 文件信息 */}
                                    <div className="p-3">
                                        <div className="flex justify-between items-start mb-2">
                                            <h3
                                                className="text-sm font-medium text-gray-900 truncate"
                                                title={media.original_filename}
                                            >
                                                {media.original_filename}
                                            </h3>
                                            <div className="flex space-x-1 ml-2">
                                                <button
                                                    className="text-blue-600 hover:text-blue-700"
                                                    title="下载"
                                                    onClick={(e) => {
                                                        e.stopPropagation();
                                                        handleDownload(media.hash, media.original_filename);
                                                    }}
                                                >
                                                    <FaDownload className="text-xs"/>
                                                </button>
                                                <button
                                                    className="text-red-600 hover:text-red-700"
                                                    title="删除"
                                                    onClick={(e) => {
                                                        e.stopPropagation();
                                                        handleDeleteClick(media.id, media.original_filename);
                                                    }}
                                                >
                                                    <FaTrash className="text-xs"/>
                                                </button>
                                            </div>
                                        </div>

                                        <div className="text-xs text-gray-500 mb-1">
                                            <span>{formatFileSize(media.file_size)}</span>
                                            <span className="mx-1">•</span>
                                            <span>{getFileExtension(media.mime_type)}</span>
                                        </div>

                                        <div className="text-xs text-gray-500 flex justify-between">
                                            <span>{media.user?.username || 'N/A'}</span>
                                            <span>{formatDate(media.created_at)}</span>
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    ) : (
                        <div className="text-center py-12">
                            <FaFileArchive className="text-5xl text-gray-400 mx-auto"/>
                            <p className="text-gray-500 mt-4">暂无附件</p>
                        </div>
                    )}
                </div>

                {/* 分页 */}
                {mediaItems.length > 0 && (
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
                            显示 {mediaItems.length} 个，共 {totalItems} 个附件
                        </div>
                    </div>
                )}
            </div>

            {/* 预览模态框 */}
            {showPreviewModal && (
                <div
                    className="fixed inset-0 bg-black bg-opacity-75 z-50 flex items-center justify-center p-4"
                    onClick={() => setShowPreviewModal(false)}
                >
                    <div
                        className="relative bg-white rounded-lg shadow-lg w-full max-w-4xl max-h-[90vh]"
                        onClick={e => e.stopPropagation()}
                    >
                        <div className="flex justify-between items-center px-6 py-4 border-b">
                            <h3 className="text-lg font-medium text-gray-900">
                                {previewMedia?.original_filename || '文件预览'}
                            </h3>
                            <button
                                className="text-gray-400 hover:text-gray-500"
                                onClick={() => setShowPreviewModal(false)}
                            >
                                <FaTimes className="text-xl"/>
                            </button>
                        </div>

                        <div className="p-6 flex items-center justify-center min-h-[300px]">
                            {previewLoading ? (
                                <div className="text-center">
                                    <FaSpinner className="animate-spin mx-auto text-3xl text-blue-500"/>
                                    <p className="mt-2 text-gray-500">加载中...</p>
                                </div>
                            ) : previewMedia?.mime_type.startsWith('image/') ? (
                                <img
                                    src={previewContent || `/api/media/${previewMedia.id}`}
                                    alt={previewMedia.original_filename}
                                    className="max-w-full max-h-[60vh] object-contain"
                                />
                            ) : previewMedia?.mime_type.startsWith('video/') ? (
                                <video controls>
                                    <source src={`/api/v1/media/${previewMedia.id}`} type={previewMedia.mime_type}/>
                                    您的浏览器不支持视频标签。</video>
                            ) : (
                                <div className="text-center">
                                    <div className="flex justify-center mb-4">
                                        {getFileIcon(previewMedia?.mime_type || '')}
                                    </div>
                                    <p className="text-gray-500">不支持在线预览此文件类型</p>
                                    <p className="text-sm text-gray-400 mt-2">{previewMedia?.mime_type}</p>
                                </div>
                            )}
                        </div>

                        <div className="px-6 py-4 border-t bg-gray-50 flex justify-between items-center">
                            <div className="text-sm text-gray-500">{previewInfo}</div>
                            <div className="flex space-x-2">
                                <button
                                    className="px-4 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300 transition-colors"
                                    onClick={() => setShowPreviewModal(false)}
                                >
                                    关闭
                                </button>
                            </div>
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
                                您确定要删除附件 "<span className="font-medium">{deleteFilename}</span>" 吗？此操作不可撤销。
                            </p>

                            <div className="flex items-center justify-end space-x-3">
                                <button
                                    onClick={() => setShowDeleteModal(false)}
                                    className="px-4 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300 transition-colors"
                                >
                                    取消
                                </button>
                                <button
                                    onClick={confirmDelete}
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

export default MediaManagement;