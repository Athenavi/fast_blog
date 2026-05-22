'use client';

import React, {useState, useEffect, useRef} from 'react';
import {useMutation, useQuery, useQueryClient} from '@tanstack/react-query';
import {AuthGuard} from '@/components/AuthGuard';
import {QueryProvider} from '@/components/QueryProvider';
import {AdminShell} from '@/components/admin/AdminShell';
import {apiClient} from '@/lib/api/base-client';
import {ChevronLeft, ChevronRight, Edit, Eye, Plus, Search, Trash2, X} from 'lucide-react';

function useDebounce<T>(value: T, delay: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => { const t = setTimeout(() => setDebounced(value), delay); return () => clearTimeout(t); }, [value, delay]);
  return debounced;
}

const STATUS_OPTIONS = [
  {value: '', label: '全部'},
  {value: 'published', label: '已发布'},
  {value: 'draft', label: '草稿'},
] as const;

function ArticlesInner() {
  const qc = useQueryClient();
  const [page, setPage] = useState(1);
  const [searchInput, setSearchInput] = useState('');
  const [status, setStatus] = useState('');
  const debouncedSearch = useDebounce(searchInput, 400);

  const prevFilters = useRef('');
  useEffect(() => {
    const f = `${status}-${debouncedSearch}`;
    if (prevFilters.current && prevFilters.current !== f) setPage(1);
    prevFilters.current = f;
  }, [status, debouncedSearch]);

  const {data, isLoading} = useQuery({
    queryKey: ['admin-articles', page, status, debouncedSearch],
    queryFn: async () => {
      const params: Record<string, any> = {page, per_page: 15};
      if (status) params.status = status;
      if (debouncedSearch) params.search = debouncedSearch;
      const res = await apiClient.get('/api/v2/dashboard/blog-management/articles', params);
      if (!res.success || !res.data) return {articles: [], total: 0};
      const articles = Array.isArray(res.data) ? res.data : [];
      const pagination = (res as any).pagination || {};
      const total = pagination.total || articles.length;
      return {articles, total};
    },
  });

  const delMut = useMutation({
    mutationFn: (id: number) => apiClient.delete(`/api/v2/articles/${id}`),
    onSuccess: () => qc.invalidateQueries({queryKey: ['admin-articles']}),
  });

  const articles = data?.articles || [];
  const total = data?.total || 0;
  const totalPages = Math.ceil(total / 15);

  const renderPagination = () => {
    if (totalPages <= 1) return null;
    const pages: (number | string)[] = [];
    const delta = 2, left = Math.max(2, page - delta), right = Math.min(totalPages - 1, page + delta);
    pages.push(1);
    if (left > 2) pages.push('...');
    for (let i = left; i <= right; i++) pages.push(i);
    if (right < totalPages - 1) pages.push('...');
    if (totalPages > 1) pages.push(totalPages);
    return (
        <div className="flex items-center justify-center gap-1.5 mt-6 pb-6">
          <button disabled={page <= 1} onClick={() => setPage(p => p - 1)}
                  className="p-2 rounded-lg border border-gray-200 dark:border-gray-700 disabled:opacity-30 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors">
            <ChevronLeft className="w-4 h-4"/>
          </button>
          {pages.map((p, i) =>
              p === '...' ? <span key={`e-${i}`} className="px-2 text-gray-400">…</span> :
              <button key={p} onClick={() => setPage(p as number)}
                      className={`min-w-[36px] h-9 rounded-lg text-sm font-medium transition-colors ${
                          p === page ? 'bg-blue-600 text-white' : 'border border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800'
                      }`}>{p}</button>
          )}
          <button disabled={page >= totalPages} onClick={() => setPage(p => p + 1)}
                  className="p-2 rounded-lg border border-gray-200 dark:border-gray-700 disabled:opacity-30 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors">
            <ChevronRight className="w-4 h-4"/>
          </button>
        </div>
    );
  };

  return (
      <AdminShell title="文章管理" actions={
        <a href="/admin/editor" className="px-4 py-1.5 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg flex items-center gap-1.5"><Plus className="w-4 h-4"/>新建</a>
      }>
        {/* 筛选栏 */}
        <div className="flex flex-wrap items-center gap-3 mb-4">
          <div className="relative flex-1 min-w-[180px]">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400"/>
            <input type="text" value={searchInput} onChange={e => setSearchInput(e.target.value)}
                   placeholder="搜索文章标题..." className="w-full pl-9 pr-8 py-2 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white"/>
            {searchInput && <button onClick={() => setSearchInput('')} className="absolute right-2 top-1/2 -translate-y-1/2 p-0.5 text-gray-400 hover:text-gray-600"><X className="w-4 h-4"/></button>}
          </div>
          <div className="flex gap-1 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-xl p-1">
            {STATUS_OPTIONS.map(opt => (
                <button key={opt.value} onClick={() => setStatus(opt.value)}
                        className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                            status === opt.value ? 'bg-blue-600 text-white' : 'text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800'
                        }`}>{opt.label}</button>
            ))}
          </div>
          <span className="text-xs text-gray-400">共 {total} 篇</span>
        </div>

        <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 overflow-hidden">
          {isLoading ? (
              <div className="p-12 text-center"><div className="animate-spin w-6 h-6 border-2 border-blue-600 border-t-transparent rounded-full mx-auto"/></div>
          ) : articles.length === 0 ? (
              <div className="p-12 text-center text-gray-400">{debouncedSearch ? '未找到匹配的文章' : '暂无文章'}</div>
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
                      <span className={`px-2 py-0.5 text-xs rounded-full font-medium ${a.status === 'published' || a.status === 1 ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400' : a.status === 'deleted' ? 'bg-red-100 text-red-700' : 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400'}`}>
                        {a.status === 'published' || a.status === 1 ? '已发布' : a.status === 'deleted' ? '已删除' : '草稿'}
                      </span>
                    </td>
                    <td className="px-5 py-4 text-sm text-gray-500 hidden md:table-cell">{a.views || 0}</td>
                    <td className="px-5 py-4 text-right">
                      <a href={`/my/posts/edit?id=${a.id}`} className="p-1.5 inline-block text-gray-400 hover:text-blue-600 rounded-lg hover:bg-blue-50 dark:hover:bg-blue-900/20"><Edit className="w-4 h-4"/></a>
                      <a href={`/view?slug=${a.slug}`} target="_blank" className="p-1.5 inline-block text-gray-400 hover:text-green-600 rounded-lg hover:bg-green-50 dark:hover:bg-green-900/20"><Eye className="w-4 h-4"/></a>
                      <button onClick={() => {if(confirm('确认删除？')) delMut.mutate(a.id);}} className="p-1.5 inline-block text-gray-400 hover:text-red-600 rounded-lg hover:bg-red-50 dark:hover:bg-red-900/20"><Trash2 className="w-4 h-4"/></button>
                    </td>
                  </tr>
              ))}
              </tbody></table>
          )}
        </div>

        {renderPagination()}
      </AdminShell>
  );
}

export default function AdminArticles() {
  return <AuthGuard><QueryProvider><ArticlesInner /></QueryProvider></AuthGuard>;
}
