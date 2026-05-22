'use client';

import React, {useState, useRef, useEffect} from 'react';
import {useQuery} from '@tanstack/react-query';
import {AuthGuard} from '@/components/AuthGuard';
import {QueryProvider} from '@/components/QueryProvider';
import {AdminShell} from '@/components/admin/AdminShell';
import {apiClient} from '@/lib/api/base-client';
import {
  ChevronLeft,
  ChevronRight,
  FileText,
  Image,
  Music,
  Search,
  Trash2,
  Video,
  X
} from 'lucide-react';
import {getConfig} from '@/lib/config';

const getFullMediaUrl = (url: string | null | undefined): string => {
    if (!url) return '';
    if (url.startsWith('http://') || url.startsWith('https://')) return url;
    const config = getConfig();
    return `${config.API_BASE_URL}${url}`;
};

// 防抖 hook
function useDebounce<T>(value: T, delay: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);
  return debounced;
}

const TYPE_OPTIONS = [
  {value: '', label: '全部'},
  {value: 'images', label: '图片'},
  {value: 'videos', label: '视频'},
  {value: 'documents', label: '文档'},
  {value: 'audio', label: '音频'},
] as const;

const SORT_OPTIONS = [
  {value: 'time', label: '时间'},
  {value: 'name', label: '名称'},
] as const;

