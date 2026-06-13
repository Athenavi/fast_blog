'use client';

import React, {useState, useCallback} from 'react';
import {useQuery, useMutation, useQueryClient} from '@tanstack/react-query';
import {AuthGuard} from '@/components/AuthGuard';
import {QueryProvider} from '@/components/QueryProvider';
import {apiClient} from '@/lib/api/base-client';
import {MEDIA} from '@/lib/api/api-paths';
import {ToastProvider, useToast} from '@/components/ui/toast-provider';
import type {MediaFile} from '@/lib/api';
import type {FolderNode} from './FolderTree';
import {MediaGrid} from './MediaGrid';
import {PreviewModal, DeleteConfirm, MoveDialog, CreateFolderDialog} from './MediaDialogs';
import {UploadArea} from './UploadArea';
import {FolderTree} from './FolderTree';
import {StorageStats} from './StorageStats';
import {useMediaUpload} from './useMediaUpload';
import {Search, Upload, Grid3X3, List, Trash2, FolderOpen, Download, X} from 'lucide-react';

function MediaBrowserInner() {
  const toast = useToast();
  const qc = useQueryClient();

  // View state
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [search, setSearch] = useState('');
  const [typeFilter, setTypeFilter] = useState('');
  const [selectedFolder, setSelectedFolder] = useState<number | null>(null);

  // Selection & dialogs
  const [selected, setSelected] = useState<number[]>([]);
  const [previewMedia, setPreviewMedia] = useState<MediaFile | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<MediaFile | null>(null);
  const [moveDialogOpen, setMoveDialogOpen] = useState(false);
  const [createFolderOpen, setCreateFolderOpen] = useState(false);
  const [uploadCollapsed, setUploadCollapsed] = useState(true);

  // Upload
  const {uploading, uploadProgress, uploadStatus, uploadFiles} = useMediaUpload(() => {
    qc.invalidateQueries({queryKey: ['media-files']});
    qc.invalidateQueries({queryKey: ['media-stats']});
    toast.success('上传完成');
  });

  // ── Queries ──

  const mediaParams: Record<string, any> = {per_page: 100};
  if (search) mediaParams.q = search;
  if (typeFilter) mediaParams.media_type = typeFilter;
  if (selectedFolder != null) mediaParams.folder_id = selectedFolder;

  const {data: mediaData, isLoading: mediaLoading} = useQuery<MediaFile[]>({
    queryKey: ['media-files', search, typeFilter, selectedFolder],
    queryFn: async () => {
      const res = await apiClient.get(MEDIA.LIST, mediaParams);
      const raw = res.data?.data || res.data?.files || res.data || [];
      return Array.isArray(raw) ? raw : [];
    },
  });

  const {data: folders, isLoading: foldersLoading} = useQuery<FolderNode[]>({
    queryKey: ['media-folders'],
    queryFn: async () => {
      const res = await apiClient.get(MEDIA.FOLDERS_TREE);
      const raw = res.data?.folders || res.data?.data || res.data;
      return Array.isArray(raw) ? raw : [];
    },
  });

  const {data: statsData, isLoading: statsLoading} = useQuery({
    queryKey: ['media-stats'],
    queryFn: async () => {
      const res = await apiClient.get(MEDIA.LIST, {page: 1, per_page: 1});
      return res.data?.stats || {};
    },
  });

  const files: MediaFile[] = mediaData || [];
  const folderList: FolderNode[] = folders || [];

  // ── Mutations ──

  const deleteMut = useMutation({
    mutationFn: (file: MediaFile) => apiClient.post(MEDIA.BATCH_DELETE, {media_ids: [file.id]}),
    onSuccess: () => {
      qc.invalidateQueries({queryKey: ['media-files']});
      qc.invalidateQueries({queryKey: ['media-stats']});
      toast.success('已删除');
    },
    onError: () => toast.error('删除失败'),
  });

  const moveMut = useMutation({
    mutationFn: ({ids, folderPath}: {ids: number[]; folderPath: string | null}) =>
      apiClient.post(MEDIA.FOLDERS_MOVE, {media_ids: ids, folder_path: folderPath}),
    onSuccess: () => {
      qc.invalidateQueries({queryKey: ['media-files']});
      qc.invalidateQueries({queryKey: ['media-folders']});
      toast.success('移动成功');
      setMoveDialogOpen(false);
      setSelected([]);
    },
    onError: () => toast.error('移动失败'),
  });

  const createFolderMut = useMutation({
    mutationFn: (name: string) => apiClient.post(MEDIA.FOLDERS_CREATE, {name}),
    onSuccess: () => {
      qc.invalidateQueries({queryKey: ['media-folders']});
      toast.success('文件夹已创建');
      setCreateFolderOpen(false);
    },
    onError: () => toast.error('创建失败'),
  });

  const deleteFolderMut = useMutation({
    mutationFn: (id: number) => apiClient.delete(MEDIA.FOLDERS_DELETE(id)),
    onSuccess: () => {
      qc.invalidateQueries({queryKey: ['media-folders']});
      toast.success('文件夹已删除');
    },
    onError: () => toast.error('删除文件夹失败'),
  });

  // ── Handlers ──

  const handleSelect = useCallback((id: number) => {
    setSelected(prev =>
      prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id],
    );
  }, []);

  const handleDelete = useCallback((file: MediaFile) => {
    setDeleteTarget(file);
  }, []);

  const confirmDelete = useCallback(() => {
    if (deleteTarget) deleteMut.mutate(deleteTarget);
    setDeleteTarget(null);
  }, [deleteTarget, deleteMut]);

  const clearSelection = useCallback(() => setSelected([]), []);

  // ── Render ──

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50 dark:from-gray-950 dark:to-gray-900 pt-20">
      <div className="max-w-7xl mx-auto px-4 py-6 space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">媒体库</h1>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setViewMode('grid')}
              className={`p-2 rounded-lg transition-colors ${viewMode === 'grid' ? 'bg-blue-100 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400' : 'text-gray-400 hover:text-gray-600 dark:hover:text-gray-300'}`}
              title="网格视图"
            >
              <Grid3X3 className="w-4 h-4"/>
            </button>
            <button
              onClick={() => setViewMode('list')}
              className={`p-2 rounded-lg transition-colors ${viewMode === 'list' ? 'bg-blue-100 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400' : 'text-gray-400 hover:text-gray-600 dark:hover:text-gray-300'}`}
              title="列表视图"
            >
              <List className="w-4 h-4"/>
            </button>
            <button
              onClick={() => setUploadCollapsed(!uploadCollapsed)}
              className="inline-flex items-center gap-1.5 px-4 py-2 bg-blue-600 text-white text-sm rounded-xl hover:bg-blue-700 transition-colors"
            >
              <Upload className="w-4 h-4"/>
              {uploadCollapsed ? '上传' : '关闭'}
            </button>
          </div>
        </div>

        {/* Upload Area */}
        <UploadArea
          onUpload={uploadFiles}
          uploading={uploading}
          progress={uploadProgress}
          status={uploadStatus}
          collapsed={uploadCollapsed}
          onToggle={() => setUploadCollapsed(!uploadCollapsed)}
        />

        {/* Storage Stats */}
        <StorageStats stats={statsData || {}} loading={statsLoading}/>

        {/* Selection toolbar */}
        {selected.length > 0 && (
          <div className="flex items-center gap-3 px-4 py-3 bg-blue-50 dark:bg-blue-900/20 rounded-xl border border-blue-200 dark:border-blue-800 animate-in fade-in slide-in-from-top-2">
            <span className="text-sm font-medium text-blue-700 dark:text-blue-300">已选择 {selected.length} 项</span>
            <button
              onClick={() => setMoveDialogOpen(true)}
              className="inline-flex items-center gap-1 px-3 py-1.5 bg-white dark:bg-gray-800 text-sm rounded-lg border border-blue-200 dark:border-blue-700 hover:bg-blue-100 dark:hover:bg-blue-900/40 transition-colors"
            >
              <FolderOpen className="w-3.5 h-3.5"/> 移动
            </button>
            <button
              onClick={() => {
                const target = files.find(f => f.id === selected[0]);
                if (target) { setDeleteTarget(target); }
              }}
              className="inline-flex items-center gap-1 px-3 py-1.5 bg-white dark:bg-gray-800 text-sm rounded-lg border border-red-200 dark:border-red-700 text-red-600 hover:bg-red-50 dark:hover:bg-red-900/30 transition-colors"
              disabled={selected.length === 0}
            >
              <Trash2 className="w-3.5 h-3.5"/> 删除
            </button>
            <button onClick={clearSelection} className="ml-auto p-1.5 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors">
              <X className="w-4 h-4"/>
            </button>
          </div>
        )}

        {/* Filters + Folder sidebar */}
        <div className="flex gap-6">
          {/* Left sidebar — FolderTree */}
          <aside className="hidden lg:block w-56 flex-shrink-0">
            <div className="bg-white/60 dark:bg-gray-900/60 backdrop-blur-sm rounded-2xl border border-gray-200 dark:border-gray-700 p-4 sticky top-24">
              <FolderTree
                folders={folderList}
                selectedId={selectedFolder}
                onSelect={(f) => setSelectedFolder(f?.id ?? null)}
                onCreate={() => setCreateFolderOpen(true)}
                onDelete={(id) => deleteFolderMut.mutate(id)}
                loading={foldersLoading}
              />
            </div>
          </aside>

          {/* Main content */}
          <div className="flex-1 min-w-0 space-y-4">
            {/* Search & filters bar */}
            <div className="flex items-center gap-3 flex-wrap">
              <div className="relative flex-1 max-w-xs">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none"/>
                <input
                  value={search}
                  onChange={e => setSearch(e.target.value)}
                  placeholder="搜索媒体文件..."
                  className="w-full pl-10 pr-4 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl bg-white/60 dark:bg-gray-900/60 backdrop-blur-sm text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white transition-all"
                />
              </div>
              <select
                value={typeFilter}
                onChange={e => setTypeFilter(e.target.value)}
                className="px-3 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl bg-white/60 dark:bg-gray-900/60 backdrop-blur-sm text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white"
              >
                <option value="">全部类型</option>
                <option value="image">图片</option>
                <option value="video">视频</option>
                <option value="audio">音频</option>
                <option value="application">文档</option>
              </select>
            </div>

            {/* Mobile folder tree toggle */}
            <div className="lg:hidden">
              <details className="bg-white/60 dark:bg-gray-900/60 backdrop-blur-sm rounded-2xl border border-gray-200 dark:border-gray-700">
                <summary className="px-4 py-3 cursor-pointer text-sm font-medium text-gray-600 dark:text-gray-400 select-none">
                  文件夹
                </summary>
                <div className="px-4 pb-4">
                  <FolderTree
                    folders={folderList}
                    selectedId={selectedFolder}
                    onSelect={(f) => setSelectedFolder(f?.id ?? null)}
                    onCreate={() => setCreateFolderOpen(true)}
                    onDelete={(id) => deleteFolderMut.mutate(id)}
                    loading={foldersLoading}
                  />
                </div>
              </details>
            </div>

            {/* Media Grid */}
            <MediaGrid
              files={files}
              loading={mediaLoading}
              viewMode={viewMode}
              selected={selected}
              onSelect={handleSelect}
              onPreview={setPreviewMedia}
              onDelete={handleDelete}
            />
          </div>
        </div>

        {/* ── Dialogs ── */}

        {deleteTarget && (
          <DeleteConfirm
            item={deleteTarget}
            onCancel={() => setDeleteTarget(null)}
            onConfirm={confirmDelete}
          />
        )}

        {previewMedia && (
          <PreviewModal
            media={previewMedia}
            onClose={() => setPreviewMedia(null)}
          />
        )}

        <MoveDialog
          open={moveDialogOpen}
          onClose={() => setMoveDialogOpen(false)}
          folders={folderList}
          mediaCount={selected.length}
          onMove={(folderPath) => moveMut.mutate({ids: selected, folderPath})}
        />

        <CreateFolderDialog
          open={createFolderOpen}
          onClose={() => setCreateFolderOpen(false)}
          onCreate={(name) => createFolderMut.mutate(name)}
        />
      </div>
    </div>
  );
}

export default function MediaPage() {
  return (
    <AuthGuard>
      <QueryProvider>
        <ToastProvider>
          <MediaBrowserInner/>
        </ToastProvider>
      </QueryProvider>
    </AuthGuard>
  );
}
