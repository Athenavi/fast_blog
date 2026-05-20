'use client';

import React from 'react';
import {useQuery, useMutation, useQueryClient} from '@tanstack/react-query';
import {AuthGuard} from '@/components/AuthGuard';
import {QueryProvider} from '@/components/QueryProvider';
import {AdminShell} from '@/components/admin/AdminShell';
import {apiClient} from '@/lib/api';
import {Plus, Trash2, Play, Pause} from 'lucide-react';

function AdsInner() {
  const qc = useQueryClient();
  const {data, isLoading} = useQuery({
    queryKey: ['admin-ads'],
    queryFn: async () => {
      const r = await apiClient.get('/ads/list');
      return r.success && r.data ? (Array.isArray(r.data) ? r.data : r.data.ads||[]) : [];
    },
  });
  const toggleMut = useMutation({
    mutationFn: ({id, action}:{id:number;action:'activate'|'pause'}) => apiClient.post(`/ads/${id}/${action}`),
    onSuccess: () => qc.invalidateQueries({queryKey: ['admin-ads']}),
  });
  const delMut = useMutation({
    mutationFn: (id:number) => apiClient.delete(`/ads/${id}`),
    onSuccess: () => qc.invalidateQueries({queryKey: ['admin-ads']}),
  });

  return (
    <AdminShell title="广告管理">
      <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 overflow-hidden">
        {isLoading ? (
          <div className="p-12 text-center"><div className="animate-spin w-6 h-6 border-2 border-blue-600 border-t-transparent rounded-full mx-auto"/></div>
        ) : !data?.length ? (
          <div className="p-12 text-center text-gray-400"><NewspaperIcon className="w-10 h-10 mx-auto mb-3 opacity-40"/><p>暂无广告</p></div>
        ) : (
          <table className="w-full"><thead className="bg-gray-50 dark:bg-gray-800 border-b"><tr><th className="px-5 py-3 text-xs font-semibold text-gray-500 uppercase text-left">名称</th><th className="px-5 py-3 text-xs font-semibold text-gray-500 uppercase text-left hidden sm:table-cell">位置</th><th className="px-5 py-3 text-xs font-semibold text-gray-500 uppercase text-left">状态</th><th className="px-5 py-3 text-xs font-semibold text-gray-500 uppercase text-right">操作</th></tr></thead><tbody className="divide-y">
            {data.map((a:any,i:number) => (
              <tr key={a.id||i} className="hover:bg-gray-50 dark:hover:bg-gray-800/50">
                <td className="px-5 py-4"><span className="text-sm font-medium text-gray-900 dark:text-white">{a.name||'广告'}</span></td>
                <td className="px-5 py-4 text-sm text-gray-500 hidden sm:table-cell">{a.slot||a.position||'-'}</td>
                <td className="px-5 py-4"><span className={`px-2 py-0.5 text-xs rounded-full ${a.is_active!==false?'bg-green-100 text-green-700':'bg-gray-100 text-gray-500'}`}>{a.is_active!==false?'投放中':'已暂停'}</span></td>
                <td className="px-5 py-4 text-right">
                  <button onClick={()=>toggleMut.mutate({id:a.id,action:a.is_active!==false?'pause':'activate'})} className="p-1.5 inline-block text-gray-400 hover:text-blue-600">{a.is_active!==false?<Pause className="w-4 h-4"/>:<Play className="w-4 h-4"/>}</button>
                  <button onClick={()=>{if(confirm('删除？'))delMut.mutate(a.id);}} className="p-1.5 inline-block text-gray-400 hover:text-red-600"><Trash2 className="w-4 h-4"/></button>
                </td>
              </tr>
            ))}
          </tbody></table>
        )}
      </div>
    </AdminShell>
  );
}
const NewspaperIcon = ({className}:{className?:string})=><svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10a2 2 0 012 2v1m2 13a2 2 0 01-2-2V7m2 13a2 2 0 002-2V9a2 2 0 00-2-2h-2m-4-3H9M7 16h6M7 8h6v4H7V8z"/></svg>;
export default function AdminAds() { return <AuthGuard><QueryProvider><AdsInner/></QueryProvider></AuthGuard>; }
