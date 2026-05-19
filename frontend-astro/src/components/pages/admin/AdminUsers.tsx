'use client';

import React, {useEffect, useState} from 'react';
import {UserManagementService} from '@/lib/api';
import type {UserWithRoles} from '@/lib/api';

const AdminUsers: React.FC = () => {
  const [users, setUsers] = useState<UserWithRoles[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    UserManagementService.getUsers({page: 1, per_page: 20}).then(res => {
      if (res.success && res.data) setUsers(res.data.users || []);
    }).finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="animate-spin w-8 h-8 border-2 border-blue-600 border-t-transparent rounded-full mx-auto" />;

  return (
    <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
      <table className="w-full">
        <thead className="bg-gray-50 dark:bg-gray-800">
          <tr>
            <th className="px-6 py-3 text-left text-sm font-medium text-gray-500">用户名</th>
            <th className="px-6 py-3 text-left text-sm font-medium text-gray-500">邮箱</th>
            <th className="px-6 py-3 text-left text-sm font-medium text-gray-500">角色</th>
            <th className="px-6 py-3 text-left text-sm font-medium text-gray-500">状态</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
          {users.map(u => (
            <tr key={u.id} className="hover:bg-gray-50 dark:hover:bg-gray-800">
              <td className="px-6 py-4 text-sm text-gray-900 dark:text-white">{u.username}</td>
              <td className="px-6 py-4 text-sm text-gray-500">{u.email}</td>
              <td className="px-6 py-4 text-sm text-gray-500">{u.roles?.map(r => r.name).join(', ')}</td>
              <td className="px-6 py-4"><span className={`px-2 py-1 text-xs rounded-full ${u.is_active ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>{u.is_active ? '活跃' : '禁用'}</span></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default AdminUsers;
