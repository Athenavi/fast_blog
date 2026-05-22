'use client';

import React, {useState} from 'react';
import {useQuery} from '@tanstack/react-query';
import {AuthGuard} from '@/components/AuthGuard';
import {QueryProvider} from '@/components/QueryProvider';
import {AdminShell} from '@/components/admin/AdminShell';
import {apiClient} from '@/lib/api/base-client';
import {FileText, Image, Music, Trash2, Video} from 'lucide-react';
import {getConfig} from '@/lib/config';

// Helper function to build full media URL
const getFullMediaUrl = (url: string | null | undefined): string => {
    if (!url) return '';
    // If already absolute URL, return as is
    if (url.startsWith('http://') || url.startsWith('https://')) return url;
    // Otherwise, prepend API base URL
    const config = getConfig();
    return `${config.API_BASE_URL}${url}`;
};

function AdminMediaInner() {
  const [page, setPage] = useState(1);
  const {data, isLoading} = useQuery({
    queryKey: ['admin-media', page],
    queryFn: async () => {
      const res = await apiClient.get<any>('/api/v2/dashboard/media-management/files', {page, per_page: 20});
      if (!res.success || !res.data) return {files: [], total: 0};

      // 后端返回格式可能是 data.files 或 data.media_items
      const files = Array.isArray(res.data.files) ? res.data.files :
          Array.isArray(res.data.media_items) ? res.data.media_items :
              Array.isArray(res.data) ? res.data : [];
      const pagination = res.pagination || {};
      const total = pagination.total || files.length;

      return {files, total};
    },
  });
  const files = data?.files || [];

  const getIcon = (mime: string) => mime?.startsWith('video/') ? Video : mime?.startsWith('audio/') ? Music : FileText;

  return (
    <AdminShell title="媒体库">
      <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 overflow-hidden">
        {isLoading ? (
          <div className="p-12 text-center"><div className="animate-spin w-6 h-6 border-2 border-blue-600 border-t-transparent rounded-full mx-auto"/></div>
        ) : !files.length ? (
          <div className="p-12 text-center text-gray-400">暂无媒体文件</div>
        ) : (
          <table className="w-full"><thead className="bg-gray-50 dark:bg-gray-800 border-b">
            <tr><th className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase">文件</th><th className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase hidden sm:table-cell">类型</th><th className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase hidden md:table-cell">大小</th><th className="px-5 py-3 text-right text-xs font-semibold text-gray-500 uppercase">操作</th></tr>
          </thead><tbody className="divide-y">
            {files.map((f: any) => {
              const Icon = f.mime_type?.startsWith('image/') ? Image : getIcon(f.mime_type || '');
              return (
                <tr key={f.id} className="hover:bg-gray-50 dark:hover:bg-gray-800/50">
                  <td className="px-5 py-3">
                    <div className="flex items-center gap-3">
                        {f.mime_type?.startsWith('image/') && f.url ?
                            <img src={getFullMediaUrl(f.url)} alt={f.original_filename}
                                 className="w-10 h-10 rounded-lg object-cover"/> :
                        <div className="w-10 h-10 rounded-lg bg-gray-100 dark:bg-gray-800 flex items-center justify-center"><Icon className="w-5 h-5 text-gray-400"/></div>}
                      <span className="text-sm font-medium text-gray-900 dark:text-white truncate max-w-[200px]">{f.original_filename}</span>
                    </div>
                  </td>
                  <td className="px-5 py-4 text-sm text-gray-500 hidden sm:table-cell">{f.mime_type?.split('/')[0] || '-'}</td>
                  <td className="px-5 py-4 text-sm text-gray-500 hidden md:table-cell">{f.file_size ? `${(f.file_size/1024).toFixed(1)} KB` : '-'}</td>
                  <td className="px-5 py-4 text-right"><button className="p-1.5 inline-block text-gray-400 hover:text-red-600"><Trash2 className="w-4 h-4"/></button></td>
                </tr>
              );
            })}
          </tbody></table>
        )}
      </div>
    </AdminShell>
  );
}

export default function AdminMedia() {
  return <AuthGuard><QueryProvider><AdminMediaInner /></QueryProvider></AuthGuard>;
}
