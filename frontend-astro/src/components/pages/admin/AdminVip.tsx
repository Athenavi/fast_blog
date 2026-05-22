'use client';

import React, {useState} from 'react';
import {useQuery, useMutation, useQueryClient} from '@tanstack/react-query';
import {AuthGuard} from '@/components/AuthGuard';
import {QueryProvider} from '@/components/QueryProvider';
import {AdminShell} from '@/components/admin/AdminShell';
import {apiClient} from '@/lib/api';
import {
  Crown, Users, TrendingUp, DollarSign, Search,
  Plus, Edit3, Trash2, X, Check, ChevronDown,
  Package, Shield, UserCheck, AlertCircle,
} from 'lucide-react';

// ─── Types ────────────────────────────────────────────
interface VIPPlan {
  id: number; name: string; description?: string;
  price: number; original_price?: number; duration_days: number;
  level: number; features?: string; is_active: boolean;
  created_at?: string; updated_at?: string;
}
interface VIPFeature {
  id: number; code: string; name: string; description?: string;
  required_level: number; is_active: boolean; created_at?: string;
}
interface Member {
  id: number; user_id: number; username: string;
  plan_name: string; level: number;
  starts_at?: string; expires_at?: string;
  is_active: boolean; amount: number;
  transaction_id?: string; status: string;
}
interface VipMgmtData {
  stats: Record<string,any>;
  members: Member[];
  plans: VIPPlan[];
  features: VIPFeature[];
}
interface PlanForm { name: string; description: string; price: string; original_price: string; duration_days: string; level: string; features: string; }
interface FeatureForm { code: string; name: string; description: string; required_level: string; }

// ─── Modal ────────────────────────────────────────────
const Modal: React.FC<{open:boolean;title:string;onClose:()=>void;children:React.ReactNode}> = ({open,title,onClose,children}) => {
  if(!open) return null;
  return <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onClick={onClose}>
    <div className="bg-white dark:bg-gray-900 rounded-2xl shadow-2xl border border-gray-200 dark:border-gray-700 w-full max-w-lg mx-4 max-h-[90vh] overflow-y-auto" onClick={e=>e.stopPropagation()}>
      <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100 dark:border-gray-800">
        <h3 className="font-bold text-gray-900 dark:text-white">{title}</h3>
        <button onClick={onClose} className="p-1 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800"><X className="w-4 h-4 text-gray-500"/></button>
      </div>
      <div className="px-6 py-4">{children}</div>
    </div>
  </div>;
};

// ─── Input helpers ────────────────────────────────────
const Inp: React.FC<{label:string;value:string;onChange:(v:string)=>void;type?:string;placeholder?:string;className?:string;rows?:number}> = ({label,value,onChange,type,placeholder,className,rows}) => (
  <div className={`mb-3 ${className||''}`}>
    <label className="block text-xs font-semibold text-gray-500 mb-1">{label}</label>
    {rows ? (
      <textarea rows={rows} value={value} onChange={e=>onChange(e.target.value)} placeholder={placeholder}
        className="w-full px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white placeholder-gray-400 resize-none"/>
    ) : (
      <input type={type||'text'} value={value} onChange={e=>onChange(e.target.value)} placeholder={placeholder}
        className="w-full px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white placeholder-gray-400"/>
    )}
  </div>
);

