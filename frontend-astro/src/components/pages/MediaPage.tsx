'use client';

import React, {useCallback, useEffect, useRef, useState} from 'react';
import type {MediaFile} from '@/lib/api';
import {MediaService} from '@/lib/api';
import {UploadArea} from '@/components/pages/media/UploadArea';
import {StorageStats} from '@/components/pages/media/StorageStats';
import {useMediaUpload} from '@/components/pages/media/useMediaUpload';
import {PreviewModal, DeleteConfirm, MoveDialog, CreateFolderDialog} from '@/components/pages/media/MediaDialogs';
import {OfflineDownloadDialog} from '@/components/pages/media/OfflineDownloadDialog';
import {FolderTree} from '@/components/pages/media/FolderTree';
import {MEDIA} from '@/lib/api/api-paths';
import type {FolderNode} from '@/components/pages/media/FolderTree';
import {MediaGrid} from '@/components/pages/media/MediaGrid';
import {AudioLayer} from '@/components/pages/media/AudioPlayer';
import {AuthGuard} from '@/components/AuthGuard';
import {QueryProvider} from '@/components/QueryProvider';
import {motion} from 'framer-motion';
import {
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  CloudDownload,
  FileText,
  Filter,
  FolderClosed,
  FolderOpen,
  Grid3X3,
  Image as ImageIcon,
  List,
  Music,
  Plus,
  Tag,
  Trash2,
  Upload,
  Video,
  X
} from 'lucide-react';
import {getConfig} from '@/lib/config';
import DesktopLyrics from '@/components/audio/DesktopLyrics';
import {apiClient} from "@/lib/api/base-client";
import {getFullMediaUrl} from '@/lib/utils';
import {useConfirm} from '@/components/ui/confirm-provider';

/* ---------- Shared icons ---------- */
const _Minus: React.FC<{ className?: string }> = p => <svg className={p.className} fill="none" viewBox="0 0 24 24"
                                                           stroke="currentColor">
  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 12H4"/>
</svg>;
const _File: React.FC<{ className?: string }> = p => <svg className={p.className} fill="none" viewBox="0 0 24 24"
                                                          stroke="currentColor">
  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
        d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z"/>
</svg>;

/* ---------- FolderTree ---------- */
/* ---------- StorageStats ---------- */
/* ---------- UploadArea ---------- */
/* ---------- MediaGrid ---------- */
/** 按分类分组：返回 Map<分类名, MediaFile[]> */

