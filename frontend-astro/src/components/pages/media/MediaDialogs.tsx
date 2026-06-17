import React, {useState, useEffect} from 'react';
import {FolderClosed, Grid3X3} from 'lucide-react';
import type {MediaFile} from '@/lib/api';
import type {FolderNode} from '@/components/pages/media/FolderTree';

/** 确认删除对话框 */
export const DeleteConfirm: React.FC<{item: MediaFile; onCancel: ()=>void; onConfirm: ()=>void}> = ({item, onCancel, onConfirm}) => (
  <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4" onClick={onCancel}>
    <div className="bg-white dark:bg-gray-900 rounded-2xl p-6 max-w-sm w-full shadow-xl" onClick={e=>e.stopPropagation()}>
      <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-2">确认删除</h3>
      <p className="text-sm text-gray-500 dark:text-gray-400 mb-6">确定要删除 <span className="font-medium">{item.original_filename}</span> 吗？</p>
      <div className="flex justify-end gap-3">
        <button onClick={onCancel} className="px-4 py-2 bg-gray-100 dark:bg-gray-800 rounded-lg text-sm font-medium">取消</button>
        <button onClick={onConfirm} className="px-4 py-2 bg-red-600 text-white rounded-lg text-sm font-medium hover:bg-red-700">删除</button>
      </div>
    </div>
  </div>
);

/** 移动文件对话框 */
export const MoveDialog: React.FC<{open: boolean; onClose: ()=>void; folders: FolderNode[]; mediaCount: number; onMove: (folderPath: string|null)=>void}> = ({open, onClose, folders, mediaCount, onMove}) => {
  if(!open) return null;
  const renderNode = (node: FolderNode, depth=0, parentPath='') => {
    const currentPath = parentPath ? `${parentPath}/${node.name}` : node.name;
    const children = (node as any).children;
    return (
      <div key={node.id}>
        <button onClick={()=>onMove(currentPath)} className="w-full flex items-center gap-3 px-4 py-3 text-left rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-blue-50 dark:hover:bg-blue-900/20 hover:border-blue-500 transition-colors" style={{paddingLeft:`${16+depth*20}px`}}>
          <FolderClosed className="w-5 h-5 text-yellow-600"/> <span className="font-medium">{node.name}</span>
        </button>
        {Array.isArray(children) && children.map((child: FolderNode) => renderNode(child, depth + 1, currentPath))}
      </div>
    );
  };
  return (<div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4" onClick={onClose}>
    <div className="bg-white dark:bg-gray-900 rounded-2xl p-6 max-w-md w-full shadow-xl" onClick={e=>e.stopPropagation()}>
      <h3 className="text-lg font-bold mb-2">移动文件</h3>
      <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">将选中的 {mediaCount} 个文件移动到：</p>
      <div className="space-y-2 max-h-64 overflow-y-auto mb-4">
        <button onClick={()=>onMove(null)} className="w-full flex items-center gap-3 px-4 py-3 text-left rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-blue-50 dark:hover:bg-blue-900/20 hover:border-blue-500 transition-colors">
          <Grid3X3 className="w-5 h-5 text-gray-500 dark:text-gray-400"/><span className="font-medium">根目录</span>
        </button>
        {folders.map(n=>renderNode(n))}
      </div>
      <div className="flex justify-end"><button onClick={onClose} className="px-4 py-2 bg-gray-100 dark:bg-gray-800 rounded-lg text-sm font-medium">取消</button></div>
    </div>
  </div>);
};

/** 新建文件夹对话框 */
export const CreateFolderDialog: React.FC<{open: boolean; onClose: ()=>void; onCreate: (name: string)=>void}> = ({open, onClose, onCreate}) => {
  const [name, setName] = useState('');
  if(!open) return null;
  return (<div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4" onClick={onClose}>
    <div className="bg-white dark:bg-gray-900 rounded-2xl p-6 max-w-sm w-full shadow-xl" onClick={e=>e.stopPropagation()}>
      <h3 className="text-lg font-bold mb-4">新建文件夹</h3>
      <input type="text" value={name} onChange={e=>setName(e.target.value)} placeholder="文件夹名称" className="w-full px-4 py-3 border border-gray-200 dark:border-gray-700 rounded-xl bg-gray-50 dark:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white mb-4" autoFocus onKeyDown={e=>{if(e.key==='Enter' && name.trim()) {onCreate(name.trim()); setName('');}}}/>
      <div className="flex justify-end gap-3"><button onClick={onClose} className="px-4 py-2 bg-gray-100 dark:bg-gray-800 rounded-lg text-sm font-medium">取消</button><button onClick={()=>{if(name.trim()){onCreate(name.trim()); setName('');}}} className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700">创建</button></div>
    </div>
  </div>);
};

