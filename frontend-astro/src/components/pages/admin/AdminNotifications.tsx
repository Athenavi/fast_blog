'use client';

import React, {useState} from 'react';
import {useMutation, useQuery, useQueryClient} from '@tanstack/react-query';
import {AuthGuard} from '@/components/AuthGuard';
import {QueryProvider} from '@/components/QueryProvider';
import {AdminShell} from '@/components/admin/AdminShell';
import {apiClient} from '@/lib/api/api-client';
import {Bell, Check, Send, Trash2} from 'lucide-react';

function NotificationsInner() {
  const qc = useQueryClient();
  const [msg, setMsg] = useState('');

  const {data, isLoading} = useQuery({
    queryKey: ['admin-notifications'],
    queryFn: async () => {
      const r = await apiClient.get<any[]>('/notifications/messages');
      return r.success && r.data ? (Array.isArray(r.data) ? r.data : r.data.notifications||[]) : [];
    },
  });

  const sendMut = useMutation({
    mutationFn: () => apiClient.post('/notifications/email/send', {content:msg}),
    onSuccess: () => { qc.invalidateQueries({queryKey:['admin-notifications']}); setMsg(''); },
  });
  const readMut = useMutation({
    mutationFn: (id:number) => apiClient.post(`/notifications/${id}/read`),
    onSuccess: () => qc.invalidateQueries({queryKey:['admin-notifications']}),
  });
  const cleanMut = useMutation({
    mutationFn: () => apiClient.delete('/notifications/messages/clean'),
    onSuccess: () => qc.invalidateQueries({queryKey:['admin-notifications']}),
  });

  return (
    <AdminShell title="通知管理" actions={
      <button onClick={()=>cleanMut.mutate()} className="px-3 py-1.5 text-sm border border-gray-200 rounded-lg hover:bg-gray-50">清理全部</button>
    }>
      {/* Send */}
      <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 p-4 mb-6 flex gap-3">
        <input type="text" value={msg} onChange={e=>setMsg(e.target.value)} placeholder="发送通知..." className="flex-1 px-4 py-2.5 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white"/>
        <button onClick={()=>sendMut.mutate()} disabled={!msg.trim()||sendMut.isPending} className="px-4 py-2.5 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded-xl disabled:opacity-50 flex items-center gap-1.5"><Send className="w-4 h-4"/>{sendMut.isPending?'...':'发送'}</button>
      </div>
      {/* List */}
      <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 overflow-hidden">
        {isLoading ? (
          <div className="p-12 text-center"><div className="animate-spin w-6 h-6 border-2 border-blue-600 border-t-transparent rounded-full mx-auto"/></div>
        ) : !data?.length ? (
          <div className="p-12 text-center text-gray-400"><Bell className="w-10 h-10 mx-auto mb-3 opacity-40"/><p>暂无通知</p></div>
        ) : (
          <div className="divide-y divide-gray-100 dark:divide-gray-800">
            {data.map((n:any,i:number) => (
              <div key={n.id||i} className="px-5 py-4 flex items-center justify-between hover:bg-gray-50 dark:hover:bg-gray-800/50">
                <div className="flex-1 min-w-0"><p className="text-sm text-gray-900 dark:text-white truncate">{n.content||n.message||n.title||'-'}</p><p className="text-xs text-gray-400 mt-0.5">{n.created_at?new Date(n.created_at).toLocaleString('zh-CN'):''}</p></div>
                <div className="flex gap-1.5 shrink-0 ml-3">
                  {!n.is_read && <button onClick={()=>readMut.mutate(n.id)} className="p-1.5 text-gray-400 hover:text-green-600"><Check className="w-4 h-4"/></button>}
                  <button className="p-1.5 text-gray-400 hover:text-red-600"><Trash2 className="w-4 h-4"/></button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </AdminShell>
  );
}
export default function AdminNotifications() { return <AuthGuard><QueryProvider><NotificationsInner/></QueryProvider></AuthGuard>; }
