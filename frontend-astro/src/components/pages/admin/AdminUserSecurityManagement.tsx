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
  Clock,
  Edit3,
  Lock,
  Mail,
  Monitor,
  Plus,
  PowerOff,
  Shield,
  Smartphone,
  Trash2,
  Unlock
} from 'lucide-react';

/* ─── Types ─────────────────────────────────────── */
interface FieldPermission {
  id: number;
  role_id: number;
  model_name: string;
  field_name: string;
  can_read: boolean;
  can_write: boolean;
  created_at?: string;
}

interface UserSession {
  id: number;
  user_id: number;
  access_token?: string;
  refresh_token?: string;
  device_info?: string;
  ip_address?: string;
  location?: string;
  is_active: boolean;
  last_activity?: string;
  expires_at?: string;
  created_at?: string;
}

interface EmailSubscription {
  id: number;
  user_id: number;
  subscribed: boolean;
  created_at?: string;
}

interface Pagination {
  page: number;
  per_page: number;
  total: number;
  total_pages: number;
}

const Input: React.FC<{
  label: string;
  value: string;
  onChange: (v: string) => void;
  type?: string;
  placeholder?: string
}> = ({label, value, onChange, type, placeholder}) => (
  <div className="mb-3">
    <label className="block text-xs font-semibold text-gray-500 dark:text-gray-400 mb-1">{label}</label>
    <input type={type || 'text'} value={value} onChange={e => onChange(e.target.value)} placeholder={placeholder}
           className="w-full px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white placeholder-gray-400"/>
  </div>
);

