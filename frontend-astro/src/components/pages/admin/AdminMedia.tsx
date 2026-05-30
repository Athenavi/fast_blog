'use client';

import React, {useState, useRef, useEffect, useMemo} from 'react';
import {useQuery, useMutation, useQueryClient} from '@tanstack/react-query';
import {AuthGuard} from '@/components/AuthGuard';
import {QueryProvider} from '@/components/QueryProvider';
import {AdminShell} from '@/components/admin/AdminShell';
import {StatCard} from '@/components/admin/shared-ui';
import {apiClient} from '@/lib/api/base-client';
import {useDebounce} from '@/lib/hooks';
import {getFullMediaUrl, formatBytes} from '@/lib/utils';
import {
  ChevronLeft, ChevronRight, FileText, Image, Music, Search, Trash2, Video, X,
  Upload, Grid, List, Filter, MoreVertical, Download, Copy, Eye,
  HardDrive, File, ArrowUpDown, ArrowUp, ArrowDown, CheckCircle2, AlertTriangle
} from 'lucide-react';

function getFileType(mime: string): 'image' | 'video' | 'audio' | 'document' {
  if (mime?.startsWith('image/')) return 'image';
  if (mime?.startsWith('video/')) return 'video';
  if (mime?.startsWith('audio/')) return 'audio';
  return 'document';
}

function getFileColor(type: string) {
  switch (type) {
    case 'image':
      return {bg: 'bg-blue-50 dark:bg-blue-900/20', text: 'text-blue-600 dark:text-blue-400', dot: 'bg-blue-500'};
    case 'video':
      return {
        bg: 'bg-purple-50 dark:bg-purple-900/20',
        text: 'text-purple-600 dark:text-purple-400',
        dot: 'bg-purple-500'
      };
    case 'audio':
      return {bg: 'bg-amber-50 dark:bg-amber-900/20', text: 'text-amber-600 dark:text-amber-400', dot: 'bg-amber-500'};
    default:
      return {bg: 'bg-gray-50 dark:bg-gray-800', text: 'text-gray-600 dark:text-gray-400', dot: 'bg-gray-500'};
  }
}

/* ── 常量 ── */
const TYPE_OPTIONS = [
  {value: '', label: '全部', icon: Grid},
  {value: 'images', label: '图片', icon: Image},
  {value: 'videos', label: '视频', icon: Video},
  {value: 'documents', label: '文档', icon: FileText},
  {value: 'audio', label: '音频', icon: Music},
] as const;

/* ── 媒体骨架屏 ── */
const MediaSkeletonGrid = () => (
    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4">
      {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12].map(i => (
          <div key={i}
               className="animate-pulse rounded-2xl border border-gray-100 dark:border-gray-800 overflow-hidden">
            <div className="aspect-square bg-gray-200 dark:bg-gray-700"/>
            <div className="p-3 space-y-2">
              <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-3/4"/>
              <div className="h-2.5 bg-gray-200 dark:bg-gray-700 rounded w-1/2"/>
            </div>
          </div>
      ))}
    </div>
);

const MediaSkeletonList = () => (
    <div className="space-y-2">
      {[1, 2, 3, 4, 5, 6, 7, 8].map(i => (
          <div key={i}
               className="animate-pulse flex items-center gap-4 p-4 bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800">
            <div className="w-12 h-12 bg-gray-200 dark:bg-gray-700 rounded-xl"/>
            <div className="flex-1 space-y-2">
              <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-40"/>
              <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-24"/>
            </div>
            <div className="w-16 h-4 bg-gray-200 dark:bg-gray-700 rounded"/>
            <div className="w-12 h-4 bg-gray-200 dark:bg-gray-700 rounded"/>
          </div>
      ))}
    </div>
);

