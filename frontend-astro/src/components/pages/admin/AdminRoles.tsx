'use client';

import React from 'react';
import {useQuery} from '@tanstack/react-query';
import {AuthGuard} from '@/components/AuthGuard';
import {QueryProvider} from '@/components/QueryProvider';
import {AdminShell} from '@/components/admin/AdminShell';
import {apiClient} from '@/lib/api/base-client';
import {Shield, Edit, Trash2} from 'lucide-react';

function RolesInner() {
  const {data: roles, isLoading} = useQuery({
    queryKey: ['admin-roles'],
    queryFn: async () => {
      const res = await apiClient.get('/security/rbac/roles');
      return res.success && res.data ? (Array.isArray(res.data) ? res.data : res.data.roles || []) : [];
    },
  });

  return (
    <AdminShell title="角色权限">
      <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 overflow-hidden">
        {isLoading ? (
          <div className="p-12 text-center"><div className="animate-spin w-6 h-6 border-2 border-blue-600 border-t-transparent rounded-full mx-auto"/></div>
        ) : !roles?.length ? (
          <div className="p-12 text-center text-gray-400">暂无角色</div>
        ) : (
          <table className="w-full"><thead className="bg-gray-50 dark:bg-gray-800 border-b">
            <tr><th className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase">角色</th><th className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase hidden sm:table-cell">描述</th><th className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase hidden md:table-cell">用户数</th><th className="px-5 py-3 text-right text-xs font-semibold text-gray-500 uppercase">操作</th></tr>
          </thead><tbody className="divide-y">
            {roles.map((r: any) => (
              <tr key={r.id} className="hover:bg-gray-50 dark:hover:bg-gray-800/50">
                <td className="px-5 py-4"><div className="flex items-center gap-2"><Shield className="w-4 h-4 text-gray-400"/><span className="font-medium text-gray-900 dark:text-white text-sm">{r.name}</span></div></td>
                <td className="px-5 py-4 text-sm text-gray-500 hidden sm:table-cell">{r.description || '-'}</td>
                <td className="px-5 py-4 text-sm text-gray-500 hidden md:table-cell">{r.user_count || 0}</td>
                <td className="px-5 py-4 text-right">
                  <button className="p-1.5 inline-block text-gray-400 hover:text-blue-600"><Edit className="w-4 h-4"/></button>
                  <button className="p-1.5 inline-block text-gray-400 hover:text-red-600"><Trash2 className="w-4 h-4"/></button>
                </td>
              </tr>
            ))}
          </tbody></table>
        )}
      </div>
    </AdminShell>
  );
}

export default function AdminRoles() {
  return <AuthGuard><QueryProvider><RolesInner /></QueryProvider></AuthGuard>;
}