/** 标签编辑对话框 */
export const TagEditorDialog: React.FC<{
  open: boolean; media: MediaFile | null;
  onClose: () => void;
  onSave: (mediaId: number, tags: string[]) => Promise<void>;
}> = ({open, media, onClose, onSave}) => {
  const [tags, setTags] = useState<string[]>([]);
  const [input, setInput] = useState('');
  const [saving, setSaving] = useState(false);
  useEffect(() => {
    if (open && media) {
      const existing = (media as any).tags ? String((media as any).tags).split(',').map((t: string) => t.trim()).filter(Boolean) : [];
      setTags(existing);
      setInput('');
    }
  }, [open, media]);
  if (!open || !media) return null;
  const addTag = () => {
    const t = input.trim();
    if (t && !tags.includes(t)) {
      if (tags.length >= 5) return;
      setTags([...tags, t]);
    }
    setInput('');
  };
  const removeTag = (t: string) => setTags(tags.filter(x => x !== t));
  return (<div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4" onClick={onClose}>
    <div className="bg-white dark:bg-gray-900 rounded-2xl p-6 max-w-sm w-full shadow-xl" onClick={e=>e.stopPropagation()}>
      <h3 className="text-lg font-bold mb-1">编辑标签</h3>
      <p className="text-xs text-gray-400 mb-4">{media.original_filename}（最多 5 个标签）</p>
      <div className="flex gap-2 mb-3">
        <input value={input} onChange={e=>setInput(e.target.value)} onKeyDown={e=>{if(e.key==='Enter')addTag()}} placeholder="输入标签" maxLength={30} className="flex-1 px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-xl bg-gray-50 dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white"/>
        <button onClick={addTag} disabled={tags.length>=5} className="px-3 py-2 bg-purple-600 text-white text-sm rounded-xl hover:bg-purple-700 disabled:opacity-40">添加</button>
      </div>
      <div className="flex flex-wrap gap-1.5 mb-5 min-h-[28px] p-2 border border-dashed border-gray-200 dark:border-gray-700 rounded-xl bg-gray-50/50 dark:bg-gray-800/50">
        {tags.length === 0 && <span className="text-xs text-gray-400">暂无标签</span>}
        {tags.map(t => (
          <span key={t} className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300 text-xs">
            {t}<button onClick={()=>removeTag(t)} className="hover:text-red-500">&times;</button>
          </span>
        ))}
      </div>
      <div className="flex justify-end gap-3">
        <button onClick={onClose} className="px-4 py-2 bg-gray-100 dark:bg-gray-800 rounded-lg text-sm font-medium">取消</button>
        <button onClick={async()=>{setSaving(true); try{await onSave(media.id, tags); onClose();}finally{setSaving(false);}}} disabled={saving} className="px-4 py-2 bg-purple-600 text-white rounded-lg text-sm font-medium hover:bg-purple-700 disabled:opacity-50">
          {saving ? '保存中...' : '保存'}
        </button>
      </div>
    </div>
  </div>);
};

