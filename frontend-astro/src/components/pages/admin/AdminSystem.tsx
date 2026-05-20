'use client';

import React from 'react';
import {useQuery} from '@tanstack/react-query';
import {AuthGuard} from '@/components/AuthGuard';
import {QueryProvider} from '@/components/QueryProvider';
import {AdminShell} from '@/components/admin/AdminShell';
import {apiClient} from '@/lib/api/base-client';
import {Server, Activity, Database, HardDrive, Clock} from 'lucide-react';

function SystemInner() {
  const {data: info} = useQuery({
    queryKey: ['admin-system-info'],
    queryFn: async () => {
      const res = await apiClient.get<any>('/system/info');
      return res.success && res.data ? res.data : {};
    },
  });
  const {data: health} = useQuery({
    queryKey: ['admin-system-health'],
    queryFn: async () => {
      const res = await apiClient.get<any>('/system/health');
      return res.success && res.data ? res.data : {};
    },
  });

  const InfoRow = ({label, value}: {label: string; value: string}) => (
    <div className="flex justify-between py-2.5 border-b border-gray-100 dark:border-gray-800 last:border-0">
      <span className="text-sm text-gray-500">{label}</span><span className="text-sm font-medium text-gray-900 dark:text-white">{value || '—'}</span>
    </div>
  );

  return (
    <AdminShell title="系统信息">
      <div className="grid gap-6 lg:grid-cols-2">
        <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 p-6">
          <h3 className="font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2"><Server className="w-5 h-5"/>系统信息</h3>
          <InfoRow label="操作系统" value={info?.os || info?.platform || '-'} />
          <InfoRow label="Python 版本" value={info?.python_version || '-'} />
          <InfoRow label="主机名" value={info?.hostname || '-'} />
          <InfoRow label="运行时间" value={info?.uptime ? `${info.uptime}h` : '-'} />
        </div>
        <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 p-6">
          <h3 className="font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2"><Activity className="w-5 h-5"/>健康检查</h3>
          {['database', 'cache', 'storage', 'queue'].map(s => (
            <div key={s} className="flex justify-between py-2.5 border-b border-gray-100 dark:border-gray-800 last:border-0">
              <span className="text-sm text-gray-500 capitalize">{s}</span>
              <span className={`px-2 py-0.5 text-xs rounded-full ${health?.[s]?.status === 'ok' || health?.[s] === true ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                {health?.[s]?.status === 'ok' || health?.[s] === true ? '正常' : '异常'}
              </span>
            </div>
          ))}
        </div>
      </div>
    </AdminShell>
  );
}

export default function AdminSystem() {
  return <AuthGuard><QueryProvider><SystemInner /></QueryProvider></AuthGuard>;
}
