import React, {useState, useRef, useMemo, useCallback, useEffect, Suspense} from 'react';
import {useQuery, useMutation, useQueryClient} from '@tanstack/react-query';
import {apiClient} from '@/lib/api/base-client';
import {MEDIA} from '@/lib/api/api-paths';
import {DASHBOARD} from '@/lib/api/api-paths';
import {useDebounce} from '@/lib/hooks';
import {StatCard} from '@/components/admin/shared-ui';
import {formatBytes} from '@/lib/utils';
import {
  ArrowUp, ArrowDown, CheckCircle2, ChevronLeft, ChevronRight, Edit3, FileText,
  Grid, HardDrive, Image, List, Music, Search, Square, CheckSquare, Tag, Trash2,
  Upload, Video, X, File
} from 'lucide-react';
const AdminMediaPreview = React.lazy(() => import('./AdminMediaPreview'));
import {
  MediaSkeletonGrid, MediaSkeletonList, MediaGridCard, MediaListRow,
  BatchActionBar, MoveDialog, Pagination, DeleteConfirm
} from './MediaUI';
import {type MediaFileItem, type FolderItem, getFileType, TYPE_OPTIONS, type TabKey} from './MediaTypes';
import ImageEditorModal from './ImageEditorModal';

export function FilesTab() {
  const qc = useQueryClient();
  const [page, setPage] = useState(1);
  const [fileType, setFileType] = useState('');
  const [sortBy, setSortBy] = useState('time');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [searchInput, setSearchInput] = useState('');
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [deleteTarget, setDeleteTarget] = useState<MediaFileItem | null>(null);
  const [previewFile, setPreviewFile] = useState<MediaFileItem | null>(null);
  const [editFile, setEditFile] = useState<MediaFileItem | null>(null);
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [showMoveDialog, setShowMoveDialog] = useState(false);
  const [batchDeleteConfirm, setBatchDeleteConfirm] = useState(false);
  const [batchTagOpen, setBatchTagOpen] = useState(false);
  const [batchCatOpen, setBatchCatOpen] = useState(false);
  const debouncedSearch = useDebounce(searchInput, 400);

  // 重置到第一页
  const prevFilters = useRef('');
  useEffect(() => {
    const filters = `${fileType}-${sortBy}-${sortOrder}-${debouncedSearch}`;
    if (prevFilters.current && prevFilters.current !== filters) setPage(1);
    prevFilters.current = filters;
  }, [fileType, sortBy, sortOrder, debouncedSearch]);

  // 选择时清除已删除的文件
  useEffect(() => {
    setSelectedIds(new Set());
  }, [page, fileType, debouncedSearch]);

  const {data, isLoading} = useQuery({
    queryKey: ['admin-media', page, fileType, sortBy, sortOrder, debouncedSearch],
    queryFn: async () => {
      const params: Record<string, string | number> = {page, per_page: 24};
      if (fileType) params.type = fileType;
      if (sortBy) params.sort = sortBy;
      if (sortOrder) params.order = sortOrder;
      if (debouncedSearch) params.q = debouncedSearch;

      const res = await apiClient.get(DASHBOARD.MEDIA_MGMT_FILES, params);
      if (!res.success || !res.data) return {files: [] as MediaFileItem[], total: 0, totalPages: 1};

      const files = (Array.isArray(res.data.files) ? res.data.files :
          Array.isArray(res.data.media_items) ? res.data.media_items :
            Array.isArray(res.data) ? res.data : []) as MediaFileItem[];
      const pagination = res.pagination;
      const total = pagination?.total || files.length;
      const totalPages = pagination?.total_pages || Math.ceil(total / 24) || 1;

      return {files, total, totalPages};
    },
  });

  const files = data?.files || [];
  const totalPages = data?.totalPages || 1;
  const total = data?.total || 0;

  // 获取文件夹列表
  const {data: folders = []} = useQuery({
    queryKey: ['admin-media-folders'],
    queryFn: async () => {
      const res = await apiClient.get(MEDIA.FOLDERS_LIST);
      return (res.data || []) as FolderItem[];
    },
  });

  const delMut = useMutation({
    mutationFn: (id: number) => apiClient.delete(MEDIA.DETAIL(id)),
    onSuccess: () => {
      qc.invalidateQueries({queryKey: ['admin-media']});
      setDeleteTarget(null);
    },
  });

  const batchDelMut = useMutation({
    mutationFn: (ids: number[]) => apiClient.post(MEDIA.BATCH_DELETE, {media_ids: ids}),
    onSuccess: () => {
      qc.invalidateQueries({queryKey: ['admin-media']});
      setSelectedIds(new Set());
      setBatchDeleteConfirm(false);
    },
  });

  const moveMut = useMutation({
    mutationFn: ({ids, folderPath}: { ids: number[]; folderPath: string | null }) =>
      apiClient.post('/media/folders/move-media', {media_ids: ids, folder_path: folderPath}),
    onSuccess: () => {
      qc.invalidateQueries({queryKey: ['admin-media']});
      setSelectedIds(new Set());
      setShowMoveDialog(false);
    },
  });

  const batchTagMut = useMutation({
    mutationFn: ({mediaIds, tags}: { mediaIds: number[]; tags: string[] }) =>
      apiClient.post(MEDIA.BATCH_TAGS, {media_ids: mediaIds, mode: 'replace', tags}),
    onSuccess: () => {
      qc.invalidateQueries({queryKey: ['admin-media']});
      setSelectedIds(new Set());
      setBatchTagOpen(false);
    },
  });

  const batchCatMut = useMutation({
    mutationFn: ({mediaIds, category}: { mediaIds: number[]; category: string }) =>
      apiClient.post(MEDIA.BATCH_CATEGORIZE, {media_ids: mediaIds, category}),
    onSuccess: () => {
      qc.invalidateQueries({queryKey: ['admin-media']});
      setSelectedIds(new Set());
      setBatchCatOpen(false);
    },
  });

  // 统计
  const stats = useMemo(() => {
    const images = files.filter((f) => f.mime_type?.startsWith('image/')).length;
    const videos = files.filter((f) => f.mime_type?.startsWith('video/')).length;
    const audio = files.filter((f) => f.mime_type?.startsWith('audio/')).length;
    const totalSize = files.reduce((sum, f) => sum + (f.file_size || 0), 0);
    return {images, videos, audio, totalSize};
  }, [files]);

  const toggleSelect = useCallback((id: number) => {
    setSelectedIds(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  const toggleSelectAll = useCallback(() => {
    if (selectedIds.size === files.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(files.map(f => f.id)));
    }
  }, [files, selectedIds.size]);

  return (
    <>
        {/* 统计卡片 */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          <StatCard icon={HardDrive} label="总文件数" value={total}
                    gradient="from-blue-500 to-blue-600"/>
          <StatCard icon={Image} label="图片" value={stats.images}
                    gradient="from-emerald-500 to-emerald-600"/>
          <StatCard icon={Video} label="视频" value={stats.videos}
                    gradient="from-purple-500 to-purple-600"/>
          <StatCard icon={File} label="总大小" value={formatBytes(stats.totalSize)}
                    gradient="from-amber-500 to-amber-600"/>
        </div>

        {/* 工具栏 */}
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 mb-4">
          {/* 搜索 */}
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400"/>
            <input type="text" value={searchInput} onChange={e => setSearchInput(e.target.value)}
                   placeholder="搜索文件名..."
                   className="w-full pl-10 pr-8 py-2.5 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white transition-all"/>
            {searchInput && (
                <button onClick={() => setSearchInput('')}
                        className="absolute right-2.5 top-1/2 -translate-y-1/2 p-0.5 text-gray-400 hover:text-gray-600">
                  <X className="w-4 h-4"/>
                </button>
            )}
          </div>

          {/* 全选 */}
          {files.length > 0 && (
            <button onClick={toggleSelectAll}
                    className={`flex items-center gap-1.5 px-3 py-2.5 rounded-xl text-xs font-medium transition-colors border ${
                      selectedIds.size === files.length && files.length > 0
                        ? 'bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-400 border-blue-200 dark:border-blue-800'
                        : 'bg-white dark:bg-gray-900 border-gray-200 dark:border-gray-700 text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800'
                    }`}>
              <CheckSquare className="w-3.5 h-3.5"/>
              {selectedIds.size === files.length && files.length > 0 ? '取消全选' : '全选'}
            </button>
          )}

          {/* 类型筛选 */}
          <div
            className="flex items-center gap-1 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-xl p-1 overflow-x-auto">
            {TYPE_OPTIONS.map(opt => (
                <button key={opt.value} onClick={() => setFileType(opt.value)}
                        className={`flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors whitespace-nowrap ${
                            fileType === opt.value
                                ? 'bg-blue-600 text-white shadow-sm'
                                : 'text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800'
                        }`}>
                  <opt.icon className="w-3.5 h-3.5"/>
                  {opt.label}
                </button>
            ))}
          </div>

          {/* 排序 */}
          <div
            className="flex items-center gap-1 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-xl p-1">
            <button onClick={() => {
              setSortBy('time');
              setSortOrder(o => o === 'asc' ? 'desc' : 'asc');
            }}
                    className={`flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                      sortBy === 'time' ? 'bg-gray-200 dark:bg-gray-700 text-gray-900 dark:text-white' : 'text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800'
                    }`}>
              时间 {sortBy === 'time' && (sortOrder === 'asc' ? <ArrowUp className="w-3 h-3"/> :
              <ArrowDown className="w-3 h-3"/>)}
            </button>
            <button onClick={() => {
              setSortBy('name');
              setSortOrder(o => o === 'asc' ? 'desc' : 'asc');
            }}
                    className={`flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                      sortBy === 'name' ? 'bg-gray-200 dark:bg-gray-700 text-gray-900 dark:text-white' : 'text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800'
                    }`}>
              名称 {sortBy === 'name' && (sortOrder === 'asc' ? <ArrowUp className="w-3 h-3"/> :
              <ArrowDown className="w-3 h-3"/>)}
            </button>
          </div>

          {/* 视图切换 */}
          <div
            className="flex items-center gap-1 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-xl p-1">
            <button onClick={() => setViewMode('grid')}
                    className={`p-2 rounded-lg transition-colors ${viewMode === 'grid' ? 'bg-gray-200 dark:bg-gray-700 text-gray-900 dark:text-white' : 'text-gray-400 hover:text-gray-600'}`}>
              <Grid className="w-4 h-4"/>
            </button>
            <button onClick={() => setViewMode('list')}
                    className={`p-2 rounded-lg transition-colors ${viewMode === 'list' ? 'bg-gray-200 dark:bg-gray-700 text-gray-900 dark:text-white' : 'text-gray-400 hover:text-gray-600'}`}>
              <List className="w-4 h-4"/>
            </button>
          </div>
        </div>

        {/* 媒体列表 */}
        {isLoading ? (
            viewMode === 'grid' ? <MediaSkeletonGrid/> : <MediaSkeletonList/>
        ) : files.length === 0 ? (
          <div
            className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-100 dark:border-gray-800 p-16 text-center">
            <div
              className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-gray-100 dark:bg-gray-800 flex items-center justify-center">
                <Image className="w-8 h-8 text-gray-300 dark:text-gray-600"/>
              </div>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
                {debouncedSearch ? '未找到匹配的文件' : '暂无媒体文件'}
              </h3>
            <p className="text-sm text-gray-500 dark:text-gray-400 mb-6">
                {debouncedSearch ? '尝试使用不同的搜索词' : '上传你的第一个文件'}
              </p>
              {!debouncedSearch && (
                <button
                  className="inline-flex items-center gap-1.5 px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-xl transition-colors">
                    <Upload className="w-4 h-4"/>上传文件
                  </button>
              )}
            </div>
        ) : viewMode === 'grid' ? (
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4">
              {files.map((f) => (
                <MediaGridCard key={f.id} file={f} selected={selectedIds.has(f.id)}
                               onSelect={toggleSelect} onDelete={setDeleteTarget} onPreview={setPreviewFile}/>
              ))}
            </div>
        ) : (
          <div
            className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-100 dark:border-gray-800 overflow-hidden">
              <div className="divide-y divide-gray-50 dark:divide-gray-800/50">
                {files.map((f) => (
                  <MediaListRow key={f.id} file={f} selected={selectedIds.has(f.id)}
                                onSelect={toggleSelect} onDelete={setDeleteTarget} onPreview={setPreviewFile}/>
                ))}
              </div>
          </div>
        )}

        {/* 分页 */}
      <Pagination page={page} totalPages={totalPages} total={total} onPageChange={setPage}/>

        {/* 全类型预览 */}
        {previewFile && (
          <Suspense fallback={
            <div className="w-full h-64 flex items-center justify-center">
              <div className="w-8 h-8 border-2 border-blue-600/30 border-t-blue-600 rounded-full animate-spin" />
            </div>
          }>
            <AdminMediaPreview
              files={files}
              activeFile={previewFile}
              onClose={() => setPreviewFile(null)}
              onNavigate={setPreviewFile}
              onEdit={(f) => { setPreviewFile(null); setEditFile(f); }}
            />
          </Suspense>
        )}

        {/* 图片编辑器 */}
        {editFile && (
          <ImageEditorModal mediaId={editFile.id} filename={editFile.original_filename || editFile.filename || ''}
                            onClose={() => setEditFile(null)} onSaved={() => { setEditFile(null); qc.invalidateQueries({queryKey: ['media-files']}); }}/>
        )}

      {/* 单文件删除确认 */}
        {deleteTarget && (
          <DeleteConfirm title="确认删除文件"
                         message={`确定要删除 <strong>${deleteTarget.original_filename}</strong> 吗？`}
                         onConfirm={() => delMut.mutate(deleteTarget.id)}
                         onCancel={() => setDeleteTarget(null)}
                         isPending={delMut.isPending}/>
        )}

      {/* 批量删除确认 */}
      {batchDeleteConfirm && (
        <DeleteConfirm title="批量删除文件"
                       message={`确定要删除选中的 <strong>${selectedIds.size}</strong> 个文件吗？`}
                       onConfirm={() => batchDelMut.mutate(Array.from(selectedIds))}
                       onCancel={() => setBatchDeleteConfirm(false)}
                       isPending={batchDelMut.isPending}/>
      )}

      {/* 移动到文件夹 */}
      <MoveDialog open={showMoveDialog} folders={folders} fileCount={selectedIds.size}
                  onMove={(path) => moveMut.mutate({ids: Array.from(selectedIds), folderPath: path})}
                  onClose={() => setShowMoveDialog(false)} isPending={moveMut.isPending}/>

      {/* 批量标签对话框 */}
      {batchTagOpen && <BatchSimpleTagDialog open={batchTagOpen} onClose={() => setBatchTagOpen(false)}
        onSave={async (tags) => { await batchTagMut.mutateAsync({mediaIds: Array.from(selectedIds), tags}); }}
        saving={batchTagMut.isPending} />}

      {/* 批量分类对话框 */}
      {batchCatOpen && <BatchSimpleCategoryDialog open={batchCatOpen} onClose={() => setBatchCatOpen(false)}
        onSave={async (category) => { await batchCatMut.mutateAsync({mediaIds: Array.from(selectedIds), category}); }}
        saving={batchCatMut.isPending} />}

      {/* 批量操作栏 */}
      {selectedIds.size > 0 && (
        <BatchActionBar count={selectedIds.size}
                        onDelete={() => setBatchDeleteConfirm(true)}
                        onMove={() => setShowMoveDialog(true)}
                        onBatchTag={() => setBatchTagOpen(true)}
                        onBatchCategory={() => setBatchCatOpen(true)}
                        onClear={() => setSelectedIds(new Set())}/>
      )}
    </>
  );
}

/* ── 批量标签对话框（内联组件） ── */
function BatchSimpleTagDialog({open, onClose, onSave, saving}: {
  open: boolean; onClose: () => void;
  onSave: (tags: string[]) => Promise<void>; saving: boolean;
}) {
  const [tags, setTags] = useState<string[]>([]);
  const [input, setInput] = useState('');
  if (!open) return null;
  const addTag = () => { const t = input.trim(); if (t && !tags.includes(t)) setTags([...tags, t]); setInput(''); };
  return (
    <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="bg-white dark:bg-gray-900 rounded-2xl p-6 max-w-sm w-full shadow-xl" onClick={e=>e.stopPropagation()}>
        <h3 className="text-lg font-bold mb-1">批量设置标签</h3>
        <p className="text-xs text-gray-400 mb-4">将替换所有选中文件的标签（最多 5 个）</p>
        <div className="flex gap-2 mb-3">
          <input value={input} onChange={e=>setInput(e.target.value)} onKeyDown={e=>{if(e.key==='Enter')addTag()}}
            placeholder="输入标签" maxLength={30}
            className="flex-1 px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-xl bg-gray-50 dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500 dark:text-white"/>
          <button onClick={addTag} disabled={tags.length>=5} className="px-3 py-2 bg-purple-600 text-white text-sm rounded-xl hover:bg-purple-700 disabled:opacity-40">添加</button>
        </div>
        <div className="flex flex-wrap gap-1.5 mb-5 min-h-[28px] p-2 border border-dashed border-gray-200 dark:border-gray-700 rounded-xl bg-gray-50/50 dark:bg-gray-800/50">
          {tags.length === 0 && <span className="text-xs text-gray-400">尚未添加标签</span>}
          {tags.map(t => (
            <span key={t} className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300 text-xs">
              {t}<button onClick={()=>setTags(tags.filter(x=>x!==t))} className="hover:text-red-500">&times;</button>
            </span>
          ))}
        </div>
        <div className="flex justify-end gap-3">
          <button onClick={onClose} className="px-4 py-2 bg-gray-100 dark:bg-gray-800 rounded-lg text-sm font-medium">取消</button>
          <button onClick={()=>onSave(tags)} disabled={saving} className="px-4 py-2 bg-purple-600 text-white rounded-lg text-sm font-medium hover:bg-purple-700 disabled:opacity-50">
            {saving ? '保存中...' : '保存'}
          </button>
        </div>
      </div>
    </div>
  );
}

/* ── 批量分类对话框（内联组件） ── */
function BatchSimpleCategoryDialog({open, onClose, onSave, saving}: {
  open: boolean; onClose: () => void;
  onSave: (category: string) => Promise<void>; saving: boolean;
}) {
  const [cat, setCat] = useState('');
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="bg-white dark:bg-gray-900 rounded-2xl p-6 max-w-sm w-full shadow-xl" onClick={e=>e.stopPropagation()}>
        <h3 className="text-lg font-bold mb-1">批量设置分类</h3>
        <p className="text-xs text-gray-400 mb-4">为所有选中的文件设置统一分类</p>
        <input value={cat} onChange={e=>setCat(e.target.value)} placeholder="输入分类名称" maxLength={50}
          className="w-full px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-xl bg-gray-50 dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 dark:text-white mb-4"/>
        <div className="flex justify-end gap-3">
          <button onClick={onClose} className="px-4 py-2 bg-gray-100 dark:bg-gray-800 rounded-lg text-sm font-medium">取消</button>
          <button onClick={()=>cat.trim() && onSave(cat.trim())} disabled={saving || !cat.trim()}
            className="px-4 py-2 bg-emerald-600 text-white rounded-lg text-sm font-medium hover:bg-emerald-700 disabled:opacity-50">
            {saving ? '保存中...' : '保存'}
          </button>
        </div>
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════
   ── 下载任务 Tab ──
   ═══════════════════════════════════════════════════════════════════ */
