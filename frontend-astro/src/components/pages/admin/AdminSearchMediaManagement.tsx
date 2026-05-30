'use client';

import React, {useState} from 'react';
import {useMutation, useQuery, useQueryClient} from '@tanstack/react-query';
import {AuthGuard} from '@/components/AuthGuard';
import {QueryProvider} from '@/components/QueryProvider';
import {AdminShell} from '@/components/admin/AdminShell';
import {EmptyState, Modal} from '@/components/admin/shared-ui';
import {apiClient} from '@/lib/api/api-client';
import {
  CheckCircle,
  ChevronLeft,
  ChevronRight,
  Database,
  Edit3,
  Plus,
  RefreshCw,
  Search,
  Trash2,
  XCircle,
  Zap
} from 'lucide-react';

/* ─── Types ─────────────────────────────────────── */
interface SearchIndex {
  id: number;
  article_id: number;
  indexed: boolean;
  last_indexed_at?: string;
  index_hash?: string;
  created_at?: string;
  updated_at?: string;
}

interface MediaOptimization {
  id: number;
  media_id: number;
  webp_url?: string;
  sizes_json?: string;
  cdn_url?: string;
  optimization_status: string;
  created_at?: string;
  updated_at?: string;
}

interface Pagination {
  page: number;
  per_page: number;
  total: number;
  total_pages: number;
}