/* ── 媒体卡片（网格视图） ── */
const MediaGridCard: React.FC<{
  file: any;
  onDelete: (f: any) => void;
  onPreview: (f: any) => void;
}> = ({file, onDelete, onPreview}) => {
  const [showMenu, setShowMenu] = useState(false);
  const type = getFileType(file.mime_type || '');
  const color = getFileColor(type);
  const isImage = type === 'image';

  return (
      <div
          className="group relative bg-white dark:bg-gray-900 rounded-2xl border border-gray-100 dark:border-gray-800 hover:border-gray-200 dark:hover:border-gray-700 hover:shadow-lg transition-all duration-200 overflow-hidden">
        {/* 预览区域 */}
        <div className="relative aspect-square bg-gray-50 dark:bg-gray-800/50 overflow-hidden cursor-pointer"
             onClick={() => isImage && onPreview(file)}>
          {isImage && file.url ? (
              <img src={getFullMediaUrl(file.url)} alt={file.original_filename}
                   className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                   loading="lazy"/>
          ) : (
              <div className="w-full h-full flex items-center justify-center">
                {type === 'video' ? <Video className="w-12 h-12 text-gray-300 dark:text-gray-600"/> :
                    type === 'audio' ? <Music className="w-12 h-12 text-gray-300 dark:text-gray-600"/> :
                        <FileText className="w-12 h-12 text-gray-300 dark:text-gray-600"/>}
              </div>
          )}
          {/* 悬浮操作 */}
          <div
              className="absolute inset-0 bg-black/0 group-hover:bg-black/30 transition-colors flex items-center justify-center gap-2 opacity-0 group-hover:opacity-100">
            {isImage && (
                <button onClick={(e) => {
                  e.stopPropagation();
                  onPreview(file);
                }}
                        className="p-2 bg-white/90 rounded-xl hover:bg-white transition-colors shadow-lg">
                  <Eye className="w-4 h-4 text-gray-700"/>
                </button>
            )}
            <button onClick={(e) => {
              e.stopPropagation();
              onDelete(file);
            }}
                    className="p-2 bg-white/90 rounded-xl hover:bg-white transition-colors shadow-lg">
              <Trash2 className="w-4 h-4 text-red-600"/>
            </button>
          </div>
          {/* 类型标签 */}
          <div
              className={`absolute top-2 left-2 px-2 py-0.5 rounded-full text-[10px] font-medium ${color.bg} ${color.text} backdrop-blur-sm`}>
            {type === 'image' ? '图片' : type === 'video' ? '视频' : type === 'audio' ? '音频' : '文档'}
          </div>
        </div>
        {/* 信息 */}
        <div className="p-3">
          <p className="text-sm font-medium text-gray-900 dark:text-white truncate" title={file.original_filename}>
            {file.original_filename}
          </p>
          <p className="text-xs text-gray-400 mt-1">
            {file.file_size ? formatBytes(file.file_size) : '-'}
          </p>
        </div>
      </div>
  );
};

/* ── 媒体行（列表视图） ── */
const MediaListRow: React.FC<{
  file: any;
  onDelete: (f: any) => void;
  onPreview: (f: any) => void;
}> = ({file, onDelete, onPreview}) => {
  const [showMenu, setShowMenu] = useState(false);
  const type = getFileType(file.mime_type || '');
  const color = getFileColor(type);
  const isImage = type === 'image';

  return (
      <div
          className="group flex items-center gap-4 px-5 py-3 hover:bg-gray-50/80 dark:hover:bg-gray-800/30 transition-colors">
        {/* 缩略图 */}
        <div
            className={`w-12 h-12 rounded-xl overflow-hidden flex-shrink-0 cursor-pointer ${isImage ? '' : color.bg + ' flex items-center justify-center'}`}
            onClick={() => isImage && onPreview(file)}>
          {isImage && file.url ? (
              <img src={getFullMediaUrl(file.url)} alt="" className="w-full h-full object-cover" loading="lazy"/>
          ) : (
              <>
                {type === 'video' ? <Video className={`w-5 h-5 ${color.text}`}/> :
                    type === 'audio' ? <Music className={`w-5 h-5 ${color.text}`}/> :
                        <FileText className={`w-5 h-5 ${color.text}`}/>}
              </>
          )}
        </div>

        {/* 文件名 */}
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-gray-900 dark:text-white truncate">{file.original_filename}</p>
          <p className="text-xs text-gray-400">{file.mime_type || '未知类型'}</p>
        </div>

        {/* 大小 */}
        <span className="text-sm text-gray-500 hidden sm:block w-20 text-right">
        {file.file_size ? formatBytes(file.file_size) : '-'}
      </span>

        {/* 类型标签 */}
        <span
            className={`hidden md:inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium ${color.bg} ${color.text}`}>
        {type === 'image' ? '图片' : type === 'video' ? '视频' : type === 'audio' ? '音频' : '文档'}
      </span>

        {/* 操作 */}
        <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
          <button onClick={() => onPreview(file)}
                  className="p-1.5 rounded-lg text-gray-400 hover:text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-colors">
            <Eye className="w-4 h-4"/>
          </button>
          <button onClick={() => onDelete(file)}
                  className="p-1.5 rounded-lg text-gray-400 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors">
            <Trash2 className="w-4 h-4"/>
          </button>
        </div>
      </div>
  );
};

