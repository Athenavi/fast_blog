'use client';

import React, {useState} from 'react';
import {useMutation, useQuery, useQueryClient} from '@tanstack/react-query';
import {AuthGuard} from '@/components/AuthGuard';
import {QueryProvider} from '@/components/QueryProvider';
import {AdminShell} from '@/components/admin/AdminShell';
import {EmptyState, Modal, Pagination} from '@/components/admin/shared-ui';
import {apiClient} from '@/lib/api/api-client';
import {BarChart3, Check, CheckCircle, Clock, Eye, FileText, X, XCircle} from 'lucide-react';

/* ─── Types ─────────────────────────────────────── */
interface ApprovalRecord {
  id: number;
  content_type: string;
  content_id: number;
  content_title?: string;
  requester_id: number;
  requester_name?: string;
  current_step: number;
  total_steps: number;
  status: string;
  priority?: string;
  reason?: string;
  admin_notes?: string;
  created_at?: string;
  updated_at?: string;
}

interface ApprovalStep {
  id: number;
  record_id: number;
  step_number: number;
  approver_id: number;
  approver_name?: string;
  status: string;
  notes?: string;
  action_at?: string;
}

interface ApprovalStats {
  total_requests: number;
  pending_count: number;
  approved_count: number;
  rejected_count: number;
  cancelled_count: number;
  avg_approval_time_hours?: number;
  by_content_type: { type: string; count: number }[];
}

/* ─── Helper Components ────────────────────────── */
const StatusBadge: React.FC<{ status: string }> = ({status}) => {
  const colors: Record<string, string> = {
    pending: 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-400',
    approved: 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400',
    rejected: 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400',
    cancelled: 'bg-gray-100 dark:bg-gray-800 text-gray-500',
  };
  const labels: Record<string, string> = {
    pending: '待审批', approved: '已通过', rejected: '已拒绝', cancelled: '已取消',
  };
  return (
    <span
      className={`px-2 py-0.5 text-[10px] rounded-full font-medium ${colors[status] || 'bg-gray-100 text-gray-500'}`}>
      {labels[status] || status}
    </span>
  );
};

const PriorityBadge: React.FC<{ priority?: string }> = ({priority}) => {
  if (!priority) return null;
  const colors: Record<string, string> = {
    high: 'bg-red-100 dark:bg-red-900/30 text-red-600',
    medium: 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-600',
    low: 'bg-green-100 dark:bg-green-900/30 text-green-600',
  };
  const labels: Record<string, string> = {high: '高', medium: '中', low: '低'};
  return (
    <span
      className={`px-1.5 py-0.5 text-[10px] rounded-full font-medium ${colors[priority] || 'bg-gray-100 text-gray-500'}`}>
      {labels[priority] || priority}
    </span>
  );
};

