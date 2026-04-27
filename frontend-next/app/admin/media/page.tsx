/**
 * 现代化媒体库管理页面
 * 功能: 网格/列表视图、无限滚动、批量操作、高级搜索过滤、拖拽上传
 */

'use client';

import {useEffect, useState} from 'react';
import {useRouter} from 'next/navigation';
import {Card, CardContent} from '@/components/ui/card';
import {Button} from '@/components/ui/button';
import {Input} from '@/components/ui/input';
import {Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle} from '@/components/ui/dialog';
import {Select, SelectContent, SelectItem, SelectTrigger, SelectValue} from '@/components/ui/select';
import {Label} from '@/components/ui/label';
import {Badge} from '@/components/ui/badge';
import dynamic from 'next/dynamic';
import {
    Calendar,
    Edit,
    File,
    Filter,
    Grid3x3,
    HardDrive,
    Image as ImageIcon,
    List,
    Search,
    Trash2,
    X
} from 'lucide-react';

// 动态导入 ImageEditor，禁用 SSR
const ImageEditor = dynamic(() => import('@/components/ImageEditor'), {
    ssr: false,
    loading: () => <div className="p-8 text-center">加载编辑器...</div>
});

interface MediaItem {
    id: number;
    filename: string;
    original_filename?: string;
    title?: string;
    alt_text?: string;
    description?: string;
    hash?: string;
    file_path?: string;
    file_url?: string;
    url?: string;
    thumbnail_url?: string;
    media_type?: string;
    mime_type?: string;
    file_size?: number;
    width?: number;
    height?: number;
    category?: string;
    tags?: string;
    created_at?: string;
    updated_at?: string;
}

interface PaginationInfo {
    page: number;
    per_page: number;
    total: number;
    total_pages: number;
    has_next: boolean;
    has_prev: boolean;
}

