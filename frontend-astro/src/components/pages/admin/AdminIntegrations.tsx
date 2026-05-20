'use client';

import React from 'react';
import {useQuery} from '@tanstack/react-query';
import {AuthGuard} from '@/components/AuthGuard';
import {QueryProvider} from '@/components/QueryProvider';
import {AdminShell} from '@/components/admin/AdminShell';
import {apiClient} from '@/lib/api';
import {Globe, Link, Unlink, Check} from 'lucide-react';

function IntegrationsInner() {
  const {data:oauth, isLoading} = useQuery({
    queryKey: ['admin-oauth'],
    queryFn: async () => {
      const r = await apiClient.get<any[]>('/integrations/oauth/providers');
      return r.success && r.data ? (Array.isArray(r.data) ? r.data : r.data.providers||[]) : [];
    },
  });
  const {data:linked} = useQuery({
    queryKey: ['admin-linked'],
    queryFn: async () => {
      const r = await apiClient.get<any[]>('/integrations/oauth/linked-accounts');
      return r.success && r.data ? (Array.isArray(r.data) ? r.data : r.data.accounts||[]) : [];
    },
  });

  const providers = oauth?.length ? oauth : [
    {name:'Google',icon:'G',enabled:true},
    {name:'GitHub',icon:'GH',enabled:true},
    {name:'WeChat',icon:'WX',enabled:false},
    {name:'QQ',icon:'QQ',enabled:false},
    {name:'Weibo',icon:'WB',enabled:false},
  ];

  return (
    <AdminShell title="集成管理">
      <div className="grid gap-6 lg:grid-cols-2">
        <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 p-6">
          <h3 className="font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2"><Globe className="w-5 h-5"/>OAuth 登录</h3>
          <div className="space-y-3">
            {providers.map((p:any,i:number) => (
              <div key={i} className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded-xl">
                <div className="flex items-center gap-3"><div className="w-8 h-8 rounded-lg bg-blue-100 dark:bg-blue-900/20 flex items-center justify-center text-xs font-bold text-blue-600">{p.icon||p.name?.charAt(0)}</div><span className="text-sm font-medium text-gray-900 dark:text-white">{p.name}</span></div>
                <span className={`px-2 py-0.5 text-xs rounded-full ${p.enabled||p.is_linked?'bg-green-100 text-green-700':'bg-gray-100 text-gray-500'}`}>{p.enabled||p.is_linked?'已连接':'未连接'}</span>
              </div>
            ))}
          </div>
        </div>
        <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 p-6">
          <h3 className="font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2"><Link className="w-5 h-5"/>已关联账号</h3>
          {linked?.length > 0 ? (
            <div className="space-y-3">
              {linked.map((a:any,i:number) => (
                <div key={i} className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded-xl">
                  <div className="flex items-center gap-2"><span className="text-sm font-medium">{a.provider||a.name}</span><span className="text-xs text-gray-500">{a.email||a.username||''}</span></div>
                  <button className="text-xs text-red-500 hover:underline">解除</button>
                </div>
              ))}
            </div>
          ) : <p className="text-sm text-gray-400 text-center py-8">暂无关联账号</p>}
        </div>
      </div>
    </AdminShell>
  );
}
export default function AdminIntegrations() { return <AuthGuard><QueryProvider><IntegrationsInner/></QueryProvider></AuthGuard>; }
