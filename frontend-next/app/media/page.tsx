'use client';

import React, {useCallback, useEffect, useMemo, useRef, useState} from 'react';
import {MediaFile, MediaResponse, MediaService} from '@/lib/api';
import {useMediaUpload} from '@/hooks/useMediaUpload';
import WithAuthProtection from '@/components/WithAuthProtection';
import StorageStats from "@/components/media/StorageStats";
import UploadArea from "@/components/media/UploadArea";
import SearchAndFilter from "@/components/media/SearchAndFilter";
import MediaGrid from "@/components/media/MediaGrid";
import Pagination from "@/components/media/Pagination";
import PreviewModal from "@/components/media/PreviewModal";
import DeleteConfirm from "@/components/media/DeleteConfirm";

// 防抖hook
const useDebounce = <T, >(value: T, delay: number): T => {
    const [debouncedValue, setDebouncedValue] = useState<T>(value);

    useEffect(() => {
        const handler = setTimeout(() => {
            setDebouncedValue(value);
        }, delay);

        return () => {
            clearTimeout(handler);
        };
    }, [value, delay]);

    return debouncedValue;
};

const MediaPage = () => {
    const [mediaFiles, setMediaFiles] = useState<MediaFile[]>([]);
    const [loading, setLoading] = useState(true);
    const [currentPage, setCurrentPage] = useState(1);
    const [totalPages, setTotalPages] = useState(1);
    const [totalItems, setTotalItems] = useState(0);
    const [filterMediaType, setFilterMediaType] = useState('');
    const [searchQuery, setSearchQuery] = useState('');
    const perPage = 20;

    const [storageStats, setStorageStats] = useState({
        image_count: 0,
        video_count: 0,
        storage_used: '0 MB',
        storage_total: '0 MB',
        storage_percentage: 0,
        canBeUploaded: true,
        totalUsed: 0
    });

    const [previewMedia, setPreviewMedia] = useState<MediaFile | null>(null);
    const [deleteItem, setDeleteItem] = useState<MediaFile | null>(null);

    // 使用防抖处理搜索
    const debouncedSearchQuery = useDebounce(searchQuery, 500);

    // 使用自定义上传Hook - 使用 useMemo 避免每次重新创建
    const {uploading, uploadProgress, uploadStatus, uploadFiles} = useMediaUpload(() => {
        loadMediaFiles();
    });

    // 使用 ref 存储 AbortController
    const abortControllerRef = useRef<AbortController | null>(null);

    // 主加载函数
    const loadMediaFiles = useCallback(async () => {
        // 取消之前的请求
        if (abortControllerRef.current) {
            abortControllerRef.current.abort();
        }

        // 创建新的 AbortController
        abortControllerRef.current = new AbortController();

        setLoading(true);

        try {
            const params: {
                media_type?: string;
                page?: number;
                q?: string;
                per_page?: number;
            } = {};

            if (filterMediaType) params.media_type = filterMediaType;
            if (debouncedSearchQuery) params.q = debouncedSearchQuery;
            params.page = currentPage;
            params.per_page = perPage;

            const response = await MediaService.getMediaFiles(params);

            if (response.success && response.data) {
                const data = response.data as MediaResponse;
                setMediaFiles(data.media_items || []);
                setTotalPages(data.pagination?.pages || 1);
                setTotalItems(data.pagination?.total || 0);

                if (data.stats) {
                    setStorageStats(data.stats);
                }
            } else {
                console.error('Failed to load media files:', response.error);
                setMediaFiles([]);
                setTotalItems(0);
            }
        } catch (error) {
            // 如果是取消请求的错误，不处理
            if (error instanceof Error && error.name === 'AbortError') {
                console.log('Request was aborted');
                return;
            }
            console.error('Error loading media files:', error);
            setMediaFiles([]);
            setTotalItems(0);
        } finally {
            setLoading(false);
        }
    }, [currentPage, filterMediaType, debouncedSearchQuery, perPage]);

    // 只在必要的时候重新加载数据
    useEffect(() => {
        loadMediaFiles();

        // 清理函数
        return () => {
            if (abortControllerRef.current) {
                abortControllerRef.current.abort();
            }
        };
    }, [loadMediaFiles]);

    // 处理搜索变化
    const handleSearchChange = useCallback((value: string) => {
        setSearchQuery(value);
        // 搜索时重置到第一页
        if (currentPage !== 1) {
            setCurrentPage(1);
        }
    }, [currentPage]);

    // 处理过滤器变化
    const handleFilterChange = useCallback((value: string) => {
        setFilterMediaType(value);
        // 过滤时重置到第一页
        if (currentPage !== 1) {
            setCurrentPage(1);
        }
    }, [currentPage]);

    // 处理删除
    const handleDeleteConfirm = useCallback(async () => {
        if (!deleteItem) return;

        try {
            const response = await MediaService.deleteMediaFile(deleteItem.id.toString());

            if (response.success) {
                // 删除成功，更新本地状态
                setMediaFiles(prev => prev.filter(file => file.id !== deleteItem.id));
                setTotalItems(prev => prev - 1);
                setDeleteItem(null);
            } else {
                console.error('删除失败:', response.error);
                alert('删除失败');
            }
        } catch (error) {
            console.error('删除失败:', error);
            alert('删除失败');
        }
    }, [deleteItem]);

    // 处理上传完成
    const handleUploadComplete = useCallback((files: File[]) => {
        uploadFiles(files);
    }, [uploadFiles]);

    // 处理页面跳转
    const handlePageChange = useCallback((page: number) => {
        if (page >= 1 && page <= totalPages && page !== currentPage) {
            setCurrentPage(page);
        }
    }, [currentPage, totalPages]);

    // 使用 useMemo 计算分页信息
    const paginationInfo = useMemo(() => {
        const startIndex = (currentPage - 1) * perPage + 1;
        const endIndex = Math.min(startIndex + perPage - 1, totalItems);
        return {startIndex, endIndex};
    }, [currentPage, perPage, totalItems]);

    return (
        <WithAuthProtection>
            <div className="min-h-screen bg-gray-50">
                {/* 页面标题 */}
                <div className="bg-white shadow-sm border-b border-gray-200">
                    <div className="px-6 py-4">
                        <h1 className="text-2xl font-bold text-gray-900">媒体文件管理</h1>
                        <p className="text-gray-600 mt-1">管理和查看您的媒体文件</p>
                    </div>
                </div>

                {/* 主要内容区域 */}
                <div className="max-w-7xl mx-auto py-6">
                    {/* 存储统计 */}
                    <StorageStats stats={storageStats}/>

                    {/* 上传区域 */}
                    <UploadArea
                        onUpload={handleUploadComplete}
                        uploading={uploading}
                        uploadProgress={uploadProgress}
                        uploadStatus={uploadStatus}
                    />

                    {/* 搜索和过滤 */}
                    <SearchAndFilter
                        filterMediaType={filterMediaType}
                        setFilterMediaType={handleFilterChange}
                        searchQuery={searchQuery}
                        handleSearchChange={handleSearchChange}
                        totalItems={totalItems}
                        setCurrentPage={setCurrentPage}
                    />

                    {/* 媒体网格 */}
                    <MediaGrid
                        mediaFiles={mediaFiles}
                        loading={loading}
                        onPreview={setPreviewMedia}
                        onDelete={setDeleteItem}
                        totalItems={totalItems}
                    />

                    {/* 分页 - 只在有数据时显示 */}
                    {!loading && mediaFiles.length > 0 && totalPages > 1 && (
                        <Pagination
                            currentPage={currentPage}
                            totalPages={totalPages}
                            totalItems={totalItems}
                            perPage={perPage}
                            goToPage={handlePageChange}
                            startIndex={paginationInfo.startIndex}
                            endIndex={paginationInfo.endIndex}
                        />
                    )}
                </div>

                {/* 预览模态框 */}
                <PreviewModal
                    media={previewMedia}
                    onClose={() => setPreviewMedia(null)}
                />

                {/* 删除确认对话框 */}
                <DeleteConfirm
                    item={deleteItem}
                    onConfirm={handleDeleteConfirm}
                    onCancel={() => setDeleteItem(null)}
                />
            </div>
        </WithAuthProtection>
    );
};

export default MediaPage;