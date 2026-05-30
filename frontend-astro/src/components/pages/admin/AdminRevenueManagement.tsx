'use client';

import React, {useState} from 'react';
import {useMutation, useQuery, useQueryClient} from '@tanstack/react-query';
import {AuthGuard} from '@/components/AuthGuard';
import {QueryProvider} from '@/components/QueryProvider';
import {AdminShell} from '@/components/admin/AdminShell';
import {EmptyState, Modal, Pagination} from '@/components/admin/shared-ui';
import {apiClient} from '@/lib/api/api-client';
import {
  Banknote,
  CheckCircle,
  Clock,
  DollarSign,
  Edit3,
  PieChart,
  Search,
  Settings,
  TrendingUp,
  XCircle
} from 'lucide-react';

/* ─── Types ─────────────────────────────────────── */
interface RevenueRecord {
  id: number;
  user_id: number;
  username?: string;
  revenue_type: string;
  amount: number;
  platform_fee: number;
  user_earnings: number;
  description?: string;
  status: string;
  created_at?: string;
}

interface RevenueSharingConfig {
  id: number;
  revenue_type: string;
  platform_percentage: number;
  user_percentage: number;
  min_payout_amount: number;
  payout_cycle: string;
  is_active: boolean;
  description?: string;
}

interface PayoutRequest {
  id: number;
  user_id: number;
  username?: string;
  amount: number;
  payment_method: string;
  payment_account: string;
  status: string;
  admin_notes?: string;
  processed_at?: string;
  created_at?: string;
}

interface UserRevenueStats {
  user_id: number;
  username?: string;
  total_earnings: number;
  total_payouts: number;
  pending_balance: number;
  available_balance: number;
  last_payout_at?: string;
}

/* ─── Helper Components ────────────────────────── */
const MoneyDisplay: React.FC<{ amount: number; className?: string }> = ({amount, className = ''}) => (
  <span className={`font-medium ${className}`}>¥{amount.toFixed(2)}</span>
);

const StatusBadge: React.FC<{ status: string }> = ({status}) => {
  const colors: Record<string, string> = {
    pending: 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-400',
    confirmed: 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400',
    approved: 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400',
    completed: 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400',
    rejected: 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400',
    cancelled: 'bg-gray-100 dark:bg-gray-800 text-gray-500',
  };
  const labels: Record<string, string> = {
    pending: '待处理', confirmed: '已确认', approved: '已批准',
    completed: '已完成', rejected: '已拒绝', cancelled: '已取消',
  };
  return (
    <span
      className={`px-2 py-0.5 text-[10px] rounded-full font-medium ${colors[status] || 'bg-gray-100 text-gray-500'}`}>
      {labels[status] || status}
    </span>
  );
};

