'use client';

import React, {useCallback, useEffect, useRef, useState} from 'react';
import {MediaService} from '@/lib/api';
import type {MediaFile, MediaResponse} from '@/lib/api';
import {motion} from 'framer-motion';
import {
  ChevronLeft, ChevronRight, FileText, FolderInput, FolderOpen, Grid3X3,
  Image as ImageIcon, List, Menu as MenuIcon, Music, Trash2, Upload, Video, X
} from 'lucide-react';

/* ---------- Sub-components ---------- */

const StorageStats: React.FC<{ stats: any; loading: boolean }> = ({stats, loading}) => {
  const items = [
    {label: '图片', count: stats.image_count || 0, color: 'from-blue-500 to-cyan-500', icon: ImageIcon},
    {label: '视频', count: stats.video_count || 0, color: 'from-purple-500 to-pink-500', icon: Video},
    {label: '已用空间', count: stats.storage_used || '0 MB', color: 'from-green-500 to-emerald-500', icon: Upload},
  ];
  return (
    <div className="space-y-3">
      <h3 className="text-sm font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">存储</h3>
      {items.map(item => {
        const Icon = item.icon;
        return (
          <div key={item.label} className={`p-4 rounded-xl bg-gradient-to-br ${item.color} text-white`}>
            <div className="flex items-center gap-2 text-sm opacity-80"><Icon className="w-4 h-4"/>{item.label}</div>
            <p className="text-xl font-bold mt-1">{loading ? '...' : item.count}</p>
          </div>
        );
      })}
      {!loading && stats.storage_percentage !== undefined && (
        <div>
          <div className="flex justify-between text-xs text-gray-500 mb-1"><span>存储</span><span>{stats.storage_percentage}%</span></div>
          <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2"><div className="bg-blue-600 h-2 rounded-full" style={{width: `${stats.storage_percentage}%`}} /></div>
        </div>
      )}
    </div>
  );
};

const UploadArea: React.FC<{
  onUpload: (files: File[]) => void; uploading: boolean; progress: number; status: string; collapsed: boolean; onToggle: () => void
}> = ({onUpload, uploading, progress, status, collapsed, onToggle}) => {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);
  const handleDrop = (e: React.DragEvent) => { e.preventDefault(); setDragOver(false); if (e.dataTransfer.files.length) onUpload(Array.from(e.dataTransfer.files)); };
  return (
    <div className="mb-6">
      <button onClick={onToggle} className="flex items-center gap-2 text-sm font-medium text-gray-600 dark:text-gray-400 mb-3">
        {collapsed ? <ChevronRight className="w-4 h-4"/> : <ChevronDown className="w-4 h-4"/>} 上传文件
      </button>
      {!collapsed && (
        <div onDragOver={e => {e.preventDefault(); setDragOver(true);}} onDragLeave={() => setDragOver(false)} onDrop={handleDrop}
          className={`border-2 border-dashed rounded-2xl p-8 text-center transition-colors cursor-pointer ${dragOver ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20' : 'border-gray-300 dark:border-gray-700 hover:border-blue-400'}`}
          onClick={() => inputRef.current?.click()}>
          <Upload className="w-10 h-10 text-gray-400 mx-auto mb-3"/>
          <p className="text-gray-600 dark:text-gray-400 font-medium">{uploading ? '上传中...' : '拖拽文件到此处或点击上传'}</p>
          <input ref={inputRef} type="file" multiple onChange={e => {if (e.target.files?.length) onUpload(Array.from(e.target.files));}} className="hidden" />
          {uploading && <div className="mt-4"><div className="w-full bg-gray-200 rounded-full h-2"><div className="bg-blue-600 h-2 rounded-full transition-all" style={{width: `${progress}%`}} /></div><p className="text-sm text-gray-500 mt-1">{status}</p></div>}
        </div>
      )}
    </div>
  );
};
const ChevronDown: React.FC<{className?: string}> = (p) => <svg className={p.className} fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7"/></svg>;

