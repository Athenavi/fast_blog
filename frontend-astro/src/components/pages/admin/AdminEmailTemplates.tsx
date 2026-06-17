'use client';

import React, {useState} from 'react';
import {useMutation, useQuery, useQueryClient} from '@tanstack/react-query';
import {AuthGuard} from '@/components/AuthGuard';
import {QueryProvider} from '@/components/QueryProvider';
import {AdminShell} from '@/components/admin/AdminShell';
import {ToastProvider} from '@/components/ui/toast-provider';
import {apiClient} from '@/lib/api/base-client';
import {useToast} from '@/components/ui/toast-provider';
import {Mail, Save, RotateCcw, Loader, FileText, Eye, Code} from 'lucide-react';

interface Template {
  name: string; label: string; subject: string; html: string; is_custom: boolean;
}

function EmailTemplatesInner() {
  const toast = useToast();
  const qc = useQueryClient();
  const [activeTemplate, setActiveTemplate] = useState<string | null>(null);
  const [editedHtml, setEditedHtml] = useState('');
  const [previewMode, setPreviewMode] = useState<'code' | 'preview'>('code');
  const [saving, setSaving] = useState(false);

  const {data, isLoading} = useQuery({
    queryKey: ['email-templates'],
    queryFn: async () => {
      const r = await apiClient.get('/notifications/email/templates');
      return (r.data?.templates || []) as Template[];
    },
  });
  const templates = data || [];

  const activeTpl = templates.find(t => t.name === activeTemplate) || null;

  const selectTemplate = (name: string) => {
    const tpl = templates.find(t => t.name === name);
    if (tpl) { setActiveTemplate(name); setEditedHtml(tpl.html); }
  };

  const saveMut = useMutation({
    mutationFn: async () => {
      setSaving(true);
      const r = await apiClient.put(`/notifications/email/templates/${activeTemplate}`, {html: editedHtml, subject: activeTpl?.subject || ''});
      setSaving(false);
      return r;
    },
    onSuccess: (r) => { if (r.success) { toast.success('模板已保存'); qc.invalidateQueries({queryKey: ['email-templates']}); } else toast.error(r.error); },
    onError: () => { setSaving(false); toast.error('保存失败'); },
  });

  const resetMut = useMutation({
    mutationFn: () => apiClient.delete(`/notifications/email/templates/${activeTemplate}/reset`),
    onSuccess: (r) => { if (r.success) { toast.success('已重置为默认'); qc.invalidateQueries({queryKey: ['email-templates']}); setEditedHtml(''); } else toast.error(r.error); },
  });

  const variables = activeTpl?.html?.match(/\{\{\s*\w+\s*\}\}/g) || [];

  return (
    <AdminShell title="邮件模板">
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Sidebar */}
        <div className="lg:col-span-1">
          <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 overflow-hidden">
            <div className="px-5 py-4 border-b border-gray-100 dark:border-gray-800">
              <h3 className="font-semibold text-gray-900 dark:text-white text-sm">模板列表</h3>
            </div>
            <div className="p-3 space-y-1">
              {isLoading ? (
                [1,2,3].map(i => <div key={i} className="h-12 bg-gray-100 dark:bg-gray-800 rounded-xl animate-pulse"/>)
              ) : templates.length === 0 ? (
                <p className="text-sm text-gray-400 text-center py-4">暂无模板</p>
              ) : (
                templates.map(t => (
                  <button key={t.name} onClick={() => selectTemplate(t.name)}
                          className={`w-full flex items-center gap-3 px-3 py-3 rounded-xl text-sm font-medium transition-all text-left ${
                            activeTemplate === t.name
                              ? 'bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300'
                              : 'text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800'
                          }`}>
                    <Mail className="w-4 h-4 shrink-0"/>
                    <div className="min-w-0">
                      <p className="truncate">{t.label}</p>
                      {t.is_custom && <span className="text-[10px] text-blue-500">已自定义</span>}
                    </div>
                  </button>
                ))
              )}
            </div>
          </div>

          {/* Template variables reference */}
          {activeTpl && variables.length > 0 && (
            <div className="mt-4 bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 overflow-hidden">
              <div className="px-5 py-3 border-b border-gray-100 dark:border-gray-800">
                <h4 className="text-xs font-semibold text-gray-500">可用变量</h4>
              </div>
              <div className="p-3 space-y-1">
                {[...new Set(variables)].map(v => (
                  <code key={v} className="block px-2 py-1 text-xs bg-gray-100 dark:bg-gray-800 rounded font-mono text-gray-600 dark:text-gray-400">{v}</code>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Editor */}
        <div className="lg:col-span-3">
          {activeTpl ? (
            <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 overflow-hidden">
              {/* Header */}
              <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700">
                <div>
                  <h3 className="font-semibold text-gray-900 dark:text-white">{activeTpl.label}</h3>
                  <p className="text-xs text-gray-500">模板名称: {activeTpl.name}</p>
                </div>
                <div className="flex items-center gap-2">
                  <div className="flex bg-gray-100 dark:bg-gray-800 p-0.5 rounded-lg">
                    <button onClick={() => setPreviewMode('code')}
                            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${previewMode === 'code' ? 'bg-white dark:bg-gray-700 shadow-sm' : ''}`}>
                      <Code className="w-3.5 h-3.5 inline mr-1"/>代码
                    </button>
                    <button onClick={() => setPreviewMode('preview')}
                            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${previewMode === 'preview' ? 'bg-white dark:bg-gray-700 shadow-sm' : ''}`}>
                      <Eye className="w-3.5 h-3.5 inline mr-1"/>预览
                    </button>
                  </div>
                  <button onClick={() => resetMut.mutate()}
                          className="p-2 text-gray-400 hover:text-orange-600 hover:bg-orange-50 dark:hover:bg-orange-900/20 rounded-lg transition-colors" title="重置为默认">
                    <RotateCcw className="w-4 h-4"/>
                  </button>
                  <button onClick={() => saveMut.mutate()} disabled={saving}
                          className="inline-flex items-center gap-1.5 px-4 py-2 bg-gradient-to-r from-blue-600 to-blue-700 text-white text-sm font-medium rounded-xl hover:from-blue-700 hover:to-blue-800 disabled:opacity-50 transition-all shadow-lg shadow-blue-500/25">
                    {saving ? <Loader className="w-4 h-4 animate-spin"/> : <Save className="w-4 h-4"/>}
                    保存
                  </button>
                </div>
              </div>

              {/* Subject */}
              <div className="px-6 py-3 border-b border-gray-100 dark:border-gray-800 bg-gray-50 dark:bg-gray-800/30">
                <label className="text-xs text-gray-500 font-medium">邮件主题</label>
                <p className="text-sm text-gray-900 dark:text-white font-mono">{activeTpl.subject}</p>
              </div>

              {/* Code editor / Preview */}
              <div className="p-6">
                {previewMode === 'code' ? (
                  <textarea value={editedHtml} onChange={e => setEditedHtml(e.target.value)}
                            className="w-full h-[500px] px-4 py-3 border border-gray-200 dark:border-gray-700 rounded-xl bg-gray-50 dark:bg-gray-800 text-sm font-mono text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-blue-500 resize-y"
                            placeholder="<!-- HTML 邮件模板 -->"/>
                ) : (
                  <div className="border border-gray-200 dark:border-gray-700 rounded-xl overflow-hidden">
                    <iframe srcDoc={editedHtml} title="email-preview"
                            className="w-full h-[500px] bg-white"/>
                  </div>
                )}
              </div>

              {/* Info */}
              <div className="px-6 py-3 border-t border-gray-100 dark:border-gray-800 bg-gray-50 dark:bg-gray-800/30 flex items-center justify-between text-xs text-gray-500">
                <span>支持 HTML + 内联样式</span>
                <span>变量使用 <code className="bg-gray-200 dark:bg-gray-700 px-1 rounded">{'{{ variable_name }}'}</code> 语法</span>
              </div>
            </div>
          ) : (
            <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 p-12 text-center">
              <Mail className="w-16 h-16 mx-auto mb-4 text-gray-300 dark:text-gray-600"/>
              <p className="text-lg font-medium text-gray-500 dark:text-gray-400 mb-1">选择邮件模板</p>
              <p className="text-sm text-gray-400">从左侧列表选择一个模板开始编辑</p>
            </div>
          )}
        </div>
      </div>
    </AdminShell>
  );
}

export default function AdminEmailTemplates() {
  return (
    <AuthGuard>
      <QueryProvider>
        <ToastProvider>
          <EmailTemplatesInner/>
        </ToastProvider>
      </QueryProvider>
    </AuthGuard>
  );
}
