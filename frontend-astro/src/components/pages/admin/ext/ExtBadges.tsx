'use client';

import React from 'react';
import {useQuery} from '@tanstack/react-query';
import {AuthGuard} from '@/components/AuthGuard';
import {QueryProvider} from '@/components/QueryProvider';
import {AdminShell} from '@/components/admin/AdminShell';
import {apiClient} from '@/lib/api';
import {Award, Medal, Star, TrendingUp} from 'lucide-react';

function ExtBadgesInner() {
  const {data:badges} = useQuery({queryKey:['ext-badges'],queryFn:async()=>{const r=await apiClient.get<any[]>('/ext/badges/available');return r.success&&r.data?(Array.isArray(r.data)?r.data:r.data.badges||[]):[]}});
  const {data:stats}=useQuery({queryKey:['ext-badge-stats'],queryFn:async()=>{const r=await apiClient.get<any>('/ext/badges/admin/stats');return r.success&&r.data?r.data:{}}});
  const {data:cats}=useQuery({queryKey:['ext-badge-cats'],queryFn:async()=>{const r=await apiClient.get<any[]>('/ext/badges/categories');return r.success&&r.data?(Array.isArray(r.data)?r.data:r.data.categories||[]):[]}});

  return (
    <AdminShell title="徽章系统">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <div className="bg-white dark:bg-gray-900 rounded-2xl border p-5"><Award className="w-5 h-5 text-blue-500 mb-2"/><p className="text-2xl font-bold">{stats?.total_badges||badges?.length||0}</p><p className="text-xs text-gray-500">徽章总数</p></div>
        <div className="bg-white dark:bg-gray-900 rounded-2xl border p-5"><Medal className="w-5 h-5 text-purple-500 mb-2"/><p className="text-2xl font-bold">{stats?.awarded_count||'—'}</p><p className="text-xs text-gray-500">已颁发</p></div>
        <div className="bg-white dark:bg-gray-900 rounded-2xl border p-5"><Star className="w-5 h-5 text-yellow-500 mb-2"/><p className="text-2xl font-bold">{stats?.categories||cats?.length||0}</p><p className="text-xs text-gray-500">分类</p></div>
        <div className="bg-white dark:bg-gray-900 rounded-2xl border p-5"><TrendingUp className="w-5 h-5 text-green-500 mb-2"/><p className="text-2xl font-bold">{stats?.recently_awarded||'—'}</p><p className="text-xs text-gray-500">近期授予</p></div>
      </div>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {badges?.map((b:any,i:number)=>(
          <div key={b.badge_key||i} className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 p-5 flex items-start gap-4 hover:shadow-sm transition-shadow">
            <div className={`w-12 h-12 rounded-xl flex items-center justify-center text-2xl ${b.color||'bg-blue-50 dark:bg-blue-900/20'}`}>{b.icon||'🏅'}</div>
            <div className="flex-1 min-w-0"><h3 className="font-semibold text-sm text-gray-900 dark:text-white">{b.name||b.badge_key}</h3><p className="text-xs text-gray-500 mt-0.5">{b.description||''}</p><p className="text-xs text-gray-400 mt-1">{b.category||''}</p></div>
          </div>
        ))}
      </div>
    </AdminShell>
  );
}
export default function ExtBadges(){return <AuthGuard><QueryProvider><ExtBadgesInner/></QueryProvider></AuthGuard>;}