// ─── Plans Tab ────────────────────────────────────────
const PlansTab: React.FC<{plans:VIPPlan[];onChanged:()=>void}> = ({plans,onChanged}) => {
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<VIPPlan|null>(null);
  const [f, setF] = useState<PlanForm>({name:'',description:'',price:'',original_price:'',duration_days:'30',level:'1',features:'[]'});

  const openCreate = () => { setEditing(null); setF({name:'',description:'',price:'',original_price:'',duration_days:'30',level:'1',features:'[]'}); setShowForm(true); };
  const openEdit = (p:VIPPlan) => { setEditing(p); setF({name:p.name,description:p.description||'',price:String(p.price),original_price:p.original_price?String(p.original_price):'',duration_days:String(p.duration_days),level:String(p.level),features:p.features||'[]'}); setShowForm(true); };

  const createMut = useMutation({
    mutationFn: (d:PlanForm)=>apiClient.post('/dashboard/vip/plans',d),
    onSuccess: (r)=>{if(r.success){qc.invalidateQueries({queryKey:['admin-vip']});setShowForm(false);onChanged();}else if(r.error)alert(r.error);},
  });
  const updateMut = useMutation({
    mutationFn: (d:{id:number;form:PlanForm})=>apiClient.put(`/dashboard/vip/plans/${d.id}`,d.form),
    onSuccess: (r)=>{if(r.success){qc.invalidateQueries({queryKey:['admin-vip']});setShowForm(false);onChanged();}else if(r.error)alert(r.error);},
  });
  const deleteMut = useMutation({
    mutationFn: (id:number)=>apiClient.delete(`/dashboard/vip/plans/${id}`),
    onSuccess: (r)=>{if(r.success){qc.invalidateQueries({queryKey:['admin-vip']});onChanged();}else if(r.error)alert(r.error);},
  });
  const toggleMut = useMutation({
    mutationFn: (p:VIPPlan)=>apiClient.put(`/dashboard/vip/plans/${p.id}`,{is_active:p.is_active?'0':'1',name:p.name,price:String(p.price),duration_days:String(p.duration_days),level:String(p.level)}),
    onSuccess: ()=>{qc.invalidateQueries({queryKey:['admin-vip']});onChanged();},
  });

  const submitPlan = () => {
    if(!f.name.trim()) return alert('请输入套餐名称');
    if(editing) updateMut.mutate({id:editing.id,form:f});
    else createMut.mutate(f);
  };

  return <>
    <div className="flex items-center justify-between mb-4">
      <h3 className="text-lg font-bold text-gray-900 dark:text-white flex items-center gap-2"><Package className="w-5 h-5"/>套餐管理</h3>
      <button onClick={openCreate} className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded-xl flex items-center gap-1.5"><Plus className="w-4 h-4"/>新建套餐</button>
    </div>
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {plans.map(p => (
        <div key={p.id} className={`rounded-2xl border p-5 relative ${p.is_active ? 'bg-white dark:bg-gray-900 border-gray-200 dark:border-gray-700' : 'bg-gray-50 dark:bg-gray-800/50 border-gray-200 dark:border-gray-700 opacity-75'}`}>
          <div className="flex items-start justify-between mb-3">
            <div>
              <h4 className="font-bold text-gray-900 dark:text-white">{p.name}</h4>
              {p.description && <p className="text-xs text-gray-500 mt-0.5">{p.description}</p>}
            </div>
            {!p.is_active && <span className="px-2 py-0.5 text-[10px] rounded-full bg-gray-200 dark:bg-gray-700 text-gray-500">已禁用</span>}
          </div>
          <div className="flex items-baseline gap-1 mb-3">
            <span className="text-2xl font-bold text-gray-900 dark:text-white">¥{p.price}</span>
            {p.original_price && p.original_price > p.price && <span className="text-xs text-gray-400 line-through">¥{p.original_price}</span>}
            <span className="text-xs text-gray-400 ml-auto">/{p.duration_days}天</span>
          </div>
          <div className="flex items-center gap-2 text-xs text-gray-500 mb-3">
            <Crown className="w-3.5 h-3.5"/>Lv.{p.level}
          </div>
          <div className="flex gap-1.5 mt-3 pt-3 border-t border-gray-100 dark:border-gray-800">
            <button onClick={()=>openEdit(p)} className="flex-1 px-3 py-1.5 text-xs border border-gray-200 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 text-gray-600 dark:text-gray-300 flex items-center justify-center gap-1"><Edit3 className="w-3 h-3"/>编辑</button>
            <button onClick={()=>toggleMut.mutate(p)} className={`flex-1 px-3 py-1.5 text-xs border rounded-lg flex items-center justify-center gap-1 ${p.is_active ? 'border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800' : 'border-green-200 text-green-700 hover:bg-green-50'}`}>
              <Check className="w-3 h-3"/>{p.is_active ? '禁用' : '启用'}
            </button>
            <button onClick={()=>{if(confirm(`确定删除「${p.name}」？`))deleteMut.mutate(p.id);}} className="px-3 py-1.5 text-xs border border-red-200 dark:border-red-900/30 rounded-lg text-red-500 hover:bg-red-50 dark:hover:bg-red-900/10 flex items-center justify-center gap-1"><Trash2 className="w-3 h-3"/></button>
          </div>
        </div>
      ))}
    </div>

    <Modal open={showForm} title={editing?'编辑套餐':'新建套餐'} onClose={()=>setShowForm(false)}>
      <Inp label="套餐名称 *" value={f.name} onChange={v=>setF({...f,name:v})} placeholder="例如：月度会员" />
      <Inp label="描述" value={f.description} onChange={v=>setF({...f,description:v})} placeholder="套餐简介" rows={2} />
      <div className="flex gap-3">
        <Inp label="价格 *" value={f.price} onChange={v=>setF({...f,price:v})} type="number" placeholder="29.99" className="flex-1" />
        <Inp label="原价" value={f.original_price} onChange={v=>setF({...f,original_price:v})} type="number" placeholder="49.99" className="flex-1" />
      </div>
      <div className="flex gap-3">
        <Inp label="有效期(天) *" value={f.duration_days} onChange={v=>setF({...f,duration_days:v})} type="number" placeholder="30" className="flex-1" />
        <Inp label="VIP 等级" value={f.level} onChange={v=>setF({...f,level:v})} type="number" placeholder="1" className="flex-1" />
      </div>
      <Inp label="功能配置 (JSON)" value={f.features} onChange={v=>setF({...f,features:v})} rows={2} placeholder='["无广告","专属标识"]' />
      <button onClick={submitPlan} className="w-full mt-2 px-4 py-2.5 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded-xl font-medium">{editing?'保存修改':'创建套餐'}</button>
    </Modal>
  </>;
};

