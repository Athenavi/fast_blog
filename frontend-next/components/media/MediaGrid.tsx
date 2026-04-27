'use client';

import React, {useState} from 'react';
import {Draggable, Droppable, DropResult} from '@hello-pangea/dnd';
import {MediaFile} from '@/lib/api';
import {Card, CardContent} from '@/components/ui/card';
import {Button} from '@/components/ui/button';
import {Badge} from '@/components/ui/badge';
import {Checkbox} from '@/components/ui/checkbox';
import {
  Copy,
  Download,
  Eye,
  File,
  FolderOpen,
  Grid3x3,
  GripVertical,
  Image as ImageIcon,
  List as ListIcon,
  MoveRight,
  Music,
  Plus,
  Tag,
  Trash2,
  Video,
  X
} from 'lucide-react';

// 缩略图组件，支持加载失败时显示默认图标
const ThumbnailImage: React.FC<{
  hash: string;
  filename: string;
  mimeType: string;
  fallbackIcon: React.ReactNode;
}> = ({ hash, filename, mimeType, fallbackIcon }) => {
  const [failed, setFailed] = useState(false);
  const [apiBaseUrl, setApiBaseUrl] = React.useState('http://localhost:8000');
  const [apiPrefix, setApiPrefix] = React.useState('/api/v1');

  // 加载 API 配置
  React.useEffect(() => {
    const loadConfig = async () => {
      const config = await import('@/lib/config');
      const apiConfig = config.getConfig();
      setApiBaseUrl(apiConfig.API_BASE_URL);
      setApiPrefix(apiConfig.API_PREFIX);
    };
    loadConfig();
  }, []);

  if (failed) {
    return (
      <div className="flex items-center justify-center w-full h-full">
        {fallbackIcon}
      </div>
    );
  }

  return (
    <img
      src={`${apiBaseUrl}${apiPrefix}/thumbnail?data=${hash}`}
      alt={filename}
      className="w-full h-full object-cover rounded-t-lg"
      loading="lazy"
      crossOrigin="anonymous"
      onError={() => setFailed(true)}
    />
  );
};

interface ContextMenuPosition {
  x: number;
  y: number;
}

interface MediaGridProps {
  mediaFiles: MediaFile[];
  loading: boolean;
  onPreview: (media: MediaFile) => void;
  onDelete: (media: MediaFile) => void;
  totalItems: number;
  viewMode?: 'grid' | 'list';
  onViewModeChange?: (mode: 'grid' | 'list') => void;
  selectedItems?: number[];
  onSelectItem?: (id: number) => void;
  onSelectAll?: () => void;
  onBatchDelete?: (ids: number[]) => void;
  onUpdateCategory?: (mediaId: number, category: string) => Promise<void>;
  onUpdateTags?: (mediaId: number, tags: string[]) => Promise<void>;
  onDragEnd?: (result: DropResult) => void;
  apiBaseUrl?: string; // API 基础 URL
  apiPrefix?: string; // API 前缀
}

