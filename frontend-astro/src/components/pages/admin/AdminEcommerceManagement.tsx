'use client';

import React, {useState} from 'react';
import {useMutation, useQuery, useQueryClient} from '@tanstack/react-query';
import {AuthGuard} from '@/components/AuthGuard';
import {QueryProvider} from '@/components/QueryProvider';
import {AdminShell} from '@/components/admin/AdminShell';
import {DeleteConfirm, EmptyState, Modal, Pagination, StatusBadge} from '@/components/admin/shared-ui';
import {apiClient} from '@/lib/api/api-client';
import {Edit3, Eye, Package, Plus, Search, ShoppingCart, Trash2} from 'lucide-react';

/* ─── Types ─────────────────────────────────────── */
interface Product {
  id: number;
  name: string;
  slug: string;
  description?: string;
  price: number;
  compare_price?: number;
  sku?: string;
  stock_quantity: number;
  is_active: boolean;
  is_digital: boolean;
  category?: string;
  image_url?: string;
  created_at?: string;
  updated_at?: string;
}

interface Order {
  id: number;
  order_number: string;
  user_id: number;
  username?: string;
  total_amount: number;
  currency: string;
  status: string;
  payment_status: string;
  payment_method?: string;
  shipping_address?: string;
  tracking_number?: string;
  items_count?: number;
  created_at?: string;
  updated_at?: string;
}

interface OrderItem {
  id: number;
  order_id: number;
  product_id: number;
  product_name: string;
  quantity: number;
  unit_price: number;
  total_price: number;
}

interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

