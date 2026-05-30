'use client';

import React, {useState} from 'react';
import {useMutation, useQuery, useQueryClient} from '@tanstack/react-query';
import {AuthGuard} from '@/components/AuthGuard';
import {QueryProvider} from '@/components/QueryProvider';
import {AdminShell} from '@/components/admin/AdminShell';
import {DeleteConfirm, EmptyState, Modal} from '@/components/admin/shared-ui';
import {apiClient} from '@/lib/api/api-client';
import {ChevronLeft, ChevronRight, Edit3, FileEdit, Link2, MapPin, MessageSquare, Plus, Trash2} from 'lucide-react';

/* ─── Types ─────────────────────────────────────── */
interface RevisionNote {
  id: number;
  revision_id: number;
  user_id: number;
  note_content: string;
  created_at?: string;
}

interface MenuLocation {
  id: number;
  name: string;
  slug: string;
  description?: string;
  theme_supports?: string;
  created_at?: string;
  updated_at?: string;
}

interface LocationAssignment {
  id: number;
  menu_id: number;
  location_id: number;
  menu_name?: string;
  location_name?: string;
  created_at?: string;
}

interface Pagination {
  page: number;
  per_page: number;
  total: number;
  total_pages: number;
}

const Input: React.FC<{
  label: string;
  value: string;
  onChange: (v: string) => void;
  type?: string;
  placeholder?: string;
  rows?: number
}> = ({label, value, onChange, type, placeholder, rows}) => (
  <div className="mb-3">
    <label className="block text-xs font-semibold text-gray-500 dark:text-gray-400 mb-1">{label}</label>
    {rows ? (
      <textarea rows={rows} value={value} onChange={e => onChange(e.target.value)} placeholder={placeholder}
                className="w-full px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white placeholder-gray-400 resize-none"/>
    ) : (
      <input type={type || 'text'} value={value} onChange={e => onChange(e.target.value)} placeholder={placeholder}
             className="w-full px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white placeholder-gray-400"/>
    )}
  </div>
);

