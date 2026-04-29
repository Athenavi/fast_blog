'use client';

import React, {Suspense, useCallback, useEffect, useMemo, useRef, useState} from 'react';
import {DragDropContext, DropResult} from '@hello-pangea/dnd';
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
import FolderTree from '@/components/media/FolderTree';
import dynamic from 'next/dynamic';
import {Dialog, DialogContent, DialogTitle} from '@/components/ui/dialog';
import {useRouter, useSearchParams} from 'next/navigation';
import {motion} from 'framer-motion';
import {
    Image as ImageIcon,
    Video,
    Music,
    FileText,
    Grid3X3,
    List,
    Upload,
    Search,
    Filter,
    Trash2,
    Edit,
    Eye,
    Download,
    Copy,
    FolderOpen,
    HardDrive
} from 'lucide-react';

// 动态导入 ImageEditor，禁用 SSR
const ImageEditor = dynamic(() => import('@/components/ImageEditor'), {
    ssr: false,
    loading: () => <div className="p-8 text-center">加载编辑器...</div>
});

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

// 内部组件 - 使用 useSearchParams
const MediaPageContent = () => {
    const router = useRouter();
    const searchParams = useSearchParams();
    
    const [mediaFiles, setMediaFiles] = useState<MediaFile[]>([]);
    const [loading, setLoading] = useState(true);
    const [currentPage, setCurrentPage] = useState(1);
    const [totalPages, setTotalPages] = useState(1);
    const [totalItems, setTotalItems] = useState(0);
    const [filterMediaType, setFilterMediaType] = useState('');
    const [searchQuery, setSearchQuery] = useState('');
    const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
    const [selectedItems, setSelectedItems] = useState<number[]>([]);
    const perPage = 20;

    // API配置
    const [apiBaseUrl, setApiBaseUrl] = useState('http://localhost:9421');
    const [apiPrefix, setApiPrefix] = useState('/api/v1');

    // 加载API配置
    React.useEffect(() => {
        const loadConfig = async () => {
            try {
                const config = await import('@/lib/config');
                const apiConfig = config.getConfig();
                setApiBaseUrl(apiConfig.API_BASE_URL);
                setApiPrefix(apiConfig.API_PREFIX);
            } catch (error) {
                console.error('❌ 加载API配置失败:', error);
            }
        };
        loadConfig();
    }, []);

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
    
    // 图片编辑状态
    const [editorDialogOpen, setEditorDialogOpen] = useState(false);
    const [editingMedia, setEditingMedia] = useState<MediaFile | null>(null);

    // 文件夹选择状态
    const [selectedFolderName, setSelectedFolderName] = useState<string | null>(() => {
        const folderName = searchParams.get('folder');
        return folderName || null;
    });
    const [hasRedirected, setHasRedirected] = useState(false);

    // 使用防抖处理搜索
    const debouncedSearchQuery = useDebounce(searchQuery, 500);

    // 使用自定义上传Hook
    const {uploading, uploadProgress, uploadStatus, uploadFiles} = useMediaUpload(() => {
        loadMediaFiles();
    });

    // 使用 ref 存储 AbortController
    const abortControllerRef = useRef<AbortController | null>(null);

    // 主加载函数
    const loadMediaFiles = useCallback(async () => {
        if (abortControllerRef.current) {
            abortControllerRef.current.abort();
        }

        abortControllerRef.current = new AbortController();
        setLoading(true);

        try {
            const params: {
                media_type?: string;
                page?: number;
                q?: string;
                per_page?: number;
                folder_name?: string | null;
            } = {};

            if (filterMediaType) params.media_type = filterMediaType;
            if (debouncedSearchQuery) params.q = debouncedSearchQuery;
            if (selectedFolderName) {
                params.folder_name = selectedFolderName;
            }
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
            if (error instanceof Error && error.name === 'AbortError') {
                return;
            }
            setMediaFiles([]);
            setTotalItems(0);
        } finally {
            setLoading(false);
        }
    }, [currentPage, filterMediaType, debouncedSearchQuery, perPage, selectedFolderName]);

    useEffect(() => {
        loadMediaFiles();

        return () => {
            if (abortControllerRef.current) {
                abortControllerRef.current.abort();
            }
        };
    }, [loadMediaFiles]);

    // 处理搜索变化
    const handleSearchChange = useCallback((value: string) => {
        setSearchQuery(value);
        if (currentPage !== 1) {
            setCurrentPage(1);
        }
    }, [currentPage]);

    // 删除媒体文件
    const handleDelete = async (mediaId: number) => {
        try {
            const response = await MediaService.deleteMediaFile(mediaId);
            if (response.success) {
                setDeleteItem(null);
                loadMediaFiles();
            } else {
                alert(response.error || '删除失败');
            }
        } catch (error) {
            console.error('删除媒体文件失败:', error);
            alert('删除失败，请稍后重试');
        }
    };

    // 批量删除
    const handleBatchDelete = async () => {
        if (selectedItems.length === 0) return;

        if (!confirm(`确定要删除选中的 ${selectedItems.length} 个文件吗？`)) {
            return;
        }

        try {
            for (const id of selectedItems) {
                await MediaService.deleteMediaFile(id);
            }
            setSelectedItems([]);
            loadMediaFiles();
        } catch (error) {
            console.error('批量删除失败:', error);
            alert('批量删除失败，请稍后重试');
        }
    };

    // 打开图片编辑器
    const openImageEditor = (media: MediaFile) => {
        setEditingMedia(media);
        setEditorDialogOpen(true);
    };

    // 处理拖拽结束
    const onDragEnd = (result: DropResult) => {
        // 可以在这里实现拖拽排序逻辑
    };

    // 获取文件类型图标
    const getFileTypeIcon = (mediaType: string) => {
        if (mediaType.startsWith('image')) return ImageIcon;
        if (mediaType.startsWith('video')) return Video;
        if (mediaType.startsWith('audio')) return Music;
        return FileText;
    };

    return (
        <div className="min-h-screen bg-gray-50 dark:bg-gray-950">
            {/* 头部 */}
            <header
                className="bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-800 sticky top-0 z-40">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
                    <div className="flex items-center justify-between">
                        <div>
                            <h1 className="text-2xl font-black text-gray-900 dark:text-white flex items-center gap-3">
                                <ImageIcon className="w-8 h-8 text-blue-600"/>
                                媒体库
                            </h1>
                            <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                                管理你的图片、视频和文档
                            </p>
                        </div>

                        {/* 视图切换 */}
                        <div className="flex items-center gap-2">
                            <button
                                onClick={() => setViewMode('grid')}
                                className={`p-2 rounded-lg transition-colors ${
                                    viewMode === 'grid'
                                        ? 'bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400'
                                        : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800'
                                }`}
                            >
                                <Grid3X3 className="w-5 h-5"/>
                            </button>
                            <button
                                onClick={() => setViewMode('list')}
                                className={`p-2 rounded-lg transition-colors ${
                                    viewMode === 'list'
                                        ? 'bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400'
                                        : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800'
                                }`}
                            >
                                <List className="w-5 h-5"/>
                            </button>
                        </div>
                    </div>
                </div>
            </header>

            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                {/* 整个拖拽上下文 - 包含侧边栏和主内容 */}
                <DragDropContext onDragEnd={onDragEnd}>
                    <div className="flex flex-col lg:flex-row gap-8">
                        {/* 侧边栏 */}
                        <aside className="lg:w-64 flex-shrink-0 space-y-6">
                            {/* 存储统计 */}
                            <StorageStats stats={storageStats} loading={loading}/>

                            {/* 文件夹树 */}
                            <FolderTree
                                apiBaseUrl={apiBaseUrl}
                                apiPrefix={apiPrefix}
                                selectedFolderName={selectedFolderName}
                                onFolderSelect={(folderName) => {
                                    setSelectedFolderName(folderName);
                                    setCurrentPage(1);
                                    router.push(`/media${folderName ? `?folder=${folderName}` : ''}`);
                                }}
                                onRefresh={loadMediaFiles}
                            />
                        </aside>

                        {/* 主内容区 */}
                        <main className="flex-1">
                            {/* 上传区域 */}
                            <UploadArea
                                onUpload={uploadFiles}
                                uploading={uploading}
                                uploadProgress={uploadProgress}
                                uploadStatus={uploadStatus}
                            />

                            {/* 搜索和筛选 */}
                            <SearchAndFilter
                                filterMediaType={filterMediaType}
                                setFilterMediaType={(type) => {
                                    setFilterMediaType(type);
                                    setCurrentPage(1);
                                }}
                                searchQuery={searchQuery}
                                handleSearchChange={handleSearchChange}
                                totalItems={totalItems}
                                setCurrentPage={setCurrentPage}
                                onUploadRequest={uploadFiles}
                            />

                            {/* 批量操作工具栏 */}
                            {selectedItems.length > 0 && (
                                <motion.div
                                    initial={{opacity: 0, y: -10}}
                                    animate={{opacity: 1, y: 0}}
                                    className="mb-4 p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-xl flex items-center justify-between"
                                >
                                    <div className="flex items-center gap-3">
                                    <span className="text-sm font-medium text-blue-900 dark:text-blue-100">
                                        已选择 {selectedItems.length} 个文件
                                    </span>
                                    </div>
                                    <div className="flex items-center gap-2">
                                        <button
                                            onClick={handleBatchDelete}
                                            className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white text-sm font-medium rounded-lg transition-colors flex items-center gap-2"
                                        >
                                            <Trash2 className="w-4 h-4"/>
                                            删除选中
                                        </button>
                                        <button
                                            onClick={() => setSelectedItems([])}
                                            className="px-4 py-2 bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 text-gray-900 dark:text-white text-sm font-medium rounded-lg transition-colors"
                                        >
                                            取消选择
                                        </button>
                                    </div>
                                </motion.div>
                            )}

                            {/* 媒体网格/列表 */}
                            <MediaGrid
                                mediaFiles={mediaFiles}
                                loading={loading}
                                viewMode={viewMode}
                                selectedItems={selectedItems}
                                setSelectedItems={setSelectedItems}
                                onPreview={setPreviewMedia}
                                onDelete={setDeleteItem}
                                onEdit={openImageEditor}
                                apiBaseUrl={apiBaseUrl}
                            />

                            {/* 分页 */}
                            {!loading && totalPages > 1 && (
                                <Pagination
                                    currentPage={currentPage}
                                    totalPages={totalPages}
                                    onPageChange={setCurrentPage}
                                />
                            )}
                        </main>
                    </div>
                </DragDropContext>
            </div>

            {/* 预览模态框 */}
            {previewMedia && (
                <PreviewModal
                    media={previewMedia}
                    onClose={() => setPreviewMedia(null)}
                    apiBaseUrl={apiBaseUrl}
                />
            )}

            {/* 删除确认 */}
            {deleteItem && (
                <DeleteConfirm
                    media={deleteItem}
                    onCancel={() => setDeleteItem(null)}
                    onConfirm={() => handleDelete(deleteItem.id!)}
                />
            )}

            {/* 图片编辑器 */}
            {editingMedia && (
                <Dialog open={editorDialogOpen} onOpenChange={setEditorDialogOpen}>
                    <DialogContent className="max-w-6xl max-h-[90vh] overflow-hidden">
                        <DialogTitle className="sr-only">编辑图片</DialogTitle>
                        <ImageEditor
                            imageUrl={`${apiBaseUrl}${editingMedia.url}`}
                            onSave={async (blob) => {
                                // 保存编辑后的图片逻辑
                                setEditorDialogOpen(false);
                            }}
                        />
                    </DialogContent>
                </Dialog>
            )}

            {/* 底部间距 */}
            <div className="h-20"/>
        </div>
    );
};

// 主页面组件
const MediaPage = () => {
    return (
        <WithAuthProtection loadingMessage="正在加载媒体库...">
            <Suspense fallback={
                <div className="min-h-screen bg-gray-50 dark:bg-gray-950 flex items-center justify-center">
                    <motion.div
                        animate={{rotate: 360}}
                        transition={{duration: 1, repeat: Infinity, ease: "linear"}}
                        className="w-12 h-12 border-4 border-blue-600 border-t-transparent rounded-full"
                    />
                </div>
            }>
                <MediaPageContent/>
            </Suspense>
        </WithAuthProtection>
    );
};

export default MediaPage;
