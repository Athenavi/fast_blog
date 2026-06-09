import React, {useEffect, useState} from 'react';
import {FileText, FolderClosed, Grid3X3} from 'lucide-react';
import type {MediaFile} from '@/lib/api';
import type {FolderNode} from '@/components/pages/media/FolderTree';
import {getFullMediaUrl} from '@/lib/utils';

/** 预览模态框 */
export const PreviewModal: React.FC<{media: MediaFile|null; onClose: ()=>void}> = ({media, onClose}) => {
  if(!media) return null;
  const fullUrl = getFullMediaUrl(media.url);
  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [onClose]);

  return (<div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80" onClick={onClose}>
    <div className="w-[90vw] max-w-7xl max-h-[95vh] bg-white dark:bg-gray-900 rounded-2xl overflow-hidden shadow-2xl flex flex-col" onClick={e => e.stopPropagation()}>
      {media.mime_type === 'application/pdf' && fullUrl ? (
        <div className="flex-1 bg-gray-100 dark:bg-gray-800 min-h-[80vh]">
          <embed src={fullUrl} type="application/pdf" className="w-full h-full" style={{minHeight: '80vh', maxHeight: '85vh'}}/>
        </div>
      ) : media.mime_type?.startsWith('video/') && fullUrl ? (
        <div className="bg-black flex-1 flex items-center justify-center">
          <video src={fullUrl} controls autoPlay preload="auto" className="max-w-full max-h-[85vh] w-full h-full object-contain" playsInline/>
        </div>
      ) : media.mime_type?.startsWith('image/') && fullUrl ? (
        <img src={fullUrl} alt={media.original_filename} className="max-w-full max-h-[70vh] object-contain" loading="eager" decoding="async"/>
      ) : (
        <div className="p-16 text-center"><FileText className="w-16 h-16 text-gray-400 mx-auto mb-4"/><p className="text-gray-600">{media.original_filename}</p></div>
      )}
      <div className="p-6 border-t border-gray-200 dark:border-gray-700 flex-shrink-0">
        <h3 className="font-bold text-gray-900 dark:text-white">{media.original_filename}</h3>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">{media.file_size ? `${(media.file_size / 1024).toFixed(1)} KB` : ''} · {media.mime_type}</p>
      </div>
    </div>
  </div>);
};

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
  const renderNode = (node: FolderNode, depth=0) => (
    <button key={node.id} onClick={()=>onMove(node.name)} className="w-full flex items-center gap-3 px-4 py-3 text-left rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-blue-50 dark:hover:bg-blue-900/20 hover:border-blue-500 transition-colors" style={{paddingLeft:`${16+depth*20}px`}}>
      <FolderClosed className="w-5 h-5 text-yellow-600"/> <span className="font-medium">{node.name}</span>
    </button>
  );
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
