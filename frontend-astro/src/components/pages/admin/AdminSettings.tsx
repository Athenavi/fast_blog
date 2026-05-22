'use client';

import React, {useState, useMemo, useCallback} from 'react';
import {useQuery, useMutation, useQueryClient} from '@tanstack/react-query';
import {AuthGuard} from '@/components/AuthGuard';
import {QueryProvider} from '@/components/QueryProvider';
import {AdminShell} from '@/components/admin/AdminShell';
import {apiClient} from '@/lib/api/base-client';
import {
  Save, Settings, Home, Menu, FileText, Shield, Plus, Trash2, X,
  Edit3, Check, AlertTriangle, Loader, ExternalLink, ChevronDown,
  Globe, Mail, Search, Image,
} from 'lucide-react';

// ─── Types ────────────────────────────────────────────
interface Menu {id: number; name: string; slug: string; description: string; is_active: boolean; created_at?: string; updated_at?: string;}
interface MenuItem {id: number; title: string; url: string; target: string; parent_id: number | null; order_index: number; is_active?: boolean; created_at?: string;}
interface Page {id: number; title: string; slug: string; content: string; excerpt: string; template: string; status: number; parent_id: number | null; order_index: number; meta_title?: string; meta_description?: string; meta_keywords?: string; created_at?: string;}

const TABS = [
  {key: 'basic', label: '基本设置', icon: Settings},
  {key: 'home', label: '首页配置', icon: Home},
  {key: 'system', label: '系统选项', icon: Shield},
  {key: 'menus', label: '菜单管理', icon: Menu},
  {key: 'pages', label: '页面管理', icon: FileText},
];

// ─── Settings field registry ──────────────────────────
interface FieldDef {key: string; label: string; type?: string; placeholder?: string; category: string; options?: {label:string;value:string}[]; rows?: number;}
const SETTINGS_FIELDS: FieldDef[] = [
  // basic
  {key:'site_title', label:'站点标题', category:'basic', placeholder:'FastBlog'},
  {key:'site_description', label:'站点描述', category:'basic', type:'textarea', rows:2, placeholder:'一个快速的博客系统'},
  {key:'site_domain', label:'站点域名', category:'basic', placeholder:'example.com'},
  {key:'site_img', label:'站点图像URL', category:'basic', placeholder:'https://...'},
  {key:'site_beian', label:'备案号', category:'basic', placeholder:'京ICP备...'},
  {key:'site_keywords', label:'站点关键词', category:'basic', placeholder:'博客, 技术, ...'},
  // home
  {key:'home_hero_title', label:'Hero 标题', category:'home', placeholder:'欢迎来到我的博客'},
  {key:'home_hero_subtitle', label:'Hero 副标题', category:'home', placeholder:'分享知识与见解'},
  {key:'home_hero_cta_text', label:'CTA 按钮文本', category:'home', placeholder:'开始阅读'},
  {key:'home_hero_cta_link', label:'CTA 按钮链接', category:'home', placeholder:'/articles'},
  {key:'home_cta_target', label:'CTA 跳转方式', category:'home', options:[{label:'当前窗口',value:'_self'},{label:'新窗口',value:'_blank'}]},
  {key:'home_hero_background_image', label:'Hero 背景图片', category:'home', placeholder:'https://...'},
  {key:'home_featured_title', label:'精选区域标题', category:'home', placeholder:'精选文章'},
  {key:'home_featured_count', label:'精选文章数量', category:'home', type:'number', placeholder:'6'},
  {key:'home_featured_empty_title', label:'精选区空标题', category:'home', placeholder:'暂无精选'},
  {key:'home_featured_empty_subtitle', label:'精选区空副标题', category:'home', placeholder:'稍后回来'},
  {key:'home_main_title', label:'主内容区标题', category:'home', placeholder:'最新文章'},
  {key:'home_main_filter_buttons', label:'过滤按钮(JSON)', category:'home', placeholder:'["latest","popular"]'},
  {key:'home_main_empty_title', label:'主区空标题', category:'home', placeholder:'暂无文章'},
  {key:'home_main_empty_subtitle', label:'主区空副标题', category:'home', placeholder:'请稍后访问'},
  {key:'home_newsletter_title', label:'订阅区标题', category:'home', placeholder:'订阅更新'},
  {key:'home_newsletter_subtitle', label:'订阅区副标题', category:'home', placeholder:'获取最新文章推送'},
  {key:'home_newsletter_placeholder', label:'订阅输入框占位', category:'home', placeholder:'your@email.com'},
  {key:'home_newsletter_button_text', label:'订阅按钮文本', category:'home', placeholder:'订阅'},
  {key:'home_no_category_msg', label:'无分类消息', category:'home', placeholder:'未分类'},
  {key:'home_unknown_author_msg', label:'未知作者消息', category:'home', placeholder:'未知作者'},
  {key:'home_no_summary_msg', label:'无摘要消息', category:'home', placeholder:'暂无摘要'},
  // system
  {key:'user_registration', label:'允许用户注册', category:'system', type:'select', options:[{label:'开启',value:'true'},{label:'关闭',value:'false'}]},
  {key:'menu_slug', label:'当前使用菜单标识', category:'system', placeholder:'main'},
];

