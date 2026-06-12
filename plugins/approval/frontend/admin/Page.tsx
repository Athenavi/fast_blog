'use client';

import React, {useState} from 'react';
import {useQuery, useMutation, useQueryClient} from '@tanstack/react-query';
import {AdminShell} from '@/components/admin/AdminShell';
import {apiClient} from '@/lib/api/base-client';
import {Clock, CheckCircle, XCircle, Search, Loader2, AlertCircle} from 'lucide-react';

const API_BASE = '/security/content-approval';

export default function ApprovalPage() {
  const qc = useQueryClient();
  const [tab, setTab] = useState<'pending' | 'my-requests' | 'history'>('pending');
  const [page, setPage] = useState(1);
  const [actionNotes, setActionNotes] = useState('');
  const [actionTarget, setActionTarget] = useState<{id: number; action: 'approve' | 'reject'} | null>(null);

  // ── 待审批 ──
  const {data: pending, isLoading: loadingPending} = useQuery({
    queryKey: ['approval-pending', page],
    queryFn: async () => {
      const r = await apiClient.get(`${API_BASE}/pending`, {page, per_page: 15});
      return r.data || {items: [], total: 0};
    },
    enabled: tab === 'pending',
  });

  // ── 我的申请 ──
  const {data: myReqs, isLoading: loadingMy} = useQuery({
    queryKey: ['approval-my-requests', page],
    queryFn: async () => {
      const r = await apiClient.get(`${API_BASE}/my-requests`, {page, per_page: 15});
      return r.data || {items: [], total: 0};
    },
    enabled: tab === 'my-requests',
  });

  // ── 统计 ──
  const {data: stats, isLoading: loadingStats} = useQuery({
    queryKey: ['approval-stats'],
    queryFn: async () => {
      const r = await apiClient.get(`${API_BASE}/stats`);
      return r.data || {};
    },
    enabled: tab === 'history',
  });

  // ── 操作 Mutation ──
  const actionMut = useMutation({
    mutationFn: async ({id, action, notes}: {id: number; action: string; notes: string}) => {
      await apiClient.post(`${API_BASE}/${id}/${action}`, {notes});
    },
    onSuccess: () => {
      qc.invalidateQueries({queryKey: ['approval-pending']});
      qc.invalidateQueries({queryKey: ['approval-my-requests']});
      qc.invalidateQueries({queryKey: ['approval-stats']});
      setActionTarget(null);
      setActionNotes('');
    },
  });

  const items = tab === 'pending' ? pending : tab === 'my-requests' ? myReqs : null;
  const isLoading = tab === 'pending' ? loadingPending : tab === 'my-requests' ? loadingMy : loadingStats;

  const tabs = [
    {key: 'pending' as const, label: '待审批', icon: Clock},
    {key: 'my-requests' as const, label: '我的申请', icon: CheckCircle},
    {key: 'history' as const, label: '统计概览', icon: AlertCircle},
  ];

  return (
    <AdminShell title="内容审批">
      {/* Tab Bar */}
      <div className="flex gap-2 mb-6">
        {tabs.map(t => (
          <button key={t.key} onClick={() => { setTab(t.key); setPage(1); }}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition flex items-center gap-1.5 ${
              tab === t.key ? 'bg-blue-600 text-white' : 'bg-white dark:bg-gray-900 border hover:bg-gray-50 dark:hover:bg-gray-800'
            }`}>
            <t.icon className="w-4 h-4"/>{t.label}
          </button>
        ))}
      </div>

      {/* Stats (history tab) */}
      {tab === 'history' && stats && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          {[
            {label: '总审批', value: stats.total_pending ?? '—'},
            {label: '已通过', value: stats.total_approved ?? '—'},
            {label: '已拒绝', value: stats.total_rejected ?? '—'},
            {label: '平均耗时', value: stats.avg_hours ? `${Math.round(stats.avg_hours)}h` : '—'},
          ].map(s => (
            <div key={s.label} className="bg-white dark:bg-gray-900 rounded-xl border p-4">
              <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">{s.label}</p>
              <p className="text-2xl font-bold">{s.value}</p>
            </div>
          ))}
        </div>
      )}

      {/* Loading */}
      {isLoading ? (
        <div className="flex justify-center py-16"><Loader2 className="w-8 h-8 animate-spin text-blue-500"/></div>
      ) : (
        <div className="bg-white dark:bg-gray-900 rounded-xl border overflow-hidden">
          {(!items?.items || items.items.length === 0) ? (
            <div className="py-16 text-center text-gray-400">
              <Clock className="w-10 h-10 mx-auto mb-3 opacity-40"/>
              <p className="text-sm">暂无数据</p>
            </div>
          ) : (
            <table className="w-full">
              <thead className="bg-gray-50 dark:bg-gray-800 border-b">
                <tr>
                  <th className="px-5 py-3 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase text-left">内容</th>
                  <th className="px-5 py-3 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase text-left hidden md:table-cell">申请⼈</th>
                  <th className="px-5 py-3 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase text-left hidden sm:table-cell">状态</th>
                  <th className="px-5 py-3 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase text-right">操作</th>
                </tr>
              </thead>
              <tbody className="divide-y dark:divide-gray-800">
                {items.items.map((item: any, i: number) => (
                  <tr key={item.id || i} className="hover:bg-gray-50 dark:hover:bg-gray-800/50">
                    <td className="px-5 py-4">
                      <p className="text-sm font-medium text-gray-900 dark:text-white">{item.content_title || `#${item.content_id}`}</p>
                      <p className="text-xs text-gray-400">{item.content_type} · {item.created_at ? new Date(item.created_at).toLocaleDateString() : ''}</p>
                    </td>
                    <td className="px-5 py-4 text-sm text-gray-500 dark:text-gray-400 hidden md:table-cell">{item.applicant_name || '—'}</td>
                    <td className="px-5 py-4 hidden sm:table-cell">
                      <span className={`px-2 py-0.5 text-xs rounded-full ${
                        item.status === 'approved' ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400' :
                        item.status === 'rejected' ? 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400' :
                        'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-400'
                      }`}>
                        {item.status === 'pending' ? '待审批' : item.status === 'approved' ? '已通过' : '已拒绝'}
                      </span>
                    </td>
                    <td className="px-5 py-4 text-right">
                      {tab === 'pending' && item.status === 'pending' && (
                        <div className="flex gap-2 justify-end">
                          <button onClick={() => setActionTarget({id: item.id, action: 'approve'})}
                            className="px-3 py-1.5 bg-green-600 text-white text-xs rounded-lg hover:bg-green-700 transition">通过</button>
                          <button onClick={() => setActionTarget({id: item.id, action: 'reject'})}
                            className="px-3 py-1.5 bg-red-600 text-white text-xs rounded-lg hover:bg-red-700 transition">拒绝</button>
                        </div>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {/* Action Modal */}
      {actionTarget && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white dark:bg-gray-900 rounded-2xl max-w-md w-full p-6">
            <h3 className="font-semibold text-lg mb-3">{actionTarget.action === 'approve' ? '审批通过' : '拒绝'}</h3>
            <textarea value={actionNotes} onChange={e => setActionNotes(e.target.value)}
              placeholder="审批意见（可选）" rows={3}
              className="w-full px-3 py-2 border rounded-lg text-sm mb-4 bg-white dark:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500"/>
            <div className="flex gap-3 justify-end">
              <button onClick={() => setActionTarget(null)} className="px-4 py-2 border rounded-lg text-sm hover:bg-gray-50 dark:hover:bg-gray-800">取消</button>
              <button onClick={() => actionMut.mutate({id: actionTarget.id, action: actionTarget.action, notes: actionNotes})}
                disabled={actionMut.isPending}
                className={`px-4 py-2 text-sm text-white rounded-lg ${
                  actionTarget.action === 'approve' ? 'bg-green-600 hover:bg-green-700' : 'bg-red-600 hover:bg-red-700'
                }`}>
                {actionMut.isPending ? '处理中...' : '确认'}
              </button>
            </div>
          </div>
        </div>
      )}
    </AdminShell>
  );
}
