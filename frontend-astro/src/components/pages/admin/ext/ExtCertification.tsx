'use client';

import React from 'react';
import {useQuery, useMutation} from '@tanstack/react-query';
import {AuthGuard} from '@/components/AuthGuard';
import {QueryProvider} from '@/components/QueryProvider';
import {AdminShell} from '@/components/admin/AdminShell';
import {apiClient} from '@/lib/api';
import {ShieldCheck, Users, FileText, Check, X} from 'lucide-react';

function ExtCertInner() {
  const {data:pending}=useQuery({queryKey:['ext-cert-pending'],queryFn:async()=>{const r=await apiClient.get<any[]>('/ext/expert-certification/admin/pending-applications');return r.success&&r.data?(Array.isArray(r.data)?r.data:r.data.applications||[]):[]}});
  const {data:stats}=useQuery({queryKey:['ext-cert-stats'],queryFn:async()=>{const r=await apiClient.get<any>('/ext/expert-certification/admin/stats');return r.success&&r.data?r.data:{}}});
  const {data:fields}=useQuery({queryKey:['ext-cert-fields'],queryFn:async()=>{const r=await apiClient.get<any[]>('/ext/expert-certification/fields');return r.success&&r.data?(Array.isArray(r.data)?r.data:r.data.fields||[]):[]}});
  const reviewMut=useMutation({mutationFn:({id,action}:{id:number;action:'approve'|'reject'})=>apiClient.post('/ext/expert-certification/admin/review',{application_id:id,action})});

  return (
    <AdminShell title="专家认证">
      <div className="grid grid-cols-3 gap-4 mb-6">
        <div className="bg-white dark:bg-gray-900 rounded-2xl border p-5"><Users className="w-5 h-5 text-blue-500 mb-2"/><p className="text-2xl font-bold">{stats?.total_experts||'—'}</p><p className="text-xs text-gray-500">认证专家</p></div>
        <div className="bg-white dark:bg-gray-900 rounded-2xl border p-5"><FileText className="w-5 h-5 text-orange-500 mb-2"/><p className="text-2xl font-bold">{pending?.length||0}</p><p className="text-xs text-gray-500">待审核</p></div>
        <div className="bg-white dark:bg-gray-900 rounded-2xl border p-5"><ShieldCheck className="w-5 h-5 text-purple-500 mb-2"/><p className="text-2xl font-bold">{fields?.length||0}</p><p className="text-xs text-gray-500">认证领域</p></div>
      </div>
      <div className="grid lg:grid-cols-2 gap-6">
        <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 overflow-hidden"><h3 className="px-5 py-4 font-semibold text-gray-900 dark:text-white border-b">待审核申请</h3>
          {pending?.length>0?<div className="divide-y">{pending.map((a:any,i:number)=><div key={i} className="px-5 py-4"><div className="flex items-center justify-between mb-2"><span className="font-medium text-sm text-gray-900 dark:text-white">{a.username||'申请者'}</span><span className="text-xs text-gray-400">{a.field||a.expertise||''}</span></div><p className="text-xs text-gray-500 mb-3">{a.reason||a.description||''}</p><div className="flex gap-2"><button onClick={()=>reviewMut.mutate({id:a.id,action:'approve'})} className="px-3 py-1 bg-green-600 text-white text-xs rounded-lg flex items-center gap-1"><Check className="w-3 h-3"/>通过</button><button onClick={()=>reviewMut.mutate({id:a.id,action:'reject'})} className="px-3 py-1 bg-red-600 text-white text-xs rounded-lg flex items-center gap-1"><X className="w-3 h-3"/>拒绝</button></div></div>)}</div>:<p className="p-8 text-center text-gray-400 text-sm">暂无待审核</p>}
        </div>
        <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 p-6"><h3 className="font-semibold text-gray-900 dark:text-white mb-4">认证领域</h3>
          <div className="flex flex-wrap gap-2">{fields?.map((f:any,i:number)=><span key={i} className="px-3 py-1.5 bg-gray-100 dark:bg-gray-800 rounded-lg text-xs font-medium">{f.name||f}</span>)}</div>
        </div>
      </div>
    </AdminShell>
  );
}
export default function ExtCertification(){return <AuthGuard><QueryProvider><ExtCertInner/></QueryProvider></AuthGuard>;}
