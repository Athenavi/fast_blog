'use client';

import React, {useState} from 'react';
import {useQuery} from '@tanstack/react-query';
import {AuthGuard} from '@/components/AuthGuard';
import {QueryProvider} from '@/components/QueryProvider';
import {AdminShell} from '@/components/admin/AdminShell';
import {apiClient} from '@/lib/api/base-client';
import {ScrollText, Download} from 'lucide-react';

function AuditLogsInner() {
  const [page, setPage] = useState(1);
  const {data, isLoading} = useQuery({
    queryKey: ['admin-audit-logs', page],
    queryFn: async () => {
      const res = await apiClient.get('/security/audit-log/logs', {page, per_page: 20});
      return res.success && res.data ? res.data : {logs: [], total: 0};
    },
  });
  const logs = Array.isArray(data?.logs) ? data.logs : Array.isArray(data) ? data : [];

  return (
    <AdminShell title="审计日志">
      <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 overflow-hidden">
        {isLoading ? (
          <div className="p-12 text-center"><div className="animate-spin w-6 h-6 border-2 border-blue-600 border-t-transparent rounded-full mx-auto"/></div>
        ) : !logs.length ? (
          <div className="p-12 text-center text-gray-400"><ScrollText className="w-10 h-10 mx-auto mb-3 opacity-50"/><p>暂无审计日志</p></div>
        ) : (
          <table className="w-full"><thead className="bg-gray-50 dark:bg-gray-800 border-b">
            <tr><th className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase">用户</th><th className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase">动作</th><th className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase hidden sm:table-cell">详情</th><th className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase hidden md:table-cell">IP</th><th className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase">时间</th></tr>
          </thead><tbody className="divide-y">
            {logs.map((log: any, i: number) => (
              <tr key={log.id || i} className="hover:bg-gray-50 dark:hover:bg-gray-800/50 text-sm">
                <td className="px-5 py-3 text-gray-900 dark:text-white">{log.username || log.user || '-'}</td>
                <td className="px-5 py-3"><span className="px-2 py-0.5 text-xs rounded-full bg-gray-100 dark:bg-gray-800">{log.action || log.event || '-'}</span></td>
                <td className="px-5 py-3 text-gray-500 hidden sm:table-cell max-w-[200px] truncate">{log.details || log.description || '-'}</td>
                <td className="px-5 py-3 text-gray-500 font-mono text-xs hidden md:table-cell">{log.ip_address || log.ip || '-'}</td>
                <td className="px-5 py-3 text-gray-500 whitespace-nowrap">{log.created_at ? new Date(log.created_at).toLocaleString('zh-CN') : '-'}</td>
              </tr>
            ))}
          </tbody></table>
        )}
      </div>
    </AdminShell>
  );
}

export default function AdminAuditLogs() {
  return <AuthGuard><QueryProvider><AuditLogsInner /></QueryProvider></AuthGuard>;
}
