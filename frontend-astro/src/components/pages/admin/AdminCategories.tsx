'use client';

import React, {useState} from 'react';
import {useMutation, useQuery, useQueryClient} from '@tanstack/react-query';
import {AuthGuard} from '@/components/AuthGuard';
import {QueryProvider} from '@/components/QueryProvider';
import {AdminShell} from '@/components/admin/AdminShell';
import {apiClient} from '@/lib/api/base-client';
import {Edit, Trash2} from 'lucide-react';

function CategoriesInner() {
  const qc = useQueryClient();
  const [editing, setEditing] = useState<any>(null);
  const [name, setName] = useState('');
  const [slug, setSlug] = useState('');

  const {data: cats, isLoading} = useQuery({
    queryKey: ['admin-categories'],
    queryFn: async () => {
      const res = await apiClient.get('/api/v2/categories');
      return res.success && res.data ? (Array.isArray(res.data) ? res.data : res.data.categories || []) : [];
    },
  });

  const saveMut = useMutation({
    mutationFn: async () => {
      const body = {name, slug: slug || undefined};
      if (editing) return apiClient.put(`/api/v2/categories/${editing.id}`, body);
      return apiClient.post('/api/v2/categories', body);
    },
    onSuccess: () => { qc.invalidateQueries({queryKey: ['admin-categories']}); setEditing(null); setName(''); setSlug(''); },
  });

  const delMut = useMutation({
    mutationFn: (id: number) => apiClient.delete(`/api/v2/categories/${id}`),
    onSuccess: () => qc.invalidateQueries({queryKey: ['admin-categories']}),
  });

  const startEdit = (c: any) => { setEditing(c); setName(c.name); setSlug(c.slug || ''); };

  return (
    <AdminShell title="分类管理">
      {/* Add / Edit form */}
      <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 p-5 mb-6">
        <h3 className="font-semibold text-gray-900 dark:text-white mb-4">{editing ? '编辑分类' : '新建分类'}</h3>
        <div className="flex flex-wrap gap-3">
          <input type="text" value={name} onChange={e => setName(e.target.value)} placeholder="分类名称" className="flex-1 min-w-[160px] px-4 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl bg-gray-50 dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white"/>
          <input type="text" value={slug} onChange={e => setSlug(e.target.value)} placeholder="Slug（可选）" className="flex-1 min-w-[120px] px-4 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl bg-gray-50 dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white font-mono"/>
          <button onClick={() => saveMut.mutate()} disabled={!name.trim() || saveMut.isPending} className="px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-xl disabled:opacity-50">{saveMut.isPending ? '保存...' : editing ? '更新' : '添加'}</button>
          {editing && <button onClick={() => {setEditing(null); setName(''); setSlug('');}} className="px-4 py-2.5 border border-gray-200 rounded-xl text-sm hover:bg-gray-100">取消</button>}
        </div>
      </div>

      {/* Table */}
      <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 overflow-hidden">
        {isLoading ? (
          <div className="p-12 text-center"><div className="animate-spin w-6 h-6 border-2 border-blue-600 border-t-transparent rounded-full mx-auto"/></div>
        ) : !cats?.length ? (
          <div className="p-12 text-center text-gray-400">暂无分类</div>
        ) : (
          <table className="w-full"><thead className="bg-gray-50 dark:bg-gray-800 border-b">
            <tr><th className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase">名称</th><th className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase hidden sm:table-cell">Slug</th><th className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase hidden md:table-cell">文章数</th><th className="px-5 py-3 text-right text-xs font-semibold text-gray-500 uppercase">操作</th></tr>
          </thead><tbody className="divide-y">
            {cats.map((c: any) => (
              <tr key={c.id} className="hover:bg-gray-50 dark:hover:bg-gray-800/50">
                <td className="px-5 py-4"><p className="font-medium text-gray-900 dark:text-white text-sm">{c.name}</p></td>
                <td className="px-5 py-4 text-sm text-gray-500 font-mono hidden sm:table-cell">{c.slug || '-'}</td>
                <td className="px-5 py-4 text-sm text-gray-500 hidden md:table-cell">{c.articles_count || c.article_count || 0}</td>
                <td className="px-5 py-4 text-right"><button onClick={() => startEdit(c)} className="p-1.5 inline-block text-gray-400 hover:text-blue-600"><Edit className="w-4 h-4"/></button><button onClick={() => {if(confirm('删除分类？')) delMut.mutate(c.id);}} className="p-1.5 inline-block text-gray-400 hover:text-red-600"><Trash2 className="w-4 h-4"/></button></td>
              </tr>
            ))}
          </tbody></table>
        )}
      </div>
    </AdminShell>
  );
}

export default function AdminCategories() {
  return <AuthGuard><QueryProvider><CategoriesInner /></QueryProvider></AuthGuard>;
}