/* ── 图片预览弹窗 ── */
const ImagePreview: React.FC<{
  file: any;
  onClose: () => void;
}> = ({file, onClose}) => (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm" onClick={onClose}>
      <div className="relative max-w-4xl max-h-[90vh] p-4" onClick={e => e.stopPropagation()}>
        <img src={getFullMediaUrl(file.url)} alt={file.original_filename}
             className="max-w-full max-h-[80vh] object-contain rounded-2xl shadow-2xl"/>
        <div className="mt-3 flex items-center justify-between bg-white/10 backdrop-blur-md rounded-xl p-3">
          <div>
            <p className="text-white font-medium text-sm">{file.original_filename}</p>
            <p className="text-white/60 text-xs">{file.mime_type} · {file.file_size ? formatBytes(file.file_size) : '-'}</p>
          </div>
          <div className="flex items-center gap-2">
            <button onClick={() => {
              navigator.clipboard.writeText(getFullMediaUrl(file.url));
            }}
                    className="p-2 bg-white/10 hover:bg-white/20 rounded-lg text-white transition-colors">
              <Copy className="w-4 h-4"/>
            </button>
            <button onClick={onClose}
                    className="p-2 bg-white/10 hover:bg-white/20 rounded-lg text-white transition-colors">
              <X className="w-4 h-4"/>
            </button>
          </div>
        </div>
      </div>
    </div>
);

/* ── 删除确认弹窗 ── */
const DeleteConfirm: React.FC<{
  file: any;
  onConfirm: () => void;
  onCancel: () => void;
  isPending: boolean;
}> = ({file, onConfirm, onCancel, isPending}) => (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm"
         onClick={onCancel}>
      <div
          className="bg-white dark:bg-gray-900 rounded-2xl shadow-2xl border border-gray-200 dark:border-gray-700 w-full max-w-md p-6"
          onClick={e => e.stopPropagation()}>
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 rounded-full bg-red-100 dark:bg-red-900/30 flex items-center justify-center">
            <AlertTriangle className="w-5 h-5 text-red-600 dark:text-red-400"/>
          </div>
          <div>
            <h3 className="font-semibold text-gray-900 dark:text-white">确认删除文件</h3>
            <p className="text-sm text-gray-500">此操作不可撤销</p>
          </div>
        </div>
        <p className="text-sm text-gray-600 dark:text-gray-400 mb-6">
          确定要删除 <strong className="text-gray-900 dark:text-white">{file.original_filename}</strong> 吗？
        </p>
        <div className="flex justify-end gap-3">
          <button onClick={onCancel}
                  className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-xl transition-colors">
            取消
          </button>
          <button onClick={onConfirm} disabled={isPending}
                  className="px-4 py-2 text-sm font-medium bg-red-600 hover:bg-red-700 text-white rounded-xl transition-colors flex items-center gap-1.5 disabled:opacity-50">
            {isPending ? (
                <><span
                    className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"/>删除中...</>
            ) : (
                <><Trash2 className="w-4 h-4"/>删除</>
            )}
          </button>
        </div>
      </div>
    </div>
);