/* ─── Revision Notes Tab ────────────────────────── */
const RevisionNotesTab: React.FC = () => {
  const [page, setPage] = useState(1);
  const [revisionId, setRevisionId] = useState('');
  const {data, isLoading} = useQuery({
    queryKey: ['revision-notes', page, revisionId],
    queryFn: () => apiClient.get('/cms/management/revision-notes', {
      page,
      per_page: 15,
      revision_id: revisionId || undefined
    }),
  });
  const items: RevisionNote[] = data?.data || [];
  const pagination: Pagination | undefined = data?.pagination;

  return (
    <>
      <div className="flex items-center gap-2 mb-4">
        <input value={revisionId} onChange={e => {
          setRevisionId(e.target.value);
          setPage(1);
        }}
               placeholder="按修订ID筛选" type="number"
               className="px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white w-40"/>
      </div>
      {isLoading ? <div className="animate-pulse space-y-2">{[1, 2, 3].map(i => <div key={i}
                                                                                     className="h-16 bg-gray-100 dark:bg-gray-800 rounded-xl"/>)}</div> :
        items.length === 0 ? <EmptyState icon={MessageSquare} title="暂无修订注释" desc="文章修订时的注释将在此显示"/> :
          <div className="space-y-2">
            {items.map(n => (
              <div key={n.id}
                   className="p-4 bg-gray-50 dark:bg-gray-800/50 rounded-xl border border-gray-100 dark:border-gray-700/50">
                <div className="flex items-center gap-2 mb-2">
                  <span
                    className="text-[10px] bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400 px-1.5 py-0.5 rounded font-mono">修订#{n.revision_id}</span>
                  <span
                    className="text-[10px] bg-gray-200 dark:bg-gray-700 px-1.5 py-0.5 rounded text-gray-600 dark:text-gray-300 font-mono">用户#{n.user_id}</span>
                  <span
                    className="text-[10px] text-gray-400 ml-auto">{n.created_at ? new Date(n.created_at).toLocaleString('zh-CN') : ''}</span>
                </div>
                <p className="text-sm text-gray-700 dark:text-gray-300">{n.note_content}</p>
              </div>
            ))}
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

/* ─── Menu Locations Tab ───────────────────────── */
const MenuLocationsTab: React.FC = () => {
  const qc = useQueryClient();
  const [page, setPage] = useState(1);
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<MenuLocation | null>(null);
  const [deleteId, setDeleteId] = useState<number | null>(null);
  const [form, setForm] = useState({name: '', slug: '', description: '', theme_supports: ''});

  const {data, isLoading} = useQuery({
    queryKey: ['menu-locations', page],
    queryFn: () => apiClient.get('/cms/management/menu-locations', {page, per_page: 15}),
  });
  const items: MenuLocation[] = data?.data || [];
  const pagination: Pagination | undefined = data?.pagination;

  const createMut = useMutation({
    mutationFn: (d: any) => apiClient.post('/cms/management/menu-locations', d),
    onSuccess: (r: any) => {
      if (r.success) {
        qc.invalidateQueries({queryKey: ['menu-locations']});
        setShowForm(false);
      } else alert(r.error);
    },
  });
  const updateMut = useMutation({
    mutationFn: ({id, ...d}: any) => apiClient.put(`/cms/management/menu-locations/${id}`, d),
    onSuccess: (r: any) => {
      if (r.success) {
        qc.invalidateQueries({queryKey: ['menu-locations']});
        setShowForm(false);
      } else alert(r.error);
    },
  });
  const deleteMut = useMutation({
    mutationFn: (id: number) => apiClient.delete(`/cms/management/menu-locations/${id}`),
    onSuccess: (r: any) => {
      if (r.success) {
        qc.invalidateQueries({queryKey: ['menu-locations']});
        setDeleteId(null);
      } else alert(r.error);
    },
  });

  const openCreate = () => {
    setEditing(null);
    setForm({name: '', slug: '', description: '', theme_supports: ''});
    setShowForm(true);
  };
  const openEdit = (l: MenuLocation) => {
    setEditing(l);
    setForm({name: l.name, slug: l.slug, description: l.description || '', theme_supports: l.theme_supports || ''});
    setShowForm(true);
  };
  const submit = () => {
    if (!form.name.trim() || !form.slug.trim()) return alert('请填写名称和标识');
    if (editing) updateMut.mutate({id: editing.id, ...form});
    else createMut.mutate(form);
  };

  return (
    <>
      <div className="flex items-center justify-end mb-4">
        <button onClick={openCreate}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded-xl flex items-center gap-1.5">
          <Plus className="w-4 h-4"/>新建位置
        </button>
      </div>
      {isLoading ? <div className="animate-pulse space-y-2">{[1, 2, 3].map(i => <div key={i}
                                                                                     className="h-16 bg-gray-100 dark:bg-gray-800 rounded-xl"/>)}</div> :
        items.length === 0 ? <EmptyState icon={MapPin} title="暂无菜单位置" desc="定义菜单位置（如主菜单、页脚菜单等）"/> :
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {items.map(l => (
              <div key={l.id}
                   className="p-4 bg-gray-50 dark:bg-gray-800/50 rounded-xl border border-gray-100 dark:border-gray-700/50">
                <div className="flex items-start justify-between mb-2">
                  <div>
                    <h4 className="text-sm font-semibold text-gray-900 dark:text-white">{l.name}</h4>
                    <code
                      className="text-[10px] bg-gray-200 dark:bg-gray-700 px-1.5 py-0.5 rounded text-gray-600 dark:text-gray-300">{l.slug}</code>
                  </div>
                  <div className="flex gap-1">
                    <button onClick={() => openEdit(l)}
                            className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-500"><Edit3
                      className="w-3.5 h-3.5"/></button>
                    <button onClick={() => setDeleteId(l.id)}
                            className="p-1.5 rounded-lg hover:bg-red-50 dark:hover:bg-red-900/20 text-red-500"><Trash2
                      className="w-3.5 h-3.5"/></button>
                  </div>
                </div>
                {l.description && <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">{l.description}</p>}
                {l.theme_supports && <p className="text-[10px] text-gray-400">主题: {l.theme_supports}</p>}
              </div>
            ))}
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
      <Modal open={showForm} onClose={() => setShowForm(false)} title={editing ? '编辑菜单位置' : '新建菜单位置'}>
        <Input label="名称 *" value={form.name} onChange={v => setForm({...form, name: v})} placeholder="例如：主菜单"/>
        <Input label="标识 *" value={form.slug} onChange={v => setForm({...form, slug: v})} placeholder="例如：primary"/>
        <Input label="描述" value={form.description} onChange={v => setForm({...form, description: v})} rows={2}/>
        <Input label="主题支持" value={form.theme_supports} onChange={v => setForm({...form, theme_supports: v})}
               placeholder="例如：default,minimal"/>
        <div className="flex justify-end gap-2 mt-4">
          <button onClick={() => setShowForm(false)}
                  className="px-4 py-2 text-sm border border-gray-200 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 text-gray-600 dark:text-gray-300">取消
          </button>
          <button onClick={submit}
                  className="px-4 py-2 text-sm bg-blue-600 hover:bg-blue-700 text-white rounded-lg">{editing ? '更新' : '创建'}</button>
        </div>
      </Modal>
      {deleteId !== null && (
        <Modal open={true} onClose={() => setDeleteId(null)} title="确认删除">
          <DeleteConfirm itemName={items.find(l => l.id === deleteId)?.name}
                         onConfirm={() => deleteMut.mutate(deleteId)} onCancel={() => setDeleteId(null)}
                         isPending={deleteMut.isPending}/>
        </Modal>
      )}
    </>
  );
};

/* ─── Assignments Tab ──────────────────────────── */
const AssignmentsTab: React.FC = () => {
  const qc = useQueryClient();
  const [page, setPage] = useState(1);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({menu_id: '', location_id: ''});

  const {data, isLoading} = useQuery({
    queryKey: ['menu-assignments', page],
    queryFn: () => apiClient.get('/cms/management/menu-location-assignments', {page, per_page: 15}),
  });
  const items: LocationAssignment[] = data?.data || [];
  const pagination: Pagination | undefined = data?.pagination;

  const createMut = useMutation({
    mutationFn: (d: any) => apiClient.post('/cms/management/menu-location-assignments', d),
    onSuccess: (r: any) => {
      if (r.success) {
        qc.invalidateQueries({queryKey: ['menu-assignments']});
        setShowForm(false);
      } else alert(r.error);
    },
  });
  const deleteMut = useMutation({
    mutationFn: (id: number) => apiClient.delete(`/cms/management/menu-location-assignments/${id}`),
    onSuccess: () => qc.invalidateQueries({queryKey: ['menu-assignments']}),
  });

  const submit = () => {
    if (!form.menu_id || !form.location_id) return alert('请填写菜单ID和位置ID');
    createMut.mutate({menu_id: parseInt(form.menu_id), location_id: parseInt(form.location_id)});
  };

  return (
    <>
      <div className="flex items-center justify-end mb-4">
        <button onClick={() => {
          setForm({menu_id: '', location_id: ''});
          setShowForm(true);
        }}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded-xl flex items-center gap-1.5">
          <Plus className="w-4 h-4"/>新建关联
        </button>
      </div>
      {isLoading ? <div className="animate-pulse space-y-2">{[1, 2, 3].map(i => <div key={i}
                                                                                     className="h-12 bg-gray-100 dark:bg-gray-800 rounded-xl"/>)}</div> :
        items.length === 0 ? <EmptyState icon={Link2} title="暂无菜单关联" desc="将菜单分配到菜单位置"/> :
          <div className="space-y-2">
            {items.map(a => (
              <div key={a.id}
                   className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800/50 rounded-xl border border-gray-100 dark:border-gray-700/50">
                <div className="flex items-center gap-3">
                  <Link2 className="w-4 h-4 text-gray-400"/>
                  <span className="text-sm text-gray-900 dark:text-white">菜单#{a.menu_id}</span>
                  <span className="text-xs text-gray-400">→</span>
                  <span className="text-sm text-gray-600 dark:text-gray-300">位置#{a.location_id}</span>
                  <span
                    className="text-[10px] text-gray-400">{a.created_at ? new Date(a.created_at).toLocaleString('zh-CN') : ''}</span>
                </div>
                <button onClick={() => {
                  if (confirm('确定删除此关联？')) deleteMut.mutate(a.id);
                }}
                        className="p-1.5 rounded-lg hover:bg-red-50 dark:hover:bg-red-900/20 text-red-500"><Trash2
                  className="w-3.5 h-3.5"/></button>
              </div>
            ))}
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
      <Modal open={showForm} onClose={() => setShowForm(false)} title="新建菜单-位置关联">
        <Input label="菜单 ID *" value={form.menu_id} onChange={v => setForm({...form, menu_id: v})} type="number"
               placeholder="菜单ID"/>
        <Input label="位置 ID *" value={form.location_id} onChange={v => setForm({...form, location_id: v})}
               type="number" placeholder="位置ID"/>
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
type TabKey = 'revision-notes' | 'menu-locations' | 'assignments';
const TABS: { key: TabKey; label: string; icon: any }[] = [
  {key: 'revision-notes', label: '修订注释', icon: FileEdit},
  {key: 'menu-locations', label: '菜单位置', icon: MapPin},
  {key: 'assignments', label: '菜单关联', icon: Link2},
];

function ContentExtInner() {
  const [tab, setTab] = useState<TabKey>('menu-locations');

  return (
    <AdminShell title="内容管理扩展" actions={<FileEdit className="w-5 h-5 text-blue-500"/>}>
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
          {tab === 'revision-notes' && <RevisionNotesTab/>}
          {tab === 'menu-locations' && <MenuLocationsTab/>}
          {tab === 'assignments' && <AssignmentsTab/>}
        </div>
      </div>
    </AdminShell>
  );
}

export default function AdminContentManagementExt() {
  return (
    <AuthGuard requireAdmin>
      <QueryProvider>
        <ContentExtInner/>
      </QueryProvider>
    </AuthGuard>
  );
}
