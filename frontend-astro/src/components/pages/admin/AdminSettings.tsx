'use client';

import React, {useState} from 'react';
import {useQuery, useMutation} from '@tanstack/react-query';
import {AuthGuard} from '@/components/AuthGuard';
import {QueryProvider} from '@/components/QueryProvider';
import {AdminShell} from '@/components/admin/AdminShell';
import {apiClient} from '@/lib/api/base-client';
import {Save} from 'lucide-react';

function SettingsInner() {
  const [siteName, setSiteName] = useState('');
  const [description, setDescription] = useState('');

  const {isLoading} = useQuery({
    queryKey: ['admin-settings'],
    queryFn: async () => {
      const res = await apiClient.get('/dashboard/system-settings');
      if (res.success && res.data) {
        const d = res.data as any;
        setSiteName(d.site_name || d.title || '');
        setDescription(d.description || d.site_description || '');
      }
      return res;
    },
  });

  const saveMut = useMutation({
    mutationFn: () => apiClient.put('/dashboard/system-settings', {site_name: siteName, description}),
    onSuccess: (res) => { if (res.success) alert('保存成功'); },
  });

  return (
    <AdminShell title="系统设置">
      <div className="max-w-2xl space-y-6">
        <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 p-6 space-y-4">
          <h3 className="font-semibold text-gray-900 dark:text-white">基本设置</h3>
          <div><label className="block text-sm text-gray-500 mb-1">站点名称</label>
            <input type="text" value={siteName} onChange={e => setSiteName(e.target.value)} className="w-full px-4 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl bg-gray-50 dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white"/></div>
          <div><label className="block text-sm text-gray-500 mb-1">站点描述</label>
            <textarea rows={3} value={description} onChange={e => setDescription(e.target.value)} className="w-full px-4 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl bg-gray-50 dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white resize-none"/></div>
          <div className="flex justify-end">
            <button onClick={() => saveMut.mutate()} disabled={saveMut.isPending} className="px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-xl disabled:opacity-50 flex items-center gap-2"><Save className="w-4 h-4"/>{saveMut.isPending ? '保存...' : '保存设置'}</button>
          </div>
        </div>
      </div>
    </AdminShell>
  );
}

export default function AdminSettings() {
  return <AuthGuard><QueryProvider><SettingsInner /></QueryProvider></AuthGuard>;
}