const MediaGrid: React.FC<{
  files: MediaFile[]; loading: boolean; viewMode: 'grid'|'list'; selected: number[];
  onSelect: (id: number) => void; onPreview: (m: MediaFile) => void; onDelete: (m: MediaFile) => void
}> = ({files, loading, viewMode, selected, onSelect, onPreview, onDelete}) => {
  if (loading) return <div className="p-12 text-center"><div className="animate-spin w-8 h-8 border-2 border-blue-600 border-t-transparent rounded-full mx-auto" /></div>;
  if (!files.length) return <div className="p-12 text-center text-gray-400"><ImageIcon className="w-12 h-12 mx-auto mb-3 opacity-50"/><p>暂无媒体文件</p></div>;

  const getIcon = (mime: string) => mime?.startsWith('video/') ? Video : mime?.startsWith('audio/') ? Music : FileText;

  if (viewMode === 'list') return (
    <div className="bg-white dark:bg-gray-900 rounded-xl border overflow-hidden">
      <table className="w-full"><thead className="bg-gray-50 dark:bg-gray-800"><tr>
        <th className="w-10 px-4 py-3"></th><th className="text-left text-sm font-medium text-gray-500 py-3">文件</th><th className="text-left text-sm font-medium text-gray-500 py-3 hidden sm:table-cell">类型</th><th className="text-right text-sm font-medium text-gray-500 py-3 pr-4">操作</th>
      </tr></thead><tbody className="divide-y">
        {files.map(f => {
          const Icon = f.mime_type?.startsWith('image/') ? ImageIcon : getIcon(f.mime_type || '');
          return (
            <tr key={f.id} className={`hover:bg-gray-50 dark:hover:bg-gray-800 ${selected.includes(f.id) ? 'bg-blue-50 dark:bg-blue-900/20' : ''}`}>
              <td className="px-4"><input type="checkbox" checked={selected.includes(f.id)} onChange={() => onSelect(f.id)} className="h-4 w-4 text-blue-600 rounded"/></td>
              <td className="py-3 cursor-pointer" onClick={() => onPreview(f)}>
                <div className="flex items-center gap-3">
                  {f.mime_type?.startsWith('image/') && f.url ? (
                    <img src={f.url} alt={f.original_filename} className="w-10 h-10 rounded-lg object-cover" />
                  ) : <div className="w-10 h-10 rounded-lg bg-gray-100 dark:bg-gray-700 flex items-center justify-center"><Icon className="w-5 h-5 text-gray-400"/></div>}
                  <div><p className="text-sm font-medium text-gray-900 dark:text-white truncate max-w-[200px]">{f.original_filename}</p><p className="text-xs text-gray-500">{f.file_size ? `${(f.file_size / 1024).toFixed(1)} KB` : ''}</p></div>
                </div>
              </td>
              <td className="text-sm text-gray-500 hidden sm:table-cell">{f.mime_type?.split('/')[0] || '-'}</td>
              <td className="pr-4 text-right"><button onClick={() => onDelete(f)} className="p-1 text-gray-400 hover:text-red-500"><Trash2 className="w-4 h-4"/></button></td>
            </tr>
          );
        })}
      </tbody></table>
    </div>
  );

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
      {files.map(f => (
        <div key={f.id} className={`relative group aspect-square rounded-xl overflow-hidden border ${selected.includes(f.id) ? 'border-blue-500 ring-2 ring-blue-500' : 'border-gray-200 dark:border-gray-700'} bg-gray-50 dark:bg-gray-800`}>
          <input type="checkbox" checked={selected.includes(f.id)} onChange={() => onSelect(f.id)} className="absolute top-2 left-2 z-10 h-4 w-4 text-blue-600 rounded" />
          {f.mime_type?.startsWith('image/') && f.url ? (
            <img src={f.url} alt={f.original_filename} className="w-full h-full object-cover cursor-pointer" onClick={() => onPreview(f)} />
          ) : (
            <div className="w-full h-full flex items-center justify-center cursor-pointer" onClick={() => onPreview(f)}>
              {React.createElement(getIcon(f.mime_type || ''), {className: 'w-10 h-10 text-gray-400'})}
            </div>
          )}
          <div className="absolute inset-x-0 bottom-0 p-2 bg-gradient-to-t from-black/60 to-transparent opacity-0 group-hover:opacity-100 transition-opacity">
            <p className="text-xs text-white truncate">{f.original_filename}</p>
          </div>
          <button onClick={() => onDelete(f)} className="absolute top-2 right-2 z-10 p-1 bg-red-500 text-white rounded-full opacity-0 group-hover:opacity-100 transition-opacity"><X className="w-3 h-3"/></button>
        </div>
      ))}
    </div>
  );
};

