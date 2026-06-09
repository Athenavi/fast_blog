import React, {useState} from 'react';
import {ChevronDown, ChevronRight, FolderClosed, FolderOpen, Grid3X3, Plus, X} from 'lucide-react';

export interface FolderNode {
  id: number; name: string; children?: FolderNode[];
}

export const FolderTree: React.FC<{
  folders: FolderNode[]; selectedId: number | null; onSelect: (f: FolderNode | null) => void;
  onCreate: () => void; onDelete: (id: number) => void; loading: boolean;
}> = ({folders, selectedId, onSelect, onCreate, onDelete, loading}) => {
  const [expanded, setExpanded] = useState<Set<number>>(new Set());

  const toggle = (id: number) => {
    const s = new Set(expanded);
    s.has(id) ? s.delete(id) : s.add(id);
    setExpanded(s);
  };

  const renderNode = (node: FolderNode, depth: number = 0) => (
    <div key={node.id}>
      <div className={`group flex items-center gap-1 px-2 py-1.5 rounded-lg cursor-pointer text-sm transition-colors ${
        selectedId === node.id ? 'bg-blue-50 text-blue-700 dark:bg-blue-900/20 dark:text-blue-400' : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800'
      }`} style={{paddingLeft: `${12 + depth * 16}px`}}>
        <button onClick={() => toggle(node.id)} className="p-0.5 hover:bg-gray-200 dark:hover:bg-gray-700 rounded">
          {node.children?.length ? (expanded.has(node.id) ? <ChevronDown className="w-3.5 h-3.5"/> : <ChevronRight className="w-3.5 h-3.5"/>) : <span className="w-3.5"/>}
        </button>
        <div className="flex-1 flex items-center gap-1.5" onClick={() => onSelect(node)}>
          {expanded.has(node.id) ? <FolderOpen className="w-4 h-4 text-yellow-500"/> : <FolderClosed className="w-4 h-4 text-yellow-600"/>}
          <span className="truncate">{node.name}</span>
        </div>
        <button onClick={e => {e.stopPropagation(); onDelete(node.id);}} className="opacity-0 group-hover:opacity-100 p-0.5 hover:bg-red-100 dark:hover:bg-red-900/30 rounded text-gray-400 hover:text-red-500"><X className="w-3 h-3"/></button>
      </div>
      {expanded.has(node.id) && node.children?.map(child => renderNode(child, depth + 1))}
    </div>
  );

  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-sm font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">文件夹</h3>
        <button onClick={onCreate} className="p-1 hover:bg-gray-100 dark:hover:bg-gray-800 rounded text-gray-400 hover:text-blue-600"><Plus className="w-4 h-4"/></button>
      </div>
      {loading ? (
        <div className="space-y-2">{[1,2,3].map(i => <div key={i} className="h-8 bg-gray-100 dark:bg-gray-800 rounded-lg animate-pulse"/>)}</div>
      ) : (
        <div className="space-y-0.5">
          <div onClick={() => onSelect(null)}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg cursor-pointer text-sm transition-colors ${selectedId === null ? 'bg-blue-50 text-blue-700 dark:bg-blue-900/20 dark:text-blue-400' : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800'}`}>
            <Grid3X3 className="w-4 h-4"/><span>全部文件</span>
          </div>
          {folders.map(n => renderNode(n))}
        </div>
      )}
    </div>
  );
};