// ─── Features Tab ─────────────────────────────────────
const FeaturesTab: React.FC<{features:VIPFeature[];onChanged:()=>void}> = ({features,onChanged}) => {
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<VIPFeature|null>(null);
  const [f, setF] = useState<FeatureForm>({code:'',name:'',description:'',required_level:'1'});

  const openCreate = () => { setEditing(null); setF({code:'',name:'',description:'',required_level:'1'}); setShowForm(true); };
  const openEdit = (fe:VIPFeature) => { setEditing(fe); setF({code:fe.code,name:fe.name,description:fe.description||'',required_level:String(fe.required_level)}); setShowForm(true); };

  const createMut = useMutation({
    mutationFn: (d:FeatureForm)=>apiClient.post('/dashboard/vip/features',d),
    onSuccess: (r)=>{if(r.success){qc.invalidateQueries({queryKey:['admin-vip']});setShowForm(false);onChanged();}else if(r.error)alert(r.error);},
  });
  const updateMut = useMutation({
    mutationFn: (d:{id:number;form:FeatureForm})=>apiClient.put(`/dashboard/vip/features/${d.id}`,d.form),
    onSuccess: (r)=>{if(r.success){qc.invalidateQueries({queryKey:['admin-vip']});setShowForm(false);onChanged();}else if(r.error)alert(r.error);},
  });
  const deleteMut = useMutation({
    mutationFn: (id:number)=>apiClient.delete(`/dashboard/vip/features/${id}`),
    onSuccess: (r)=>{if(r.success){qc.invalidateQueries({queryKey:['admin-vip']});onChanged();}else if(r.error)alert(r.error);},
  });
  const toggleMut = useMutation({
    mutationFn: (fe:VIPFeature)=>apiClient.put(`/dashboard/vip/features/${fe.id}`,{is_active:fe.is_active?'0':'1',code:fe.code,name:fe.name,required_level:String(fe.required_level)}),
    onSuccess: ()=>{qc.invalidateQueries({queryKey:['admin-vip']});onChanged();},
  });

  const submitFeature = () => {
    if(!f.code.trim()||!f.name.trim()) return alert('请填写功能代码和名称');
    if(editing) updateMut.mutate({id:editing.id,form:f});
    else createMut.mutate(f);
  };

  return <>
    <div className="flex items-center justify-between mb-4">
      <h3 className="text-lg font-bold text-gray-900 dark:text-white flex items-center gap-2"><Shield className="w-5 h-5"/>功能管理</h3>
      <button onClick={openCreate} className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded-xl flex items-center gap-1.5"><Plus className="w-4 h-4"/>新建功能</button>
    </div>
    <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 overflow-hidden">
      <table className="w-full"><thead className="bg-gray-50 dark:bg-gray-800 border-b">
        <tr><th className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase">代码</th><th className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase">名称</th><th className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase hidden sm:table-cell">描述</th><th className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase">等级</th><th className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase">状态</th><th className="px-5 py-3 text-right text-xs font-semibold text-gray-500 uppercase">操作</th></tr>
      </thead><tbody className="divide-y">
        {features.map(fe => (
          <tr key={fe.id} className="hover:bg-gray-50 dark:hover:bg-gray-800/50">
            <td className="px-5 py-3 text-sm font-mono text-gray-700 dark:text-gray-300">{fe.code}</td>
            <td className="px-5 py-3 text-sm font-medium text-gray-900 dark:text-white">{fe.name}</td>
            <td className="px-5 py-3 text-sm text-gray-500 hidden sm:table-cell">{fe.description||'-'}</td>
            <td className="px-5 py-3 text-sm"><span className="px-2 py-0.5 text-xs rounded-full bg-purple-100 dark:bg-purple-900/20 text-purple-700">Lv.{fe.required_level}</span></td>
            <td className="px-5 py-3"><span className={`px-2 py-0.5 text-xs rounded-full ${fe.is_active?'bg-green-100 text-green-700':'bg-gray-100 text-gray-500'}`}>{fe.is_active?'启用':'禁用'}</span></td>
            <td className="px-5 py-3 text-right">
              <button onClick={()=>openEdit(fe)} className="p-1.5 text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded-lg" title="编辑"><Edit3 className="w-3.5 h-3.5"/></button>
              <button onClick={()=>toggleMut.mutate(fe)} className="p-1.5 text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg" title={fe.is_active?'禁用':'启用'}><Check className="w-3.5 h-3.5"/></button>
              <button onClick={()=>{if(confirm(`确定删除「${fe.name}」？`))deleteMut.mutate(fe.id);}} className="p-1.5 text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg" title="删除"><Trash2 className="w-3.5 h-3.5"/></button>
            </td>
          </tr>
        ))}
      </tbody></table>
    </div>

    <Modal open={showForm} title={editing?'编辑功能':'新建功能'} onClose={()=>setShowForm(false)}>
      <Inp label="功能代码 *" value={f.code} onChange={v=>setF({...f,code:v})} placeholder="no_ads" />
      <Inp label="功能名称 *" value={f.name} onChange={v=>setF({...f,name:v})} placeholder="无广告" />
      <Inp label="描述" value={f.description} onChange={v=>setF({...f,description:v})} placeholder="浏览时无广告干扰" rows={2} />
      <Inp label="所需 VIP 等级" value={f.required_level} onChange={v=>setF({...f,required_level:v})} type="number" placeholder="1" />
      <button onClick={submitFeature} className="w-full mt-2 px-4 py-2.5 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded-xl font-medium">{editing?'保存修改':'创建功能'}</button>
    </Modal>
  </>;
};

