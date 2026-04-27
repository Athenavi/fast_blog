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

    // API配置 - 与 /admin/media 保持一致
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
                console.log('✅ API配置已加载:', apiConfig.API_BASE_URL);
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
    
    // 文件夹选择状态 - 从 URL 参数初始化（使用文件夹名称而非ID）
    const [selectedFolderName, setSelectedFolderName] = useState<string | null>(() => {
        const folderName = searchParams.get('folder');
        return folderName || null;
    });
    const [hasRedirected, setHasRedirected] = useState(false); // 防止重复重定向

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
        //console.log('\n=== loadMediaFiles 被调用 ===');
        //console.log('Current abortController:', abortControllerRef.current ? '存在' : '不存在');
        
        // 取消之前的请求
        if (abortControllerRef.current) {
            console.log('取消之前的请求...');
            abortControllerRef.current.abort();
        }

        // 创建新的 AbortController
        abortControllerRef.current = new AbortController();
        //console.log('创建新的 AbortController');

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
                console.log('📁 筛选文件夹:', selectedFolderName);
            }
            params.page = currentPage;
            params.per_page = perPage;

            console.log('🔍 API 请求参数:', params);
            const response = await MediaService.getMediaFiles(params);
            console.log('Media files response:', response); // Debug log
            //console.log('收到响应:', response);

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
                console.log('✓ 请求被取消（AbortError）');
                return;
            }
            //console.error('✗ Error loading media files:', error);
            setMediaFiles([]);
            setTotalItems(0);
        } finally {
            setLoading(false);
            //console.log('=== loadMediaFiles 完成 ===\n');
        }
    }, [currentPage, filterMediaType, debouncedSearchQuery, perPage, selectedFolderName]);

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

    // 处理文件夹选择 - 同步到 URL（使用文件夹名称）
    const handleFolderSelect = useCallback((folderName: string | null) => {
        setSelectedFolderName(folderName);
        
        // 更新 URL 参数
        const params = new URLSearchParams(searchParams.toString());
        if (folderName) {
            params.set('folder', folderName);
        } else {
            params.delete('folder');
        }
        
        // 重置到第一页
        params.delete('page');
        
        router.push(`/media?${params.toString()}`, { scroll: false });
    }, [router, searchParams]);

    // 处理媒体文件放置到文件夹
    const handleDropMediaToFolder = useCallback(async (folderPath: string | null) => {
        // 如果没有选中文件，不执行任何操作
        if (selectedItems.length === 0) {
            console.log('⚠️ 没有选中的文件，忽略拖拽');
            return;
        }

        console.log('📦 开始移动文件:', {
            selectedItems,
            targetFolder: folderPath || '根目录'
        });

        try {
            // 使用统一的 getAuthHeaders 函数
            const headers = getAuthHeaders();
            console.log('🔐 请求 Headers:', headers);
            
            const response = await fetch(`${apiBaseUrl}${apiPrefix}/media/folders/move-media`, {
                method: 'POST',
                headers: {
                    ...headers,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    media_ids: selectedItems,
                    folder_path: folderPath  // 使用路径而非 ID
                })
            });

            console.log('📡 API 响应状态:', response.status);

            if (response.ok) {
                const data = await response.json();
                console.log('📊 API 响应数据:', data);
                
                if (data.success) {
                    console.log(`✅ 成功移动 ${data.data.moved_count} 个文件`);
                    alert(`成功移动 ${data.data.moved_count} 个文件到 ${folderPath || '根目录'}`);
                    setSelectedItems([]); // 清空选择
                    await loadMediaFiles(); // 刷新列表
                    console.log('🔄 列表已刷新');
                } else {
                    console.error('❌ 移动失败:', data.error);
                    alert(`移动失败: ${data.error}`);
                }
            } else {
                console.error('❌ HTTP 错误:', response.status, response.statusText);
                if (response.status === 401) {
                    alert('未授权，请重新登录');
                } else {
                    alert('移动失败，请重试');
                }
            }
        } catch (error) {
            console.error('❌ 批量移动异常:', error);
            alert('移动失败');
        }
    }, [selectedItems, apiBaseUrl, apiPrefix, loadMediaFiles]);

    // 处理媒体文件拖拽结束
    const handleDragEnd = useCallback((result: DropResult) => {
        console.log('🎯 handleDragEnd 被调用');
        console.log('📋 完整 result 对象:', JSON.stringify(result, null, 2));
        
        const { destination, source, draggableId } = result;
        
        console.log('🔍 解析后的数据:', {
            hasDestination: !!destination,
            destination: destination,
            source: source,
            draggableId: draggableId
        });
        
        // 如果没有放置目标，或者放置在原位，不做任何操作
        if (!destination) {
            console.log('⚠️ 没有放置目标 - 可能拖拽到了无效区域');
            console.log('💡 提示: 请确保将文件拖拽到左侧的文件夹上，看到蓝色边框后再释放');
            return;
        }
        
        console.log('✅ 检测到有效的放置目标:', destination.droppableId);
        if (
            destination.droppableId === source.droppableId &&
            destination.index === source.index
        ) {
            console.log('↔️ 位置未变化');
            return;
        }
        
        console.log('📍 拖拽信息:', {
            draggableId,
            source: source.droppableId,
            destination: destination.droppableId
        });
        
        // 从 draggableId 中提取媒体文件 ID (格式: "media-123")
        const mediaId = parseInt(draggableId.replace('media-', ''));
        if (isNaN(mediaId)) {
            console.error('无法解析媒体文件ID:', draggableId);
            return;
        }
        
        // 确定目标文件夹路径
        let targetFolderPath: string | null = null;
        
        if (destination.droppableId === 'folder-root') {
            // 拖拽到根目录
            targetFolderPath = null;
            console.log('📁 拖拽到根目录');
        } else if (destination.droppableId.startsWith('folder-')) {
            // 拖拽到特定文件夹 - droppableId 格式为 "folder-/path/to/folder" 或 "folder-id-123"
            const folderPath = destination.droppableId.substring(7); // 去掉 "folder-" 前缀
            
            // 如果是 "folder-id-xxx" 格式，说明 buildFolderPath 返回了 null，需要特殊处理
            if (folderPath.startsWith('id-')) {
                console.warn('⚠️ 检测到 folder-id-xxx 格式，这可能意味着路径构建失败');
                // 暂时无法移动到该文件夹，因为不知道路径
                alert('无法移动到该文件夹：路径信息丢失');
                return;
            }
            
            targetFolderPath = folderPath || null;
            console.log('📁 拖拽到文件夹:', targetFolderPath);
        } else if (destination.droppableId === 'media-grid' || destination.droppableId === 'media-list') {
            // 在媒体网格内拖拽（重新排序），不执行移动操作
            console.log('↔️ 媒体网格内拖拽，不执行移动');
            return;
        } else {
            console.log('⚠️ 未知的放置目标:', destination.droppableId);
            return;
        }
        
        // 设置选中的文件并执行移动
        setSelectedItems([mediaId]);
        // 使用 setTimeout 确保状态更新后再执行移动
        // 注意：这里不使用 handleDropMediaToFolder，直接内联逻辑避免循环依赖
        setTimeout(async () => {
            if ([mediaId].length === 0) {
                console.log('⚠️ 没有选中的文件，忽略拖拽');
                return;
            }

            console.log('📦 开始移动文件:', {
                selectedItems: [mediaId],
                targetFolder: targetFolderPath || '根目录',
                targetFolderPath_value: targetFolderPath,
                targetFolderPath_type: typeof targetFolderPath
            });

            try {
                // 使用统一的 getAuthHeaders 函数
                const headers = getAuthHeaders();
                console.log('🔐 请求 Headers:', headers);
                
                // 构建请求体
                const requestBody = {
                    media_ids: [mediaId],
                    folder_path: targetFolderPath  // null 或 字符串路径
                };
                
                console.log('📤 发送请求体:', JSON.stringify(requestBody));
                
                const response = await fetch(`${apiBaseUrl}${apiPrefix}/media/folders/move-media`, {
                    method: 'POST',
                    headers: {
                        ...headers,
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(requestBody)
                });

                console.log('📡 API 响应状态:', response.status);

                if (response.ok) {
                    const data = await response.json();
                    console.log('📊 API 响应数据:', data);
                    
                    if (data.success) {
                        console.log(`✅ 成功移动 ${data.data.moved_count} 个文件`);
                        alert(`成功移动 ${data.data.moved_count} 个文件到 ${targetFolderPath || '根目录'}`);
                        setSelectedItems([]); // 清空选择
                        await loadMediaFiles(); // 刷新列表
                        console.log('🔄 列表已刷新');
                    } else {
                        console.error('❌ 移动失败:', data.error);
                        alert(`移动失败: ${data.error}`);
                    }
                } else {
                    console.error('❌ HTTP 错误:', response.status, response.statusText);
                    if (response.status === 401) {
                        alert('未授权，请重新登录');
                    } else {
                        alert('移动失败，请重试');
                    }
                }
            } catch (error) {
                console.error('❌ 批量移动异常:', error);
                alert('移动失败');
            }
        }, 0);
    }, [apiBaseUrl, apiPrefix, loadMediaFiles]);

    // 处理删除确认
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

    // 选择/取消选择
    const handleSelectItem = useCallback((id: number) => {
        setSelectedItems(prev =>
            prev.includes(id) ? prev.filter(i => i !== id) : [...prev, id]
        );
    }, []);

    // 全选/取消全选
    const handleSelectAll = useCallback(() => {
        if (selectedItems.length === mediaFiles.length) {
            setSelectedItems([]);
        } else {
            setSelectedItems(mediaFiles.map(m => m.id));
        }
    }, [selectedItems.length, mediaFiles]);

    // 批量删除
    const handleBatchDelete = useCallback(async (ids: number[]) => {
        try {
            const response = await MediaService.deleteMediaFile(ids);
            if (response.success) {
                alert(`成功删除 ${ids.length} 个文件`);
                setSelectedItems([]);
                loadMediaFiles();
            } else {
                alert('删除失败: ' + (response.error || '未知错误'));
            }
        } catch (error) {
            console.error('批量删除失败:', error);
            alert('删除失败');
        }
    }, []);

    // 获取认证头
    const getAuthHeaders = (): HeadersInit => {
        const getTokenFromCookie = (): string | null => {
            if (typeof document === 'undefined') {
                console.warn('⚠️ 在服务端环境中，无法访问 cookie');
                return null;
            }
            
            console.log('🍪 所有 cookies:', document.cookie);
            
            const cookies = document.cookie.split(';');
            for (const cookie of cookies) {
                const [name, value] = cookie.trim().split('=');
                console.log('🔍 检查 cookie:', { name, hasValue: !!value });
                if (name === 'access_token') {
                    const decodedValue = decodeURIComponent(value);
                    console.log('✅ 找到 access_token:', decodedValue.substring(0, 20) + '...');
                    return decodedValue;
                }
            }
            
            console.warn('⚠️ 未找到 access_token cookie');
            return null;
        };

        const token = getTokenFromCookie();
        const headers: HeadersInit = {'Content-Type': 'application/json'};

        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
            console.log('🔐 已添加 Authorization header');
        } else {
            console.error('❌ 没有 token，请求将失败');
            // 自动跳转到登录页面，保存当前路径用于登录后重定向
            if (typeof window !== 'undefined' && !hasRedirected) {
                setHasRedirected(true); // 标记已重定向，防止重复
                const currentPath = window.location.pathname + window.location.search;
                localStorage.setItem('redirect_after_login', currentPath);
                console.log('🔄 正在跳转到登录页面...');
                router.push('/login');
            }
        }

        return headers;
    };

    // 更新单个媒体分类
    const handleUpdateCategory = useCallback(async (mediaId: number, category: string) => {
        try {
            const response = await fetch(
                `${apiBaseUrl}${apiPrefix}/media/detail/${mediaId}`,
                {
                    method: 'PUT',
                    headers: getAuthHeaders(),
                    body: JSON.stringify({category})
                }
            );

            if (response.ok) {
                // 重新加载媒体列表
                loadMediaFiles();
            } else {
                const error = await response.json();
                throw new Error(error.error || '更新分类失败');
            }
        } catch (error) {
            console.error('更新分类失败:', error);
            alert('更新分类失败');
            throw error;
        }
    }, [loadMediaFiles, apiBaseUrl, apiPrefix]);

    // 更新单个媒体标签
    const handleUpdateTags = useCallback(async (mediaId: number, tags: string[]) => {
        console.log('开始更新标签:', { mediaId, tags });
        
        try {
            const url = `${apiBaseUrl}${apiPrefix}/media/detail/${mediaId}`;
            console.log('请求 URL:', url);
            
            const headers = getAuthHeaders();
            console.log('请求 Headers:', headers);
            
            const body = JSON.stringify({tags: tags.join(',')});
            console.log('请求 Body:', body);
            
            const response = await fetch(url, {
                method: 'PUT',
                headers: headers,
                body: body
            });

            console.log('响应状态:', response.status, response.statusText);
            console.log('响应 Content-Type:', response.headers.get('content-type'));

            if (response.ok) {
                const data = await response.json();
                console.log('✓ 标签更新成功:', data);
                // 重新加载媒体列表
                loadMediaFiles();
            } else {
                // 先检查 Content-Type
                const contentType = response.headers.get('content-type');
                console.log('响应类型:', contentType);
                
                if (contentType && contentType.includes('application/json')) {
                    const error = await response.json();
                    console.error('✗ 服务器返回JSON错误:', error);
                    throw new Error(error.error || error.detail || '更新标签失败');
                } else {
                    // 返回的不是 JSON，可能是 HTML 错误页面
                    const text = await response.text();
                    console.error('✗ 服务器返回非JSON响应:', text.substring(0, 500));
                    console.error('完整响应:', text);
                    
                    // 根据状态码提供更友好的错误提示
                    let errorMessage = `服务器错误 (${response.status})`;
                    if (response.status === 401) {
                        errorMessage = '未授权，请重新登录';
                    } else if (response.status === 403) {
                        errorMessage = '没有权限执行此操作';
                    } else if (response.status === 404) {
                        errorMessage = '媒体文件不存在';
                    } else if (response.status === 500) {
                        errorMessage = '服务器内部错误';
                    }
                    
                    throw new Error(errorMessage);
                }
            }
        } catch (error) {
            console.error('✗ 更新标签异常:', error);
            if (error instanceof Error) {
                alert(`更新标签失败: ${error.message}`);
            } else {
                alert('更新标签失败，请查看控制台获取详细信息');
            }
            throw error;
        }
    }, [loadMediaFiles, apiBaseUrl, apiPrefix]);

    // 打开图片编辑器
    const handleEditImage = (media: MediaFile) => {
        setEditingMedia(media);
        setEditorDialogOpen(true);
        setPreviewMedia(null); // 关闭预览对话框
    };

    // 保存编辑后的图片
    const handleSaveEditedImage = async (editedBlob: Blob) => {
        if (!editingMedia) return;

        try {
            const formData = new FormData();
            formData.append('file', editedBlob, editingMedia.filename);
            formData.append('media_id', editingMedia.id.toString());

            const response = await fetch(
                `${apiBaseUrl}${apiPrefix}/media/${editingMedia.id}/edit`,
                {
                    method: 'POST',
                    headers: getAuthHeaders(),
                    body: formData,
                }
            );

            if (response.ok) {
                alert('图片保存成功！');
                setEditorDialogOpen(false);
                loadMediaFiles();
            } else {
                const error = await response.json();
                alert(`保存失败: ${error.detail || '未知错误'}`);
            }
        } catch (error) {
            console.error('保存图片失败:', error);
            alert('保存失败，请重试');
        }
    };

    // 使用 useMemo 计算分页信息
    const paginationInfo = useMemo(() => {
        const startIndex = (currentPage - 1) * perPage + 1;
        const endIndex = Math.min(startIndex + perPage - 1, totalItems);
        return {startIndex, endIndex};
    }, [currentPage, perPage, totalItems]);

    return (
        <WithAuthProtection>
            <DragDropContext onDragEnd={handleDragEnd}>
                <div className="min-h-screen bg-gray-50">
                {/* 页面标题 */}
                <div className="bg-white shadow-sm border-b border-gray-200">
                    <div className="px-6 py-4">
                        <h1 className="text-2xl font-bold text-gray-900">媒体文件管理</h1>
                        <p className="text-gray-600 mt-1">管理和查看您的媒体文件</p>
                    </div>
                </div>

                {/* 主要内容区域 - 使用 flex 布局 */}
                <div className="max-w-7xl mx-auto py-6 px-6">
                    <div className="flex gap-6">
                        {/* 左侧文件夹导航 */}
                        <div className="w-64 flex-shrink-0">
                            <div className="bg-white rounded-lg shadow-sm border border-gray-200 h-[calc(100vh-200px)] overflow-hidden sticky top-6">
                                <FolderTree
                                    apiBaseUrl={apiBaseUrl}
                                    apiPrefix={apiPrefix}
                                    selectedFolderName={selectedFolderName}
                                    onFolderSelect={handleFolderSelect}
                                    onRefresh={loadMediaFiles}
                                    onDropMedia={handleDropMediaToFolder}
                                />
                            </div>
                        </div>

                        {/* 右侧主内容区 */}
                        <div className="flex-1 min-w-0 space-y-6">
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
                                viewMode={viewMode}
                                onViewModeChange={setViewMode}
                                selectedItems={selectedItems}
                                onSelectItem={handleSelectItem}
                                onSelectAll={handleSelectAll}
                                onBatchDelete={handleBatchDelete}
                                onUpdateCategory={handleUpdateCategory}
                                onUpdateTags={handleUpdateTags}
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
                    </div>
                </div>
                </div>
            </DragDropContext>

            {/* 预览模态框 */}
            <PreviewModal
                media={previewMedia}
                onClose={() => setPreviewMedia(null)}
                onEdit={handleEditImage}
            />

            {/* 图片编辑器对话框 */}
            <Dialog open={editorDialogOpen} onOpenChange={setEditorDialogOpen}>
                <DialogContent className="max-w-6xl max-h-[90vh] p-0">
                    {/* Dialog 标题 - 对屏幕阅读器可见但视觉上隐藏 */}
                    <DialogTitle className="sr-only">图片编辑器</DialogTitle>
                    {editingMedia && (
                        <ImageEditor
                            imageUrl={`${apiBaseUrl}${apiPrefix}/media/${editingMedia.id}`}
                            onSave={handleSaveEditedImage}
                            onClose={() => setEditorDialogOpen(false)}
                        />
                    )}
                </DialogContent>
            </Dialog>

            {/* 删除确认对话框 */}
            <DeleteConfirm
                item={deleteItem}
                onConfirm={handleDeleteConfirm}
                onCancel={() => setDeleteItem(null)}
            />
        </WithAuthProtection>
    );
};

// 主组件 - 提供 Suspense 边界
const MediaPage = () => {
    return (
        <Suspense fallback={
            <div className="min-h-screen bg-gray-50 flex items-center justify-center">
                <div className="text-center">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-900 mx-auto"></div>
                    <p className="mt-4 text-gray-600">加载中...</p>
                </div>
            </div>
        }>
            <MediaPageContent />
        </Suspense>
    );
};

export default MediaPage;