'use client';

import React, {useState, useEffect, useRef} from 'react';
import {useQuery, useMutation, useQueryClient} from '@tanstack/react-query';
import {AuthGuard} from '@/components/AuthGuard';
import {QueryProvider} from '@/components/QueryProvider';
import {AdminShell} from '@/components/admin/AdminShell';
import {apiClient} from '@/lib/api/base-client';
import {ChevronLeft, ChevronRight, Search, X} from 'lucide-react';

function useDebounce<T>(value: T, delay: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => { const t = setTimeout(() => setDebounced(value), delay); return () => clearTimeout(t); }, [value, delay]);
  return debounced;
}

const STATUS_OPTIONS = [
  {value: '', label: '全部'},
  {value: 'active', label: '正常'},
  {value: 'banned', label: '禁用'},
] as const;

function UsersInner() {
  const qc = useQueryClient();
  const [page, setPage] = useState(1);
  const [searchInput, setSearchInput] = useState('');
  const [status, setStatus] = useState('');
  const debouncedSearch = useDebounce(searchInput, 400);

  const prevFilters = useRef('');
  useEffect(() => {
    const f = `${status}-${debouncedSearch}`;
    if (prevFilters.current && prevFilters.current !== f) setPage(1);
    prevFilters.current = f;
  }, [status, debouncedSearch]);

  const {data, isLoading} = useQuery({
    queryKey: ['admin-users', page, status, debouncedSearch],
    queryFn: async () => {
      const params: Record<string, any> = {page, per_page: 20};
      if (debouncedSearch) params.search = debouncedSearch;
      const res = await apiClient.get('/api/v2/dashboard/user-management/users', params);
      if (!res.success || !res.data) return {users: [], total: 0};
      const users = Array.isArray(res.data) ? res.data : (res.data.users || []);
      const pagination = res.data.pagination || res.pagination || {};
      const total = pagination.total || users.length;
      return {users, total};
    },
  });

  const toggleMut = useMutation({
    mutationFn: ({id, action}: {id: number; action: 'ban' | 'unban'}) =>
        apiClient.post(`/api/v2/dashboard/user-management/users/${id}/${action}`),
    onSuccess: () => qc.invalidateQueries({queryKey: ['admin-users']}),
  });

  const users = data?.users || [];
  const total = data?.total || 0;
  const totalPages = Math.ceil(total / 20);

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
        <div className="flex items-center justify-center gap-1.5 mt-6 pb-6">
          <button disabled={page <= 1} onClick={() => setPage(p => p - 1)}
                  className="p-2 rounded-lg border border-gray-200 dark:border-gray-700 disabled:opacity-30 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors">
            <ChevronLeft className="w-4 h-4"/>
          </button>
          {pages.map((p, i) =>
              p === '...' ? <span key={`e-${i}`} className="px-2 text-gray-400">…</span> :
              <button key={p} onClick={() => setPage(p as number)}
                      className={`min-w-[36px] h-9 rounded-lg text-sm font-medium transition-colors ${
                          p === page ? 'bg-blue-600 text-white' : 'border border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800'
                      }`}>{p}</button>
          )}
          <button disabled={page >= totalPages} onClick={() => setPage(p => p + 1)}
                  className="p-2 rounded-lg border border-gray-200 dark:border-gray-700 disabled:opacity-30 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors">
            <ChevronRight className="w-4 h-4"/>
          </button>
        </div>
    );
  };

  return (
      <AdminShell title="用户管理">
        {/* 筛选栏 */}
        <div className="flex flex-wrap items-center gap-3 mb-4">
          <div className="relative flex-1 min-w-[180px]">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400"/>
            <input type="text" value={searchInput} onChange={e => setSearchInput(e.target.value)}
                   placeholder="搜索用户名或邮箱..." className="w-full pl-9 pr-8 py-2 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white"/>
            {searchInput && <button onClick={() => setSearchInput('')} className="absolute right-2 top-1/2 -translate-y-1/2 p-0.5 text-gray-400 hover:text-gray-600"><X className="w-4 h-4"/></button>}
          </div>
          <div className="flex gap-1 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-xl p-1">
            {STATUS_OPTIONS.map(opt => (
                <button key={opt.value} onClick={() => setStatus(opt.value)}
                        className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                            status === opt.value ? 'bg-blue-600 text-white' : 'text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800'
                        }`}>{opt.label}</button>
            ))}
          </div>
          <span className="text-xs text-gray-400 ml-auto">共 {total} 位用户</span>
        </div>

        <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 overflow-hidden">
          {isLoading ? (
              <div className="p-12 text-center"><div className="animate-spin w-6 h-6 border-2 border-blue-600 border-t-transparent rounded-full mx-auto"/></div>
          ) : users.length === 0 ? (
              <div className="p-12 text-center text-gray-400">{debouncedSearch ? '未找到匹配的用户' : '暂无用户'}</div>
          ) : (
              <table className="w-full"><thead className="bg-gray-50 dark:bg-gray-800 border-b">
              <tr><th className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase">用户名</th><th className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase hidden sm:table-cell">邮箱</th><th className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase hidden md:table-cell">角色</th><th className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase">状态</th><th className="px-5 py-3 text-right text-xs font-semibold text-gray-500 uppercase">操作</th></tr>
              </thead><tbody className="divide-y">
              {users.map((u: any) => (
                  <tr key={u.id} className="hover:bg-gray-50 dark:hover:bg-gray-800/50">
                    <td className="px-5 py-4"><p className="font-medium text-gray-900 dark:text-white text-sm">{u.username}</p></td>
                    <td className="px-5 py-4 text-sm text-gray-500 hidden sm:table-cell">{u.email || '-'}</td>
                    <td className="px-5 py-4 hidden md:table-cell">
                      {u.roles?.length ? u.roles.map((r: any) => (
                          <span key={r.id} className="mr-1 px-2 py-0.5 text-xs rounded-full bg-gray-100 dark:bg-gray-800">{r.name}</span>
                      )) : <span className="px-2 py-0.5 text-xs rounded-full bg-gray-100 dark:bg-gray-800">{u.role || 'user'}</span>}
                    </td>
                    <td className="px-5 py-4">
                      <span className={`px-2 py-0.5 text-xs rounded-full font-medium ${
                          u.is_active !== false
                              ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                              : 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
                      }`}>{u.is_active !== false ? '正常' : '禁用'}</span>
                    </td>
                    <td className="px-5 py-4 text-right">
                      <button onClick={() => toggleMut.mutate({id: u.id, action: u.is_active !== false ? 'ban' : 'unban'})}
                              className={`px-3 py-1 text-xs rounded-lg border transition-colors ${
                                  u.is_active !== false
                                      ? 'border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-400 hover:bg-red-50 dark:hover:bg-red-900/20 hover:text-red-600'
                                      : 'border-green-200 dark:border-green-800 text-green-600 dark:text-green-400 hover:bg-green-50 dark:hover:bg-green-900/20'
                              }`}>
                        {u.is_active !== false ? '禁用' : '启用'}
                      </button>
                    </td>
                  </tr>
              ))}
              </tbody></table>
          )}
        </div>

        {renderPagination()}
      </AdminShell>
  );
}

export default function AdminUsers() {
  return <AuthGuard><QueryProvider><UsersInner /></QueryProvider></AuthGuard>;
}