// ─── Members Tab ──────────────────────────────────────
const MembersTab: React.FC<{members:Member[];stats:Record<string,any>}> = ({members,stats}) => {
  const [search, setSearch] = useState('');
  const filtered = members.filter(m=>!search||m.username.includes(search));

  return <>
    {/* Stats */}
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
      <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 p-5"><div className="flex items-center gap-2 text-sm text-gray-500 mb-1"><Crown className="w-4 h-4"/>VIP 总数</div><p className="text-2xl font-bold">{stats.total_vip_count??'—'}</p></div>
      <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 p-5"><div className="flex items-center gap-2 text-sm text-gray-500 mb-1"><Users className="w-4 h-4"/>本月新增</div><p className="text-2xl font-bold">{stats.monthly_new??'—'}</p></div>
      <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 p-5"><div className="flex items-center gap-2 text-sm text-gray-500 mb-1"><DollarSign className="w-4 h-4"/>月收入</div><p className="text-2xl font-bold">{stats.monthly_revenue??'—'}</p></div>
      <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 p-5"><div className="flex items-center gap-2 text-sm text-gray-500 mb-1"><TrendingUp className="w-4 h-4"/>续费率</div><p className="text-2xl font-bold">{stats.renewal_rate?`${stats.renewal_rate}%`:'—'}</p></div>
    </div>

    {/* Search */}
    <div className="relative mb-4"><Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400"/><input type="text" value={search} onChange={e=>setSearch(e.target.value)} placeholder="搜索会员..." className="w-full pl-10 pr-4 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl bg-white dark:bg-gray-900 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white"/></div>

    {/* Table */}
    <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 overflow-hidden">
      {!filtered.length ? (
        <div className="p-12 text-center text-gray-400"><Crown className="w-10 h-10 mx-auto mb-3 opacity-40"/><p>暂无 VIP 会员</p></div>
      ) : (
        <table className="w-full"><thead className="bg-gray-50 dark:bg-gray-800 border-b">
          <tr><th className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase">用户</th><th className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase hidden sm:table-cell">套餐</th><th className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase hidden md:table-cell">到期</th><th className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase">状态</th><th className="px-5 py-3 text-right text-xs font-semibold text-gray-500 uppercase hidden lg:table-cell">金额</th></tr>
        </thead><tbody className="divide-y">
          {filtered.map(m => (
            <tr key={m.id} className="hover:bg-gray-50 dark:hover:bg-gray-800/50">
              <td className="px-5 py-4"><div className="flex items-center gap-3"><div className="w-8 h-8 rounded-full bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center text-white text-xs font-bold">{m.username?.charAt(0)||'?'}</div><span className="font-medium text-sm text-gray-900 dark:text-white">{m.username}</span></div></td>
              <td className="px-5 py-4 text-sm hidden sm:table-cell">
                <span className="px-2 py-0.5 text-xs rounded-full bg-purple-100 dark:bg-purple-900/20 text-purple-700">{m.plan_name}</span>
              </td>
              <td className="px-5 py-4 text-sm text-gray-500 hidden md:table-cell">{m.expires_at?new Date(m.expires_at).toLocaleDateString('zh-CN'):'-'}</td>
              <td className="px-5 py-4"><span className={`px-2 py-0.5 text-xs rounded-full ${m.is_active?'bg-green-100 text-green-700':'bg-red-100 text-red-700'}`}>{m.is_active?'有效':'过期'}</span></td>
              <td className="px-5 py-4 text-sm text-gray-500 text-right hidden lg:table-cell">¥{m.amount.toFixed(2)}</td>
            </tr>
          ))}
        </tbody></table>
      )}
    </div>
  </>;
};