const StatCard: React.FC<{
  icon: React.ElementType;
  label: string;
  value: string | number;
  color: string
}> = ({icon: Icon, label, value, color}) => (
  <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-4">
    <div className="flex items-center gap-3">
      <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${color}`}>
        <Icon className="w-5 h-5 text-white"/>
      </div>
      <div>
        <div className="text-xs text-gray-500">{label}</div>
        <div className="text-lg font-semibold text-gray-900 dark:text-gray-100">{value}</div>
      </div>
    </div>
  </div>
);

/* ─── Pending Approvals Tab ─────────────────────── */
const PendingTab: React.FC = () => {
  const qc = useQueryClient();
  const [page, setPage] = useState(1);
  const [typeFilter, setTypeFilter] = useState('');
  const [showDetail, setShowDetail] = useState<ApprovalRecord | null>(null);
  const [actionNotes, setActionNotes] = useState('');

  const {data, isLoading} = useQuery({
    queryKey: ['pending-approvals', page, typeFilter],
    queryFn: () => apiClient.get('/security/content-approval/pending', {
      page, per_page: 15,
      content_type: typeFilter || undefined,
    }),
  });

  const items: ApprovalRecord[] = data?.data?.approvals || data?.data?.items || [];
  const total: number = data?.data?.total || 0;

  const approveMut = useMutation({
    mutationFn: (id: number) => apiClient.post(`/security/content-approval/${id}/approve`, {notes: actionNotes}),
    onSuccess: (r: any) => {
      if (r.success) {
        qc.invalidateQueries({queryKey: ['pending-approvals']});
        setShowDetail(null);
        setActionNotes('');
      } else alert(r.error);
    },
  });
  const rejectMut = useMutation({
    mutationFn: (id: number) => apiClient.post(`/security/content-approval/${id}/reject`, {notes: actionNotes}),
    onSuccess: (r: any) => {
      if (r.success) {
        qc.invalidateQueries({queryKey: ['pending-approvals']});
        setShowDetail(null);
        setActionNotes('');
      } else alert(r.error);
    },
  });
  const cancelMut = useMutation({
    mutationFn: (id: number) => apiClient.post(`/security/content-approval/${id}/cancel`),
    onSuccess: (r: any) => {
      if (r.success) {
        qc.invalidateQueries({queryKey: ['pending-approvals']});
        setShowDetail(null);
      } else alert(r.error);
    },
  });

  const contentTypeLabels: Record<string, string> = {
    article: '文章', page: '页面', comment: '评论', media: '媒体', product: '商品',
  };

  return (
    <>
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <select value={typeFilter} onChange={e => {
            setTypeFilter(e.target.value);
            setPage(1);
          }}
                  className="px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-sm dark:text-white">
            <option value="">全部类型</option>
            {Object.entries(contentTypeLabels).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
        </div>
      </div>

      {isLoading ? (
        <div className="space-y-2">{[...Array(5)].map((_, i) => <div key={i}
                                                                     className="h-20 bg-gray-100 dark:bg-gray-800 rounded-lg animate-pulse"/>)}</div>
      ) : items.length === 0 ? (
        <EmptyState icon={CheckCircle} title="暂无待审批内容" description="所有内容已处理完毕"/>
      ) : (
        <div className="space-y-3">
          {items.map(a => (
            <div key={a.id}
                 className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-5 hover:shadow-md transition-shadow">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <span
                      className="px-2 py-0.5 text-[10px] rounded-full font-medium bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400">
                      {contentTypeLabels[a.content_type] || a.content_type}
                    </span>
                    <PriorityBadge priority={a.priority}/>
                    <StatusBadge status={a.status}/>
                  </div>
                  <h3
                    className="font-semibold text-gray-900 dark:text-gray-100 mb-1">{a.content_title || `内容#${a.content_id}`}</h3>
                  <div className="flex items-center gap-4 text-xs text-gray-500">
                    <span>申请人: {a.requester_name || `用户#${a.requester_id}`}</span>
                    <span>步骤: {a.current_step}/{a.total_steps}</span>
                    <span>申请时间: {a.created_at?.slice(0, 16)}</span>
                  </div>
                  {a.reason && <p className="text-xs text-gray-400 mt-1 line-clamp-1">理由: {a.reason}</p>}
                </div>
                <div className="flex items-center gap-1 ml-4">
                  <button onClick={() => {
                    setShowDetail(a);
                    setActionNotes('');
                  }}
                          className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800" title="查看详情">
                    <Eye className="w-4 h-4 text-gray-500"/>
                  </button>
                  <button onClick={() => {
                    setShowDetail(a);
                    setActionNotes('');
                  }}
                          className="p-2 rounded-lg hover:bg-green-50 dark:hover:bg-green-900/20" title="审批通过">
                    <Check className="w-4 h-4 text-green-500"/>
                  </button>
                  <button onClick={() => {
                    setShowDetail(a);
                    setActionNotes('');
                  }}
                          className="p-2 rounded-lg hover:bg-red-50 dark:hover:bg-red-900/20" title="审批拒绝">
                    <X className="w-4 h-4 text-red-500"/>
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {total > 15 &&
        <div className="mt-4"><Pagination page={page} total={total} perPage={15} onPageChange={setPage}/></div>}

      {/* Detail & Action Modal */}
      <Modal open={showDetail !== null} onClose={() => setShowDetail(null)} title="审批详情">
        {showDetail && (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-gray-500">内容类型：</span>
                <span
                  className="font-medium">{contentTypeLabels[showDetail.content_type] || showDetail.content_type}</span>
              </div>
              <div>
                <span className="text-gray-500">内容ID：</span>
                <span className="font-mono">#{showDetail.content_id}</span>
              </div>
              <div>
                <span className="text-gray-500">申请人：</span>
                <span>{showDetail.requester_name || `#${showDetail.requester_id}`}</span>
              </div>
              <div>
                <span className="text-gray-500">审批进度：</span>
                <span>{showDetail.current_step}/{showDetail.total_steps} 步</span>
              </div>
              <div className="col-span-2">
                <span className="text-gray-500">申请理由：</span>
                <span>{showDetail.reason || '无'}</span>
              </div>
            </div>

            <div className="border-t border-gray-100 dark:border-gray-800 pt-4">
              <label className="block text-xs font-semibold text-gray-500 dark:text-gray-400 mb-1">审批备注</label>
              <textarea rows={3} value={actionNotes} onChange={e => setActionNotes(e.target.value)}
                        placeholder="输入审批意见（可选）"
                        className="w-full px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white resize-none"/>
            </div>

            <div className="flex justify-end gap-2 pt-3 border-t border-gray-100 dark:border-gray-800">
              <button onClick={() => cancelMut.mutate(showDetail.id)} disabled={cancelMut.isPending}
                      className="px-4 py-2 text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg">
                取消申请
              </button>
              <button onClick={() => rejectMut.mutate(showDetail.id)} disabled={rejectMut.isPending}
                      className="px-4 py-2 text-sm bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50">
                {rejectMut.isPending ? '处理中...' : '拒绝'}
              </button>
              <button onClick={() => approveMut.mutate(showDetail.id)} disabled={approveMut.isPending}
                      className="px-4 py-2 text-sm bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50">
                {approveMut.isPending ? '处理中...' : '通过'}
              </button>
            </div>
          </div>
        )}
      </Modal>
    </>
  );
};