const PreviewModal: React.FC<{media: MediaFile | null; onClose: () => void}> = ({media, onClose}) => {
  if (!media) return null;
  return (
    <div className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-4" onClick={onClose}>
      <div className="max-w-4xl max-h-[90vh] bg-white dark:bg-gray-900 rounded-2xl overflow-hidden shadow-2xl" onClick={e => e.stopPropagation()}>
        {media.mime_type?.startsWith('image/') && media.url ? (
          <img src={media.url} alt={media.original_filename} className="max-w-full max-h-[70vh] object-contain" />
        ) : (
          <div className="p-16 text-center"><FileText className="w-16 h-16 text-gray-400 mx-auto mb-4"/><p className="text-gray-600">{media.original_filename}</p></div>
        )}
        <div className="p-6 border-t border-gray-200 dark:border-gray-700">
          <h3 className="font-bold text-gray-900 dark:text-white">{media.original_filename}</h3>
          <p className="text-sm text-gray-500 mt-1">{(media.file_size / 1024).toFixed(1)} KB · {media.mime_type}</p>
        </div>
      </div>
    </div>
  );
};

const DeleteConfirm: React.FC<{item: MediaFile; onCancel: () => void; onConfirm: () => void}> = ({item, onCancel, onConfirm}) => (
  <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4" onClick={onCancel}>
    <div className="bg-white dark:bg-gray-900 rounded-2xl p-6 max-w-sm w-full shadow-xl" onClick={e => e.stopPropagation()}>
      <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-2">确认删除</h3>
      <p className="text-sm text-gray-500 mb-6">确定要删除 <span className="font-medium text-gray-700 dark:text-gray-300">{item.original_filename}</span> 吗？此操作不可恢复。</p>
      <div className="flex justify-end gap-3">
        <button onClick={onCancel} className="px-4 py-2 bg-gray-100 dark:bg-gray-800 rounded-lg text-sm font-medium">取消</button>
        <button onClick={onConfirm} className="px-4 py-2 bg-red-600 text-white rounded-lg text-sm font-medium hover:bg-red-700">删除</button>
      </div>
    </div>
  </div>
);

/* ---------- Shared upload hook ---------- */
const useMediaUpload = (onComplete?: () => void) => {
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadStatus, setUploadStatus] = useState('');
  const uploadFiles = async (files: File[]) => {
    if (!files.length) return;
    setUploading(true); setUploadProgress(0); setUploadStatus(`开始上传 ${files.length} 个文件...`);
    try {
      for (let i = 0; i < files.length; i++) {
        const pct = ((i) / files.length) * 100;
        setUploadProgress(pct); setUploadStatus(`正在上传: ${files[i].name} (${i+1}/${files.length})`);
        await MediaService.uploadMediaFileWithProgress(files[i], (p, s) => {
          setUploadProgress(((i / files.length) * 100) + (p / files.length));
          setUploadStatus(s);
        });
      }
      setUploadStatus('上传完成!');
      if (onComplete) onComplete();
    } catch (e: any) { setUploadStatus(`上传失败: ${e.message}`); }
    finally { setTimeout(() => { setUploading(false); setUploadProgress(0); setUploadStatus(''); }, 2000); }
  };
  return {uploading, uploadProgress, uploadStatus, uploadFiles};
};

