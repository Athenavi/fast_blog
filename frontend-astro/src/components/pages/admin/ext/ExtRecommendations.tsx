'use client';

import React from 'react';
import {useQuery} from '@tanstack/react-query';
import {AuthGuard} from '@/components/AuthGuard';
import {QueryProvider} from '@/components/QueryProvider';
import {AdminShell} from '@/components/admin/AdminShell';
import {apiClient} from '@/lib/api';
import {TrendingUp, Zap, Star, Sparkles} from 'lucide-react';

function ExtRecInner() {
  const {data:trending}=useQuery({queryKey:['ext-rec-trending'],queryFn:async()=>{const r=await apiClient.get<any[]>('/ext/recommendations/trending');return r.success&&r.data?(Array.isArray(r.data)?r.data:r.data.articles||[]):[]}});
  const {data:rising}=useQuery({queryKey:['ext-rec-rising'],queryFn:async()=>{const r=await apiClient.get<any[]>('/ext/recommendations/rising-stars');return r.success&&r.data?(Array.isArray(r.data)?r.data:r.data.articles||[]):[]}});

  const Card = ({a}:{a:any}) => (
    <div className="flex items-center gap-3 p-3 bg-gray-50 dark:bg-gray-800 rounded-xl">
      <div className="flex-1 min-w-0"><p className="text-sm font-medium text-gray-900 dark:text-white truncate">{a.title}</p><p className="text-xs text-gray-400 mt-0.5">{a.views||0} 阅读 · {a.likes||0} 赞</p></div>
      <span className="text-xs text-gray-500 px-2 py-0.5 bg-white dark:bg-gray-700 rounded-full">{a.category||'—'}</span>
    </div>
  );

  return (
    <AdminShell title="推荐系统">
      <div className="grid lg:grid-cols-2 gap-6">
        <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 overflow-hidden">
          <div className="px-5 py-4 border-b flex items-center gap-2"><TrendingUp className="w-5 h-5 text-orange-500"/><span className="font-semibold text-gray-900 dark:text-white">热门文章</span></div>
          {trending?.length>0?<div className="p-4 space-y-2">{trending.map((a:any,i:number)=><Card key={i} a={a}/>)}</div>:<p className="p-8 text-center text-gray-400 text-sm">暂无热门文章</p>}
        </div>
        <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 overflow-hidden">
          <div className="px-5 py-4 border-b flex items-center gap-2"><Star className="w-5 h-5 text-yellow-500"/><span className="font-semibold text-gray-900 dark:text-white">新星文章</span></div>
          {rising?.length>0?<div className="p-4 space-y-2">{rising.map((a:any,i:number)=><Card key={i} a={a}/>)}</div>:<p className="p-8 text-center text-gray-400 text-sm">暂无新星文章</p>}
        </div>
      </div>
    </AdminShell>
  );
}
export default function ExtRecommendations(){return <AuthGuard><QueryProvider><ExtRecInner/></QueryProvider></AuthGuard>;}
