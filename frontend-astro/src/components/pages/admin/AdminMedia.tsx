'use client';

import React, {useState} from 'react';
import {AuthGuard} from '@/components/AuthGuard';
import {QueryProvider} from '@/components/QueryProvider';
import {AdminShell} from '@/components/admin/AdminShell';
import {PermissionGuard} from '@/components/admin/PermissionGuard';
import {Upload} from 'lucide-react';
import {FilesTab} from './media/FilesTab';
import {UploadTasksTab} from './media/UploadTasksTab';
import {DownloadTasksTab} from './media/DownloadTasksTab';
import {TABS, type TabKey} from './media/MediaTypes';

/* ═══════════════════════════════════════════════════════════════════
   ── 主组件 ──
   ═══════════════════════════════════════════════════════════════════ */
function AdminMediaInner() {
  const [tab, setTab] = useState<TabKey>('files');

  return (
    <AdminShell title="媒体库" actions={
      <button
        className="flex items-center gap-1.5 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg transition-colors shadow-sm">
        <Upload className="w-4 h-4"/>上传文件
      </button>
    }>
      {/* Tab 导航 */}
      <div className="flex gap-1 bg-gray-100 dark:bg-gray-800 rounded-xl p-1 mb-6">
        {TABS.map(t => (
          <button key={t.key} onClick={() => setTab(t.key)}
                  className={`flex-1 flex items-center justify-center gap-1.5 px-4 py-2.5 text-sm rounded-lg transition-colors ${
                    tab === t.key
                      ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm font-medium'
                      : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
                  }`}>
            <t.icon className="w-4 h-4"/>
            {t.label}
          </button>
        ))}
      </div>

      {/* Tab 内容 */}
      {tab === 'files' && <FilesTab/>}
      {tab === 'upload-tasks' && <UploadTasksTab/>}
      {tab === 'download-tasks' && <DownloadTasksTab/>}
    </AdminShell>
  );
}

export default function AdminMedia() {
  return <AuthGuard><QueryProvider><PermissionGuard capability="media:view"><AdminMediaInner/></PermissionGuard></QueryProvider></AuthGuard>;
}