/* ---------- Main MediaPage ---------- */
const MediaPage: React.FC = () => {
  const [files, setFiles] = useState<MediaFile[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [filterType, setFilterType] = useState('');
  const [search, setSearch] = useState('');
  const [viewMode, setViewMode] = useState<'grid'|'list'>('grid');
  const [selected, setSelected] = useState<number[]>([]);
  const [previewMedia, setPreviewMedia] = useState<MediaFile | null>(null);
  const [deleteItem, setDeleteItem] = useState<MediaFile | null>(null);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [uploadCollapsed, setUploadCollapsed] = useState(true);
  const [stats, setStats] = useState<any>({image_count: 0, video_count: 0, storage_used: '0 MB', storage_percentage: 0});

  const loadFiles = useCallback(async () => {
    setLoading(true);
    try {
      const res = await MediaService.getMediaFiles({page, per_page: 20, media_type: filterType || undefined, q: search || undefined});
      if (res.success && res.data) {
        const d = res.data as MediaResponse;
        setFiles(d.media_items || []);
        setTotalPages(d.pagination?.pages || 1);
        if (d.stats) setStats(d.stats);
      }
    } catch {} finally { setLoading(false); }
  }, [page, filterType, search]);

  useEffect(() => { loadFiles(); }, [loadFiles]);

  const {uploading, uploadProgress, uploadStatus, uploadFiles} = useMediaUpload(() => loadFiles());

  const handleDelete = async (id: number) => {
    const res = await MediaService.deleteMediaFile([id]);
    if (res.success) { setDeleteItem(null); loadFiles(); }
    else alert(res.error || '删除失败');
  };

  const filteredFiles = files;

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950 pt-24 pb-12">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Toolbar */}
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">媒体库</h1>
          <div className="flex items-center gap-2">
            <button onClick={() => setSidebarCollapsed(!sidebarCollapsed)} className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800">
              {sidebarCollapsed ? <ChevronRight className="w-5 h-5"/> : <ChevronLeft className="w-5 h-5"/>}
            </button>
            <button onClick={() => setViewMode('grid')} className={`p-2 rounded-lg ${viewMode === 'grid' ? 'bg-blue-100 text-blue-600' : 'hover:bg-gray-100 dark:hover:bg-gray-800'}`}><Grid3X3 className="w-5 h-5"/></button>
            <button onClick={() => setViewMode('list')} className={`p-2 rounded-lg ${viewMode === 'list' ? 'bg-blue-100 text-blue-600' : 'hover:bg-gray-100 dark:hover:bg-gray-800'}`}><List className="w-5 h-5"/></button>
          </div>
        </div>

        <div className="flex flex-col lg:flex-row gap-8">
          {/* Sidebar */}
          <aside className={`${sidebarCollapsed ? 'hidden' : 'lg:w-56'} flex-shrink-0 space-y-6`}>
            <StorageStats stats={stats} loading={loading} />
            <div className="space-y-2">
              <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider">筛选</h3>
              {[{value:'',label:'全部'},{value:'image',label:'图片'},{value:'video',label:'视频'},{value:'audio',label:'音频'},{value:'application',label:'文档'}].map(t => (
                <button key={t.value} onClick={() => {setFilterType(t.value); setPage(1)}}
                  className={`w-full text-left px-3 py-2 rounded-lg text-sm ${filterType === t.value ? 'bg-blue-50 text-blue-600 dark:bg-blue-900/20 dark:text-blue-400' : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800'}`}>
                  {t.label}
                </button>
              ))}
            </div>
          </aside>

          {/* Main */}
          <main className="flex-1">
            {/* Upload */}
            <UploadArea onUpload={uploadFiles} uploading={uploading} progress={uploadProgress} status={uploadStatus} collapsed={uploadCollapsed} onToggle={() => setUploadCollapsed(!uploadCollapsed)} />

            {/* Search & batch actions */}
            <div className="flex flex-wrap items-center gap-3 mb-4">
              <input type="text" value={search} onChange={e => {setSearch(e.target.value); setPage(1)}}
                placeholder="搜索文件..." className="flex-1 min-w-[200px] px-4 py-2.5 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white" />
              {selected.length > 0 && (
                <div className="flex items-center gap-2">
                  <span className="text-sm text-blue-600 font-medium">{selected.length} 已选</span>
                  <button onClick={() => setSelected([])} className="px-3 py-2 text-sm bg-gray-200 dark:bg-gray-700 rounded-lg">取消</button>
                  <button onClick={async () => {const res = await MediaService.deleteMediaFile(selected); if (res.success) {setSelected([]); loadFiles();}}} className="px-3 py-2 text-sm bg-red-600 text-white rounded-lg hover:bg-red-700"><Trash2 className="w-4 h-4 inline-block mr-1"/>删除</button>
                </div>
              )}
            </div>

            <MediaGrid files={filteredFiles} loading={loading} viewMode={viewMode} selected={selected} onSelect={id => setSelected(s => s.includes(id) ? s.filter(x => x !== id) : [...s, id])} onPreview={setPreviewMedia} onDelete={setDeleteItem} />

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-center gap-2 mt-8">
                <button disabled={page <= 1} onClick={() => setPage(p => p-1)} className="p-2 rounded-lg border disabled:opacity-30 hover:bg-gray-100 dark:hover:bg-gray-800"><ChevronLeft className="w-4 h-4"/></button>
                {Array.from({length: totalPages}, (_, i) => i+1).map(p => (
                  <button key={p} onClick={() => setPage(p)} className={`px-3 py-1.5 rounded-lg text-sm ${p === page ? 'bg-blue-600 text-white' : 'border hover:bg-gray-100 dark:hover:bg-gray-800'}`}>{p}</button>
                ))}
                <button disabled={page >= totalPages} onClick={() => setPage(p => p+1)} className="p-2 rounded-lg border disabled:opacity-30 hover:bg-gray-100"><ChevronRight className="w-4 h-4"/></button>
              </div>
            )}
          </main>
        </div>
      </div>

      <PreviewModal media={previewMedia} onClose={() => setPreviewMedia(null)} />
      {deleteItem && <DeleteConfirm item={deleteItem} onCancel={() => setDeleteItem(null)} onConfirm={() => handleDelete(deleteItem.id)} />}
    </div>
  );
};

export default MediaPage;