/* ─── My Requests Tab ───────────────────────────── */
const MyRequestsTab: React.FC = () => {
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState('');

  const {data, isLoading} = useQuery({
    queryKey: ['my-approval-requests', page, statusFilter],
    queryFn: () => apiClient.get('/security/content-approval/my-requests', {
      page, per_page: 15,
      status: statusFilter || undefined,
    }),
  });

  const items: ApprovalRecord[] = data?.data?.requests || data?.data?.items || [];
  const total: number = data?.data?.total || 0;

  const contentTypeLabels: Record<string, string> = {
    article: '文章', page: '页面', comment: '评论', media: '媒体', product: '商品',
  };

  return (
    <>
      <div className="flex items-center gap-2 mb-4">
        <select value={statusFilter} onChange={e => {
          setStatusFilter(e.target.value);
          setPage(1);
        }}
                className="px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-sm dark:text-white">
          <option value="">全部状态</option>
          <option value="pending">待审批</option>
          <option value="approved">已通过</option>
          <option value="rejected">已拒绝</option>
          <option value="cancelled">已取消</option>
        </select>
      </div>

      {isLoading ? (
        <div className="space-y-2">{[...Array(5)].map((_, i) => <div key={i}
                                                                     className="h-16 bg-gray-100 dark:bg-gray-800 rounded-lg animate-pulse"/>)}</div>
      ) : items.length === 0 ? (
        <EmptyState icon={FileText} title="暂无审批请求" description="您提交的审批请求将在此显示"/>
      ) : (
        <div
          className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 overflow-hidden">
          <table className="w-full text-sm">
            <thead>
            <tr className="bg-gray-50 dark:bg-gray-800/50">
              <th className="text-left px-4 py-3 font-medium text-gray-500">内容</th>
              <th className="text-left px-4 py-3 font-medium text-gray-500">类型</th>
              <th className="text-center px-4 py-3 font-medium text-gray-500">进度</th>
              <th className="text-center px-4 py-3 font-medium text-gray-500">状态</th>
              <th className="text-left px-4 py-3 font-medium text-gray-500">申请时间</th>
              <th className="text-left px-4 py-3 font-medium text-gray-500">备注</th>
            </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
            {items.map(r => (
              <tr key={r.id} className="hover:bg-gray-50 dark:hover:bg-gray-800/30">
                <td
                  className="px-4 py-3 font-medium text-gray-900 dark:text-gray-100">{r.content_title || `#${r.content_id}`}</td>
                <td className="px-4 py-3">
                    <span
                      className="px-2 py-0.5 text-[10px] rounded-full font-medium bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400">
                      {contentTypeLabels[r.content_type] || r.content_type}
                    </span>
                </td>
                <td className="px-4 py-3 text-center text-xs text-gray-500">{r.current_step}/{r.total_steps}</td>
                <td className="px-4 py-3 text-center"><StatusBadge status={r.status}/></td>
                <td className="px-4 py-3 text-xs text-gray-500">{r.created_at?.slice(0, 16)}</td>
                <td className="px-4 py-3 text-xs text-gray-400 max-w-[150px] truncate">{r.admin_notes || '-'}</td>
              </tr>
            ))}
            </tbody>
          </table>
          {total > 15 && (
            <div className="p-3 border-t border-gray-100 dark:border-gray-800">
              <Pagination page={page} total={total} perPage={15} onPageChange={setPage}/>
            </div>
          )}
        </div>
      )}
    </>
  );
};

