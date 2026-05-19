'use client';

import React, {useCallback, useState} from 'react';
import {useQuery, useMutation, useQueryClient} from '@tanstack/react-query';
import {apiClient} from '@/lib/api';
import type {Article} from '@/lib/api/base-types';
import {Edit, Eye, Plus, Search, Trash2, Lock, Calendar} from 'lucide-react';
import {QueryProvider} from '@/components/QueryProvider';

const MyPostsPageInner: React.FC = () => {
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const qc = useQueryClient();
  const perPage = 12;

  const {data, isLoading} = useQuery({
    queryKey: ['my-posts', page, search],
    queryFn: async () => {
      const res = await apiClient.get<{articles: Article[]; total: number}>('/dashboard/blog-management/articles', {page, per_page: perPage, q: search || undefined});
      return res.success && res.data ? res.data : {articles: [], total: 0};
    },
  });

  const deleteMut = useMutation({
    mutationFn: (id: number) => apiClient.delete(`/dashboard/blog-management/articles/${id}`),
    onSuccess: () => qc.invalidateQueries({queryKey: ['my-posts']}),
  });

  const articles = data?.articles || [];
  const total = data?.total || 0;
  const totalPages = Math.ceil(total / perPage);

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950 pt-24 pb-12">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between mb-8">
          <div><h1 className="text-3xl font-black text-gray-900 dark:text-white">我的文章</h1><p className="text-gray-500 mt-1">共 {total} 篇文章</p></div>
          <a href="/my/posts/create" className="inline-flex items-center gap-2 px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-xl transition-colors"><Plus className="w-5 h-5"/>写文章</a>
        </div>

        <div className="relative mb-6">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400"/>
          <input type="text" value={search} onChange={e => {setSearch(e.target.value); setPage(1);}} placeholder="搜索文章..." className="w-full pl-12 pr-4 py-3 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white"/>
        </div>

        {isLoading ? (
          <div className="p-12 text-center"><div className="animate-spin w-8 h-8 border-2 border-blue-600 border-t-transparent rounded-full mx-auto"/></div>
        ) : articles.length === 0 ? (
          <div className="bg-white dark:bg-gray-900 rounded-2xl border p-12 text-center">
            <p className="text-gray-400 text-lg mb-4">还没有文章</p>
            <a href="/my/posts/create" className="inline-flex items-center gap-2 px-5 py-2.5 bg-blue-600 text-white rounded-xl hover:bg-blue-700"><Plus className="w-5 h-5"/>开始写作</a>
          </div>
        ) : (
          <div className="space-y-3">
            {articles.map(article => (
              <div key={article.id} className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 p-5 hover:shadow-md transition-shadow">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className={`px-2 py-0.5 text-xs rounded-full font-medium ${
                        article.status === 'publish' || article.status === 1 ? 'bg-green-100 text-green-700' :
                        article.status === 'draft' || article.status === 0 ? 'bg-yellow-100 text-yellow-700' : 'bg-gray-100 text-gray-600'
                      }`}>{article.status === 'publish' || article.status === 1 ? '已发布' : '草稿'}</span>
                      {article.hidden && <span className="px-2 py-0.5 text-xs rounded-full bg-gray-100 text-gray-600"><Lock className="w-3 h-3 inline mr-0.5"/>隐藏</span>}
                      {article.is_vip_only && <span className="px-2 py-0.5 text-xs rounded-full bg-purple-100 text-purple-700">VIP</span>}
                    </div>
                    <a href={`/articles/${article.slug}`} className="text-lg font-bold text-gray-900 dark:text-white hover:text-blue-600 transition-colors line-clamp-1">{article.title}</a>
                    <p className="text-sm text-gray-500 mt-1 line-clamp-1">{article.excerpt || article.summary || ''}</p>
                    <div className="flex items-center gap-4 mt-3 text-xs text-gray-400">
                      <span className="flex items-center gap-1"><Calendar className="w-3.5 h-3.5"/>{article.created_at ? new Date(article.created_at).toLocaleDateString('zh-CN') : ''}</span>
                      <span className="flex items-center gap-1"><Eye className="w-3.5 h-3.5"/>{article.views||0}</span>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    <a href={`/my/posts/edit?id=${article.id}`} className="p-2 text-gray-400 hover:text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded-lg transition-colors"><Edit className="w-4 h-4"/></a>
                    <a href={`/articles/${article.slug}`} target="_blank" className="p-2 text-gray-400 hover:text-green-600 hover:bg-green-50 dark:hover:bg-green-900/20 rounded-lg transition-colors"><Eye className="w-4 h-4"/></a>
                    <button onClick={() => {if(confirm('确定删除此文？')) deleteMut.mutate(article.id);}} className="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors"><Trash2 className="w-4 h-4"/></button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {totalPages > 1 && (
          <div className="flex justify-center gap-2 mt-8">
            {Array.from({length: totalPages}, (_, i) => i+1).map(p => (
              <button key={p} onClick={() => setPage(p)} className={`px-3 py-1.5 rounded-lg text-sm ${p === page ? 'bg-blue-600 text-white' : 'border border-gray-300 dark:border-gray-600 hover:bg-gray-100 dark:hover:bg-gray-800'}`}>{p}</button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

const MyPostsPage: React.FC = () => (
  <QueryProvider><MyPostsPageInner /></QueryProvider>
);
export default MyPostsPage;