/* ─── Search Index Tab ─────────────────────────── */
const SearchIndexTab: React.FC = () => {
  const qc = useQueryClient();
  const [page, setPage] = useState(1);
  const [indexedFilter, setIndexedFilter] = useState('');
  const [reindexArticleId, setReindexArticleId] = useState('');

  const {data, isLoading} = useQuery({
    queryKey: ['search-index', page, indexedFilter],
    queryFn: () => apiClient.get('/search/management/search-index', {
      page, per_page: 15,
      indexed: indexedFilter !== '' ? indexedFilter === 'true' : undefined,
    }),
  });
  const items: SearchIndex[] = data?.data?.search_indexes || [];
  const pagination: Pagination | undefined = data?.data?.pagination;

  const createMut = useMutation({
    mutationFn: (d: any) => apiClient.post('/search/management/search-index', d),
    onSuccess: (r: any) => {
      if (r.success) qc.invalidateQueries({queryKey: ['search-index']}); else alert(r.error);
    },
  });
  const updateMut = useMutation({
    mutationFn: ({id, ...d}: any) => apiClient.put(`/search/management/search-index/${id}`, d),
    onSuccess: () => qc.invalidateQueries({queryKey: ['search-index']}),
  });
  const deleteMut = useMutation({
    mutationFn: (id: number) => apiClient.delete(`/search/management/search-index/${id}`),
    onSuccess: () => qc.invalidateQueries({queryKey: ['search-index']}),
  });
  const batchReindexMut = useMutation({
    mutationFn: (articleIds?: number[]) => apiClient.post('/search/management/search-index/batch-reindex', {article_ids: articleIds}),
    onSuccess: (r: any) => {
      if (r.success) {
        qc.invalidateQueries({queryKey: ['search-index']});
        alert(r.message || '重新索引已触发');
      } else alert(r.error);
    },
  });

  return (
    <>
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <select value={indexedFilter} onChange={e => {
            setIndexedFilter(e.target.value);
            setPage(1);
          }}
                  className="px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white">
            <option value="">全部状态</option>
            <option value="true">已索引</option>
            <option value="false">未索引</option>
          </select>
          <div className="flex items-center gap-1">
            <input value={reindexArticleId} onChange={e => setReindexArticleId(e.target.value)}
                   placeholder="文章ID" type="number"
                   className="px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white w-28"/>
            <button onClick={() => {
              const ids = reindexArticleId ? [parseInt(reindexArticleId)] : undefined;
              batchReindexMut.mutate(ids);
            }} disabled={batchReindexMut.isPending}
                    className="px-3 py-2 bg-yellow-500 hover:bg-yellow-600 text-white text-sm rounded-lg flex items-center gap-1 disabled:opacity-50">
              <RefreshCw className={`w-4 h-4 ${batchReindexMut.isPending ? 'animate-spin' : ''}`}/>重建索引
            </button>
          </div>
        </div>
        <button onClick={() => {
          const id = prompt('输入文章ID:');
          if (id) createMut.mutate({article_id: parseInt(id)});
        }} className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded-xl flex items-center gap-1.5">
          <Plus className="w-4 h-4"/>添加索引
        </button>
      </div>
      {isLoading ? <div className="animate-pulse space-y-2">{[1, 2, 3].map(i => <div key={i}
                                                                                     className="h-14 bg-gray-100 dark:bg-gray-800 rounded-xl"/>)}</div> :
        items.length === 0 ? <EmptyState icon={Search} title="暂无搜索索引" desc="文章索引状态将在此显示"/> :
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
              <tr className="border-b border-gray-100 dark:border-gray-800">
                <th className="text-left py-3 px-4 text-xs font-semibold text-gray-500">ID</th>
                <th className="text-left py-3 px-4 text-xs font-semibold text-gray-500">文章ID</th>
                <th className="text-left py-3 px-4 text-xs font-semibold text-gray-500">索引状态</th>
                <th className="text-left py-3 px-4 text-xs font-semibold text-gray-500">索引哈希</th>
                <th className="text-left py-3 px-4 text-xs font-semibold text-gray-500">最后索引时间</th>
                <th className="text-right py-3 px-4 text-xs font-semibold text-gray-500">操作</th>
              </tr>
              </thead>
              <tbody>{items.map(s => (
                <tr key={s.id}
                    className="border-b border-gray-50 dark:border-gray-800/50 hover:bg-gray-50 dark:hover:bg-gray-800/30">
                  <td className="py-3 px-4 font-mono text-xs">#{s.id}</td>
                  <td className="py-3 px-4 font-medium text-gray-900 dark:text-white">文章#{s.article_id}</td>
                  <td className="py-3 px-4">
                 <span
                   className={`flex items-center gap-1 text-xs ${s.indexed ? 'text-green-600 dark:text-green-400' : 'text-gray-400'}`}>
                   {s.indexed ? <CheckCircle className="w-3.5 h-3.5"/> : <XCircle className="w-3.5 h-3.5"/>}
                   {s.indexed ? '已索引' : '未索引'}
                 </span>
                  </td>
                  <td
                    className="py-3 px-4 text-xs font-mono text-gray-500">{s.index_hash ? s.index_hash.substring(0, 12) + '...' : '—'}</td>
                  <td
                    className="py-3 px-4 text-xs text-gray-500">{s.last_indexed_at ? new Date(s.last_indexed_at).toLocaleString('zh-CN') : '—'}</td>
                  <td className="py-3 px-4 text-right">
                    <button onClick={() => updateMut.mutate({id: s.id, indexed: !s.indexed})}
                            className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-500 mr-1"
                            title="切换索引状态">
                      <RefreshCw className="w-3.5 h-3.5"/>
                    </button>
                    <button onClick={() => {
                      if (confirm('确定删除？')) deleteMut.mutate(s.id);
                    }}
                            className="p-1.5 rounded-lg hover:bg-red-50 dark:hover:bg-red-900/20 text-red-500"><Trash2
                      className="w-3.5 h-3.5"/></button>
                  </td>
                </tr>
              ))}</tbody>
            </table>
          </div>}
      {pagination && pagination.total_pages > 1 && (
        <div className="flex items-center justify-between mt-4">
          <span className="text-xs text-gray-500">共 {pagination.total} 条</span>
          <div className="flex items-center gap-1">
            <button disabled={page <= 1} onClick={() => setPage(p => p - 1)}
                    className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 disabled:opacity-30">
              <ChevronLeft className="w-4 h-4"/></button>
            <span className="text-xs text-gray-600 dark:text-gray-400 px-2">{page}/{pagination.total_pages}</span>
            <button disabled={page >= pagination.total_pages} onClick={() => setPage(p => p + 1)}
                    className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 disabled:opacity-30">
              <ChevronRight className="w-4 h-4"/></button>
          </div>
        </div>
      )}
    </>
  );
};

