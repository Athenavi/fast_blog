import React, {useState} from 'react';
import {
  AlertTriangle, ArrowUp, ArrowDown, CheckCircle2, ChevronLeft, ChevronRight,
  Clock, Copy, Download, Edit3, Eye, FileText, FolderOpen, Grid, Image, List, Music,
  Search, Square, CheckSquare, Tag, Trash2, Upload, Video, X
} from 'lucide-react';
import {getFullMediaUrl, formatBytes} from '@/lib/utils';
import {type MediaFileItem, type FolderItem, getFileColor, getFileType, type TabKey} from './MediaTypes';

export const MediaSkeletonGrid = () => (
    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4">
      {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12].map(i => (
        <div key={i} className="animate-pulse rounded-2xl border border-gray-100 dark:border-gray-800 overflow-hidden">
            <div className="aspect-square bg-gray-200 dark:bg-gray-700"/>
            <div className="p-3 space-y-2">
              <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-3/4"/>
              <div className="h-2.5 bg-gray-200 dark:bg-gray-700 rounded w-1/2"/>
            </div>
          </div>
      ))}
    </div>
);

export const MediaSkeletonList = () => (
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

export const TaskSkeleton = () => (
  <div className="space-y-3">
    {[1, 2, 3, 4, 5].map(i => (
      <div key={i}
           className="animate-pulse flex items-center gap-4 p-4 bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800">
        <div className="w-10 h-10 bg-gray-200 dark:bg-gray-700 rounded-xl"/>
        <div className="flex-1 space-y-2">
          <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-48"/>
          <div className="h-2 bg-gray-200 dark:bg-gray-700 rounded w-full"/>
        </div>
        <div className="w-20 h-6 bg-gray-200 dark:bg-gray-700 rounded-full"/>
      </div>
    ))}
  </div>
);

/* ── 媒体卡片（网格视图） ── */
export const MediaGridCard: React.FC<{
  file: MediaFileItem;
  selected: boolean;
  onSelect: (id: number) => void;
  onDelete: (f: MediaFileItem) => void;
  onPreview: (f: MediaFileItem) => void;
}> = ({file, selected, onSelect, onDelete, onPreview}) => {
  const type = getFileType(file.mime_type || '');
  const color = getFileColor(type);
  const isImage = type === 'image';

  return (
      <div
        className={`group relative bg-white dark:bg-gray-900 rounded-2xl border transition-all duration-200 overflow-hidden ${
          selected ? 'border-blue-400 dark:border-blue-500 ring-2 ring-blue-100 dark:ring-blue-900/30' : 'border-gray-100 dark:border-gray-800 hover:border-gray-200 dark:hover:border-gray-700 hover:shadow-lg'
        }`}>
        {/* 选择框 */}
        <button onClick={(e) => {
          e.stopPropagation();
          onSelect(file.id);
        }}
                className={`absolute top-2 right-2 z-10 w-6 h-6 rounded-lg border-2 flex items-center justify-center transition-all ${
                  selected
                    ? 'bg-blue-600 border-blue-600 text-white'
                    : 'bg-white/80 dark:bg-gray-800/80 border-gray-300 dark:border-gray-600 opacity-0 group-hover:opacity-100'
                }`}>
          {selected && <CheckSquare className="w-3.5 h-3.5"/>}
        </button>

        {/* 预览区域 */}
        <div className="relative aspect-square bg-gray-50 dark:bg-gray-800/50 overflow-hidden cursor-pointer"
             onClick={() => isImage && onPreview(file)}>
          {isImage && (file.thumbnail_url || file.url) ? (
              <img src={getFullMediaUrl(file.thumbnail_url || file.url)} alt={file.original_filename}
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
          <div className="flex items-center gap-1 mt-1 flex-wrap">
            {file.category && <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400 font-medium">{file.category}</span>}
            {file.tags && file.tags.split(',').filter(Boolean).slice(0, 2).map(t => (
              <span key={t.trim()} className="text-[10px] px-1.5 py-0.5 rounded-full bg-purple-100 dark:bg-purple-900/30 text-purple-600 dark:text-purple-400">{t.trim()}</span>
            ))}
          </div>
          <p className="text-xs text-gray-400 mt-1">
            {file.file_size ? formatBytes(file.file_size) : '-'}
          </p>
        </div>
      </div>
  );
};

/* ── 媒体行（列表视图） ── */
export const MediaListRow: React.FC<{
  file: MediaFileItem;
  selected: boolean;
  onSelect: (id: number) => void;
  onDelete: (f: MediaFileItem) => void;
  onPreview: (f: MediaFileItem) => void;
}> = ({file, selected, onSelect, onDelete, onPreview}) => {
  const type = getFileType(file.mime_type || '');
  const color = getFileColor(type);
  const isImage = type === 'image';

  return (
    <div className={`group flex items-center gap-4 px-5 py-3 transition-colors ${
      selected ? 'bg-blue-50/80 dark:bg-blue-900/20' : 'hover:bg-gray-50/80 dark:hover:bg-gray-800/30'
    }`}>
      {/* 选择框 */}
      <button onClick={() => onSelect(file.id)}
              className={`w-5 h-5 rounded border-2 flex items-center justify-center flex-shrink-0 transition-all ${
                selected
                  ? 'bg-blue-600 border-blue-600 text-white'
                  : 'border-gray-300 dark:border-gray-600 opacity-0 group-hover:opacity-100'
              }`}>
        {selected && <CheckSquare className="w-3 h-3"/>}
      </button>

        {/* 缩略图 */}
      <div
        className={`w-12 h-12 rounded-xl overflow-hidden flex-shrink-0 cursor-pointer ${isImage ? '' : color.bg + ' flex items-center justify-center'}`}
        onClick={() => isImage && onPreview(file)}>
          {isImage && (file.thumbnail_url || file.url) ? (
              <img src={getFullMediaUrl(file.thumbnail_url || file.url)} alt="" className="w-full h-full object-cover" loading="lazy"/>
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
          <div className="flex items-center gap-1 mt-0.5 flex-wrap">
            {file.category && <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400 font-medium">{file.category}</span>}
            {file.tags && file.tags.split(',').filter(Boolean).slice(0, 3).map(t => (
              <span key={t.trim()} className="text-[10px] px-1.5 py-0.5 rounded-full bg-purple-100 dark:bg-purple-900/30 text-purple-600 dark:text-purple-400">{t.trim()}</span>
            ))}
          </div>
        </div>

        {/* 大小 */}
      <span className="text-sm text-gray-500 dark:text-gray-400 hidden sm:block w-20 text-right">
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
export const ImagePreview: React.FC<{
  file: MediaFileItem;
  onClose: () => void;
  onEdit?: (f: MediaFileItem) => void;
}> = ({file, onClose, onEdit}) => (
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
            {onEdit && (
              <button onClick={() => onEdit(file)}
                      className="p-2 bg-white/10 hover:bg-white/20 rounded-lg text-white transition-colors">
                <Edit3 className="w-4 h-4"/>
              </button>
            )}
            <button onClick={() => navigator.clipboard.writeText(getFullMediaUrl(file.url))}
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
export const DeleteConfirm: React.FC<{
  title: string;
  message: string;
  onConfirm: () => void;
  onCancel: () => void;
  isPending: boolean;
}> = ({title, message, onConfirm, onCancel, isPending}) => (
  <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm" onClick={onCancel}>
    <div
      className="bg-white dark:bg-gray-900 rounded-2xl shadow-2xl border border-gray-200 dark:border-gray-700 w-full max-w-md p-6"
      onClick={e => e.stopPropagation()}>
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 rounded-full bg-red-100 dark:bg-red-900/30 flex items-center justify-center">
            <AlertTriangle className="w-5 h-5 text-red-600 dark:text-red-400"/>
          </div>
          <div>
            <h3 className="font-semibold text-gray-900 dark:text-white">{title}</h3>
            <p className="text-sm text-gray-500 dark:text-gray-400">此操作不可撤销</p>
          </div>
        </div>
      <p className="text-sm text-gray-600 dark:text-gray-400 mb-6" dangerouslySetInnerHTML={{__html: message}}/>
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

/* ── 批量操作栏 ── */
export const BatchActionBar: React.FC<{
  count: number;
  onDelete: () => void;
  onMove: () => void;
  onBatchTag: () => void;
  onBatchCategory: () => void;
  onClear: () => void;
}> = ({count, onDelete, onMove, onBatchTag, onBatchCategory, onClear}) => (
  <div
    className="fixed bottom-6 left-1/2 -translate-x-1/2 z-40 flex items-center gap-3 px-5 py-3 bg-white dark:bg-gray-900 rounded-2xl shadow-2xl border border-gray-200 dark:border-gray-700">
      <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
        已选 <span className="text-blue-600 dark:text-blue-400 font-semibold">{count}</span> 个文件
      </span>
    <div className="w-px h-6 bg-gray-200 dark:bg-gray-700"/>
    <button onClick={onMove}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded-lg transition-colors">
      <FolderOpen className="w-4 h-4"/>移动
    </button>
    <button onClick={onBatchTag}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-purple-600 hover:bg-purple-50 dark:hover:bg-purple-900/20 rounded-lg transition-colors">
      <Tag className="w-4 h-4"/>标签
    </button>
    <button onClick={onBatchCategory}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-emerald-600 hover:bg-emerald-50 dark:hover:bg-emerald-900/20 rounded-lg transition-colors">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-4 h-4"><path d="M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z"/></svg>分类
    </button>
    <button onClick={onDelete}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors">
      <Trash2 className="w-4 h-4"/>删除
    </button>
    <button onClick={onClear}
            className="p-1.5 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors">
      <X className="w-4 h-4"/>
    </button>
  </div>
);

/* ── 移动到文件夹弹窗 ── */
export const MoveDialog: React.FC<{
  open: boolean;
  folders: FolderItem[];
  fileCount: number;
  onMove: (folderPath: string | null) => void;
  onClose: () => void;
  isPending: boolean;
}> = ({open, folders, fileCount, onMove, onClose, isPending}) => {
  const [selectedPath, setSelectedPath] = useState<string | null>(null);
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm" onClick={onClose}>
      <div
        className="bg-white dark:bg-gray-900 rounded-2xl shadow-2xl border border-gray-200 dark:border-gray-700 w-full max-w-sm p-6"
        onClick={e => e.stopPropagation()}>
        <h3 className="font-semibold text-gray-900 dark:text-white mb-1">移动到文件夹</h3>
        <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">将 {fileCount} 个文件移动到：</p>

        <div className="space-y-1 max-h-60 overflow-y-auto mb-4">
          <button onClick={() => setSelectedPath(null)}
                  className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-colors ${
                    selectedPath === null ? 'bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-400' : 'hover:bg-gray-50 dark:hover:bg-gray-800 text-gray-700 dark:text-gray-300'
                  }`}>
            <FolderOpen className="w-4 h-4 inline mr-2"/>根目录
          </button>
          {folders.map(f => (
            <button key={f.id} onClick={() => setSelectedPath(f.path)}
                    className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-colors ${
                      selectedPath === f.path ? 'bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-400' : 'hover:bg-gray-50 dark:hover:bg-gray-800 text-gray-700 dark:text-gray-300'
                    }`}>
              <FolderOpen className="w-4 h-4 inline mr-2"/>{f.name}
              {f.media_count !== undefined && <span className="text-xs text-gray-400 ml-2">({f.media_count})</span>}
            </button>
          ))}
          {folders.length === 0 && (
            <p className="text-sm text-gray-400 text-center py-4">暂无文件夹</p>
          )}
        </div>

        <div className="flex justify-end gap-3">
          <button onClick={onClose}
                  className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-xl transition-colors">
            取消
          </button>
          <button onClick={() => onMove(selectedPath)} disabled={isPending}
                  className="px-4 py-2 text-sm font-medium bg-blue-600 hover:bg-blue-700 text-white rounded-xl transition-colors flex items-center gap-1.5 disabled:opacity-50">
            {isPending ? (
              <><span
                className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"/>移动中...</>
            ) : '移动'}
          </button>
        </div>
      </div>
    </div>
  );
};

/* ── 分页组件 ── */
export const Pagination: React.FC<{
  page: number;
  totalPages: number;
  total: number;
  onPageChange: (p: number) => void;
}> = ({page, totalPages, total, onPageChange}) => {
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
      <p className="text-xs text-gray-400">第 {page} / {totalPages} 页 · 共 {total} 条</p>
      <div className="flex items-center gap-1.5">
        <button disabled={page <= 1} onClick={() => onPageChange(page - 1)}
                className="p-2 rounded-lg border border-gray-200 dark:border-gray-700 disabled:opacity-30 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors">
          <ChevronLeft className="w-4 h-4"/>
        </button>
        {pages.map((p, i) =>
          p === '...' ? (
            <span key={`ellipsis-${i}`} className="px-2 text-gray-400">…</span>
          ) : (
            <button key={p} onClick={() => onPageChange(p as number)}
                    className={`min-w-[36px] h-9 rounded-lg text-sm font-medium transition-colors ${
                      p === page
                        ? 'bg-blue-600 text-white shadow-sm'
                        : 'border border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800'
                    }`}>{p}</button>
          )
        )}
        <button disabled={page >= totalPages} onClick={() => onPageChange(page + 1)}
                className="p-2 rounded-lg border border-gray-200 dark:border-gray-700 disabled:opacity-30 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors">
          <ChevronRight className="w-4 h-4"/>
        </button>
      </div>
    </div>
  );
};

/* ═══════════════════════════════════════════════════════════════════
   ── 媒体文件 Tab ──
   ═══════════════════════════════════════════════════════════════════ */
