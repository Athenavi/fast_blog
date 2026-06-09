import React, {useEffect} from 'react';
import {FileText} from 'lucide-react';
import type {MediaFile} from '@/lib/api';
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