/* ─── Media Optimization Tab ───────────────────── */
const MediaOptimizationTab: React.FC = () => {
  const qc = useQueryClient();
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({media_id: '', webp_url: '', cdn_url: '', optimization_status: 'pending'});

  const {data, isLoading} = useQuery({
    queryKey: ['media-optimization', page, statusFilter],
    queryFn: () => apiClient.get('/search/management/media-optimization', {
      page,
      per_page: 15,
      status: statusFilter || undefined
    }),
  });
  const items: MediaOptimization[] = data?.data?.media_optimizations || [];
  const pagination: Pagination | undefined = data?.data?.pagination;

  const createMut = useMutation({
    mutationFn: (d: any) => apiClient.post('/search/management/media-optimization', d),
    onSuccess: (r: any) => {
      if (r.success) {
        qc.invalidateQueries({queryKey: ['media-optimization']});
        setShowForm(false);
      } else alert(r.error);
    },
  });
  const updateMut = useMutation({
    mutationFn: ({id, ...d}: any) => apiClient.put(`/search/management/media-optimization/${id}`, d),
    onSuccess: () => qc.invalidateQueries({queryKey: ['media-optimization']}),
  });
  const deleteMut = useMutation({
    mutationFn: (id: number) => apiClient.delete(`/search/management/media-optimization/${id}`),
    onSuccess: () => qc.invalidateQueries({queryKey: ['media-optimization']}),
  });

  const submit = () => {
    if (!form.media_id) return alert('请填写媒体ID');
    createMut.mutate({...form, media_id: parseInt(form.media_id)});
  };

  const statusColors: Record<string, string> = {
    completed: 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400',
    processing: 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400',
    pending: 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-400',
    failed: 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400',
  };
  const statusLabels: Record<string, string> = {
    completed: '已完成', processing: '处理中', pending: '等待中', failed: '失败',
  };

  return (
    <>
      <div className="flex items-center justify-between mb-4">
        <select value={statusFilter} onChange={e => {
          setStatusFilter(e.target.value);
          setPage(1);
        }}
                className="px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white">
          <option value="">全部状态</option>
          <option value="pending">等待中</option>
          <option value="processing">处理中</option>
          <option value="completed">已完成</option>
          <option value="failed">失败</option>
        </select>
        <button onClick={() => {
          setForm({media_id: '', webp_url: '', cdn_url: '', optimization_status: 'pending'});
          setShowForm(true);
        }}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded-xl flex items-center gap-1.5">
          <Plus className="w-4 h-4"/>新建优化记录
        </button>
      </div>
      {isLoading ? <div className="animate-pulse space-y-2">{[1, 2, 3].map(i => <div key={i}
                                                                                     className="h-14 bg-gray-100 dark:bg-gray-800 rounded-xl"/>)}</div> :
        items.length === 0 ? <EmptyState icon={Zap} title="暂无媒体优化记录" desc="媒体优化配置将在此显示"/> :
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
              <tr className="border-b border-gray-100 dark:border-gray-800">
                <th className="text-left py-3 px-4 text-xs font-semibold text-gray-500">ID</th>
                <th className="text-left py-3 px-4 text-xs font-semibold text-gray-500">媒体ID</th>
                <th className="text-left py-3 px-4 text-xs font-semibold text-gray-500">WebP URL</th>
                <th className="text-left py-3 px-4 text-xs font-semibold text-gray-500">CDN URL</th>
                <th className="text-left py-3 px-4 text-xs font-semibold text-gray-500">状态</th>
                <th className="text-left py-3 px-4 text-xs font-semibold text-gray-500">多尺寸</th>
                <th className="text-right py-3 px-4 text-xs font-semibold text-gray-500">操作</th>
              </tr>
              </thead>
              <tbody>{items.map(m => (
                <tr key={m.id}
                    className="border-b border-gray-50 dark:border-gray-800/50 hover:bg-gray-50 dark:hover:bg-gray-800/30">
                  <td className="py-3 px-4 font-mono text-xs">#{m.id}</td>
                  <td className="py-3 px-4 font-medium text-gray-900 dark:text-white">媒体#{m.media_id}</td>
                  <td className="py-3 px-4 text-xs">
                    {m.webp_url ? <a href={m.webp_url} target="_blank" rel="noopener"
                                     className="text-blue-500 hover:underline truncate max-w-[120px] inline-block">查看</a> : '—'}
                  </td>
                  <td className="py-3 px-4 text-xs">
                    {m.cdn_url ? <a href={m.cdn_url} target="_blank" rel="noopener"
                                    className="text-blue-500 hover:underline truncate max-w-[120px] inline-block">查看</a> : '—'}
                  </td>
                  <td className="py-3 px-4">
                 <span
                   className={`px-2 py-0.5 text-[10px] rounded-full font-medium ${statusColors[m.optimization_status] || 'bg-gray-100 text-gray-500'}`}>
                   {statusLabels[m.optimization_status] || m.optimization_status}
                 </span>
                  </td>
                  <td className="py-3 px-4 text-xs text-gray-500">{m.sizes_json ? '有' : '—'}</td>
                  <td className="py-3 px-4 text-right">
                    <button onClick={() => {
                      const url = prompt('WebP URL:', m.webp_url || '');
                      if (url !== null) updateMut.mutate({id: m.id, webp_url: url});
                    }} className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-500 mr-1"><Edit3
                      className="w-3.5 h-3.5"/></button>
                    <button onClick={() => {
                      if (confirm('确定删除？')) deleteMut.mutate(m.id);
                    }}
                            className="p-1.5 rounded-lg hover:bg-red-50 dark:hover:bg-red-900/20 text-red-500"><Trash2
                      className="w-3.5 h-3.5"/></button>
                  </td>
                </tr>
              ))}</tbody>
            </table>
          </div>}
      {pagination && pagination.total_pages > 1 && (
        <div className="flex items-center justify-between mt-4">
          <span className="text-xs text-gray-500">共 {pagination.total} 条</span>
          <div className="flex items-center gap-1">
            <button disabled={page <= 1} onClick={() => setPage(p => p - 1)}
                    className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 disabled:opacity-30">
              <ChevronLeft className="w-4 h-4"/></button>
            <span className="text-xs text-gray-600 dark:text-gray-400 px-2">{page}/{pagination.total_pages}</span>
            <button disabled={page >= pagination.total_pages} onClick={() => setPage(p => p + 1)}
                    className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 disabled:opacity-30">
              <ChevronRight className="w-4 h-4"/></button>
          </div>
        </div>
      )}
      <Modal open={showForm} onClose={() => setShowForm(false)} title="新建媒体优化记录">
        <div className="mb-3">
          <label className="block text-xs font-semibold text-gray-500 dark:text-gray-400 mb-1">媒体 ID *</label>
          <input type="number" value={form.media_id} onChange={e => setForm({...form, media_id: e.target.value})}
                 placeholder="媒体ID"
                 className="w-full px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white placeholder-gray-400"/>
        </div>
        <div className="mb-3">
          <label className="block text-xs font-semibold text-gray-500 dark:text-gray-400 mb-1">WebP URL</label>
          <input value={form.webp_url} onChange={e => setForm({...form, webp_url: e.target.value})}
                 placeholder="WebP 图片URL"
                 className="w-full px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white placeholder-gray-400"/>
        </div>
        <div className="mb-3">
          <label className="block text-xs font-semibold text-gray-500 dark:text-gray-400 mb-1">CDN URL</label>
          <input value={form.cdn_url} onChange={e => setForm({...form, cdn_url: e.target.value})} placeholder="CDN URL"
                 className="w-full px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white placeholder-gray-400"/>
        </div>
        <div className="flex justify-end gap-2 mt-4">
          <button onClick={() => setShowForm(false)}
                  className="px-4 py-2 text-sm border border-gray-200 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 text-gray-600 dark:text-gray-300">取消
          </button>
          <button onClick={submit}
                  className="px-4 py-2 text-sm bg-blue-600 hover:bg-blue-700 text-white rounded-lg">创建
          </button>
        </div>
      </Modal>
    </>
  );
};

