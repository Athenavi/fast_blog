'use client';

import React, {useState, useEffect, useRef, useMemo} from 'react';
import {useQuery, useMutation, useQueryClient} from '@tanstack/react-query';
import {AuthGuard} from '@/components/AuthGuard';
import {QueryProvider} from '@/components/QueryProvider';
import {AdminShell} from '@/components/admin/AdminShell';
import {PermissionGuard} from '@/components/admin/PermissionGuard';
import {useCapability} from '@/lib/hooks/useCapability';
import {adminService} from '@/lib/api/admin-service';
import {adminApi} from '@/lib/api/admin-api-client';
import {useDebounce} from '@/lib/hooks';
import {
  ChevronLeft,
  ChevronRight,
  Search,
  X,
  Shield,
  Crown,
  UserCheck,
  UserX,
  Users,
  Mail,
  Calendar,
  MoreHorizontal,
  Ban,
  CheckCircle,
  Eye,
  RefreshCw,
  TrendingUp,
  UserPlus,
  Key,
  Loader,
  Save
} from 'lucide-react';

const STATUS_OPTIONS = [
    {value: '', label: '全部', icon: Users},
    {value: 'active', label: '正常', icon: UserCheck},
    {value: 'banned', label: '禁用', icon: Ban},
] as const;

const ROLE_COLORS: Record<string, { bg: string; text: string; icon: React.ComponentType<{ className?: string }> }> = {
    admin: {bg: 'bg-purple-50 dark:bg-purple-900/20', text: 'text-purple-700 dark:text-purple-400', icon: Crown},
    editor: {bg: 'bg-blue-50 dark:bg-blue-900/20', text: 'text-blue-700 dark:text-blue-400', icon: Shield},
    user: {bg: 'bg-gray-50 dark:bg-gray-800', text: 'text-gray-600 dark:text-gray-400', icon: Users},
    vip: {bg: 'bg-amber-50 dark:bg-amber-900/20', text: 'text-amber-700 dark:text-amber-400', icon: Crown},
};

/* ── User Avatar ── */
const UserAvatar: React.FC<{ user: any; size?: 'sm' | 'md' | 'lg' }> = ({user, size = 'md'}) => {
    const sizes = {sm: 'w-8 h-8 text-xs', md: 'w-10 h-10 text-sm', lg: 'w-12 h-12 text-base'};
    const colors = ['from-blue-500 to-indigo-500', 'from-purple-500 to-pink-500', 'from-emerald-500 to-teal-500', 'from-amber-500 to-orange-500', 'from-rose-500 to-red-500'];
    const colorIndex = (user.username || '').charCodeAt(0) % colors.length;

    if (user.avatar) {
        return <img src={user.avatar} alt={user.username}
                    className={`${sizes[size]} rounded-full object-cover border-2 border-white dark:border-gray-800 shadow-sm`}/>;
    }
    return (
        <div
            className={`${sizes[size]} rounded-full bg-gradient-to-br ${colors[colorIndex]} flex items-center justify-center text-white font-bold shadow-sm`}>
            {(user.username || '?').charAt(0).toUpperCase()}
        </div>
    );
};