export default function ModernMediaLibraryPage() {
    const router = useRouter();
    const [hasRedirected, setHasRedirected] = useState(false); // 防止重复重定向
    const [media, setMedia] = useState<MediaItem[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [selectedItems, setSelectedItems] = useState<number[]>([]);
    const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');

    // API配置
    const [apiBaseUrl, setApiBaseUrl] = useState('http://localhost:9421');
    const [apiPrefix, setApiPrefix] = useState('/api/v1');

    // 加载API配置
    useEffect(() => {
        const loadConfig = async () => {
            try {
                const config = await import('@/lib/config');
                const apiConfig = config.getConfig();
                setApiBaseUrl(apiConfig.API_BASE_URL);
                setApiPrefix(apiConfig.API_PREFIX);
            } catch (error) {
                console.error('加载API配置失败:', error);
            }
        };
        loadConfig();
    }, []);

    // 获取认证头
    const getAuthHeaders = (): HeadersInit => {
        const getTokenFromCookie = (): string | null => {
            if (typeof document === 'undefined') return null;
            const cookies = document.cookie.split(';');
            for (const cookie of cookies) {
                const [name, value] = cookie.trim().split('=');
                if (name === 'access_token') {
                    return decodeURIComponent(value);
                }
            }
            return null;
        };

        const token = getTokenFromCookie();
        const headers: HeadersInit = {'Content-Type': 'application/json'};

        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        } else {
            // 自动跳转到登录页面，保存当前路径用于登录后重定向
            if (typeof window !== 'undefined' && !hasRedirected) {
                setHasRedirected(true); // 标记已重定向，防止重复
                const currentPath = window.location.pathname + window.location.search;
                localStorage.setItem('redirect_after_login', currentPath);
                router.push('/login');
            }
        }

        return headers;
    };

    // 高级搜索和过滤
    const [searchQuery, setSearchQuery] = useState('');
    const [mediaType, setMediaType] = useState<string>('');
    const [dateFrom, setDateFrom] = useState<string>('');
    const [dateTo, setDateTo] = useState<string>('');
    const [minSize, setMinSize] = useState<number | null>(null);
    const [maxSize, setMaxSize] = useState<number | null>(null);
    const [sortBy, setSortBy] = useState<string>('created_at');
    const [sortOrder, setSortOrder] = useState<string>('desc');

    // 分页
    const [currentPage, setCurrentPage] = useState(1);
    const [pageSize] = useState(24);
    const [pagination, setPagination] = useState<PaginationInfo | null>(null);

    // 统计信息
    const [statistics, setStatistics] = useState<any>(null);

    // 对话框状态
    const [detailDialogOpen, setDetailDialogOpen] = useState(false);
    const [selectedMedia, setSelectedMedia] = useState<MediaItem | null>(null);
    const [editorDialogOpen, setEditorDialogOpen] = useState(false);
    const [editingMedia, setEditingMedia] = useState<MediaItem | null>(null);
    
    // 详情对话框图片懒加载状态
    const [shouldLoadDetailImage, setShouldLoadDetailImage] = useState(false);
    const [detailImageLoaded, setDetailImageLoaded] = useState(false);

    // 批量操作状态
    const [isBatchDeleting, setIsBatchDeleting] = useState(false);
    const [showFilters, setShowFilters] = useState(false);
    
    // 批量分类/标签对话框
    const [categoryDialogOpen, setCategoryDialogOpen] = useState(false);
    const [tagDialogOpen, setTagDialogOpen] = useState(false);
    const [batchCategory, setBatchCategory] = useState('');
    const [batchTags, setBatchTags] = useState('');
    const [tagMode, setTagMode] = useState<'add' | 'replace'>('add');
    
    // 单个媒体分类/标签
    const [singleCategoryDialog, setSingleCategoryDialog] = useState<{open: boolean; media: MediaItem | null}>({open: false, media: null});
    const [singleTagDialog, setSingleTagDialog] = useState<{open: boolean; media: MediaItem | null}>({open: false, media: null});
    const [singleCategory, setSingleCategory] = useState('');
    const [singleTags, setSingleTags] = useState<string[]>([]);
    const [newSingleTag, setNewSingleTag] = useState('');

    useEffect(() => {
        loadMedia();
        loadStatistics();
    }, [currentPage, searchQuery, mediaType, dateFrom, dateTo, minSize, maxSize, sortBy, sortOrder]);

    // 监听详情对话框打开状态，控制图片懒加载
    useEffect(() => {
        if (detailDialogOpen) {
            // 对话框打开时，重置加载状态
            setDetailImageLoaded(false);
            // 延迟加载图片（给对话框动画时间）
            const timer = setTimeout(() => {
                setShouldLoadDetailImage(true);
            }, 100);
            return () => clearTimeout(timer);
        } else {
            // 对话框关闭时，重置加载状态
            setShouldLoadDetailImage(false);
            setDetailImageLoaded(false);
        }
    }, [detailDialogOpen]);

    // 加载媒体列表
    const loadMedia = async () => {
        try {
            setIsLoading(true);

            const params = new URLSearchParams({
                page: currentPage.toString(),
                per_page: pageSize.toString(),
                sort_by: sortBy,
                sort_order: sortOrder
            });

            if (searchQuery) params.append('search', searchQuery);
            if (mediaType) params.append('media_type', mediaType);
            if (dateFrom) params.append('date_from', dateFrom);
            if (dateTo) params.append('date_to', dateTo);
            if (minSize !== null) params.append('min_size', minSize.toString());
            if (maxSize !== null) params.append('max_size', maxSize.toString());

            const response = await fetch(
                `${apiBaseUrl}${apiPrefix}/media/files?${params}`,
                {headers: getAuthHeaders()}
            );

            if (response.ok) {
                const data = await response.json();
                if (data.success) {
                    setMedia(data.data?.media_items || []);
                    setPagination(data.data?.pagination || {});
                }
            }
        } catch (error) {
            console.error('加载媒体失败:', error);
        } finally {
            setIsLoading(false);
        }
    };

    // 加载统计信息
    const loadStatistics = async () => {
        try {
            const response = await fetch(
                `${apiBaseUrl}${apiPrefix}/media/statistics`,
                {headers: getAuthHeaders()}
            );

            if (response.ok) {
                const data = await response.json();
                if (data.success) {
                    setStatistics(data.data);
                }
            }
        } catch (error) {
            console.error('加载统计信息失败:', error);
        }
    };

    // 选择/取消选择
    const toggleSelect = (id: number) => {
        setSelectedItems(prev =>
            prev.includes(id) ? prev.filter(item => item !== id) : [...prev, id]
        );
    };

    const selectAll = () => {
        if (selectedItems.length === media.length) {
            setSelectedItems([]);
        } else {
            setSelectedItems(media.map(item => item.id));
        }
    };

    // 批量删除
    const handleBatchDelete = async () => {
        if (selectedItems.length === 0) return;

        if (!confirm(`确定要删除选中的 ${selectedItems.length} 个文件吗？`)) {
            return;
        }

        try {
            setIsBatchDeleting(true);

            const response = await fetch(
                `${apiBaseUrl}${apiPrefix}/media/batch-delete`,
                {
                    method: 'POST',
                    headers: getAuthHeaders(),
                    body: JSON.stringify({media_ids: selectedItems})
                }
            );

            if (response.ok) {
                const data = await response.json();
                if (data.success) {
                    alert(`成功删除 ${data.data.deleted_count} 个文件`);
                    setSelectedItems([]);
                    loadMedia();
                    loadStatistics();
                }
            }
        } catch (error) {
            console.error('批量删除失败:', error);
            alert('删除失败');
        } finally {
            setIsBatchDeleting(false);
        }
    };

    // 批量分类
    const handleBatchCategorize = async () => {
        if (selectedItems.length === 0 || !batchCategory) return;

        try {
            const response = await fetch(
                `${apiBaseUrl}${apiPrefix}/media/batch-categorize`,
                {
                    method: 'POST',
                    headers: getAuthHeaders(),
                    body: JSON.stringify({
                        media_ids: selectedItems,
                        category: batchCategory
                    })
                }
            );

            if (response.ok) {
                const data = await response.json();
                if (data.success) {
                    alert(data.message || '分类设置成功');
                    setCategoryDialogOpen(false);
                    setBatchCategory('');
                    setSelectedItems([]);
                    loadMedia();
                }
            } else {
                const error = await response.json();
                alert(`分类失败: ${error.error || '未知错误'}`);
            }
        } catch (error) {
            console.error('批量分类失败:', error);
            alert('分类失败');
        }
    };

    // 批量标签
    const handleBatchTags = async () => {
        if (selectedItems.length === 0 || !batchTags) return;

        const tagsList = batchTags.split(',').map(t => t.trim()).filter(t => t);

        try {
            const response = await fetch(
                `${apiBaseUrl}${apiPrefix}/media/batch-tags`,
                {
                    method: 'POST',
                    headers: getAuthHeaders(),
                    body: JSON.stringify({
                        media_ids: selectedItems,
                        tags: tagsList,
                        mode: tagMode
                    })
                }
            );

            if (response.ok) {
                const data = await response.json();
                if (data.success) {
                    alert(data.message || '标签更新成功');
                    setTagDialogOpen(false);
                    setBatchTags('');
                    setSelectedItems([]);
                    loadMedia();
                }
            } else {
                const error = await response.json();
                alert(`标签更新失败: ${error.error || '未知错误'}`);
            }
        } catch (error) {
            console.error('批量标签失败:', error);
            alert('标签更新失败');
        }
    };

    // 打开单个媒体分类对话框
    const openSingleCategoryDialog = (media: MediaItem, e?: React.MouseEvent) => {
        if (e) e.stopPropagation();
        setSingleCategoryDialog({open: true, media});
        setSingleCategory(media.category || '');
    };

    // 保存单个媒体分类
    const handleSaveSingleCategory = async () => {
        if (!singleCategoryDialog.media) return;

        try {
            const response = await fetch(
                `${apiBaseUrl}${apiPrefix}/media/detail/${singleCategoryDialog.media.id}`,
                {
                    method: 'PUT',
                    headers: getAuthHeaders(),
                    body: JSON.stringify({category: singleCategory.trim()})
                }
            );

            if (response.ok) {
                setSingleCategoryDialog({open: false, media: null});
                setSingleCategory('');
                loadMedia();
            } else {
                const error = await response.json();
                alert(`分类设置失败: ${error.error || '未知错误'}`);
            }
        } catch (error) {
            console.error('设置分类失败:', error);
            alert('设置分类失败');
        }
    };

    // 打开单个媒体标签对话框
    const openSingleTagDialog = (media: MediaItem, e?: React.MouseEvent) => {
        if (e) e.stopPropagation();
        setSingleTagDialog({open: true, media});
        const tags = media.tags ? media.tags.split(',').map(t => t.trim()).filter(t => t) : [];
        setSingleTags(tags);
        setNewSingleTag('');
    };

    // 添加标签
    const handleAddSingleTag = () => {
        const tag = newSingleTag.trim();
        if (tag && !singleTags.includes(tag)) {
            setSingleTags([...singleTags, tag]);
            setNewSingleTag('');
        }
    };

    // 移除标签
    const handleRemoveSingleTag = (tagToRemove: string) => {
        setSingleTags(singleTags.filter(tag => tag !== tagToRemove));
    };

    // 保存单个媒体标签
    const handleSaveSingleTags = async () => {
        if (!singleTagDialog.media) return;

        try {
            const response = await fetch(
                `${apiBaseUrl}${apiPrefix}/media/detail/${singleTagDialog.media.id}`,
                {
                    method: 'PUT',
                    headers: getAuthHeaders(),
                    body: JSON.stringify({tags: singleTags.join(',')})
                }
            );

            if (response.ok) {
                setSingleTagDialog({open: false, media: null});
                setSingleTags([]);
                setNewSingleTag('');
                loadMedia();
            } else {
                const error = await response.json();
                alert(`标签更新失败: ${error.error || '未知错误'}`);
            }
        } catch (error) {
            console.error('更新标签失败:', error);
            alert('更新标签失败');
        }
    };

    // 格式化文件大小
    const formatFileSize = (bytes: number): string => {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
    };

    // 格式化日期
    const formatDate = (dateString: string): string => {
        return new Date(dateString).toLocaleDateString('zh-CN');
    };

    // 获取媒体类型图标
    const getTypeIcon = (mediaType: string) => {
        if (mediaType?.startsWith('image')) return <ImageIcon className="w-5 h-5"/>;
        return <File className="w-5 h-5"/>;
    };

    // 重置过滤器
    const resetFilters = () => {
        setSearchQuery('');
        setMediaType('');
        setDateFrom('');
        setDateTo('');
        setMinSize(null);
        setMaxSize(null);
        setCurrentPage(1);
    };

    // 打开图片编辑器
    const handleEditImage = (media: MediaItem) => {
        setEditingMedia(media);
        setEditorDialogOpen(true);
        setDetailDialogOpen(false);
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
                loadMedia();
            } else {
                const error = await response.json();
                alert(`保存失败: ${error.detail || '未知错误'}`);
            }
        } catch (error) {
            console.error('保存图片失败:', error);
            alert('保存失败，请重试');
        }
    };

    return (
        <div className="p-6 space-y-6">
            {/* 页面标题 */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold text-gray-900">媒体库</h1>
                    <p className="text-gray-600 mt-1">管理您的图片、视频和文档</p>
                </div>
                <div className="flex gap-2">
                    <Button variant="outline" onClick={() => setShowFilters(!showFilters)}>
                        <Filter className="w-4 h-4 mr-2"/>
                        {showFilters ? '隐藏过滤' : '高级过滤'}
                    </Button>
                    <Button variant="outline" onClick={selectAll}>
                        {selectedItems.length === media.length ? '取消全选' : '全选'}
                    </Button>
                    {selectedItems.length > 0 && (
                        <>
                            <Button
                                variant="destructive"
                                onClick={handleBatchDelete}
                                disabled={isBatchDeleting}
                            >
                                <Trash2 className="w-4 h-4 mr-2"/>
                                批量删除 ({selectedItems.length})
                            </Button>
                            <Button
                                variant="outline"
                                onClick={() => setCategoryDialogOpen(true)}
                            >
                                批量分类
                            </Button>
                            <Button
                                variant="outline"
                                onClick={() => setTagDialogOpen(true)}
                            >
                                批量标签
                            </Button>
                        </>
                    )}
                </div>
            </div>

            {/* 统计卡片 */}
            {statistics && (
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                    <Card>
                        <CardContent className="pt-6">
                            <div className="flex items-center space-x-2">
                                <HardDrive className="w-5 h-5 text-blue-600"/>
                                <div>
                                    <p className="text-sm text-gray-600">总文件数</p>
                                    <p className="text-2xl font-bold">{statistics.total_count}</p>
                                </div>
                            </div>
                        </CardContent>
                    </Card>
                    <Card>
                        <CardContent className="pt-6">
                            <div className="flex items-center space-x-2">
                                <ImageIcon className="w-5 h-5 text-green-600"/>
                                <div>
                                    <p className="text-sm text-gray-600">图片</p>
                                    <p className="text-2xl font-bold">{statistics.by_type?.image || 0}</p>
                                </div>
                            </div>
                        </CardContent>
                    </Card>
                    <Card>
                        <CardContent className="pt-6">
                            <div className="flex items-center space-x-2">
                                <File className="w-5 h-5 text-purple-600"/>
                                <div>
                                    <p className="text-sm text-gray-600">文档</p>
                                    <p className="text-2xl font-bold">{statistics.by_type?.document || 0}</p>
                                </div>
                            </div>
                        </CardContent>
                    </Card>
                    <Card>
                        <CardContent className="pt-6">
                            <div className="flex items-center space-x-2">
                                <Calendar className="w-5 h-5 text-orange-600"/>
                                <div>
                                    <p className="text-sm text-gray-600">本月上传</p>
                                    <p className="text-2xl font-bold">{statistics.uploaded_this_month}</p>
                                </div>
                            </div>
                        </CardContent>
                    </Card>
                </div>
            )}

            {/* 搜索和视图切换 */}
            <Card>
                <CardContent className="pt-6">
                    <div className="flex flex-col md:flex-row gap-4">
                        <div className="flex-1 relative">
                            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4"/>
                            <Input
                                placeholder="搜索文件名、标题、描述..."
                                value={searchQuery}
                                onChange={(e) => {
                                    setSearchQuery(e.target.value);
                                    setCurrentPage(1);
                                }}
                                className="pl-10"
                            />
                        </div>
                        <div className="flex gap-2">
                            <Button
                                variant={viewMode === 'grid' ? 'default' : 'outline'}
                                size="sm"
                                onClick={() => setViewMode('grid')}
                            >
                                <Grid3x3 className="w-4 h-4"/>
                            </Button>
                            <Button
                                variant={viewMode === 'list' ? 'default' : 'outline'}
                                size="sm"
                                onClick={() => setViewMode('list')}
                            >
                                <List className="w-4 h-4"/>
                            </Button>
                        </div>
                    </div>

                    {/* 高级过滤器 */}
                    {showFilters && (
                        <div className="mt-4 pt-4 border-t grid grid-cols-1 md:grid-cols-3 lg:grid-cols-6 gap-4">
                            <div>
                                <Label className="text-xs">媒体类型</Label>
                                <Select value={mediaType} onValueChange={(v) => {
                                    setMediaType(v === 'all' ? '' : v);
                                    setCurrentPage(1);
                                }}>
                                    <SelectTrigger>
                                        <SelectValue placeholder="全部类型"/>
                                    </SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="all">全部类型</SelectItem>
                                        <SelectItem value="image">图片</SelectItem>
                                        <SelectItem value="video">视频</SelectItem>
                                        <SelectItem value="document">文档</SelectItem>
                                    </SelectContent>
                                </Select>
                            </div>
                            <div>
                                <Label className="text-xs">起始日期</Label>
                                <Input
                                    type="date"
                                    value={dateFrom}
                                    onChange={(e) => {
                                        setDateFrom(e.target.value);
                                        setCurrentPage(1);
                                    }}
                                />
                            </div>
                            <div>
                                <Label className="text-xs">结束日期</Label>
                                <Input
                                    type="date"
                                    value={dateTo}
                                    onChange={(e) => {
                                        setDateTo(e.target.value);
                                        setCurrentPage(1);
                                    }}
                                />
                            </div>
                            <div>
                                <Label className="text-xs">最小大小 (KB)</Label>
                                <Input
                                    type="number"
                                    placeholder="0"
                                    value={minSize || ''}
                                    onChange={(e) => {
                                        setMinSize(e.target.value ? parseInt(e.target.value) * 1024 : null);
                                        setCurrentPage(1);
                                    }}
                                />
                            </div>
                            <div>
                                <Label className="text-xs">最大大小 (KB)</Label>
                                <Input
                                    type="number"
                                    placeholder="无限制"
                                    value={maxSize || ''}
                                    onChange={(e) => {
                                        setMaxSize(e.target.value ? parseInt(e.target.value) * 1024 : null);
                                        setCurrentPage(1);
                                    }}
                                />
                            </div>
                            <div className="flex items-end">
                                <Button variant="outline" onClick={resetFilters} className="w-full">
                                    <X className="w-4 h-4 mr-2"/>
                                    重置
                                </Button>
                            </div>
                        </div>
                    )}
                </CardContent>
            </Card>

            {/* 媒体列表 */}
            {isLoading ? (
                <div className="flex items-center justify-center py-12">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                </div>
            ) : media.length === 0 ? (
                <Card>
                    <CardContent className="py-12 text-center">
                        <ImageIcon className="w-16 h-16 text-gray-300 mx-auto mb-4"/>
                        <p className="text-gray-500">暂无媒体文件</p>
                    </CardContent>
                </Card>
            ) : viewMode === 'grid' ? (
                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6 gap-4">
                    {media.map((item) => (
                        <Card
                            key={item.id}
                            className={`cursor-pointer transition-all hover:shadow-lg ${
                                selectedItems.includes(item.id) ? 'ring-2 ring-blue-500' : ''
                            }`}
                            onClick={() => {
                                setSelectedMedia(item);
                                setDetailDialogOpen(true);
                            }}
                        >
                            <div className="relative aspect-square">
                                {item.thumbnail_url || item.url || (item.hash && item.hash.trim()) ? (
                                    <img
                                        src={item.thumbnail_url ? `${apiBaseUrl}${item.thumbnail_url}` : (item.url ? `${apiBaseUrl}${item.url}` : `${apiBaseUrl}${apiPrefix}/thumbnail?data=${item.hash}`)}
                                        alt={item.alt_text || item.filename}
                                        className="w-full h-full object-cover rounded-t-lg"
                                        crossOrigin="anonymous"
                                        onError={(e) => {
                                            const target = e.target as HTMLImageElement;
                                            target.onerror = null;
                                            // 如果缩略图加载失败，尝试使用 hash 生成缩略图 URL
                                            if (item.hash && item.hash.trim()) {
                                                target.src = `${apiBaseUrl}${apiPrefix}/thumbnail?data=${item.hash}`;
                                            } else {
                                                target.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjQiIGhlaWdodD0iNjQiIHZpZXdCb3g9IjAgMCA2NCA2NCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSIjZjBmMGYwIi8+PC9zdmc+';
                                            }
                                        }}
                                    />
                                ) : (
                                    <div
                                        className="w-full h-full flex items-center justify-center bg-gray-100 rounded-t-lg">
                                        <File className="w-8 h-8 text-gray-400"/>
                                    </div>
                                )}
                                <div className="absolute top-2 right-2">
                                    <input
                                        type="checkbox"
                                        checked={selectedItems.includes(item.id)}
                                        onChange={(e) => {
                                            e.stopPropagation();
                                            toggleSelect(item.id);
                                        }}
                                        className="w-4 h-4"
                                    />
                                </div>
                            </div>
                            <CardContent className="p-3">
                                <p className="text-sm font-medium truncate" title={item.filename}>
                                    {item.filename}
                                </p>
                                <p className="text-xs text-gray-500 mt-1">
                                    {formatFileSize(item.file_size || 0)}
                                </p>
                                
                                {/* 分类和标签显示 */}
                                {(item.category || item.tags) && (
                                    <div className="flex flex-wrap gap-1 mt-2">
                                        {item.category && (
                                            <Badge variant="secondary" className="text-[10px] h-4 px-1">
                                                {item.category}
                                            </Badge>
                                        )}
                                        {item.tags && item.tags.split(',').slice(0, 2).map((tag, idx) => (
                                            tag.trim() && (
                                                <Badge key={idx} variant="outline" className="text-[10px] h-4 px-1">
                                                    {tag.trim()}
                                                </Badge>
                                            )
                                        ))}
                                    </div>
                                )}
                                
                                {/* 操作按钮 */}
                                <div className="flex gap-1 mt-2">
                                    <Button
                                        size="sm"
                                        variant="ghost"
                                        className="h-6 px-2 text-xs"
                                        onClick={(e) => {
                                            e.stopPropagation();
                                            openSingleCategoryDialog(item);
                                        }}
                                        title="设置分类"
                                    >
                                        分类
                                    </Button>
                                    <Button
                                        size="sm"
                                        variant="ghost"
                                        className="h-6 px-2 text-xs"
                                        onClick={(e) => {
                                            e.stopPropagation();
                                            openSingleTagDialog(item);
                                        }}
                                        title="管理标签"
                                    >
                                        标签
                                    </Button>
                                </div>
                            </CardContent>
                        </Card>
                    ))}
                </div>
            ) : (
                <Card>
                    <div className="overflow-x-auto">
                        <table className="w-full">
                            <thead className="bg-gray-50">
                            <tr>
                                <th className="px-4 py-3 text-left">
                                    <input
                                        type="checkbox"
                                        checked={selectedItems.length === media.length}
                                        onChange={selectAll}
                                    />
                                </th>
                                <th className="px-4 py-3 text-left text-sm font-medium text-gray-700">预览</th>
                                <th className="px-4 py-3 text-left text-sm font-medium text-gray-700">文件名</th>
                                <th className="px-4 py-3 text-left text-sm font-medium text-gray-700">类型</th>
                                <th className="px-4 py-3 text-left text-sm font-medium text-gray-700">大小</th>
                                <th className="px-4 py-3 text-left text-sm font-medium text-gray-700">上传日期</th>
                            </tr>
                            </thead>
                            <tbody className="divide-y divide-gray-200">
                            {media.map((item) => (
                                <tr
                                    key={item.id}
                                    className={`hover:bg-gray-50 cursor-pointer ${
                                        selectedItems.includes(item.id) ? 'bg-blue-50' : ''
                                    }`}
                                    onClick={() => {
                                        setSelectedMedia(item);
                                        setDetailDialogOpen(true);
                                    }}
                                >
                                    <td className="px-4 py-3">
                                        <input
                                            type="checkbox"
                                            checked={selectedItems.includes(item.id)}
                                            onChange={(e) => {
                                                e.stopPropagation();
                                                toggleSelect(item.id);
                                            }}
                                        />
                                    </td>
                                    <td className="px-4 py-3">
                                        {item.thumbnail_url || item.url || (item.hash && item.hash.trim()) ? (
                                            <img
                                                src={item.thumbnail_url ? `${apiBaseUrl}${item.thumbnail_url}` : (item.url ? `${apiBaseUrl}${item.url}` : `${apiBaseUrl}${apiPrefix}/thumbnail?data=${item.hash}`)}
                                                alt=""
                                                className="w-12 h-12 object-cover rounded"
                                                crossOrigin="anonymous"
                                                onError={(e) => {
                                                    const target = e.target as HTMLImageElement;
                                                    target.onerror = null;
                                                    if (item.hash && item.hash.trim()) {
                                                        target.src = `${apiBaseUrl}${apiPrefix}/thumbnail?data=${item.hash}`;
                                                    }
                                                }}
                                            />
                                        ) : (
                                            <div
                                                className="w-12 h-12 flex items-center justify-center bg-gray-100 rounded">
                                                <File className="w-6 h-6 text-gray-400"/>
                                            </div>
                                        )}
                                    </td>
                                    <td className="px-4 py-3 text-sm">{item.filename}</td>
                                    <td className="px-4 py-3 text-sm">{item.media_type}</td>
                                    <td className="px-4 py-3 text-sm">{formatFileSize(item.file_size || 0)}</td>
                                    <td className="px-4 py-3 text-sm">{formatDate(item.created_at || '')}</td>
                                </tr>
                            ))}
                            </tbody>
                        </table>
                    </div>
                </Card>
            )}

            {/* 分页 */}
            {pagination && pagination.total_pages > 1 && (
                <div className="flex items-center justify-between">
                    <p className="text-sm text-gray-600">
                        第 {pagination.page} / {pagination.total_pages} 页，共 {pagination.total} 个文件
                    </p>
                    <div className="flex gap-2">
                        <Button
                            variant="outline"
                            size="sm"
                            disabled={!pagination.has_prev}
                            onClick={() => setCurrentPage(p => p - 1)}
                        >
                            上一页
                        </Button>
                        <Button
                            variant="outline"
                            size="sm"
                            disabled={!pagination.has_next}
                            onClick={() => setCurrentPage(p => p + 1)}
                        >
                            下一页
                        </Button>
                    </div>
                </div>
            )}

            {/* 详情对话框 */}
            <Dialog open={detailDialogOpen} onOpenChange={setDetailDialogOpen}>
                <DialogContent className="max-w-3xl">
                    <DialogHeader>
                        <DialogTitle>媒体详情</DialogTitle>
                    </DialogHeader>
                    {selectedMedia && (
                        <div className="space-y-4">
                            <div className="aspect-video bg-gray-100 rounded-lg overflow-hidden relative">
                                {/* 始终显示缩略图作为占位 */}
                                {selectedMedia.thumbnail_url || selectedMedia.hash ? (
                                    <img
                                        src={selectedMedia.thumbnail_url ? `${apiBaseUrl}${selectedMedia.thumbnail_url}` : `${apiBaseUrl}${apiPrefix}/thumbnail?data=${selectedMedia.hash}`}
                                        alt={selectedMedia.alt_text || selectedMedia.filename}
                                        className={`w-full h-full object-contain transition-opacity duration-300 ${
                                            detailImageLoaded ? 'opacity-0 absolute inset-0' : 'opacity-100'
                                        }`}
                                        crossOrigin="anonymous"
                                    />
                                ) : null}
                                
                                {/* 懒加载原图 */}
                                {shouldLoadDetailImage && (selectedMedia.url || selectedMedia.hash) ? (
                                    <img
                                        src={selectedMedia.url ? `${apiBaseUrl}${selectedMedia.url}` : `${apiBaseUrl}${apiPrefix}/thumbnail?data=${selectedMedia.hash}`}
                                        alt={selectedMedia.alt_text || selectedMedia.filename}
                                        className={`w-full h-full object-contain transition-opacity duration-300 ${
                                            detailImageLoaded ? 'opacity-100' : 'opacity-0'
                                        }`}
                                        loading="lazy"
                                        onLoad={() => setDetailImageLoaded(true)}
                                        onError={(e) => {
                                            const target = e.target as HTMLImageElement;
                                            target.onerror = null;
                                            // 如果原图加载失败，显示缩略图
                                            if (selectedMedia.hash) {
                                                target.src = `${apiBaseUrl}${apiPrefix}/thumbnail?data=${selectedMedia.hash}`;
                                                setDetailImageLoaded(true);
                                            }
                                        }}
                                    />
                                ) : shouldLoadDetailImage ? (
                                    <div className="absolute inset-0 flex items-center justify-center">
                                        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900"></div>
                                    </div>
                                ) : null}
                                
                                {/* 如果没有图片，显示占位符 */}
                                {!selectedMedia.thumbnail_url && !selectedMedia.url && !selectedMedia.hash && (
                                    <div className="w-full h-full flex items-center justify-center">
                                        <File className="w-16 h-16 text-gray-400"/>
                                    </div>
                                )}
                            </div>
                            <div className="grid grid-cols-2 gap-4 text-sm">
                                <div>
                                    <Label className="text-gray-600">文件名</Label>
                                    <p>{selectedMedia.filename}</p>
                                </div>
                                <div>
                                    <Label className="text-gray-600">文件类型</Label>
                                    <p>{selectedMedia.mime_type}</p>
                                </div>
                                <div>
                                    <Label className="text-gray-600">文件大小</Label>
                                    <p>{formatFileSize(selectedMedia.file_size || 0)}</p>
                                </div>
                                <div>
                                    <Label className="text-gray-600">尺寸</Label>
                                    <p>{selectedMedia.width} x {selectedMedia.height}</p>
                                </div>
                                <div>
                                    <Label className="text-gray-600">上传日期</Label>
                                    <p>{formatDate(selectedMedia.created_at || '')}</p>
                                </div>
                            </div>
                        </div>
                    )}
                    <DialogFooter>
                        {selectedMedia?.mime_type?.startsWith('image/') && (
                            <Button onClick={() => handleEditImage(selectedMedia)}>
                                <Edit className="w-4 h-4 mr-2"/>
                                编辑图片
                            </Button>
                        )}
                        <Button variant="outline" onClick={() => setDetailDialogOpen(false)}>
                            关闭
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* 图片编辑器对话框 */}
            <Dialog open={editorDialogOpen} onOpenChange={setEditorDialogOpen}>
                <DialogContent className="max-w-6xl max-h-[90vh] p-0">
                    {editingMedia && (
                        <ImageEditor
                            imageUrl={`${apiBaseUrl}${editingMedia.url}`}
                            onSave={handleSaveEditedImage}
                            onClose={() => setEditorDialogOpen(false)}
                        />
                    )}
                </DialogContent>
            </Dialog>

            {/* 批量分类对话框 */}
            <Dialog open={categoryDialogOpen} onOpenChange={setCategoryDialogOpen}>
                <DialogContent className="sm:max-w-md">
                    <DialogHeader>
                        <DialogTitle>批量设置分类</DialogTitle>
                    </DialogHeader>
                    <div className="space-y-4 py-4">
                        <div className="space-y-2">
                            <Label htmlFor="category">分类名称</Label>
                            <Input
                                id="category"
                                placeholder="输入分类名称，如：产品图片、文章配图等"
                                value={batchCategory}
                                onChange={(e) => setBatchCategory(e.target.value)}
                            />
                            <p className="text-sm text-gray-500">
                                将为选中的 {selectedItems.length} 个文件设置分类
                            </p>
                        </div>
                    </div>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setCategoryDialogOpen(false)}>
                            取消
                        </Button>
                        <Button onClick={handleBatchCategorize} disabled={!batchCategory}>
                            确定
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* 批量标签对话框 */}
            <Dialog open={tagDialogOpen} onOpenChange={setTagDialogOpen}>
                <DialogContent className="sm:max-w-md">
                    <DialogHeader>
                        <DialogTitle>批量设置标签</DialogTitle>
                    </DialogHeader>
                    <div className="space-y-4 py-4">
                        <div className="space-y-2">
                            <Label htmlFor="tags">标签列表</Label>
                            <Input
                                id="tags"
                                placeholder="输入标签，用逗号分隔，如：风景,人像,旅行"
                                value={batchTags}
                                onChange={(e) => setBatchTags(e.target.value)}
                            />
                            <p className="text-sm text-gray-500">
                                将为选中的 {selectedItems.length} 个文件设置标签
                            </p>
                        </div>
                        <div className="space-y-2">
                            <Label>标签模式</Label>
                            <Select value={tagMode} onValueChange={(v) => setTagMode(v as 'add' | 'replace')}>
                                <SelectTrigger>
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="add">追加标签（保留原有标签）</SelectItem>
                                    <SelectItem value="replace">替换标签（清空原有标签）</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>
                    </div>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setTagDialogOpen(false)}>
                            取消
                        </Button>
                        <Button onClick={handleBatchTags} disabled={!batchTags}>
                            确定
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* 单个媒体分类对话框 */}
            <Dialog open={singleCategoryDialog.open} onOpenChange={(open) => setSingleCategoryDialog({open, media: singleCategoryDialog.media})}>
                <DialogContent className="sm:max-w-md">
                    <DialogHeader>
                        <DialogTitle>设置分类</DialogTitle>
                    </DialogHeader>
                    <div className="space-y-4 py-4">
                        <div className="space-y-2">
                            <Label htmlFor="single-category">分类名称</Label>
                            <Input
                                id="single-category"
                                placeholder="输入分类名称"
                                value={singleCategory}
                                onChange={(e) => setSingleCategory(e.target.value)}
                                onKeyDown={(e) => {
                                    if (e.key === 'Enter') {
                                        handleSaveSingleCategory();
                                    }
                                }}
                            />
                        </div>
                    </div>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setSingleCategoryDialog({open: false, media: null})}>
                            取消
                        </Button>
                        <Button onClick={handleSaveSingleCategory} disabled={!singleCategory}>
                            确定
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* 单个媒体标签对话框 */}
            <Dialog open={singleTagDialog.open} onOpenChange={(open) => setSingleTagDialog({open, media: singleTagDialog.media})}>
                <DialogContent className="sm:max-w-md">
                    <DialogHeader>
                        <DialogTitle>管理标签</DialogTitle>
                    </DialogHeader>
                    <div className="space-y-4 py-4">
                        <div className="space-y-2">
                            <Label>当前标签</Label>
                            <div className="flex flex-wrap gap-2 min-h-[40px] p-2 border rounded-md">
                                {singleTags.map((tag, idx) => (
                                    <Badge key={idx} variant="secondary" className="gap-1">
                                        {tag}
                                        <button
                                            onClick={() => handleRemoveSingleTag(tag)}
                                            className="ml-1 hover:text-red-500"
                                        >
                                            ×
                                        </button>
                                    </Badge>
                                ))}
                                {singleTags.length === 0 && (
                                    <span className="text-sm text-gray-400">暂无标签</span>
                                )}
                            </div>
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="new-tag">添加标签</Label>
                            <div className="flex gap-2">
                                <Input
                                    id="new-tag"
                                    placeholder="输入标签名称"
                                    value={newSingleTag}
                                    onChange={(e) => setNewSingleTag(e.target.value)}
                                    onKeyDown={(e) => {
                                        if (e.key === 'Enter') {
                                            handleAddSingleTag();
                                        }
                                    }}
                                />
                                <Button onClick={handleAddSingleTag} disabled={!newSingleTag.trim()}>
                                    添加
                                </Button>
                            </div>
                        </div>
                    </div>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setSingleTagDialog({open: false, media: null})}>
                            取消
                        </Button>
                        <Button onClick={handleSaveSingleTags}>
                            保存
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    );
}
