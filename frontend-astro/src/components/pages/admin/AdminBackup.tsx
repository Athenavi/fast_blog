'use client';

import React from 'react';
import {useQuery, useMutation, useQueryClient} from '@tanstack/react-query';
import {AuthGuard} from '@/components/AuthGuard';
import {QueryProvider} from '@/components/QueryProvider';
import {AdminShell} from '@/components/admin/AdminShell';
import {apiClient} from '@/lib/api/base-client';
import {Database, HardDrive, Download, RotateCcw, Trash2, Clock} from 'lucide-react';

function BackupInner() {
  const qc = useQueryClient();
  const {data: backups, isLoading} = useQuery({
    queryKey: ['admin-backups'],
    queryFn: async () => {
      const res = await apiClient.get<any[]>('/backup/list');
      return res.success && res.data ? (Array.isArray(res.data) ? res.data : []) : [];
    },
  });
  const {data: stats} = useQuery({
    queryKey: ['admin-backup-stats'],
    queryFn: async () => {
      const res = await apiClient.get<any>('/backup/stats');
      return res.success && res.data ? res.data : {};
    },
  });

  const createMut = useMutation({
    mutationFn: (type: string) => apiClient.post(`/backup/${type}`),
    onSuccess: () => qc.invalidateQueries({queryKey: ['admin-backups']}),
  });
  const delMut = useMutation({
    mutationFn: () => apiClient.delete('/backup/delete'),
    onSuccess: () => qc.invalidateQueries({queryKey: ['admin-backups']}),
  });

  return (
    <AdminShell title="备份管理">
      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <div className="bg-white dark:bg-gray-900 p-5 rounded-2xl border border-gray-200"><div className="flex items-center gap-2 text-sm text-gray-500 mb-1"><Database className="w-4 h-4"/>数据库备份</div><p className="text-2xl font-bold">{stats?.database_count ?? backups?.filter((b:any) => b.type === 'database').length ?? 0}</p></div>
        <div className="bg-white dark:bg-gray-900 p-5 rounded-2xl border border-gray-200"><div className="flex items-center gap-2 text-sm text-gray-500 mb-1"><HardDrive className="w-4 h-4"/>文件备份</div><p className="text-2xl font-bold">{stats?.files_count ?? backups?.filter((b:any) => b.type === 'files').length ?? 0}</p></div>
        <div className="bg-white dark:bg-gray-900 p-5 rounded-2xl border border-gray-200"><div className="flex items-center gap-2 text-sm text-gray-500 mb-1"><HardDrive className="w-4 h-4"/>完整备份</div><p className="text-2xl font-bold">{stats?.full_count ?? 0}</p></div>
        <div className="bg-white dark:bg-gray-900 p-5 rounded-2xl border border-gray-200"><div className="flex items-center gap-2 text-sm text-gray-500 mb-1"><Database className="w-4 h-4"/>总大小</div><p className="text-2xl font-bold">{stats?.total_size || '—'}</p></div>
      </div>

      {/* Actions */}
      <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 p-5 mb-6">
        <h3 className="font-semibold text-gray-900 dark:text-white mb-4">创建备份</h3>
        <div className="flex flex-wrap gap-3">
          {['database','files','full'].map(t => (
            <button key={t} onClick={() => createMut.mutate(t)} disabled={createMut.isPending}
              className="px-4 py-2.5 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-xl disabled:opacity-50 flex items-center gap-2">
              <Download className="w-4 h-4"/>{t === 'database' ? '数据库' : t === 'files' ? '文件' : '完整备份'}
            </button>
          ))}
          <button onClick={() => delMut.mutate()} className="px-4 py-2.5 border border-red-200 text-red-600 text-sm font-medium rounded-xl hover:bg-red-50 flex items-center gap-2"><Trash2 className="w-4 h-4"/>清理旧备份</button>
        </div>
      </div>

      {/* List */}
      <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 overflow-hidden">
        {isLoading ? (
          <div className="p-12 text-center"><div className="animate-spin w-6 h-6 border-2 border-blue-600 border-t-transparent rounded-full mx-auto"/></div>
        ) : !backups?.length ? (
          <div className="p-12 text-center text-gray-400"><Database className="w-10 h-10 mx-auto mb-3 opacity-50"/><p>暂无备份</p></div>
        ) : (
          <table className="w-full"><thead className="bg-gray-50 dark:bg-gray-800 border-b">
            <tr><th className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase">类型</th><th className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase hidden sm:table-cell">时间</th><th className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase hidden md:table-cell">大小</th><th className="px-5 py-3 text-right text-xs font-semibold text-gray-500 uppercase">操作</th></tr>
          </thead><tbody className="divide-y">
            {backups.map((b: any, i: number) => (
              <tr key={i} className="hover:bg-gray-50 dark:hover:bg-gray-800/50">
                <td className="px-5 py-4"><span className="px-2 py-0.5 text-xs rounded-full bg-blue-100 text-blue-700">{b.type || b.backup_type || 'database'}</span></td>
                <td className="px-5 py-4 text-sm text-gray-500 hidden sm:table-cell">{b.created_at ? new Date(b.created_at).toLocaleString('zh-CN') : '-'}</td>
                <td className="px-5 py-4 text-sm text-gray-500 hidden md:table-cell">{b.file_size || b.size || '-'}</td>
                <td className="px-5 py-4 text-right"><button className="p-1.5 text-gray-400 hover:text-red-600"><Trash2 className="w-4 h-4"/></button></td>
              </tr>
            ))}
          </tbody></table>
        )}
      </div>
    </AdminShell>
  );
}

export default function AdminBackup() {
  return <AuthGuard><QueryProvider><BackupInner /></QueryProvider></AuthGuard>;
}
