'use client';

import React from 'react';
import {useQuery} from '@tanstack/react-query';
import {AuthGuard} from '@/components/AuthGuard';
import {QueryProvider} from '@/components/QueryProvider';
import {AdminShell} from '@/components/admin/AdminShell';
import {apiClient} from '@/lib/api/base-client';
import {Code, FileText, Copy, CheckCircle2} from 'lucide-react';

function ShortcodesInner() {
  const [copied, setCopied] = React.useState<string | null>(null);

  const {data, isLoading} = useQuery({
    queryKey: ['shortcodes'],
    queryFn: async () => {
      const r = await apiClient.get('/cms/shortcodes/list');
      return (r.data?.shortcodes || r.data || []) as string[];
    },
  });
  const shortcodes = data || [];

  const copy = (name: string) => {
    navigator.clipboard.writeText(`[${name}]`);
    setCopied(name);
    setTimeout(() => setCopied(null), 1500);
  };

  const builtinHelp: Record<string, string> = {
    'code': '嵌入格式化代码块<br/>用法: [code language="python"]print("hello")[/code]',
    'gist': '嵌入 GitHub Gist<br/>用法: [gist id="abc123"]',
    'youtube': '嵌入 YouTube 视频<br/>用法: [youtube id="dQw4w9WgXcQ"]',
    'bilibili': '嵌入 Bilibili 视频<br/>用法: [bilibili id="BV1xx411c7mD"]',
    'note': '显示提示框<br/>用法: [note type="info|warning|tip"]内容[/note]',
    'tabs': '创建标签切换<br/>用法: [tabs][tab name="A"]内容A[/tab][tab name="B"]内容B[/tabs]',
  };

  return (
    <AdminShell title="短代码管理">
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Shortcode list */}
        <div className="lg:col-span-1">
          <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 overflow-hidden">
            <div className="px-5 py-4 border-b border-gray-100 dark:border-gray-800">
              <h3 className="font-semibold text-gray-900 dark:text-white text-sm">已注册短代码</h3>
            </div>
            <div className="p-3">
              {isLoading ? (
                [1,2,3,4,5].map(i => <div key={i} className="h-10 bg-gray-100 dark:bg-gray-800 rounded-lg mb-2 animate-pulse"/>)
              ) : shortcodes.length === 0 ? (
                <p className="text-sm text-gray-400 text-center py-4">暂无短代码</p>
              ) : (
                shortcodes.map((name: string) => (
                  <div key={name}
                       className="flex items-center justify-between px-3 py-2.5 rounded-xl hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors group">
                    <div className="flex items-center gap-2">
                      <Code className="w-4 h-4 text-blue-500 shrink-0"/>
                      <code className="text-sm font-mono text-gray-800 dark:text-gray-200">{name}</code>
                    </div>
                    <button onClick={() => copy(name)}
                            className="p-1.5 text-gray-400 hover:text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded-lg transition-all opacity-0 group-hover:opacity-100">
                      {copied === name ? <CheckCircle2 className="w-3.5 h-3.5 text-green-500"/> : <Copy className="w-3.5 h-3.5"/>}
                    </button>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>

        {/* Usage help */}
        <div className="lg:col-span-2">
          <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 overflow-hidden">
            <div className="px-5 py-4 border-b border-gray-100 dark:border-gray-800">
              <h3 className="font-semibold text-gray-900 dark:text-white">短代码用法参考</h3>
              <p className="text-xs text-gray-500 mt-0.5">在文章内容中使用短代码插入动态内容</p>
            </div>
            <div className="p-5 space-y-4">
              {shortcodes.length === 0 ? (
                <p className="text-sm text-gray-400 text-center py-8">暂无内置短代码文档</p>
              ) : (
                shortcodes.map((name: string) => (
                  <div key={name} className="p-4 bg-gray-50 dark:bg-gray-800/50 rounded-xl border border-gray-100 dark:border-gray-700">
                    <div className="flex items-center justify-between mb-2">
                      <code className="text-sm font-bold font-mono text-blue-700 dark:text-blue-300 bg-blue-100 dark:bg-blue-900/30 px-2 py-0.5 rounded">
                        [{name}]
                      </code>
                      <button onClick={() => copy(name)}
                              className="text-xs text-gray-400 hover:text-blue-600 transition-colors flex items-center gap-1">
                        {copied === name ? <><CheckCircle2 className="w-3 h-3"/>已复制</> : <><Copy className="w-3 h-3"/>复制</>}
                      </button>
                    </div>
                    {builtinHelp[name] ? (
                      <p className="text-sm text-gray-600 dark:text-gray-400 leading-relaxed" dangerouslySetInnerHTML={{__html: builtinHelp[name]}}/>
                    ) : (
                      <p className="text-sm text-gray-400 italic">暂无说明</p>
                    )}
                    <div className="mt-2 text-[10px] text-gray-400 font-mono bg-gray-100 dark:bg-gray-800 px-2 py-1 rounded">
                      示例: <span className="text-blue-600">{'{{'}&nbsp;{name}&nbsp;{'{...}'}&nbsp;{'}}'}</span>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>
    </AdminShell>
  );
}

export default function AdminShortcodes() {
  return (
    <AuthGuard>
      <QueryProvider>
        <ShortcodesInner/>
      </QueryProvider>
    </AuthGuard>
  );
}
