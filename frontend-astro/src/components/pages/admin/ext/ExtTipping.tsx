'use client';

import React from 'react';
import {useQuery, useMutation} from '@tanstack/react-query';
import {AuthGuard} from '@/components/AuthGuard';
import {QueryProvider} from '@/components/QueryProvider';
import {AdminShell} from '@/components/admin/AdminShell';
import {apiClient} from '@/lib/api';
import {Coins, TrendingUp, Users, DollarSign, Check, X} from 'lucide-react';

function ExtTippingInner() {
  const {data:stats}=useQuery({queryKey:['ext-tip-stats'],queryFn:async()=>{const r=await apiClient.get<any>('/ext/tipping/my-stats');return r.success&&r.data?r.data:{}}});
  const {data:recent}=useQuery({queryKey:['ext-tip-recent'],queryFn:async()=>{const r=await apiClient.get<any[]>('/ext/tipping/recent');return r.success&&r.data?(Array.isArray(r.data)?r.data:r.data.tips||[]):[]}});
  const {data:withdrawals}=useQuery({queryKey:['ext-tip-withdrawals'],queryFn:async()=>{const r=await apiClient.get<any[]>('/ext/tipping/my-withdrawals');return r.success&&r.data?(Array.isArray(r.data)?r.data:r.data.withdrawals||[]):[]}});
  const processMut=useMutation({mutationFn:(id:number)=>apiClient.post('/ext/tipping/admin/process-withdrawal',{withdrawal_id:id})});

  return (
    <AdminShell title="打赏系统">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <div className="bg-white dark:bg-gray-900 rounded-2xl border p-5"><DollarSign className="w-5 h-5 text-green-500 mb-2"/><p className="text-2xl font-bold">{stats?.total_received||'—'}</p><p className="text-xs text-gray-500">总收入</p></div>
        <div className="bg-white dark:bg-gray-900 rounded-2xl border p-5"><Coins className="w-5 h-5 text-yellow-500 mb-2"/><p className="text-2xl font-bold">{stats?.balance||'—'}</p><p className="text-xs text-gray-500">可提现</p></div>
        <div className="bg-white dark:bg-gray-900 rounded-2xl border p-5"><TrendingUp className="w-5 h-5 text-blue-500 mb-2"/><p className="text-2xl font-bold">{stats?.total_tips||'—'}</p><p className="text-xs text-gray-500">打赏次数</p></div>
        <div className="bg-white dark:bg-gray-900 rounded-2xl border p-5"><Users className="w-5 h-5 text-purple-500 mb-2"/><p className="text-2xl font-bold">{stats?.tippers||'—'}</p><p className="text-xs text-gray-500">打赏者</p></div>
      </div>
      <div className="grid lg:grid-cols-2 gap-6">
        <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 overflow-hidden">
          <h3 className="px-5 py-4 font-semibold text-gray-900 dark:text-white border-b">最近打赏</h3>
          {recent?.length>0?<div className="divide-y">{recent.map((t:any,i:number)=><div key={i} className="px-5 py-3 flex justify-between text-sm"><span className="text-gray-900 dark:text-white">{t.from_username||'匿名'}</span><span className="font-medium text-green-600">+¥{t.amount||t.amount_usd||'—'}</span></div>)}</div>:<p className="p-8 text-center text-gray-400 text-sm">暂无打赏</p>}
        </div>
        <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 overflow-hidden">
          <h3 className="px-5 py-4 font-semibold text-gray-900 dark:text-white border-b">提现申请</h3>
          {withdrawals?.length>0?<div className="divide-y">{withdrawals.map((w:any,i:number)=><div key={i} className="px-5 py-3 flex items-center justify-between"><div><p className="text-sm font-medium text-gray-900 dark:text-white">¥{w.amount}</p><p className="text-xs text-gray-500">{w.created_at?new Date(w.created_at).toLocaleDateString('zh-CN'):''}</p></div><div className="flex items-center gap-2">{w.status==='pending'?<button onClick={()=>processMut.mutate(w.id)} className="px-3 py-1 bg-blue-600 text-white text-xs rounded-lg">处理</button>:<span className={`px-2 py-0.5 text-xs rounded-full ${w.status==='completed'?'bg-green-100 text-green-700':'bg-gray-100 text-gray-500'}`}>{w.status}</span>}</div></div>)}</div>:<p className="p-8 text-center text-gray-400 text-sm">暂无提现</p>}
        </div>
      </div>
    </AdminShell>
  );
}
export default function ExtTipping(){return <AuthGuard><QueryProvider><ExtTippingInner/></QueryProvider></AuthGuard>;}
