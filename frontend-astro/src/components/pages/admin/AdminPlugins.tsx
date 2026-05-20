'use client';

import React from 'react';
import {useQuery, useMutation, useQueryClient} from '@tanstack/react-query';
import {AuthGuard} from '@/components/AuthGuard';
import {QueryProvider} from '@/components/QueryProvider';
import {AdminShell} from '@/components/admin/AdminShell';
import {apiClient} from '@/lib/api/base-client';
import {ToggleLeft, ToggleRight, Puzzle} from 'lucide-react';

function PluginsInner() {
  const qc = useQueryClient();
  const {data: plugins, isLoading} = useQuery({
    queryKey: ['admin-plugins'],
    queryFn: async () => {
      const res = await apiClient.get<any[]>('/plugins/active');
      return res.success && res.data ? (Array.isArray(res.data) ? res.data : []) : [];
    },
  });

  const toggleMut = useMutation({
    mutationFn: ({slug, active}: {slug: string; active: boolean}) =>
      active ? apiClient.post(`/plugins/${slug}/deactivate`) : apiClient.post(`/plugins/${slug}/activate`),
    onSuccess: () => qc.invalidateQueries({queryKey: ['admin-plugins']}),
  });

  return (
    <AdminShell title="插件管理">
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {isLoading ? (
          <div className="col-span-full p-12 text-center"><div className="animate-spin w-6 h-6 border-2 border-blue-600 border-t-transparent rounded-full mx-auto"/></div>
        ) : !plugins?.length ? (
          <div className="col-span-full p-12 text-center text-gray-400"><Puzzle className="w-10 h-10 mx-auto mb-3 opacity-50"/><p>暂无插件</p></div>
        ) : plugins.map((p: any) => (
          <div key={p.slug || p.name} className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 p-5 flex flex-col">
            <div className="flex items-start justify-between mb-3">
              <div><h3 className="font-semibold text-gray-900 dark:text-white text-sm">{p.name || p.slug}</h3><p className="text-xs text-gray-400 mt-0.5">v{p.version || '1.0'}</p></div>
              <button onClick={() => toggleMut.mutate({slug: p.slug, active: p.active})}
                className={`p-1.5 rounded-lg ${p.active ? 'bg-green-100 text-green-600' : 'bg-gray-100 text-gray-400'}`}>
                {p.active ? <ToggleRight className="w-5 h-5"/> : <ToggleLeft className="w-5 h-5"/>}
              </button>
            </div>
            <p className="text-xs text-gray-500 flex-1">{p.description || '暂无描述'}</p>
            <div className="mt-3 flex gap-1.5">
              <span className={`px-2 py-0.5 text-xs rounded-full ${p.active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>{p.active ? '已启用' : '已禁用'}</span>
              {p.author && <span className="px-2 py-0.5 text-xs rounded-full bg-blue-50 text-blue-600">{p.author}</span>}
            </div>
          </div>
        ))}
      </div>
    </AdminShell>
  );
}

export default function AdminPlugins() {
  return <AuthGuard><QueryProvider><PluginsInner /></QueryProvider></AuthGuard>;
}
