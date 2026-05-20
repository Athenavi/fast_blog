'use client';

import React, {useState} from 'react';
import {useQuery, useMutation, useQueryClient} from '@tanstack/react-query';
import {AuthGuard} from '@/components/AuthGuard';
import {QueryProvider} from '@/components/QueryProvider';
import {AdminShell} from '@/components/admin/AdminShell';
import {apiClient} from '@/lib/api/base-client';
import {Search, ShieldAlert, Ban, Check} from 'lucide-react';

function UsersInner() {
  const [search, setSearch] = useState('');
  const {data: users, isLoading} = useQuery({
    queryKey: ['admin-users', search],
    queryFn: async () => {
      const res = await apiClient.get('/dashboard/user-management/users', {q: search || undefined, per_page: 50});
      return res.success && res.data ? (Array.isArray(res.data) ? res.data : res.data.users || []) : [];
    },
  });

  const toggleMut = useMutation({
    mutationFn: ({id, action}: {id: number; action: 'ban' | 'unban'}) => apiClient.post(`/dashboard/user-management/users/${id}/${action}`),
    onSuccess: () => { /* refresh would go here */ },
  });

  return (
    <AdminShell title="用户管理">
      <div className="relative mb-4">
        <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400"/>
        <input type="text" value={search} onChange={e => setSearch(e.target.value)} placeholder="搜索用户..." className="w-full pl-10 pr-4 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl bg-white dark:bg-gray-900 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white"/>
      </div>
      <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 overflow-hidden">
        {isLoading ? (
          <div className="p-12 text-center"><div className="animate-spin w-6 h-6 border-2 border-blue-600 border-t-transparent rounded-full mx-auto"/></div>
        ) : !users?.length ? (
          <div className="p-12 text-center text-gray-400">暂无用户</div>
        ) : (
          <table className="w-full"><thead className="bg-gray-50 dark:bg-gray-800 border-b">
            <tr><th className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase">用户名</th><th className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase hidden sm:table-cell">邮箱</th><th className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase hidden md:table-cell">角色</th><th className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase">状态</th><th className="px-5 py-3 text-right text-xs font-semibold text-gray-500 uppercase">操作</th></tr>
          </thead><tbody className="divide-y">
            {users.map((u: any) => (
              <tr key={u.id} className="hover:bg-gray-50 dark:hover:bg-gray-800/50">
                <td className="px-5 py-4"><p className="font-medium text-gray-900 dark:text-white text-sm">{u.username}</p></td>
                <td className="px-5 py-4 text-sm text-gray-500 hidden sm:table-cell">{u.email || '-'}</td>
                <td className="px-5 py-4 hidden md:table-cell"><span className="px-2 py-0.5 text-xs rounded-full bg-gray-100 dark:bg-gray-800">{u.role || u.roles?.[0] || 'user'}</span></td>
                <td className="px-5 py-4"><span className={`px-2 py-0.5 text-xs rounded-full ${u.is_active !== false ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>{u.is_active !== false ? '正常' : '禁用'}</span></td>
                <td className="px-5 py-4 text-right">
                  <button onClick={() => toggleMut.mutate({id: u.id, action: u.is_active !== false ? 'ban' : 'unban'})} className="px-3 py-1 text-xs border border-gray-200 dark:border-gray-700 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800">{u.is_active !== false ? '禁用' : '启用'}</button>
                </td>
              </tr>
            ))}
          </tbody></table>
        )}
      </div>
    </AdminShell>
  );
}

export default function AdminUsers() {
  return <AuthGuard><QueryProvider><UsersInner /></QueryProvider></AuthGuard>;
}
