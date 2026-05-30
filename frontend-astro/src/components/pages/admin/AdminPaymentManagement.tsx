'use client';

import React, {useState} from 'react';
import {useMutation, useQuery, useQueryClient} from '@tanstack/react-query';
import {AuthGuard} from '@/components/AuthGuard';
import {QueryProvider} from '@/components/QueryProvider';
import {AdminShell} from '@/components/admin/AdminShell';
import {DeleteConfirm, EmptyState, Modal} from '@/components/admin/shared-ui';
import {apiClient} from '@/lib/api/api-client';
import {
  ChevronLeft,
  ChevronRight,
  CreditCard,
  DollarSign,
  Edit3,
  FileText,
  Plus,
  Search,
  Settings,
  Trash2
} from 'lucide-react';

/* ─── Types ─────────────────────────────────────── */
interface PaymentGateway {
  id: number;
  name: string;
  provider: string;
  config_data?: string;
  is_active: boolean;
  supported_currencies?: string;
  created_at?: string;
  updated_at?: string;
}

interface PaymentTransaction {
  id: number;
  user_id: number;
  order_id: string;
  gateway_id?: number;
  amount: number;
  currency: string;
  status: string;
  transaction_id?: string;
  payment_method?: string;
  extra_metadata?: string;
  created_at?: string;
  updated_at?: string;
}

interface TaxConfig {
  id: number;
  country: string;
  region?: string;
  tax_type: string;
  rate: number;
  description?: string;
  is_active: boolean;
  effective_from?: string;
  effective_to?: string;
  created_at?: string;
}

interface Pagination {
  page: number;
  per_page: number;
  total: number;
  total_pages: number;
}

/* ─── Helper Components ────────────────────────── */
const Input: React.FC<{
  label: string;
  value: string;
  onChange: (v: string) => void;
  type?: string;
  placeholder?: string;
  rows?: number
}> = ({label, value, onChange, type, placeholder, rows}) => (
  <div className="mb-3">
    <label className="block text-xs font-semibold text-gray-500 dark:text-gray-400 mb-1">{label}</label>
    {rows ? (
      <textarea rows={rows} value={value} onChange={e => onChange(e.target.value)} placeholder={placeholder}
                className="w-full px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white placeholder-gray-400 resize-none"/>
    ) : (
      <input type={type || 'text'} value={value} onChange={e => onChange(e.target.value)} placeholder={placeholder}
             className="w-full px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white placeholder-gray-400"/>
    )}
  </div>
);

const Badge: React.FC<{ active: boolean; activeText?: string; inactiveText?: string }> = ({
                                                                                            active,
                                                                                            activeText = '启用',
                                                                                            inactiveText = '禁用'
                                                                                          }) => (
  <span
    className={`px-2 py-0.5 text-[10px] rounded-full font-medium ${active ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400' : 'bg-gray-100 dark:bg-gray-800 text-gray-500'}`}>
    {active ? activeText : inactiveText}
  </span>
);

const StatusBadge: React.FC<{ status: string }> = ({status}) => {
  const colors: Record<string, string> = {
    completed: 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400',
    pending: 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-400',
    failed: 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400',
    refunded: 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400',
    cancelled: 'bg-gray-100 dark:bg-gray-800 text-gray-500',
  };
  return <span
    className={`px-2 py-0.5 text-[10px] rounded-full font-medium ${colors[status] || 'bg-gray-100 text-gray-500'}`}>{status}</span>;
};

