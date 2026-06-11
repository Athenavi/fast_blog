'use client';

import React, {useState} from 'react';
import {useQuery, useMutation, useQueryClient} from '@tanstack/react-query';
import {AuthGuard} from '@/components/AuthGuard';
import {QueryProvider} from '@/components/QueryProvider';
import {AdminShell} from '@/components/admin/AdminShell';
import {apiClient} from '@/lib/api/base-client';
import {Clock, Calendar, X, Send} from 'lucide-react';

function ScheduledManager() {
  const qc = useQueryClient();
  const [page, setPage] = useState(1);

  const {data, isLoading} = useQuery({
    queryKey: ['scheduled-articles', page],
    queryFn: async () => {
      const res = await apiClient.get('/articles/scheduler/list', {page, per_page: 20});
      return res.data || {articles: [], total: 0, page: 1, total_pages: 1};
    },
  });

  const cancelMut = useMutation({
    mutationFn: (id: number) => apiClient.post(`/articles/scheduler/cancel/${id}`),
    onSuccess: () => qc.invalidateQueries({queryKey: ['scheduled-articles']}),
  });

  const publishNowMut = useMutation({
    mutationFn: async () => { await apiClient.post('/articles/scheduler/publish-due'); },
    onSuccess: () => qc.invalidateQueries({queryKey: ['scheduled-articles']}),
  });

  const articles: any[] = (data as any)?.articles || [];
  const total = (data as any)?.total || 0;

  return (
    <AdminShell title="Scheduled Articles" actions={
      <button onClick={() => publishNowMut.mutate()} disabled={publishNowMut.isPending}
              className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-gradient-to-r from-blue-600 to-indigo-600 rounded-xl hover:from-blue-700 hover:to-indigo-700 disabled:opacity-50 transition-all">
        <Send className="w-4 h-4"/> Publish Due Now
      </button>
    }>
      {isLoading ? (
        <div className="space-y-3">{[1,2,3].map(i => <div key={i} className="h-16 bg-gray-100 dark:bg-gray-800 rounded-xl animate-pulse"/>)}</div>
      ) : articles.length === 0 ? (
        <div className="text-center py-20 text-gray-400">
          <Clock className="w-12 h-12 mx-auto mb-4 opacity-50"/>
          <p className="text-lg font-medium text-gray-500 dark:text-gray-400 mb-1">No scheduled articles</p>
          <p className="text-sm">Schedule articles from the article editor sidebar</p>
        </div>
      ) : (
        <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-200 dark:border-gray-800 text-xs text-gray-500 uppercase">
                <th className="text-left px-4 py-3 font-medium">Title</th>
                <th className="text-left px-4 py-3 font-medium">Scheduled At</th>
                <th className="text-right px-4 py-3 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              {articles.map((a: any) => (
                <tr key={a.id} className="border-b border-gray-100 dark:border-gray-800/50 hover:bg-gray-50 dark:hover:bg-gray-800/30 transition-colors">
                  <td className="px-4 py-3 text-sm text-gray-900 dark:text-white">{a.title || `Article #${a.id}`}</td>
                  <td className="px-4 py-3 text-sm text-gray-500 flex items-center gap-1.5">
                    <Calendar className="w-3.5 h-3.5"/>
                    {a.scheduled_at ? new Date(a.scheduled_at).toLocaleString('zh-CN') : '-'}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button onClick={() => cancelMut.mutate(a.id)}
                            className="inline-flex items-center gap-1 px-3 py-1.5 text-xs border border-red-200 dark:border-red-800 text-red-500 rounded-lg hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors">
                      <X className="w-3 h-3"/> Cancel
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {total > 20 && (
            <div className="flex items-center justify-between px-4 py-3 border-t border-gray-200 dark:border-gray-800">
              <span className="text-sm text-gray-500">{total} total</span>
              <div className="flex gap-2">
                <button disabled={page <= 1} onClick={() => setPage(p => p - 1)}
                        className="px-3 py-1 text-sm border border-gray-200 dark:border-gray-700 rounded-lg disabled:opacity-50">Previous</button>
                <button disabled={articles.length < 20} onClick={() => setPage(p => p + 1)}
                        className="px-3 py-1 text-sm border border-gray-200 dark:border-gray-700 rounded-lg disabled:opacity-50">Next</button>
              </div>
            </div>
          )}
        </div>
      )}
    </AdminShell>
  );
}

export default function AdminScheduled() {
  return <AuthGuard><QueryProvider><ScheduledManager/></QueryProvider></AuthGuard>;
}