// ─── Form field helper ────────────────────────────────
const FieldInput: React.FC<{field: FieldDef; value: string; onChange: (v: string) => void}> = ({field, value, onChange}) => {
  if (field.type === 'select' && field.options) {
    return (
      <select value={value} onChange={e => onChange(e.target.value)}
        className="w-full px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-sm dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500">
        {field.options.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>
    );
  }
  if (field.type === 'textarea') {
    return (
      <textarea value={value} onChange={e => onChange(e.target.value)} rows={field.rows||3}
        className="w-full px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-sm dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none" placeholder={field.placeholder}/>
    );
  }
  return (
    <input type={field.type||'text'} value={value} onChange={e => onChange(e.target.value)}
      className="w-full px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-sm dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500" placeholder={field.placeholder}/>
  );
};

// ─── Modal ────────────────────────────────────────────
const Modal: React.FC<{open: boolean; onClose: () => void; title: string; children: React.ReactNode}> = ({open, onClose, title, children}) => {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onClick={onClose}>
      <div className="bg-white dark:bg-gray-900 rounded-2xl shadow-2xl w-full max-w-lg max-h-[85vh] overflow-y-auto m-4" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <h2 className="font-semibold text-gray-900 dark:text-white">{title}</h2>
          <button onClick={onClose} className="p-1 text-gray-400 hover:text-gray-600"><X className="w-5 h-5"/></button>
        </div>
        <div className="p-6">{children}</div>
      </div>
    </div>
  );
};

