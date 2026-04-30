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
    HardDrive,
    FolderInput,
    ChevronLeft,
    ChevronRight
} from 'lucide-react';
import dynamic from "next/dynamic";

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
    const [isMounted, setIsMounted] = useState(false);

    // 确保组件只在客户端挂载后渲染
    useEffect(() => {
        setIsMounted(true);
    }, []);
    
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

    // 批量移动对话框状态
    const [moveDialogOpen, setMoveDialogOpen] = useState(false);
    const [folders, setFolders] = useState<Array<{ id: number; name: string; path: string }>>([]);

    // 上传区块折叠状态 - 从 localStorage 读取初始值
    const [uploadAreaCollapsed, setUploadAreaCollapsed] = useState<boolean>(() => {
        if (typeof window !== 'undefined') {
            const saved = localStorage.getItem('media_upload_area_collapsed');
            return saved === 'true';
        }
        return false;
    });

    // 侧边栏折叠状态 - 从 localStorage 读取初始值
    const [sidebarCollapsed, setSidebarCollapsed] = useState<boolean>(() => {
        if (typeof window !== 'undefined') {
            const saved = localStorage.getItem('media_sidebar_collapsed');
            return saved === 'true';
        }
        return false;
    });

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

    // 批量移动
    const handleBatchMove = async (folderPath: string | null) => {
        if (selectedItems.length === 0) return;

        try {
            const response = await MediaService.moveMediaFiles(selectedItems, folderPath);

            if (response.success) {
                console.log('✅ 批量移动成功');
                setSelectedItems([]);
                setMoveDialogOpen(false);
                loadMediaFiles();
            } else {
                console.error('❌ 批量移动失败:', response.error);
                alert(`移动失败: ${response.error}`);
            }
        } catch (error) {
            console.error('批量移动失败:', error);
            alert('批量移动失败，请稍后重试');
        }
    };

    // 加载文件夹列表
    const loadFolders = async () => {
        try {
            console.log('📂 开始加载文件夹列表...');

            // 使用 apiClient 发送请求，它会自动处理认证
            const {apiClient} = await import('@/lib/api');

            const response = await apiClient.get('/media/folders/tree');

            console.log('📂 API响应:', response);

            if (response.success && response.data) {
                // 将树形结构展平为列表
                const flattenFolders = (
                    nodes: Array<{ id: number; name: string; children?: Array<any> }>,
                    parentPath: string = ''
                ): Array<{ id: number; name: string; path: string }> => {
                    const result: Array<{ id: number; name: string; path: string }> = [];
                    for (const node of nodes) {
                        const currentPath = parentPath ? `${parentPath}/${node.name}` : node.name;
                        result.push({
                            id: node.id,
                            name: node.name,
                            path: currentPath
                        });
                        if (node.children && node.children.length > 0) {
                            result.push(...flattenFolders(node.children, currentPath));
                        }
                    }
                    return result;
                };

                const flattenedFolders = flattenFolders(response.data.tree || []);
                console.log('📂 展平后的文件夹列表:', flattenedFolders);
                console.log('📂 文件夹数量:', flattenedFolders.length);
                setFolders(flattenedFolders);
            } else {
                console.error('❌ 获取文件夹失败:', response.error);
                alert(`获取文件夹失败: ${response.error || '未知错误'}`);
            }
        } catch (error) {
            console.error('❌ 加载文件夹异常:', error);
            alert('加载文件夹失败，请重试');
        }
    };

    // 打开批量移动对话框
    const openMoveDialog = () => {
        if (selectedItems.length === 0) return;
        loadFolders();
        setMoveDialogOpen(true);
    };

    // 切换上传区块折叠状态
    const toggleUploadArea = () => {
        const newState = !uploadAreaCollapsed;
        setUploadAreaCollapsed(newState);
        // 保存到 localStorage
        localStorage.setItem('media_upload_area_collapsed', String(newState));
    };

    // 切换侧边栏折叠状态
    const toggleSidebar = () => {
        const newState = !sidebarCollapsed;
        setSidebarCollapsed(newState);
        // 保存到 localStorage
        localStorage.setItem('media_sidebar_collapsed', String(newState));
    };

    // 更新媒体分类
    const handleUpdateCategory = async (mediaId: number, category: string) => {
        try {
            const response = await MediaService.updateMediaCategory(mediaId, category);
            if (response.success) {
                console.log('✅ 分类更新成功');
                loadMediaFiles(); // 刷新列表
            } else {
                console.error('❌ 分类更新失败:', response.error);
                alert(`更新分类失败: ${response.error}`);
            }
        } catch (error) {
            console.error('更新分类异常:', error);
            alert('更新分类失败，请重试');
        }
    };

    // 更新媒体标签
    const handleUpdateTags = async (mediaId: number, tags: string[]) => {
        try {
            const response = await MediaService.updateMediaTags(mediaId, tags, 'replace');
            if (response.success) {
                console.log('✅ 标签更新成功');
                loadMediaFiles(); // 刷新列表
            } else {
                console.error('❌ 标签更新失败:', response.error);
                alert(`更新标签失败: ${response.error}`);
            }
        } catch (error) {
            console.error('更新标签异常:', error);
            alert('更新标签失败，请重试');
        }
    };

    // 打开图片编辑器
    const openImageEditor = (media: MediaFile) => {
        setEditingMedia(media);
        setEditorDialogOpen(true);
    };

    // 处理拖拽结束 - 移动文件到文件夹
    const onDragEnd = (result: DropResult) => {
        const {destination, draggableId} = result;

        // 如果没有放置目标，直接返回
        if (!destination) return;

        // 解析 draggableId 获取媒体文件 ID
        // draggableId 格式: "media-{id}"
        const mediaId = parseInt(draggableId.replace('media-', ''));

        // 解析 destination.droppableId 获取文件夹路径
        // droppableId 格式: "folder-root" (根目录) 或 "folder-{path}" (子文件夹)
        let folderPath: string | null = null;

        if (destination.droppableId === 'folder-root') {
            // 拖拽到根目录
            folderPath = null;
        } else if (destination.droppableId.startsWith('folder-')) {
            // 拖拽到子文件夹
            folderPath = destination.droppableId.replace('folder-', '');
        }

        console.log('📦 移动文件:', {mediaId, folderPath});

        // 异步执行移动操作，但不阻塞拖拽完成
        const moveFile = async () => {
            try {
                // 调用 API 移动文件 - 使用 MediaService
                const response = await MediaService.moveMediaFiles([mediaId], folderPath);

                if (response.success) {
                    console.log('✅ 文件移动成功');
                    // 刷新媒体列表
                    loadMediaFiles();
                } else {
                    console.error('❌ 移动失败:', response.error);
                    alert(`移动失败: ${response.error}`);
                }
            } catch (error) {
                console.error('❌ 移动文件异常:', error);
                alert('移动失败，请重试');
            }
        };

        // 在后台执行移动操作
        moveFile();
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

                        {/* 右侧工具栏 */}
                        <div className="flex items-center gap-2">
                            {/* 侧边栏折叠按钮 */}
                            <button
                                onClick={toggleSidebar}
                                className="p-2 rounded-lg transition-colors text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800"
                                title={sidebarCollapsed ? '展开侧边栏' : '折叠侧边栏'}
                            >
                                {sidebarCollapsed ? (
                                    <ChevronRight className="w-5 h-5"/>
                                ) : (
                                    <ChevronLeft className="w-5 h-5"/>
                                )}
                            </button>

                            {/* 视图切换 */}
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
                {/* 整个拖拽上下文 - 只在客户端挂载后渲染 */}
                {isMounted ? (
                    <DragDropContext onDragEnd={onDragEnd}>
                        <div className="flex flex-col lg:flex-row gap-8">
                        {/* 侧边栏 */}
                            <aside className={`transition-all duration-300 ease-in-out ${
                                sidebarCollapsed ? 'lg:w-0 lg:opacity-0 lg:overflow-hidden' : 'lg:w-64'
                            } flex-shrink-0 space-y-6`}>
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
                                onDropMedia={(folderPath) => {
                                    // 这个函数在 FolderTree 内部使用，用于启用/禁用放置功能
                                    console.log('📂 文件放置到文件夹:', folderPath);
                                }}
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
                                collapsed={uploadAreaCollapsed}
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
                                uploadAreaCollapsed={uploadAreaCollapsed}
                                onToggleUploadArea={toggleUploadArea}
                                sidebarCollapsed={sidebarCollapsed}
                                onToggleSidebar={toggleSidebar}
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
                                            onClick={openMoveDialog}
                                            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg transition-colors flex items-center gap-2"
                                        >
                                            <FolderInput className="w-4 h-4"/>
                                            移动选中
                                        </button>
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
                                onSelectItem={(id) => {
                                    setSelectedItems(prev =>
                                        prev.includes(id)
                                            ? prev.filter(item => item !== id)
                                            : [...prev, id]
                                    );
                                }}
                                onPreview={setPreviewMedia}
                                onDelete={setDeleteItem}
                                onEdit={openImageEditor}
                                onUpdateCategory={handleUpdateCategory}
                                onUpdateTags={handleUpdateTags}
                                apiBaseUrl={apiBaseUrl}
                            />

                            {/* 分页 */}
                            {!loading && totalPages > 1 && (
                                <Pagination
                                    currentPage={currentPage}
                                    totalPages={totalPages}
                                    totalItems={totalItems}
                                    perPage={perPage}
                                    goToPage={setCurrentPage}
                                    startIndex={(currentPage - 1) * perPage + 1}
                                    endIndex={currentPage * perPage}
                                />
                            )}
                        </main>
                    </div>
                </DragDropContext>
                ) : (
                    // 服务端渲染时的占位符
                    <div className="flex flex-col lg:flex-row gap-8">
                        <aside className="lg:w-64 flex-shrink-0 space-y-6">
                            <StorageStats stats={storageStats} loading={loading}/>
                        </aside>
                        <main className="flex-1">
                            {loading ? (
                                <div className="p-12 text-center">
                                    <div
                                        className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
                                </div>
                            ) : null}
                        </main>
                    </div>
                )}
            </div>

            {/* 预览模态框 */}
            {previewMedia && (
                <PreviewModal
                    media={previewMedia}
                    onClose={() => setPreviewMedia(null)}
                />
            )}

            {/* 删除确认 */}
            {deleteItem && (
                <DeleteConfirm
                    item={deleteItem}
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

            {/* 批量移动对话框 */}
            <Dialog open={moveDialogOpen} onOpenChange={setMoveDialogOpen}>
                <DialogContent className="max-w-md">
                    <DialogTitle>移动文件到文件夹</DialogTitle>
                    <div className="mt-4">
                        <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
                            将选中的 {selectedItems.length} 个文件移动到：
                        </p>

                        {/* 调试信息 */}

                        <div className="space-y-2 max-h-64 overflow-y-auto">
                            {/* 根目录选项 */}
                            <button
                                onClick={() => handleBatchMove(null)}
                                className="w-full px-4 py-3 text-left rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-blue-50 dark:hover:bg-blue-900/20 hover:border-blue-500 transition-colors"
                            >
                                <div className="flex items-center gap-3">
                                    <FolderOpen className="w-5 h-5 text-gray-500"/>
                                    <span className="font-medium">根目录</span>
                                </div>
                            </button>

                            {/* 文件夹列表 */}
                            {folders.map((folder) => (
                                <button
                                    key={folder.id}
                                    onClick={() => handleBatchMove(folder.path)}
                                    className="w-full px-4 py-3 text-left rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-blue-50 dark:hover:bg-blue-900/20 hover:border-blue-500 transition-colors"
                                >
                                    <div className="flex items-center gap-3">
                                        <FolderOpen className="w-5 h-5 text-blue-500"/>
                                        <span className="font-medium">{folder.path}</span>
                                    </div>
                                </button>
                            ))}

                            {folders.length === 0 && (
                                <div className="text-center py-8 text-gray-500">
                                    暂无文件夹，请先创建文件夹
                                </div>
                            )}
                        </div>
                    </div>
                </DialogContent>
            </Dialog>

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
