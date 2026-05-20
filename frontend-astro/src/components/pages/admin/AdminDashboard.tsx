'use client';

import React from 'react';
import {useQuery} from '@tanstack/react-query';
import {AuthGuard} from '@/components/AuthGuard';
import {QueryProvider} from '@/components/QueryProvider';
import {AdminShell} from '@/components/admin/AdminShell';
import {apiClient} from '@/lib/api/base-client';
import {FileText, Users, MessageSquare, Eye, TrendingUp, Calendar, Activity} from 'lucide-react';

const StatCard: React.FC<{label: string; value: number | string; icon: any; color: string}> = ({label, value, icon: Icon, color}) => (
  <div className={`p-5 rounded-2xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900`}>
    <div className="flex items-center justify-between mb-3">
      <span className="text-sm font-medium text-gray-500">{label}</span>
      <Icon className={`w-5 h-5 text-${color}-500`} />
    </div>
    <p className="text-3xl font-black text-gray-900 dark:text-white">{value ?? '—'}</p>
  </div>
);

function DashboardInner() {
  const {data: stats} = useQuery({
    queryKey: ['admin-dashboard'],
    queryFn: async () => {
      const res = await apiClient.get<{
        articles: number; users: number; comments: number; visitors: number; views_today: number;
      }>('/dashboard/stats');
      return res.success && res.data ? res.data : {};
    },
  });

  const {data: activities} = useQuery({
    queryKey: ['admin-activity'],
    queryFn: async () => {
      const res = await apiClient.get<any[]>('/dashboard/activities', {page: 1, per_page: 8});
      return res.success && res.data ? (Array.isArray(res.data) ? res.data : []) : [];
    },
  });

  return (
    <AdminShell title="仪表盘" actions={
      <a href="/admin/editor" className="px-4 py-1.5 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg transition-colors"><PenSquare className="w-4 h-4 inline mr-1 -mt-0.5"/>写文章</a>
    }>
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatCard label="文章总数" value={stats?.articles ?? '—'} icon={FileText} color="blue" />
        <StatCard label="用户数" value={stats?.users ?? '—'} icon={Users} color="green" />
        <StatCard label="评论数" value={stats?.comments ?? '—'} icon={MessageSquare} color="purple" />
        <StatCard label="今日访问" value={stats?.views_today ?? stats?.visitors ?? '—'} icon={Eye} color="orange" />
      </div>

      <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 p-6">
        <h2 className="font-bold text-gray-900 dark:text-white mb-4 flex items-center gap-2"><Activity className="w-5 h-5"/>最近活动</h2>
        {activities?.length > 0 ? (
          <div className="space-y-3">
            {activities.map((a: any, i: number) => (
              <div key={i} className="flex items-center gap-3 text-sm">
                <div className="w-2 h-2 rounded-full bg-blue-500 flex-shrink-0"/>
                <span className="flex-1 text-gray-700 dark:text-gray-300">{a.message || a.action || '-'}</span>
                <span className="text-gray-400 text-xs flex-shrink-0">{a.created_at ? new Date(a.created_at).toLocaleString('zh-CN') : ''}</span>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-gray-400 text-sm text-center py-8">暂无活动记录</p>
        )}
      </div>
    </AdminShell>
  );
}

export default function AdminDashboard() {
  return <AuthGuard><QueryProvider><DashboardInner /></QueryProvider></AuthGuard>;
}

const PenSquare = ({className}: {className?: string}) => <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/></svg>;