/* ─── Helper Components ────────────────────────── */
const Input: React.FC<{
  label: string;
  value: string;
  onChange: (v: string) => void;
  type?: string;
  placeholder?: string;
  rows?: number;
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

const Select: React.FC<{
  label: string;
  value: string;
  onChange: (v: string) => void;
  options: { value: string; label: string }[];
}> = ({label, value, onChange, options}) => (
  <div className="mb-3">
    <label className="block text-xs font-semibold text-gray-500 dark:text-gray-400 mb-1">{label}</label>
    <select value={value} onChange={e => onChange(e.target.value)}
            className="w-full px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white">
      {options.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
    </select>
  </div>
);

const MoneyDisplay: React.FC<{ amount: number; currency?: string }> = ({amount, currency = 'CNY'}) => (
  <span className="font-medium text-gray-900 dark:text-gray-100">
    {currency === 'CNY' ? '¥' : currency + ' '}{amount.toFixed(2)}
  </span>
);

/* ─── Products Tab ─────────────────────────────── */
const ProductsTab: React.FC = () => {
  const qc = useQueryClient();
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<Product | null>(null);
  const [deleteId, setDeleteId] = useState<number | null>(null);
  const [form, setForm] = useState({
    name: '', slug: '', description: '', price: '', compare_price: '',
    sku: '', stock_quantity: '0', is_active: 'true', is_digital: 'false', category: ''
  });

  const {data, isLoading} = useQuery({
    queryKey: ['products', page, search],
    queryFn: () => apiClient.get('/shop/products', {page, per_page: 15, search: search || undefined}),
  });

  const items: Product[] = data?.data?.products || data?.data?.items || [];
  const total: number = data?.data?.total || 0;

  const createMut = useMutation({
    mutationFn: (d: any) => apiClient.post('/shop/products', d),
    onSuccess: (r: any) => {
      if (r.success) {
        qc.invalidateQueries({queryKey: ['products']});
        setShowForm(false);
      } else alert(r.error);
    },
  });
  const updateMut = useMutation({
    mutationFn: ({id, ...d}: any) => apiClient.put(`/shop/products/${id}`, d),
    onSuccess: (r: any) => {
      if (r.success) {
        qc.invalidateQueries({queryKey: ['products']});
        setShowForm(false);
      } else alert(r.error);
    },
  });
  const deleteMut = useMutation({
    mutationFn: (id: number) => apiClient.delete(`/shop/products/${id}`),
    onSuccess: (r: any) => {
      if (r.success) {
        qc.invalidateQueries({queryKey: ['products']});
        setDeleteId(null);
      } else alert(r.error);
    },
  });

  const openCreate = () => {
    setEditing(null);
    setForm({
      name: '',
      slug: '',
      description: '',
      price: '',
      compare_price: '',
      sku: '',
      stock_quantity: '0',
      is_active: 'true',
      is_digital: 'false',
      category: ''
    });
    setShowForm(true);
  };
  const openEdit = (p: Product) => {
    setEditing(p);
    setForm({
      name: p.name, slug: p.slug, description: p.description || '', price: String(p.price),
      compare_price: p.compare_price ? String(p.compare_price) : '', sku: p.sku || '',
      stock_quantity: String(p.stock_quantity), is_active: String(p.is_active),
      is_digital: String(p.is_digital), category: p.category || ''
    });
    setShowForm(true);
  };
  const submit = () => {
    if (!form.name.trim()) return alert('请填写商品名称');
    const payload = {
      ...form,
      price: parseFloat(form.price) || 0,
      compare_price: form.compare_price ? parseFloat(form.compare_price) : null,
      stock_quantity: parseInt(form.stock_quantity) || 0,
      is_active: form.is_active === 'true',
      is_digital: form.is_digital === 'true',
    };
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
                   placeholder="搜索商品..."
                   className="pl-9 pr-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-sm dark:text-white w-64"/>
          </div>
        </div>
        <button onClick={openCreate}
                className="flex items-center gap-1.5 px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700">
          <Plus className="w-4 h-4"/> 新增商品
        </button>
      </div>

      {isLoading ? (
        <div className="space-y-2">{[...Array(5)].map((_, i) => <div key={i}
                                                                     className="h-16 bg-gray-100 dark:bg-gray-800 rounded-lg animate-pulse"/>)}</div>
      ) : items.length === 0 ? (
        <EmptyState icon={Package} title="暂无商品" description="点击" 新增商品"开始创建"/>
      ) : (
        <div
          className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 overflow-hidden">
          <table className="w-full text-sm">
            <thead>
            <tr className="bg-gray-50 dark:bg-gray-800/50">
              <th className="text-left px-4 py-3 font-medium text-gray-500">商品名称</th>
              <th className="text-left px-4 py-3 font-medium text-gray-500">SKU</th>
              <th className="text-right px-4 py-3 font-medium text-gray-500">价格</th>
              <th className="text-right px-4 py-3 font-medium text-gray-500">库存</th>
              <th className="text-center px-4 py-3 font-medium text-gray-500">状态</th>
              <th className="text-center px-4 py-3 font-medium text-gray-500">类型</th>
              <th className="text-right px-4 py-3 font-medium text-gray-500">操作</th>
            </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
            {items.map(p => (
              <tr key={p.id} className="hover:bg-gray-50 dark:hover:bg-gray-800/30">
                <td className="px-4 py-3">
                  <div className="font-medium text-gray-900 dark:text-gray-100">{p.name}</div>
                  {p.category && <div className="text-xs text-gray-400">{p.category}</div>}
                </td>
                <td className="px-4 py-3 text-gray-500 font-mono text-xs">{p.sku || '-'}</td>
                <td className="px-4 py-3 text-right">
                  <MoneyDisplay amount={p.price}/>
                  {p.compare_price && p.compare_price > p.price && (
                    <span className="ml-1 text-xs text-gray-400 line-through">¥{p.compare_price.toFixed(2)}</span>
                  )}
                </td>
                <td className="px-4 py-3 text-right">
                    <span
                      className={p.stock_quantity <= 0 ? 'text-red-500 font-medium' : p.stock_quantity <= 10 ? 'text-yellow-600' : ''}>
                      {p.stock_quantity}
                    </span>
                </td>
                <td className="px-4 py-3 text-center">
                  <StatusBadge active={p.is_active}/>
                </td>
                <td className="px-4 py-3 text-center">
                    <span
                      className={`px-2 py-0.5 text-[10px] rounded-full font-medium ${p.is_digital ? 'bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-400' : 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400'}`}>
                      {p.is_digital ? '数字' : '实物'}
                    </span>
                </td>
                <td className="px-4 py-3 text-right">
                  <div className="flex items-center justify-end gap-1">
                    <button onClick={() => openEdit(p)}
                            className="p-1.5 rounded hover:bg-gray-100 dark:hover:bg-gray-800" title="编辑">
                      <Edit3 className="w-3.5 h-3.5 text-gray-500"/>
                    </button>
                    <button onClick={() => setDeleteId(p.id)}
                            className="p-1.5 rounded hover:bg-red-50 dark:hover:bg-red-900/20" title="删除">
                      <Trash2 className="w-3.5 h-3.5 text-red-500"/>
                    </button>
                  </div>
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

      {/* Create/Edit Modal */}
      <Modal open={showForm} onClose={() => setShowForm(false)} title={editing ? '编辑商品' : '新增商品'}>
        <div className="max-h-[70vh] overflow-y-auto pr-1">
          <Input label="商品名称 *" value={form.name} onChange={v => setForm(f => ({...f, name: v}))}
                 placeholder="输入商品名称"/>
          <Input label="Slug" value={form.slug} onChange={v => setForm(f => ({...f, slug: v}))}
                 placeholder="product-slug"/>
          <Input label="描述" value={form.description} onChange={v => setForm(f => ({...f, description: v}))}
                 placeholder="商品描述" rows={3}/>
          <div className="grid grid-cols-2 gap-3">
            <Input label="价格 *" value={form.price} onChange={v => setForm(f => ({...f, price: v}))} type="number"
                   placeholder="0.00"/>
            <Input label="划线价" value={form.compare_price} onChange={v => setForm(f => ({...f, compare_price: v}))}
                   type="number" placeholder="0.00"/>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <Input label="SKU" value={form.sku} onChange={v => setForm(f => ({...f, sku: v}))} placeholder="SKU-001"/>
            <Input label="库存" value={form.stock_quantity} onChange={v => setForm(f => ({...f, stock_quantity: v}))}
                   type="number" placeholder="0"/>
          </div>
          <Input label="分类" value={form.category} onChange={v => setForm(f => ({...f, category: v}))}
                 placeholder="商品分类"/>
          <div className="grid grid-cols-2 gap-3">
            <Select label="状态" value={form.is_active} onChange={v => setForm(f => ({...f, is_active: v}))}
                    options={[{value: 'true', label: '启用'}, {value: 'false', label: '禁用'}]}/>
            <Select label="类型" value={form.is_digital} onChange={v => setForm(f => ({...f, is_digital: v}))}
                    options={[{value: 'false', label: '实物商品'}, {value: 'true', label: '数字商品'}]}/>
          </div>
        </div>
        <div className="flex justify-end gap-2 mt-4 pt-3 border-t border-gray-100 dark:border-gray-800">
          <button onClick={() => setShowForm(false)}
                  className="px-4 py-2 text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg">取消
          </button>
          <button onClick={submit} disabled={createMut.isPending || updateMut.isPending}
                  className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50">
            {createMut.isPending || updateMut.isPending ? '保存中...' : '保存'}
          </button>
        </div>
      </Modal>

      {/* Delete Confirm */}
      <DeleteConfirm open={deleteId !== null} onClose={() => setDeleteId(null)}
                     onConfirm={() => deleteId && deleteMut.mutate(deleteId)}
                     title="确定删除此商品？" message="删除后无法恢复，相关订单数据将保留。"/>
    </>
  );
};

/* ─── Orders Tab ────────────────────────────────── */
const OrdersTab: React.FC = () => {
  const qc = useQueryClient();
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [selectedOrder, setSelectedOrder] = useState<Order | null>(null);
  const [showDetail, setShowDetail] = useState(false);

  const {data, isLoading} = useQuery({
    queryKey: ['orders', page, search, statusFilter],
    queryFn: () => apiClient.get('/shop/orders', {
      page, per_page: 15,
      search: search || undefined,
      status: statusFilter || undefined,
    }),
  });

  const items: Order[] = data?.data?.orders || data?.data?.items || [];
  const total: number = data?.data?.total || 0;

  const statusMut = useMutation({
    mutationFn: ({id, status}: { id: number; status: string }) => apiClient.put(`/shop/orders/${id}`, {status}),
    onSuccess: (r: any) => {
      if (r.success) qc.invalidateQueries({queryKey: ['orders']});
      else alert(r.error);
    },
  });

  const statusColors: Record<string, string> = {
    pending: 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-400',
    confirmed: 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400',
    shipped: 'bg-indigo-100 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-400',
    delivered: 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400',
    completed: 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400',
    cancelled: 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400',
    refunded: 'bg-gray-100 dark:bg-gray-800 text-gray-500',
  };

  const statusLabels: Record<string, string> = {
    pending: '待处理', confirmed: '已确认', shipped: '已发货',
    delivered: '已送达', completed: '已完成', cancelled: '已取消', refunded: '已退款',
  };

  const paymentStatusColors: Record<string, string> = {
    pending: 'text-yellow-600', paid: 'text-green-600', failed: 'text-red-600', refunded: 'text-gray-500',
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
                   placeholder="搜索订单..."
                   className="pl-9 pr-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-sm dark:text-white w-64"/>
          </div>
          <select value={statusFilter} onChange={e => {
            setStatusFilter(e.target.value);
            setPage(1);
          }}
                  className="px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-sm dark:text-white">
            <option value="">全部状态</option>
            {Object.entries(statusLabels).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
        </div>
      </div>

      {isLoading ? (
        <div className="space-y-2">{[...Array(5)].map((_, i) => <div key={i}
                                                                     className="h-16 bg-gray-100 dark:bg-gray-800 rounded-lg animate-pulse"/>)}</div>
      ) : items.length === 0 ? (
        <EmptyState icon={ShoppingCart} title="暂无订单" description="订单将在用户购买商品后自动生成"/>
      ) : (
        <div
          className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 overflow-hidden">
          <table className="w-full text-sm">
            <thead>
            <tr className="bg-gray-50 dark:bg-gray-800/50">
              <th className="text-left px-4 py-3 font-medium text-gray-500">订单号</th>
              <th className="text-left px-4 py-3 font-medium text-gray-500">用户</th>
              <th className="text-right px-4 py-3 font-medium text-gray-500">金额</th>
              <th className="text-center px-4 py-3 font-medium text-gray-500">订单状态</th>
              <th className="text-center px-4 py-3 font-medium text-gray-500">支付状态</th>
              <th className="text-left px-4 py-3 font-medium text-gray-500">时间</th>
              <th className="text-right px-4 py-3 font-medium text-gray-500">操作</th>
            </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
            {items.map(o => (
              <tr key={o.id} className="hover:bg-gray-50 dark:hover:bg-gray-800/30">
                <td className="px-4 py-3 font-mono text-xs text-gray-900 dark:text-gray-100">{o.order_number}</td>
                <td className="px-4 py-3 text-gray-700 dark:text-gray-300">{o.username || `用户#${o.user_id}`}</td>
                <td className="px-4 py-3 text-right font-medium"><MoneyDisplay amount={o.total_amount}
                                                                               currency={o.currency}/></td>
                <td className="px-4 py-3 text-center">
                    <span
                      className={`px-2 py-0.5 text-[10px] rounded-full font-medium ${statusColors[o.status] || 'bg-gray-100 text-gray-500'}`}>
                      {statusLabels[o.status] || o.status}
                    </span>
                </td>
                <td className="px-4 py-3 text-center">
                    <span className={`text-xs font-medium ${paymentStatusColors[o.payment_status] || 'text-gray-500'}`}>
                      {o.payment_status === 'paid' ? '已支付' : o.payment_status === 'pending' ? '待支付' : o.payment_status === 'failed' ? '失败' : o.payment_status}
                    </span>
                </td>
                <td className="px-4 py-3 text-xs text-gray-500">{o.created_at?.slice(0, 16)}</td>
                <td className="px-4 py-3 text-right">
                  <button onClick={() => {
                    setSelectedOrder(o);
                    setShowDetail(true);
                  }}
                          className="p-1.5 rounded hover:bg-gray-100 dark:hover:bg-gray-800" title="查看详情">
                    <Eye className="w-3.5 h-3.5 text-gray-500"/>
                  </button>
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

      {/* Order Detail Modal */}
      <Modal open={showDetail} onClose={() => setShowDetail(false)} title={`订单详情 #${selectedOrder?.order_number}`}>
        {selectedOrder && (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-gray-500">用户：</span>
                <span className="font-medium">{selectedOrder.username || `#${selectedOrder.user_id}`}</span>
              </div>
              <div>
                <span className="text-gray-500">金额：</span>
                <MoneyDisplay amount={selectedOrder.total_amount} currency={selectedOrder.currency}/>
              </div>
              <div>
                <span className="text-gray-500">支付方式：</span>
                <span>{selectedOrder.payment_method || '未指定'}</span>
              </div>
              <div>
                <span className="text-gray-500">下单时间：</span>
                <span>{selectedOrder.created_at?.slice(0, 16)}</span>
              </div>
              {selectedOrder.shipping_address && (
                <div className="col-span-2">
                  <span className="text-gray-500">收货地址：</span>
                  <span>{selectedOrder.shipping_address}</span>
                </div>
              )}
              {selectedOrder.tracking_number && (
                <div className="col-span-2">
                  <span className="text-gray-500">物流单号：</span>
                  <span className="font-mono">{selectedOrder.tracking_number}</span>
                </div>
              )}
            </div>
            <div className="border-t border-gray-100 dark:border-gray-800 pt-4">
              <h4 className="text-sm font-semibold mb-2">更新订单状态</h4>
              <div className="flex gap-2 flex-wrap">
                {['confirmed', 'shipped', 'delivered', 'completed', 'cancelled'].map(s => (
                  <button key={s} onClick={() => statusMut.mutate({id: selectedOrder.id, status: s})}
                          disabled={selectedOrder.status === s || statusMut.isPending}
                          className={`px-3 py-1.5 text-xs rounded-lg border ${selectedOrder.status === s ? 'opacity-50 cursor-not-allowed' : 'hover:bg-gray-50 dark:hover:bg-gray-800'} border-gray-200 dark:border-gray-700`}>
                    {statusLabels[s]}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}
      </Modal>
    </>
  );
};

/* ─── Main Component ────────────────────────────── */
const AdminEcommerceManagementInner: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'products' | 'orders'>('products');

  return (
    <AdminShell title="电商管理" actions={
      <div className="flex bg-gray-100 dark:bg-gray-800 rounded-lg p-0.5">
        <button onClick={() => setActiveTab('products')}
                className={`px-4 py-1.5 text-sm rounded-md transition-colors ${activeTab === 'products' ? 'bg-white dark:bg-gray-700 shadow-sm text-gray-900 dark:text-white' : 'text-gray-500 hover:text-gray-700'}`}>
          <Package className="w-4 h-4 inline mr-1.5"/>商品管理
        </button>
        <button onClick={() => setActiveTab('orders')}
                className={`px-4 py-1.5 text-sm rounded-md transition-colors ${activeTab === 'orders' ? 'bg-white dark:bg-gray-700 shadow-sm text-gray-900 dark:text-white' : 'text-gray-500 hover:text-gray-700'}`}>
          <ShoppingCart className="w-4 h-4 inline mr-1.5"/>订单管理
        </button>
      </div>
    }>
      <div className="p-6 max-w-7xl mx-auto">
        {activeTab === 'products' ? <ProductsTab/> : <OrdersTab/>}
      </div>
    </AdminShell>
  );
};

export default function AdminEcommerceManagement() {
  return (
    <AuthGuard>
      <QueryProvider>
        <AdminEcommerceManagementInner/>
      </QueryProvider>
    </AuthGuard>
  );
}
