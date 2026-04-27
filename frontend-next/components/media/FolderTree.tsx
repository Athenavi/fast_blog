'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Droppable } from '@hello-pangea/dnd';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import {
  Folder,
  FolderOpen,
  FolderPlus,
  MoreVertical,
  Edit,
  Trash2,
  ChevronRight,
  ChevronDown,
  FileImage
} from 'lucide-react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';

interface FolderNode {
  id: number;
  name: string;
  parent_id: number | null;
  description?: string;
  media_count?: number;
  children?: FolderNode[];
  created_at?: string;
  updated_at?: string;
}

interface FolderTreeProps {
  apiBaseUrl: string;
  apiPrefix: string;
  selectedFolderName: string | null;
  onFolderSelect: (folderName: string | null) => void;
  onRefresh?: () => void;
  onDropMedia?: (folderPath: string | null) => void;
}

const FolderTree: React.FC<FolderTreeProps> = ({
  apiBaseUrl,
  apiPrefix,
  selectedFolderName,
  onFolderSelect,
  onRefresh,
  onDropMedia
}) => {
  const router = useRouter();
  const [folders, setFolders] = useState<FolderNode[]>([]);
  const [expandedFolders, setExpandedFolders] = useState<Set<number>>(new Set());
  const [isLoading, setIsLoading] = useState(true);
  const [hasRedirected, setHasRedirected] = useState(false); // 防止重复重定向

  // 对话框状态
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [newFolderName, setNewFolderName] = useState('');
  const [editingFolder, setEditingFolder] = useState<FolderNode | null>(null);
  const [deletingFolder, setDeletingFolder] = useState<FolderNode | null>(null);
  const [parentFolderId, setParentFolderId] = useState<number | null>(null);

  // 验证文件夹名称
  const validateFolderName = (name: string): string | null => {
    if (!name || !name.trim()) {
      return '文件夹名称不能为空';
    }
    
    name = name.trim();
    
    // 检查长度
    if (name.length > 255) {
      return '文件夹名称不能超过255个字符';
    }
    
    // 禁止路径穿越攻击字符
    if (name.includes('..')) {
      return "文件夹名称不能包含 '..'";
    }
    
    if (name.includes('/') || name.includes('\\')) {
      return '文件夹名称不能包含路径分隔符 (/ 或 \\)';
    }
    
    // 禁止其他危险字符
    const dangerousChars = ['<', '>', ':', '"', '|', '?', '*'];
    for (const char of dangerousChars) {
      if (name.includes(char)) {
        return `文件夹名称不能包含特殊字符: ${char}`;
      }
    }
    
    // 只允许字母、数字、中文、下划线、连字符、空格、点
    const validPattern = /^[a-zA-Z0-9\u4e00-\u9fa5_\-\.\s]+$/;
    if (!validPattern.test(name)) {
      return '文件夹名称只能包含字母、数字、中文、下划线、连字符、空格和点';
    }
    
    // 不能以点开头（避免隐藏文件夹）
    if (name.startsWith('.')) {
      return '文件夹名称不能以点开头';
    }
    
    // 不能以空格开头或结尾
    if (name !== name.trim()) {
      return '文件夹名称不能以空格开头或结尾';
    }
    
    return null; // 验证通过
  };

  // 构建文件夹的完整路径（从根到当前文件夹）
  const buildFolderPath = (folderId: number, folderList: FolderNode[]): string | null => {
    const path: string[] = [];
    let currentId: number | null = folderId;
    
    console.log('🔍 buildFolderPath 开始:', { folderId, totalFolders: folderList.length });
    
    // 最多遍历 100 层，防止无限循环
    let depth = 0;
    while (currentId !== null && depth < 100) {
      // 查找当前 ID 对应的文件夹
      const findFolder = (nodes: FolderNode[]): FolderNode | null => {
        for (const node of nodes) {
          if (node.id === currentId) return node;
          if (node.children) {
            const found = findFolder(node.children);
            if (found) return found;
          }
        }
        return null;
      };
      
      const folder = findFolder(folderList);
      if (!folder) {
        console.warn('⚠️ 未找到文件夹:', currentId);
        return null;
      }
      
      path.unshift(folder.name);
      console.log(`  - 层级 ${depth}: ${folder.name} (parent_id: ${folder.parent_id})`);
      currentId = folder.parent_id;
      depth++;
    }
    
    const result = path.length > 0 ? path.join('/') : null;
    console.log('✅ buildFolderPath 结果:', result);
    return result;
  };

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
    const headers: HeadersInit = { 'Content-Type': 'application/json' };

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

  // 加载文件夹树
  const loadFolders = async () => {
    try {
      setIsLoading(true);
      console.log('📂 开始加载文件夹树...');
      
      const response = await fetch(
        `${apiBaseUrl}${apiPrefix}/media/folders/tree`,
        { headers: getAuthHeaders() }
      );

      console.log('📥 文件夹树响应状态:', response.status);

      if (response.ok) {
        const data = await response.json();
        console.log('📊 文件夹树响应数据:', data);
        
        if (data.success) {
          const treeData = data.data.tree || [];
          console.log('✅ 文件夹树加载成功，共', treeData.length, '个根文件夹');
          setFolders(treeData);
        } else {
          console.error('❌ 加载失败:', data.error);
          setFolders([]);
        }
      } else {
        console.error('❌ HTTP 错误:', response.status, response.statusText);
        if (response.status === 401) {
          console.error('⚠️ 未授权，请重新登录');
        }
        setFolders([]);
      }
    } catch (error) {
      console.error('❌ 加载文件夹异常:', error);
      setFolders([]);
    } finally {
      setIsLoading(false);
      console.log('🏁 文件夹加载完成');
    }
  };

  useEffect(() => {
    loadFolders();
  }, [apiBaseUrl, apiPrefix]);

  // 切换文件夹展开/折叠
  const toggleExpand = (folderId: number) => {
    const newExpanded = new Set(expandedFolders);
    if (newExpanded.has(folderId)) {
      newExpanded.delete(folderId);
    } else {
      newExpanded.add(folderId);
    }
    setExpandedFolders(newExpanded);
  };

  // 创建文件夹
  const handleCreateFolder = async () => {
    if (!newFolderName.trim()) {
      alert('请输入文件夹名称');
      return;
    }

    // 验证文件夹名称
    const validationError = validateFolderName(newFolderName);
    if (validationError) {
      alert(validationError);
      return;
    }

    try {
      console.log('📤 创建文件夹请求:', {
        name: newFolderName.trim(),
        parent_id: parentFolderId
      });
      
      const response = await fetch(
        `${apiBaseUrl}${apiPrefix}/media/folders/`,
        {
          method: 'POST',
          headers: getAuthHeaders(),
          body: JSON.stringify({
            name: newFolderName.trim(),
            parent_id: parentFolderId
          })
        }
      );

      console.log('📥 创建文件夹响应状态:', response.status);

      if (response.ok) {
        const data = await response.json();
        console.log('📊 创建文件夹响应数据:', data);
        
        if (data.success) {
          console.log('✅ 文件夹创建成功');
          setCreateDialogOpen(false);
          setNewFolderName('');
          setParentFolderId(null);
          
          // 重新加载文件夹树
          console.log('🔄 重新加载文件夹树...');
          await loadFolders();
          
          // 刷新媒体列表
          console.log('🔄 刷新媒体列表...');
          onRefresh?.();
        } else {
          console.error('❌ 创建失败:', data.error);
          alert(`创建失败: ${data.error}`);
        }
      } else {
        console.error('❌ HTTP 错误:', response.status, response.statusText);
        alert('创建失败，请重试');
      }
    } catch (error) {
      console.error('❌ 创建文件夹异常:', error);
      alert('创建失败');
    }
  };

  // 更新文件夹
  const handleUpdateFolder = async () => {
    if (!editingFolder || !newFolderName.trim()) return;

    // 验证文件夹名称
    const validationError = validateFolderName(newFolderName);
    if (validationError) {
      alert(validationError);
      return;
    }

    try {
      const response = await fetch(
        `${apiBaseUrl}${apiPrefix}/media/folders/${editingFolder.id}`,
        {
          method: 'PUT',
          headers: getAuthHeaders(),
          body: JSON.stringify({
            name: newFolderName.trim()
          })
        }
      );

      if (response.ok) {
        console.log('✅ 文件夹更新成功');
        setEditDialogOpen(false);
        setEditingFolder(null);
        setNewFolderName('');
        
        // 重新加载文件夹树
        console.log('🔄 重新加载文件夹树...');
        await loadFolders();
        
        // 刷新媒体列表
        console.log('🔄 刷新媒体列表...');
        onRefresh?.();
      }
    } catch (error) {
      console.error('更新文件夹失败:', error);
      alert('更新失败');
    }
  };

  // 删除文件夹
  const handleDeleteFolder = async () => {
    if (!deletingFolder) return;

    try {
      const response = await fetch(
        `${apiBaseUrl}${apiPrefix}/media/folders/${deletingFolder.id}?delete_media=false`,
        {
          method: 'DELETE',
          headers: getAuthHeaders()
        }
      );

      if (response.ok) {
        const data = await response.json();
        if (data.success) {
          console.log('✅ 文件夹删除成功');
          setDeleteDialogOpen(false);
          setDeletingFolder(null);
          
          // 重新加载文件夹树
          console.log('🔄 重新加载文件夹树...');
          await loadFolders();
          
          // 刷新媒体列表
          console.log('🔄 刷新媒体列表...');
          onRefresh?.();
        } else {
          console.error('❌ 删除失败:', data.error);
          alert(`删除失败: ${data.error}`);
        }
      }
    } catch (error) {
      console.error('删除文件夹失败:', error);
      alert('删除失败');
    }
  };

  // 打开创建对话框
  const openCreateDialog = (parentId: number | null = null) => {
    console.log('📂 打开创建对话框:', { parentId });
    setParentFolderId(parentId);
    setNewFolderName('');
    setCreateDialogOpen(true);
  };

  // 打开编辑对话框
  const openEditDialog = (folder: FolderNode) => {
    setEditingFolder(folder);
    setNewFolderName(folder.name);
    setEditDialogOpen(true);
  };

  // 打开删除对话框
  const openDeleteDialog = (folder: FolderNode) => {
    setDeletingFolder(folder);
    setDeleteDialogOpen(true);
  };

  // 渲染文件夹节点
  const renderFolderNode = (folder: FolderNode, level: number = 0) => {
    const isExpanded = expandedFolders.has(folder.id);
    const hasChildren = folder.children && folder.children.length > 0;
    
    // 构建当前文件夹的完整路径
    const folderPath = buildFolderPath(folder.id, folders);
    const isSelected = selectedFolderName === folderPath;
    const droppableId = `folder-${folderPath}`;

    return (
      <div key={folder.id}>
        <Droppable droppableId={droppableId} type="MEDIA" isDropDisabled={!onDropMedia}>
          {(provided, snapshot) => {
            // 调试日志 - 只在状态变化时输出
            if (snapshot.isDraggingOver) {
              console.log('✅ 文件夹正在被拖拽覆盖:', {
                folderPath,
                droppableId,
                level,
                folderName: folder.name
              });
            }
            
            return (
            <div
              ref={provided.innerRef}
              {...provided.droppableProps}
              className={`group flex items-center justify-between px-3 py-2 rounded cursor-pointer transition-all min-h-[40px] relative ${
                isSelected ? 'bg-blue-50 dark:bg-blue-900/20 border-l-2 border-blue-500' : 'hover:bg-gray-100 dark:hover:bg-gray-800'
              } ${snapshot.isDraggingOver ? '!bg-blue-100 dark:!bg-blue-900/40 !border-2 !border-dashed !border-blue-500 !scale-[1.02] !z-10 shadow-lg' : ''}`}
              style={{ paddingLeft: `${level * 16 + 8}px`, zIndex: snapshot.isDraggingOver ? 100 : 1 }}
              onClick={() => onFolderSelect(folderPath)}
            >
              <div className="flex items-center flex-1 min-w-0">
                {hasChildren ? (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      toggleExpand(folder.id);
                    }}
                    className="mr-1 p-0.5 hover:bg-gray-200 dark:hover:bg-gray-700 rounded"
                  >
                    {isExpanded ? (
                      <ChevronDown className="w-4 h-4 text-gray-500" />
                    ) : (
                      <ChevronRight className="w-4 h-4 text-gray-500" />
                    )}
                  </button>
                ) : (
                  <span className="w-6" />
                )}
                
                {isExpanded ? (
                  <FolderOpen className="w-4 h-4 mr-2 text-blue-500 flex-shrink-0" />
                ) : (
                  <Folder className="w-4 h-4 mr-2 text-gray-500 flex-shrink-0" />
                )}
                
                <span className="text-sm truncate flex-1">{folder.name}</span>
                
                {folder.media_count !== undefined && folder.media_count > 0 && (
                  <span className="text-xs text-gray-500 ml-2 flex-shrink-0">
                    ({folder.media_count})
                  </span>
                )}
                
                {/* 拖拽时的提示文字 */}
                {snapshot.isDraggingOver && (
                  <span className="ml-2 text-xs text-blue-600 font-medium flex-shrink-0 animate-pulse">
                    ← 放置到这里
                  </span>
                )}
              </div>

              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-6 w-6 p-0 opacity-0 group-hover:opacity-100 hover:opacity-100 focus:opacity-100"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <MoreVertical className="w-4 h-4" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" onClick={(e) => e.stopPropagation()}>
                  <DropdownMenuItem onClick={(e) => {
                    e.stopPropagation();
                    openCreateDialog(folder.id);
                  }}>
                    <FolderPlus className="w-4 h-4 mr-2" />
                    新建子文件夹
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={(e) => {
                    e.stopPropagation();
                    openEditDialog(folder);
                  }}>
                    <Edit className="w-4 h-4 mr-2" />
                    重命名
                  </DropdownMenuItem>
                  <DropdownMenuItem
                    className="text-red-600"
                    onClick={(e) => {
                      e.stopPropagation();
                      openDeleteDialog(folder);
                    }}
                  >
                    <Trash2 className="w-4 h-4 mr-2" />
                    删除
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
            );
          }}
        </Droppable>

        {/* 递归渲染子文件夹 */}
        {isExpanded && hasChildren && (
          <div>
            {folder.children!.map(child => renderFolderNode(child, level + 1))}
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="border-r bg-white dark:bg-gray-900 h-full overflow-y-auto">
      {/* 头部 */}
      <div className="p-3 border-b flex items-center justify-between">
        <h3 className="font-semibold text-sm">文件夹</h3>
        <Button
          size="sm"
          variant="outline"
          onClick={() => openCreateDialog(null)}
          className="h-7 px-2"
        >
          <FolderPlus className="w-4 h-4" />
        </Button>
      </div>

      {/* 文件夹列表 */}
      <div className="p-2">
        {/* 根目录选项 - 也作为放置区域 */}
        <Droppable droppableId="folder-root" type="MEDIA" isDropDisabled={!onDropMedia}>
          {(provided, snapshot) => {
            // 调试日志
            if (snapshot.isDraggingOver) {
              console.log('📂 根目录正在被拖拽覆盖', 'droppableId: folder-root');
            }
            return (
            <div
              ref={provided.innerRef}
              {...provided.droppableProps}
              className={`flex items-center px-3 py-2 rounded cursor-pointer transition-all min-h-[40px] mb-1 ${
                selectedFolderName === null ? 'bg-blue-50 dark:bg-blue-900/20 border-l-2 border-blue-500' : 'hover:bg-gray-100 dark:hover:bg-gray-800'
              } ${snapshot.isDraggingOver ? 'bg-blue-100 dark:bg-blue-900/40 border-2 border-dashed border-blue-500 scale-[1.02]' : ''}`}
              onClick={() => onFolderSelect(null)}
            >
              <FileImage className="w-4 h-4 mr-2 text-gray-500" />
              <span className="text-sm">全部文件</span>
              {/* 拖拽时的提示文字 */}
              {snapshot.isDraggingOver && (
                <span className="ml-2 text-xs text-blue-600 font-medium animate-pulse">
                  ← 放置到这里
                </span>
              )}
            </div>
            );
          }}
        </Droppable>

        {/* 文件夹树 */}
        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
          </div>
        ) : folders.length === 0 ? (
          <div className="text-center py-8 text-gray-500 text-sm">
            <Folder className="w-8 h-8 mx-auto mb-2 opacity-30" />
            <p>暂无文件夹</p>
            <Button
              variant="link"
              size="sm"
              onClick={() => openCreateDialog(null)}
              className="mt-2"
            >
              创建第一个文件夹
            </Button>
          </div>
        ) : (
          <div className="space-y-0.5">
            {folders.map(folder => renderFolderNode(folder))}
          </div>
        )}
      </div>

      {/* 创建文件夹对话框 */}
      <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>新建文件夹</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            {parentFolderId && (
              <div className="text-sm text-gray-600 dark:text-gray-400">
                将在选中的文件夹内创建子文件夹
              </div>
            )}
            <div className="space-y-2">
              <Label>文件夹名称</Label>
              <Input
                value={newFolderName}
                onChange={(e) => setNewFolderName(e.target.value)}
                placeholder="输入文件夹名称"
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    handleCreateFolder();
                  }
                }}
                autoFocus
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCreateDialogOpen(false)}>
              取消
            </Button>
            <Button onClick={handleCreateFolder}>
              创建
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* 编辑文件夹对话框 */}
      <Dialog open={editDialogOpen} onOpenChange={setEditDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>重命名文件夹</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>文件夹名称</Label>
              <Input
                value={newFolderName}
                onChange={(e) => setNewFolderName(e.target.value)}
                placeholder="输入文件夹名称"
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    handleUpdateFolder();
                  }
                }}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditDialogOpen(false)}>
              取消
            </Button>
            <Button onClick={handleUpdateFolder}>
              保存
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* 删除确认对话框 */}
      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>删除文件夹</DialogTitle>
          </DialogHeader>
          <div className="py-4">
            <p className="text-sm text-gray-600 dark:text-gray-400">
              确定要删除文件夹 &ldquo;{deletingFolder?.name}&rdquo; 吗？
            </p>
            <p className="text-xs text-gray-500 mt-2">
              文件夹内的文件将被移动到根目录
            </p>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteDialogOpen(false)}>
              取消
            </Button>
            <Button variant="destructive" onClick={handleDeleteFolder}>
              删除
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default FolderTree;
