'use client';

import React, {useState, useRef} from 'react';
import {useQuery, useMutation, useQueryClient} from '@tanstack/react-query';
import {AuthGuard} from '@/components/AuthGuard';
import {QueryProvider} from '@/components/QueryProvider';
import {AdminShell} from '@/components/admin/AdminShell';
import {apiClient} from '@/lib/api/base-client';
import {ChevronLeft, ChevronRight, Database, HardDrive, Download, Trash2, Loader, ShieldAlert} from 'lucide-react';

function formatSize(bytes: number | string | undefined | null): string {
  if (bytes == null) return '—';
  const n = typeof bytes === 'string' ? parseFloat(bytes) : bytes;
  if (isNaN(n) || n <= 0) return '—';
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  let i = 0;
  let size = n;
  while (size >= 1024 && i < units.length - 1) { size /= 1024; i++; }
  return `${size.toFixed(i === 0 ? 0 : 1)} ${units[i]}`;
}

const TYPE_OPTIONS = [
  {value: '', label: '全部'},
  {value: 'database', label: '数据库'},
  {value: 'files', label: '文件'},
  {value: 'full', label: '完整'},
] as const;

function BackupInner() {
  const qc = useQueryClient();
  const [page, setPage] = useState(1);
  const [typeFilter, setTypeFilter] = useState('');
  // 追踪正在进行的备份类型（防 concurrent backup）
  const [backingUp, setBackingUp] = useState<string | null>(null);
  const prevFilterRef = useRef('');
  const filterKey = `${typeFilter}`;
  if (prevFilterRef.current !== filterKey) {
    prevFilterRef.current = filterKey;
    if (page !== 1) setPage(1);
  }

  const {data, isLoading} = useQuery({
    queryKey: ['admin-backups', page, typeFilter],
    queryFn: async () => {
      const params: Record<string, any> = {page, per_page: 15};
      if (typeFilter) params.backup_type = typeFilter;
      const res = await apiClient.get<any>('/api/v2/system/backup/list', params);
      if (res.success && res.data) return res.data;
      return {backups: [], total: 0, page: 1, per_page: 15, total_pages: 1};
    },
  });

  const {data: stats, refetch: refetchStats} = useQuery({
    queryKey: ['admin-backup-stats'],
    queryFn: async () => {
      const res = await apiClient.get<any>('/api/v2/system/backup/stats');
      return res.success && res.data ? res.data : {};
    },
  });

  const backups = data?.backups || [];
  const total = data?.total || 0;
  const totalPages = data?.total_pages || 1;

  // 创建备份 — 同一时间只允许一种类型的备份
  const createMut = useMutation({
    mutationFn: async (type: string) => {
      setBackingUp(type);
      const res = await apiClient.post(`/api/v2/system/backup/${type}`);
      return {type, res};
    },
    onSuccess: ({type}) => {
      setBackingUp(null);
      qc.invalidateQueries({queryKey: ['admin-backups']});
      refetchStats();
    },
    onError: () => setBackingUp(null),
  });

  // 删除单个备份
  const delOneMut = useMutation({
    mutationFn: (filename: string) => apiClient.delete(`/api/v2/system/backup/${encodeURIComponent(filename)}`),
    onSuccess: () => {
      qc.invalidateQueries({queryKey: ['admin-backups']});
      refetchStats();
    },
  });

  // 清理旧备份
  const delMut = useMutation({
    mutationFn: () => apiClient.post('/api/v2/system/backup/cleanup'),
    onSuccess: () => {
      qc.invalidateQueries({queryKey: ['admin-backups']});
      refetchStats();
    },
  });

  const isBusy = backingUp !== null;

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
        <div className="flex items-center justify-center gap-1.5 mt-4">
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
      <AdminShell title="备份管理">
        {/* 统计卡片 */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          <div className="bg-white dark:bg-gray-900 p-5 rounded-2xl border border-gray-200">
            <div className="flex items-center gap-2 text-sm text-gray-500 mb-1"><Database className="w-4 h-4"/>数据库备份</div>
            <p className="text-2xl font-bold">{stats?.database_count ?? 0}</p></div>
          <div className="bg-white dark:bg-gray-900 p-5 rounded-2xl border border-gray-200">
            <div className="flex items-center gap-2 text-sm text-gray-500 mb-1"><HardDrive className="w-4 h-4"/>文件备份</div>
            <p className="text-2xl font-bold">{stats?.files_count ?? 0}</p></div>
          <div className="bg-white dark:bg-gray-900 p-5 rounded-2xl border border-gray-200">
            <div className="flex items-center gap-2 text-sm text-gray-500 mb-1"><HardDrive className="w-4 h-4"/>完整备份</div>
            <p className="text-2xl font-bold">{stats?.full_count ?? 0}</p></div>
          <div className="bg-white dark:bg-gray-900 p-5 rounded-2xl border border-gray-200">
            <div className="flex items-center gap-2 text-sm text-gray-500 mb-1"><Database className="w-4 h-4"/>总大小</div>
            <p className="text-2xl font-bold">{formatSize(stats?.total_size)}</p></div>
        </div>

        {/* 操作栏 + 筛选 */}
        <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 p-5 mb-6">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <h3 className="font-semibold text-gray-900 dark:text-white mb-3">创建备份</h3>
              <div className="flex flex-wrap gap-2">
                {(['database', 'files', 'full'] as const).map(t => (
                    <button key={t}
                            onClick={() => { if (!isBusy) createMut.mutate(t); }}
                            disabled={isBusy}
                            className={`px-4 py-2 rounded-xl text-sm font-medium transition-all flex items-center gap-2 ${
                                backingUp === t
                                    ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400 cursor-wait'
                                    : isBusy
                                        ? 'bg-gray-100 dark:bg-gray-800 text-gray-400 cursor-not-allowed'
                                        : 'bg-blue-600 hover:bg-blue-700 text-white'
                            }`}>
                      {backingUp === t
                          ? <><Loader className="w-4 h-4 animate-spin"/>备份中…</>
                          : <><Download className="w-4 h-4"/>{t === 'database' ? '数据库' : t === 'files' ? '文件' : '完整备份'}</>
                      }
                    </button>
                ))}
              </div>
            </div>
            <div className="flex items-center gap-3">
              <div className="flex gap-1 bg-gray-100 dark:bg-gray-800 rounded-xl p-1">
                {TYPE_OPTIONS.map(opt => (
                    <button key={opt.value} onClick={() => setTypeFilter(opt.value)}
                            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                                typeFilter === opt.value ? 'bg-white dark:bg-gray-700 shadow-sm text-gray-900 dark:text-white' : 'text-gray-500 dark:text-gray-400 hover:text-gray-700'
                            }`}>{opt.label}</button>
                ))}
              </div>
              <button onClick={() => delMut.mutate()}
                      className="px-3 py-1.5 border border-red-200 dark:border-red-800 text-red-600 dark:text-red-400 text-xs font-medium rounded-xl hover:bg-red-50 dark:hover:bg-red-900/20 flex items-center gap-1">
                <Trash2 className="w-3.5 h-3.5"/>清理旧备份
              </button>
            </div>
          </div>
        </div>

        {/* 列表 */}
        <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 overflow-hidden">
          {isLoading ? (
              <div className="p-12 text-center"><div className="animate-spin w-6 h-6 border-2 border-blue-600 border-t-transparent rounded-full mx-auto"/></div>
          ) : !backups.length ? (
              <div className="p-12 text-center text-gray-400"><Database className="w-10 h-10 mx-auto mb-3 opacity-50"/><p>暂无备份</p></div>
          ) : (
              <table className="w-full"><thead className="bg-gray-50 dark:bg-gray-800 border-b">
              <tr>
                <th className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase">类型</th>
                <th className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase hidden sm:table-cell">文件名</th>
                <th className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase hidden md:table-cell">时间</th>
                <th className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase">大小</th>
                <th className="px-5 py-3 text-right text-xs font-semibold text-gray-500 uppercase">操作</th>
              </tr>
              </thead><tbody className="divide-y">
              {backups.map((b: any, i: number) => {
                const filename = b.filename || b.path?.split('/').pop() || b.backup_dir?.split('/').pop() || '';
                const isFull = b.type === 'full';
                const downloadUrl = `/api/v2/system/backup/download/${encodeURIComponent(filename)}`;
                return (
                    <tr key={b.filename || i} className="hover:bg-gray-50 dark:hover:bg-gray-800/50">
                      <td className="px-5 py-4">
                        <span className={`px-2 py-0.5 text-xs rounded-full font-medium ${
                            b.type === 'database' ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400'
                                : b.type === 'files' ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400'
                                    : 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400'
                        }`}>
                          {b.type === 'database' ? '数据库' : b.type === 'files' ? '文件' : '完整'}
                        </span>
                      </td>
                      <td className="px-5 py-4 text-sm text-gray-700 dark:text-gray-300 hidden sm:table-cell max-w-[200px] truncate">{filename}</td>
                      <td className="px-5 py-4 text-sm text-gray-500 hidden md:table-cell">
                        {b.created_at ? new Date(b.created_at).toLocaleString('zh-CN') : '-'}
                      </td>
                      <td className="px-5 py-4 text-sm text-gray-500">
                        {isFull ? (b.database_backup?.size_human || b.files_backup?.size_human || '—') : formatSize(b.size)}
                      </td>
                      <td className="px-5 py-4 text-right">
                        <a href={downloadUrl}
                           className="p-1.5 inline-block text-gray-400 hover:text-blue-600 rounded-lg hover:bg-blue-50 dark:hover:bg-blue-900/20">
                          <Download className="w-4 h-4"/>
                        </a>
                        <button onClick={() => { if (confirm('确认删除此备份？')) delOneMut.mutate(filename); }}
                                className="p-1.5 inline-block text-gray-400 hover:text-red-600 rounded-lg hover:bg-red-50 dark:hover:bg-red-900/20">
                          <Trash2 className="w-4 h-4"/>
                        </button>
                      </td>
                    </tr>
                );
              })}
              </tbody></table>
          )}
        </div>

        {/* 分页 */}
        <div className="flex items-center justify-between mt-4">
          <span className="text-xs text-gray-400">共 {total} 个备份</span>
          {renderPagination()}
        </div>
      </AdminShell>
  );
}

export default function AdminBackup() {
  return <AuthGuard><QueryProvider><BackupInner/></QueryProvider></AuthGuard>;
}
