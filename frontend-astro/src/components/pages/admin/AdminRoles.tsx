'use client';

import React, {useState} from 'react';
import {useQuery, useMutation, useQueryClient} from '@tanstack/react-query';
import {AuthGuard} from '@/components/AuthGuard';
import {QueryProvider} from '@/components/QueryProvider';
import {AdminShell} from '@/components/admin/AdminShell';
import {apiClient} from '@/lib/api/base-client';
import {Shield, Edit, Trash2, Plus, X, Check, AlertTriangle, Users} from 'lucide-react';

/* ---------- 编辑角色 Modal ---------- */
function RoleModal({mode, role, permissions, onClose}: {
  mode: 'create' | 'edit';
  role?: any;
  permissions: any[];
  onClose: () => void;
}) {
  const qc = useQueryClient();
  const [name, setName] = useState(role?.name || '');
  const [slug, setSlug] = useState(role?.slug || '');
  const [desc, setDesc] = useState(role?.description || '');
  // role?.permission_codes 可能是 [1,2,3] 或 ['article:read',...]
  const [selectedPerms, setSelectedPerms] = useState<Set<string>>(() => {
    if (!role?.permission_codes) return new Set<string>();
    return new Set(role.permission_codes.map((c: any) => typeof c === 'string' ? c : String(c)));
  });
  const [error, setError] = useState('');

  // 按 resource_type 分组权限
  const grouped = permissions.reduce((acc: any, p: any) => {
    const rt = p.resource_type || p.code?.split(':')[0] || 'other';
    if (!acc[rt]) acc[rt] = [];
    acc[rt].push(p);
    return acc;
  }, {} as Record<string, any[]>);

  const togglePerm = (code: string) => {
    const s = new Set(selectedPerms);
    s.has(code) ? s.delete(code) : s.add(code);
    setSelectedPerms(s);
  };

  const submitMut = useMutation({
    mutationFn: async () => {
      if (!name.trim()) throw new Error('角色名称不能为空');
      if (!slug.trim()) throw new Error('角色标识不能为空');
      const perms = [...selectedPerms];
      if (mode === 'create') {
        return apiClient.post('/api/v2/security/rbac/roles', {name, slug, description: desc, permission_codes: perms});
      } else {
        return apiClient.put(`/api/v2/security/rbac/roles/${role!.id}/permissions`, {permission_codes: perms});
      }
    },
    onSuccess: (res: any) => {
      if (!res.success) { setError(res.error || '操作失败'); return; }
      qc.invalidateQueries({queryKey: ['admin-roles']});
      onClose();
    },
    onError: (e: any) => setError(e.message || '请求失败'),
  });

  return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onClick={onClose}>
        <div className="bg-white dark:bg-gray-900 rounded-2xl shadow-2xl border border-gray-200 dark:border-gray-700 w-full max-w-2xl max-h-[85vh] flex flex-col" onClick={e => e.stopPropagation()}>
          {/* 头部 */}
          <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">{mode === 'create' ? '创建角色' : '编辑角色'}</h2>
            <button onClick={onClose} className="p-1 text-gray-400 hover:text-gray-600"><X className="w-5 h-5"/></button>
          </div>

          {/* 表单 */}
          <div className="p-6 overflow-y-auto space-y-4">
            {error && <div className="flex items-center gap-2 p-3 bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 text-sm rounded-xl"><AlertTriangle className="w-4 h-4 shrink-0"/>{error}</div>}

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">角色名称</label>
                <input type="text" value={name} onChange={e => setName(e.target.value)}
                       className="w-full px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-xl bg-white dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white"
                       placeholder="例如: 编辑者"/>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">角色标识</label>
                <input type="text" value={slug} onChange={e => setSlug(e.target.value)}
                       className="w-full px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-xl bg-white dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white"
                       placeholder="例如: editor" disabled={mode === 'edit'}/>
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">描述</label>
              <textarea value={desc} onChange={e => setDesc(e.target.value)} rows={2}
                        className="w-full px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-xl bg-white dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white resize-none"
                        placeholder="角色描述"/>
            </div>

            {/* 权限选择 */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="text-sm font-medium text-gray-700 dark:text-gray-300">权限</label>
                <span className="text-xs text-gray-400">已选 {selectedPerms.size} 项</span>
              </div>
              <div className="max-h-64 overflow-y-auto border border-gray-200 dark:border-gray-700 rounded-xl p-3 space-y-3">
                {Object.entries(grouped).map(([rt, perms]: [string, any[]]) => (
                    <div key={rt}>
                      <p className="text-xs font-semibold text-gray-500 uppercase mb-1.5">{rt}</p>
                      <div className="flex flex-wrap gap-1.5">
                        {perms.map((p: any) => {
                          const code = p.code || `${p.resource_type}:${p.action}`;
                          const active = selectedPerms.has(code);
                          return (
                              <button key={code} onClick={() => togglePerm(code)}
                                      className={`px-2.5 py-1 rounded-lg text-xs font-medium border transition-colors ${
                                          active
                                              ? 'bg-blue-100 dark:bg-blue-900/30 border-blue-300 dark:border-blue-700 text-blue-700 dark:text-blue-400'
                                              : 'bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-400 hover:border-blue-300'
                                      }`}>
                                {p.name || code}
                              </button>
                          );
                        })}
                      </div>
                    </div>
                ))}
              </div>
            </div>
          </div>

          {/* 底部按钮 */}
          <div className="flex justify-end gap-3 px-6 py-4 border-t border-gray-200 dark:border-gray-700">
            <button onClick={onClose} className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-xl transition-colors">取消</button>
            <button onClick={() => submitMut.mutate()}
                    className="px-4 py-2 text-sm font-medium bg-blue-600 hover:bg-blue-700 text-white rounded-xl transition-colors flex items-center gap-1.5"
                    disabled={submitMut.isPending}>
              {submitMut.isPending ? '保存中...' : <><Check className="w-4 h-4"/>保存</>}
            </button>
          </div>
        </div>
      </div>
  );
}

