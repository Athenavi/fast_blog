'use client';

import React from 'react';
import {useQuery} from '@tanstack/react-query';
import {AuthGuard} from '@/components/AuthGuard';
import {QueryProvider} from '@/components/QueryProvider';
import {AdminShell} from '@/components/admin/AdminShell';
import {apiClient} from '@/lib/api/base-client';
import {TrendingUp, Eye, MousePointerClick, Globe, Smartphone, Monitor} from 'lucide-react';

const StatBox: React.FC<{label: string; value: any; icon: any; sub?: string}> = ({label, value, icon: Icon, sub}) => (
  <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 p-5">
    <div className="flex items-center justify-between mb-2"><span className="text-sm text-gray-500">{label}</span><Icon className="w-5 h-5 text-gray-400"/></div>
    <p className="text-2xl font-bold text-gray-900 dark:text-white">{value ?? '—'}</p>
    {sub && <p className="text-xs text-gray-400 mt-1">{sub}</p>}
  </div>
);

function AnalyticsInner() {
  const {data: overview} = useQuery({
    queryKey: ['admin-analytics'],
    queryFn: async () => {
      const res = await apiClient.get<any>('/dashboard/analytics/overview');
      return res.success && res.data ? res.data : {};
    },
  });
  const {data: traffic} = useQuery({
    queryKey: ['admin-traffic'],
    queryFn: async () => {
      const res = await apiClient.get<any>('/dashboard/traffic');
      return res.success && res.data ? res.data : {};
    },
  });

  return (
    <AdminShell title="数据分析">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <StatBox label="总访问量" value={overview?.total_views ?? traffic?.total_visits} icon={Eye} />
        <StatBox label="独立访客" value={overview?.unique_visitors ?? traffic?.unique_visitors} icon={UsersIcon} />
        <StatBox label="页面浏览量" value={overview?.page_views ?? traffic?.page_views} icon={MousePointerClick} />
        <StatBox label="跳出率" value={overview?.bounce_rate ? `${overview.bounce_rate}%` : '—'} icon={TrendingUp} />
      </div>
      <div className="grid lg:grid-cols-2 gap-6">
        <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 p-6">
          <h3 className="font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2"><Globe className="w-5 h-5"/>流量来源</h3>
          <div className="space-y-3">
            {traffic?.sources ? Object.entries(traffic.sources).map(([k, v]: [string, any]) => (
              <div key={k} className="flex justify-between text-sm"><span className="text-gray-600 capitalize">{k}</span><span className="font-medium">{v}</span></div>
            )) : <p className="text-sm text-gray-400 text-center py-6">暂无数据</p>}
          </div>
        </div>
        <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 p-6">
          <h3 className="font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2"><Monitor className="w-5 h-5"/>设备分布</h3>
          <div className="space-y-3">
            {traffic?.devices ? Object.entries(traffic.devices).map(([k, v]: [string, any]) => (
              <div key={k} className="flex justify-between text-sm"><span className="text-gray-600 capitalize">{k}</span><span className="font-medium">{v}</span></div>
            )) : <p className="text-sm text-gray-400 text-center py-6">暂无数据</p>}
          </div>
        </div>
      </div>
    </AdminShell>
  );
}

const UsersIcon = ({className}: {className?: string}) => <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z"/></svg>;

export default function AdminAnalytics() {
  return <AuthGuard><QueryProvider><AnalyticsInner /></QueryProvider></AuthGuard>;
}
