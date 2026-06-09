import React, {useRef, useState} from 'react';
import {Upload, ChevronDown, ChevronRight} from 'lucide-react';

export const UploadArea: React.FC<{onUpload: (files: File[]) => void; uploading: boolean; progress: number; status: string; collapsed: boolean; onToggle: () => void}> = ({onUpload, uploading, progress, status, collapsed, onToggle}) => {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);
  return (<div className="mb-6">
    <button onClick={onToggle} className="flex items-center gap-2 text-sm font-medium text-gray-600 dark:text-gray-400 mb-3">
      {collapsed ? <ChevronRight className="w-4 h-4"/> : <ChevronDown className="w-4 h-4"/>} 上传文件
    </button>
    {!collapsed && (<div onDragOver={e => {e.preventDefault(); setDragOver(true);}} onDragLeave={() => setDragOver(false)} onDrop={e => {e.preventDefault(); setDragOver(false); if (e.dataTransfer.files.length) onUpload(Array.from(e.dataTransfer.files));}}
      className={`border-2 border-dashed rounded-2xl p-8 text-center transition-colors cursor-pointer ${dragOver ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20' : 'border-gray-300 dark:border-gray-700 hover:border-blue-400'}`}
      onClick={() => inputRef.current?.click()}>
      <Upload className="w-10 h-10 text-gray-400 mx-auto mb-3"/>
      <p className="text-gray-600 dark:text-gray-400 font-medium">{uploading ? '上传中...' : '拖拽文件到此处或点击上传'}</p>
      <input ref={inputRef} type="file" multiple onChange={e => {if (e.target.files?.length) onUpload(Array.from(e.target.files));}} className="hidden"/>
      {uploading && <div className="mt-4">
        <div className="w-full bg-gray-200 rounded-full h-2">
          <div className="bg-blue-600 h-2 rounded-full transition-all" style={{width: `${progress}%`}}/>
        </div>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">{status}</p></div>}
    </div>)}
  </div>);
};