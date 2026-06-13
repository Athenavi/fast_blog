'use client';

import React, {useState} from 'react';
import {useMutation, useQuery, useQueryClient} from '@tanstack/react-query';
import {AuthGuard} from '@/components/AuthGuard';
import {QueryProvider} from '@/components/QueryProvider';
import {AdminShell} from '@/components/admin/AdminShell';
import {apiClient} from '@/lib/api/base-client';
import {useToast} from '@/components/ui/toast-provider';
import {
  FileText, Plus, Edit3, Trash2, Save, X, CheckCircle2, Loader, Layers,
} from 'lucide-react';

interface CPT {
  id: number; name: string; slug: string; description?: string;
  menu_icon?: string; is_active?: boolean; created_at?: string;
}

function CptInner() {
  const toast = useToast();
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<CPT | null>(null);
  const [form, setForm] = useState({name: '', slug: '', description: '', menu_icon: 'FileText', is_active: 'true'});

  const {data, isLoading} = useQuery({
    queryKey: ['custom-post-types'],
    queryFn: async () => {
      const r = await apiClient.get('/cms/post-types');
      return ((r.data as any)?.items || r.data || []) as CPT[];
    },
  });
  const types = data || [];

  const saveMut = useMutation({
    mutationFn: () => {
      const body: Record<string, any> = {
        name: form.name,
        description: form.description,
        menu_icon: form.menu_icon || 'FileText',
        supports: 'title,editor,thumbnail',
        has_archive: true,
      };
      if (editing) {
        body.is_active = form.is_active === 'true';
        return apiClient.put(`/cms/post-types/${editing.id}`, body);
      }
      body.slug = form.slug;
      return apiClient.post('/cms/post-types', body);
    },
    onSuccess: (r) => { if (r.success) { qc.invalidateQueries({queryKey: ['custom-post-types']}); setShowForm(false); setEditing(null); toast.success(editing ? '已更新' : '已创建'); } else toast.error(r.error); },
    onError: () => toast.error('保存失败'),
  });

  const delMut = useMutation({
    mutationFn: (id: number) => apiClient.delete(`/cms/post-types/${id}`),
    onSuccess: () => { qc.invalidateQueries({queryKey: ['custom-post-types']}); toast.success('已删除'); },
  });

  const openEdit = (cpt: CPT) => {
    setEditing(cpt);
    setForm({name: cpt.name, slug: cpt.slug, description: cpt.description || '', menu_icon: cpt.menu_icon || 'FileText', is_active: String(cpt.is_active ?? true)});
    setShowForm(true);
  };

  const openCreate = () => {
    setEditing(null);
    setForm({name: '', slug: '', description: '', menu_icon: 'FileText', is_active: 'true'});
    setShowForm(true);
  };

  return (
    <AdminShell title="自定义文章类型" actions={
      !showForm && <button onClick={openCreate}
              className="inline-flex items-center gap-1.5 px-4 py-2 bg-gradient-to-r from-blue-600 to-blue-700 text-white text-sm font-medium rounded-xl hover:from-blue-700 hover:to-blue-800 transition-all shadow-lg shadow-blue-500/25">
        <Plus className="w-4 h-4"/>新建类型
      </button>
    }>
      {showForm && (
        <div className="mb-6 bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 p-6">
          <h3 className="font-semibold text-gray-900 dark:text-white mb-4">{editing ? '编辑文章类型' : '新建文章类型'}</h3>
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-xs text-gray-500 mb-1 block">名称</label>
                <input value={form.name} onChange={e => setForm(p => ({...p, name: e.target.value}))}
                       className="w-full px-4 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl bg-gray-50 dark:bg-gray-800 text-sm"/>
              </div>
              <div>
                <label className="text-xs text-gray-500 mb-1 block">标识 (slug)</label>
                <input value={form.slug} onChange={e => setForm(p => ({...p, slug: e.target.value}))}
                       className="w-full px-4 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl bg-gray-50 dark:bg-gray-800 text-sm font-mono"/>
              </div>
            </div>
            <div>
              <label className="text-xs text-gray-500 mb-1 block">描述</label>
              <textarea value={form.description} onChange={e => setForm(p => ({...p, description: e.target.value}))} rows={2}
                        className="w-full px-4 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl bg-gray-50 dark:bg-gray-800 text-sm"/>
            </div>
            <div className="flex items-center gap-4">
              <label className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
                <input type="checkbox" checked={form.is_active === 'true'} onChange={e => setForm(p => ({...p, is_active: String(e.target.checked)}))}
                       className="rounded border-gray-300"/>
                公开
              </label>
            </div>
            <div className="flex justify-end gap-2">
              <button onClick={() => { setShowForm(false); setEditing(null); }}
                      className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-xl">取消</button>
              <button onClick={() => saveMut.mutate()} disabled={saveMut.isPending || !form.name || !form.slug}
                      className="px-4 py-2 text-sm bg-blue-600 text-white rounded-xl hover:bg-blue-700 disabled:opacity-50 inline-flex items-center gap-1.5">
                {saveMut.isPending ? <Loader className="w-4 h-4 animate-spin"/> : <Save className="w-4 h-4"/>}
                {editing ? '更新' : '创建'}
              </button>
            </div>
          </div>
        </div>
      )}

      {isLoading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1,2,3].map(i => <div key={i} className="h-32 bg-gray-100 dark:bg-gray-800 rounded-2xl animate-pulse"/>)}
        </div>
      ) : types.length === 0 && !showForm ? (
        <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 p-16 text-center">
          <Layers className="w-16 h-16 mx-auto mb-4 text-gray-300 dark:text-gray-600"/>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">暂无自定义文章类型</h3>
          <p className="text-sm text-gray-500 dark:text-gray-400 mb-6">自定义文章类型允许你创建不同于标准文章的内容类型</p>
          <button onClick={openCreate}
                  className="inline-flex items-center gap-1.5 px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-xl transition-colors">
            <Plus className="w-4 h-4"/>新建文章类型
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {types.map(cpt => (
            <div key={cpt.id}
                 className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 p-5 hover:border-gray-300 dark:hover:border-gray-600 hover:shadow-lg transition-all group">
              <div className="flex items-start justify-between mb-3">
                <div className="w-10 h-10 rounded-xl bg-purple-100 dark:bg-purple-900/30 flex items-center justify-center">
                  <Layers className="w-5 h-5 text-purple-600 dark:text-purple-400"/>
                </div>
                <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                  <button onClick={() => openEdit(cpt)}
                          className="p-1.5 text-gray-400 hover:text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded-lg transition-colors">
                    <Edit3 className="w-4 h-4"/>
                  </button>
                  <button onClick={() => { if (confirm('确定删除此文章类型？')) delMut.mutate(cpt.id); }}
                          className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors">
                    <Trash2 className="w-4 h-4"/>
                  </button>
                </div>
              </div>
              <h3 className="font-semibold text-gray-900 dark:text-white mb-1">{cpt.name}</h3>
              <code className="text-xs text-gray-400 font-mono">/{cpt.slug}</code>
              {cpt.description && <p className="text-xs text-gray-500 mt-2">{cpt.description}</p>}
              <div className="flex items-center gap-2 mt-3 pt-3 border-t border-gray-100 dark:border-gray-800">
                <span className={`px-2 py-0.5 rounded-full text-[10px] font-medium ${cpt.is_active ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400' : 'bg-gray-100 text-gray-500'}`}>
                  {cpt.is_active ? '公开' : '内部'}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </AdminShell>
  );
}

export default function AdminCustomPostTypes() {
  return (
    <AuthGuard>
      <QueryProvider>
        <CptInner/>
      </QueryProvider>
    </AuthGuard>
  );
}