/* ─── History Tab ────────────────────────────────── */
const HistoryTab: React.FC = () => {
  const [page, setPage] = useState(1);
  const [selectedRecord, setSelectedRecord] = useState<number | null>(null);

  const {data, isLoading} = useQuery({
    queryKey: ['approval-history', page],
    queryFn: () => apiClient.get('/security/content-approval/stats'),
  });

  const stats: ApprovalStats = data?.data || {};

  const {data: historyData, isLoading: historyLoading} = useQuery({
    queryKey: ['approval-record-history', selectedRecord],
    queryFn: () => selectedRecord ? apiClient.get(`/security/content-approval/${selectedRecord}/history`) : null,
    enabled: !!selectedRecord,
  });

  const historySteps: ApprovalStep[] = historyData?.data?.steps || [];

  return (
    <div className="space-y-6">
      {isLoading ? (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => <div key={i}
                                            className="h-20 bg-gray-100 dark:bg-gray-800 rounded-lg animate-pulse"/>)}
        </div>
      ) : (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard icon={FileText} label="总申请数" value={stats.total_requests || 0} color="bg-blue-500"/>
          <StatCard icon={Clock} label="待审批" value={stats.pending_count || 0} color="bg-yellow-500"/>
          <StatCard icon={CheckCircle} label="已通过" value={stats.approved_count || 0} color="bg-green-500"/>
          <StatCard icon={XCircle} label="已拒绝" value={stats.rejected_count || 0} color="bg-red-500"/>
        </div>
      )}

      <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-5">
        <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-4">按内容类型统计</h3>
        <div className="space-y-3">
          {(stats.by_content_type || []).map(ct => (
            <div key={ct.type} className="flex items-center gap-3">
              <span className="text-xs text-gray-500 w-16">{ct.type}</span>
              <div className="flex-1 bg-gray-100 dark:bg-gray-800 rounded-full h-4 overflow-hidden">
                <div className="h-full bg-blue-500 rounded-full"
                     style={{width: `${Math.min((ct.count / (stats.total_requests || 1)) * 100, 100)}%`}}/>
              </div>
              <span className="text-xs font-medium text-gray-700 dark:text-gray-300 w-8 text-right">{ct.count}</span>
            </div>
          ))}
          {(!stats.by_content_type || stats.by_content_type.length === 0) && (
            <p className="text-xs text-gray-400 text-center py-2">暂无数据</p>
          )}
        </div>
      </div>
    </div>
  );
};

/* ─── Main Component ────────────────────────────── */
const AdminContentApprovalInner: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'pending' | 'my-requests' | 'history'>('pending');

  const tabs = [
    {key: 'pending' as const, label: '待审批', icon: Clock},
    {key: 'my-requests' as const, label: '我的申请', icon: FileText},
    {key: 'history' as const, label: '统计历史', icon: BarChart3},
  ];

  return (
    <AdminShell title="内容审批管理" actions={
      <div className="flex bg-gray-100 dark:bg-gray-800 rounded-lg p-0.5">
        {tabs.map(t => (
          <button key={t.key} onClick={() => setActiveTab(t.key)}
                  className={`px-3 py-1.5 text-sm rounded-md transition-colors ${activeTab === t.key ? 'bg-white dark:bg-gray-700 shadow-sm text-gray-900 dark:text-white' : 'text-gray-500 hover:text-gray-700'}`}>
            <t.icon className="w-4 h-4 inline mr-1"/>
            {t.label}
          </button>
        ))}
      </div>
    }>
      <div className="p-6 max-w-7xl mx-auto">
        {activeTab === 'pending' && <PendingTab/>}
        {activeTab === 'my-requests' && <MyRequestsTab/>}
        {activeTab === 'history' && <HistoryTab/>}
      </div>
    </AdminShell>
  );
};

export default function AdminContentApproval() {
  return (
    <AuthGuard>
      <QueryProvider>
        <AdminContentApprovalInner/>
      </QueryProvider>
    </AuthGuard>
  );
}