// ─── Main Component ───────────────────────────────────
type Tab = 'plans'|'features'|'members';

function VipAdminInner() {
  const [tab, setTab] = useState<Tab>('members');
  const {data: mgmt, isLoading, refetch} = useQuery({
    queryKey: ['admin-vip'],
    queryFn: async () => {
      const r = await apiClient.get<any>('/dashboard/vip-management');
      return (r.success && r.data) ? (r.data as VipMgmtData) : {stats:{},members:[],plans:[],features:[]};
    },
  });
  const stats = mgmt?.stats || {};
  const members = mgmt?.members || [];
  const plans = mgmt?.plans || [];
  const features = mgmt?.features || [];

  const tabs: {key:Tab;label:string;icon:any;count?:number}[] = [
    {key:'members', label:'会员管理', icon:UserCheck, count:members.length},
    {key:'plans', label:'套餐管理', icon:Package, count:plans.length},
    {key:'features', label:'功能管理', icon:Shield, count:features.length},
  ];

  return (
    <AdminShell title="VIP 管理">
      {/* Tabs */}
      <div className="flex gap-1 mb-6 bg-gray-100 dark:bg-gray-800 rounded-xl p-1">
        {tabs.map(t => (
          <button key={t.key} onClick={()=>setTab(t.key)}
            className={`flex items-center gap-1.5 px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
              tab===t.key
                ? 'bg-white dark:bg-gray-900 text-gray-900 dark:text-white shadow-sm'
                : 'text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'
            }`}>
            <t.icon className="w-4 h-4"/>{t.label}
            {t.count!==undefined && <span className="text-xs text-gray-400 ml-0.5">({t.count})</span>}
          </button>
        ))}
      </div>

      {isLoading ? (
        <div className="p-12 text-center"><div className="animate-spin w-6 h-6 border-2 border-blue-600 border-t-transparent rounded-full mx-auto"/></div>
      ) : (
        <>
          {tab==='members' && <MembersTab members={members} stats={stats} />}
          {tab==='plans' && <PlansTab plans={plans} onChanged={()=>refetch()} />}
          {tab==='features' && <FeaturesTab features={features} onChanged={()=>refetch()} />}
        </>
      )}
    </AdminShell>
  );
}

export default function AdminVip() { return <AuthGuard><QueryProvider><VipAdminInner /></QueryProvider></AuthGuard>; }