function AdminMediaInner() {
  const [page, setPage] = useState(1);
  const [fileType, setFileType] = useState('');
  const [sortBy, setSortBy] = useState('time');
  const [sortOrder, setSortOrder] = useState('desc');
  const [searchInput, setSearchInput] = useState('');
  const debouncedSearch = useDebounce(searchInput, 400);

  // 重置到第一页当筛选条件改变
  const prevFilters = useRef('');
  useEffect(() => {
    const filters = `${fileType}-${sortBy}-${sortOrder}-${debouncedSearch}`;
    if (prevFilters.current && prevFilters.current !== filters) {
      setPage(1);
    }
    prevFilters.current = filters;
  }, [fileType, sortBy, sortOrder, debouncedSearch]);

  const {data, isLoading} = useQuery({
    queryKey: ['admin-media', page, fileType, sortBy, sortOrder, debouncedSearch],
    queryFn: async () => {
      const params: Record<string, any> = {page, per_page: 20};
      if (fileType) params.type = fileType;
      if (sortBy) params.sort = sortBy;
      if (sortOrder) params.order = sortOrder;
      if (debouncedSearch) params.q = debouncedSearch;

      const res = await apiClient.get<any>('/api/v2/dashboard/media-management/files', params);
      if (!res.success || !res.data) return {files: [], total: 0, totalPages: 1};

      const files = Array.isArray(res.data.files) ? res.data.files :
          Array.isArray(res.data.media_items) ? res.data.media_items :
              Array.isArray(res.data) ? res.data : [];
      const pagination = res.pagination || {};
      const total = pagination.total || files.length;
      const totalPages = pagination.total_pages || Math.ceil(total / 20) || 1;

      return {files, total, totalPages};
    },
  });
  const files = data?.files || [];
  const totalPages = data?.totalPages || 1;
  const total = data?.total || 0;

  const toggleSortOrder = () => {
    setSortOrder(o => o === 'asc' ? 'desc' : 'asc');
  };

  const getIcon = (mime: string) =>
      mime?.startsWith('video/') ? Video : mime?.startsWith('audio/') ? Music : FileText;

  // 分页按钮渲染
  const renderPagination = () => {
    if (totalPages <= 1) return null;
    const pages: (number | string)[] = [];
    const delta = 2;
    const left = Math.max(2, page - delta);
    const right = Math.min(totalPages - 1, page + delta);

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
              p === '...' ? (
                  <span key={`ellipsis-${i}`} className="px-2 text-gray-400">…</span>
              ) : (
                  <button key={p} onClick={() => setPage(p as number)}
                          className={`min-w-[36px] h-9 rounded-lg text-sm font-medium transition-colors ${
                              p === page
                                  ? 'bg-blue-600 text-white'
                                  : 'border border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800'
                          }`}>{p}</button>
              )
          )}
          <button disabled={page >= totalPages} onClick={() => setPage(p => p + 1)}
                  className="p-2 rounded-lg border border-gray-200 dark:border-gray-700 disabled:opacity-30 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors">
            <ChevronRight className="w-4 h-4"/>
          </button>
        </div>
    );
  };

  return (
      <AdminShell title="媒体库">
        {/* 筛选栏 */}
        <div className="flex flex-wrap items-center gap-3 mb-4">
          {/* 搜索框（防抖） */}
          <div className="relative flex-1 min-w-[200px]">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400"/>
            <input type="text" value={searchInput} onChange={e => setSearchInput(e.target.value)}
                   placeholder="搜索文件名..."
                   className="w-full pl-9 pr-8 py-2 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white"/>
            {searchInput && (
                <button onClick={() => setSearchInput('')}
                        className="absolute right-2 top-1/2 -translate-y-1/2 p-0.5 text-gray-400 hover:text-gray-600">
                  <X className="w-4 h-4"/>
                </button>
            )}
          </div>

          {/* 类型筛选 */}
          <div className="flex gap-1 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-xl p-1">
            {TYPE_OPTIONS.map(opt => (
                <button key={opt.value} onClick={() => setFileType(opt.value)}
                        className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                            fileType === opt.value
                                ? 'bg-blue-600 text-white'
                                : 'text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800'
                        }`}>{opt.label}</button>
            ))}
          </div>

          {/* 排序 */}
          <div className="flex gap-1 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-xl p-1">
            {SORT_OPTIONS.map(opt => (
                <button key={opt.value} onClick={() => { setSortBy(opt.value); setSortOrder('desc'); }}
                        className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                            sortBy === opt.value
                                ? 'bg-gray-200 dark:bg-gray-700 text-gray-900 dark:text-white'
                                : 'text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800'
                        }`}>{opt.label}</button>
            ))}
            <button onClick={toggleSortOrder}
                    className="px-2 py-1.5 rounded-lg text-xs text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors">
              {sortOrder === 'asc' ? '↑' : '↓'}
            </button>
          </div>

          {/* 统计 */}
          <span className="text-xs text-gray-400 ml-auto">
            共 {total} 个文件
          </span>
        </div>

        {/* 文件列表 */}
        <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 overflow-hidden">
          {isLoading ? (
              <div className="p-12 text-center">
                <div className="animate-spin w-6 h-6 border-2 border-blue-600 border-t-transparent rounded-full mx-auto"/>
              </div>
          ) : !files.length ? (
              <div className="p-12 text-center text-gray-400">
                {debouncedSearch ? '未找到匹配的文件' : '暂无媒体文件'}
              </div>
          ) : (
              <table className="w-full">
                <thead className="bg-gray-50 dark:bg-gray-800 border-b">
                <tr>
                  <th className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase">文件</th>
                  <th className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase hidden sm:table-cell">类型</th>
                  <th className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase hidden md:table-cell">大小</th>
                  <th className="px-5 py-3 text-right text-xs font-semibold text-gray-500 uppercase">操作</th>
                </tr>
                </thead>
                <tbody className="divide-y">
                {files.map((f: any) => {
                  const Icon = f.mime_type?.startsWith('image/') ? Image : getIcon(f.mime_type || '');
                  return (
                      <tr key={f.id} className="hover:bg-gray-50 dark:hover:bg-gray-800/50">
                        <td className="px-5 py-3">
                          <div className="flex items-center gap-3">
                            {f.mime_type?.startsWith('image/') && f.url ?
                                <img src={getFullMediaUrl(f.url)} alt={f.original_filename}
                                     className="w-10 h-10 rounded-lg object-cover"/> :
                                <div
                                    className="w-10 h-10 rounded-lg bg-gray-100 dark:bg-gray-800 flex items-center justify-center">
                                  <Icon className="w-5 h-5 text-gray-400"/></div>}
                            <span
                                className="text-sm font-medium text-gray-900 dark:text-white truncate max-w-[200px]">{f.original_filename}</span>
                          </div>
                        </td>
                        <td className="px-5 py-4 text-sm text-gray-500 hidden sm:table-cell">{f.mime_type?.split('/')[0] || '-'}</td>
                        <td className="px-5 py-4 text-sm text-gray-500 hidden md:table-cell">{f.file_size ? `${(f.file_size / 1024).toFixed(1)} KB` : '-'}</td>
                        <td className="px-5 py-4 text-right">
                          <button className="p-1.5 inline-block text-gray-400 hover:text-red-600">
                            <Trash2 className="w-4 h-4"/>
                          </button>
                        </td>
                      </tr>
                  );
                })}
                </tbody>
              </table>
          )}
        </div>

        {/* 分页 */}
        {renderPagination()}
      </AdminShell>
  );
}

export default function AdminMedia() {
  return <AuthGuard><QueryProvider><AdminMediaInner/></QueryProvider></AuthGuard>;
}
