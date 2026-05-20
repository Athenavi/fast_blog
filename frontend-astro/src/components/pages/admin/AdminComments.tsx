'use client';

import React from 'react';
import {useQuery, useMutation, useQueryClient} from '@tanstack/react-query';
import {AuthGuard} from '@/components/AuthGuard';
import {QueryProvider} from '@/components/QueryProvider';
import {AdminShell} from '@/components/admin/AdminShell';
import {apiClient} from '@/lib/api/base-client';
import {Check, X, MessageSquare} from 'lucide-react';

function CommentsInner() {
  const qc = useQueryClient();
  const {data: comments, isLoading} = useQuery({
    queryKey: ['admin-comments'],
    queryFn: async () => {
      const res = await apiClient.get<any[]>('/comments/admin/comments/pending');
      return res.success && res.data ? (Array.isArray(res.data) ? res.data : []) : [];
    },
  });

  const approveMut = useMutation({
    mutationFn: (id: number) => apiClient.post(`/comments/admin/comments/${id}/approve`),
    onSuccess: () => qc.invalidateQueries({queryKey: ['admin-comments']}),
  });
  const rejectMut = useMutation({
    mutationFn: (id: number) => apiClient.post(`/comments/admin/comments/${id}/reject`),
    onSuccess: () => qc.invalidateQueries({queryKey: ['admin-comments']}),
  });

  return (
    <AdminShell title="评论管理">
      <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 overflow-hidden">
        {isLoading ? (
          <div className="p-12 text-center"><div className="animate-spin w-6 h-6 border-2 border-blue-600 border-t-transparent rounded-full mx-auto"/></div>
        ) : !comments?.length ? (
          <div className="p-12 text-center text-gray-400"><MessageSquare className="w-10 h-10 mx-auto mb-3 opacity-50"/><p>暂无待审评论</p></div>
        ) : (
          <div className="divide-y divide-gray-100 dark:divide-gray-800">
            {comments.map((c: any) => (
              <div key={c.id} className="p-5 hover:bg-gray-50 dark:hover:bg-gray-800/50">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 text-sm mb-1">
                      <span className="font-medium text-gray-900 dark:text-white">{c.author_name || c.author?.username || '匿名'}</span>
                      <span className="text-gray-400">·</span>
                      <span className="text-gray-400 text-xs">{c.created_at ? new Date(c.created_at).toLocaleString('zh-CN') : ''}</span>
                    </div>
                    <p className="text-gray-700 dark:text-gray-300 text-sm">{c.content}</p>
                    {c.article_title && <p className="text-xs text-gray-400 mt-2">文章: {c.article_title}</p>}
                  </div>
                  <div className="flex gap-1.5 flex-shrink-0">
                    <button onClick={() => approveMut.mutate(c.id)} className="p-2 bg-green-100 dark:bg-green-900/20 text-green-600 rounded-lg hover:bg-green-200"><Check className="w-4 h-4"/></button>
                    <button onClick={() => rejectMut.mutate(c.id)} className="p-2 bg-red-100 dark:bg-red-900/20 text-red-600 rounded-lg hover:bg-red-200"><X className="w-4 h-4"/></button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </AdminShell>
  );
}

export default function AdminComments() {
  return <AuthGuard><QueryProvider><CommentsInner /></QueryProvider></AuthGuard>;
}
