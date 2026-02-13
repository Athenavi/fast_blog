'use client';

import React, {useEffect, useState} from 'react';
import {MediaFile, MediaService} from '@/lib/api';
import {Button} from '@/components/ui/button';

interface MediaSelectorModalProps {
    isOpen: boolean;
    onClose: () => void;
    onSelect: (media: MediaFile | MediaFile[]) => void;
    allowedTypes?: string[]; // 允许的文件类型，如 ['image'] 或 ['image', 'video']
}

const MediaSelectorModal: React.FC<MediaSelectorModalProps> = ({
                                                                   isOpen,
                                                                   onClose,
                                                                   onSelect,
                                                                   allowedTypes = ['image']
                                                               }) => {
    const [mediaFiles, setMediaFiles] = useState<MediaFile[]>([]);
    const [loading, setLoading] = useState(false);
    const [currentPage, setCurrentPage] = useState(1);
    const [totalPages, setTotalPages] = useState(1);
    const [searchQuery, setSearchQuery] = useState('');
    const [selectedMedia, setSelectedMedia] = useState<MediaFile[]>([]);

    // 根据允许的类型过滤媒体文件
    const filterMediaByType = (media: MediaFile) => {
        if (allowedTypes.includes('image') && media.mime_type.startsWith('image/')) {
            return true;
        }
        if (allowedTypes.includes('video') && media.mime_type.startsWith('video/')) {
            return true;
        }
        return allowedTypes.includes('audio') && media.mime_type.startsWith('audio/');
    };

    const loadMediaFiles = async () => {
        setLoading(true);
        try {
            const params: { media_type?: string; page?: number } = {};

            // 根据允许的类型设置过滤参数
            if (allowedTypes.length === 1) {
                params.media_type = allowedTypes[0];
            }

            params.page = currentPage;

            const response = await MediaService.getMediaFiles(params);

            if (response.success && response.data) {
                const filteredMedia = response.data.media_items.filter(filterMediaByType);
                setMediaFiles(filteredMedia);
                setTotalPages(response.data.pagination.pages || 1);
            } else {
                setMediaFiles([]);
            }
        } catch (error) {
            console.error('加载媒体文件失败:', error);
            setMediaFiles([]);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        if (isOpen) {
            loadMediaFiles();
            setSelectedMedia([]); // 重置选择
        }
    }, [isOpen, currentPage, allowedTypes]);

    const handleSelectMedia = (media: MediaFile) => {
        setSelectedMedia(prev => {
            const isSelected = prev.some(item => item.id === media.id);
            if (isSelected) {
                // 如果已选择，则移除
                return prev.filter(item => item.id !== media.id);
            } else {
                // 如果未选择，则添加到末尾
                return [...prev, media];
            }
        });
    };

    const handleConfirmSelection = () => {
        if (selectedMedia.length > 0) {
            onSelect(selectedMedia);
            onClose();
        }
    };

    const handleClose = () => {
        setSelectedMedia([]);
        onClose();
    };

    const goToPage = (page: number) => {
        if (page >= 1 && page <= totalPages && page !== currentPage) {
            setCurrentPage(page);
        }
    };

    const formatFileSize = (size?: number) => {
        if (!size) return '0 KB';
        const units = ['B', 'KB', 'MB', 'GB'];
        let unitIndex = 0;
        let fileSize = size;
        while (fileSize >= 1024 && unitIndex < units.length - 1) {
            fileSize /= 1024;
            unitIndex++;
        }
        return `${fileSize.toFixed(1)} ${units[unitIndex]}`;
    };

    // 处理重新排序
    const handleReorder = (fromIndex: number, toIndex: number) => {
        setSelectedMedia(prev => {
            const newSelected = [...prev];
            const [movedItem] = newSelected.splice(fromIndex, 1);
            newSelected.splice(toIndex, 0, movedItem);
            return newSelected;
        });
    };

    // 获取选中文件的序号
    const getSelectionOrder = (mediaId: number) => {
        return selectedMedia.findIndex(item => item.id === mediaId) + 1;
    };

    // 检查文件是否被选中
    const isMediaSelected = (mediaId: number) => {
        return selectedMedia.some(item => item.id === mediaId);
    };

    // 检查文件是否被选中（备用方法）
    const isSelected = (mediaId: number) => {
        return selectedMedia.some(item => item.id === mediaId);
    };

    // 获取选择索引
    const getSelectedIndex = (mediaId: number) => {
        return selectedMedia.findIndex(item => item.id === mediaId);
    };


    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
            <div
                className="bg-white rounded-lg shadow-xl w-full max-w-6xl max-h-[90vh] flex flex-col"
                onClick={(e) => e.stopPropagation()}
            >
                {/* 头部 */}
                <div className="flex justify-between items-center px-6 py-4 border-b">
                    <h3 className="text-lg font-semibold text-gray-900">
                        选择媒体文件
                    </h3>
                    <button
                        onClick={handleClose}
                        className="text-gray-400 hover:text-gray-500"
                    >
                        <i className="fas fa-times text-xl"></i>
                    </button>
                </div>

                {/* 搜索和工具栏 */}
                <div className="px-6 py-4 border-b">
                    <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center">
                        <div className="relative flex-1 max-w-md">
                            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                                <i className="fas fa-search text-gray-400"></i>
                            </div>
                            <input
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                                className="block w-full pl-10 pr-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                                placeholder="搜索文件名..."
                                type="text"
                            />
                        </div>
                        <div className="text-sm text-gray-500">
                            共找到 {mediaFiles.length} 个文件，已选择 {selectedMedia.length} 个
                        </div>
                    </div>
                </div>

                {/* 媒体文件网格 */}
                <div className="flex-1 overflow-y-auto p-6">
                    {loading ? (
                        <div className="flex items-center justify-center h-64">
                            <div className="text-center">
                                <i className="fas fa-spinner fa-spin text-2xl text-blue-500 mb-2"></i>
                                <p className="text-gray-500">加载中...</p>
                            </div>
                        </div>
                    ) : mediaFiles.length === 0 ? (
                        <div className="flex items-center justify-center h-64">
                            <div className="text-center">
                                <i className="fas fa-file-archive text-4xl text-gray-300 mb-2"></i>
                                <p className="text-gray-500">暂无符合条件的媒体文件</p>
                            </div>
                        </div>
                    ) : (
                        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
                            {mediaFiles.map((media) => (
                                <div
                                    key={media.id}
                                    className={`border rounded-lg overflow-hidden cursor-pointer transition-all relative ${
                                        isMediaSelected(media.id)
                                            ? 'ring-2 ring-blue-500 border-blue-500'
                                            : 'border-gray-200 hover:border-gray-300'
                                    }`}
                                    onClick={() => handleSelectMedia(media)}
                                >
                                    <div className="h-24 flex items-center justify-center bg-gray-50">
                                        {media.mime_type.startsWith('image/') || media.mime_type.startsWith('video/') ? (
                                            <img
                                                src={`/api/v1/thumbnail/?data=${media.hash}`}
                                                alt={media.original_filename}
                                                className="w-full h-full object-cover"
                                                onError={(e) => {
                                                    const target = e.target as HTMLImageElement;
                                                    target.onerror = null;
                                                    target.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTAwIiBoZWlnaHQ9IjEwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSIjZTVlN2ViIi8+PHRleHQgeD0iNTAlIiB5PSI1MCUiIGRvbWluYW50LWJhc2VsaW5lPSJtaWRkbGUiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGZvbnQtZmFtaWx5PSJBcmlhbCIgZm9udC1zaXplPSI4IiBmaWxsPSIjNmI3MjgwIj5JbWFnZSBQbGFjZWhvbGRlcjwvdGV4dD48L3N2Zz4=';
                                                }}
                                            />
                                        ) : (
                                            <div className="text-center">
                                                <i className={`${
                                                    media.mime_type.startsWith('video/') ? 'fas fa-file-video text-purple-500' :
                                                        media.mime_type.startsWith('audio/') ? 'fas fa-file-audio text-green-500' :
                                                            'fas fa-file text-gray-400'
                                                } text-2xl`}></i>
                                            </div>
                                        )}
                                    </div>
                                    <div className="p-2">
                                        <p
                                            className="text-xs font-medium text-gray-900 truncate"
                                            title={media.original_filename}
                                        >
                                            {media.original_filename}
                                        </p>
                                        <p className="text-xs text-gray-500 mt-1">
                                            {formatFileSize(media.file_size)}
                                        </p>
                                    </div>
                                    {isMediaSelected(media.id) && (
                                        <div
                                            className="absolute top-1 right-1 w-6 h-6 bg-blue-500 rounded-full flex items-center justify-center">
                      <span className="text-white text-xs font-bold">
                        {getSelectionOrder(media.id)}
                      </span>
                                        </div>
                                    )}
                                </div>
                            ))}
                        </div>
                    )}
                </div>

                {/* 底部分页和操作按钮 */}
                <div
                    className="px-6 py-4 border-t bg-gray-50 flex flex-col sm:flex-row justify-between items-center gap-4">
                    {/* 分页 */}
                    <div className="flex items-center space-x-2">
                        <button
                            disabled={currentPage === 1}
                            className={`px-3 py-1 rounded border text-sm ${
                                currentPage === 1
                                    ? 'border-gray-300 text-gray-400 cursor-not-allowed'
                                    : 'border-gray-300 text-gray-700 hover:bg-gray-50'
                            }`}
                            onClick={() => goToPage(currentPage - 1)}
                        >
                            上一页
                        </button>

                        <span className="text-sm text-gray-600">
              第 {currentPage} 页，共 {totalPages} 页
            </span>

                        <button
                            disabled={currentPage === totalPages}
                            className={`px-3 py-1 rounded border text-sm ${
                                currentPage === totalPages
                                    ? 'border-gray-300 text-gray-400 cursor-not-allowed'
                                    : 'border-gray-300 text-gray-700 hover:bg-gray-50'
                            }`}
                            onClick={() => goToPage(currentPage + 1)}
                        >
                            下一页
                        </button>
                    </div>

                    {/* 操作按钮 */}
                    <div className="flex space-x-3">
                        <Button
                            variant="outline"
                            onClick={handleClose}
                        >
                            取消
                        </Button>
                        <Button
                            onClick={handleConfirmSelection}
                            disabled={selectedMedia.length === 0}
                            className="bg-blue-500 hover:bg-blue-600"
                        >
                            插入 {selectedMedia.length} 个选中文件
                        </Button>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default MediaSelectorModal;