/* ---------- 用户列表弹窗 ---------- */
function UsersModal({roleId, roleName, onClose}: {roleId: number; roleName: string; onClose: () => void}) {
  const {data: users} = useQuery({
    queryKey: ['admin-role-users', roleId],
    queryFn: async () => {
      const res = await apiClient.get('/api/v2/dashboard/user-management/users', {per_page: 100});
      if (!res.success || !res.data) return [];
      const all = Array.isArray(res.data) ? res.data : (res.data.users || []);
      return all;
    },
  });
  const assigned = (users || []).filter((u: any) =>
      u.roles?.some((r: any) => r.id === roleId)
  );

  return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onClick={onClose}>
        <div className="bg-white dark:bg-gray-900 rounded-2xl shadow-2xl border border-gray-200 dark:border-gray-700 w-full max-w-lg max-h-[70vh] flex flex-col" onClick={e => e.stopPropagation()}>
          <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2"><Users className="w-5 h-5"/>{roleName} 的用户</h2>
            <button onClick={onClose} className="p-1 text-gray-400 hover:text-gray-600"><X className="w-5 h-5"/></button>
          </div>
          <div className="p-6 overflow-y-auto">
            {assigned.length === 0 ? (
                <p className="text-sm text-gray-400 text-center py-8">暂无用户拥有此角色</p>
            ) : (
                <div className="space-y-2">
                  {assigned.map((u: any) => (
                      <div key={u.id} className="flex items-center gap-3 p-3 bg-gray-50 dark:bg-gray-800 rounded-xl">
                        <div className="w-8 h-8 rounded-full bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center text-xs font-bold text-blue-600 dark:text-blue-400">
                          {u.username?.[0]?.toUpperCase() || '?'}
                        </div>
                        <div>
                          <p className="text-sm font-medium text-gray-900 dark:text-white">{u.username}</p>
                          <p className="text-xs text-gray-400">{u.email || '-'}</p>
                        </div>
                      </div>
                  ))}
                </div>
            )}
          </div>
        </div>
      </div>
  );
}

