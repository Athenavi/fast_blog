'use client';

import React, {useState} from 'react';
import {useMutation, useQuery, useQueryClient} from '@tanstack/react-query';
import {AuthGuard} from '@/components/AuthGuard';
import {QueryProvider} from '@/components/QueryProvider';
import {AdminShell} from '@/components/admin/AdminShell';
import {apiClient} from '@/lib/api/base-client';
import {Edit, Eye, Plus, Search, Trash2} from 'lucide-react';

function ArticlesInner() {
  const qc = useQueryClient();
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');

  const {data, isLoading} = useQuery({
    queryKey: ['admin-articles', page, search],
    queryFn: async () => {
      const res = await apiClient.get('/api/v2/dashboard/blog-management/articles', {
        page,
        per_page: 15,
        q: search || undefined
      });
      return res.success && res.data ? (res.data as any) : {articles: [], total: 0};
    },
  });

  const delMut = useMutation({
    mutationFn: (id: number) => apiClient.delete(`/api/v2/articles/${id}`),
    onSuccess: () => qc.invalidateQueries({queryKey: ['admin-articles']}),
  });

  const articles = data?.articles || [];
  const total = data?.total || 0;
  const totalPages = Math.ceil(total / 15);

  return (
    <AdminShell title="文章管理" actions={
      <a href="/admin/editor" className="px-4 py-1.5 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg flex items-center gap-1.5"><Plus className="w-4 h-4"/>新建</a>
    }>
      {/* Search */}
      <div className="relative mb-4">
        <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400"/>
        <input type="text" value={search} onChange={e => {setSearch(e.target.value); setPage(1);}} placeholder="搜索文章..." className="w-full pl-10 pr-4 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl bg-white dark:bg-gray-900 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white"/>
      </div>

      {/* Table */}
      <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 overflow-hidden">
        {isLoading ? (
          <div className="p-12 text-center"><div className="animate-spin w-6 h-6 border-2 border-blue-600 border-t-transparent rounded-full mx-auto"/></div>
        ) : articles.length === 0 ? (
          <div className="p-12 text-center text-gray-400">暂无文章</div>
        ) : (
          <table className="w-full"><thead className="bg-gray-50 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
            <tr><th className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase">标题</th><th className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase hidden sm:table-cell">状态</th><th className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase hidden md:table-cell">浏览</th><th className="px-5 py-3 text-right text-xs font-semibold text-gray-500 uppercase">操作</th></tr>
          </thead><tbody className="divide-y divide-gray-100 dark:divide-gray-800">
            {articles.map((a: any) => (
              <tr key={a.id} className="hover:bg-gray-50 dark:hover:bg-gray-800/50">
                <td className="px-5 py-4">
                  <p className="font-medium text-gray-900 dark:text-white text-sm line-clamp-1">{a.title}</p>
                  <p className="text-xs text-gray-400 mt-0.5">{a.created_at ? new Date(a.created_at).toLocaleDateString('zh-CN') : ''}</p>
                </td>
                <td className="px-5 py-4 hidden sm:table-cell">
                  <span className={`px-2 py-0.5 text-xs rounded-full font-medium ${a.status === 'publish' || a.status === 1 ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'}`}>
                    {a.status === 'publish' || a.status === 1 ? '已发布' : '草稿'}
                  </span>
                </td>
                <td className="px-5 py-4 text-sm text-gray-500 hidden md:table-cell">{a.views || 0}</td>
                <td className="px-5 py-4 text-right">
                  <a href={`/my/posts/edit?id=${a.id}`} className="p-1.5 inline-block text-gray-400 hover:text-blue-600 rounded-lg hover:bg-blue-50 dark:hover:bg-blue-900/20"><Edit className="w-4 h-4"/></a>
                  <a href={`/view?slug=${a.slug}`} target="_blank"
                     className="p-1.5 inline-block text-gray-400 hover:text-green-600 rounded-lg hover:bg-green-50 dark:hover:bg-green-900/20"><Eye
                      className="w-4 h-4"/></a>
                  <button onClick={() => {if(confirm('确认删除？')) delMut.mutate(a.id);}} className="p-1.5 inline-block text-gray-400 hover:text-red-600 rounded-lg hover:bg-red-50 dark:hover:bg-red-900/20"><Trash2 className="w-4 h-4"/></button>
                </td>
              </tr>
            ))}
          </tbody></table>
        )}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex justify-center gap-1.5 mt-4">
          {Array.from({length: totalPages}, (_, i) => i+1).map(p => (
            <button key={p} onClick={() => setPage(p)} className={`px-3 py-1.5 rounded-lg text-sm ${p === page ? 'bg-blue-600 text-white' : 'border border-gray-200 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-800'}`}>{p}</button>
          ))}
        </div>
      )}
    </AdminShell>
  );
}

export default function AdminArticles() {
  return <AuthGuard><QueryProvider><ArticlesInner /></QueryProvider></AuthGuard>;
}
