'use client';

import React, {useState} from 'react';
import {useQuery, useMutation} from '@tanstack/react-query';
import {apiClient} from '@/lib/api';
import {History, RotateCcw, Clock, User, FileText, X} from 'lucide-react';

interface Revision {
  id: number; revision_number: number; title: string; excerpt: string; content: string;
  change_summary: string | null; created_at: string; author?: {username: string};
}

export const RevisionsSidebar: React.FC<{
  articleId: number | string; open: boolean; onClose: () => void;
  onRestore: (content: string, title: string, excerpt: string) => void;
}> = ({articleId, open, onClose, onRestore}) => {
  const [selected, setSelected] = useState<Revision | null>(null);
  const [previewContent, setPreviewContent] = useState<string | null>(null);

  const {data: revisions, isLoading} = useQuery({
    queryKey: ['revisions', articleId],
    enabled: open && !!articleId,
    queryFn: async () => {
      const res = await apiClient.get<Revision[]>(`/articles/${articleId}/revisions`);
      return res.success && res.data ? (Array.isArray(res.data) ? res.data : (res.data as any).revisions || []) : [];
    },
  });

  const rollbackMut = useMutation({
    mutationFn: async (revId: number) => {
      const res = await apiClient.post(`/articles/${articleId}/revisions/${revId}/rollback`);
      return res;
    },
    onSuccess: (res) => {
      if (res.success && selected) {
        onRestore(selected.content, selected.title, selected.excerpt);
        onClose();
      }
    },
  });

  const viewRevision = async (rev: Revision) => {
    setSelected(rev);
    try {
      const res = await apiClient.get<any>(`/articles/revisions/${rev.id}`);
      if (res.success && res.data) {
        setPreviewContent(res.data.content || rev.content);
      } else setPreviewContent(rev.content);
    } catch { setPreviewContent(rev.content); }
  };

  if (!open) return null;

  return (
    <div className="fixed inset-y-0 right-0 z-50 w-96 bg-white dark:bg-gray-900 border-l border-gray-200 dark:border-gray-700 shadow-xl flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center gap-2"><History className="w-5 h-5 text-gray-600 dark:text-gray-300"/><h2 className="font-bold text-gray-900 dark:text-white">版本历史</h2></div>
        <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800"><X className="w-5 h-5"/></button>
      </div>

      <div className="flex-1 overflow-hidden flex">
        {/* Revisions list */}
        <div className={`${selected ? 'w-1/2' : 'flex-1'} overflow-y-auto p-4 space-y-2`}>
          {isLoading ? (
            <div className="space-y-3">{[1,2,3].map(i => <div key={i} className="h-16 bg-gray-100 dark:bg-gray-800 rounded-lg animate-pulse"/>)}</div>
          ) : !revisions?.length ? (
            <div className="text-center py-8 text-gray-400"><FileText className="w-10 h-10 mx-auto mb-2 opacity-50"/><p className="text-sm">暂无版本记录</p></div>
          ) : revisions.map((rev) => (
            <button key={rev.id} onClick={() => viewRevision(rev)}
              className={`w-full text-left p-3 rounded-xl border transition-colors ${selected?.id === rev.id ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20' : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'}`}>
              <div className="flex items-center gap-2 text-sm font-medium text-gray-900 dark:text-white">
                <Clock className="w-3.5 h-3.5 text-gray-400"/> v{rev.revision_number}
                <span className="text-xs text-gray-500">{new Date(rev.created_at).toLocaleString('zh-CN')}</span>
              </div>
              {rev.change_summary && <p className="text-xs text-gray-500 mt-1 line-clamp-1">{rev.change_summary}</p>}
              {rev.author && <p className="text-xs text-gray-400 mt-1"><User className="w-3 h-3 inline mr-0.5"/>{rev.author.username}</p>}
            </button>
          ))}
        </div>

        {/* Preview panel */}
        {selected && (
          <div className="w-1/2 border-l border-gray-200 dark:border-gray-700 flex flex-col">
            <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800">
              <span className="text-sm font-medium">v{selected.revision_number}</span>
              <div className="flex gap-1">
                <button onClick={() => {if(confirm('确定回滚到此版本？')) rollbackMut.mutate(selected.id);}}
                  className="px-3 py-1.5 text-xs bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center gap-1">
                  <RotateCcw className="w-3 h-3"/>回滚
                </button>
              </div>
            </div>
            <div className="flex-1 overflow-y-auto p-4">
              <h3 className="font-bold text-gray-900 dark:text-white mb-2">{selected.title}</h3>
              {selected.excerpt && <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">{selected.excerpt}</p>}
              <div className="prose prose-sm dark:prose-invert max-w-none" dangerouslySetInnerHTML={{__html: previewContent || selected.content}} />
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default RevisionsSidebar;