/* ─── Field Permissions Tab ─────────────────────── */
const FieldPermissionsTab: React.FC = () => {
  const qc = useQueryClient();
  const [page, setPage] = useState(1);
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<FieldPermission | null>(null);
  const [deleteId, setDeleteId] = useState<number | null>(null);
  const [form, setForm] = useState({role_id: '', model_name: '', field_name: '', can_read: 'true', can_write: 'false'});

  const {data, isLoading} = useQuery({
    queryKey: ['field-permissions', page],
    queryFn: () => apiClient.get('/users/security/field-permissions', {page, per_page: 15}),
  });
  const items: FieldPermission[] = data?.data?.field_permissions || [];
  const pagination: Pagination | undefined = data?.data?.pagination;

  const createMut = useMutation({
    mutationFn: (d: any) => apiClient.post('/users/security/field-permissions', d),
    onSuccess: (r: any) => {
      if (r.success) {
        qc.invalidateQueries({queryKey: ['field-permissions']});
        setShowForm(false);
      } else alert(r.error);
    },
  });
  const updateMut = useMutation({
    mutationFn: ({id, ...d}: any) => apiClient.put(`/users/security/field-permissions/${id}`, d),
    onSuccess: (r: any) => {
      if (r.success) {
        qc.invalidateQueries({queryKey: ['field-permissions']});
        setShowForm(false);
      } else alert(r.error);
    },
  });
  const deleteMut = useMutation({
    mutationFn: (id: number) => apiClient.delete(`/users/security/field-permissions/${id}`),
    onSuccess: (r: any) => {
      if (r.success) {
        qc.invalidateQueries({queryKey: ['field-permissions']});
        setDeleteId(null);
      } else alert(r.error);
    },
  });

  const openCreate = () => {
    setEditing(null);
    setForm({role_id: '', model_name: '', field_name: '', can_read: 'true', can_write: 'false'});
    setShowForm(true);
  };
  const openEdit = (p: FieldPermission) => {
    setEditing(p);
    setForm({
      role_id: String(p.role_id),
      model_name: p.model_name,
      field_name: p.field_name,
      can_read: String(p.can_read),
      can_write: String(p.can_write)
    });
    setShowForm(true);
  };
  const submit = () => {
    if (!form.role_id || !form.model_name.trim() || !form.field_name.trim()) return alert('请填写完整信息');
    const payload = {
      role_id: parseInt(form.role_id),
      model_name: form.model_name,
      field_name: form.field_name,
      can_read: form.can_read === 'true',
      can_write: form.can_write === 'true'
    };
    if (editing) updateMut.mutate({id: editing.id, ...payload});
    else createMut.mutate(payload);
  };

  return (
    <>
      <div className="flex items-center justify-end mb-4">
        <button onClick={openCreate}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded-xl flex items-center gap-1.5">
          <Plus className="w-4 h-4"/>新建权限
        </button>
      </div>
      {isLoading ? <div className="animate-pulse space-y-2">{[1, 2, 3].map(i => <div key={i}
                                                                                     className="h-14 bg-gray-100 dark:bg-gray-800 rounded-xl"/>)}</div> :
        items.length === 0 ? <EmptyState icon={Lock} title="暂无字段权限" desc="配置角色对模型字段的读写权限"/> :
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
              <tr className="border-b border-gray-100 dark:border-gray-800">
                <th className="text-left py-3 px-4 text-xs font-semibold text-gray-500">角色ID</th>
                <th className="text-left py-3 px-4 text-xs font-semibold text-gray-500">模型</th>
                <th className="text-left py-3 px-4 text-xs font-semibold text-gray-500">字段</th>
                <th className="text-center py-3 px-4 text-xs font-semibold text-gray-500">可读</th>
                <th className="text-center py-3 px-4 text-xs font-semibold text-gray-500">可写</th>
                <th className="text-right py-3 px-4 text-xs font-semibold text-gray-500">操作</th>
              </tr>
              </thead>
              <tbody>{items.map(p => (
                <tr key={p.id}
                    className="border-b border-gray-50 dark:border-gray-800/50 hover:bg-gray-50 dark:hover:bg-gray-800/30">
                  <td className="py-3 px-4 font-mono text-xs">#{p.role_id}</td>
                  <td className="py-3 px-4"><code
                    className="text-xs bg-gray-100 dark:bg-gray-800 px-1.5 py-0.5 rounded">{p.model_name}</code></td>
                  <td className="py-3 px-4"><code
                    className="text-xs bg-blue-50 dark:bg-blue-900/20 px-1.5 py-0.5 rounded text-blue-700 dark:text-blue-400">{p.field_name}</code>
                  </td>
                  <td className="py-3 px-4 text-center">{p.can_read ?
                    <Lock className="w-4 h-4 text-green-500 mx-auto"/> :
                    <Lock className="w-4 h-4 text-gray-300 mx-auto"/>}</td>
                  <td className="py-3 px-4 text-center">{p.can_write ?
                    <Unlock className="w-4 h-4 text-green-500 mx-auto"/> :
                    <Lock className="w-4 h-4 text-gray-300 mx-auto"/>}</td>
                  <td className="py-3 px-4 text-right">
                    <button onClick={() => openEdit(p)}
                            className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-500 mr-1">
                      <Edit3 className="w-3.5 h-3.5"/></button>
                    <button onClick={() => setDeleteId(p.id)}
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
      <Modal open={showForm} onClose={() => setShowForm(false)} title={editing ? '编辑字段权限' : '新建字段权限'}>
        <Input label="角色 ID *" value={form.role_id} onChange={v => setForm({...form, role_id: v})} type="number"
               placeholder="角色ID"/>
        <Input label="模型名称 *" value={form.model_name} onChange={v => setForm({...form, model_name: v})}
               placeholder="例如：Article"/>
        <Input label="字段名称 *" value={form.field_name} onChange={v => setForm({...form, field_name: v})}
               placeholder="例如：title"/>
        <div className="flex gap-4 mb-3">
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={form.can_read === 'true'}
                   onChange={e => setForm({...form, can_read: String(e.target.checked)})} className="rounded"/>可读
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={form.can_write === 'true'}
                   onChange={e => setForm({...form, can_write: String(e.target.checked)})} className="rounded"/>可写
          </label>
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
          <DeleteConfirm itemName={`权限#${deleteId}`} onConfirm={() => deleteMut.mutate(deleteId)}
                         onCancel={() => setDeleteId(null)} isPending={deleteMut.isPending}/>
        </Modal>
      )}
    </>
  );
};

/* ─── Sessions Tab ─────────────────────────────── */
const SessionsTab: React.FC = () => {
  const qc = useQueryClient();
  const [page, setPage] = useState(1);

  const {data, isLoading} = useQuery({
    queryKey: ['user-sessions', page],
    queryFn: () => apiClient.get('/users/security/sessions', {page, per_page: 15}),
  });
  const items: UserSession[] = data?.data?.sessions || [];
  const pagination: Pagination | undefined = data?.data?.pagination;

  const deactivateMut = useMutation({
    mutationFn: (id: number) => apiClient.post(`/users/security/sessions/${id}/deactivate`),
    onSuccess: (r: any) => {
      if (r.success) qc.invalidateQueries({queryKey: ['user-sessions']}); else alert(r.error);
    },
  });
  const deleteMut = useMutation({
    mutationFn: (id: number) => apiClient.delete(`/users/security/sessions/${id}`),
    onSuccess: () => qc.invalidateQueries({queryKey: ['user-sessions']}),
  });

  return (
    <>
      {isLoading ? <div className="animate-pulse space-y-2">{[1, 2, 3].map(i => <div key={i}
                                                                                     className="h-16 bg-gray-100 dark:bg-gray-800 rounded-xl"/>)}</div> :
        items.length === 0 ? <EmptyState icon={Monitor} title="暂无活跃会话" desc="用户登录会话将在此显示"/> :
          <div className="space-y-2">
            {items.map(s => (
              <div key={s.id}
                   className={`flex items-center justify-between p-4 rounded-xl border ${s.is_active ? 'bg-white dark:bg-gray-900 border-gray-200 dark:border-gray-700' : 'bg-gray-50 dark:bg-gray-800/50 border-gray-100 dark:border-gray-800 opacity-60'}`}>
                <div className="flex items-center gap-3">
                  {s.device_info?.toLowerCase().includes('mobile') ? <Smartphone className="w-4 h-4 text-gray-400"/> :
                    <Monitor className="w-4 h-4 text-gray-400"/>}
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-gray-900 dark:text-white">用户#{s.user_id}</span>
                      <span
                        className={`px-1.5 py-0.5 text-[10px] rounded-full ${s.is_active ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400' : 'bg-gray-100 dark:bg-gray-800 text-gray-500'}`}>
                     {s.is_active ? '活跃' : '已失效'}
                   </span>
                    </div>
                    <div className="flex items-center gap-2 mt-0.5 text-[11px] text-gray-500">
                      {s.device_info && <span>{s.device_info}</span>}
                      {s.ip_address && <><span>·</span><span>{s.ip_address}</span></>}
                      {s.location && <><span>·</span><span>{s.location}</span></>}
                      {s.last_activity && <><span>·</span><span className="flex items-center gap-0.5"><Clock
                        className="w-3 h-3"/>{new Date(s.last_activity).toLocaleString('zh-CN')}</span></>}
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-1">
                  {s.is_active && (
                    <button onClick={() => {
                      if (confirm('确定要强制下线此会话？')) deactivateMut.mutate(s.id);
                    }}
                            className="px-2.5 py-1 text-xs border border-yellow-200 dark:border-yellow-900/30 rounded-lg text-yellow-600 hover:bg-yellow-50 dark:hover:bg-yellow-900/10 flex items-center gap-1"
                            title="强制下线">
                      <PowerOff className="w-3 h-3"/>下线
                    </button>
                  )}
                  <button onClick={() => {
                    if (confirm('确定删除此会话记录？')) deleteMut.mutate(s.id);
                  }}
                          className="p-1.5 rounded-lg hover:bg-red-50 dark:hover:bg-red-900/20 text-red-500"><Trash2
                    className="w-3.5 h-3.5"/></button>
                </div>
              </div>
            ))}
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

/* ─── Email Subscriptions Tab ──────────────────── */
const EmailSubscriptionsTab: React.FC = () => {
  const qc = useQueryClient();
  const [page, setPage] = useState(1);

  const {data, isLoading} = useQuery({
    queryKey: ['email-subscriptions', page],
    queryFn: () => apiClient.get('/users/security/email-subscriptions', {page, per_page: 15}),
  });
  const items: EmailSubscription[] = data?.data?.email_subscriptions || [];
  const pagination: Pagination | undefined = data?.data?.pagination;

  const toggleMut = useMutation({
    mutationFn: ({id, subscribed}: {
      id: number;
      subscribed: boolean
    }) => apiClient.put(`/users/security/email-subscriptions/${id}`, {subscribed: !subscribed}),
    onSuccess: () => qc.invalidateQueries({queryKey: ['email-subscriptions']}),
  });
  const deleteMut = useMutation({
    mutationFn: (id: number) => apiClient.delete(`/users/security/email-subscriptions/${id}`),
    onSuccess: () => qc.invalidateQueries({queryKey: ['email-subscriptions']}),
  });

  return (
    <>
      {isLoading ? <div className="animate-pulse space-y-2">{[1, 2, 3].map(i => <div key={i}
                                                                                     className="h-14 bg-gray-100 dark:bg-gray-800 rounded-xl"/>)}</div> :
        items.length === 0 ? <EmptyState icon={Mail} title="暂无邮件订阅" desc="用户的邮件订阅状态将在此显示"/> :
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
              <tr className="border-b border-gray-100 dark:border-gray-800">
                <th className="text-left py-3 px-4 text-xs font-semibold text-gray-500">ID</th>
                <th className="text-left py-3 px-4 text-xs font-semibold text-gray-500">用户ID</th>
                <th className="text-left py-3 px-4 text-xs font-semibold text-gray-500">订阅状态</th>
                <th className="text-left py-3 px-4 text-xs font-semibold text-gray-500">创建时间</th>
                <th className="text-right py-3 px-4 text-xs font-semibold text-gray-500">操作</th>
              </tr>
              </thead>
              <tbody>{items.map(s => (
                <tr key={s.id}
                    className="border-b border-gray-50 dark:border-gray-800/50 hover:bg-gray-50 dark:hover:bg-gray-800/30">
                  <td className="py-3 px-4 font-mono text-xs">#{s.id}</td>
                  <td className="py-3 px-4 font-medium text-gray-900 dark:text-white">用户#{s.user_id}</td>
                  <td className="py-3 px-4">
                    <button onClick={() => toggleMut.mutate({id: s.id, subscribed: s.subscribed})}
                            className={`px-2.5 py-1 text-[10px] rounded-full font-medium ${s.subscribed ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400' : 'bg-gray-100 dark:bg-gray-800 text-gray-500'}`}>
                      {s.subscribed ? '已订阅' : '未订阅'}
                    </button>
                  </td>
                  <td
                    className="py-3 px-4 text-xs text-gray-500">{s.created_at ? new Date(s.created_at).toLocaleString('zh-CN') : '—'}</td>
                  <td className="py-3 px-4 text-right">
                    <button onClick={() => {
                      if (confirm('确定删除？')) deleteMut.mutate(s.id);
                    }}
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
    </>
  );
};

/* ─── Main Component ───────────────────────────── */
type TabKey = 'field-permissions' | 'sessions' | 'email-subscriptions';
const TABS: { key: TabKey; label: string; icon: any }[] = [
  {key: 'field-permissions', label: '字段权限', icon: Shield},
  {key: 'sessions', label: '会话管理', icon: Monitor},
  {key: 'email-subscriptions', label: '邮件订阅', icon: Mail},
];

function UserSecurityInner() {
  const [tab, setTab] = useState<TabKey>('sessions');

  return (
    <AdminShell title="用户安全管理" actions={<Shield className="w-5 h-5 text-blue-500"/>}>
      <div className="space-y-6">
        <div className="flex gap-1 bg-gray-100 dark:bg-gray-800 rounded-xl p-1">
          {TABS.map(t => (
            <button key={t.key} onClick={() => setTab(t.key)}
                    className={`flex-1 flex items-center justify-center gap-1.5 px-4 py-2.5 text-sm rounded-lg transition-colors ${tab === t.key ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm font-medium' : 'text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'}`}>
              <t.icon className="w-4 h-4"/>
              {t.label}
            </button>
          ))}
        </div>
        <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 p-5">
          {tab === 'field-permissions' && <FieldPermissionsTab/>}
          {tab === 'sessions' && <SessionsTab/>}
          {tab === 'email-subscriptions' && <EmailSubscriptionsTab/>}
        </div>
      </div>
    </AdminShell>
  );
}

export default function AdminUserSecurityManagement() {
  return (
    <AuthGuard>
      <QueryProvider>
        <UserSecurityInner/>
      </QueryProvider>
    </AuthGuard>
  );
}
