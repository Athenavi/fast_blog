'use client';

import React, {useState, useMemo, useCallback} from 'react';
import {useMutation, useQuery, useQueryClient} from '@tanstack/react-query';
import {AuthGuard} from '@/components/AuthGuard';
import {QueryProvider} from '@/components/QueryProvider';
import {AdminShell} from '@/components/admin/AdminShell';
import {apiClient} from '@/lib/api/base-client';
import {adminService} from '@/lib/api/admin-service';
import {useToast} from '@/components/ui/toast-provider';

import {
  DndContext, closestCenter, KeyboardSensor, PointerSensor, useSensor, useSensors,
  type DragEndEvent,
} from '@dnd-kit/core';
import {
  SortableContext, sortableKeyboardCoordinates, useSortable,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable';
import {CSS} from '@dnd-kit/utilities';

import {
  Palette, Menu, Layout, Sun, Moon, Monitor, Save, Plus, Trash2, Edit3,
  GripVertical, ChevronDown, Globe, ExternalLink, Image, Type, FileText, Home, Layers,
} from 'lucide-react';

// ─── Types ────────────────────────────────────────────
interface Theme {
  id?: number; name: string; slug: string; version: string; description?: string;
  author?: string; screenshot?: string; is_active?: boolean; is_installed?: boolean;
  category?: string;
}
interface SiteMenu {id: number; name: string; slug: string; description: string; is_active: boolean;}
interface MenuItem {id: number; title: string; url: string; target: string; parent_id: number | null; order_index: number; menu_id?: number;}

const TABS = [
  {key: 'theme', label: '主题', icon: Palette},
  {key: 'menus', label: '菜单', icon: Menu},
  {key: 'header-footer', label: '页头 & 页脚', icon: Layout},
];

// ─── Draggable Menu Item ──────────────────────────────
function SortableMenuItem({item, onDelete, menuId, allItems}: {
  item: MenuItem; onDelete: (id: number) => void; menuId: number;
  allItems: MenuItem[];
}) {
  const {attributes, listeners, setNodeRef, transform, transition, isDragging} = useSortable({id: item.id});
  const style = {transform: CSS.Transform.toString(transform), transition, opacity: isDragging ? 0.5 : 1};

  return (
    <div ref={setNodeRef} style={style}
         className={`flex items-center gap-2 py-2 px-3 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm ${
           isDragging ? 'shadow-lg ring-2 ring-blue-400' : ''
         }`}>
      <button {...attributes} {...listeners} className="cursor-grab active:cursor-grabbing text-gray-400 hover:text-gray-600 dark:hover:text-gray-300">
        <GripVertical className="w-4 h-4"/>
      </button>
      <div className="flex-1 min-w-0 flex items-center gap-2">
        <span className="text-sm font-medium text-gray-800 dark:text-gray-200 truncate">{item.title}</span>
        <span className="text-[10px] text-gray-400 font-mono truncate hidden sm:inline">{item.url}</span>
        {item.target === '_blank' && (
          <span className="px-1.5 py-0.5 bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 rounded text-[10px]">新窗口</span>
        )}
      </div>
      <button onClick={() => onDelete(item.id)}
              className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors">
        <Trash2 className="w-3.5 h-3.5"/>
      </button>
    </div>
  );
}

// ─── Theme Tab ────────────────────────────────────────
function ThemeTab() {
  const toast = useToast();
  const qc = useQueryClient();

  const {data: themes, isLoading} = useQuery({
    queryKey: ['appearance-themes'],
    queryFn: async () => {
      const r = await apiClient.get('/themes/installed');
      return (r.data || []) as Theme[];
    },
  });

  const activateMut = useMutation({
    mutationFn: (slug: string) => apiClient.post(`/themes/${slug}/activate`),
    onSuccess: (r) => { if (r.success) { qc.invalidateQueries({queryKey: ['appearance-themes']}); toast.success('主题已切换'); }},
    onError: () => toast.error('切换失败'),
  });

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">主题管理</h3>
          <p className="text-sm text-gray-500">选择、安装和管理站点主题</p>
        </div>
        <a href="/admin/theme-marketplace"
           className="inline-flex items-center gap-1.5 px-4 py-2 bg-gradient-to-r from-blue-600 to-blue-700 text-white text-sm font-medium rounded-xl hover:from-blue-700 hover:to-blue-800 transition-all shadow-lg shadow-blue-500/25">
          <Plus className="w-4 h-4"/>主题市场
        </a>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1,2,3].map(i => (
            <div key={i} className="h-48 bg-gray-100 dark:bg-gray-800 rounded-2xl animate-pulse"/>
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {(themes || []).map(t => (
            <div key={t.slug}
                 className={`relative rounded-2xl border-2 overflow-hidden transition-all ${
                   t.is_active
                     ? 'border-blue-500 shadow-lg shadow-blue-500/20'
                     : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'
                 }`}>
              <div className="h-32 bg-gradient-to-br from-gray-100 to-gray-200 dark:from-gray-700 dark:to-gray-800 flex items-center justify-center">
                {t.screenshot ? (
                  <img src={t.screenshot} alt={t.name} className="w-full h-full object-cover"/>
                ) : (
                  <Palette className="w-12 h-12 text-gray-400"/>
                )}
              </div>
              <div className="p-4">
                <div className="flex items-center justify-between mb-1">
                  <h4 className="font-semibold text-gray-900 dark:text-white">{t.name}</h4>
                  {t.is_active && (
                    <span className="px-2 py-0.5 bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 rounded-full text-[10px] font-medium">当前</span>
                  )}
                </div>
                <p className="text-xs text-gray-500 mb-3">{t.version} · {t.author || 'FastBlog Team'}</p>
                {!t.is_active && (
                  <button onClick={() => activateMut.mutate(t.slug)}
                          className="w-full py-2 text-sm font-medium text-blue-600 hover:text-white border border-blue-600 hover:bg-blue-600 rounded-xl transition-all">
                    启用
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ─── Menus Tab ────────────────────────────────────────
function MenusTab() {
  const toast = useToast();
  const qc = useQueryClient();

  const {data, isLoading} = useQuery({
    queryKey: ['appearance-menus'],
    queryFn: async () => {
      const r = await adminService.system.getSettings();
      return {menus: (r.data?.menus || []) as SiteMenu[], items: (r.data?.menu_items || {}) as Record<string, MenuItem[]>};
    },
  });
  const menus = data?.menus || [];
  const menuItems = data?.items || {};

  const [selectedMenuId, setSelectedMenuId] = useState<number | null>(null);
  const [showItemForm, setShowItemForm] = useState(false);
  const [itemForm, setItemForm] = useState({title: '', url: '', target: '_self', parent_id: ''});

  const createItemMut = useMutation({
    mutationFn: (d: any) => apiClient.post('/system/settings/menu-items', d),
    onSuccess: () => { qc.invalidateQueries({queryKey: ['appearance-menus']}); setShowItemForm(false); setItemForm({title:'', url:'', target:'_self', parent_id:''}); toast.success('菜单项已添加'); },
    onError: () => toast.error('添加失败'),
  });
  const delItemMut = useMutation({
    mutationFn: (id: number) => apiClient.delete(`/system/settings/menu-items/${id}`),
    onSuccess: () => { qc.invalidateQueries({queryKey: ['appearance-menus']}); toast.success('已删除'); },
  });

  const sensors = useSensors(
    useSensor(PointerSensor, {activationConstraint: {distance: 8}}),
    useSensor(KeyboardSensor, {coordinateGetter: sortableKeyboardCoordinates}),
  );

  const currentItems = selectedMenuId ? (menuItems[String(selectedMenuId)] || []) : [];
  const sortedItems = useMemo(() =>
    [...currentItems].sort((a, b) => a.order_index - b.order_index),
    [currentItems]
  );

  const handleDragEnd = useCallback(async (event: DragEndEvent) => {
    const {active, over} = event;
    if (!over || active.id === over.id) return;

    const oldIdx = sortedItems.findIndex(i => i.id === active.id);
    const newIdx = sortedItems.findIndex(i => i.id === over.id);
    if (oldIdx === -1 || newIdx === -1) return;

    const reordered = [...sortedItems];
    const [moved] = reordered.splice(oldIdx, 1);
    reordered.splice(newIdx, 0, moved);

    const itemsOrder = reordered.map((item, idx) => ({id: item.id, parent_id: item.parent_id, order_index: idx + 1}));
    try {
      await apiClient.post(`/cms/management/menus/${selectedMenuId}/reorder`, {items_order: itemsOrder});
      qc.invalidateQueries({queryKey: ['appearance-menus']});
    } catch { toast.error('排序失败'); }
  }, [sortedItems, selectedMenuId, qc, toast]);

  const parentOptions = useMemo(() => {
    if (!selectedMenuId) return [];
    const items = menuItems[String(selectedMenuId)] || [];
    return [{id: '', title: '(无 — 顶级菜单)'}, ...items.map(i => ({id: String(i.id), title: i.title}))];
  }, [selectedMenuId, menuItems]);

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">菜单管理</h3>
          <p className="text-sm text-gray-500">管理导航菜单和菜单项，支持拖拽排序和嵌套</p>
        </div>
        <a href="/admin/settings" className="text-sm text-blue-600 hover:text-blue-700 dark:text-blue-400">
          管理全部菜单 →
        </a>
      </div>

      {/* Menu selector */}
      <div className="flex gap-2 mb-6 flex-wrap">
        {menus.map(m => (
          <button key={m.id} onClick={() => setSelectedMenuId(m.id)}
                  className={`px-4 py-2 rounded-xl text-sm font-medium transition-all ${
                    selectedMenuId === m.id
                      ? 'bg-blue-600 text-white shadow-lg shadow-blue-500/25'
                      : 'bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 border border-gray-200 dark:border-gray-700 hover:border-blue-300'
                  }`}>
            {m.name}
          </button>
        ))}
      </div>

      {selectedMenuId && (
        <div className="space-y-3">
          <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
            <SortableContext items={sortedItems.map(i => i.id)} strategy={verticalListSortingStrategy}>
              {sortedItems.map(item => (
                <SortableMenuItem key={item.id} item={item} menuId={selectedMenuId}
                                  allItems={sortedItems} onDelete={(id) => delItemMut.mutate(id)}/>
              ))}
            </SortableContext>
          </DndContext>

          {sortedItems.length === 0 && (
            <div className="text-center py-8 text-sm text-gray-400">暂无菜单项</div>
          )}

          {showItemForm ? (
            <div className="p-4 bg-gray-50 dark:bg-gray-800/50 rounded-2xl border border-gray-200 dark:border-gray-700 space-y-3">
              <input value={itemForm.title} onChange={e => setItemForm(p => ({...p, title: e.target.value}))}
                     placeholder="菜单标题" className="w-full px-4 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl bg-white dark:bg-gray-800 text-sm"/>
              <input value={itemForm.url} onChange={e => setItemForm(p => ({...p, url: e.target.value}))}
                     placeholder="链接 URL (如 /articles 或 https://...)" className="w-full px-4 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl bg-white dark:bg-gray-800 text-sm"/>
              <div className="flex gap-3">
                <select value={itemForm.target} onChange={e => setItemForm(p => ({...p, target: e.target.value}))}
                        className="flex-1 px-4 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl bg-white dark:bg-gray-800 text-sm">
                  <option value="_self">当前窗口</option>
                  <option value="_blank">新窗口</option>
                </select>
                <select value={itemForm.parent_id} onChange={e => setItemForm(p => ({...p, parent_id: e.target.value}))}
                        className="flex-1 px-4 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl bg-white dark:bg-gray-800 text-sm">
                  {parentOptions.map(o => (
                    <option key={o.id} value={o.id}>{o.title}</option>
                  ))}
                </select>
              </div>
              <div className="flex gap-2 justify-end">
                <button onClick={() => setShowItemForm(false)}
                        className="px-4 py-2 text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-xl transition-colors">取消</button>
                <button onClick={() => createItemMut.mutate({...itemForm, menu_id: selectedMenuId, parent_id: itemForm.parent_id ? Number(itemForm.parent_id) : null})}
                        className="px-4 py-2 text-sm bg-blue-600 text-white rounded-xl hover:bg-blue-700 transition-colors">添加</button>
              </div>
            </div>
          ) : (
            <button onClick={() => setShowItemForm(true)}
                    className="w-full py-3 border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-2xl text-sm text-gray-500 hover:border-blue-400 hover:text-blue-600 transition-all inline-flex items-center justify-center gap-2">
              <Plus className="w-4 h-4"/>添加菜单项
            </button>
          )}
        </div>
      )}
    </div>
  );
}

// ─── Header & Footer Tab ──────────────────────────────
function HeaderFooterTab() {
  const toast = useToast();
  const qc = useQueryClient();

  const {data, isLoading} = useQuery({
    queryKey: ['appearance-hf'],
    queryFn: async () => {
      const r = await adminService.system.getSettings();
      return (r.data?.settings || {}) as Record<string, string>;
    },
  });
  const settings = data || {};

  const [local, setLocal] = useState<Record<string, string>>({});
  const [hasChanges, setHasChanges] = useState(false);
  const [saving, setSaving] = useState(false);

  React.useEffect(() => {
    if (Object.keys(settings).length > 0 && Object.keys(local).length === 0) {
      setLocal(prev => ({...prev, ...settings}));
    }
  }, [settings, local]);

  const setVal = (k: string, v: string) => { setLocal(p => ({...p, [k]: v})); setHasChanges(true); };

  const save = async () => {
    setSaving(true);
    try {
      const r = await apiClient.post('/system/settings', {settings: local, action: 'update_settings'});
      if (r.success) { toast.success('已保存'); setHasChanges(false); qc.invalidateQueries({queryKey: ['appearance-hf']}); }
      else toast.error(r.error || '保存失败');
    } catch { toast.error('网络异常'); } finally { setSaving(false); }
  };

  const fields = [
    {key: 'site_img', label: 'Logo URL', type: 'text', icon: Image, desc: '站点 Logo 图片地址'},
    {key: 'site_icon', label: '站点图标 (Favicon)', type: 'text', icon: Image, desc: '浏览器标签图标，推荐 32x32px'},
    {key: 'menu_slug', label: '主导航菜单', type: 'text', icon: Menu, desc: '顶部导航使用的菜单标识 (slug)'},
    {key: 'footer_menu_slug', label: '页脚菜单', type: 'text', icon: Menu, desc: '页脚导航使用的菜单标识 (slug)'},
    {key: 'copyright', label: '版权信息', type: 'textarea', icon: Type, desc: '页脚版权文字'},
  ];

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">页头 & 页脚</h3>
          <p className="text-sm text-gray-500">配置站点 Logo、导航菜单和页脚信息</p>
        </div>
        <button onClick={save} disabled={saving || !hasChanges}
                className="inline-flex items-center gap-1.5 px-4 py-2 bg-gradient-to-r from-blue-600 to-blue-700 text-white text-sm font-medium rounded-xl disabled:opacity-50 transition-all shadow-lg shadow-blue-500/25">
          <Save className="w-4 h-4"/>{saving ? '保存中...' : '保存'}
        </button>
      </div>

      <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 overflow-hidden">
        <div className="p-6 space-y-5">
          {fields.map(f => (
            <div key={f.key}>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">{f.label}</label>
              {f.type === 'textarea' ? (
                <textarea value={local[f.key] || ''} onChange={e => setVal(f.key, e.target.value)} rows={2}
                          className="w-full px-4 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl bg-gray-50 dark:bg-gray-800 text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-blue-500"/>
              ) : (
                <input value={local[f.key] || ''} onChange={e => setVal(f.key, e.target.value)}
                       className="w-full px-4 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl bg-gray-50 dark:bg-gray-800 text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-blue-500"/>
              )}
              {f.desc && <p className="text-[10px] text-gray-400 mt-1">{f.desc}</p>}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ─── Main Component ──────────────────────────────────
function AppInner() {
  const [activeTab, setActiveTab] = useState('theme');

  return (
    <AdminShell title="外观设置">
      <div className="mb-6">
        <div className="flex gap-1 bg-gray-100 dark:bg-gray-800 p-1 rounded-2xl w-fit">
          {TABS.map(tab => (
            <button key={tab.key} onClick={() => setActiveTab(tab.key)}
                    className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-medium transition-all ${
                      activeTab === tab.key
                        ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm'
                        : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
                    }`}>
              <tab.icon className="w-4 h-4"/>{tab.label}
            </button>
          ))}
        </div>
      </div>

      {activeTab === 'theme' && <ThemeTab/>}
      {activeTab === 'menus' && <MenusTab/>}
      {activeTab === 'header-footer' && <HeaderFooterTab/>}
    </AdminShell>
  );
}

export default function AdminAppearance() {
  return (
    <AuthGuard>
      <QueryProvider>
        <AppInner/>
      </QueryProvider>
    </AuthGuard>
  );
}