// 将歌词行拆分为逐字/逐词 token（中文按字，英文按单词）
/* ========== Main MediaPage ========== */
const MediaPage: React.FC = () => {
  const confirm = useConfirm();
  const [files, setFiles] = useState<MediaFile[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [filterType, setFilterType] = useState('');
  const [search, setSearch] = useState('');
  const [viewMode, setViewMode] = useState<'grid'|'list'>('grid');
  const [selected, setSelected] = useState<number[]>([]);
  const [previewMedia, setPreviewMedia] = useState<MediaFile|null>(null);
  const [nowPlaying, setNowPlaying] = useState<MediaFile|null>(null);
  const [deleteItem, setDeleteItem] = useState<MediaFile|null>(null);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [uploadCollapsed, setUploadCollapsed] = useState(true);
  const [stats, setStats] = useState<any>({});
  // Folder state
  const [folders, setFolders] = useState<FolderNode[]>([]);
  const [selectedFolder, setSelectedFolder] = useState<number|null>(null);
  const [folderLoading, setFolderLoading] = useState(true);
  const [showCreateFolder, setShowCreateFolder] = useState(false);
  const [showMoveDialog, setShowMoveDialog] = useState(false);

  // Tags & Categories state
    const [allTags, setAllTags] = useState<{ id: string; name: string }[]>([]);
    const [allCategories, setAllCategories] = useState<{ id: string; name: string; count?: number }[]>([]);
    const [selectedTagIds, setSelectedTagIds] = useState<string[]>([]);
    const [selectedCategoryId, setSelectedCategoryId] = useState<string | null>(null);
  const [showFilters, setShowFilters] = useState(false);

  // Offline download dialog
  const [showOfflineDownload, setShowOfflineDownload] = useState(false);

  // Tag editor state (单文件 + 批量)
  const [tagEditorMedia, setTagEditorMedia] = useState<{id: number; tags: string; multiple?: boolean} | null>(null);

  const loadFolders = useCallback(async () => {
    setFolderLoading(true);
    try {
      const res = await apiClient.get(MEDIA.FOLDERS_TREE);
      if (res.success && res.data) setFolders((res.data as any).tree || []);
    } catch {} finally { setFolderLoading(false); }
  }, []);

  const loadTags = useCallback(async () => {
    try {
      const res = await apiClient.get(MEDIA.TAGS_LIST);
      if (res.success && res.data) {
        const d = res.data as any;
        setAllTags((d.tags || []).map((t: {name: string; count: number}) => ({id: t.name, name: t.name, count: t.count})));
      }
    } catch {}
  }, []);

  const loadCategories = useCallback(async () => {
    try {
      const res = await apiClient.get(MEDIA.CATEGORIES);
      if (res.success && res.data) {
        const d = res.data as any;
        setAllCategories((d.categories || []).map((c: {name: string; count: number}) => ({id: c.name, name: c.name, count: c.count})));
      }
    } catch {}
  }, []);

  const loadFiles = useCallback(async () => {
    setLoading(true);
    try {
      const params: any = {page, per_page: 20, media_type: filterType||undefined, q: search||undefined};
      // Advanced filters
      if (selectedCategoryId) params.category = selectedCategoryId;
      // Get folder name from selected folder
      if (selectedFolder !== null) {
        const findName = (nodes: FolderNode[], id: number): string|null => {
          for (const n of nodes) { if (n.id===id) return n.name; if (n.children) {const r=findName(n.children,id); if(r) return r;}} return null;
        };
        const fn = findName(folders, selectedFolder);
        if (fn) params.folder_name = fn;
      }
      const res = await MediaService.getMediaFiles(params);
      if (res.success && res.data) {
        const d = res.data as any;
        setFiles(d.media_items || d.files || []);
        setTotalPages(d.pagination?.pages || d.total_pages || 1);
        if (d.stats) setStats(d.stats);
      } else {
        console.error('[MediaPage] loadFiles failed:', res.error || res.message);
      }
    } catch (e) {
      console.error('[MediaPage] loadFiles error:', e);
    } finally { setLoading(false); }
  }, [page, filterType, search, selectedFolder, folders, selectedCategoryId]);

  useEffect(() => { loadFiles(); }, [loadFiles]);
  useEffect(() => { loadFolders(); }, []);
  useEffect(() => { loadTags(); loadCategories(); }, []);

  const {uploading, uploadProgress, uploadStatus, uploadFiles} = useMediaUpload(() => loadFiles());

  const handleDelete = async (id: number) => {
    const res = await apiClient.delete(MEDIA.DELETE(id));
    if (res.success) {
      setDeleteItem(null);
      await loadFiles();
    } else alert(res.error || '删除失败');
  };

  const handleCreateFolder = async (name: string) => {
    const res = await apiClient.post(MEDIA.FOLDERS_CREATE, {name});
    if (res.success) {
      setShowCreateFolder(false);
      await loadFolders();
    }
    else alert(res.error||'创建失败');
  };

  const handleMoveToFolder = async (folderPath: string|null) => {
    if (!selected.length) return;
    const res = await apiClient.post(MEDIA.FOLDERS_MOVE, {media_ids: selected, folder_path: folderPath});
    if (res.success) {
      setSelected([]);
      setShowMoveDialog(false);
      await loadFiles();
    }
    else alert(res.error||'移动失败');
  };

  const handleDeleteFolder = async (id: number) => {
    if (!await confirm({message: '确定删除此文件夹？', variant: 'danger'})) return;
    const res = await apiClient.delete(MEDIA.FOLDERS_DELETE(id));
    if (res.success) {
      if (selectedFolder === id) setSelectedFolder(null);
      await loadFolders();
    }
    else alert(res.error||'删除失败');
  };

  const handleSaveTags = async (mediaId: number, tags: string[], mode: 'add' | 'replace') => {
    try {
      const res = await apiClient.post(MEDIA.TAGS(mediaId), {tags, mode});
      if (res.success) {
        await loadFiles();
        loadTags();
        return true;
      }
      else { alert(res.error || '保存标签失败'); return false; }
    } catch { alert('保存标签失败'); return false; }
  };

  // 分类编辑
  const [categoryEditorMedia, setCategoryEditorMedia] = useState<{id: number; category: string | null; multiple?: boolean} | null>(null);

  const handleSaveCategory = async (mediaId: number, category: string | null) => {
    try {
      const res = await apiClient.put(MEDIA.DETAIL(mediaId), {category});
      if (res.success) {
        await loadFiles();
        loadCategories();
        return true;
      }
      else { alert(res.error || '保存分类失败'); return false; }
    } catch { alert('保存分类失败'); return false; }
  };

  const handleSaveBatchCategory = async (category: string) => {
    if (!selected.length) return;
    try {
      const res = await apiClient.post(MEDIA.BATCH_CATEGORIZE, {media_ids: selected, category});
      if (res.success) {
        await loadFiles();
        loadCategories();
      }
      else alert(res.error || '批量设置分类失败');
    } catch { alert('批量设置分类失败'); }
  };

  const handleSaveBatchTags = async (tag: string) => {
    if (!selected.length) return;
    try {
      const res = await apiClient.post(MEDIA.BATCH_TAGS, {media_ids: selected, tags: [tag], mode: 'add'});
      if (res.success) {
        await loadFiles();
        loadTags();
      }
      else alert(res.error || '批量添加标签失败');
    } catch { alert('批量添加标签失败'); }
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950 pt-24 pb-12">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">媒体库</h1>
          <div className="flex items-center gap-2">
            <button onClick={()=>setShowOfflineDownload(true)}
                    className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-purple-600 hover:bg-purple-700 text-white text-sm font-medium transition-colors shadow-sm">
              <CloudDownload className="w-4 h-4"/>
              <span className="hidden sm:inline">离线下载</span>
            </button>
            <button onClick={()=>setSidebarCollapsed(!sidebarCollapsed)} className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800">{sidebarCollapsed?<ChevronRight className="w-5 h-5"/>:<ChevronLeft className="w-5 h-5"/>}</button>
            <button onClick={()=>setViewMode('grid')} className={`p-2 rounded-lg ${viewMode==='grid'?'bg-blue-100 text-blue-600':'hover:bg-gray-100 dark:hover:bg-gray-800'}`}><Grid3X3 className="w-5 h-5"/></button>
            <button onClick={()=>setViewMode('list')} className={`p-2 rounded-lg ${viewMode==='list'?'bg-blue-100 text-blue-600':'hover:bg-gray-100 dark:hover:bg-gray-800'}`}><List className="w-5 h-5"/></button>
          </div>
        </div>

        <div className="flex flex-col lg:flex-row gap-8">
          <aside className={`${sidebarCollapsed?'hidden':'lg:w-56'} flex-shrink-0 space-y-6`}>
            <StorageStats stats={stats} loading={loading}/>
            <FolderTree folders={folders} selectedId={selectedFolder} onSelect={f=>{setSelectedFolder(f?.id??null);setPage(1)}} onCreate={()=>setShowCreateFolder(true)} onDelete={handleDeleteFolder} loading={folderLoading}/>
          </aside>

          <main className="flex-1">
            <UploadArea onUpload={uploadFiles} uploading={uploading} progress={uploadProgress} status={uploadStatus} collapsed={uploadCollapsed} onToggle={()=>setUploadCollapsed(!uploadCollapsed)}/>

            <div className="flex flex-wrap items-center gap-3 mb-2">
              <input type="text" value={search} onChange={e=>{setSearch(e.target.value);setPage(1)}} placeholder="搜索文件..." className="flex-1 min-w-[200px] px-4 py-2.5 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white"/>
              <button onClick={() => setShowFilters(v => !v)}
                      className={`px-3 py-2.5 rounded-xl text-sm flex items-center gap-1.5 transition-colors ${showFilters || selectedTagIds.length || selectedCategoryId ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 border border-blue-200 dark:border-blue-800' : 'bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800'}`}>
                <Filter className="w-4 h-4"/>
                {selectedTagIds.length || selectedCategoryId ? <span className="inline-flex items-center justify-center w-5 h-5 text-[10px] font-bold bg-blue-500 text-white rounded-full">{(selectedTagIds.length) + (selectedCategoryId ? 1 : 0)}</span> : '筛选'}
              </button>
              {selected.length>0 && (<div className="flex items-center gap-2 flex-wrap">
                <span className="text-sm text-blue-600 font-medium">{selected.length} 已选</span>
                <button onClick={()=>setSelected([])} className="px-3 py-2 text-sm bg-gray-200 dark:bg-gray-700 rounded-lg">取消</button>
                <button onClick={()=>{if(selected.length)setShowMoveDialog(true);}} className="px-3 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700"><FolderClosed className="w-4 h-4 inline mr-1"/>移动</button>
                <button onClick={()=>{if(selected.length)setTagEditorMedia({id:0, tags:'', multiple:true});}} className="px-3 py-2 text-sm bg-purple-600 text-white rounded-lg hover:bg-purple-700"><Tag className="w-4 h-4 inline mr-1"/>标签</button>
                <button onClick={async () => {
                  if (selected.length) setCategoryEditorMedia({id: 0, category: null, multiple: true});
                }} className="px-3 py-2 text-sm bg-emerald-600 text-white rounded-lg hover:bg-emerald-700"><FolderClosed
                  className="w-4 h-4 inline mr-1"/>分类
                </button>
                <button onClick={async () => {
                  if (!await confirm({message: `删除 ${selected.length} 个文件？`, variant: 'danger'})) return;
                  const r = await MediaService.deleteMediaFile(selected);
                  if (r.success) {
                    setSelected([]);
                    loadFiles();
                  }
                }} className="px-3 py-2 text-sm bg-red-600 text-white rounded-lg hover:bg-red-700"><Trash2
                  className="w-4 h-4 inline mr-1"/>删除
                </button>
              </div>)}
            </div>

            {/* 高级筛选面板 */}
            {showFilters && (
                <motion.div
                    initial={{height: 0, opacity: 0}}
                    animate={{height: 'auto', opacity: 1}}
                    className="overflow-hidden mb-4"
                >
                  <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-xl p-4 space-y-4">
                    {/* 类型筛选 */}
                    <div>
                      <label className="text-xs font-medium text-gray-500 dark:text-gray-400 block mb-2">文件类型</label>
                      <div className="flex flex-wrap gap-2">
                        {[
                          {key: '', label: '全部'},
                          {key: 'image', label: '图片'},
                          {key: 'video', label: '视频'},
                          {key: 'audio', label: '音频'},
                          {key: 'application/pdf', label: 'PDF'},
                        ].map(t => (
                            <button key={t.key}
                                    onClick={() => { setFilterType(t.key); setPage(1); }}
                                    className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                                        filterType === t.key
                                            ? 'bg-blue-600 text-white'
                                            : 'bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700'
                                    }`}
                            >{t.label}</button>
                        ))}
                      </div>
                    </div>

                    {/* 标签筛选 */}
                    {allTags.length > 0 && (
                        <div>
                          <label className="text-xs font-medium text-gray-500 dark:text-gray-400 block mb-2">
                            标签 {selectedTagIds.length > 0 && (
                              <button onClick={() => { setSelectedTagIds([]); setPage(1); }}
                                      className="ml-2 text-blue-500 hover:text-blue-600 text-[10px]">清除</button>
                          )}
                          </label>
                          <div className="flex flex-wrap gap-1.5">
                            {allTags.map(tag => (
                                <button key={tag.id}
                                        onClick={() => {
                                          setSelectedTagIds(prev =>
                                              prev.includes(tag.id)
                                                  ? prev.filter(id => id !== tag.id)
                                                  : [...prev, tag.id]
                                          );
                                          setPage(1);
                                        }}
                                        className={`px-2.5 py-1 rounded-lg text-xs transition-colors ${
                                            selectedTagIds.includes(tag.id)
                                                ? 'bg-purple-600 text-white'
                                                : 'bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700'
                                        }`}
                                >{tag.name}</button>
                            ))}
                          </div>
                        </div>
                    )}

                    {/* 分类筛选 */}
                    {allCategories.length > 0 && (
                        <div>
                          <label className="text-xs font-medium text-gray-500 dark:text-gray-400 block mb-2">
                            分类 {selectedCategoryId && (
                              <button onClick={() => { setSelectedCategoryId(null); setPage(1); }}
                                      className="ml-2 text-blue-500 hover:text-blue-600 text-[10px]">清除</button>
                          )}
                          </label>
                          <div className="flex flex-wrap gap-1.5">
                            {allCategories.map(cat => (
                                <button key={cat.id}
                                        onClick={() => {
                                          setSelectedCategoryId(prev => prev === cat.id ? null : cat.id);
                                          setPage(1);
                                        }}
                                        className={`px-2.5 py-1 rounded-lg text-xs transition-colors ${
                                            selectedCategoryId === cat.id
                                                ? 'bg-emerald-600 text-white'
                                                : 'bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700'
                                        }`}
                                >{cat.name}</button>
                            ))}
                          </div>
                        </div>
                    )}

                    {/* 摘要: 当前筛选条件 */}
                    {(selectedTagIds.length > 0 || selectedCategoryId || filterType) && (
                        <div className="flex items-center gap-2 pt-2 border-t border-gray-100 dark:border-gray-800">
                          <span className="text-xs text-gray-400">当前筛选:</span>
                          {filterType && (
                              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400 text-xs">
                            {filterType === 'application/pdf' ? 'PDF' : filterType}
                                <button onClick={() => { setFilterType(''); setPage(1); }} className="hover:text-blue-800">✕</button>
                          </span>
                          )}
                          {selectedTagIds.map(id => {
                            const tag = allTags.find(t => t.id === id);
                            return tag ? (
                                <span key={id} className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-purple-50 dark:bg-purple-900/20 text-purple-600 dark:text-purple-400 text-xs">
                              {tag.name}
                                  <button onClick={() => { setSelectedTagIds(prev => prev.filter(i => i !== id)); setPage(1); }} className="hover:text-purple-800">✕</button>
                            </span>
                            ) : null;
                          })}
                          {selectedCategoryId && allCategories.find(c => c.id === selectedCategoryId) && (
                              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-emerald-50 dark:bg-emerald-900/20 text-emerald-600 dark:text-emerald-400 text-xs">
                            {allCategories.find(c => c.id === selectedCategoryId)?.name}
                                <button onClick={() => { setSelectedCategoryId(null); setPage(1); }} className="hover:text-emerald-800">✕</button>
                            </span>
                          )}
                          <button onClick={() => { setSelectedTagIds([]); setSelectedCategoryId(null); setFilterType(''); setPage(1); }}
                                  className="text-xs text-red-500 hover:text-red-600 ml-auto">清除全部</button>
                        </div>
                    )}
                  </div>
                </motion.div>
            )}

            <MediaGrid files={files} loading={loading} viewMode={viewMode} selected={selected} onSelect={id=>setSelected(s=>s.includes(id)?s.filter(x=>x!==id):[...s,id])} onPreview={f => {
              if (f.mime_type?.startsWith('audio/')) { setNowPlaying(f); }
              else { setPreviewMedia(f); }
            }} onDelete={setDeleteItem} onEditTags={f => setTagEditorMedia({id: f.id, tags: (f as any).tags || ''})} onEditCategory={f => setCategoryEditorMedia({id: f.id, category: (f as any).category || null})}/>

            {totalPages>1 && (<div className="flex items-center justify-center gap-2 mt-8">
              <button disabled={page<=1} onClick={()=>setPage(p=>p-1)} className="p-2 rounded-lg border disabled:opacity-30 hover:bg-gray-100"><ChevronLeft className="w-4 h-4"/></button>
              {Array.from({length:totalPages},(_,i)=>i+1).map(p=><button key={p} onClick={()=>setPage(p)} className={`px-3 py-1.5 rounded-lg text-sm ${p===page?'bg-blue-600 text-white':'border hover:bg-gray-100 dark:hover:bg-gray-800'}`}>{p}</button>)}
              <button disabled={page>=totalPages} onClick={()=>setPage(p=>p+1)} className="p-2 rounded-lg border disabled:opacity-30 hover:bg-gray-100"><ChevronRight className="w-4 h-4"/></button>
            </div>)}
          </main>
        </div>
      </div>

      {/* 非音频预览 */}
      <PreviewModal media={previewMedia} onClose={()=>setPreviewMedia(null)}/>
      {/* 持久音频层 — 独立于预览，不被打断 */}
      {nowPlaying && (
          <AudioLayer
              media={nowPlaying}
              onClose={() => { setNowPlaying(null); }}
          />
      )}
      {deleteItem && <DeleteConfirm item={deleteItem} onCancel={()=>setDeleteItem(null)} onConfirm={()=>handleDelete(deleteItem.id)}/>}
      <CreateFolderDialog open={showCreateFolder} onClose={()=>setShowCreateFolder(false)} onCreate={handleCreateFolder}/>
      <MoveDialog open={showMoveDialog} onClose={()=>setShowMoveDialog(false)} folders={folders} mediaCount={selected.length} onMove={handleMoveToFolder}/>
      <TagEditor
          media={tagEditorMedia}
          allTags={allTags}
          onClose={() => setTagEditorMedia(null)}
          onSave={handleSaveTags}
      />
      <BatchTagDialog
          open={tagEditorMedia?.multiple === true}
          mediaCount={selected.length}
          onClose={() => setTagEditorMedia(null)}
          onSave={handleSaveBatchTags}
          allTags={allTags}
      />
      <CategoryEditor
          media={categoryEditorMedia}
          allCategories={allCategories}
          onClose={() => setCategoryEditorMedia(null)}
          onSave={handleSaveCategory}
      />
      <BatchCategoryDialog
          open={categoryEditorMedia?.multiple === true}
          mediaCount={selected.length}
          onClose={() => setCategoryEditorMedia(null)}
          onSave={handleSaveBatchCategory}
          allCategories={allCategories}
      />
      <OfflineDownloadDialog open={showOfflineDownload} onClose={()=>setShowOfflineDownload(false)}/>
    </div>
  );
};

const MediaPageGuard: React.FC = () => <AuthGuard><QueryProvider><MediaPage/></QueryProvider></AuthGuard>;
export default MediaPageGuard;

/* ========== Tag Editor (single media) ========== */
const TagEditor: React.FC<{
  media: {id: number; tags: string; multiple?: boolean} | null;
  allTags: {id: string; name: string; count?: number}[];
  onClose: () => void;
  onSave: (mediaId: number, tags: string[], mode: 'add'|'replace') => Promise<boolean>;
}> = ({media, allTags, onClose, onSave}) => {
  const [tags, setTags] = useState<string[]>([]);
  const [inputVal, setInputVal] = useState('');
  const [saving, setSaving] = useState(false);
  const [suggestions, setSuggestions] = useState<{id: string; name: string}[]>([]);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (media) {
      setTags((media.tags || '').split(',').filter(Boolean).map(t => t.trim()));
      setInputVal('');
    }
  }, [media]);

  useEffect(() => {
    if (!inputVal.trim()) { setSuggestions([]); return; }
    const q = inputVal.toLowerCase();
    setSuggestions(
        allTags.filter(t => t.name.toLowerCase().includes(q) && !tags.includes(t.name)).slice(0, 5)
    );
  }, [inputVal, allTags, tags]);

  if (!media || media.multiple) return null;

  const addTag = (name: string) => {
    const trimmed = name.trim();
    if (!trimmed || tags.includes(trimmed) || tags.length >= 5) return;
    setTags(prev => [...prev, trimmed]);
    setInputVal('');
    setSuggestions([]);
  };

  const removeTag = (name: string) => setTags(prev => prev.filter(t => t !== name));

  const handleSave = async () => {
    setSaving(true);
    const ok = await onSave(media.id, tags, 'replace');
    setSaving(false);
    if (ok) onClose();
  };

  return (
      <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4" onClick={onClose}>
        <div className="bg-white dark:bg-gray-900 rounded-2xl shadow-2xl p-6 w-full max-w-md" onClick={e => e.stopPropagation()}>
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-bold text-gray-900 dark:text-white">编辑标签</h3>
            <button onClick={onClose} className="p-1 rounded-full hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-400">✕</button>
          </div>
          <p className="text-xs text-gray-500 dark:text-gray-400 mb-3">最多 5 个标签</p>

          {/* 已选标签 */}
          <div className="flex flex-wrap gap-2 mb-3 min-h-[32px] p-2 bg-gray-50 dark:bg-gray-800 rounded-lg">
            {tags.map(tag => (
                <span key={tag}
                      className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300 text-xs font-medium">
                  {tag}
                  <button onClick={() => removeTag(tag)} className="hover:text-red-500">✕</button>
                </span>
            ))}
            {tags.length === 0 && <span className="text-xs text-gray-400">暂无标签，输入添加</span>}
          </div>

          {/* 输入框 + 建议 */}
          <div className="relative mb-4">
            <input ref={inputRef} type="text" value={inputVal}
                   onChange={e => setInputVal(e.target.value)}
                   onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); addTag(inputVal); } }}
                   placeholder="输入标签名称..."
                   className="w-full px-3 py-2 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-purple-500 dark:text-white"
                   disabled={tags.length >= 5}
            />
            {suggestions.length > 0 && (
                <div className="absolute top-full left-0 right-0 mt-1 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl shadow-lg overflow-hidden z-10">
                  {suggestions.map(s => (
                      <button key={s.id} onClick={() => addTag(s.name)}
                              className="w-full px-3 py-2 text-left text-sm hover:bg-gray-50 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300 flex items-center gap-2">
                        <Tag className="w-3 h-3 text-purple-500"/>
                        {s.name}
                      </button>
                  ))}
                </div>
            )}
          </div>

          {/* 快速标签 */}
          {allTags.length > 0 && (
              <div className="mb-4">
                <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">常用标签</p>
                <div className="flex flex-wrap gap-1.5">
                  {allTags.filter(t => !tags.includes(t.name)).slice(0, 10).map(t => (
                      <button key={t.id} onClick={() => addTag(t.name)}
                              className="px-2 py-1 rounded-lg text-xs bg-gray-100 dark:bg-gray-800 hover:bg-purple-100 dark:hover:bg-purple-900/30 text-gray-600 dark:text-gray-400 hover:text-purple-600 transition-colors">
                        {t.name}
                      </button>
                  ))}
                </div>
              </div>
          )}

          <button onClick={handleSave} disabled={saving}
                  className="w-full py-2.5 rounded-xl bg-purple-600 text-white text-sm font-medium hover:bg-purple-700 disabled:opacity-50 transition-colors">
            {saving ? '保存中...' : '保存标签'}
          </button>
        </div>
      </div>
  );
};

/* ========== Batch Tag Dialog ========== */
const BatchTagDialog: React.FC<{
  open: boolean;
  mediaCount: number;
  onClose: () => void;
  onSave: (tag: string) => Promise<void>;
  allTags: {id: string; name: string; count?: number}[];
}> = ({open, mediaCount, onClose, onSave, allTags}) => {
  const [inputVal, setInputVal] = useState('');
  const [saving, setSaving] = useState(false);

  if (!open) return null;

  const handleSave = async () => {
    if (!inputVal.trim()) return;
    setSaving(true);
    await onSave(inputVal.trim());
    setSaving(false);
    onClose();
  };

  return (
      <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4" onClick={onClose}>
        <div className="bg-white dark:bg-gray-900 rounded-2xl shadow-2xl p-6 w-full max-w-sm" onClick={e => e.stopPropagation()}>
          <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-2">批量添加标签</h3>
          <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">将为 {mediaCount} 个文件添加标签</p>

          <input type="text" value={inputVal}
                 onChange={e => setInputVal(e.target.value)}
                 onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); handleSave(); } }}
                 placeholder="输入标签名称..."
                 className="w-full px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-purple-500 dark:bg-gray-800 dark:text-white mb-3"
                 autoFocus
          />

          <div className="flex gap-2">
            <button onClick={onClose}
                    className="flex-1 py-2 rounded-xl border border-gray-200 dark:border-gray-700 text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800">
              取消
            </button>
            <button onClick={handleSave} disabled={saving || !inputVal.trim()}
                    className="flex-1 py-2 rounded-xl bg-purple-600 text-white text-sm font-medium hover:bg-purple-700 disabled:opacity-50 transition-colors">
              {saving ? '添加中...' : '添加标签'}
            </button>
          </div>
        </div>
      </div>
  );
};

/* ========== Category Editor (single media) ========== */
const CategoryEditor: React.FC<{
  media: {id: number; category: string | null; multiple?: boolean} | null;
  allCategories: {id: string; name: string; count?: number}[];
  onClose: () => void;
  onSave: (mediaId: number, category: string | null) => Promise<boolean>;
}> = ({media, allCategories, onClose, onSave}) => {
  const [selected, setSelected] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [customVal, setCustomVal] = useState('');

  useEffect(() => {
    if (media && !media.multiple) {
      setSelected(media.category);
      setCustomVal('');
    }
  }, [media]);

  if (!media || media.multiple) return null;

  const handleSave = async () => {
    const category = selected || customVal.trim() || null;
    setSaving(true);
    const ok = await onSave(media.id, category);
    setSaving(false);
    if (ok) onClose();
  };

  return (
      <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4" onClick={onClose}>
        <div className="bg-white dark:bg-gray-900 rounded-2xl shadow-2xl p-6 w-full max-w-md" onClick={e => e.stopPropagation()}>
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-bold text-gray-900 dark:text-white">设置分类</h3>
            <button onClick={onClose} className="p-1 rounded-full hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-400">✕</button>
          </div>
          <p className="text-xs text-gray-500 dark:text-gray-400 mb-3">一个媒体文件只能属于一个分类</p>

          {/* 已有分类列表 */}
          <div className="flex flex-wrap gap-2 mb-4">
            {allCategories.map(cat => (
                <button key={cat.id}
                        onClick={() => { setSelected(cat.name); setCustomVal(''); }}
                        className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                            selected === cat.name
                                ? 'bg-emerald-600 text-white'
                                : 'bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700'
                        }`}
                >{cat.name}</button>
            ))}
            <button onClick={() => { setSelected(null); setCustomVal(''); }}
                    className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                        selected === null && !customVal
                            ? 'bg-gray-600 text-white'
                            : 'bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:bg-gray-200'
                    }`}>
              无
            </button>
          </div>

          {/* 自定义分类 */}
          <div className="mb-4">
            <label className="text-xs text-gray-500 dark:text-gray-400 mb-1 block">或输入自定义分类</label>
            <input type="text" value={customVal}
                   onChange={e => { setCustomVal(e.target.value); setSelected(null); }}
                   placeholder="输入新分类名称..."
                   className="w-full px-3 py-2 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 dark:text-white"
            />
          </div>

          <button onClick={handleSave} disabled={saving}
                  className="w-full py-2.5 rounded-xl bg-emerald-600 text-white text-sm font-medium hover:bg-emerald-700 disabled:opacity-50 transition-colors">
            {saving ? '保存中...' : '保存分类'}
          </button>
        </div>
      </div>
  );
};

/* ========== Batch Category Dialog ========== */
const BatchCategoryDialog: React.FC<{
  open: boolean;
  mediaCount: number;
  onClose: () => void;
  onSave: (category: string) => Promise<void>;
  allCategories: {id: string; name: string; count?: number}[];
}> = ({open, mediaCount, onClose, onSave, allCategories}) => {
  const [selected, setSelected] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  if (!open) return null;

  const handleSave = async () => {
    if (!selected) return;
    setSaving(true);
    await onSave(selected);
    setSaving(false);
    onClose();
  };

  return (
      <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4" onClick={onClose}>
        <div className="bg-white dark:bg-gray-900 rounded-2xl shadow-2xl p-6 w-full max-w-sm" onClick={e => e.stopPropagation()}>
          <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-2">批量设置分类</h3>
          <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">将为 {mediaCount} 个文件设置分类</p>

          <div className="flex flex-wrap gap-2 mb-4">
            {allCategories.map(cat => (
                <button key={cat.id}
                        onClick={() => setSelected(cat.name)}
                        className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                            selected === cat.name
                                ? 'bg-emerald-600 text-white'
                                : 'bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700'
                        }`}
                >{cat.name}</button>
            ))}
          </div>

          <div className="flex gap-2">
            <button onClick={onClose}
                    className="flex-1 py-2 rounded-xl border border-gray-200 dark:border-gray-700 text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800">
              取消
            </button>
            <button onClick={handleSave} disabled={saving || !selected}
                    className="flex-1 py-2 rounded-xl bg-emerald-600 text-white text-sm font-medium hover:bg-emerald-700 disabled:opacity-50 transition-colors">
              {saving ? '设置中...' : '设置分类'}
            </button>
          </div>
        </div>
      </div>
  );
};