const StatCard: React.FC<{ icon: React.ElementType; label: string; value: string; color: string }> = ({
                                                                                                        icon: Icon,
                                                                                                        label,
                                                                                                        value,
                                                                                                        color
                                                                                                      }) => (
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

/* ─── Revenue Records Tab ──────────────────────── */
const RecordsTab: React.FC = () => {
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [typeFilter, setTypeFilter] = useState('');

  const {data, isLoading} = useQuery({
    queryKey: ['revenue-records', page, search, typeFilter],
    queryFn: () => apiClient.get('/shop/revenue/records', {
      page, per_page: 15,
      search: search || undefined,
      revenue_type: typeFilter || undefined,
    }),
  });

  const items: RevenueRecord[] = data?.data?.records || data?.data?.items || [];
  const total: number = data?.data?.total || 0;

  const revenueTypes = ['article_purchase', 'ad_revenue', 'tipping', 'subscription', 'digital_download'];

  return (
    <>
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400"/>
            <input value={search} onChange={e => {
              setSearch(e.target.value);
              setPage(1);
            }}
                   placeholder="搜索用户..."
                   className="pl-9 pr-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-sm dark:text-white w-64"/>
          </div>
          <select value={typeFilter} onChange={e => {
            setTypeFilter(e.target.value);
            setPage(1);
          }}
                  className="px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-sm dark:text-white">
            <option value="">全部类型</option>
            {revenueTypes.map(t => <option key={t} value={t}>{t}</option>)}
          </select>
        </div>
      </div>

      {isLoading ? (
        <div className="space-y-2">{[...Array(5)].map((_, i) => <div key={i}
                                                                     className="h-16 bg-gray-100 dark:bg-gray-800 rounded-lg animate-pulse"/>)}</div>
      ) : items.length === 0 ? (
        <EmptyState icon={DollarSign} title="暂无收益记录" description="收益记录将在产生交易后自动生成"/>
      ) : (
        <div
          className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 overflow-hidden">
          <table className="w-full text-sm">
            <thead>
            <tr className="bg-gray-50 dark:bg-gray-800/50">
              <th className="text-left px-4 py-3 font-medium text-gray-500">用户</th>
              <th className="text-left px-4 py-3 font-medium text-gray-500">类型</th>
              <th className="text-right px-4 py-3 font-medium text-gray-500">总额</th>
              <th className="text-right px-4 py-3 font-medium text-gray-500">平台费用</th>
              <th className="text-right px-4 py-3 font-medium text-gray-500">用户收益</th>
              <th className="text-center px-4 py-3 font-medium text-gray-500">状态</th>
              <th className="text-left px-4 py-3 font-medium text-gray-500">时间</th>
            </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
            {items.map(r => (
              <tr key={r.id} className="hover:bg-gray-50 dark:hover:bg-gray-800/30">
                <td className="px-4 py-3 text-gray-900 dark:text-gray-100">{r.username || `用户#${r.user_id}`}</td>
                <td className="px-4 py-3">
                    <span
                      className="px-2 py-0.5 text-[10px] rounded-full font-medium bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400">
                      {r.revenue_type}
                    </span>
                </td>
                <td className="px-4 py-3 text-right"><MoneyDisplay amount={r.amount}/></td>
                <td className="px-4 py-3 text-right text-gray-500">¥{r.platform_fee.toFixed(2)}</td>
                <td className="px-4 py-3 text-right text-green-600 font-medium">¥{r.user_earnings.toFixed(2)}</td>
                <td className="px-4 py-3 text-center"><StatusBadge status={r.status}/></td>
                <td className="px-4 py-3 text-xs text-gray-500">{r.created_at?.slice(0, 16)}</td>
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

/* ─── Payout Requests Tab ──────────────────────── */
const PayoutsTab: React.FC = () => {
  const qc = useQueryClient();
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState('');

  const {data, isLoading} = useQuery({
    queryKey: ['payout-requests', page, statusFilter],
    queryFn: () => apiClient.get('/shop/revenue/payouts', {
      page, per_page: 15,
      status: statusFilter || undefined,
    }),
  });

  const items: PayoutRequest[] = data?.data?.payouts || data?.data?.items || [];
  const total: number = data?.data?.total || 0;

  const approveMut = useMutation({
    mutationFn: (id: number) => apiClient.post(`/shop/revenue/payouts/${id}/approve`),
    onSuccess: (r: any) => {
      if (r.success) qc.invalidateQueries({queryKey: ['payout-requests']});
      else alert(r.error);
    },
  });
  const completeMut = useMutation({
    mutationFn: (id: number) => apiClient.post(`/shop/revenue/payouts/${id}/complete`),
    onSuccess: (r: any) => {
      if (r.success) qc.invalidateQueries({queryKey: ['payout-requests']});
      else alert(r.error);
    },
  });
  const rejectMut = useMutation({
    mutationFn: (id: number) => apiClient.post(`/shop/revenue/payouts/${id}/reject`),
    onSuccess: (r: any) => {
      if (r.success) qc.invalidateQueries({queryKey: ['payout-requests']});
      else alert(r.error);
    },
  });

  return (
    <>
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <select value={statusFilter} onChange={e => {
            setStatusFilter(e.target.value);
            setPage(1);
          }}
                  className="px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-sm dark:text-white">
            <option value="">全部状态</option>
            <option value="pending">待处理</option>
            <option value="approved">已批准</option>
            <option value="completed">已完成</option>
            <option value="rejected">已拒绝</option>
          </select>
        </div>
      </div>

      {isLoading ? (
        <div className="space-y-2">{[...Array(5)].map((_, i) => <div key={i}
                                                                     className="h-16 bg-gray-100 dark:bg-gray-800 rounded-lg animate-pulse"/>)}</div>
      ) : items.length === 0 ? (
        <EmptyState icon={Banknote} title="暂无提现申请" description="用户发起提现后将在此显示"/>
      ) : (
        <div
          className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 overflow-hidden">
          <table className="w-full text-sm">
            <thead>
            <tr className="bg-gray-50 dark:bg-gray-800/50">
              <th className="text-left px-4 py-3 font-medium text-gray-500">用户</th>
              <th className="text-right px-4 py-3 font-medium text-gray-500">金额</th>
              <th className="text-left px-4 py-3 font-medium text-gray-500">支付方式</th>
              <th className="text-left px-4 py-3 font-medium text-gray-500">收款账户</th>
              <th className="text-center px-4 py-3 font-medium text-gray-500">状态</th>
              <th className="text-left px-4 py-3 font-medium text-gray-500">申请时间</th>
              <th className="text-right px-4 py-3 font-medium text-gray-500">操作</th>
            </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
            {items.map(p => (
              <tr key={p.id} className="hover:bg-gray-50 dark:hover:bg-gray-800/30">
                <td className="px-4 py-3 text-gray-900 dark:text-gray-100">{p.username || `用户#${p.user_id}`}</td>
                <td className="px-4 py-3 text-right font-medium text-green-600">¥{p.amount.toFixed(2)}</td>
                <td className="px-4 py-3 text-gray-500">{p.payment_method}</td>
                <td className="px-4 py-3 text-xs font-mono text-gray-500">{p.payment_account}</td>
                <td className="px-4 py-3 text-center"><StatusBadge status={p.status}/></td>
                <td className="px-4 py-3 text-xs text-gray-500">{p.created_at?.slice(0, 16)}</td>
                <td className="px-4 py-3 text-right">
                  {p.status === 'pending' && (
                    <div className="flex items-center justify-end gap-1">
                      <button onClick={() => approveMut.mutate(p.id)}
                              className="p-1.5 rounded hover:bg-green-50 dark:hover:bg-green-900/20" title="批准">
                        <CheckCircle className="w-3.5 h-3.5 text-green-500"/>
                      </button>
                      <button onClick={() => rejectMut.mutate(p.id)}
                              className="p-1.5 rounded hover:bg-red-50 dark:hover:bg-red-900/20" title="拒绝">
                        <XCircle className="w-3.5 h-3.5 text-red-500"/>
                      </button>
                    </div>
                  )}
                  {p.status === 'approved' && (
                    <button onClick={() => completeMut.mutate(p.id)}
                            className="px-2 py-1 text-xs bg-green-600 text-white rounded hover:bg-green-700">
                      标记完成
                    </button>
                  )}
                </td>
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

/* ─── Config Tab ────────────────────────────────── */
const ConfigTab: React.FC = () => {
  const qc = useQueryClient();
  const [editing, setEditing] = useState<RevenueSharingConfig | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({platform_percentage: '', min_payout_amount: '', payout_cycle: '', description: ''});

  const {data, isLoading} = useQuery({
    queryKey: ['revenue-configs'],
    queryFn: () => apiClient.get('/shop/revenue/configs'),
  });

  const items: RevenueSharingConfig[] = data?.data?.configs || [];

  const updateMut = useMutation({
    mutationFn: ({revenue_type, ...d}: any) => apiClient.put(`/shop/revenue/configs/${revenue_type}`, d),
    onSuccess: (r: any) => {
      if (r.success) {
        qc.invalidateQueries({queryKey: ['revenue-configs']});
        setShowForm(false);
      } else alert(r.error);
    },
  });

  const openEdit = (c: RevenueSharingConfig) => {
    setEditing(c);
    setForm({
      platform_percentage: String(c.platform_percentage),
      min_payout_amount: String(c.min_payout_amount),
      payout_cycle: c.payout_cycle || 'monthly',
      description: c.description || '',
    });
    setShowForm(true);
  };

  const submit = () => {
    if (!editing) return;
    updateMut.mutate({
      revenue_type: editing.revenue_type,
      platform_percentage: parseFloat(form.platform_percentage) || 30,
      min_payout_amount: parseFloat(form.min_payout_amount) || 100,
      payout_cycle: form.payout_cycle,
      description: form.description,
    });
  };

  return (
    <>
      {isLoading ? (
        <div className="space-y-2">{[...Array(3)].map((_, i) => <div key={i}
                                                                     className="h-20 bg-gray-100 dark:bg-gray-800 rounded-lg animate-pulse"/>)}</div>
      ) : items.length === 0 ? (
        <EmptyState icon={Settings} title="暂无分成配置" description="系统将在首次交易时自动生成默认配置"/>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {items.map(c => (
            <div key={c.id}
                 className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-5">
              <div className="flex items-center justify-between mb-3">
                <div>
                  <h3 className="font-semibold text-gray-900 dark:text-gray-100">{c.revenue_type}</h3>
                  {c.description && <p className="text-xs text-gray-500 mt-0.5">{c.description}</p>}
                </div>
                <button onClick={() => openEdit(c)} className="p-1.5 rounded hover:bg-gray-100 dark:hover:bg-gray-800">
                  <Edit3 className="w-4 h-4 text-gray-500"/>
                </button>
              </div>
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <div className="text-xs text-gray-500">平台分成</div>
                  <div className="text-lg font-semibold text-blue-600">{c.platform_percentage}%</div>
                </div>
                <div>
                  <div className="text-xs text-gray-500">用户分成</div>
                  <div className="text-lg font-semibold text-green-600">{(100 - c.platform_percentage).toFixed(1)}%
                  </div>
                </div>
                <div>
                  <div className="text-xs text-gray-500">最低提现</div>
                  <div className="font-medium">¥{c.min_payout_amount.toFixed(2)}</div>
                </div>
                <div>
                  <div className="text-xs text-gray-500">结算周期</div>
                  <div
                    className="font-medium">{c.payout_cycle === 'monthly' ? '每月' : c.payout_cycle === 'weekly' ? '每周' : c.payout_cycle}</div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      <Modal open={showForm} onClose={() => setShowForm(false)} title={`编辑分成配置 - ${editing?.revenue_type}`}>
        <div className="mb-3">
          <label className="block text-xs font-semibold text-gray-500 dark:text-gray-400 mb-1">平台分成比例 (%)</label>
          <input type="number" value={form.platform_percentage}
                 onChange={e => setForm(f => ({...f, platform_percentage: e.target.value}))}
                 className="w-full px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white"/>
          <p
            className="text-xs text-gray-400 mt-1">用户分成将自动设为 {100 - (parseFloat(form.platform_percentage) || 30)}%</p>
        </div>
        <div className="mb-3">
          <label className="block text-xs font-semibold text-gray-500 dark:text-gray-400 mb-1">最低提现金额</label>
          <input type="number" value={form.min_payout_amount}
                 onChange={e => setForm(f => ({...f, min_payout_amount: e.target.value}))}
                 className="w-full px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white"/>
        </div>
        <div className="mb-3">
          <label className="block text-xs font-semibold text-gray-500 dark:text-gray-400 mb-1">结算周期</label>
          <select value={form.payout_cycle} onChange={e => setForm(f => ({...f, payout_cycle: e.target.value}))}
                  className="w-full px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white">
            <option value="weekly">每周</option>
            <option value="biweekly">每两周</option>
            <option value="monthly">每月</option>
          </select>
        </div>
        <div className="mb-3">
          <label className="block text-xs font-semibold text-gray-500 dark:text-gray-400 mb-1">说明</label>
          <textarea rows={2} value={form.description}
                    onChange={e => setForm(f => ({...f, description: e.target.value}))}
                    className="w-full px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white resize-none"/>
        </div>
        <div className="flex justify-end gap-2 mt-4 pt-3 border-t border-gray-100 dark:border-gray-800">
          <button onClick={() => setShowForm(false)}
                  className="px-4 py-2 text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg">取消
          </button>
          <button onClick={submit} disabled={updateMut.isPending}
                  className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50">
            {updateMut.isPending ? '保存中...' : '保存'}
          </button>
        </div>
      </Modal>
    </>
  );
};

/* ─── Platform Stats Tab ────────────────────────── */
const StatsTab: React.FC = () => {
  const {data, isLoading} = useQuery({
    queryKey: ['revenue-platform-stats'],
    queryFn: () => apiClient.get('/shop/revenue/stats/platform'),
  });

  const stats = data?.data || {};

  if (isLoading) {
    return <div className="space-y-4">{[...Array(4)].map((_, i) => <div key={i}
                                                                        className="h-24 bg-gray-100 dark:bg-gray-800 rounded-lg animate-pulse"/>)}</div>;
  }

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard icon={DollarSign} label="总交易额" value={`¥${(stats.total_revenue || 0).toLocaleString()}`}
                  color="bg-blue-500"/>
        <StatCard icon={TrendingUp} label="平台收益" value={`¥${(stats.platform_revenue || 0).toLocaleString()}`}
                  color="bg-green-500"/>
        <StatCard icon={Banknote} label="用户收益" value={`¥${(stats.user_revenue || 0).toLocaleString()}`}
                  color="bg-purple-500"/>
        <StatCard icon={Clock} label="待处理提现" value={`${stats.pending_payouts || 0} 笔`} color="bg-yellow-500"/>
      </div>
      <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-6">
        <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-4">分成比例概览</h3>
        <div className="flex items-center gap-4">
          <div className="flex-1 bg-gray-100 dark:bg-gray-800 rounded-full h-6 overflow-hidden">
            <div className="h-full bg-blue-500 rounded-full flex items-center justify-end pr-2"
                 style={{width: `${stats.platform_ratio || 30}%`}}>
              <span className="text-[10px] text-white font-medium">{stats.platform_ratio || 30}%</span>
            </div>
          </div>
          <span className="text-xs text-gray-500 whitespace-nowrap">平台 | 用户</span>
          <div className="flex-1 bg-gray-100 dark:bg-gray-800 rounded-full h-6 overflow-hidden">
            <div className="h-full bg-green-500 rounded-full flex items-center justify-start pl-2"
                 style={{width: `${100 - (stats.platform_ratio || 30)}%`}}>
              <span className="text-[10px] text-white font-medium">{100 - (stats.platform_ratio || 30)}%</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

/* ─── Main Component ────────────────────────────── */
const AdminRevenueManagementInner: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'records' | 'payouts' | 'config' | 'stats'>('records');

  const tabs = [
    {key: 'records' as const, label: '收益记录', icon: DollarSign},
    {key: 'payouts' as const, label: '提现管理', icon: Banknote},
    {key: 'config' as const, label: '分成配置', icon: Settings},
    {key: 'stats' as const, label: '平台统计', icon: PieChart},
  ];

  return (
    <AdminShell title="收益分成管理" actions={
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
        {activeTab === 'records' && <RecordsTab/>}
        {activeTab === 'payouts' && <PayoutsTab/>}
        {activeTab === 'config' && <ConfigTab/>}
        {activeTab === 'stats' && <StatsTab/>}
      </div>
    </AdminShell>
  );
};

export default function AdminRevenueManagement() {
  return (
    <AuthGuard>
      <QueryProvider>
        <AdminRevenueManagementInner/>
      </QueryProvider>
    </AuthGuard>
  );
}