/* ─── Gateways Tab ─────────────────────────────── */
const GatewaysTab: React.FC = () => {
  const qc = useQueryClient();
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<PaymentGateway | null>(null);
  const [deleteId, setDeleteId] = useState<number | null>(null);
  const [form, setForm] = useState({
    name: '',
    provider: '',
    config_data: '{}',
    supported_currencies: '',
    is_active: 'true'
  });

  const {data, isLoading} = useQuery({
    queryKey: ['payment-gateways', page, search],
    queryFn: () => apiClient.get('/payment-management/gateways', {page, per_page: 15, search: search || undefined}),
  });

  const items: PaymentGateway[] = data?.data?.gateways || [];
  const pagination: Pagination | undefined = data?.data?.pagination;

  const createMut = useMutation({
    mutationFn: (d: any) => apiClient.post('/payment-management/gateways', d),
    onSuccess: (r: any) => {
      if (r.success) {
        qc.invalidateQueries({queryKey: ['payment-gateways']});
        setShowForm(false);
      } else alert(r.error);
    },
  });
  const updateMut = useMutation({
    mutationFn: ({id, ...d}: any) => apiClient.put(`/payment-management/gateways/${id}`, d),
    onSuccess: (r: any) => {
      if (r.success) {
        qc.invalidateQueries({queryKey: ['payment-gateways']});
        setShowForm(false);
      } else alert(r.error);
    },
  });
  const deleteMut = useMutation({
    mutationFn: (id: number) => apiClient.delete(`/payment-management/gateways/${id}`),
    onSuccess: (r: any) => {
      if (r.success) {
        qc.invalidateQueries({queryKey: ['payment-gateways']});
        setDeleteId(null);
      } else alert(r.error);
    },
  });

  const openCreate = () => {
    setEditing(null);
    setForm({name: '', provider: '', config_data: '{}', supported_currencies: '', is_active: 'true'});
    setShowForm(true);
  };
  const openEdit = (g: PaymentGateway) => {
    setEditing(g);
    setForm({
      name: g.name,
      provider: g.provider,
      config_data: g.config_data || '{}',
      supported_currencies: g.supported_currencies || '',
      is_active: String(g.is_active)
    });
    setShowForm(true);
  };
  const submit = () => {
    if (!form.name.trim() || !form.provider.trim()) return alert('请填写名称和提供商');
    const payload = {...form, is_active: form.is_active === 'true'};
    if (editing) updateMut.mutate({id: editing.id, ...payload});
    else createMut.mutate(payload);
  };

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
                   placeholder="搜索网关..."
                   className="pl-9 pr-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white w-48"/>
          </div>
        </div>
        <button onClick={openCreate}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded-xl flex items-center gap-1.5">
          <Plus className="w-4 h-4"/>新建网关
        </button>
      </div>
      {isLoading ? <div className="animate-pulse space-y-2">{[1, 2, 3].map(i => <div key={i}
                                                                                     className="h-16 bg-gray-100 dark:bg-gray-800 rounded-xl"/>)}</div> :
        items.length === 0 ?
          <EmptyState icon={CreditCard} title="暂无支付网关" desc="创建第一个支付网关以开始接受支付"/> :
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
              <tr className="border-b border-gray-100 dark:border-gray-800">
                <th className="text-left py-3 px-4 text-xs font-semibold text-gray-500">名称</th>
                <th className="text-left py-3 px-4 text-xs font-semibold text-gray-500">提供商</th>
                <th className="text-left py-3 px-4 text-xs font-semibold text-gray-500">支持货币</th>
                <th className="text-left py-3 px-4 text-xs font-semibold text-gray-500">状态</th>
                <th className="text-right py-3 px-4 text-xs font-semibold text-gray-500">操作</th>
              </tr>
              </thead>
              <tbody>{items.map(g => (
                <tr key={g.id}
                    className="border-b border-gray-50 dark:border-gray-800/50 hover:bg-gray-50 dark:hover:bg-gray-800/30">
                  <td className="py-3 px-4 font-medium text-gray-900 dark:text-white">{g.name}</td>
                  <td className="py-3 px-4 text-gray-600 dark:text-gray-400">{g.provider}</td>
                  <td className="py-3 px-4 text-gray-500 text-xs">{g.supported_currencies || '—'}</td>
                  <td className="py-3 px-4"><Badge active={g.is_active}/></td>
                  <td className="py-3 px-4 text-right">
                    <button onClick={() => openEdit(g)}
                            className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-500 mr-1">
                      <Edit3 className="w-3.5 h-3.5"/></button>
                    <button onClick={() => setDeleteId(g.id)}
                            className="p-1.5 rounded-lg hover:bg-red-50 dark:hover:bg-red-900/20 text-red-500"><Trash2
                      className="w-3.5 h-3.5"/></button>
                  </td>
                </tr>
              ))}</tbody>
            </table>
          </div>}
      {pagination && pagination.total_pages > 1 && (
        <div className="flex items-center justify-between mt-4">
          <span className="text-xs text-gray-500">共 {pagination.total} 条</span>
          <div className="flex items-center gap-1">
            <button disabled={page <= 1} onClick={() => setPage(p => p - 1)}
                    className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 disabled:opacity-30">
              <ChevronLeft className="w-4 h-4"/></button>
            <span className="text-xs text-gray-600 dark:text-gray-400 px-2">{page}/{pagination.total_pages}</span>
            <button disabled={page >= pagination.total_pages} onClick={() => setPage(p => p + 1)}
                    className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 disabled:opacity-30">
              <ChevronRight className="w-4 h-4"/></button>
          </div>
        </div>
      )}
      <Modal open={showForm} onClose={() => setShowForm(false)} title={editing ? '编辑支付网关' : '新建支付网关'}>
        <Input label="名称 *" value={form.name} onChange={v => setForm({...form, name: v})} placeholder="例如：Stripe"/>
        <Input label="提供商 *" value={form.provider} onChange={v => setForm({...form, provider: v})}
               placeholder="例如：stripe"/>
        <Input label="支持货币" value={form.supported_currencies}
               onChange={v => setForm({...form, supported_currencies: v})} placeholder="例如：USD,EUR,CNY"/>
        <Input label="配置数据 (JSON)" value={form.config_data} onChange={v => setForm({...form, config_data: v})}
               rows={3}/>
        <div className="mb-3">
          <label className="block text-xs font-semibold text-gray-500 dark:text-gray-400 mb-1">状态</label>
          <select value={form.is_active} onChange={e => setForm({...form, is_active: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white">
            <option value="true">启用</option>
            <option value="false">禁用</option>
          </select>
        </div>
        <div className="flex justify-end gap-2 mt-4">
          <button onClick={() => setShowForm(false)}
                  className="px-4 py-2 text-sm border border-gray-200 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 text-gray-600 dark:text-gray-300">取消
          </button>
          <button onClick={submit}
                  className="px-4 py-2 text-sm bg-blue-600 hover:bg-blue-700 text-white rounded-lg">{editing ? '更新' : '创建'}</button>
        </div>
      </Modal>
      {deleteId !== null && (
        <Modal open={true} onClose={() => setDeleteId(null)} title="确认删除">
          <DeleteConfirm itemName={items.find(g => g.id === deleteId)?.name}
                         onConfirm={() => deleteMut.mutate(deleteId)} onCancel={() => setDeleteId(null)}
                         isPending={deleteMut.isPending}/>
        </Modal>
      )}
    </>
  );
};

/* ─── Transactions Tab ─────────────────────────── */
const TransactionsTab: React.FC = () => {
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');

  const {data, isLoading} = useQuery({
    queryKey: ['payment-transactions', page, search, statusFilter],
    queryFn: () => apiClient.get('/payment-management/transactions', {
      page,
      per_page: 15,
      search: search || undefined,
      status: statusFilter || undefined
    }),
  });

  const items: PaymentTransaction[] = data?.data?.transactions || [];
  const pagination: Pagination | undefined = data?.data?.pagination;

  return (
    <>
      <div className="flex items-center gap-2 mb-4">
        <div className="relative flex-1 max-w-xs">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400"/>
          <input value={search} onChange={e => {
            setSearch(e.target.value);
            setPage(1);
          }}
                 placeholder="搜索订单号..."
                 className="pl-9 pr-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white w-full"/>
        </div>
        <select value={statusFilter} onChange={e => {
          setStatusFilter(e.target.value);
          setPage(1);
        }}
                className="px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white">
          <option value="">全部状态</option>
          <option value="pending">待处理</option>
          <option value="completed">已完成</option>
          <option value="failed">失败</option>
          <option value="refunded">已退款</option>
          <option value="cancelled">已取消</option>
        </select>
      </div>
      {isLoading ? <div className="animate-pulse space-y-2">{[1, 2, 3].map(i => <div key={i}
                                                                                     className="h-16 bg-gray-100 dark:bg-gray-800 rounded-xl"/>)}</div> :
        items.length === 0 ? <EmptyState icon={DollarSign} title="暂无交易记录" desc="尚无支付交易数据"/> :
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
              <tr className="border-b border-gray-100 dark:border-gray-800">
                <th className="text-left py-3 px-4 text-xs font-semibold text-gray-500">ID</th>
                <th className="text-left py-3 px-4 text-xs font-semibold text-gray-500">订单号</th>
                <th className="text-left py-3 px-4 text-xs font-semibold text-gray-500">金额</th>
                <th className="text-left py-3 px-4 text-xs font-semibold text-gray-500">状态</th>
                <th className="text-left py-3 px-4 text-xs font-semibold text-gray-500">支付方式</th>
                <th className="text-left py-3 px-4 text-xs font-semibold text-gray-500">创建时间</th>
              </tr>
              </thead>
              <tbody>{items.map(t => (
                <tr key={t.id}
                    className="border-b border-gray-50 dark:border-gray-800/50 hover:bg-gray-50 dark:hover:bg-gray-800/30">
                  <td className="py-3 px-4 font-mono text-xs text-gray-500">#{t.id}</td>
                  <td className="py-3 px-4 font-medium text-gray-900 dark:text-white text-xs">{t.order_id}</td>
                  <td className="py-3 px-4 font-semibold text-gray-900 dark:text-white">{t.amount} {t.currency}</td>
                  <td className="py-3 px-4"><StatusBadge status={t.status}/></td>
                  <td className="py-3 px-4 text-gray-600 dark:text-gray-400">{t.payment_method || '—'}</td>
                  <td
                    className="py-3 px-4 text-xs text-gray-500">{t.created_at ? new Date(t.created_at).toLocaleString('zh-CN') : '—'}</td>
                </tr>
              ))}</tbody>
            </table>
          </div>}
      {pagination && pagination.total_pages > 1 && (
        <div className="flex items-center justify-between mt-4">
          <span className="text-xs text-gray-500">共 {pagination.total} 条</span>
          <div className="flex items-center gap-1">
            <button disabled={page <= 1} onClick={() => setPage(p => p - 1)}
                    className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 disabled:opacity-30">
              <ChevronLeft className="w-4 h-4"/></button>
            <span className="text-xs text-gray-600 dark:text-gray-400 px-2">{page}/{pagination.total_pages}</span>
            <button disabled={page >= pagination.total_pages} onClick={() => setPage(p => p + 1)}
                    className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 disabled:opacity-30">
              <ChevronRight className="w-4 h-4"/></button>
          </div>
        </div>
      )}
    </>
  );
};

/* ─── Tax Configs Tab ──────────────────────────── */
const TaxConfigsTab: React.FC = () => {
  const qc = useQueryClient();
  const [page, setPage] = useState(1);
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<TaxConfig | null>(null);
  const [deleteId, setDeleteId] = useState<number | null>(null);
  const [form, setForm] = useState({
    country: '',
    region: '',
    tax_type: 'VAT',
    rate: '',
    description: '',
    is_active: 'true'
  });

  const {data, isLoading} = useQuery({
    queryKey: ['tax-configs', page],
    queryFn: () => apiClient.get('/payment-management/tax-configs', {page, per_page: 15}),
  });

  const items: TaxConfig[] = data?.data?.tax_configs || [];
  const pagination: Pagination | undefined = data?.data?.pagination;

  const createMut = useMutation({
    mutationFn: (d: any) => apiClient.post('/payment-management/tax-configs', d),
    onSuccess: (r: any) => {
      if (r.success) {
        qc.invalidateQueries({queryKey: ['tax-configs']});
        setShowForm(false);
      } else alert(r.error);
    },
  });
  const updateMut = useMutation({
    mutationFn: ({id, ...d}: any) => apiClient.put(`/payment-management/tax-configs/${id}`, d),
    onSuccess: (r: any) => {
      if (r.success) {
        qc.invalidateQueries({queryKey: ['tax-configs']});
        setShowForm(false);
      } else alert(r.error);
    },
  });
  const deleteMut = useMutation({
    mutationFn: (id: number) => apiClient.delete(`/payment-management/tax-configs/${id}`),
    onSuccess: (r: any) => {
      if (r.success) {
        qc.invalidateQueries({queryKey: ['tax-configs']});
        setDeleteId(null);
      } else alert(r.error);
    },
  });

  const openCreate = () => {
    setEditing(null);
    setForm({country: '', region: '', tax_type: 'VAT', rate: '', description: '', is_active: 'true'});
    setShowForm(true);
  };
  const openEdit = (t: TaxConfig) => {
    setEditing(t);
    setForm({
      country: t.country,
      region: t.region || '',
      tax_type: t.tax_type,
      rate: String(t.rate),
      description: t.description || '',
      is_active: String(t.is_active)
    });
    setShowForm(true);
  };
  const submit = () => {
    if (!form.country.trim() || !form.rate) return alert('请填写国家和税率');
    const payload = {...form, rate: parseFloat(form.rate), is_active: form.is_active === 'true'};
    if (editing) updateMut.mutate({id: editing.id, ...payload});
    else createMut.mutate(payload);
  };

  return (
    <>
      <div className="flex items-center justify-end mb-4">
        <button onClick={openCreate}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded-xl flex items-center gap-1.5">
          <Plus className="w-4 h-4"/>新建税务配置
        </button>
      </div>
      {isLoading ? <div className="animate-pulse space-y-2">{[1, 2, 3].map(i => <div key={i}
                                                                                     className="h-16 bg-gray-100 dark:bg-gray-800 rounded-xl"/>)}</div> :
        items.length === 0 ? <EmptyState icon={FileText} title="暂无税务配置" desc="创建税务配置以自动计算税费"/> :
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
              <tr className="border-b border-gray-100 dark:border-gray-800">
                <th className="text-left py-3 px-4 text-xs font-semibold text-gray-500">国家</th>
                <th className="text-left py-3 px-4 text-xs font-semibold text-gray-500">地区</th>
                <th className="text-left py-3 px-4 text-xs font-semibold text-gray-500">税种</th>
                <th className="text-left py-3 px-4 text-xs font-semibold text-gray-500">税率</th>
                <th className="text-left py-3 px-4 text-xs font-semibold text-gray-500">状态</th>
                <th className="text-right py-3 px-4 text-xs font-semibold text-gray-500">操作</th>
              </tr>
              </thead>
              <tbody>{items.map(t => (
                <tr key={t.id}
                    className="border-b border-gray-50 dark:border-gray-800/50 hover:bg-gray-50 dark:hover:bg-gray-800/30">
                  <td className="py-3 px-4 font-medium text-gray-900 dark:text-white">{t.country}</td>
                  <td className="py-3 px-4 text-gray-600 dark:text-gray-400">{t.region || '—'}</td>
                  <td className="py-3 px-4 text-gray-600 dark:text-gray-400">{t.tax_type}</td>
                  <td className="py-3 px-4 font-semibold text-gray-900 dark:text-white">{(t.rate * 100).toFixed(1)}%
                  </td>
                  <td className="py-3 px-4"><Badge active={t.is_active}/></td>
                  <td className="py-3 px-4 text-right">
                    <button onClick={() => openEdit(t)}
                            className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-500 mr-1">
                      <Edit3 className="w-3.5 h-3.5"/></button>
                    <button onClick={() => setDeleteId(t.id)}
                            className="p-1.5 rounded-lg hover:bg-red-50 dark:hover:bg-red-900/20 text-red-500"><Trash2
                      className="w-3.5 h-3.5"/></button>
                  </td>
                </tr>
              ))}</tbody>
            </table>
          </div>}
      {pagination && pagination.total_pages > 1 && (
        <div className="flex items-center justify-between mt-4">
          <span className="text-xs text-gray-500">共 {pagination.total} 条</span>
          <div className="flex items-center gap-1">
            <button disabled={page <= 1} onClick={() => setPage(p => p - 1)}
                    className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 disabled:opacity-30">
              <ChevronLeft className="w-4 h-4"/></button>
            <span className="text-xs text-gray-600 dark:text-gray-400 px-2">{page}/{pagination.total_pages}</span>
            <button disabled={page >= pagination.total_pages} onClick={() => setPage(p => p + 1)}
                    className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 disabled:opacity-30">
              <ChevronRight className="w-4 h-4"/></button>
          </div>
        </div>
      )}
      <Modal open={showForm} onClose={() => setShowForm(false)} title={editing ? '编辑税务配置' : '新建税务配置'}>
        <Input label="国家 *" value={form.country} onChange={v => setForm({...form, country: v})}
               placeholder="例如：CN"/>
        <Input label="地区" value={form.region} onChange={v => setForm({...form, region: v})} placeholder="例如：上海"/>
        <Input label="税种" value={form.tax_type} onChange={v => setForm({...form, tax_type: v})}
               placeholder="例如：VAT"/>
        <Input label="税率 (小数) *" value={form.rate} onChange={v => setForm({...form, rate: v})} type="number"
               placeholder="例如：0.13 表示 13%"/>
        <Input label="描述" value={form.description} onChange={v => setForm({...form, description: v})} rows={2}/>
        <div className="mb-3">
          <label className="block text-xs font-semibold text-gray-500 dark:text-gray-400 mb-1">状态</label>
          <select value={form.is_active} onChange={e => setForm({...form, is_active: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white">
            <option value="true">启用</option>
            <option value="false">禁用</option>
          </select>
        </div>
        <div className="flex justify-end gap-2 mt-4">
          <button onClick={() => setShowForm(false)}
                  className="px-4 py-2 text-sm border border-gray-200 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 text-gray-600 dark:text-gray-300">取消
          </button>
          <button onClick={submit}
                  className="px-4 py-2 text-sm bg-blue-600 hover:bg-blue-700 text-white rounded-lg">{editing ? '更新' : '创建'}</button>
        </div>
      </Modal>
      {deleteId !== null && (
        <Modal open={true} onClose={() => setDeleteId(null)} title="确认删除">
          <DeleteConfirm itemName={items.find(t => t.id === deleteId)?.country}
                         onConfirm={() => deleteMut.mutate(deleteId)} onCancel={() => setDeleteId(null)}
                         isPending={deleteMut.isPending}/>
        </Modal>
      )}
    </>
  );
};

/* ─── Main Component ───────────────────────────── */
type TabKey = 'gateways' | 'transactions' | 'tax-configs';
const TABS: { key: TabKey; label: string; icon: any }[] = [
  {key: 'gateways', label: '支付网关', icon: CreditCard},
  {key: 'transactions', label: '交易记录', icon: DollarSign},
  {key: 'tax-configs', label: '税务配置', icon: Settings},
];

function PaymentManagementInner() {
  const [tab, setTab] = useState<TabKey>('gateways');

  return (
    <AdminShell title="支付管理" actions={<CreditCard className="w-5 h-5 text-blue-500"/>}>
      <div className="space-y-6">
        {/* Tabs */}
        <div className="flex gap-1 bg-gray-100 dark:bg-gray-800 rounded-xl p-1">
          {TABS.map(t => (
            <button key={t.key} onClick={() => setTab(t.key)}
                    className={`flex-1 flex items-center justify-center gap-1.5 px-4 py-2.5 text-sm rounded-lg transition-colors ${tab === t.key ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm font-medium' : 'text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'}`}>
              <t.icon className="w-4 h-4"/>
              {t.label}
            </button>
          ))}
        </div>
        {/* Content */}
        <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 p-5">
          {tab === 'gateways' && <GatewaysTab/>}
          {tab === 'transactions' && <TransactionsTab/>}
          {tab === 'tax-configs' && <TaxConfigsTab/>}
        </div>
      </div>
    </AdminShell>
  );
}

export default function AdminPaymentManagement() {
  return (
    <AuthGuard>
      <QueryProvider>
        <PaymentManagementInner/>
      </QueryProvider>
    </AuthGuard>
  );
}
