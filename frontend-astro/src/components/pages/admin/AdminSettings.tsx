'use client';

import React, {useCallback, useEffect, useMemo, useState} from 'react';
import {useMutation, useQuery, useQueryClient} from '@tanstack/react-query';
import {AuthGuard} from '@/components/AuthGuard';
import {QueryProvider} from '@/components/QueryProvider';
import {AdminShell} from '@/components/admin/AdminShell';
import {PermissionGuard} from '@/components/admin/PermissionGuard';
import {StatCard} from '@/components/admin/shared-ui';
import {apiClient} from '@/lib/api/base-client';
import {SYSTEM} from '@/lib/api/api-paths';
import {adminService} from '@/lib/api/admin-service';
import {getConfig} from '@/lib/config';
import {type Locale, locales, useTranslation} from '@/lib/i18n';
import {
  AlertTriangle, CheckCircle2, ChevronDown, Clock, Download, Edit3, ExternalLink, Eye,
  FileCode, FileText, Film, Globe, Hash, Home, Image, Layers, Layout, Link2, Loader, Mail,
  Menu as MenuIcon, Monitor, Plus, Save, Search, Settings as SettingsIcon, Shield, Trash2,
  Type, Upload, X, XCircle, Zap
} from 'lucide-react';

import {TABS, SETTINGS_FIELDS} from './settings/SettingsTypes';
import type {SiteMenu as Menu, MenuItem, Page, FieldDef} from './settings/SettingsTypes';
import {SectionTitle, SettingsSkeleton, MenuSkeleton, PageSkeleton, FieldInput, MediaField, Modal, StatusBadge, TemplateBadge, EmptyState, DeleteConfirm} from './settings/SettingsUI';
// ─── Main Component ───────────────────────────────────
function AdminSettingsInner() {
  const qc = useQueryClient();
  const {locale, setLocale, t} = useTranslation();
  const [activeTab, setActiveTab] = useState('basic');
  const [localSettings, setLocalSettings] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);
  const [saveMsg, setSaveMsg] = useState<{type:'ok'|'err'; text:string}|null>(null);
  const [hasChanges, setHasChanges] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  // ── Delete confirm state ──
  const [deleteTarget, setDeleteTarget] = useState<{
    type: 'menu' | 'menuItem' | 'page';
    id: number;
    name: string
  } | null>(null);

  // ── Load settings ──
  const {data: fullData, isLoading} = useQuery({
    queryKey: ['admin-system-settings'],
    queryFn: async () => {
      const r = await adminService.system.getSettings();
      if (r.success && r.data) {
        const raw = r.data.settings || {};
        const norm: Record<string, string> = {};
        for (const [k, v] of Object.entries(raw)) {
          norm[k] = String(v ?? '');
        }
        setLocalSettings(prev => Object.keys(norm).length > 0 ? norm : prev);
        return r.data;
      }
      return {settings:{}, menus:[], menu_items:{}, pages:[]};
    },
  });

  const settings: Record<string, string> = localSettings;
  const menus: Menu[] = Array.isArray(fullData?.menus) ? fullData.menus : [];
  const menuItems: Record<string, MenuItem[]> = fullData?.menu_items || {};
  const pages: Page[] = Array.isArray(fullData?.pages) ? fullData.pages : [];

  // ── Stats ──
  const stats = useMemo(() => ({
    totalSettings: Object.keys(settings).filter(k => settings[k]).length,
    activeMenus: menus.filter(m => m.is_active).length,
    totalPages: pages.length,
    publishedPages: pages.filter(p => p.status === 1).length,
  }), [settings, menus, pages]);

  // ── Save settings ──
  const saveSettings = async () => {
    setSaving(true); setSaveMsg(null);
    try {
      const r = await apiClient.post(SYSTEM.SETTINGS, {settings: localSettings, action: 'update_settings'});
      setSaveMsg({type: r.success ? 'ok' : 'err', text: r.success ? '✓ 保存成功' : (r.error || '保存失败')});
      if (r.success) {
        qc.invalidateQueries({queryKey: ['admin-system-settings']});
        setHasChanges(false);
      }
    } catch { setSaveMsg({type:'err', text:'网络异常'}); } finally {
      setSaving(false);
      setTimeout(() => setSaveMsg(null), 4000);
    }
  };

  const setVal = (key: string, val: string) => {
    setLocalSettings(prev => ({...prev, [key]: val}));
    setHasChanges(true);
  };

  // ── Export settings ──
  const exportSettings = useCallback(() => {
    const data = {settings: localSettings, menus, menuItems, pages, exportedAt: new Date().toISOString()};
    const blob = new Blob([JSON.stringify(data, null, 2)], {type: 'application/json'});
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `fastblog-settings-${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }, [localSettings, menus, menuItems, pages]);

  // ── Menu mutations ──
  const createMenuMut = useMutation({mutationFn:(d:any)=>apiClient.post(SYSTEM.SETTINGS_MENUS, d), onSuccess:()=>qc.invalidateQueries({queryKey:['admin-system-settings']})});
  const updateMenuMut = useMutation({mutationFn:({id,...d}:any)=>apiClient.put(`/system/settings/menus/${id}`, d), onSuccess:()=>qc.invalidateQueries({queryKey:['admin-system-settings']})});
  const delMenuMut = useMutation({mutationFn:(id:number)=>apiClient.delete(`/system/settings/menus/${id}`), onSuccess:()=>qc.invalidateQueries({queryKey:['admin-system-settings']})});
  const createMenuItemMut = useMutation({mutationFn:(d:any)=>apiClient.post(SYSTEM.SETTINGS_MENU_ITEMS, d), onSuccess:()=>qc.invalidateQueries({queryKey:['admin-system-settings']})});
  const delMenuItemMut = useMutation({mutationFn:(id:number)=>apiClient.delete(`/system/settings/menu-items/${id}`), onSuccess:()=>qc.invalidateQueries({queryKey:['admin-system-settings']})});

  // ── Page mutations ──
  const createPageMut = useMutation({mutationFn:(d:any)=>apiClient.post(SYSTEM.SETTINGS_PAGES, d), onSuccess:()=>qc.invalidateQueries({queryKey:['admin-system-settings']})});
  const delPageMut = useMutation({mutationFn:(id:number)=>apiClient.delete(`/system/settings/pages/${id}`), onSuccess:()=>qc.invalidateQueries({queryKey:['admin-system-settings']})});

  // ── Menus dialog state ──
  const [menuModal, setMenuModal] = useState<{mode:'create'|'edit'; menu?: Menu} | null>(null);
  const [menuForm, setMenuForm] = useState({name:'', slug:'', description:''});
  const [itemModal, setItemModal] = useState<{menuId: number|null} | null>(null);
  const [itemForm, setItemForm] = useState({title: '', url: '', menu_id: 0, target: '_self', parent_id: ''});

  // ── Pages dialog state ──
  const [pageModal, setPageModal] = useState<{mode:'create'|'edit'; page?: Page} | null>(null);
  const [pageForm, setPageForm] = useState({title:'', slug:'', content:'', excerpt:'', template:'default', status:'0'});

  // ── Filtered settings fields ──
  const filteredFields = useMemo(() => {
    const fields = SETTINGS_FIELDS.filter(f => f.category === activeTab);
    if (!searchQuery) return fields;
    const q = searchQuery.toLowerCase();
    return fields.filter(f => f.label.toLowerCase().includes(q) || f.key.toLowerCase().includes(q) || f.desc?.toLowerCase().includes(q));
  }, [activeTab, searchQuery]);

  // ── Handle delete confirm ──
  const handleDeleteConfirm = useCallback(() => {
    if (!deleteTarget) return;
    switch (deleteTarget.type) {
      case 'menu':
        delMenuMut.mutate(deleteTarget.id);
        break;
      case 'menuItem':
        delMenuItemMut.mutate(deleteTarget.id);
        break;
      case 'page':
        delPageMut.mutate(deleteTarget.id);
        break;
    }
    setDeleteTarget(null);
  }, [deleteTarget, delMenuMut, delMenuItemMut, delPageMut]);

  // ── Render tab content ──
  const renderTabContent = () => {
    if (isLoading) {
      return (
          <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200/80 dark:border-gray-700/80 p-6">
            <SettingsSkeleton/>
          </div>
      );
    }

    switch (activeTab) {
      // ── Basic + Home + System (Settings fields) ──
      case 'basic':
      case 'home':
      case 'system': {
        const tabConfig = TABS.find(tb => tb.key === activeTab)!;
        const localeNames: Record<Locale, string> = {
          'zh-CN': t('settings.languageSwitcher.languages.zh-CN'),
          'en': t('settings.languageSwitcher.languages.en'),
          'ar': t('settings.languageSwitcher.languages.ar'),
          'he': t('settings.languageSwitcher.languages.he'),
        };
        return (
          <>
            <div
                className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200/80 dark:border-gray-700/80 overflow-hidden">
              <div className="px-6 py-5 border-b border-gray-100 dark:border-gray-800">
                <SectionTitle icon={tabConfig.icon} title={tabConfig.label} subtitle={tabConfig.desc}
                              action={
                                <div className="flex items-center gap-2">
                                  <div className="relative">
                                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400"/>
                                    <input value={searchQuery} onChange={e => setSearchQuery(e.target.value)}
                                           placeholder={t('settings.systemOptionsDesc')}
                                           className="pl-9 pr-4 py-2 text-sm border border-gray-200 dark:border-gray-700 rounded-xl bg-gray-50 dark:bg-gray-800 text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-blue-500 w-48 transition-all"/>
                                  </div>
                                  <button onClick={saveSettings} disabled={saving || !hasChanges}
                                          className="inline-flex items-center gap-1.5 px-4 py-2 bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 text-white text-sm font-medium rounded-xl disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-lg shadow-blue-500/25 hover:shadow-blue-500/40">
                                    {saving ? <Loader className="w-4 h-4 animate-spin"/> : <Save className="w-4 h-4"/>}
                                    {t('settings.saveSettings')}
                                  </button>
                                </div>
                              }
                />
              </div>

              {/* Save message */}
            {saveMsg && (
                <div className={`mx-6 mt-4 p-3.5 rounded-xl text-sm flex items-center gap-2.5 border ${
                    saveMsg.type === 'ok'
                        ? 'bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-900/20 dark:text-emerald-400 dark:border-emerald-800'
                        : 'bg-red-50 text-red-600 border-red-200 dark:bg-red-900/20 dark:text-red-400 dark:border-red-800'
                }`}>
                  {saveMsg.type === 'ok' ? <CheckCircle2 className="w-4.5 h-4.5"/> : <XCircle className="w-4.5 h-4.5"/>}
                {saveMsg.text}
              </div>
            )}

              {/* Unsaved changes indicator */}
              {hasChanges && !saveMsg && (
                  <div
                      className="mx-6 mt-4 p-3 rounded-xl text-sm flex items-center gap-2 bg-amber-50 text-amber-700 border border-amber-200 dark:bg-amber-900/20 dark:text-amber-400 dark:border-amber-800">
                    <Clock className="w-4 h-4"/>{t('common.loading')}
                  </div>
              )}

              <div className="p-6 space-y-5">
                {filteredFields.length === 0 ? (
                    <div className="text-center py-8 text-sm text-gray-400">
                      {searchQuery ? t('common.noData') : t('common.noData')}
                    </div>
                ) : (
                    filteredFields.map((f, i) => (
                        <div key={f.key} className="group">
                          <div className="flex items-start gap-3">
                            {f.icon && (
                                <div
                                    className="w-8 h-8 rounded-lg bg-gray-100 dark:bg-gray-800 flex items-center justify-center mt-1 group-focus-within:bg-blue-50 dark:group-focus-within:bg-blue-900/20 transition-colors">
                                  <f.icon
                                      className="w-4 h-4 text-gray-400 group-focus-within:text-blue-500 transition-colors"/>
                                </div>
                            )}
                            <div className="flex-1 min-w-0">
                              <label
                                  className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">{f.label}</label>
                              <FieldInput field={f} value={settings[f.key] ?? ''} onChange={v => setVal(f.key, v)}/>
                              <div className="flex items-center justify-between mt-1.5">
                                <p className="text-[10px] text-gray-400 font-mono">{f.key}</p>
                                {f.desc && <p className="text-[10px] text-gray-400">{f.desc}</p>}
                              </div>
                            </div>
                          </div>
                        </div>
                    ))
                )}
            </div>
          </div>

            {/* ── Language Switcher Card ── */}
            <div
              className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200/80 dark:border-gray-700/80 overflow-hidden">
              <div className="px-6 py-5 border-b border-gray-100 dark:border-gray-800">
                <SectionTitle icon={Globe} title={t('settings.languageSwitcher.title')}
                              subtitle={t('settings.languageSwitcher.subtitle')}/>
              </div>
              <div className="p-6">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-3">
                    <div
                      className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center">
                      <Globe className="w-5 h-5 text-white"/>
                    </div>
                    <div>
                      <p
                        className="text-sm font-medium text-gray-700 dark:text-gray-300">{t('settings.languageSwitcher.current')}</p>
                      <p className="text-lg font-semibold text-gray-900 dark:text-white">{localeNames[locale]}</p>
                    </div>
                  </div>
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  {locales.map((loc) => (
                    <button
                      key={loc}
                      onClick={() => setLocale(loc)}
                      className={`relative flex flex-col items-center gap-2 p-4 rounded-xl border-2 transition-all duration-200 ${
                        locale === loc
                          ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20 shadow-md shadow-blue-500/20'
                          : 'border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 hover:border-gray-300 dark:hover:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-750'
                      }`}
                    >
                      {locale === loc && (
                        <div className="absolute top-2 right-2">
                          <CheckCircle2 className="w-4 h-4 text-blue-500"/>
                        </div>
                      )}
                      <span className={`text-sm font-medium ${
                        locale === loc
                          ? 'text-blue-700 dark:text-blue-300'
                          : 'text-gray-700 dark:text-gray-300'
                      }`}>
                        {localeNames[loc]}
                      </span>
                      <span className={`text-xs ${
                        locale === loc
                          ? 'text-blue-500 dark:text-blue-400'
                          : 'text-gray-400 dark:text-gray-500'
                      }`}>
                        {loc}
                      </span>
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </>
        );
      }

      // ── Menus ──
      case 'menus':
        return (
          <div className="space-y-6">
            <div
                className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200/80 dark:border-gray-700/80 overflow-hidden">
              <div className="px-6 py-5 border-b border-gray-100 dark:border-gray-800">
                <SectionTitle icon={MenuIcon} title="导航菜单" subtitle={`共 ${menus.length} 个菜单`}
                              action={
                                <button onClick={() => {
                                  setMenuForm({name: '', slug: '', description: ''});
                                  setMenuModal({mode: 'create'});
                                }}
                                        className="inline-flex items-center gap-1.5 px-4 py-2 bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 text-white text-sm font-medium rounded-xl transition-all shadow-lg shadow-blue-500/25 hover:shadow-blue-500/40">
                                  <Plus className="w-4 h-4"/>新建菜单
                                </button>
                              }
                />
              </div>

              {isLoading ? (
                  <div className="p-6"><MenuSkeleton/></div>
              ) : menus.length === 0 ? (
                  <EmptyState icon={MenuIcon} title="暂无菜单" desc="创建您的第一个导航菜单"
                              action={
                                <button onClick={() => {
                                  setMenuForm({name: '', slug: '', description: ''});
                                  setMenuModal({mode: 'create'});
                                }}
                                        className="inline-flex items-center gap-1.5 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded-xl transition-colors">
                                  <Plus className="w-4 h-4"/>新建菜单
                                </button>
                              }
                  />
              ) : (
                <div className="divide-y divide-gray-100 dark:divide-gray-800">
                  {menus.map((m, idx) => (
                      <div key={m.id}
                           className="px-6 py-5 hover:bg-gray-50/50 dark:hover:bg-gray-800/20 transition-colors group">
                        <div className="flex items-center justify-between mb-3">
                          <div className="flex items-center gap-3">
                            <div
                                className="w-10 h-10 rounded-xl bg-gradient-to-br from-amber-500 to-orange-500 flex items-center justify-center shadow-lg shadow-amber-500/20">
                              <MenuIcon className="w-5 h-5 text-white"/>
                            </div>
                            <div>
                              <div className="flex items-center gap-2">
                                <span className="text-sm font-semibold text-gray-900 dark:text-white">{m.name}</span>
                                <StatusBadge active={m.is_active}/>
                              </div>
                              <div className="flex items-center gap-2 mt-0.5">
                                <span className="text-[10px] text-gray-400 font-mono">{m.slug}</span>
                                {m.description && <span className="text-[10px] text-gray-400">· {m.description}</span>}
                              </div>
                            </div>
                        </div>
                          <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                          <button onClick={() => { setMenuForm({name:m.name, slug:m.slug, description:m.description}); setMenuModal({mode:'edit', menu:m}); }}
                                  className="p-2 text-gray-400 hover:text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded-xl transition-colors"
                                  title="编辑">
                            <Edit3 className="w-4 h-4"/>
                          </button>
                            <button onClick={() => setDeleteTarget({type: 'menu', id: m.id, name: m.name})}
                                    className="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-xl transition-colors"
                                    title="删除">
                              <Trash2 className="w-4 h-4"/>
                            </button>
                        </div>
                      </div>

                        {/* Menu items */}
                      {menuItems[String(m.id)]?.length > 0 && (
                          <div className="ml-[52px] space-y-1.5">
                            {menuItems[String(m.id)].map((item, itemIdx) => (
                                <div key={item.id}
                                     className="flex items-center justify-between py-2 px-3.5 bg-gray-50 dark:bg-gray-800/50 rounded-xl text-sm group/item hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors">
                                  <div className="flex items-center gap-2.5 min-w-0">
                                <span
                                  className="w-5 h-5 rounded bg-gray-200 dark:bg-gray-700 flex items-center justify-center text-[10px] font-mono text-gray-500 dark:text-gray-400 shrink-0">
                                  {itemIdx + 1}
                                </span>
                                    <span
                                        className="text-gray-700 dark:text-gray-300 truncate font-medium">{item.title}</span>
                                    <span className="text-[10px] text-gray-400 truncate font-mono">{item.url}</span>
                                    {item.target === '_blank' && (
                                        <span
                                            className="inline-flex items-center gap-0.5 px-1.5 py-0.5 bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 rounded text-[10px] font-medium shrink-0">
                                    <ExternalLink className="w-2.5 h-2.5"/>新窗口
                                  </span>
                                    )}
                              </div>
                                  <button
                                      onClick={() => setDeleteTarget({type: 'menuItem', id: item.id, name: item.title})}
                                      className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors opacity-0 group-hover/item:opacity-100 shrink-0 ml-2">
                                    <Trash2 className="w-3.5 h-3.5"/>
                                  </button>
                            </div>
                          ))}
                        </div>
                      )}
                      <button onClick={() => { setItemForm({title:'', url:'', menu_id:m.id, target:'_self', parent_id:''}); setItemModal({menuId:m.id}); }}
                              className="ml-[52px] mt-2.5 text-xs text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300 inline-flex items-center gap-1 font-medium hover:underline">
                        <Plus className="w-3.5 h-3.5"/>添加菜单项
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Menu modal */}
            <Modal open={!!menuModal} onClose={() => setMenuModal(null)}
                   title={menuModal?.mode === 'create' ? '新建菜单' : '编辑菜单'}
                   subtitle={menuModal?.mode === 'create' ? '创建一个新的导航菜单' : `编辑菜单「${menuModal?.menu?.name}」`}>
              <div className="space-y-5">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">名称</label>
                  <input value={menuForm.name} onChange={e => setMenuForm(p=>({...p,name:e.target.value}))}
                         className="w-full px-4 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl bg-white dark:bg-gray-800 text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-blue-500 transition-all"
                         placeholder="主导航菜单"/>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">标识
                    (slug)</label>
                  <input value={menuForm.slug} onChange={e => setMenuForm(p=>({...p,slug:e.target.value}))} disabled={menuModal?.mode==='edit'}
                         className="w-full px-4 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl bg-white dark:bg-gray-800 text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-all font-mono"
                         placeholder="main-nav"/>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">描述</label>
                  <input value={menuForm.description} onChange={e => setMenuForm(p=>({...p,description:e.target.value}))}
                         className="w-full px-4 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl bg-white dark:bg-gray-800 text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-blue-500 transition-all"
                         placeholder="菜单用途说明（可选）"/>
                </div>
                <div className="flex justify-end gap-3 pt-3 border-t border-gray-100 dark:border-gray-800">
                  <button onClick={() => setMenuModal(null)}
                          className="px-5 py-2.5 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-xl transition-colors">
                    取消
                  </button>
                  <button onClick={() => {
                    if (menuModal?.mode === 'create') createMenuMut.mutate(menuForm);
                    else if (menuModal?.menu) updateMenuMut.mutate({id: menuModal.menu.id, ...menuForm, is_active: menuModal.menu.is_active});
                    setMenuModal(null);
                  }}
                          className="px-5 py-2.5 text-sm font-medium text-white bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 rounded-xl transition-all shadow-lg shadow-blue-500/25">
                    {menuModal?.mode === 'create' ? '创建菜单' : '保存更改'}
                  </button>
                </div>
              </div>
            </Modal>

            {/* Menu item modal */}
            <Modal open={!!itemModal} onClose={() => setItemModal(null)} title="添加菜单项"
                   subtitle="为菜单添加一个新的导航项">
              <div className="space-y-5">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">标题</label>
                  <input value={itemForm.title} onChange={e => setItemForm(p=>({...p,title:e.target.value}))}
                         className="w-full px-4 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl bg-white dark:bg-gray-800 text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-blue-500 transition-all"
                         placeholder="菜单项名称"/>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">链接 URL</label>
                  <input value={itemForm.url} onChange={e => setItemForm(p=>({...p,url:e.target.value}))}
                         className="w-full px-4 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl bg-white dark:bg-gray-800 text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-blue-500 transition-all font-mono"
                         placeholder="/articles 或 https://..."/>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label
                        className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">打开方式</label>
                    <div className="relative">
                      <select value={itemForm.target} onChange={e => setItemForm(p => ({...p, target: e.target.value}))}
                              className="w-full px-4 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl bg-white dark:bg-gray-800 text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-blue-500 appearance-none pr-10 transition-all">
                        <option value="_self">当前窗口</option>
                        <option value="_blank">新窗口</option>
                      </select>
                      <ChevronDown
                          className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none"/>
                    </div>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">父级 ID</label>
                    <input value={itemForm.parent_id} onChange={e => setItemForm(p=>({...p,parent_id:e.target.value}))}
                           className="w-full px-4 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl bg-white dark:bg-gray-800 text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-blue-500 transition-all"
                           placeholder="留空=顶级"/>
                  </div>
                </div>
                <div className="flex justify-end gap-3 pt-3 border-t border-gray-100 dark:border-gray-800">
                  <button onClick={() => setItemModal(null)}
                          className="px-5 py-2.5 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-xl transition-colors">
                    取消
                  </button>
                  <button onClick={() => {
                    createMenuItemMut.mutate({
                      title: itemForm.title,
                      url: itemForm.url,
                      menu_id: itemForm.menu_id,
                      target: itemForm.target,
                      parent_id: itemForm.parent_id ? parseInt(itemForm.parent_id) : undefined,
                    });
                    setItemModal(null);
                  }}
                          className="px-5 py-2.5 text-sm font-medium text-white bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 rounded-xl transition-all shadow-lg shadow-blue-500/25">
                    添加菜单项
                  </button>
                </div>
              </div>
            </Modal>
          </div>
        );

      // ── Pages ──
      case 'pages':
        return (
            <div
                className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200/80 dark:border-gray-700/80 overflow-hidden">
              <div className="px-6 py-5 border-b border-gray-100 dark:border-gray-800">
                <SectionTitle icon={FileText} title="独立页面" subtitle={`共 ${pages.length} 个页面`}
                              action={
                                <button onClick={() => {
                                  setPageForm({
                                    title: '',
                                    slug: '',
                                    content: '',
                                    excerpt: '',
                                    template: 'default',
                                    status: '0'
                                  });
                                  setPageModal({mode: 'create'});
                                }}
                                        className="inline-flex items-center gap-1.5 px-4 py-2 bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 text-white text-sm font-medium rounded-xl transition-all shadow-lg shadow-blue-500/25 hover:shadow-blue-500/40">
                                  <Plus className="w-4 h-4"/>新建页面
                                </button>
                              }
                />
            </div>

              {isLoading ? (
                  <PageSkeleton/>
              ) : pages.length === 0 ? (
                  <EmptyState icon={FileText} title="暂无页面" desc="创建您的第一个独立页面"
                              action={
                                <button onClick={() => {
                                  setPageForm({
                                    title: '',
                                    slug: '',
                                    content: '',
                                    excerpt: '',
                                    template: 'default',
                                    status: '0'
                                  });
                                  setPageModal({mode: 'create'});
                                }}
                                        className="inline-flex items-center gap-1.5 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded-xl transition-colors">
                                  <Plus className="w-4 h-4"/>新建页面
                                </button>
                              }
                  />
            ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full">
                      <thead
                          className="bg-gray-50/80 dark:bg-gray-800/50 border-b border-gray-100 dark:border-gray-800">
                      <tr>
                        <th className="px-5 py-3.5 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase text-left">标题</th>
                        <th className="px-5 py-3.5 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase text-left hidden sm:table-cell">别名</th>
                        <th className="px-5 py-3.5 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase text-left hidden lg:table-cell">模板</th>
                        <th className="px-5 py-3.5 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase text-left hidden md:table-cell">状态</th>
                        <th className="px-5 py-3.5 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase text-right">操作</th>
                      </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-50 dark:divide-gray-800/50">
                      {pages.map(p => (
                          <tr key={p.id}
                              className="group hover:bg-gray-50/80 dark:hover:bg-gray-800/30 transition-colors">
                            <td className="px-5 py-4">
                              <div className="flex items-center gap-3">
                                <div
                                    className="w-8 h-8 rounded-lg bg-gradient-to-br from-rose-500 to-red-500 flex items-center justify-center shadow-sm">
                                  <FileCode className="w-4 h-4 text-white"/>
                                </div>
                                <span className="text-sm font-medium text-gray-900 dark:text-white">{p.title}</span>
                              </div>
                            </td>
                            <td
                              className="px-5 py-4 text-sm text-gray-500 dark:text-gray-400 font-mono hidden sm:table-cell">
                              <span
                                  className="px-2 py-0.5 bg-gray-100 dark:bg-gray-800 rounded text-xs">/{p.slug}</span>
                            </td>
                            <td className="px-5 py-4 hidden lg:table-cell">
                              <TemplateBadge template={p.template}/>
                            </td>
                            <td className="px-5 py-4 hidden md:table-cell">
                              <StatusBadge active={p.status === 1} label={p.status === 1 ? '已发布' : '草稿'}/>
                            </td>
                            <td className="px-5 py-4 text-right">
                              <div
                                  className="flex items-center justify-end gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                                <a href={`/p/${p.slug}`} target="_blank" rel="noopener"
                                   className="p-2 text-gray-400 hover:text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded-xl transition-colors"
                                   title="预览">
                                  <Eye className="w-4 h-4"/>
                                </a>
                                <button onClick={() => setDeleteTarget({type: 'page', id: p.id, name: p.title})}
                                        className="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-xl transition-colors"
                                        title="删除">
                                  <Trash2 className="w-4 h-4"/>
                                </button>
                              </div>
                            </td>
                          </tr>
                      ))}
                      </tbody>
                    </table>
                  </div>
            )}

              {/* Page modal */}
            <Modal open={!!pageModal} onClose={() => setPageModal(null)}
                   title={pageModal?.mode === 'create' ? '新建页面' : '编辑页面'}
                   subtitle={pageModal?.mode === 'create' ? '创建一个新的独立页面' : `编辑页面「${pageModal?.page?.title}」`}
                   maxWidth="max-w-2xl">
              <div className="space-y-5">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">标题</label>
                    <input value={pageForm.title} onChange={e => setPageForm(p => ({...p, title: e.target.value}))}
                           className="w-full px-4 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl bg-white dark:bg-gray-800 text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-blue-500 transition-all"
                           placeholder="页面标题"/>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">别名
                      (slug)</label>
                    <input value={pageForm.slug} onChange={e => setPageForm(p => ({...p, slug: e.target.value}))}
                           className="w-full px-4 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl bg-white dark:bg-gray-800 text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-blue-500 transition-all font-mono"
                           placeholder="about"/>
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">摘要</label>
                  <input value={pageForm.excerpt} onChange={e => setPageForm(p=>({...p,excerpt:e.target.value}))}
                         className="w-full px-4 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl bg-white dark:bg-gray-800 text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-blue-500 transition-all"
                         placeholder="页面摘要（可选）"/>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">模板</label>
                    <div className="relative">
                      <select value={pageForm.template}
                              onChange={e => setPageForm(p => ({...p, template: e.target.value}))}
                              className="w-full px-4 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl bg-white dark:bg-gray-800 text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-blue-500 appearance-none pr-10 transition-all">
                        <option value="default">默认</option>
                        <option value="full-width">全宽</option>
                        <option value="sidebar">侧边栏</option>
                      </select>
                      <ChevronDown
                          className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none"/>
                    </div>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">状态</label>
                    <div className="relative">
                      <select value={pageForm.status} onChange={e => setPageForm(p => ({...p, status: e.target.value}))}
                              className="w-full px-4 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl bg-white dark:bg-gray-800 text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-blue-500 appearance-none pr-10 transition-all">
                        <option value="0">草稿</option>
                        <option value="1">已发布</option>
                      </select>
                      <ChevronDown
                          className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none"/>
                    </div>
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">内容
                    (Markdown)</label>
                  <textarea value={pageForm.content} onChange={e => setPageForm(p => ({...p, content: e.target.value}))}
                            rows={8}
                            className="w-full px-4 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl bg-white dark:bg-gray-800 text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-blue-500 resize-none font-mono transition-all"
                            placeholder="使用 Markdown 格式编写页面内容..."/>
                </div>
                <div className="flex justify-end gap-3 pt-3 border-t border-gray-100 dark:border-gray-800">
                  <button onClick={() => setPageModal(null)}
                          className="px-5 py-2.5 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-xl transition-colors">
                    取消
                  </button>
                  <button onClick={() => {
                    createPageMut.mutate(pageForm);
                    setPageModal(null);
                  }}
                          className="px-5 py-2.5 text-sm font-medium text-white bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 rounded-xl transition-all shadow-lg shadow-blue-500/25">
                    {pageModal?.mode === 'create' ? '创建页面' : '保存更改'}
                  </button>
                </div>
              </div>
            </Modal>
          </div>
        );
    }
  };

  return (
      <AdminShell title="系统设置" actions={
        <div className="flex items-center gap-2">
          <button onClick={exportSettings}
                  className="inline-flex items-center gap-1.5 px-3 py-2 text-sm text-gray-600 dark:text-gray-400 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-xl hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
            <Download className="w-4 h-4"/>导出配置
          </button>
          {hasChanges && (
              <button onClick={saveSettings} disabled={saving}
                      className="inline-flex items-center gap-1.5 px-4 py-2 bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 text-white text-sm font-medium rounded-xl disabled:opacity-50 transition-all shadow-lg shadow-blue-500/25">
                {saving ? <Loader className="w-4 h-4 animate-spin"/> : <Save className="w-4 h-4"/>}
                保存
              </button>
          )}
        </div>
      }>
        {/* ═══ Stats Cards ═══ */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          <StatCard icon={SettingsIcon} label="已配置项" value={stats.totalSettings}
                    gradient="from-blue-500 to-blue-600"/>
          <StatCard icon={MenuIcon} label="激活菜单" value={stats.activeMenus} gradient="from-amber-500 to-amber-600"/>
          <StatCard icon={FileText} label="总页面数" value={stats.totalPages} gradient="from-purple-500 to-purple-600"/>
          <StatCard icon={CheckCircle2} label="已发布页面" value={stats.publishedPages}
                    gradient="from-emerald-500 to-emerald-600"/>
        </div>

      {/* ═══ Tabs ═══ */}
        <div className="flex gap-1.5 mb-6 overflow-x-auto pb-1 scrollbar-hide">
        {TABS.map(t => {
          const Icon = t.icon;
          const isActive = activeTab === t.key;
          return (
              <button key={t.key} onClick={() => {
                setActiveTab(t.key);
                setSearchQuery('');
              }}
                      className={`relative flex items-center gap-2 px-4 py-2.5 text-sm font-medium rounded-xl whitespace-nowrap transition-all duration-200 ${
                          isActive
                              ? 'bg-gradient-to-r ' + t.gradient + ' text-white shadow-lg shadow-gray-200/50 dark:shadow-gray-900/50'
                              : 'bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800 hover:border-gray-300 dark:hover:border-gray-600'
                      }`}>
              <Icon className="w-4 h-4"/>{t.label}
            </button>
          );
        })}
      </div>

        {/* ═══ Content ═══ */}
      {renderTabContent()}

        {/* ═══ Delete Confirm Modal ═══ */}
        <Modal open={!!deleteTarget} onClose={() => setDeleteTarget(null)} title="确认删除">
          {deleteTarget && (
              <DeleteConfirm
                  title={`删除${deleteTarget.type === 'menu' ? '菜单' : deleteTarget.type === 'menuItem' ? '菜单项' : '页面'}`}
                  desc={`确定要删除「${deleteTarget.name}」吗？此操作不可撤销。`}
                  onConfirm={handleDeleteConfirm}
                  onCancel={() => setDeleteTarget(null)}
                  isPending={delMenuMut.isPending || delMenuItemMut.isPending || delPageMut.isPending}
              />
          )}
        </Modal>
    </AdminShell>
  );
}

export default function AdminSettings() {
  return (
    <QueryProvider>
      <AuthGuard>
        <PermissionGuard capability="settings:view">
          <AdminSettingsInner />
          </PermissionGuard>
      </AuthGuard>
    </QueryProvider>
  );
}
