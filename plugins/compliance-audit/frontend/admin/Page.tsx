'use client';

import React, {useState} from 'react';
import {useMutation, useQuery} from '@tanstack/react-query';
import {AdminShell} from '@/components/admin/AdminShell';
import {apiClient} from '@/lib/api/base-client';
import {CheckCircle2, Loader2, RefreshCw, Shield, ShieldAlert, ShieldCheck, XCircle} from 'lucide-react';

const PLUGIN_SLUG = 'compliance-audit';

function call(action: string, params: any = {}) {
  return apiClient.post(`/plugins/${PLUGIN_SLUG}/action`, {action, params});
}

interface CheckItem {
  id: number;
  name: string;
  status: 'compliant' | 'non-compliant' | 'not_audited';
  detail: string;
}

interface AuditReport {
  overall_status: string;
  checked_at: string;
  checks: CheckItem[];
}

function ComplianceAuditDashboard() {
  const [userId, setUserId] = useState('');

  const {data: report, isLoading, refetch} = useQuery({
    queryKey: ['compliance-audit'],
    queryFn: async () => {
      const r = await call('check_pci_dss');
      return r.data as AuditReport;
    },
  });

  const auditUserMut = useMutation({
    mutationFn: () => call('check_gdpr', {user_data: {user_id: parseInt(userId, 10) || 0}}),
    onSuccess: () => refetch(),
  });

  const statusIcon = (status: string) => {
    switch (status) {
      case 'compliant':
        return <CheckCircle2 className="w-5 h-5 text-green-500"/>;
      case 'non-compliant':
        return <XCircle className="w-5 h-5 text-red-500"/>;
      default:
        return <Shield className="w-5 h-5 text-gray-400"/>;
    }
  };

  const statusLabel = (status: string) => {
    switch (status) {
      case 'compliant':
        return '合规';
      case 'non-compliant':
        return '不合规';
      default:
        return '未审计';
    }
  };

  const statusColor = (status: string) => {
    switch (status) {
      case 'compliant':
        return 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400';
      case 'non-compliant':
        return 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400';
      default:
        return 'bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400';
    }
  };

  return (
    <AdminShell title="合规审计" actions={
      <button onClick={() => refetch()} disabled={isLoading}
              className="flex items-center gap-1.5 px-4 py-2 border rounded-lg text-sm hover:bg-gray-50 dark:hover:bg-gray-800 disabled:opacity-50">
        <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`}/> 重新审计
      </button>
    }>
      {/* 总体状态 */}
      <div
        className={`mb-6 p-5 rounded-xl border ${report?.overall_status === 'compliant' ? 'bg-green-50 dark:bg-green-900/10 border-green-200 dark:border-green-800' : 'bg-red-50 dark:bg-red-900/10 border-red-200 dark:border-red-800'}`}>
        <div className="flex items-center gap-3">
          {report?.overall_status === 'compliant'
            ? <ShieldCheck className="w-8 h-8 text-green-600 dark:text-green-400"/>
            : <ShieldAlert className="w-8 h-8 text-red-600 dark:text-red-400"/>}
          <div>
            <p className="text-lg font-semibold">
              整体状态：{report?.overall_status === 'compliant' ? '合规' : '不合规'}
            </p>
            <p
              className="text-sm text-gray-500">审计时间：{report?.checked_at ? new Date(report.checked_at).toLocaleString() : '—'}</p>
          </div>
        </div>
      </div>

      {/* 审计项目列表 */}
      {isLoading ? (
        <div className="flex justify-center py-16"><Loader2 className="w-8 h-8 animate-spin text-blue-500"/></div>
      ) : !report?.checks?.length ? (
        <div className="text-center py-16 text-gray-400">
          <Shield className="w-12 h-12 mx-auto mb-4 opacity-50"/>
          <p className="text-sm">暂无审计数据</p>
        </div>
      ) : (
        <div className="bg-white dark:bg-gray-900 rounded-xl border overflow-hidden">
          <div className="divide-y dark:divide-gray-800">
            {report.checks.map((check) => (
              <div key={check.id} className="flex items-start gap-4 px-5 py-4">
                {statusIcon(check.status)}
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900 dark:text-white">{check.name}</p>
                  <p className="text-xs text-gray-400 mt-0.5">{check.detail}</p>
                </div>
                <span
                  className={`px-2.5 py-0.5 rounded-full text-xs font-medium whitespace-nowrap ${statusColor(check.status)}`}>
                  {statusLabel(check.status)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 用户审计输入 */}
      <div className="mt-6 p-5 bg-white dark:bg-gray-900 rounded-xl border">
        <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">审计特定用户数据</h3>
        <div className="flex gap-3">
          <input value={userId} onChange={e => setUserId(e.target.value)}
                 placeholder="输入用户ID"
                 className="flex-1 max-w-xs px-3 py-2 border rounded-lg text-sm bg-white dark:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500"/>
          <button onClick={() => auditUserMut.mutate()} disabled={auditUserMut.isPending || !userId}
                  className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 disabled:opacity-50">
            {auditUserMut.isPending ? '审计中...' : '审计'}
          </button>
        </div>
        {auditUserMut.data && (
          <div className="mt-3 p-3 bg-gray-50 dark:bg-gray-800 rounded-lg text-xs text-gray-600 dark:text-gray-400">
            <pre className="whitespace-pre-wrap">{JSON.stringify(auditUserMut.data, null, 2)}</pre>
          </div>
        )}
      </div>
    </AdminShell>
  );
}

export default function ComplianceAuditPage() {
  return <ComplianceAuditDashboard/>;
}