/* ─── Main Component ───────────────────────────── */
type TabKey = 'search-index' | 'media-optimization';
const TABS: { key: TabKey; label: string; icon: any }[] = [
  {key: 'search-index', label: '搜索索引', icon: Search},
  {key: 'media-optimization', label: '媒体优化', icon: Zap},
];

function SearchMediaInner() {
  const [tab, setTab] = useState<TabKey>('search-index');

  return (
    <AdminShell title="搜索与媒体管理" actions={<Database className="w-5 h-5 text-blue-500"/>}>
      <div className="space-y-6">
        <div className="flex gap-1 bg-gray-100 dark:bg-gray-800 rounded-xl p-1">
          {TABS.map(t => (
            <button key={t.key} onClick={() => setTab(t.key)}
                    className={`flex-1 flex items-center justify-center gap-1.5 px-4 py-2.5 text-sm rounded-lg transition-colors ${tab === t.key ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm font-medium' : 'text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'}`}>
              <t.icon className="w-4 h-4"/>
              {t.label}
            </button>
          ))}
        </div>
        <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 p-5">
          {tab === 'search-index' && <SearchIndexTab/>}
          {tab === 'media-optimization' && <MediaOptimizationTab/>}
        </div>
      </div>
    </AdminShell>
  );
}

export default function AdminSearchMediaManagement() {
  return (
    <AuthGuard>
      <QueryProvider>
        <SearchMediaInner/>
      </QueryProvider>
    </AuthGuard>
  );
}
