import React, {useState} from 'react';
import {FileText, ImageIcon, Music, Tag, Video} from 'lucide-react';
import type {MediaFile} from '@/lib/api';
import {getFullMediaUrl} from '@/lib/utils';

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  return `${(bytes / 1024).toFixed(1)} KB`;
}

function groupByCategory(files: MediaFile[]): Map<string, MediaFile[]> {
  const groups = new Map<string, MediaFile[]>();
  for (const f of files) {
    const key = (f as any).category || '\0未分类';
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key)!.push(f);
  }
  return groups;
}

export const MediaGrid: React.FC<{
  files: MediaFile[]; loading: boolean; viewMode: 'grid'|'list';
  selected: number[]; onSelect: (id: number) => void;
  onPreview: (m: MediaFile) => void; onDelete: (m: MediaFile) => void;
  onEditTags?: (m: MediaFile) => void; onEditCategory?: (m: MediaFile) => void;
}> = ({files, loading, viewMode, selected, onSelect, onPreview, onDelete, onEditTags, onEditCategory}) => {
  const [groupCollapsed, setGroupCollapsed] = useState<Set<string>>(new Set());
  const [allExpanded, setAllExpanded] = useState(true);

  if (loading) return <div className="p-12 text-center"><div className="animate-spin w-8 h-8 border-2 border-blue-600 border-t-transparent rounded-full mx-auto"/></div>;
  if (!files.length) return <div className="p-12 text-center text-gray-400"><ImageIcon className="w-12 h-12 mx-auto mb-3 opacity-50"/><p>暂无媒体文件</p></div>;

  const getIcon = (m: string) => m?.startsWith('video/') ? Video : m?.startsWith('audio/') ? Music : FileText;

  const groups = groupByCategory(files);

  const toggleGroup = (key: string) => {
    setGroupCollapsed(prev => {
      const next = new Set(prev);
      next.has(key) ? next.delete(key) : next.add(key);
      return next;
    });
  };

  const expandAll = () => { setGroupCollapsed(new Set()); setAllExpanded(true); };
  const collapseAll = () => {
    const all = new Set<string>();
    for (const k of groups.keys()) all.add(k);
    setGroupCollapsed(all); setAllExpanded(false);
  };

  const selectGroup = (items: MediaFile[]) => {
    const allSelected = items.every(f => selected.includes(f.id));
    items.forEach(f => { if (allSelected) { onSelect(f.id); onSelect(f.id); } else { onSelect(f.id); } });
  };

  const renderListItem = (f: MediaFile) => {
    const isPDF = f.mime_type === 'application/pdf';
    const tags = (f as any).tags ? String((f as any).tags).split(',').map((t: string) => t.trim()).filter(Boolean) : [];
    return (
      <tr key={f.id} className={`hover:bg-gray-50 dark:hover:bg-gray-800 ${selected.includes(f.id)?'bg-blue-50 dark:bg-blue-900/20':''}`}>
        <td className="px-4"><input type="checkbox" checked={selected.includes(f.id)} onChange={() => onSelect(f.id)} className="h-4 w-4 text-blue-600 rounded"/></td>
        <td className="py-2 cursor-pointer" onClick={() => onPreview(f)}>
          <div className="flex items-center gap-3">
            {f.mime_type?.startsWith('image/') && (f.thumbnail_url || f.url) ? (
              <img src={getFullMediaUrl(f.thumbnail_url || f.url)} alt={f.original_filename} className="w-10 h-10 rounded-lg object-cover" loading="lazy" decoding="async"/>
            ) : f.mime_type?.startsWith('video/') && f.url ? (
              <div className="w-10 h-10 rounded-lg bg-gray-900 flex items-center justify-center relative">
                <Video className="w-5 h-5 text-white"/>
                <div className="absolute inset-0 flex items-center justify-center">
                  <div className="w-4 h-4 bg-white/80 rounded-full flex items-center justify-center">
                    <div className="w-0 h-0 border-t-[3px] border-t-transparent border-l-[6px] border-l-black border-b-[3px] border-b-transparent ml-0.5"/>
                  </div>
                </div>
              </div>
            ) : isPDF ? (
              <div className="w-10 h-10 rounded-lg bg-red-50 dark:bg-red-900/10 flex items-center justify-center"><FileText className="w-5 h-5 text-red-500"/></div>
            ) : (
              <div className="w-10 h-10 rounded-lg bg-gray-100 dark:bg-gray-700 flex items-center justify-center">{React.createElement(getIcon(f.mime_type || ''), {className: 'w-5 h-5 text-gray-400'})}</div>
            )}
            <div className="min-w-0">
              <p className="text-sm font-medium text-gray-900 dark:text-white truncate max-w-[180px]">{f.original_filename}</p>
              <div className="flex items-center gap-1.5 mt-0.5 flex-wrap">
                {(f as any).category && <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400 font-medium">{String((f as any).category)}</span>}
                {tags.slice(0, 3).map(t => <span key={t} className="text-[10px] px-1.5 py-0.5 rounded-full bg-purple-100 dark:bg-purple-900/30 text-purple-600 dark:text-purple-400">{t}</span>)}
                {tags.length > 3 && <span className="text-[10px] text-gray-400">+{tags.length - 3}</span>}
              </div>
            </div>
          </div>
        </td>
        <td className="px-2"><span className="text-xs text-gray-500">{f.mime_type?.split('/')[0]}</span></td>
        <td className="px-2"><span className="text-xs text-gray-400">{f.file_size ? `${(f.file_size / 1024).toFixed(1)} KB` : ''}</span></td>
        <td className="px-2"><span className="text-xs text-gray-400">{f.created_at ? new Date(f.created_at).toLocaleDateString() : ''}</span></td>
        <td className="px-2 text-right">
          <div className="flex items-center justify-end gap-1">
            {onEditCategory && <button onClick={(e) => { e.stopPropagation(); onEditCategory(f); }} className="p-1 hover:bg-emerald-50 dark:hover:bg-emerald-900/20 rounded text-gray-400 hover:text-emerald-600" title="设置分类"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-3.5 h-3.5"><path d="M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z"/></svg></button>}
            {onEditTags && <button onClick={(e) => { e.stopPropagation(); onEditTags(f); }} className="p-1 hover:bg-purple-50 dark:hover:bg-purple-900/20 rounded text-gray-400 hover:text-purple-600" title="编辑标签"><Tag className="w-3.5 h-3.5"/></button>}
            <button onClick={(e) => { e.stopPropagation(); onPreview(f); }} className="p-1 hover:bg-gray-100 dark:hover:bg-gray-800 rounded text-gray-400 hover:text-blue-600" title="预览"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-3.5 h-3.5"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg></button>
            <button onClick={(e) => { e.stopPropagation(); onDelete(f); }} className="p-1 hover:bg-red-50 dark:hover:bg-red-900/20 rounded text-gray-400 hover:text-red-500" title="删除"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-3.5 h-3.5"><path d="M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6M8 6V4a2 2 0 012-2h4a2 2 0 012 2v2"/></svg></button>
          </div>
        </td>
      </tr>
    );
  };

  const renderGridItem = (f: MediaFile) => {
    const tags = (f as any).tags ? String((f as any).tags).split(',').map((t: string) => t.trim()).filter(Boolean) : [];
    return (
    <div key={f.id} className={`group relative aspect-square rounded-xl overflow-hidden border-2 cursor-pointer transition-all ${
      selected.includes(f.id) ? 'border-blue-500 shadow-md' : 'border-gray-200 dark:border-gray-700 hover:border-blue-300 dark:hover:border-blue-700'
    }`}>
      <div onClick={() => onPreview(f)} className="w-full h-full">
        {f.mime_type?.startsWith('image/') && (f.thumbnail_url || f.url) ? (
          <img src={getFullMediaUrl(f.thumbnail_url || f.url)} alt={f.original_filename} className="w-full h-full object-cover" loading="lazy" decoding="async"/>
        ) : f.mime_type?.startsWith('video/') && f.url ? (
          <video src={getFullMediaUrl(f.url)} preload="metadata" muted playsInline className="w-full h-full object-cover"/>
        ) : (
          <div className="w-full h-full flex items-center justify-center bg-gray-50 dark:bg-gray-800">
            {React.createElement(getIcon(f.mime_type || ''), {className: 'w-10 h-10 text-gray-300'})}
          </div>
        )}
      </div>
      {/* Category & Tags overlay */}
      <div className="absolute top-2 left-2 right-2 flex flex-wrap gap-1 pointer-events-none">
        {(f as any).category && <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-emerald-600/80 text-white font-medium">{String((f as any).category)}</span>}
        {tags.slice(0, 2).map(t => <span key={t} className="text-[10px] px-1.5 py-0.5 rounded-full bg-purple-600/70 text-white">{t}</span>)}
      </div>
      {/* Bottom overlay */}
      <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/70 to-transparent p-2 pt-5">
        <p className="text-white text-xs font-medium truncate">{f.original_filename}</p>
        <p className="text-white/60 text-[10px]">{f.file_size ? formatSize(f.file_size) : ''}</p>
      </div>
      {/* Action buttons */}
      <div className="absolute top-2 right-2 flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none">
        <div className="pointer-events-auto">
          {onEditCategory && <button onClick={(e) => { e.stopPropagation(); onEditCategory(f); }} className="p-1 rounded bg-black/50 hover:bg-emerald-600/80 text-white" title="设置分类"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-3 h-3"><path d="M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z"/></svg></button>}
        </div>
        <div className="pointer-events-auto">
          {onEditTags && <button onClick={(e) => { e.stopPropagation(); onEditTags(f); }} className="p-1 rounded bg-black/50 hover:bg-purple-600/80 text-white" title="编辑标签"><Tag className="w-3 h-3"/></button>}
        </div>
      </div>
      <input type="checkbox" checked={selected.includes(f.id)} onChange={(e) => { e.stopPropagation(); onSelect(f.id); }}
        className="absolute top-2 left-2 h-4 w-4 text-blue-600 rounded opacity-0 group-hover:opacity-100 transition-opacity"/>
    </div>
  );
  };

  const renderGroupHeader = (key: string, label: string, items: MediaFile[]) => {
    const collapsed = groupCollapsed.has(key);
    const groupSelectedAll = items.every(f => selected.includes(f.id));
    return (
      <div key={key} className="mb-4">
        <div className="flex items-center gap-2 mb-2">
          <button onClick={() => toggleGroup(key)} className="p-1 hover:bg-gray-100 dark:hover:bg-gray-800 rounded">
            {collapsed ? <span className="text-gray-400">▶</span> : <span className="text-gray-400">▼</span>
}</button>
          <span className="text-sm font-semibold text-gray-700 dark:text-gray-300">{label}</span>
          <span className="text-xs text-gray-400">({items.length})</span>
        </div>
        {!collapsed && (viewMode === 'list' ? (
          <table className="w-full">
            <tbody>{items.map(f => renderListItem(f))}</tbody>
          </table>
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-3">
            {items.map(f => renderGridItem(f))}
          </div>
        ))}
      </div>
    );
  };

  // Ungrouped view (no categories)
  if (groups.size <= 1 && groups.has('\0未分类')) {
    return viewMode === 'list' ? (
      <table className="w-full">
        <thead>
          <tr className="text-xs text-gray-400 uppercase border-b dark:border-gray-700">
            <th className="px-4 py-2 text-left w-8"/>
            <th className="px-2 py-2 text-left">文件</th><th className="px-2 py-2 text-left">类型</th>
            <th className="px-2 py-2 text-left">大小</th><th className="px-2 py-2 text-left">日期</th><th className="px-2 py-2 text-right">操作</th>
          </tr>
        </thead>
        <tbody>{files.map(f => renderListItem(f))}</tbody>
      </table>
    ) : (
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-3">
        {files.map(f => renderGridItem(f))}
      </div>
    );
  }

  // Grouped view
  return (
    <div className="space-y-2">
      <div className="flex gap-2 mb-4">
        <button onClick={expandAll} className="text-xs px-2 py-1 bg-gray-100 dark:bg-gray-800 rounded hover:bg-gray-200">全部展开</button>
        <button onClick={collapseAll} className="text-xs px-2 py-1 bg-gray-100 dark:bg-gray-800 rounded hover:bg-gray-200">全部折叠</button>
      </div>
      {Array.from(groups.entries()).map(([key, items]) => renderGroupHeader(key, key === '\0未分类' ? '未分类' : key, items))}
    </div>
  );
};
