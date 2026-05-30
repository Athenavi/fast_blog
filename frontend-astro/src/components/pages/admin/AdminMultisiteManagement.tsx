'use client';

import React, {useState} from 'react';
import {useMutation, useQuery, useQueryClient} from '@tanstack/react-query';
import {AuthGuard} from '@/components/AuthGuard';
import {QueryProvider} from '@/components/QueryProvider';
import {AdminShell} from '@/components/admin/AdminShell';
import {DeleteConfirm, EmptyState, Modal} from '@/components/admin/shared-ui';
import {apiClient} from '@/lib/api/api-client';
import {Edit3, Globe, Link, Map, Plus, Search, Trash2, Users} from 'lucide-react';

/* ─── Types ─────────────────────────────────────── */
interface Site {
  id: number;
  name: string;
  domain: string;
  description?: string;
  is_active: boolean;
  theme?: string;
  logo_url?: string;
  additional_domains?: string[];
  user_count?: number;
  content_count?: number;
  created_at?: string;
  updated_at?: string;
}

interface SiteUser {
  id: number;
  user_id: number;
  username: string;
  email?: string;
  role: string;
  joined_at?: string;
}

interface ContentMapping {
  id: number;
  source_site_id: number;
  target_site_id: number;
  source_site_name?: string;
  target_site_name?: string;
  content_type: string;
  content_id: number;
  mapped_content_id?: number;
  sync_status: string;
  last_synced_at?: string;
  created_at?: string;
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

const StatusBadge: React.FC<{ active: boolean }> = ({active}) => (
  <span
    className={`px-2 py-0.5 text-[10px] rounded-full font-medium ${active ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400' : 'bg-gray-100 dark:bg-gray-800 text-gray-500'}`}>
    {active ? '活跃' : '停用'}
  </span>
);

/* ─── Sites Tab ─────────────────────────────────── */
const SitesTab: React.FC = () => {
  const qc = useQueryClient();
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<Site | null>(null);
  const [deleteId, setDeleteId] = useState<number | null>(null);
  const [showUsers, setShowUsers] = useState<number | null>(null);
  const [form, setForm] = useState({
    name: '', domain: '', description: '', is_active: 'true', theme: '', additional_domains: ''
  });

  const {data, isLoading} = useQuery({
    queryKey: ['sites', page, search],
    queryFn: () => apiClient.get('/system/multisite', {page, per_page: 15, search: search || undefined}),
  });

  const sites: Site[] = data?.data?.sites || data?.data?.items || [];
  const total: number = data?.data?.total || 0;

  const createMut = useMutation({
    mutationFn: (d: any) => apiClient.post('/system/multisite', d),
    onSuccess: (r: any) => {
      if (r.success) {
        qc.invalidateQueries({queryKey: ['sites']});
        setShowForm(false);
      } else alert(r.error);
    },
  });
  const updateMut = useMutation({
    mutationFn: ({id, ...d}: any) => apiClient.put(`/system/multisite/${id}`, d),
    onSuccess: (r: any) => {
      if (r.success) {
        qc.invalidateQueries({queryKey: ['sites']});
        setShowForm(false);
      } else alert(r.error);
    },
  });
  const deleteMut = useMutation({
    mutationFn: (id: number) => apiClient.delete(`/system/multisite/${id}`),
    onSuccess: (r: any) => {
      if (r.success) {
        qc.invalidateQueries({queryKey: ['sites']});
        setDeleteId(null);
      } else alert(r.error);
    },
  });

  const openCreate = () => {
    setEditing(null);
    setForm({name: '', domain: '', description: '', is_active: 'true', theme: '', additional_domains: ''});
    setShowForm(true);
  };
  const openEdit = (s: Site) => {
    setEditing(s);
    setForm({
      name: s.name, domain: s.domain, description: s.description || '',
      is_active: String(s.is_active), theme: s.theme || '',
      additional_domains: s.additional_domains?.join(', ') || '',
    });
    setShowForm(true);
  };
  const submit = () => {
    if (!form.name.trim() || !form.domain.trim()) return alert('请填写站点名称和域名');
    const payload = {
      ...form,
      is_active: form.is_active === 'true',
      additional_domains: form.additional_domains ? form.additional_domains.split(',').map(d => d.trim()).filter(Boolean) : [],
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
                   placeholder="搜索站点..."
                   className="pl-9 pr-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-sm dark:text-white w-64"/>
          </div>
        </div>
        <button onClick={openCreate}
                className="flex items-center gap-1.5 px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700">
          <Plus className="w-4 h-4"/> 新增站点
        </button>
      </div>

      {isLoading ? (
        <div className="space-y-2">{[...Array(5)].map((_, i) => <div key={i}
                                                                     className="h-16 bg-gray-100 dark:bg-gray-800 rounded-lg animate-pulse"/>)}</div>
      ) : sites.length === 0 ? (
        <EmptyState icon={Globe} title="暂无站点" description="点击" 新增站点"开始配置多站点"/>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {sites.map(s => (
            <div key={s.id}
                 className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-5 hover:shadow-md transition-shadow">
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-3">
                  <div
                    className="w-10 h-10 rounded-lg bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center">
                    <Globe className="w-5 h-5 text-blue-600 dark:text-blue-400"/>
                  </div>
                  <div>
                    <h3 className="font-semibold text-gray-900 dark:text-gray-100">{s.name}</h3>
                    <p className="text-xs text-gray-500 font-mono">{s.domain}</p>
                  </div>
                </div>
                <StatusBadge active={s.is_active}/>
              </div>
              {s.description && <p className="text-xs text-gray-500 mb-3 line-clamp-2">{s.description}</p>}
              <div className="flex items-center gap-4 text-xs text-gray-500 mb-3">
                <span className="flex items-center gap-1"><Users className="w-3 h-3"/> {s.user_count || 0} 用户</span>
                <span className="flex items-center gap-1"><Map className="w-3 h-3"/> {s.content_count || 0} 内容</span>
              </div>
              {s.additional_domains && s.additional_domains.length > 0 && (
                <div className="flex flex-wrap gap-1 mb-3">
                  {s.additional_domains.map((d, i) => (
                    <span key={i}
                          className="px-1.5 py-0.5 text-[10px] bg-gray-100 dark:bg-gray-800 rounded font-mono">{d}</span>
                  ))}
                </div>
              )}
              <div className="flex items-center justify-end gap-1 pt-2 border-t border-gray-100 dark:border-gray-800">
                <button onClick={() => setShowUsers(s.id)}
                        className="p-1.5 rounded hover:bg-gray-100 dark:hover:bg-gray-800" title="用户管理">
                  <Users className="w-3.5 h-3.5 text-gray-500"/>
                </button>
                <button onClick={() => openEdit(s)} className="p-1.5 rounded hover:bg-gray-100 dark:hover:bg-gray-800"
                        title="编辑">
                  <Edit3 className="w-3.5 h-3.5 text-gray-500"/>
                </button>
                <button onClick={() => setDeleteId(s.id)}
                        className="p-1.5 rounded hover:bg-red-50 dark:hover:bg-red-900/20" title="删除">
                  <Trash2 className="w-3.5 h-3.5 text-red-500"/>
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Create/Edit Modal */}
      <Modal open={showForm} onClose={() => setShowForm(false)} title={editing ? '编辑站点' : '新增站点'}>
        <div className="max-h-[70vh] overflow-y-auto pr-1">
          <Input label="站点名称 *" value={form.name} onChange={v => setForm(f => ({...f, name: v}))}
                 placeholder="我的站点"/>
          <Input label="域名 *" value={form.domain} onChange={v => setForm(f => ({...f, domain: v}))}
                 placeholder="example.com"/>
          <Input label="描述" value={form.description} onChange={v => setForm(f => ({...f, description: v}))}
                 placeholder="站点描述" rows={3}/>
          <Input label="主题" value={form.theme} onChange={v => setForm(f => ({...f, theme: v}))}
                 placeholder="default"/>
          <Input label="附加域名" value={form.additional_domains}
                 onChange={v => setForm(f => ({...f, additional_domains: v}))}
                 placeholder="www.example.com, m.example.com（逗号分隔）"/>
          <div className="mb-3">
            <label className="block text-xs font-semibold text-gray-500 dark:text-gray-400 mb-1">状态</label>
            <select value={form.is_active} onChange={e => setForm(f => ({...f, is_active: e.target.value}))}
                    className="w-full px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white">
              <option value="true">活跃</option>
              <option value="false">停用</option>
            </select>
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

      {/* Site Users Modal */}
      <Modal open={showUsers !== null} onClose={() => setShowUsers(null)} title="站点用户管理">
        <SiteUsersPanel siteId={showUsers}/>
      </Modal>

      {/* Delete Confirm */}
      <DeleteConfirm open={deleteId !== null} onClose={() => setDeleteId(null)}
                     onConfirm={() => deleteId && deleteMut.mutate(deleteId)}
                     title="确定删除此站点？" message="删除站点将同时移除所有关联的用户关系和内容映射。"/>
    </>
  );
};

/* ─── Site Users Panel ──────────────────────────── */
const SiteUsersPanel: React.FC<{ siteId: number | null }> = ({siteId}) => {
  const qc = useQueryClient();
  const [addUserId, setAddUserId] = useState('');
  const [addRole, setAddRole] = useState('editor');

  const {data, isLoading} = useQuery({
    queryKey: ['site-users', siteId],
    queryFn: () => siteId ? apiClient.get(`/system/multisite/${siteId}/users`) : null,
    enabled: !!siteId,
  });

  const users: SiteUser[] = data?.data?.users || [];

  const addUserMut = useMutation({
    mutationFn: (d: any) => apiClient.post('/system/multisite/users', {site_id: siteId, ...d}),
    onSuccess: (r: any) => {
      if (r.success) {
        qc.invalidateQueries({queryKey: ['site-users', siteId]});
        setAddUserId('');
      } else alert(r.error);
    },
  });
  const removeUserMut = useMutation({
    mutationFn: (userId: number) => apiClient.delete(`/system/multisite/users/${userId}`),
    onSuccess: (r: any) => {
      if (r.success) qc.invalidateQueries({queryKey: ['site-users', siteId]});
      else alert(r.error);
    },
  });
  const updateRoleMut = useMutation({
    mutationFn: ({userId, role}: any) => apiClient.put(`/system/multisite/${siteId}/users/${userId}/role`, {role}),
    onSuccess: (r: any) => {
      if (r.success) qc.invalidateQueries({queryKey: ['site-users', siteId]});
      else alert(r.error);
    },
  });

  if (!siteId) return null;

  return (
    <div>
      {isLoading ? (
        <div className="space-y-2">{[...Array(3)].map((_, i) => <div key={i}
                                                                     className="h-12 bg-gray-100 dark:bg-gray-800 rounded-lg animate-pulse"/>)}</div>
      ) : (
        <>
          <div className="space-y-2 mb-4 max-h-60 overflow-y-auto">
            {users.length === 0 ? (
              <p className="text-sm text-gray-500 text-center py-4">暂无用户</p>
            ) : users.map(u => (
              <div key={u.id} className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
                <div>
                  <span className="text-sm font-medium text-gray-900 dark:text-gray-100">{u.username}</span>
                  {u.email && <span className="text-xs text-gray-400 ml-2">{u.email}</span>}
                </div>
                <div className="flex items-center gap-2">
                  <select value={u.role} onChange={e => updateRoleMut.mutate({userId: u.user_id, role: e.target.value})}
                          className="px-2 py-1 text-xs border border-gray-200 dark:border-gray-700 rounded bg-white dark:bg-gray-800 dark:text-white">
                    <option value="admin">管理员</option>
                    <option value="editor">编辑</option>
                    <option value="author">作者</option>
                    <option value="viewer">查看者</option>
                  </select>
                  <button onClick={() => removeUserMut.mutate(u.user_id)}
                          className="p-1 rounded hover:bg-red-50 dark:hover:bg-red-900/20" title="移除">
                    <Trash2 className="w-3.5 h-3.5 text-red-500"/>
                  </button>
                </div>
              </div>
            ))}
          </div>
          <div className="border-t border-gray-100 dark:border-gray-800 pt-4">
            <h4 className="text-xs font-semibold text-gray-500 mb-2">添加用户</h4>
            <div className="flex gap-2">
              <input value={addUserId} onChange={e => setAddUserId(e.target.value)} placeholder="用户ID"
                     className="flex-1 px-3 py-2 text-sm border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 dark:text-white"/>
              <select value={addRole} onChange={e => setAddRole(e.target.value)}
                      className="px-3 py-2 text-sm border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 dark:text-white">
                <option value="admin">管理员</option>
                <option value="editor">编辑</option>
                <option value="author">作者</option>
                <option value="viewer">查看者</option>
              </select>
              <button onClick={() => addUserMut.mutate({user_id: parseInt(addUserId), role: addRole})}
                      disabled={!addUserId || addUserMut.isPending}
                      className="px-3 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50">
                添加
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
};

/* ─── Content Mappings Tab ──────────────────────── */
const ContentMappingsTab: React.FC = () => {
  const [page, setPage] = useState(1);
  const [siteFilter, setSiteFilter] = useState('');

  const {data, isLoading} = useQuery({
    queryKey: ['content-mappings', page, siteFilter],
    queryFn: () => {
      if (!siteFilter) return {data: {mappings: [], total: 0}};
      return apiClient.get(`/system/multisite/${siteFilter}/content-mappings`, {page, per_page: 15});
    },
  });

  const items: ContentMapping[] = data?.data?.mappings || [];
  const total: number = data?.data?.total || 0;

  const syncStatusColors: Record<string, string> = {
    synced: 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400',
    pending: 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-400',
    failed: 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400',
  };

  return (
    <>
      <div className="flex items-center gap-2 mb-4">
        <select value={siteFilter} onChange={e => {
          setSiteFilter(e.target.value);
          setPage(1);
        }}
                className="px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-sm dark:text-white">
          <option value="">选择站点查看映射</option>
        </select>
      </div>

      {!siteFilter ? (
        <EmptyState icon={Link} title="请选择站点" description="选择一个站点以查看其内容映射关系"/>
      ) : isLoading ? (
        <div className="space-y-2">{[...Array(5)].map((_, i) => <div key={i}
                                                                     className="h-16 bg-gray-100 dark:bg-gray-800 rounded-lg animate-pulse"/>)}</div>
      ) : items.length === 0 ? (
        <EmptyState icon={Link} title="暂无内容映射" description="该站点暂无跨站内容同步映射"/>
      ) : (
        <div
          className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 overflow-hidden">
          <table className="w-full text-sm">
            <thead>
            <tr className="bg-gray-50 dark:bg-gray-800/50">
              <th className="text-left px-4 py-3 font-medium text-gray-500">来源站点</th>
              <th className="text-left px-4 py-3 font-medium text-gray-500">目标站点</th>
              <th className="text-left px-4 py-3 font-medium text-gray-500">内容类型</th>
              <th className="text-center px-4 py-3 font-medium text-gray-500">同步状态</th>
              <th className="text-left px-4 py-3 font-medium text-gray-500">最后同步</th>
            </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
            {items.map(m => (
              <tr key={m.id} className="hover:bg-gray-50 dark:hover:bg-gray-800/30">
                <td className="px-4 py-3">{m.source_site_name || `站点#${m.source_site_id}`}</td>
                <td className="px-4 py-3">{m.target_site_name || `站点#${m.target_site_id}`}</td>
                <td className="px-4 py-3">
                    <span
                      className="px-2 py-0.5 text-[10px] rounded-full font-medium bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400">
                      {m.content_type}
                    </span>
                </td>
                <td className="px-4 py-3 text-center">
                    <span
                      className={`px-2 py-0.5 text-[10px] rounded-full font-medium ${syncStatusColors[m.sync_status] || 'bg-gray-100 text-gray-500'}`}>
                      {m.sync_status}
                    </span>
                </td>
                <td className="px-4 py-3 text-xs text-gray-500">{m.last_synced_at?.slice(0, 16) || '-'}</td>
              </tr>
            ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
};

/* ─── Main Component ────────────────────────────── */
const AdminMultisiteManagementInner: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'sites' | 'mappings'>('sites');

  return (
    <AdminShell title="多站点管理" actions={
      <div className="flex bg-gray-100 dark:bg-gray-800 rounded-lg p-0.5">
        <button onClick={() => setActiveTab('sites')}
                className={`px-4 py-1.5 text-sm rounded-md transition-colors ${activeTab === 'sites' ? 'bg-white dark:bg-gray-700 shadow-sm text-gray-900 dark:text-white' : 'text-gray-500 hover:text-gray-700'}`}>
          <Globe className="w-4 h-4 inline mr-1.5"/>站点管理
        </button>
        <button onClick={() => setActiveTab('mappings')}
                className={`px-4 py-1.5 text-sm rounded-md transition-colors ${activeTab === 'mappings' ? 'bg-white dark:bg-gray-700 shadow-sm text-gray-900 dark:text-white' : 'text-gray-500 hover:text-gray-700'}`}>
          <Link className="w-4 h-4 inline mr-1.5"/>内容映射
        </button>
      </div>
    }>
      <div className="p-6 max-w-7xl mx-auto">
        {activeTab === 'sites' ? <SitesTab/> : <ContentMappingsTab/>}
      </div>
    </AdminShell>
  );
};

export default function AdminMultisiteManagement() {
  return (
    <AuthGuard>
      <QueryProvider>
        <AdminMultisiteManagementInner/>
      </QueryProvider>
    </AuthGuard>
  );
}
