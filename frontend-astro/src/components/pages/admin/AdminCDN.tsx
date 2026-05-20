'use client';

import React from 'react';
import {useQuery, useMutation} from '@tanstack/react-query';
import {AuthGuard} from '@/components/AuthGuard';
import {QueryProvider} from '@/components/QueryProvider';
import {AdminShell} from '@/components/admin/AdminShell';
import {apiClient} from '@/lib/api';
import {Radio, Server, RefreshCw, Activity} from 'lucide-react';

function CDNInner() {
  const {data:config} = useQuery({
    queryKey: ['admin-cdn-config'], queryFn: async () => {
      const r = await apiClient.get<any>('/cdn/config'); return r.success&&r.data?r.data:{};
    },
  });
  const {data:stats} = useQuery({
    queryKey: ['admin-cdn-stats'], queryFn: async () => {
      const r = await apiClient.get<any>('/cdn/stats'); return r.success&&r.data?r.data:{};
    },
  });
  const purgeMut = useMutation({mutationFn:()=>apiClient.post('/cdn/purge-cache')});

  return (
    <AdminShell title="CDN 管理">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <div className="bg-white dark:bg-gray-900 rounded-2xl border p-5"><div className="flex items-center gap-2 text-sm text-gray-500 mb-1"><Server className="w-4 h-4"/>提供商</div><p className="text-2xl font-bold">{config?.provider||'—'}</p></div>
        <div className="bg-white dark:bg-gray-900 rounded-2xl border p-5"><div className="flex items-center gap-2 text-sm text-gray-500 mb-1"><Activity className="w-4 h-4"/>请求数</div><p className="text-2xl font-bold">{stats?.total_requests||'—'}</p></div>
        <div className="bg-white dark:bg-gray-900 rounded-2xl border p-5"><div className="flex items-center gap-2 text-sm text-gray-500 mb-1"><Radio className="w-4 h-4"/>缓存命中</div><p className="text-2xl font-bold">{stats?.cache_hit_rate||'—'}</p></div>
        <div className="bg-white dark:bg-gray-900 rounded-2xl border p-5"><div className="flex items-center gap-2 text-sm text-gray-500 mb-1"><Server className="w-4 h-4"/>传输</div><p className="text-2xl font-bold">{stats?.total_bandwidth||'—'}</p></div>
      </div>
      <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 p-6 flex items-center justify-between">
        <div><p className="font-medium text-gray-900 dark:text-white">CDN 配置</p><p className="text-sm text-gray-500 mt-0.5">当前: {config?.provider||'未配置'} | 域名: {config?.domain||'—'}</p></div>
        <button onClick={()=>purgeMut.mutate()} className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded-lg flex items-center gap-1.5"><RefreshCw className="w-4 h-4"/>刷新缓存</button>
      </div>
    </AdminShell>
  );
}
export default function AdminCDN() { return <AuthGuard><QueryProvider><CDNInner/></QueryProvider></AuthGuard>; }