const MediaGrid: React.FC<MediaGridProps> = ({
  mediaFiles,
  loading,
  onPreview,
  onDelete,
  totalItems,
  viewMode = 'grid',
  onViewModeChange,
  selectedItems = [],
  onSelectItem,
  onSelectAll,
  onBatchDelete,
  onUpdateCategory,
  onUpdateTags,
                                               onDragEnd,
                                               apiBaseUrl: propApiBaseUrl,
                                               apiPrefix: propApiPrefix
}) => {
  const [apiBaseUrl, setApiBaseUrl] = React.useState(propApiBaseUrl || 'http://localhost:8000');
  const [apiPrefix, setApiPrefix] = React.useState(propApiPrefix || '/api/v1');

  // 右键菜单状态
  const [contextMenu, setContextMenu] = useState<{ position: ContextMenuPosition; media: MediaFile } | null>(null);

  // 分类管理状态
  const [categoryDialog, setCategoryDialog] = useState<{ open: boolean; media: MediaFile | null }>({
    open: false,
    media: null
  });
  const [newCategory, setNewCategory] = useState('');

  // 标签管理状态
  const [tagDialog, setTagDialog] = useState<{ open: boolean; media: MediaFile | null }>({
    open: false,
    media: null
  });
  const [currentTags, setCurrentTags] = useState<string[]>([]);
  const [newTag, setNewTag] = useState('');

  // 批量移动状态
  const [moveDialog, setMoveDialog] = useState(false);
  const [targetFolderPath, setTargetFolderPath] = useState<string | null>(null);
  const [folders, setFolders] = useState<Array<{ id: number; name: string; path: string }>>([]);

  // 加载 API 配置
  React.useEffect(() => {
    const loadConfig = async () => {
      const config = await import('@/lib/config');
      const apiConfig = config.getConfig();
      setApiBaseUrl(apiConfig.API_BASE_URL);
      setApiPrefix(apiConfig.API_PREFIX);
    };
    loadConfig();
  }, []);

  // 加载文件夹列表（使用树形结构）
  const loadFolders = async () => {
    try {
      const token = document.cookie.split(';').find(c => c.trim().startsWith('access_token='))?.split('=')[1];
      const response = await fetch(`${apiBaseUrl}${apiPrefix}/media/folders/tree`, {
        headers: {
          'Authorization': `Bearer ${decodeURIComponent(token || '')}`,
          'Content-Type': 'application/json'
        }
      });
      if (response.ok) {
        const data = await response.json();
        if (data.success) {
          // 将树形结构展平为列表，并构建完整路径
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          const flattenFolders = (nodes: Array<{ id: number; name: string; children?: Array<any> }>, parentPath: string = ''): Array<{ id: number; name: string; path: string }> => {
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
          
          setFolders(flattenFolders(data.data.tree || []));
        }
      }
    } catch (error) {
      console.error('加载文件夹失败:', error);
    }
  };

  // 打开批量移动对话框
  const handleOpenMoveDialog = () => {
    if (selectedItems.length === 0) return;
    loadFolders();
    setTargetFolderPath(null);
    setMoveDialog(true);
  };

  // 执行批量移动
  const handleBatchMove = async () => {
    try {
      const token = document.cookie.split(';').find(c => c.trim().startsWith('access_token='))?.split('=')[1];
      const response = await fetch(`${apiBaseUrl}${apiPrefix}/media/folders/move-media`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${decodeURIComponent(token || '')}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          media_ids: selectedItems,
          folder_path: targetFolderPath  // 使用路径而非 ID
        })
      });

      if (response.ok) {
        const data = await response.json();
        if (data.success) {
          alert(`成功移动 ${data.data.moved_count} 个文件`);
          setMoveDialog(false);
          // 通知父组件刷新
          window.dispatchEvent(new CustomEvent('mediaFilesChanged'));
        } else {
          alert(`移动失败: ${data.error}`);
        }
      }
    } catch (error) {
      console.error('批量移动失败:', error);
      alert('移动失败');
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

  const getFileIconClass = (mimeType: string) => {
    if (mimeType.startsWith('image/')) return 'fas fa-file-image text-blue-500';
    if (mimeType.startsWith('video/')) return 'fas fa-file-video text-purple-500';
    if (mimeType.startsWith('audio/')) return 'fas fa-file-audio text-green-500';
    if (mimeType === 'application/pdf') return 'fas fa-file-pdf text-red-500';
    if (mimeType.includes('word')) return 'fas fa-file-word text-blue-600';
    if (mimeType.includes('excel')) return 'fas fa-file-excel text-green-600';
    if (mimeType.includes('powerpoint')) return 'fas fa-file-powerpoint text-orange-500';
    if (mimeType.startsWith('text/')) return 'fas fa-file-alt text-gray-500';
    if (mimeType.includes('zip') || mimeType.includes('rar')) return 'fas fa-file-archive text-yellow-500';
    return 'fas fa-file text-gray-400';
  };

  const downloadFile = (hash: string) => {
    window.open(`${apiBaseUrl}${apiPrefix}/media/${hash}`, '_blank');
  };

  // 获取文件图标组件
  const getFileIcon = (mimeType: string) => {
    if (mimeType.startsWith('image/')) return <ImageIcon className="w-8 h-8 text-blue-500" />;
    if (mimeType.startsWith('video/')) return <Video className="w-8 h-8 text-purple-500" />;
    if (mimeType.startsWith('audio/')) return <Music className="w-8 h-8 text-green-500" />;
    return <File className="w-8 h-8 text-gray-400" />;
  };

  // 右键菜单处理
  const handleContextMenu = (e: React.MouseEvent, media: MediaFile) => {
    e.preventDefault();
    e.stopPropagation();
    setContextMenu({
      position: { x: e.clientX, y: e.clientY },
      media
    });
  };

  // 关闭右键菜单
  const closeContextMenu = () => {
    setContextMenu(null);
  };

  // 复制文件链接
  const handleCopyLink = (media: MediaFile) => {
    const url = `${window.location.origin}${apiBaseUrl}${apiPrefix}/media/${media.hash}`;
    navigator.clipboard.writeText(url).then(() => {
      alert('链接已复制到剪贴板');
    }).catch(() => {
      alert('复制失败');
    });
    closeContextMenu();
  };

  // 右键菜单删除
  const handleContextMenuDelete = (media: MediaFile) => {
    if (confirm(`确定要删除 "${media.original_filename}" 吗？此操作不可恢复！`)) {
      onDelete(media);
    }
    closeContextMenu();
  };

  // 批量删除
  const handleBatchDeleteClick = () => {
    if (selectedItems.length === 0) return;
    if (confirm(`确定要删除选中的 ${selectedItems.length} 个文件吗？此操作不可恢复！`)) {
      onBatchDelete && onBatchDelete(selectedItems);
    }
  };

  // 打开分类对话框
  const openCategoryDialog = (media: MediaFile) => {
    setCategoryDialog({ open: true, media });
    setNewCategory(media.category || '');
  };

  // 保存分类
  const handleSaveCategory = async () => {
    if (!categoryDialog.media || !onUpdateCategory) return;

    try {
      await onUpdateCategory(categoryDialog.media.id, newCategory.trim());
      setCategoryDialog({ open: false, media: null });
      setNewCategory('');
    } catch (error) {
      console.error('更新分类失败:', error);
      alert('更新分类失败');
    }
  };

  // 打开标签对话框
  const openTagDialog = (media: MediaFile) => {
    setTagDialog({ open: true, media });
    // 解析标签字符串为数组
    const tags = media.tags ? media.tags.split(',').map(t => t.trim()).filter(t => t) : [];
    setCurrentTags(tags);
    setNewTag('');
  };

  // 添加标签
  const handleAddTag = () => {
    const tag = newTag.trim();
    if (!tag) return;
    
    // 检查是否已达到最大标签数（5个）
    if (currentTags.length >= 5) {
      alert('最多只能添加5个标签');
      return;
    }
    
    if (!currentTags.includes(tag)) {
      setCurrentTags([...currentTags, tag]);
      setNewTag('');
    }
  };

  // 移除标签
  const handleRemoveTag = (tagToRemove: string) => {
    setCurrentTags(currentTags.filter(tag => tag !== tagToRemove));
  };

  // 保存标签
  const handleSaveTags = async () => {
    if (!tagDialog.media || !onUpdateTags) return;

    try {
      await onUpdateTags(tagDialog.media.id, currentTags);
      setTagDialog({ open: false, media: null });
      setCurrentTags([]);
      setNewTag('');
    } catch (error) {
      console.error('更新标签失败:', error);
      alert('更新标签失败');
    }
  };

  // 点击页面其他地方关闭菜单
  React.useEffect(() => {
    const handleClick = () => closeContextMenu();
    document.addEventListener('click', handleClick);
    return () => document.removeEventListener('click', handleClick);
  }, []);

  if (loading) {
    return (
      <div className="p-12 text-center">
        <i className="fas fa-spinner fa-spin text-3xl text-blue-500 mb-4"></i>
        <p className="text-gray-500">加载中...</p>
      </div>
    );
  }

  if (mediaFiles.length === 0) {
    return (
      <div className="p-12 text-center">
        <div className="text-gray-400 mb-4">
          <i className="fas fa-file-archive text-5xl"></i>
        </div>
        <p className="text-gray-500">暂无媒体文件</p>
      </div>
    );
  }

  // 统一返回一个 Fragment，包含视图和所有对话框/菜单
  return (
    <>
      {(viewMode as 'grid' | 'list') === 'grid' ? (
        // 网格视图
        <div className="p-6">
          {/* 工具栏 */}
          {onViewModeChange && onSelectAll && (
            <div className="mb-4 flex justify-between items-center">
              <div className="flex items-center gap-2">
                {onSelectAll && mediaFiles.length > 0 && (
                  <Checkbox
                    checked={selectedItems.length === mediaFiles.length && mediaFiles.length > 0}
                    onCheckedChange={onSelectAll}
                  />
                )}
                <span className="text-sm text-gray-600">
                  已选 {selectedItems.length} / {mediaFiles.length}
                </span>
                {selectedItems.length > 0 && (
                  <>
                    <Button
                      size="sm"
                      variant="destructive"
                      onClick={handleBatchDeleteClick}
                    >
                      <Trash2 className="w-4 h-4 mr-1" />
                      批量删除
                    </Button>
                    <Button
                      size="sm"
                      variant="default"
                      onClick={handleOpenMoveDialog}
                    >
                      <MoveRight className="w-4 h-4 mr-1" />
                      移动到文件夹
                    </Button>
                  </>
                )}
              </div>
              <div className="flex gap-2">
                <Button
                    variant={(viewMode as 'grid' | 'list') === 'grid' ? 'default' : 'outline'}
                  size="sm"
                    onClick={() => onViewModeChange && onViewModeChange('grid')}
                >
                  <Grid3x3 className="w-4 h-4" />
                </Button>
                <Button
                    variant={(viewMode as 'grid' | 'list') === 'list' ? 'default' : 'outline'}
                  size="sm"
                    onClick={() => onViewModeChange && onViewModeChange('list')}
                >
                  <ListIcon className="w-4 h-4" />
                </Button>
              </div>
            </div>
          )}

          {/* 网格布局 */}
          <Droppable droppableId="media-grid" type="MEDIA" direction="horizontal">
            {(provided) => (
                <div 
                  ref={provided.innerRef}
                  {...provided.droppableProps}
                  className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4"
                >
                  {mediaFiles.map((media, index) => {
                    const isSelected = selectedItems.includes(media.id);
                    return (
                        <Draggable key={media.id} draggableId={`media-${media.id}`} index={index}>
                        {(provided, snapshot) => {
                          // 添加拖拽状态日志
                          if (snapshot.isDragging) {
                            console.log('🚀 开始拖拽文件:', media.id, media.original_filename);
                          }
                          return (
                          <div
                            ref={provided.innerRef}
                            {...provided.draggableProps}
                            className={`${snapshot.isDragging ? 'opacity-50' : ''}`}
                          >
                            <Card
                              className={`group cursor-pointer transition-all hover:shadow-md ${isSelected ? 'ring-2 ring-blue-500' : ''
                                }`}
                              onClick={() => onSelectItem && onSelectItem(media.id)}
                            >
                              <CardContent className="p-0">
                                {/* 缩略图区域 */}
                                <div
                                  className="relative h-32 flex items-center justify-center bg-gray-100 overflow-hidden rounded-t-lg"
                                  onContextMenu={(e) => handleContextMenu(e, media)}
                                >
                      {onSelectItem && (
                        <div className="absolute top-2 left-2 z-10">
                          <Checkbox
                            checked={isSelected}
                            onCheckedChange={(checked) => {
                              onSelectItem(media.id);
                            }}
                            onClick={(e) => e.stopPropagation()}
                          />
                        </div>
                      )}
                      
                      {/* 拖拽手柄 */}
                      <div
                        {...provided.dragHandleProps}
                        className="absolute top-2 right-2 z-10 opacity-0 group-hover:opacity-100 transition-opacity cursor-move"
                      >
                        <div className="bg-white/90 dark:bg-gray-800/90 p-1 rounded shadow-sm hover:bg-white dark:hover:bg-gray-700">
                          <GripVertical className="w-4 h-4 text-gray-600 dark:text-gray-300" />
                        </div>
                      </div>

                      {media.mime_type.startsWith('image/') || media.mime_type.startsWith('video/') || media.mime_type.startsWith('audio/') ? (
                        <ThumbnailImage
                          hash={media.hash}
                          filename={media.original_filename}
                          mimeType={media.mime_type}
                          fallbackIcon={getFileIcon(media.mime_type)}
                        />
                      ) : (
                        <div className="flex items-center justify-center">
                          {getFileIcon(media.mime_type)}
                        </div>
                      )}

                      {/* 悬停操作按钮 */}
                      <div className="absolute inset-0 bg-gradient-to-t from-black/50 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-all flex items-end justify-center pb-2">
                        <div className="flex gap-1">
                          <Button
                            size="sm"
                            variant="secondary"
                            className="bg-white/90 hover:bg-white shadow-sm"
                            onClick={(e) => {
                              e.stopPropagation();
                              onPreview(media);
                            }}
                          >
                            <Eye className="w-3 h-3" />
                          </Button>
                          <Button
                            size="sm"
                            variant="secondary"
                            className="bg-white/90 hover:bg-white shadow-sm"
                            onClick={(e) => {
                              e.stopPropagation();
                              downloadFile(media.hash);
                            }}
                          >
                            <Download className="w-3 h-3" />
                          </Button>
                          <Button
                            size="sm"
                            variant="destructive"
                            className="shadow-sm"
                            onClick={(e) => {
                              e.stopPropagation();
                              onDelete(media);
                            }}
                          >
                            <Trash2 className="w-3 h-3" />
                          </Button>
                        </div>
                      </div>
                    </div>

                    {/* 文件信息 */}
                    <div className="p-3">
                      <h3
                        title={media.original_filename}
                        className="text-xs font-medium text-gray-900 truncate mb-1"
                      >
                        {media.original_filename}
                      </h3>

                      {/* 分类和标签显示 */}
                      {(media.category || media.tags) && (
                        <div className="flex flex-wrap gap-1 mb-2">
                          {media.category && (
                            <Badge variant="secondary" className="text-[10px] h-4 px-1">
                              <FolderOpen className="w-2 h-2 mr-0.5" />
                              {media.category}
                            </Badge>
                          )}
                          {media.tags && media.tags.split(',').slice(0, 5).map((tag, idx) => (
                            tag.trim() && (
                              <Badge key={idx} variant="outline" className="text-[10px] h-4 px-1">
                                <Tag className="w-2 h-2 mr-0.5" />
                                {tag.trim()}
                              </Badge>
                            )
                          ))}
                        </div>
                      )}

                      <div className="flex justify-between items-center text-xs text-gray-500">
                        <span>{formatFileSize(media.file_size)}</span>
                        <span>{new Date(media.created_at || '').toLocaleDateString('zh-CN')}</span>
                      </div>

                      {/* 快速操作按钮 */}
                      <div className="flex gap-1 mt-2 pt-2 border-t">
                        <Button
                          size="sm"
                          variant="ghost"
                          className="h-6 px-2 text-xs"
                          onClick={(e) => {
                            e.stopPropagation();
                            openCategoryDialog(media);
                          }}
                        >
                          <FolderOpen className="w-3 h-3 mr-1" />
                          分类
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          className="h-6 px-2 text-xs"
                          onClick={(e) => {
                            e.stopPropagation();
                            openTagDialog(media);
                          }}
                        >
                          <Tag className="w-3 h-3 mr-1" />
                          标签
                        </Button>
                      </div>
                                </div>
                              </CardContent>
                            </Card>
                          </div>
                          );
                        }}
                      </Draggable>
                    );
                  })}
                  {provided.placeholder}
                </div>
              )}
            </Droppable>
        </div>
      ) : (
        // 列表视图
        <div className="p-6">
          {/* 工具栏 */}
          {onViewModeChange && onSelectAll && (
            <div className="mb-4 flex justify-between items-center">
              <div className="flex items-center gap-2">
                {onSelectAll && mediaFiles.length > 0 && (
                  <Checkbox
                    checked={selectedItems.length === mediaFiles.length && mediaFiles.length > 0}
                    onCheckedChange={onSelectAll}
                  />
                )}
                <span className="text-sm text-gray-600">
                  已选 {selectedItems.length} / {mediaFiles.length}
                </span>
              </div>
              <div className="flex gap-2">
                <Button
                    variant={(viewMode as 'grid' | 'list') === 'grid' ? 'default' : 'outline'}
                  size="sm"
                    onClick={() => onViewModeChange && onViewModeChange('grid')}
                >
                  <Grid3x3 className="w-4 h-4" />
                </Button>
                <Button
                    variant={(viewMode as 'grid' | 'list') === 'list' ? 'default' : 'outline'}
                  size="sm"
                    onClick={() => onViewModeChange && onViewModeChange('list')}
                >
                  <ListIcon className="w-4 h-4" />
                </Button>
              </div>
            </div>
          )}

          {/* 列表布局 */}
          <Droppable droppableId="media-list" type="MEDIA">
            {(provided) => (
                <div
                  ref={provided.innerRef}
                  {...provided.droppableProps}
                  className="border rounded-lg overflow-hidden"
                >
                  <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  {onSelectItem && (
                    <th className="px-4 py-3 text-left">
                      <Checkbox
                        checked={selectedItems.length === mediaFiles.length && mediaFiles.length > 0}
                        onCheckedChange={onSelectAll}
                      />
                    </th>
                  )}
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">文件</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">大小</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">类型</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">日期</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">操作</th>
                </tr>
              </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {mediaFiles.map((media, index) => {
                      const isSelected = selectedItems.includes(media.id);
                      return (
                          <Draggable key={media.id} draggableId={`media-${media.id}`} index={index}>
                          {(provided, snapshot) => (
                            <tr
                              ref={provided.innerRef}
                              {...provided.draggableProps}
                              className={`hover:bg-gray-50 cursor-pointer ${isSelected ? 'bg-blue-50' : ''} ${snapshot.isDragging ? 'opacity-50' : ''}`}
                              onClick={() => onSelectItem && onSelectItem(media.id)}
                            >
                              {onSelectItem && (
                                <td className="px-4 py-3">
                                  <Checkbox
                                    checked={isSelected}
                                    onCheckedChange={(checked) => {
                                      onSelectItem(media.id);
                                    }}
                                    onClick={(e) => e.stopPropagation()}
                                  />
                                </td>
                              )}
                              <td className="px-4 py-3">
                                <div className="flex items-center">
                                  {/* 拖拽手柄 */}
                                  <div
                                    {...provided.dragHandleProps}
                                    className="cursor-move mr-2 opacity-0 group-hover:opacity-100 hover:opacity-100 transition-opacity"
                                  >
                                    <GripVertical className="w-4 h-4 text-gray-400" />
                                  </div>
                                  <div className="flex-shrink-0 h-10 w-10">
                            {media.mime_type.startsWith('image/') || media.mime_type.startsWith('video/') ? (
                              <img
                                src={`${apiBaseUrl}${apiPrefix}/thumbnail/?data=${media.hash}`}
                                alt={media.original_filename}
                                className="h-10 w-10 rounded object-cover"
                                loading="lazy"
                                crossOrigin="anonymous"
                              />
                            ) : (
                              <div className="h-10 w-10 flex items-center justify-center bg-gray-100 rounded">
                                {getFileIcon(media.mime_type)}
                              </div>
                            )}
                          </div>
                          <div className="ml-4">
                            <div className="text-sm font-medium text-gray-900 truncate max-w-xs">
                              {media.original_filename}
                            </div>
                            {/* 分类和标签 */}
                            {(media.category || media.tags) && (
                              <div className="flex flex-wrap gap-1 mt-1">
                                {media.category && (
                                  <Badge variant="secondary" className="text-[10px] h-4 px-1">
                                    <FolderOpen className="w-2 h-2 mr-0.5" />
                                    {media.category}
                                  </Badge>
                                )}
                                {media.tags && media.tags.split(',').slice(0, 5).map((tag, idx) => (
                                  tag.trim() && (
                                    <Badge key={idx} variant="outline" className="text-[10px] h-4 px-1">
                                      <Tag className="w-2 h-2 mr-0.5" />
                                      {tag.trim()}
                                    </Badge>
                                  )
                                ))}
                              </div>
                            )}
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-500">
                        {formatFileSize(media.file_size)}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap">
                        <Badge variant="outline" className="text-xs">
                          {media.mime_type.split('/')[0]}
                        </Badge>
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-500">
                        {new Date(media.created_at || '').toLocaleDateString('zh-CN')}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-right text-sm font-medium">
                        <div className="flex justify-end gap-1 group">
                          <Button
                            size="sm"
                            variant="ghost"
                            className="h-7 px-2"
                            onClick={(e) => {
                              e.stopPropagation();
                              openCategoryDialog(media);
                            }}
                            title="设置分类"
                          >
                            <FolderOpen className="w-3.5 h-3.5" />
                          </Button>
                          <Button
                            size="sm"
                            variant="ghost"
                            className="h-7 px-2"
                            onClick={(e) => {
                              e.stopPropagation();
                              openTagDialog(media);
                            }}
                            title="管理标签"
                          >
                            <Tag className="w-3.5 h-3.5" />
                          </Button>
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={(e) => {
                              e.stopPropagation();
                              onPreview(media);
                            }}
                          >
                            <Eye className="w-4 h-4" />
                          </Button>
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={(e) => {
                              e.stopPropagation();
                              downloadFile(media.hash);
                            }}
                          >
                            <Download className="w-4 h-4" />
                          </Button>
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={(e) => {
                              e.stopPropagation();
                              onDelete(media);
                            }}
                          >
                            <Trash2 className="w-4 h-4 text-red-500" />
                          </Button>
                        </div>
                      </td>
                            </tr>
                          )}
                        </Draggable>
                      );
                    })}
                    {provided.placeholder}
                  </tbody>
                </table>
              </div>
            )}
          </Droppable>
        </div>
      )}

      {/* 右键菜单 */}
      {contextMenu && (
        <div
          className="fixed z-50 bg-white rounded-lg shadow-lg border border-gray-200 py-1 min-w-[160px]"
          style={{
            left: contextMenu.position.x,
            top: contextMenu.position.y
          }}
          onClick={(e) => e.stopPropagation()}
        >
          <button
            className="w-full px-4 py-2 text-left text-sm hover:bg-gray-100 flex items-center gap-2"
            onClick={() => handleCopyLink(contextMenu.media)}
          >
            <Copy className="w-4 h-4" />
            复制链接
          </button>
          <button
            className="w-full px-4 py-2 text-left text-sm hover:bg-gray-100 flex items-center gap-2 text-red-600"
            onClick={() => handleContextMenuDelete(contextMenu.media)}
          >
            <Trash2 className="w-4 h-4" />
            删除
          </button>
        </div>
      )}

      {/* 分类管理对话框 */}
      {categoryDialog.open && categoryDialog.media && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="bg-white rounded-lg shadow-xl p-6 w-96 max-w-[90vw]">
            <h3 className="text-lg font-semibold mb-4">设置分类</h3>
            <p className="text-sm text-gray-600 mb-4 truncate">
              {categoryDialog.media.original_filename}
            </p>
            <input
              type="text"
              value={newCategory}
              onChange={(e) => setNewCategory(e.target.value)}
              placeholder="输入分类名称（留空则清除分类）"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              onKeyPress={(e) => e.key === 'Enter' && handleSaveCategory()}
              autoFocus
            />
            <div className="flex gap-2 mt-4">
              <Button
                variant="outline"
                className="flex-1"
                onClick={() => setCategoryDialog({ open: false, media: null })}
              >
                取消
              </Button>
              <Button
                className="flex-1"
                onClick={handleSaveCategory}
              >
                保存
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* 标签管理对话框 */}
      {tagDialog.open && tagDialog.media && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="bg-white rounded-lg shadow-xl p-6 w-[500px] max-w-[90vw] max-h-[80vh] overflow-y-auto">
            <h3 className="text-lg font-semibold mb-4">管理标签</h3>
            <p className="text-sm text-gray-600 mb-4 truncate">
              {tagDialog.media.original_filename}
            </p>

            {/* 当前标签列表 */}
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                当前标签
              </label>
              <div className="flex flex-wrap gap-2 min-h-[40px] p-2 border border-gray-200 rounded-md bg-gray-50">
                {currentTags.length === 0 ? (
                  <span className="text-sm text-gray-400">暂无标签</span>
                ) : (
                  currentTags.map((tag, idx) => (
                    <Badge key={idx} variant="secondary" className="gap-1">
                      {tag}
                      <button
                        onClick={() => handleRemoveTag(tag)}
                        className="hover:text-red-500"
                      >
                        <X className="w-3 h-3" />
                      </button>
                    </Badge>
                  ))
                )}
              </div>
            </div>

            {/* 添加新标签 */}
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                添加标签 {currentTags.length >= 5 && <span className="text-red-500 text-xs">(已达上限)</span>}
              </label>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={newTag}
                  onChange={(e) => setNewTag(e.target.value)}
                  placeholder={currentTags.length >= 5 ? "已达标签上限" : "输入标签名称"}
                  disabled={currentTags.length >= 5}
                  className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100 disabled:cursor-not-allowed"
                  onKeyPress={(e) => e.key === 'Enter' && handleAddTag()}
                />
                <Button onClick={handleAddTag} size="sm" disabled={currentTags.length >= 5}>
                  <Plus className="w-4 h-4 mr-1" />
                  添加
                </Button>
              </div>
              <p className="text-xs text-gray-500 mt-1">
                已添加 {currentTags.length}/5 个标签
              </p>
            </div>

            <div className="flex gap-2">
              <Button
                variant="outline"
                className="flex-1"
                onClick={() => setTagDialog({ open: false, media: null })}
              >
                取消
              </Button>
              <Button
                className="flex-1"
                onClick={handleSaveTags}
              >
                保存
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* 批量移动对话框 */}
      {moveDialog && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="bg-white rounded-lg shadow-xl p-6 w-96 max-w-[90vw]">
            <h3 className="text-lg font-semibold mb-4">移动到文件夹</h3>
            <p className="text-sm text-gray-600 mb-4">
              已选择 {selectedItems.length} 个文件
            </p>
            
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                目标文件夹
              </label>
              <select
                value={targetFolderPath || ''}
                onChange={(e) => setTargetFolderPath(e.target.value === '' ? null : e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">根目录（无文件夹）</option>
                {folders.map(folder => (
                  <option key={folder.id} value={folder.path}>
                    {folder.path}
                  </option>
                ))}
              </select>
            </div>

            <div className="flex gap-2">
              <Button
                variant="outline"
                className="flex-1"
                onClick={() => setMoveDialog(false)}
              >
                取消
              </Button>
              <Button
                className="flex-1"
                onClick={handleBatchMove}
              >
                移动
              </Button>
            </div>
          </div>
        </div>
      )}
    </>
  );
};

export default MediaGrid;