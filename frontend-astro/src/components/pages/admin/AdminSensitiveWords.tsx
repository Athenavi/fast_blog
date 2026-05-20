'use client';

import React, {useState} from 'react';
import {useQuery, useMutation, useQueryClient} from '@tanstack/react-query';
import {AuthGuard} from '@/components/AuthGuard';
import {QueryProvider} from '@/components/QueryProvider';
import {AdminShell} from '@/components/admin/AdminShell';
import {apiClient} from '@/lib/api/base-client';
import {Trash2, Plus, AlertTriangle, RefreshCw} from 'lucide-react';

function SensitiveWordsInner() {
  const qc = useQueryClient();
  const [word, setWord] = useState('');
  const {data: words, isLoading} = useQuery({
    queryKey: ['admin-sensitive-words'],
    queryFn: async () => {
      const res = await apiClient.get<any[]>('/security/sensitive-words/');
      return res.success && res.data ? (Array.isArray(res.data) ? res.data : []) : [];
    },
  });
  const {data: stats} = useQuery({
    queryKey: ['admin-sensitive-stats'],
    queryFn: async () => {
      const res = await apiClient.get<any>('/security/sensitive-words/statistics');
      return res.success && res.data ? res.data : {};
    },
  });

  const addMut = useMutation({
    mutationFn: () => apiClient.post('/security/sensitive-words/', {word}),
    onSuccess: () => { qc.invalidateQueries({queryKey: ['admin-sensitive-words']}); setWord(''); },
  });
  const delMut = useMutation({
    mutationFn: (id: number) => apiClient.delete(`/security/sensitive-words/${id}`),
    onSuccess: () => qc.invalidateQueries({queryKey: ['admin-sensitive-words']}),
  });
  const refreshMut = useMutation({
    mutationFn: () => apiClient.post('/security/sensitive-words/refresh-cache'),
    onSuccess: () => alert('缓存已刷新'),
  });

  return (
    <AdminShell title="敏感词管理" actions={
      <button onClick={() => refreshMut.mutate()} className="px-3 py-1.5 border border-gray-200 rounded-lg text-sm hover:bg-gray-50 flex items-center gap-1.5"><RefreshCw className="w-4 h-4"/>刷新缓存</button>
    }>
      {/* Stats */}
      <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 p-5 mb-6 flex items-center justify-between">
        <div className="flex items-center gap-3"><AlertTriangle className="w-8 h-8 text-orange-500"/><div><p className="font-bold text-gray-900 dark:text-white">{stats?.total_count ?? words?.length ?? 0} 个敏感词</p><p className="text-xs text-gray-500">最后更新: {stats?.last_updated ? new Date(stats.last_updated).toLocaleString('zh-CN') : '-'}</p></div></div>
      </div>

      {/* Add form */}
      <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 p-5 mb-6">
        <div className="flex gap-3">
          <input type="text" value={word} onChange={e => setWord(e.target.value)} placeholder="输入敏感词..."
            className="flex-1 px-4 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl bg-gray-50 dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white"
            onKeyDown={e => {if (e.key === 'Enter' && word.trim()) addMut.mutate();}} />
          <button onClick={() => addMut.mutate()} disabled={!word.trim() || addMut.isPending}
            className="px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-xl disabled:opacity-50 flex items-center gap-1.5"><Plus className="w-4 h-4"/>添加</button>
        </div>
      </div>

      {/* Table */}
      <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 overflow-hidden">
        {isLoading ? (
          <div className="p-12 text-center"><div className="animate-spin w-6 h-6 border-2 border-blue-600 border-t-transparent rounded-full mx-auto"/></div>
        ) : !words?.length ? (
          <div className="p-12 text-center text-gray-400">暂无敏感词</div>
        ) : (
          <table className="w-full"><thead className="bg-gray-50 dark:bg-gray-800 border-b">
            <tr><th className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase">敏感词</th><th className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase hidden sm:table-cell">创建时间</th><th className="px-5 py-3 text-right text-xs font-semibold text-gray-500 uppercase">操作</th></tr>
          </thead><tbody className="divide-y">
            {words.map((w: any) => (
              <tr key={w.id} className="hover:bg-gray-50 dark:hover:bg-gray-800/50">
                <td className="px-5 py-4"><span className="px-3 py-1 bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 text-sm rounded-lg font-mono">{w.word}</span></td>
                <td className="px-5 py-4 text-sm text-gray-500 hidden sm:table-cell">{w.created_at ? new Date(w.created_at).toLocaleString('zh-CN') : '-'}</td>
                <td className="px-5 py-4 text-right"><button onClick={() => delMut.mutate(w.id)} className="p-1.5 text-gray-400 hover:text-red-600"><Trash2 className="w-4 h-4"/></button></td>
              </tr>
            ))}
          </tbody></table>
        )}
      </div>
    </AdminShell>
  );
}

export default function AdminSensitiveWords() {
  return <AuthGuard><QueryProvider><SensitiveWordsInner /></QueryProvider></AuthGuard>;
}