/* ── User Actions Menu ── */
const UserActions: React.FC<{ user: any; onToggle: (action: 'ban' | 'unban') => void }> = ({user, onToggle}) => {
    const [open, setOpen] = useState(false);
    const ref = useRef<HTMLDivElement>(null);
    const isActive = user.is_active !== false;

    useEffect(() => {
        if (!open) return;
        const handler = (e: MouseEvent) => {
            if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
        };
        document.addEventListener('mousedown', handler);
        return () => document.removeEventListener('mousedown', handler);
    }, [open]);

    return (
        <div className="relative" ref={ref}>
            <button onClick={() => setOpen(!open)}
                    className="p-2 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors">
                <MoreHorizontal className="w-4 h-4"/>
            </button>
            {open && (
                <div
                    className="absolute right-0 top-full mt-1 z-50 bg-white dark:bg-gray-800 rounded-xl shadow-xl border border-gray-200 dark:border-gray-700 p-1.5 min-w-[160px]">
                    <button onClick={() => {
                        setOpen(false);
                        onToggle(isActive ? 'ban' : 'unban');
                    }}
                            className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-colors ${
                                isActive
                                    ? 'text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20'
                                    : 'text-emerald-600 hover:bg-emerald-50 dark:hover:bg-emerald-900/20'
                            }`}>
                        {isActive ? <Ban className="w-4 h-4"/> : <CheckCircle className="w-4 h-4"/>}
                        {isActive ? '禁用用户' : '启用用户'}
                    </button>
                </div>
            )}
        </div>
    );
};

/* ── Role Assignment Modal ── */
const RoleAssignmentModal: React.FC<{
  user: any;
  onClose: () => void;
  onSuccess: () => void;
}> = ({ user, onClose, onSuccess }) => {
  const qc = useQueryClient();
  const [selectedRoleIds, setSelectedRoleIds] = useState<Set<number>>(new Set());
  const [error, setError] = useState('');
  const [initialized, setInitialized] = useState(false);

  // Fetch user's current roles
  const { data: userRoles } = useQuery({
    queryKey: ['admin-user-roles', user.id],
    queryFn: async () => {
      const res = await adminApi.get(`/api/v3/admin/users/${user.id}`, `/users/${user.id}`);
      const userData = res.success && res.data ? (res.data.data || res.data) : null;
      const roles = userData?.roles || [];
      if (!initialized) {
        setSelectedRoleIds(new Set(roles.map((r: any) => r.id || r.role_id)));
        setInitialized(true);
      }
      return roles;
    },
  });

  const { data: allRoles, isLoading: rolesLoading } = useQuery({
    queryKey: ['admin-roles-list'],
    queryFn: async () => {
      const res = await adminService.roles.listRoles();
      return res.success && res.data ? (Array.isArray(res.data) ? res.data : res.data.roles || []) : [];
    },
  });

  const assignMut = useMutation({
    mutationFn: async () => {
      // Send full set of selected role IDs (V3 replaces all, V2 may add incrementally)
      const res = await adminService.users.assignRoles(user.id, [...selectedRoleIds]);
      if (!res.success) throw new Error(res.error || 'Failed to assign roles');
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['admin-users'] });
      onSuccess();
      onClose();
    },
    onError: (e: any) => setError(e.message || '操作失败'),
  });

  const toggleRole = (roleId: number) => {
    const s = new Set(selectedRoleIds);
    s.has(roleId) ? s.delete(roleId) : s.add(roleId);
    setSelectedRoleIds(s);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm"
         onClick={onClose}>
      <div className="bg-white dark:bg-gray-900 rounded-2xl shadow-2xl w-full max-w-md max-h-[85vh] overflow-hidden transform transition-all"
           onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100 dark:border-gray-800">
          <div>
            <h2 className="font-semibold text-gray-900 dark:text-white text-base">管理角色</h2>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">{user.username}</p>
          </div>
          <button onClick={onClose}
                  className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-xl transition-colors">
            <X className="w-4.5 h-4.5"/>
          </button>
        </div>
        <div className="p-6 overflow-y-auto max-h-[calc(85vh-80px)]">
          {error && (
            <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 rounded-xl text-sm">
              {error}
            </div>
          )}
          {rolesLoading ? (
            <div className="flex items-center justify-center py-8">
              <Loader className="w-6 h-6 animate-spin text-gray-400"/>
            </div>
          ) : !allRoles || allRoles.length === 0 ? (
            <div className="text-center py-8 text-sm text-gray-500">暂无可用角色</div>
          ) : (
            <div className="space-y-2">
              {allRoles.map((role: any) => {
                const isSelected = selectedRoleIds.has(role.id);
                return (
                  <label key={role.id}
                         className={`flex items-center gap-3 p-3 rounded-xl cursor-pointer transition-all ${
                           isSelected
                             ? 'bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800'
                             : 'bg-gray-50 dark:bg-gray-800/50 border border-transparent hover:bg-gray-100 dark:hover:bg-gray-800'
                         }`}>
                    <input type="checkbox" checked={isSelected} onChange={() => toggleRole(role.id)}
                           className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"/>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-gray-900 dark:text-white">{role.name}</span>
                        {role.is_system && (
                          <span className="px-1.5 py-0.5 bg-purple-100 dark:bg-purple-900/30 text-purple-600 dark:text-purple-400 rounded text-[10px] font-semibold">
                            系统
                          </span>
                        )}
                      </div>
                      {role.description && (
                        <p className="text-xs text-gray-400 mt-0.5 truncate">{role.description}</p>
                      )}
                    </div>
                    <span className="text-xs text-gray-400">{role.permission_count || 0} 权限</span>
                  </label>
                );
              })}
            </div>
          )}
          <div className="mt-6 flex items-center justify-end gap-3">
            <button onClick={onClose}
                    className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-xl transition-colors">
              取消
            </button>
            <button onClick={() => assignMut.mutate()} disabled={assignMut.isPending}
                    className="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-xl transition-colors disabled:opacity-50 inline-flex items-center gap-2">
              {assignMut.isPending && <Loader className="w-4 h-4 animate-spin"/>}
              <Save className="w-4 h-4"/>
              保存
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

/* ── Table Skeleton ── */
const UserSkeleton = () => (
    <tr className="animate-pulse">
        <td className="px-5 py-4">
            <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-gray-200 dark:bg-gray-700 rounded-full"/>
                <div className="space-y-2">
                    <div className="h-4 w-28 bg-gray-200 dark:bg-gray-700 rounded"/>
                    <div className="h-3 w-36 bg-gray-100 dark:bg-gray-800 rounded"/>
                </div>
            </div>
        </td>
        <td className="px-5 py-4 hidden sm:table-cell">
            <div className="h-4 w-32 bg-gray-100 dark:bg-gray-800 rounded"/>
        </td>
        <td className="px-5 py-4 hidden md:table-cell">
            <div className="h-5 w-16 bg-gray-200 dark:bg-gray-700 rounded-full"/>
        </td>
        <td className="px-5 py-4">
            <div className="h-5 w-14 bg-gray-200 dark:bg-gray-700 rounded-full"/>
        </td>
        <td className="px-5 py-4">
            <div className="flex justify-end">
                <div className="w-8 h-8 bg-gray-100 dark:bg-gray-800 rounded-lg"/>
            </div>
        </td>
    </tr>
);

function AdminUsersInner() {
  const qc = useQueryClient();
  const [page, setPage] = useState(1);
  const [searchInput, setSearchInput] = useState('');
  const [status, setStatus] = useState('');
  const [roleModalUser, setRoleModalUser] = useState<any | null>(null);
  const debouncedSearch = useDebounce(searchInput, 400);
  const canEdit = useCapability('user:edit');

  const prevFilters = useRef('');
  useEffect(() => {
    const f = `${status}-${debouncedSearch}`;
    if (prevFilters.current && prevFilters.current !== f) setPage(1);
    prevFilters.current = f;
  }, [status, debouncedSearch]);

    const {data, isLoading, refetch} = useQuery({
    queryKey: ['admin-users', page, status, debouncedSearch],
    queryFn: async () => {
      const params: Record<string, any> = {page, per_page: 20};
      if (debouncedSearch) params.search = debouncedSearch;
      const res = await adminService.users.list(params);
      if (!res.success || !res.data) return {users: [], total: 0};
      const users = Array.isArray(res.data) ? res.data : (res.data.users || []);
      const pagination = res.data.pagination || res.pagination || {};
      const total = pagination.total || users.length;
      return {users, total};
    },
  });

  const toggleMut = useMutation({
    mutationFn: ({id, action}: {id: number; action: 'ban' | 'unban'}) =>
        adminService.users.update(id, {is_active: action === 'unban'}),
    onSuccess: () => qc.invalidateQueries({queryKey: ['admin-users']}),
  });

  const users = data?.users || [];
  const total = data?.total || 0;
  const totalPages = Math.ceil(total / 20);

    // Stats
    const stats = useMemo(() => {
      const active = users.filter((u: any) => u.is_active !== false).length;
      const banned = users.filter((u: any) => u.is_active === false).length;
      const admins = users.filter((u: any) => u.roles?.some((r: any) => r.name === 'admin') || u.role === 'admin').length;
        return {active, banned, admins};
    }, [users]);

  const renderPagination = () => {
    if (totalPages <= 1) return null;
    const pages: (number | string)[] = [];
    const delta = 2, left = Math.max(2, page - delta), right = Math.min(totalPages - 1, page + delta);
    pages.push(1);
    if (left > 2) pages.push('...');
    for (let i = left; i <= right; i++) pages.push(i);
    if (right < totalPages - 1) pages.push('...');
    if (totalPages > 1) pages.push(totalPages);
    return (
        <div className="flex items-center justify-between px-5 py-4 border-t border-gray-100 dark:border-gray-800">
            <span className="text-xs text-gray-400">第 {page} / {totalPages} 页</span>
            <div className="flex items-center gap-1.5">
          <button disabled={page <= 1} onClick={() => setPage(p => p - 1)}
                  className="p-2 rounded-lg border border-gray-200 dark:border-gray-700 disabled:opacity-30 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors">
            <ChevronLeft className="w-4 h-4"/>
          </button>
          {pages.map((p, i) =>
              p === '...' ? <span key={`e-${i}`} className="px-2 text-gray-400 text-sm">…</span> :
                  <button key={p} onClick={() => setPage(p as number)}
                          className={`min-w-[36px] h-9 rounded-lg text-sm font-medium transition-all ${
                              p === page ? 'bg-blue-600 text-white shadow-md shadow-blue-500/20' : 'border border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800'
                          }`}>{p}</button>
          )}
          <button disabled={page >= totalPages} onClick={() => setPage(p => p + 1)}
                  className="p-2 rounded-lg border border-gray-200 dark:border-gray-700 disabled:opacity-30 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors">
            <ChevronRight className="w-4 h-4"/>
          </button>
        </div>
        </div>
    );
  };

  return (
      <AdminShell title="用户管理" actions={
          <button onClick={() => refetch()}
                  className="p-2 rounded-lg border border-gray-200 dark:border-gray-700 text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
                  title="刷新">
              <RefreshCw className="w-4 h-4"/>
          </button>
      }>
          {/* Stats */}
          <div className="grid grid-cols-3 gap-3 mb-6">
              {[
                  {
                      label: '总用户',
                      value: total,
                      icon: Users,
                      bg: 'bg-blue-50 dark:bg-blue-900/20',
                      text: 'text-blue-600 dark:text-blue-400',
                      gradient: 'from-blue-500 to-indigo-500'
                  },
                  {
                      label: '正常',
                      value: stats.active,
                      icon: UserCheck,
                      bg: 'bg-emerald-50 dark:bg-emerald-900/20',
                      text: 'text-emerald-600 dark:text-emerald-400',
                      gradient: 'from-emerald-500 to-teal-500'
                  },
                  {
                      label: '禁用',
                      value: stats.banned,
                      icon: Ban,
                      bg: 'bg-red-50 dark:bg-red-900/20',
                      text: 'text-red-600 dark:text-red-400',
                      gradient: 'from-red-500 to-rose-500'
                  },
              ].map(s => (
                  <div key={s.label} className={`${s.bg} rounded-xl p-4 border border-gray-100 dark:border-gray-800`}>
                      <div className="flex items-center justify-between mb-2">
                          <span className={`text-xs font-semibold ${s.text} uppercase tracking-wider`}>{s.label}</span>
                          <div
                              className={`w-8 h-8 rounded-lg bg-gradient-to-br ${s.gradient} flex items-center justify-center`}>
                              <s.icon className="w-4 h-4 text-white"/>
                          </div>
                      </div>
                      <div className="text-2xl font-bold text-gray-900 dark:text-white">{s.value.toLocaleString()}</div>
                  </div>
              ))}
          </div>

          {/* Filters */}
          <div className="flex flex-wrap items-center gap-3 mb-4">
              <div className="relative flex-1 min-w-[200px]">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400"/>
                  <input type="text" value={searchInput} onChange={e => setSearchInput(e.target.value)}
                         placeholder="搜索用户名或邮箱..."
                         className="w-full pl-10 pr-10 py-2.5 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 dark:text-white transition-all"/>
                  {searchInput && (
                      <button onClick={() => setSearchInput('')}
                              className="absolute right-3 top-1/2 -translate-y-1/2 p-0.5 text-gray-400 hover:text-gray-600 transition-colors">
                          <X className="w-4 h-4"/>
                      </button>
                  )}
              </div>
              <div
                  className="flex gap-1 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-xl p-1">
                  {STATUS_OPTIONS.map(opt => (
                      <button key={opt.value} onClick={() => setStatus(opt.value)}
                              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                                  status === opt.value ? 'bg-blue-600 text-white shadow-sm' : 'text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800'
                              }`}>
                          <opt.icon className="w-3.5 h-3.5"/>
                          {opt.label}
                      </button>
                  ))}
              </div>
              <span className="text-xs text-gray-400 ml-auto">共 {total} 位用户</span>
          </div>

          {/* Users Table */}
          <div
              className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-100 dark:border-gray-800 overflow-hidden shadow-sm">
              {isLoading ? (
                  <table className="w-full">
                      <thead
                          className="bg-gray-50/80 dark:bg-gray-800/50 border-b border-gray-100 dark:border-gray-800">
                      <tr>
                        <th
                          className="px-5 py-3.5 text-left text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">用户
                        </th>
                        <th
                          className="px-5 py-3.5 text-left text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider hidden sm:table-cell">邮箱
                        </th>
                        <th
                          className="px-5 py-3.5 text-left text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider hidden md:table-cell">角色
                        </th>
                        <th
                          className="px-5 py-3.5 text-left text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">状态
                        </th>
                        <th
                          className="px-5 py-3.5 text-right text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">操作
                        </th>
                      </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-50 dark:divide-gray-800/50">
                      {[1, 2, 3, 4, 5].map(i => <UserSkeleton key={i}/>)}
                      </tbody>
                  </table>
              ) : users.length === 0 ? (
                  <div className="p-16 text-center">
                      <div
                          className="w-16 h-16 bg-gray-100 dark:bg-gray-800 rounded-2xl flex items-center justify-center mx-auto mb-4">
                          <Users className="w-8 h-8 text-gray-300 dark:text-gray-600"/>
                      </div>
                      <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-1">
                          {debouncedSearch ? '未找到匹配的用户' : '暂无用户'}
                      </h3>
                    <p className="text-sm text-gray-500 dark:text-gray-400">
                          {debouncedSearch ? '尝试使用不同的关键词搜索' : '等待用户注册'}
                      </p>
                  </div>
              ) : (
                  <>
                      <table className="w-full">
                          <thead
                              className="bg-gray-50/80 dark:bg-gray-800/50 border-b border-gray-100 dark:border-gray-800">
                          <tr>
                            <th
                              className="px-5 py-3.5 text-left text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">用户
                            </th>
                            <th
                              className="px-5 py-3.5 text-left text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider hidden sm:table-cell">邮箱
                            </th>
                            <th
                              className="px-5 py-3.5 text-left text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider hidden md:table-cell">角色
                            </th>
                            <th
                              className="px-5 py-3.5 text-left text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">状态
                            </th>
                            <th
                              className="px-5 py-3.5 text-right text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">操作
                            </th>
                          </tr>
                          </thead>
                          <tbody className="divide-y divide-gray-50 dark:divide-gray-800/50">
                          {users.map((u: any) => {
                              const isActive = u.is_active !== false;
                              const role = u.roles?.[0]?.name || u.role || 'user';
                              const roleConfig = ROLE_COLORS[role] || ROLE_COLORS.user;
                              const RoleIcon = roleConfig.icon;

                              return (
                                  <tr key={u.id}
                                      className="group hover:bg-gray-50/80 dark:hover:bg-gray-800/30 transition-colors">
                                      <td className="px-5 py-4">
                                          <div className="flex items-center gap-3">
                                              <UserAvatar user={u}/>
                                              <div className="min-w-0">
                                                  <p className="font-medium text-gray-900 dark:text-white text-sm group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">{u.username}</p>
                                                  <div className="flex items-center gap-1.5 mt-0.5">
                                                      <Calendar className="w-3 h-3 text-gray-400"/>
                                                      <span
                                                          className="text-xs text-gray-400">{u.created_at ? new Date(u.created_at).toLocaleDateString('zh-CN') : ''}</span>
                                                  </div>
                                              </div>
                                          </div>
                                      </td>
                                      <td className="px-5 py-4 hidden sm:table-cell">
                                        <div
                                          className="flex items-center gap-1.5 text-sm text-gray-500 dark:text-gray-400">
                                              <Mail className="w-3.5 h-3.5 text-gray-400"/>{u.email || '—'}
                                          </div>
                                      </td>
                                      <td className="px-5 py-4 hidden md:table-cell">
                        <span
                            className={`inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium rounded-full ${roleConfig.bg} ${roleConfig.text}`}>
                          <RoleIcon className="w-3 h-3"/>{role}
                        </span>
                                      </td>
                                      <td className="px-5 py-4">
                        <span
                            className={`inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium rounded-full ${
                                isActive
                                    ? 'bg-emerald-50 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-400'
                                    : 'bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400'
                            }`}>
                          <span className={`w-1.5 h-1.5 rounded-full ${isActive ? 'bg-emerald-500' : 'bg-red-500'}`}/>
                            {isActive ? '正常' : '禁用'}
                        </span>
                                      </td>
                                      <td className="px-5 py-4 text-right">
                                          <div className="flex items-center justify-end gap-1">
                                              {canEdit && (
                                              <button onClick={() => toggleMut.mutate({
                                                  id: u.id,
                                                  action: isActive ? 'ban' : 'unban'
                                              })}
                                                      className={`p-2 rounded-lg transition-colors ${
                                                          isActive
                                                              ? 'text-gray-400 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20'
                                                              : 'text-gray-400 hover:text-emerald-600 hover:bg-emerald-50 dark:hover:bg-emerald-900/20'
                                                      }`} title={isActive ? '禁用' : '启用'}>
                                                  {isActive ? <Ban className="w-4 h-4"/> :
                                                      <CheckCircle className="w-4 h-4"/>}
                                              </button>
                                              )}
                                              <button onClick={() => setRoleModalUser(u)}
                                                      className="p-2 rounded-lg text-gray-400 hover:text-purple-600 hover:bg-purple-50 dark:hover:bg-purple-900/20 transition-colors"
                                                      title="管理角色">
                                                <Key className="w-4 h-4"/>
                                              </button>
                                              <UserActions user={u}
                                                           onToggle={(action) => toggleMut.mutate({id: u.id, action})}/>
                                          </div>
                                      </td>
                                  </tr>
                              );
                          })}
                          </tbody>
                      </table>
                      {renderPagination()}
                  </>
              )}
          </div>
          {roleModalUser && (
              <RoleAssignmentModal user={roleModalUser} onClose={() => setRoleModalUser(null)}
                                   onSuccess={() => refetch()}/>
          )}
      </AdminShell>
  );
}

export default function AdminUsers() {
  return (
    <QueryProvider>
      <AuthGuard>
        <PermissionGuard capability="user:view">
          <AdminUsersInner />
        </PermissionGuard>
      </AuthGuard>
    </QueryProvider>
  );
}
