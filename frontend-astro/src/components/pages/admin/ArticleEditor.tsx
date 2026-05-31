'use client';

import React, {useState} from 'react';
import {useQuery, useMutation} from '@tanstack/react-query';
import {AuthGuard} from '@/components/AuthGuard';
import {QueryProvider} from '@/components/QueryProvider';
import {AdminShell} from '@/components/admin/AdminShell';
import {apiClient} from '@/lib/api/base-client';
import {Save} from 'lucide-react';
import {useToast} from '@/components/ui/toast-provider';

const RichEditor = React.lazy(() => import('@/components/editor/RichEditor'));

function EditorInner() {
  const toast = useToast();
  const [content, setContent] = useState('');

  const submitMut = useMutation({
    mutationFn: async () => {
      const fd = new FormData();
      fd.append('title', 'New Article');
      fd.append('content', content);
      return apiClient.request('/articles', {method: 'POST', body: fd});
    },
    onSuccess: (res) => {
      if (res.success) toast.success('文章已创建');
    },
  });

  return (
    <AdminShell title="写文章" actions={
      <button onClick={() => submitMut.mutate()} disabled={submitMut.isPending} className="px-4 py-1.5 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg flex items-center gap-1.5"><Save className="w-4 h-4"/>{submitMut.isPending ? '发布中...' : '发布'}</button>
    }>
      <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 overflow-hidden">
        <React.Suspense fallback={<div className="h-[60vh] animate-pulse bg-gray-50 dark:bg-gray-800"/>}>
          <RichEditor value={content} onChange={setContent} />
        </React.Suspense>
      </div>
    </AdminShell>
  );
}

export default function ArticleEditor() {
  return <AuthGuard><QueryProvider><EditorInner /></QueryProvider></AuthGuard>;
}