/** 批量标签对话框 */
export const BatchTagDialog: React.FC<{
  open: boolean; onClose: () => void;
  onSave: (tags: string[]) => Promise<void>;
  saving: boolean;
}> = ({open, onClose, onSave, saving}) => {
  const [tags, setTags] = useState<string[]>([]);
  const [input, setInput] = useState('');
  if (!open) return null;
  const addTag = () => {
    const t = input.trim();
    if (t && !tags.includes(t)) { setTags([...tags, t]); }
    setInput('');
  };
  const removeTag = (t: string) => setTags(tags.filter(x => x !== t));
  return (<div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4" onClick={onClose}>
    <div className="bg-white dark:bg-gray-900 rounded-2xl p-6 max-w-sm w-full shadow-xl" onClick={e=>e.stopPropagation()}>
      <h3 className="text-lg font-bold mb-1">批量设置标签</h3>
      <p className="text-xs text-gray-400 mb-4">将替换所有选中文件的标签（最多 5 个）</p>
      <div className="flex gap-2 mb-3">
        <input value={input} onChange={e=>setInput(e.target.value)} onKeyDown={e=>{if(e.key==='Enter')addTag()}} placeholder="输入标签" maxLength={30} className="flex-1 px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-xl bg-gray-50 dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500 dark:text-white"/>
        <button onClick={addTag} disabled={tags.length>=5} className="px-3 py-2 bg-purple-600 text-white text-sm rounded-xl hover:bg-purple-700 disabled:opacity-40">添加</button>
      </div>
      <div className="flex flex-wrap gap-1.5 mb-5 min-h-[28px] p-2 border border-dashed border-gray-200 dark:border-gray-700 rounded-xl bg-gray-50/50 dark:bg-gray-800/50">
        {tags.length === 0 && <span className="text-xs text-gray-400">尚未添加标签</span>}
        {tags.map(t => (
          <span key={t} className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300 text-xs">
            {t}<button onClick={()=>removeTag(t)} className="hover:text-red-500">&times;</button>
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
  </div>);
};

/** 分类编辑对话框（单选） */
export const CategoryEditorDialog: React.FC<{
  open: boolean; media: MediaFile | null;
  categories: string[];
  onClose: () => void;
  onSave: (mediaId: number, category: string) => Promise<void>;
}> = ({open, media, categories, onClose, onSave}) => {
  const [category, setCategory] = useState('');
  const [custom, setCustom] = useState('');
  const [showCustom, setShowCustom] = useState(false);
  const [saving, setSaving] = useState(false);
  useEffect(() => {
    if (open && media) {
      const cur = String((media as any).category || '');
      if (categories.includes(cur)) { setCategory(cur); setShowCustom(false); }
      else { setCategory(''); setCustom(cur); setShowCustom(true); }
    }
  }, [open, media, categories]);
  if (!open || !media) return null;
  const finalCategory = showCustom ? custom.trim() : category;
  return (<div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4" onClick={onClose}>
    <div className="bg-white dark:bg-gray-900 rounded-2xl p-6 max-w-sm w-full shadow-xl" onClick={e=>e.stopPropagation()}>
      <h3 className="text-lg font-bold mb-1">设置分类</h3>
      <p className="text-xs text-gray-400 mb-4">{media.original_filename}（每张图片仅一个分类）</p>
      <div className="space-y-2 mb-4 max-h-40 overflow-y-auto">
        {categories.length === 0 && <p className="text-xs text-gray-400">暂无可用分类，请在下方的输入框中输入新分类名称</p>}
        {!showCustom && categories.map(c => (
          <label key={c} className="flex items-center gap-2 p-2 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 cursor-pointer">
            <input type="radio" name="media-category" checked={category === c} onChange={()=>setCategory(c)} className="text-emerald-600"/>
            <span className="text-sm">{c}</span>
          </label>
        ))}
      </div>
      <div className="flex items-center gap-2 mb-4">
        <input type="checkbox" checked={showCustom} onChange={e => { setShowCustom(e.target.checked); if (!e.target.checked) setCustom(''); }} className="text-emerald-600" id="custom-cat"/>
        <label htmlFor="custom-cat" className="text-xs text-gray-500">自定义分类</label>
      </div>
      {showCustom && (
        <input value={custom} onChange={e=>setCustom(e.target.value)} placeholder="输入新分类名称" maxLength={50} className="w-full px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-xl bg-gray-50 dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 dark:text-white mb-4"/>
      )}
      <div className="flex justify-end gap-3">
        <button onClick={onClose} className="px-4 py-2 bg-gray-100 dark:bg-gray-800 rounded-lg text-sm font-medium">取消</button>
        <button onClick={async()=>{if(!finalCategory) return; setSaving(true); try{await onSave(media.id, finalCategory); onClose();}finally{setSaving(false);}}} disabled={saving || !finalCategory} className="px-4 py-2 bg-emerald-600 text-white rounded-lg text-sm font-medium hover:bg-emerald-700 disabled:opacity-50">
          {saving ? '保存中...' : '保存'}
        </button>
      </div>
    </div>
  </div>);
};
