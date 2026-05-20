'use client';

import React, {useState} from 'react';
import {useQuery, useMutation, useQueryClient} from '@tanstack/react-query';
import {apiClient} from '@/lib/api';
import {Edit, Eye, Plus, Search, Trash2, Lock, Calendar, FileText} from 'lucide-react';
import {QueryProvider} from '@/components/QueryProvider';
import {AuthGuard} from '@/components/AuthGuard';

function MyPostsInner() {
  const [page, setPage] = useState(1);
  const [q, setQ] = useState('');
  const qc = useQueryClient();

  const {data, isLoading} = useQuery({
    queryKey: ['my-posts', page, q],
    queryFn: async () => {
      const res = await apiClient.get<any>('/dashboard/my/articles', {page, per_page: 15, q: q || undefined});
      if (!res.success || !res.data) return {articles: [], total: 0};
      // API may return {articles:[], total:N} or {data:{articles:[], total:N}} or just an array
      if (Array.isArray(res.data)) return {articles: res.data, total: res.data.length};
      if (res.data.articles) return {articles: res.data.articles, total: res.data.total || res.data.articles.length};
      if (res.data.data) return {articles: (res.data.data as any).articles || [], total: (res.data.data as any).total || 0};
      return {articles: [], total: 0};
    },
  });

  const delMut = useMutation({
    mutationFn: (id: number) => apiClient.delete(`/dashboard/blog-management/article-detail?slug=id`),
    onSuccess: () => qc.invalidateQueries({queryKey: ['my-posts']}),
  });

  const articles = data?.articles || [];
  const total = data?.total || 0;
  const pages = Math.ceil(total / 15);

  const statusLabel = (s: any) => {
    if (s === 'publish' || s === 1 || s === true) return '已发布';
    if (s === 'draft' || s === 0 || s === false) return '草稿';
    return String(s || '草稿');
  };
  const isPublished = (s: any) => s === 'publish' || s === 1 || s === true;

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50 dark:from-gray-950 dark:to-gray-900 pt-20">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 pb-12">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div><h1 className="text-2xl font-bold text-gray-900 dark:text-white">我的文章</h1><p className="text-sm text-gray-500 mt-0.5">{total > 0 ? `共 ${total} 篇` : ''}</p></div>
          <a href="/my/posts/create" className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-xl flex items-center gap-1.5 transition-colors shadow-sm"><Plus className="w-4 h-4"/>写文章</a>
        </div>

        {/* Search */}
        <div className="relative mb-5">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400"/>
          <input type="text" value={q} onChange={e=>{setQ(e.target.value);setPage(1);}} placeholder="搜索文章..." className="w-full pl-10 pr-4 py-2.5 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white"/>
        </div>

        {/* List */}
        <div className="space-y-2">
          {isLoading ? (
            <div className="space-y-2">{[1,2,3,4].map(i=><div key={i} className="h-20 bg-white/50 dark:bg-gray-800/50 rounded-xl animate-pulse"/>)}</div>
          ) : articles.length === 0 ? (
            <div className="bg-white/70 dark:bg-gray-900/70 backdrop-blur-sm rounded-2xl border border-gray-100 dark:border-gray-800 p-12 text-center">
              <FileText className="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto mb-3"/>
              <p className="text-gray-500 mb-4 text-sm">{q ? '没有匹配的文章' : '还没有文章'}</p>
              {!q && <a href="/my/posts/create" className="inline-flex items-center gap-1.5 px-4 py-2 bg-blue-600 text-white text-sm rounded-xl hover:bg-blue-700"><Plus className="w-4 h-4"/>开始写作</a>}
            </div>
          ) : (
            articles.map((a: any) => (
              <div key={a.id} className="bg-white/70 dark:bg-gray-900/70 backdrop-blur-sm rounded-xl border border-gray-100 dark:border-gray-800 p-4 hover:border-gray-200 dark:hover:border-gray-700 transition-all hover:shadow-sm flex items-start gap-3">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className={`px-2 py-0.5 text-xs rounded-full font-medium ${isPublished(a.status) ? 'bg-green-100 text-green-700' : 'bg-amber-100 text-amber-700'}`}>{statusLabel(a.status)}</span>
                    {a.hidden && <Lock className="w-3 h-3 text-gray-400"/>}
                  </div>
                  <div className="flex items-center gap-2">
                    <a href={`/article-detail?slug=a.slug`} className="font-semibold text-gray-900 dark:text-white text-sm hover:text-blue-600 truncate">{a.title||'无标题'}</a>
                  </div>
                  {(a.excerpt||a.summary) && <p className="text-xs text-gray-500 mt-1 line-clamp-1">{a.excerpt||a.summary}</p>}
                  <div className="flex items-center gap-3 mt-1.5 text-xs text-gray-400">
                    <span><Calendar className="w-3 h-3 inline mr-0.5"/>{a.created_at ? new Date(a.created_at).toLocaleDateString('zh-CN') : ''}</span>
                    <span><Eye className="w-3 h-3 inline mr-0.5"/>{a.views ?? 0}</span>
                  </div>
                </div>
                <div className="flex items-center gap-1 shrink-0">
                  <a href={`/my/posts/edit?id=${a.id}`} className="p-1.5 text-gray-400 hover:text-blue-600 rounded-lg hover:bg-blue-50 dark:hover:bg-blue-900/20"><Edit className="w-4 h-4"/></a>
                  <button onClick={()=>{if(confirm('删除此文章？'))delMut.mutate(a.id);}} className="p-1.5 text-gray-400 hover:text-red-600 rounded-lg hover:bg-red-50 dark:hover:bg-red-900/20"><Trash2 className="w-4 h-4"/></button>
                </div>
              </div>
            ))
          )}
        </div>

        {/* Pagination */}
        {pages > 1 && (
          <div className="flex justify-center gap-1.5 mt-6">
            {Array.from({length: pages}, (_, i) => i+1).map(p => (
              <button key={p} onClick={() => setPage(p)} className={`px-3 py-1.5 rounded-lg text-sm ${p === page ? 'bg-blue-600 text-white' : 'border border-gray-200 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-800'}`}>{p}</button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default function MyPostsPage() {
  return <AuthGuard><QueryProvider><MyPostsInner/></QueryProvider></AuthGuard>;
}