/* ========== Image Crop Dialog ========== */
const _ImageCropDialog: React.FC<{
  open: boolean;
  media: MediaFile | null;
  onClose: () => void;
  onOptimize: (mediaId: number, cropData?: any) => Promise<void>;
}> = ({open, media, onClose, onOptimize}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [crop, setCrop] = useState({x: 0, y: 0, width: 100, height: 100});
  const [processing, setProcessing] = useState(false);

  useEffect(() => {
    if (media && canvasRef.current) {
      const img = new Image();
      img.crossOrigin = 'anonymous';
      img.onload = () => {
        const canvas = canvasRef.current!;
        const ctx = canvas.getContext('2d')!;
        canvas.width = img.width;
        canvas.height = img.height;
        ctx.drawImage(img, 0, 0);
        setCrop({x: 0, y: 0, width: img.width, height: img.height});
      };
      img.src = getFullMediaUrl(media.url);
    }
  }, [media]);

  const handleOptimize = async () => {
    if (!media || !canvasRef.current) return;
    setProcessing(true);
    try {
      // Convert crop to WebP and send to backend
      const canvas = canvasRef.current;
      const blob = await new Promise<Blob>((resolve) => {
        canvas.toBlob((b) => resolve(b!), 'image/webp', 0.8);
      });
      const formData = new FormData();
      formData.append('file', blob, `${media.filename}.webp`);
      formData.append('crop_data', JSON.stringify(crop));

      await onOptimize(media.id, crop);
      onClose();
    } catch (error) {
      console.error('优化失败:', error);
    } finally {
      setProcessing(false);
    }
  };

  if (!open || !media) return null;

  return (
      <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4" onClick={onClose}>
        <div className="bg-white dark:bg-gray-900 rounded-2xl shadow-2xl w-full max-w-4xl max-h-[90vh] flex flex-col"
             onClick={e => e.stopPropagation()}>
          <div className="flex items-center justify-between px-6 py-4 border-b dark:border-gray-700">
            <h3 className="text-lg font-bold text-gray-900 dark:text-white">图像裁剪与优化</h3>
            <button onClick={onClose} className="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-800"><X
                className="w-5 h-5"/></button>
          </div>
          <div className="flex-1 overflow-auto p-6">
            <div className="mb-4">
              <canvas ref={canvasRef} className="max-w-full border rounded-lg"/>
            </div>
            <div className="grid grid-cols-2 gap-4 mb-4">
              <div>
                <label className="text-xs text-gray-500 dark:text-gray-400 mb-1 block">X 坐标</label>
                <input type="number" value={crop.x} onChange={e => setCrop({...crop, x: Number(e.target.value)})}
                       className="w-full px-3 py-2 border rounded-lg"/>
              </div>
              <div>
                <label className="text-xs text-gray-500 dark:text-gray-400 mb-1 block">Y 坐标</label>
                <input type="number" value={crop.y} onChange={e => setCrop({...crop, y: Number(e.target.value)})}
                       className="w-full px-3 py-2 border rounded-lg"/>
              </div>
              <div>
                <label className="text-xs text-gray-500 dark:text-gray-400 mb-1 block">宽度</label>
                <input type="number" value={crop.width}
                       onChange={e => setCrop({...crop, width: Number(e.target.value)})}
                       className="w-full px-3 py-2 border rounded-lg"/>
              </div>
              <div>
                <label className="text-xs text-gray-500 dark:text-gray-400 mb-1 block">高度</label>
                <input type="number" value={crop.height}
                       onChange={e => setCrop({...crop, height: Number(e.target.value)})}
                       className="w-full px-3 py-2 border rounded-lg"/>
              </div>
            </div>
          </div>
          <div className="px-6 py-4 border-t dark:border-gray-700 flex gap-2">
            <button onClick={onClose} className="flex-1 py-2 rounded-xl border text-sm">取消</button>
            <button onClick={handleOptimize} disabled={processing}
                    className="flex-1 py-2 rounded-xl bg-blue-600 text-white text-sm hover:bg-blue-700 disabled:opacity-50">
              {processing ? '优化中...' : '生成 WebP'}
            </button>
          </div>
        </div>
      </div>
  );
};