/* ---------- 主页面 ---------- */
function RolesInner() {
  const qc = useQueryClient();
  const [modal, setModal] = useState<{mode: 'create' | 'edit'; role?: any} | null>(null);
  const [usersModal, setUsersModal] = useState<{id: number; name: string} | null>(null);
  const [deleteConfirm, setDeleteConfirm] = useState<any | null>(null);

  const {data: roles, isLoading} = useQuery({
    queryKey: ['admin-roles'],
    queryFn: async () => {
      const res = await apiClient.get('/api/v2/security/rbac/roles');
      return res.success && res.data ? (Array.isArray(res.data) ? res.data : res.data.roles || []) : [];
    },
  });

  const {data: permissions} = useQuery({
    queryKey: ['admin-permissions'],
    queryFn: async () => {
      const res = await apiClient.get('/api/v2/security/rbac/permissions');
      return res.success && res.data ? (Array.isArray(res.data) ? res.data : res.data.permissions || []) : [];
    },
  });

  const deleteMut = useMutation({
    mutationFn: (id: number) => apiClient.delete(`/api/v2/security/rbac/roles/${id}`),
    onSuccess: (res: any) => {
      if (!res.success) return;
      qc.invalidateQueries({queryKey: ['admin-roles']});
      setDeleteConfirm(null);
    },
  });

  return (
      <AdminShell title="角色权限" actions={
        <button onClick={() => setModal({mode: 'create'})}
                className="px-4 py-1.5 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg flex items-center gap-1.5">
          <Plus className="w-4 h-4"/>新建角色
        </button>
      }>
        <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 overflow-hidden">
          {isLoading ? (
              <div className="p-12 text-center"><div className="animate-spin w-6 h-6 border-2 border-blue-600 border-t-transparent rounded-full mx-auto"/></div>
          ) : !roles?.length ? (
              <div className="p-12 text-center text-gray-400">暂无角色</div>
          ) : (
              <table className="w-full"><thead className="bg-gray-50 dark:bg-gray-800 border-b">
              <tr>
                <th className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase">角色</th>
                <th className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase hidden sm:table-cell">标识</th>
                <th className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase">权限数</th>
                <th className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase hidden md:table-cell">用户数</th>
                <th className="px-5 py-3 text-right text-xs font-semibold text-gray-500 uppercase">操作</th>
              </tr>
              </thead><tbody className="divide-y">
              {roles.map((r: any) => (
                  <tr key={r.id} className="hover:bg-gray-50 dark:hover:bg-gray-800/50">
                    <td className="px-5 py-4">
                      <div className="flex items-center gap-2">
                        <Shield className={`w-4 h-4 ${r.is_system ? 'text-purple-500' : 'text-blue-500'}`}/>
                        <span className="font-medium text-gray-900 dark:text-white text-sm">{r.name}</span>
                        {r.is_system && <span className="px-1.5 py-0.5 text-[10px] rounded bg-purple-100 dark:bg-purple-900/30 text-purple-600 dark:text-purple-400 font-medium">系统</span>}
                      </div>
                    </td>
                    <td className="px-5 py-4 text-sm text-gray-500 hidden sm:table-cell"><code className="text-xs bg-gray-100 dark:bg-gray-800 px-1.5 py-0.5 rounded">{r.slug}</code></td>
                    <td className="px-5 py-4 text-sm text-gray-500">{r.permission_count || 0}</td>
                    <td className="px-5 py-4 hidden md:table-cell">
                      <button onClick={() => setUsersModal({id: r.id, name: r.name})}
                              className="text-sm text-blue-600 dark:text-blue-400 hover:underline flex items-center gap-1">
                        {r.user_count || 0} <Users className="w-3 h-3"/>
                      </button>
                    </td>
                    <td className="px-5 py-4 text-right space-x-1">
                      <button onClick={() => setModal({mode: 'edit', role: {...r, permission_codes: r.permission_codes || []}})}
                              className="p-1.5 inline-block text-gray-400 hover:text-blue-600 rounded-lg hover:bg-blue-50 dark:hover:bg-blue-900/20">
                        <Edit className="w-4 h-4"/>
                      </button>
                      {!r.is_system && (
                          <button onClick={() => setDeleteConfirm(r)}
                                  className="p-1.5 inline-block text-gray-400 hover:text-red-600 rounded-lg hover:bg-red-50 dark:hover:bg-red-900/20">
                            <Trash2 className="w-4 h-4"/>
                          </button>
                      )}
                    </td>
                  </tr>
              ))}
              </tbody></table>
          )}
        </div>

        {/* 创建/编辑 Modal */}
        {modal && <RoleModal mode={modal.mode} role={modal.role} permissions={permissions || []} onClose={() => setModal(null)}/>}

        {/* 用户列表 Modal */}
        {usersModal && <UsersModal roleId={usersModal.id} roleName={usersModal.name} onClose={() => setUsersModal(null)}/>}

        {/* 删除确认 */}
        {deleteConfirm && (
            <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onClick={() => setDeleteConfirm(null)}>
              <div className="bg-white dark:bg-gray-900 rounded-2xl shadow-2xl border border-gray-200 dark:border-gray-700 w-full max-w-md p-6" onClick={e => e.stopPropagation()}>
                <div className="flex items-center gap-3 mb-4">
                  <div className="w-10 h-10 rounded-full bg-red-100 dark:bg-red-900/30 flex items-center justify-center"><AlertTriangle className="w-5 h-5 text-red-600 dark:text-red-400"/></div>
                  <div>
                    <h3 className="font-semibold text-gray-900 dark:text-white">确认删除</h3>
                    <p className="text-sm text-gray-500">此操作不可撤销</p>
                  </div>
                </div>
                <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">确定要删除角色 <strong>{deleteConfirm.name}</strong> 吗？</p>
                <p className="text-xs text-gray-400 mb-6">拥有该角色的用户将失去相关权限。</p>
                <div className="flex justify-end gap-3">
                  <button onClick={() => setDeleteConfirm(null)} className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-xl transition-colors">取消</button>
                  <button onClick={() => deleteMut.mutate(deleteConfirm.id)}
                          className="px-4 py-2 text-sm font-medium bg-red-600 hover:bg-red-700 text-white rounded-xl transition-colors flex items-center gap-1.5"
                          disabled={deleteMut.isPending}>
                    {deleteMut.isPending ? '删除中...' : <><Trash2 className="w-4 h-4"/>删除</>}
                  </button>
                </div>
              </div>
            </div>
        )}
      </AdminShell>
  );
}

export default function AdminRoles() {
  return <AuthGuard><QueryProvider><RolesInner/></QueryProvider></AuthGuard>;
}