/* ── 主页面 ── */
function AdminMediaInner() {
  const qc = useQueryClient();
  const [page, setPage] = useState(1);
  const [fileType, setFileType] = useState('');
  const [sortBy, setSortBy] = useState('time');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [searchInput, setSearchInput] = useState('');
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [deleteTarget, setDeleteTarget] = useState<any>(null);
  const [previewFile, setPreviewFile] = useState<any>(null);
  const debouncedSearch = useDebounce(searchInput, 400);

  // 重置到第一页
  const prevFilters = useRef('');
  useEffect(() => {
    const filters = `${fileType}-${sortBy}-${sortOrder}-${debouncedSearch}`;
    if (prevFilters.current && prevFilters.current !== filters) setPage(1);
    prevFilters.current = filters;
  }, [fileType, sortBy, sortOrder, debouncedSearch]);

  const {data, isLoading} = useQuery({
    queryKey: ['admin-media', page, fileType, sortBy, sortOrder, debouncedSearch],
    queryFn: async () => {
      const params: Record<string, any> = {page, per_page: 24};
      if (fileType) params.type = fileType;
      if (sortBy) params.sort = sortBy;
      if (sortOrder) params.order = sortOrder;
      if (debouncedSearch) params.q = debouncedSearch;

      const res = await apiClient.get<any>('/api/v2/dashboard/media-management/files', params);
      if (!res.success || !res.data) return {files: [], total: 0, totalPages: 1};

      const files = Array.isArray(res.data.files) ? res.data.files :
          Array.isArray(res.data.media_items) ? res.data.media_items :
              Array.isArray(res.data) ? res.data : [];
      const pagination = res.pagination || {};
      const total = pagination.total || files.length;
      const totalPages = pagination.total_pages || Math.ceil(total / 24) || 1;

      return {files, total, totalPages};
    },
  });

  const files = data?.files || [];
  const totalPages = data?.totalPages || 1;
  const total = data?.total || 0;

  const delMut = useMutation({
    mutationFn: (id: number) => apiClient.delete(`/api/v2/dashboard/media-management/files/${id}`),
    onSuccess: () => {
      qc.invalidateQueries({queryKey: ['admin-media']});
      setDeleteTarget(null);
    },
  });

  // 统计
  const stats = useMemo(() => {
    const images = files.filter((f: any) => f.mime_type?.startsWith('image/')).length;
    const videos = files.filter((f: any) => f.mime_type?.startsWith('video/')).length;
    const audio = files.filter((f: any) => f.mime_type?.startsWith('audio/')).length;
    const totalSize = files.reduce((sum: number, f: any) => sum + (f.file_size || 0), 0);
    return {images, videos, audio, totalSize};
  }, [files]);

  // 分页
  const renderPagination = () => {
    if (totalPages <= 1) return null;
    const pages: (number | string)[] = [];
    const delta = 2;
    const left = Math.max(2, page - delta);
    const right = Math.min(totalPages - 1, page + delta);

    pages.push(1);
    if (left > 2) pages.push('...');
    for (let i = left; i <= right; i++) pages.push(i);
    if (right < totalPages - 1) pages.push('...');
    if (totalPages > 1) pages.push(totalPages);

    return (
        <div className="flex items-center justify-between mt-6 pt-4 border-t border-gray-100 dark:border-gray-800">
          <p className="text-xs text-gray-400">
            第 {page} / {totalPages} 页 · 共 {total} 个文件
          </p>
          <div className="flex items-center gap-1.5">
          <button disabled={page <= 1} onClick={() => setPage(p => p - 1)}
                  className="p-2 rounded-lg border border-gray-200 dark:border-gray-700 disabled:opacity-30 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors">
            <ChevronLeft className="w-4 h-4"/>
          </button>
          {pages.map((p, i) =>
              p === '...' ? (
                  <span key={`ellipsis-${i}`} className="px-2 text-gray-400">…</span>
              ) : (
                  <button key={p} onClick={() => setPage(p as number)}
                          className={`min-w-[36px] h-9 rounded-lg text-sm font-medium transition-colors ${
                              p === page
                                  ? 'bg-blue-600 text-white shadow-sm'
                                  : 'border border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800'
                          }`}>{p}</button>
              )
          )}
          <button disabled={page >= totalPages} onClick={() => setPage(p => p + 1)}
                  className="p-2 rounded-lg border border-gray-200 dark:border-gray-700 disabled:opacity-30 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors">
            <ChevronRight className="w-4 h-4"/>
          </button>
        </div>
        </div>
    );
  };

  return (
      <AdminShell title="媒体库" actions={
        <button
            className="flex items-center gap-1.5 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg transition-colors shadow-sm">
          <Upload className="w-4 h-4"/>上传文件
        </button>
      }>
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
                        sortBy === 'time' ? 'bg-gray-200 dark:bg-gray-700 text-gray-900 dark:text-white' : 'text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800'
                    }`}>
              时间 {sortBy === 'time' && (sortOrder === 'asc' ? <ArrowUp className="w-3 h-3"/> :
                <ArrowDown className="w-3 h-3"/>)}
            </button>
            <button onClick={() => {
              setSortBy('name');
              setSortOrder(o => o === 'asc' ? 'desc' : 'asc');
            }}
                    className={`flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                        sortBy === 'name' ? 'bg-gray-200 dark:bg-gray-700 text-gray-900 dark:text-white' : 'text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800'
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
              <p className="text-sm text-gray-500 mb-6">
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
              {files.map((f: any) => (
                  <MediaGridCard key={f.id} file={f} onDelete={setDeleteTarget} onPreview={setPreviewFile}/>
              ))}
            </div>
        ) : (
            <div
                className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-100 dark:border-gray-800 overflow-hidden">
              <div className="divide-y divide-gray-50 dark:divide-gray-800/50">
                {files.map((f: any) => (
                    <MediaListRow key={f.id} file={f} onDelete={setDeleteTarget} onPreview={setPreviewFile}/>
                ))}
              </div>
        </div>
        )}

        {/* 分页 */}
        {renderPagination()}

        {/* 图片预览 */}
        {previewFile && <ImagePreview file={previewFile} onClose={() => setPreviewFile(null)}/>}

        {/* 删除确认 */}
        {deleteTarget && (
            <DeleteConfirm
                file={deleteTarget}
                onConfirm={() => delMut.mutate(deleteTarget.id)}
                onCancel={() => setDeleteTarget(null)}
                isPending={delMut.isPending}
            />
        )}
      </AdminShell>
  );
}

export default function AdminMedia() {
  return <AuthGuard><QueryProvider><AdminMediaInner/></QueryProvider></AuthGuard>;
}