// ─── Main ─────────────────────────────────────────────
function SettingsInner() {
  const qc = useQueryClient();
  const [activeTab, setActiveTab] = useState('basic');
  const [localSettings, setLocalSettings] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);
  const [saveMsg, setSaveMsg] = useState<{type:'ok'|'err'; text:string}|null>(null);

  // ── Load settings ──
  const {data: fullData, isLoading} = useQuery({
    queryKey: ['admin-system-settings'],
    queryFn: async () => {
      const r = await apiClient.get<any>('/system/settings/');
      if (r.success && r.data) {
        const raw = r.data.settings || {};
        // Normalize: convert all values to strings for the form
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

  // ── Save settings ──
  const saveSettings = async () => {
    setSaving(true); setSaveMsg(null);
    try {
      const r = await apiClient.post('/system/settings/', {settings: localSettings, action: 'update_settings'});
      setSaveMsg({type: r.success ? 'ok' : 'err', text: r.success ? '保存成功' : (r.error||'保存失败')});
      if (r.success) qc.invalidateQueries({queryKey:['admin-system-settings']});
    } catch { setSaveMsg({type:'err', text:'网络异常'}); }
    finally { setSaving(false); setTimeout(() => setSaveMsg(null), 3000); }
  };

  const setVal = (key: string, val: string) => setLocalSettings(prev => ({...prev, [key]: val}));

  // ── Menu mutations ──
  const createMenuMut = useMutation({mutationFn:(d:any)=>apiClient.post('/system/settings/menus', d), onSuccess:()=>qc.invalidateQueries({queryKey:['admin-system-settings']})});
  const updateMenuMut = useMutation({mutationFn:({id,...d}:any)=>apiClient.put(`/system/settings/menus/${id}`, d), onSuccess:()=>qc.invalidateQueries({queryKey:['admin-system-settings']})});
  const delMenuMut = useMutation({mutationFn:(id:number)=>apiClient.delete(`/system/settings/menus/${id}`), onSuccess:()=>qc.invalidateQueries({queryKey:['admin-system-settings']})});
  const createMenuItemMut = useMutation({mutationFn:(d:any)=>apiClient.post('/system/settings/menu-items', d), onSuccess:()=>qc.invalidateQueries({queryKey:['admin-system-settings']})});
  const delMenuItemMut = useMutation({mutationFn:(id:number)=>apiClient.delete(`/system/settings/menu-items/${id}`), onSuccess:()=>qc.invalidateQueries({queryKey:['admin-system-settings']})});

  // ── Page mutations ──
  const createPageMut = useMutation({mutationFn:(d:any)=>apiClient.post('/system/settings/pages', d), onSuccess:()=>qc.invalidateQueries({queryKey:['admin-system-settings']})});
  const delPageMut = useMutation({mutationFn:(id:number)=>apiClient.delete(`/system/settings/pages/${id}`), onSuccess:()=>qc.invalidateQueries({queryKey:['admin-system-settings']})});

  // ── Menus dialog state ──
  const [menuModal, setMenuModal] = useState<{mode:'create'|'edit'; menu?: Menu} | null>(null);
  const [menuForm, setMenuForm] = useState({name:'', slug:'', description:''});
  const [itemModal, setItemModal] = useState<{menuId: number|null} | null>(null);
  const [itemForm, setItemForm] = useState({title:'', url:'', menu_id: 0, target:'_self', parent_id: ''});

  // ── Pages dialog state ──
  const [pageModal, setPageModal] = useState<{mode:'create'|'edit'; page?: Page} | null>(null);
  const [pageForm, setPageForm] = useState({title:'', slug:'', content:'', excerpt:'', template:'default', status:'0'});

  // ── Render ──
  const renderTabContent = () => {
    if (isLoading) return <div className="p-12 text-center"><div className="animate-spin w-6 h-6 border-2 border-blue-600 border-t-transparent rounded-full mx-auto"/></div>;

    switch (activeTab) {
      // ── Basic + Home + System (Settings fields) ──
      case 'basic':
      case 'home':
      case 'system': {
        const fields = SETTINGS_FIELDS.filter(f => f.category === activeTab);
        return (
          <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 p-6">
            <div className="flex items-center justify-between mb-6">
              <h3 className="font-semibold text-gray-900 dark:text-white">{TABS.find(t=>t.key===activeTab)?.label}</h3>
              <button onClick={saveSettings} disabled={saving}
                className="inline-flex items-center gap-1.5 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-xl disabled:opacity-50 transition-colors">
                {saving ? <Loader className="w-4 h-4 animate-spin"/> : <Save className="w-4 h-4"/>}
                保存设置
              </button>
            </div>
            {saveMsg && (
              <div className={`mb-4 p-3 rounded-xl text-sm flex items-center gap-2 ${saveMsg.type==='ok' ? 'bg-green-50 text-green-700 dark:bg-green-900/20' : 'bg-red-50 text-red-600 dark:bg-red-900/20'}`}>
                {saveMsg.type==='ok' ? <Check className="w-4 h-4"/> : <AlertTriangle className="w-4 h-4"/>}
                {saveMsg.text}
              </div>
            )}
            <div className="space-y-5">
              {fields.map(f => (
                <div key={f.key}>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">{f.label}</label>
                  <FieldInput field={f} value={settings[f.key] ?? ''} onChange={v => setVal(f.key, v)}/>
                  <p className="text-[10px] text-gray-400 mt-0.5 font-mono">{f.key}</p>
                </div>
              ))}
            </div>
          </div>
        );
      }

      // ── Menus ──
      case 'menus':
        return (
          <div className="space-y-6">
            {/* Menu list */}
            <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 overflow-hidden">
              <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700">
                <h3 className="font-semibold text-gray-900 dark:text-white">导航菜单</h3>
                <button onClick={() => { setMenuForm({name:'', slug:'', description:''}); setMenuModal({mode:'create'}); }}
                  className="inline-flex items-center gap-1 px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded-lg"><Plus className="w-4 h-4"/>新建菜单</button>
              </div>
              {menus.length === 0 ? (
                <div className="p-8 text-center text-sm text-gray-400">暂无菜单</div>
              ) : (
                <div className="divide-y divide-gray-100 dark:divide-gray-800">
                  {menus.map(m => (
                    <div key={m.id} className="px-6 py-4">
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-medium text-gray-900 dark:text-white">{m.name}</span>
                          <span className="text-[10px] text-gray-400 font-mono">{m.slug}</span>
                          {m.is_active && <span className="px-1.5 py-0.5 bg-green-100 text-green-700 text-[10px] rounded font-medium">激活</span>}
                        </div>
                        <div className="flex items-center gap-1">
                          <button onClick={() => { setMenuForm({name:m.name, slug:m.slug, description:m.description}); setMenuModal({mode:'edit', menu:m}); }}
                            className="p-1 text-gray-400 hover:text-blue-600"><Edit3 className="w-4 h-4"/></button>
                          <button onClick={() => { if(confirm('删除菜单「'+m.name+'」？')) delMenuMut.mutate(m.id); }}
                            className="p-1 text-gray-400 hover:text-red-600"><Trash2 className="w-4 h-4"/></button>
                        </div>
                      </div>
                      {/* Menu items for this menu */}
                      {menuItems[String(m.id)]?.length > 0 && (
                        <div className="ml-4 mt-2 space-y-1">
                          {menuItems[String(m.id)].map(item => (
                            <div key={item.id} className="flex items-center justify-between py-1.5 px-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg text-sm">
                              <div className="flex items-center gap-2 min-w-0">
                                <span className="text-gray-700 dark:text-gray-300 truncate">{item.title}</span>
                                <span className="text-[10px] text-gray-400 truncate">{item.url}</span>
                                {item.target === '_blank' && <ExternalLink className="w-3 h-3 text-gray-400 shrink-0"/>}
                              </div>
                              <button onClick={() => { if(confirm('删除菜单项「'+item.title+'」？')) delMenuItemMut.mutate(item.id); }}
                                className="p-0.5 text-gray-400 hover:text-red-600 shrink-0 ml-2"><Trash2 className="w-3.5 h-3.5"/></button>
                            </div>
                          ))}
                        </div>
                      )}
                      <button onClick={() => { setItemForm({title:'', url:'', menu_id:m.id, target:'_self', parent_id:''}); setItemModal({menuId:m.id}); }}
                        className="mt-2 text-xs text-blue-600 hover:underline inline-flex items-center gap-1"><Plus className="w-3 h-3"/>添加菜单项</button>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Menu modal */}
            <Modal open={!!menuModal} onClose={() => setMenuModal(null)}
              title={menuModal?.mode === 'create' ? '新建菜单' : '编辑菜单'}>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">名称</label>
                  <input value={menuForm.name} onChange={e => setMenuForm(p=>({...p,name:e.target.value}))}
                    className="w-full px-3 py-2 border rounded-lg text-sm dark:bg-gray-800 dark:text-white dark:border-gray-700"/>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">标识 (slug)</label>
                  <input value={menuForm.slug} onChange={e => setMenuForm(p=>({...p,slug:e.target.value}))} disabled={menuModal?.mode==='edit'}
                    className="w-full px-3 py-2 border rounded-lg text-sm dark:bg-gray-800 dark:text-white dark:border-gray-700 disabled:opacity-50"/>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">描述</label>
                  <input value={menuForm.description} onChange={e => setMenuForm(p=>({...p,description:e.target.value}))}
                    className="w-full px-3 py-2 border rounded-lg text-sm dark:bg-gray-800 dark:text-white dark:border-gray-700"/>
                </div>
                <div className="flex justify-end gap-3 pt-2">
                  <button onClick={() => setMenuModal(null)} className="px-4 py-2 text-sm border rounded-lg text-gray-600">取消</button>
                  <button onClick={() => {
                    if (menuModal?.mode === 'create') createMenuMut.mutate(menuForm);
                    else if (menuModal?.menu) updateMenuMut.mutate({id: menuModal.menu.id, ...menuForm, is_active: menuModal.menu.is_active});
                    setMenuModal(null);
                  }} className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg">保存</button>
                </div>
              </div>
            </Modal>

            {/* Menu item modal */}
            <Modal open={!!itemModal} onClose={() => setItemModal(null)} title="添加菜单项">
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">标题</label>
                  <input value={itemForm.title} onChange={e => setItemForm(p=>({...p,title:e.target.value}))}
                    className="w-full px-3 py-2 border rounded-lg text-sm dark:bg-gray-800 dark:text-white dark:border-gray-700"/>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">链接 URL</label>
                  <input value={itemForm.url} onChange={e => setItemForm(p=>({...p,url:e.target.value}))}
                    className="w-full px-3 py-2 border rounded-lg text-sm dark:bg-gray-800 dark:text-white dark:border-gray-700" placeholder="/articles"/>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">打开方式</label>
                    <select value={itemForm.target} onChange={e => setItemForm(p=>({...p,target:e.target.value}))}
                      className="w-full px-3 py-2 border rounded-lg text-sm dark:bg-gray-800 dark:text-white dark:border-gray-700">
                      <option value="_self">当前窗口</option>
                      <option value="_blank">新窗口</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">父级 ID</label>
                    <input value={itemForm.parent_id} onChange={e => setItemForm(p=>({...p,parent_id:e.target.value}))}
                      className="w-full px-3 py-2 border rounded-lg text-sm dark:bg-gray-800 dark:text-white dark:border-gray-700" placeholder="留空=顶级"/>
                  </div>
                </div>
                <div className="flex justify-end gap-3 pt-2">
                  <button onClick={() => setItemModal(null)} className="px-4 py-2 text-sm border rounded-lg text-gray-600">取消</button>
                  <button onClick={() => {
                    createMenuItemMut.mutate({
                      title: itemForm.title,
                      url: itemForm.url,
                      menu_id: itemForm.menu_id,
                      target: itemForm.target,
                      parent_id: itemForm.parent_id ? parseInt(itemForm.parent_id) : undefined,
                    });
                    setItemModal(null);
                  }} className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg">添加</button>
                </div>
              </div>
            </Modal>
          </div>
        );

      // ── Pages ──
      case 'pages':
        return (
          <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 overflow-hidden">
            <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700">
              <h3 className="font-semibold text-gray-900 dark:text-white">独立页面</h3>
              <button onClick={() => { setPageForm({title:'', slug:'', content:'', excerpt:'', template:'default', status:'0'}); setPageModal({mode:'create'}); }}
                className="inline-flex items-center gap-1 px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded-lg"><Plus className="w-4 h-4"/>新建页面</button>
            </div>
            {pages.length === 0 ? (
              <div className="p-8 text-center text-sm text-gray-400">暂无页面</div>
            ) : (
              <table className="w-full"><thead className="bg-gray-50 dark:bg-gray-800 border-b"><tr>
                <th className="px-5 py-3 text-xs font-semibold text-gray-500 uppercase text-left">标题</th>
                <th className="px-5 py-3 text-xs font-semibold text-gray-500 uppercase text-left hidden sm:table-cell">别名</th>
                <th className="px-5 py-3 text-xs font-semibold text-gray-500 uppercase text-left hidden lg:table-cell">模板</th>
                <th className="px-5 py-3 text-xs font-semibold text-gray-500 uppercase text-right">操作</th>
              </tr></thead><tbody className="divide-y divide-gray-100 dark:divide-gray-800">
                {pages.map(p => (
                  <tr key={p.id} className="hover:bg-gray-50 dark:hover:bg-gray-800/50">
                    <td className="px-5 py-4"><span className="text-sm font-medium text-gray-900 dark:text-white">{p.title}</span></td>
                    <td className="px-5 py-4 text-sm text-gray-500 font-mono hidden sm:table-cell">{p.slug}</td>
                    <td className="px-5 py-4 text-sm text-gray-500 hidden lg:table-cell">{p.template}</td>
                    <td className="px-5 py-4 text-right">
                      <button onClick={() => { if(confirm('删除页面「'+p.title+'」？')) delPageMut.mutate(p.id); }}
                        className="p-1.5 text-gray-400 hover:text-red-600"><Trash2 className="w-4 h-4"/></button>
                    </td>
                  </tr>
                ))}
              </tbody></table>
            )}

            <Modal open={!!pageModal} onClose={() => setPageModal(null)}
              title={pageModal?.mode === 'create' ? '新建页面' : '编辑页面'}>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">标题</label>
                  <input value={pageForm.title} onChange={e => setPageForm(p=>({...p,title:e.target.value}))}
                    className="w-full px-3 py-2 border rounded-lg text-sm dark:bg-gray-800 dark:text-white dark:border-gray-700"/>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">别名 (slug)</label>
                  <input value={pageForm.slug} onChange={e => setPageForm(p=>({...p,slug:e.target.value}))}
                    className="w-full px-3 py-2 border rounded-lg text-sm dark:bg-gray-800 dark:text-white dark:border-gray-700" placeholder="about"/>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">摘要</label>
                  <input value={pageForm.excerpt} onChange={e => setPageForm(p=>({...p,excerpt:e.target.value}))}
                    className="w-full px-3 py-2 border rounded-lg text-sm dark:bg-gray-800 dark:text-white dark:border-gray-700"/>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">模板</label>
                  <select value={pageForm.template} onChange={e => setPageForm(p=>({...p,template:e.target.value}))}
                    className="w-full px-3 py-2 border rounded-lg text-sm dark:bg-gray-800 dark:text-white dark:border-gray-700">
                    <option value="default">默认</option>
                    <option value="full-width">全宽</option>
                    <option value="sidebar">侧边栏</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">内容 (Markdown)</label>
                  <textarea value={pageForm.content} onChange={e => setPageForm(p=>({...p,content:e.target.value}))} rows={6}
                    className="w-full px-3 py-2 border rounded-lg text-sm font-mono dark:bg-gray-800 dark:text-white dark:border-gray-700 resize-none"/>
                </div>
                <div className="flex justify-end gap-3 pt-2">
                  <button onClick={() => setPageModal(null)} className="px-4 py-2 text-sm border rounded-lg text-gray-600">取消</button>
                  <button onClick={() => {
                    createPageMut.mutate(pageForm);
                    setPageModal(null);
                  }} className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg">创建</button>
                </div>
              </div>
            </Modal>
          </div>
        );
    }
  };

  return (
    <AdminShell title="系统设置">
      {/* ═══ Tabs ═══ */}
      <div className="flex gap-1 mb-6 overflow-x-auto pb-1">
        {TABS.map(t => {
          const Icon = t.icon;
          return (
            <button key={t.key} onClick={() => setActiveTab(t.key)}
              className={`flex items-center gap-1.5 px-4 py-2 text-sm font-medium rounded-xl whitespace-nowrap transition-colors
                ${activeTab === t.key ? 'bg-blue-600 text-white' : 'bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800'}`}>
              <Icon className="w-4 h-4"/>{t.label}
            </button>
          );
        })}
      </div>

      {renderTabContent()}
    </AdminShell>
  );
}

export default function AdminSettings() {
  return <AuthGuard><QueryProvider><SettingsInner/></QueryProvider></AuthGuard>;
}
