'use client';

import React, {useState} from 'react';
import {useMutation, useQuery, useQueryClient} from '@tanstack/react-query';
import {AuthGuard} from '@/components/AuthGuard';
import {QueryProvider} from '@/components/QueryProvider';
import {AdminShell} from '@/components/admin/AdminShell';
import {apiClient} from '@/lib/api/base-client';
import {useToast} from '@/components/ui/toast-provider';
import {
  RefreshCw, Trash2, Activity, Database, Server, Zap,
  ChevronDown, ChevronUp, CheckCircle2, Loader, AlertTriangle,
} from 'lucide-react';

function CacheInner() {
  const toast = useToast();
  const qc = useQueryClient();
  const [purging, setPurging] = useState(false);
  const [warming, setWarming] = useState(false);

  const {data: stats, isLoading} = useQuery({
    queryKey: ['admin-cache-stats'],
    queryFn: async () => {
      const r = await apiClient.get('/admin/caches/stats');
      return r.data || {};
    },
  });

  const purgeMut = useMutation({
    mutationFn: () => apiClient.post('/admin/caches/purge'),
    onSuccess: (r) => {
      if (r.success) { toast.success('缓存已清空'); qc.invalidateQueries({queryKey: ['admin-cache-stats']}); }
      else toast.error(r.error || '清空失败');
    },
    onError: () => toast.error('清空失败'),
  });

  const warmupMut = useMutation({
    mutationFn: () => apiClient.post('/admin/caches/warmup'),
    onSuccess: (r) => {
      if (r.success) toast.success('缓存预热已触发');
      else toast.error(r.error || '预热失败');
    },
    onError: () => toast.error('预热失败'),
  });

  return (
    <AdminShell title="缓存管理" actions={
      <div className="flex gap-2">
        <button onClick={() => warmupMut.mutate()}
                className="inline-flex items-center gap-1.5 px-4 py-2 bg-gradient-to-r from-emerald-600 to-emerald-700 text-white text-sm font-medium rounded-xl hover:from-emerald-700 hover:to-emerald-800 transition-all shadow-lg shadow-emerald-500/25">
          <Zap className="w-4 h-4"/>预热缓存
        </button>
        <button onClick={() => purgeMut.mutate()}
                className="inline-flex items-center gap-1.5 px-4 py-2 bg-gradient-to-r from-red-600 to-red-700 text-white text-sm font-medium rounded-xl hover:from-red-700 hover:to-red-800 transition-all shadow-lg shadow-red-500/25">
          <Trash2 className="w-4 h-4"/>清空全部
        </button>
      </div>
    }>
      {/* Cache Overview */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
        <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 p-5">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-10 h-10 bg-blue-100 dark:bg-blue-900/30 rounded-xl flex items-center justify-center">
              <Activity className="w-5 h-5 text-blue-600 dark:text-blue-400"/>
            </div>
            <div>
              <p className="text-xs text-gray-500 dark:text-gray-400">缓存状态</p>
              <p className="text-lg font-bold text-gray-900 dark:text-white">{stats?.status || '检查中...'}</p>
            </div>
          </div>
        </div>
        <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 p-5">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-10 h-10 bg-purple-100 dark:bg-purple-900/30 rounded-xl flex items-center justify-center">
              <Server className="w-5 h-5 text-purple-600 dark:text-purple-400"/>
            </div>
            <div>
              <p className="text-xs text-gray-500 dark:text-gray-400">缓存层数</p>
              <p className="text-lg font-bold text-gray-900 dark:text-white">{(stats?.layers?.length) || '—'}</p>
            </div>
          </div>
        </div>
        <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 p-5">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-10 h-10 bg-amber-100 dark:bg-amber-900/30 rounded-xl flex items-center justify-center">
              <Database className="w-5 h-5 text-amber-600 dark:text-amber-400"/>
            </div>
            <div>
              <p className="text-xs text-gray-500 dark:text-gray-400">缓存驱动</p>
              <p className="text-lg font-bold text-gray-900 dark:text-white font-mono text-sm">{stats?.cache_service || '—'}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Cache Layers */}
      <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-100 dark:border-gray-800">
          <h3 className="font-semibold text-gray-900 dark:text-white">缓存层级</h3>
        </div>
        <div className="p-6">
          {isLoading ? (
            <div className="space-y-3">
              {[1,2,3].map(i => <div key={i} className="h-14 bg-gray-100 dark:bg-gray-800 rounded-xl animate-pulse"/>)}
            </div>
          ) : (
            <div className="space-y-3">
              {(stats?.layers || ['memory', 'file', 'redis']).map((layer: string) => (
                <div key={layer}
                     className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-800/50 rounded-xl">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-lg bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center">
                      {layer === 'memory' ? <Zap className="w-4 h-4 text-blue-600"/> :
                       layer === 'redis' ? <Server className="w-4 h-4 text-red-600"/> :
                       <Database className="w-4 h-4 text-amber-600"/>}
                    </div>
                    <div>
                      <p className="text-sm font-medium text-gray-800 dark:text-gray-200 capitalize">{layer}</p>
                      <p className="text-[10px] text-gray-400">{layer === 'memory' ? '内存缓存，最快' : layer === 'redis' ? 'Redis 分布式缓存' : '文件缓存，持久化'}</p>
                    </div>
                  </div>
                  <span className="px-2.5 py-1 bg-green-100 dark:bg-green-900/30 text-green-600 dark:text-green-400 rounded-full text-[10px] font-medium">在线</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </AdminShell>
  );
}

export default function AdminCache() {
  return (
    <AuthGuard>
      <QueryProvider>
        <CacheInner/>
      </QueryProvider>
    </AuthGuard>
  );
}
