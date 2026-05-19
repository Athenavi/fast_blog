'use client';

import React, {useEffect, useState} from 'react';
import {RoleManagementService} from '@/lib/api';
import type {Role} from '@/lib/api';

const AdminRoles: React.FC = () => {
  const [roles, setRoles] = useState<Role[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    RoleManagementService.getRoles({page: 1, per_page: 20}).then(res => {
      if (res.success && res.data) setRoles(res.data.roles || []);
    }).finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="animate-spin w-8 h-8 border-2 border-blue-600 border-t-transparent rounded-full mx-auto" />;

  return (
    <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
      <table className="w-full">
        <thead className="bg-gray-50 dark:bg-gray-800">
          <tr>
            <th className="px-6 py-3 text-left text-sm font-medium text-gray-500">角色名</th>
            <th className="px-6 py-3 text-left text-sm font-medium text-gray-500">描述</th>
            <th className="px-6 py-3 text-left text-sm font-medium text-gray-500">用户数</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
          {roles.map(r => (
            <tr key={r.id} className="hover:bg-gray-50 dark:hover:bg-gray-800">
              <td className="px-6 py-4 text-sm font-medium text-gray-900 dark:text-white">{r.name}</td>
              <td className="px-6 py-4 text-sm text-gray-500">{r.description || '-'}</td>
              <td className="px-6 py-4 text-sm text-gray-500">{r.user_count || 0}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default AdminRoles;
