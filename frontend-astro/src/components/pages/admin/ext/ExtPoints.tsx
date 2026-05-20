'use client';

import React, {useState} from 'react';
import {useQuery, useMutation, useQueryClient} from '@tanstack/react-query';
import {AuthGuard} from '@/components/AuthGuard';
import {QueryProvider} from '@/components/QueryProvider';
import {AdminShell} from '@/components/admin/AdminShell';
import {apiClient} from '@/lib/api';
import {Coins, Plus, Minus, Trophy, History} from 'lucide-react';

function ExtPointsInner() {
  const qc = useQueryClient();
  const [uid, setUid] = useState(''); const [pts, setPts] = useState(''); const [reason, setReason] = useState('');

  const {data:stats}=useQuery({queryKey:['ext-points'],queryFn:async()=>{const r=await apiClient.get<any>('/ext/points/admin/stats');return r.success&&r.data?r.data:{}}});
  const {data:rules}=useQuery({queryKey:['ext-point-rules'],queryFn:async()=>{const r=await apiClient.get<any[]>('/ext/points/points-rules');return r.success&&r.data?(Array.isArray(r.data)?r.data:r.data.rules||[]):[]}});

  const addMut=useMutation({mutationFn:()=>apiClient.post('/ext/points/admin/add-points',{user_id:Number(uid),points:Number(pts),reason}),onSuccess:()=>{qc.invalidateQueries({queryKey:['ext-points']});setUid('');setPts('');setReason('');}});
  const dedMut=useMutation({mutationFn:()=>apiClient.post('/ext/points/admin/deduct-points',{user_id:Number(uid),points:Number(pts),reason})});

  return (
    <AdminShell title="积分系统">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <div className="bg-white dark:bg-gray-900 rounded-2xl border p-5"><Coins className="w-5 h-5 text-yellow-500 mb-2"/><p className="text-2xl font-bold">{stats?.total_points||'—'}</p><p className="text-xs text-gray-500">总积分</p></div>
        <div className="bg-white dark:bg-gray-900 rounded-2xl border p-5"><Plus className="w-5 h-5 text-green-500 mb-2"/><p className="text-2xl font-bold">{stats?.total_given||'—'}</p><p className="text-xs text-gray-500">已发放</p></div>
        <div className="bg-white dark:bg-gray-900 rounded-2xl border p-5"><Trophy className="w-5 h-5 text-orange-500 mb-2"/><p className="text-2xl font-bold">{stats?.users_with_points||'—'}</p><p className="text-xs text-gray-500">活跃用户</p></div>
        <div className="bg-white dark:bg-gray-900 rounded-2xl border p-5"><History className="w-5 h-5 text-blue-500 mb-2"/><p className="text-2xl font-bold">{stats?.total_transactions||'—'}</p><p className="text-xs text-gray-500">交易数</p></div>
      </div>
      <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 p-6 mb-6"><h3 className="font-semibold text-gray-900 dark:text-white mb-4">管理积分</h3>
        <div className="flex flex-wrap gap-3 items-end">
          <div><label className="text-xs text-gray-500 mb-1 block">用户ID</label><input type="number" value={uid} onChange={e=>setUid(e.target.value)} className="w-28 px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-gray-50 dark:bg-gray-800 text-sm"/></div>
          <div><label className="text-xs text-gray-500 mb-1 block">数量</label><input type="number" value={pts} onChange={e=>setPts(e.target.value)} className="w-28 px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-gray-50 dark:bg-gray-800 text-sm"/></div>
          <div><label className="text-xs text-gray-500 mb-1 block">原因</label><input type="text" value={reason} onChange={e=>setReason(e.target.value)} className="w-40 px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-gray-50 dark:bg-gray-800 text-sm"/></div>
          <button onClick={()=>addMut.mutate()} disabled={!uid||!pts} className="px-4 py-2 bg-green-600 text-white text-sm rounded-lg hover:bg-green-700 flex items-center gap-1"><Plus className="w-4 h-4"/>增加</button>
          <button onClick={()=>dedMut.mutate()} disabled={!uid||!pts} className="px-4 py-2 bg-red-600 text-white text-sm rounded-lg hover:bg-red-700 flex items-center gap-1"><Minus className="w-4 h-4"/>扣除</button>
        </div>
      </div>
      {rules?.length>0&&<div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 overflow-hidden"><table className="w-full"><thead className="bg-gray-50 dark:bg-gray-800 border-b"><tr><th className="px-5 py-3 text-xs font-semibold text-gray-500 uppercase text-left">规则</th><th className="px-5 py-3 text-xs font-semibold text-gray-500 uppercase text-left">积分</th><th className="px-5 py-3 text-xs font-semibold text-gray-500 uppercase text-left">限制</th></tr></thead><tbody className="divide-y">{rules.map((r:any,i:number)=><tr key={i} className="hover:bg-gray-50 dark:hover:bg-gray-800/50"><td className="px-5 py-4 text-sm text-gray-900 dark:text-white">{r.name||r.action}</td><td className="px-5 py-4"><span className="px-2 py-0.5 text-xs rounded-full bg-green-100 text-green-700">+{r.points}</span></td><td className="px-5 py-4 text-sm text-gray-500">{r.limit||'不限'}</td></tr>)}</tbody></table></div>}
    </AdminShell>
  );
}
export default function ExtPoints(){return <AuthGuard><QueryProvider><ExtPointsInner/></QueryProvider></AuthGuard>;}
