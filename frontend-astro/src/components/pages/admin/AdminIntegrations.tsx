'use client';

import React, {useCallback, useRef, useState} from 'react';
import {useMutation, useQuery, useQueryClient} from '@tanstack/react-query';
import {AuthGuard} from '@/components/AuthGuard';
import {QueryProvider} from '@/components/QueryProvider';
import {AdminShell} from '@/components/admin/AdminShell';
import {EmptyState, Modal, SectionTitle, StatCard, StatusBadge} from '@/components/admin/shared-ui';
import {apiClient} from '@/lib/api/api-client';
import {
  Activity,
  AlertCircle,
  ArrowRight,
  BarChart3,
  Check,
  CheckCircle,
  CloudUpload,
  Copy,
  Database,
  Edit3,
  Eye,
  FileText,
  FileUp,
  Globe,
  HardDrive,
  Key,
  Link,
  Loader,
  Pin,
  PinOff,
  Plus,
  Save,
  Server,
  Shield,
  Trash2,
  Unlink,
  Upload,
  X,
  XCircle
} from 'lucide-react';

/* ═══════════════════════════════════════════
   Types
   ═══════════════════════════════════════════ */
interface OAuthProvider {
  name: string;
  display_name?: string;
  configured?: boolean;
  icon?: string;
  client_id?: string;
  redirect_uri?: string;
}

interface LinkedAccount {
  provider: string;
  provider_name?: string;
  provider_user_id?: string;
  email?: string;
  username?: string;
  bound_at?: string;
}

interface GAConfig {
  id?: number;
  tracking_id?: string;
  measurement_id?: string;
  api_secret?: string;
  enable_page_view_tracking?: boolean;
  enable_event_tracking?: boolean;
  enable_user_behavior_analysis?: boolean;
  anonymize_ip?: boolean;
  sample_rate?: number;
  is_active?: boolean;
}

interface BaiduConfig {
  id?: number;
  site_token?: string;
  api_key?: string;
  site_id?: number;
  site_name?: string;
  tracking_id?: string;
  enable_tracking?: boolean;
  enable_data_sync?: boolean;
  is_active?: boolean;
}

interface IPFSFile {
  cid: string;
  name?: string;
  filename?: string;
  size?: number;
  content_type?: string;
  gateway_url?: string;
  pinned?: boolean;
  created_at?: string;
}

/* ═══════════════════════════════════════════
   Constants
   ═══════════════════════════════════════════ */
const TABS = [
  {key: 'oauth', label: 'OAuth 登录', icon: Globe, color: 'from-blue-500 to-indigo-500'},
  {key: 'sso', label: 'SSO 企业认证', icon: Shield, color: 'from-emerald-500 to-teal-500'},
  {key: 'analytics', label: '统计分析', icon: BarChart3, color: 'from-orange-500 to-amber-500'},
  {key: 'ipfs', label: 'IPFS 存储', icon: Database, color: 'from-purple-500 to-violet-500'},
  {key: 'import', label: '数据导入', icon: Upload, color: 'from-pink-500 to-rose-500'},
];

const PROVIDER_COLORS: Record<string, { bg: string; text: string }> = {
  github: {bg: 'bg-gray-900', text: 'text-white'},
  google: {bg: 'bg-blue-500', text: 'text-white'},
  wechat: {bg: 'bg-green-500', text: 'text-white'},
  qq: {bg: 'bg-blue-400', text: 'text-white'},
  microsoft: {bg: 'bg-blue-700', text: 'text-white'},
  weibo: {bg: 'bg-red-500', text: 'text-white'},
};

/* ═══════════════════════════════════════════
   Helper Components
   ═══════════════════════════════════════════ */
const ProviderAvatar: React.FC<{ name: string; icon?: string; size?: 'sm' | 'md' | 'lg' }> = ({
                                                                                                name,
                                                                                                icon,
                                                                                                size = 'md'
                                                                                              }) => {
  const sz = size === 'sm' ? 'w-7 h-7 text-[10px]' : size === 'lg' ? 'w-11 h-11 text-sm' : 'w-9 h-9 text-xs';
  const colors = PROVIDER_COLORS[(icon || name || '').toLowerCase()];
  const bg = colors?.bg || 'bg-gradient-to-br from-blue-100 to-indigo-100 dark:from-blue-900/30 dark:to-indigo-900/30';
  const fg = colors?.text || 'text-blue-600 dark:text-blue-400';
  const label = (icon || name || '?').charAt(0).toUpperCase();
  return <div
    className={`${sz} rounded-xl ${bg} ${fg} flex items-center justify-center font-bold shrink-0`}>{label}</div>;
};

const Toggle: React.FC<{ checked: boolean; onChange: (v: boolean) => void; disabled?: boolean }> = ({
                                                                                                      checked,
                                                                                                      onChange,
                                                                                                      disabled
                                                                                                    }) => (
  <button type="button" disabled={disabled} onClick={() => onChange(!checked)}
          className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${checked ? 'bg-blue-600' : 'bg-gray-200 dark:bg-gray-700'} ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}>
    <span
      className={`inline-block h-4 w-4 transform rounded-full bg-white shadow transition-transform ${checked ? 'translate-x-6' : 'translate-x-1'}`}/>
  </button>
);

const InputField: React.FC<{
  label: string;
  value: string;
  onChange: (v: string) => void;
  type?: string;
  placeholder?: string;
  hint?: string;
  disabled?: boolean
}> =
  ({label, value, onChange, type = 'text', placeholder, hint, disabled}) => (
    <div>
      <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1.5">{label}</label>
      <input type={type} value={value} onChange={e => onChange(e.target.value)} placeholder={placeholder}
             disabled={disabled}
             className="w-full px-3 py-2 text-sm border border-gray-200 dark:border-gray-700 rounded-xl bg-white dark:bg-gray-800 text-gray-900 dark:text-white placeholder:text-gray-400 focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 outline-none transition-all disabled:opacity-50"/>
      {hint && <p className="text-[11px] text-gray-400 mt-1">{hint}</p>}
    </div>
  );

const ActionButton: React.FC<{
  onClick: () => void;
  icon: any;
  label: string;
  variant?: 'primary' | 'danger' | 'ghost';
  loading?: boolean;
  disabled?: boolean;
  size?: 'sm' | 'md'
}> =
  ({onClick, icon: Icon, label, variant = 'primary', loading, disabled, size = 'md'}) => {
    const base = size === 'sm' ? 'px-2.5 py-1.5 text-xs gap-1' : 'px-4 py-2 text-sm gap-1.5';
    const colors = variant === 'primary' ? 'bg-blue-600 hover:bg-blue-700 text-white' :
      variant === 'danger' ? 'bg-red-600 hover:bg-red-700 text-white' :
        'bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300';
    return (
      <button onClick={onClick} disabled={disabled || loading}
              className={`${base} inline-flex items-center font-medium rounded-xl transition-colors ${colors} disabled:opacity-50`}>
        {loading ? <Loader className="w-3.5 h-3.5 animate-spin"/> : <Icon className="w-3.5 h-3.5"/>}
        {label}
      </button>
    );
  };

const Toast: React.FC<{ message: string; type: 'success' | 'error' | 'info'; onClose: () => void }> = ({
                                                                                                         message,
                                                                                                         type,
                                                                                                         onClose
                                                                                                       }) => {
  const colorMap = {
    success: 'bg-green-50 border-green-200 text-green-800',
    error: 'bg-red-50 border-red-200 text-red-800',
    info: 'bg-blue-50 border-blue-200 text-blue-800'
  };
  const iconMap = {success: CheckCircle, error: XCircle, info: AlertCircle};
  const Icon = iconMap[type];
  return (
    <div
      className={`fixed top-4 right-4 z-[100] flex items-center gap-2 px-4 py-3 rounded-xl border shadow-lg animate-in slide-in-from-right ${colorMap[type]}`}>
      <Icon className="w-4 h-4 shrink-0"/>
      <span className="text-sm font-medium">{message}</span>
      <button onClick={onClose} className="ml-2 p-0.5 hover:opacity-70"><X className="w-3.5 h-3.5"/></button>
    </div>
  );
};

/* ═══════════════════════════════════════════
   Main Component
   ═══════════════════════════════════════════ */
function IntegrationsInner() {
  const qc = useQueryClient();
  const [activeTab, setActiveTab] = useState('oauth');
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' | 'info' } | null>(null);

  const showToast = (message: string, type: 'success' | 'error' | 'info' = 'success') => {
    setToast({message, type});
    setTimeout(() => setToast(null), 3000);
  };

  return (
    <AdminShell title="集成管理" actions={
      <div className="text-xs text-gray-400">管理第三方登录 · 统计 · 存储 · 数据迁移</div>
    }>
      {toast && <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)}/>}

      {/* ═══ Tab Bar ═══ */}
      <div className="flex gap-1.5 mb-6 overflow-x-auto pb-1 scrollbar-hide">
        {TABS.map(t => {
          const Icon = t.icon;
          const isActive = activeTab === t.key;
          return (
            <button key={t.key} onClick={() => setActiveTab(t.key)}
                    className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium rounded-xl whitespace-nowrap transition-all ${isActive
                      ? `bg-gradient-to-r ${t.color} text-white shadow-lg shadow-blue-500/20`
                      : 'bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800 hover:border-gray-300'
                    }`}>
              <Icon className="w-4 h-4"/>{t.label}
            </button>
          );
        })}
      </div>

      {/* ═══ Tab Content ═══ */}
      {activeTab === 'oauth' && <OAuthTab showToast={showToast}/>}
      {activeTab === 'sso' && <SSOTab showToast={showToast}/>}
      {activeTab === 'analytics' && <AnalyticsTab showToast={showToast}/>}
      {activeTab === 'ipfs' && <IPFSTab showToast={showToast}/>}
      {activeTab === 'import' && <ImportTab showToast={showToast}/>}
    </AdminShell>
  );
}

/* ════════════════════════════════════════════════════════════════
   OAuth Tab - 第三方登录管理
   ════════════════════════════════════════════════════════════════ */
function OAuthTab({showToast}: { showToast: (msg: string, type?: 'success' | 'error' | 'info') => void }) {
  const qc = useQueryClient();
  const [showConfigModal, setShowConfigModal] = useState(false);
  const [configProvider, setConfigProvider] = useState('');
  const [configForm, setConfigForm] = useState({client_id: '', client_secret: '', redirect_uri: ''});

  const {data: providers, isLoading: loadingProviders} = useQuery({
    queryKey: ['integ-oauth-providers'],
    queryFn: async () => {
      const r = await apiClient.get<any>('/integrations/oauth/providers');
      const raw = r.success && r.data ? (r.data.providers || r.data) : [];
      return (Array.isArray(raw) ? raw : []).filter((p: any) =>
        (p.name || p.provider || '').toLowerCase() !== 'weibo'
      );
    },
  });

  const {data: linkedAccounts} = useQuery({
    queryKey: ['integ-oauth-linked'],
    queryFn: async () => {
      const r = await apiClient.get<any>('/integrations/oauth/linked-accounts');
      const raw = r.success && r.data ? (r.data.linked_accounts || r.data.accounts || r.data) : [];
      return (Array.isArray(raw) ? raw : []) as LinkedAccount[];
    },
  });

  const unlinkMut = useMutation({
    mutationFn: (provider: string) => apiClient.post(`/integrations/oauth/unlink/${provider}`),
    onSuccess: (r) => {
      qc.invalidateQueries({queryKey: ['integ-oauth-linked']});
      showToast(r.message || '已解绑', 'success');
    },
    onError: () => showToast('解绑失败', 'error'),
  });

  const linked = Array.isArray(linkedAccounts) ? linkedAccounts : [];
  const providerList = Array.isArray(providers) ? providers : [];

  return (
    <div className="space-y-6">
      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard icon={Globe} label="可用提供商" value={providerList.length} color="from-blue-500 to-indigo-500"/>
        <StatCard icon={CheckCircle} label="已配置" value={providerList.filter((p: any) => p.configured).length}
                  color="from-green-500 to-emerald-500"/>
        <StatCard icon={Link} label="已关联账号" value={linked.length} color="from-purple-500 to-violet-500"/>
        <StatCard icon={Shield} label="登录方式" value={linked.length + 1} sub="含密码登录"
                  color="from-orange-500 to-amber-500"/>
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        {/* Providers List */}
        <div
          className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 overflow-hidden">
          <div className="p-5 border-b border-gray-100 dark:border-gray-800 flex items-center justify-between">
            <SectionTitle icon={Globe} title="OAuth 提供商" subtitle="管理第三方登录渠道"/>
          </div>
          <div className="divide-y divide-gray-100 dark:divide-gray-800">
            {loadingProviders ? (
              <div className="p-8 text-center"><Loader className="w-6 h-6 animate-spin mx-auto text-gray-400"/></div>
            ) : providerList.length > 0 ? providerList.map((p: OAuthProvider, i: number) => {
              const name = p.name || (p as any).provider || '';
              const isConfigured = p.configured || false;
              const isLinked = linked.some((l: LinkedAccount) => (l.provider || '').toLowerCase() === name.toLowerCase());
              return (
                <div key={i}
                     className="flex items-center justify-between p-4 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors">
                  <div className="flex items-center gap-3">
                    <ProviderAvatar name={name} icon={p.icon}/>
                    <div>
                      <p className="text-sm font-medium text-gray-900 dark:text-white">{p.display_name || name}</p>
                      <p className="text-xs text-gray-400 mt-0.5">
                        {isConfigured ? '已配置 Client ID' : '未配置'}
                        {isLinked && ' · 已关联'}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <StatusBadge active={isConfigured} activeText="已启用" inactiveText="未启用"/>
                  </div>
                </div>
              );
            }) : (
              <EmptyState icon={Globe} title="暂无提供商" desc="系统尚未配置 OAuth 提供商"/>
            )}
          </div>
        </div>

        {/* Linked Accounts */}
        <div
          className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 overflow-hidden">
          <div className="p-5 border-b border-gray-100 dark:border-gray-800">
            <SectionTitle icon={Link} title="已关联账号" subtitle="管理当前用户的第三方绑定"/>
          </div>
          <div className="divide-y divide-gray-100 dark:divide-gray-800">
            {linked.length > 0 ? linked.map((a: LinkedAccount, i: number) => (
              <div key={i}
                   className="flex items-center justify-between p-4 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors">
                <div className="flex items-center gap-3 min-w-0">
                  <ProviderAvatar name={a.provider} size="sm"/>
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-gray-900 dark:text-white">{a.provider_name || a.provider}</p>
                    <p
                      className="text-xs text-gray-400 truncate">{a.provider_user_id || a.email || a.username || ''}</p>
                    {a.bound_at && <p
                      className="text-[10px] text-gray-300 mt-0.5">绑定于 {new Date(a.bound_at).toLocaleDateString('zh-CN')}</p>}
                  </div>
                </div>
                <ActionButton onClick={() => {
                  if (confirm(`确定解绑 ${a.provider_name || a.provider}？`)) unlinkMut.mutate(a.provider);
                }} icon={Unlink} label="解绑" variant="danger" size="sm" loading={unlinkMut.isPending}/>
              </div>
            )) : (
              <EmptyState icon={Link} title="暂无关联账号" desc="用户尚未绑定任何第三方账号"/>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

/* ════════════════════════════════════════════════════════════════
   SSO Tab - 企业认证配置
   ════════════════════════════════════════════════════════════════ */
function SSOTab({showToast}: { showToast: (msg: string, type?: 'success' | 'error' | 'info') => void }) {
  const [activeSection, setActiveSection] = useState<'oauth2' | 'saml' | 'ldap'>('oauth2');

  const {data: ssoConfig, isLoading} = useQuery({
    queryKey: ['integ-sso-config'],
    queryFn: async () => {
      const r = await apiClient.get<any>('/integrations/sso/config');
      return r.success && r.data ? r.data : {};
    },
  });

  const ssoProviders = ssoConfig?.oauth || {};
  const samlConfigured = ssoConfig?.saml || false;
  const ldapConfigured = ssoConfig?.ldap || false;

  const sections = [
    {
      key: 'oauth2' as const,
      label: 'OAuth 2.0',
      icon: Key,
      desc: 'Google / GitHub / Microsoft',
      configured: Object.values(ssoProviders).some(Boolean)
    },
    {
      key: 'saml' as const,
      label: 'SAML 2.0',
      icon: Shield,
      desc: 'Okta / Azure AD / OneLogin',
      configured: samlConfigured
    },
    {
      key: 'ldap' as const,
      label: 'LDAP',
      icon: Server,
      desc: 'OpenLDAP / Active Directory',
      configured: ldapConfigured
    },
  ];

  return (
    <div className="space-y-6">
      {/* Stats */}
      <div className="grid grid-cols-3 gap-4">
        {sections.map(s => {
          const Icon = s.icon;
          return (
            <div key={s.key}
                 className={`bg-white dark:bg-gray-900 rounded-2xl border p-5 cursor-pointer transition-all hover:shadow-md ${activeSection === s.key ? 'ring-2 ring-blue-500 border-blue-200' : 'border-gray-200 dark:border-gray-700'}`}
                 onClick={() => setActiveSection(s.key)}>
              <div className="flex items-center justify-between mb-3">
                <div
                  className={`w-10 h-10 rounded-xl ${s.configured ? 'bg-gradient-to-br from-green-500 to-emerald-500' : 'bg-gradient-to-br from-gray-400 to-gray-500'} flex items-center justify-center`}>
                  <Icon className="w-5 h-5 text-white"/>
                </div>
                <StatusBadge active={s.configured} activeText="已配置" inactiveText="未配置"/>
              </div>
              <p className="text-sm font-semibold text-gray-900 dark:text-white">{s.label}</p>
              <p className="text-xs text-gray-400 mt-1">{s.desc}</p>
            </div>
          );
        })}
      </div>

      {/* Detail Panels */}
      <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 p-6">
        {activeSection === 'oauth2' && (
          <div className="space-y-6">
            <SectionTitle icon={Key} title="OAuth 2.0 配置" subtitle="通过环境变量配置 OAuth2 提供商凭证"/>
            <div className="grid sm:grid-cols-3 gap-4">
              {['Google', 'GitHub', 'Microsoft'].map(name => {
                const key = name.toLowerCase();
                const configured = ssoProviders[key] || false;
                return (
                  <div key={name}
                       className={`p-4 rounded-xl border ${configured ? 'border-green-200 bg-green-50/50 dark:bg-green-900/10 dark:border-green-800' : 'border-gray-200 dark:border-gray-700'}`}>
                    <div className="flex items-center gap-3 mb-3">
                      <ProviderAvatar name={key} size="sm"/>
                      <div>
                        <p className="text-sm font-medium text-gray-900 dark:text-white">{name}</p>
                        <p
                          className={`text-xs ${configured ? 'text-green-600' : 'text-gray-400'}`}>{configured ? '已配置' : '未配置'}</p>
                      </div>
                    </div>
                    <div className="space-y-2">
                      <InputField label={`Client ID`} value="" onChange={() => {
                      }} placeholder={`OAUTH_${key.toUpperCase()}_CLIENT_ID`} hint="通过环境变量设置"/>
                      <InputField label="Client Secret" value="" onChange={() => {
                      }} type="password" placeholder={`OAUTH_${key.toUpperCase()}_CLIENT_SECRET`}
                                  hint="通过环境变量设置"/>
                    </div>
                  </div>
                );
              })}
            </div>
            <div
              className="p-4 bg-blue-50 dark:bg-blue-900/10 rounded-xl border border-blue-100 dark:border-blue-800/30">
              <p className="text-xs text-blue-700 dark:text-blue-300">
                <strong>配置方式：</strong>在 <code
                className="bg-blue-100 dark:bg-blue-800 px-1 rounded">.env</code> 文件中设置对应环境变量后重启服务即可。授权端点：<code
                className="bg-blue-100 dark:bg-blue-800 px-1 rounded">/api/v2/integrations/sso/oauth/{"{provider}"}/authorize</code>
              </p>
            </div>
          </div>
        )}

        {activeSection === 'saml' && (
          <div className="space-y-6">
            <SectionTitle icon={Shield} title="SAML 2.0 配置" subtitle="配置企业身份提供商 (IdP) 进行单点登录"/>
            <div className="grid sm:grid-cols-2 gap-6">
              <div className="space-y-4">
                <InputField label="Entity ID (IdP)" value="" onChange={() => {
                }} placeholder="https://idp.company.com/metadata" hint="身份提供商的实体 ID / Metadata URL"/>
                <InputField label="SSO URL" value="" onChange={() => {
                }} placeholder="https://idp.company.com/sso/saml" hint="IdP 的 SSO 登录 URL"/>
                <InputField label="SLO URL" value="" onChange={() => {
                }} placeholder="https://idp.company.com/slo/saml" hint="单点登出 URL（可选）"/>
                <InputField label="X.509 证书" value="" onChange={() => {
                }} placeholder="-----BEGIN CERTIFICATE-----" hint="IdP 的签名证书"/>
              </div>
              <div className="space-y-4">
                <div className="p-4 bg-gray-50 dark:bg-gray-800 rounded-xl">
                  <p className="text-sm font-medium text-gray-900 dark:text-white mb-2">支持的 IdP</p>
                  <div className="space-y-2">
                    {['Okta', 'Azure AD', 'OneLogin', 'Auth0'].map(idp => (
                      <div key={idp} className="flex items-center gap-2 text-xs text-gray-600 dark:text-gray-400">
                        <Check className="w-3.5 h-3.5 text-green-500"/>{idp}
                      </div>
                    ))}
                  </div>
                </div>
                <div className="p-4 bg-gray-50 dark:bg-gray-800 rounded-xl">
                  <p className="text-sm font-medium text-gray-900 dark:text-white mb-2">SP 端点</p>
                  <p className="text-xs text-gray-500 font-mono">ACS: /api/v2/integrations/sso/saml/acs</p>
                  <p className="text-xs text-gray-500 font-mono mt-1">SLO: /api/v2/integrations/sso/saml/slo</p>
                </div>
              </div>
            </div>
          </div>
        )}

        {activeSection === 'ldap' && (
          <div className="space-y-6">
            <SectionTitle icon={Server} title="LDAP 配置" subtitle="连接企业目录服务进行身份认证"/>
            <div className="grid sm:grid-cols-2 gap-6">
              <div className="space-y-4">
                <InputField label="LDAP 服务器" value="" onChange={() => {
                }} placeholder="ldap://ldap.company.com:389" hint="LDAP 服务器地址"/>
                <InputField label="Base DN" value="" onChange={() => {
                }} placeholder="dc=company,dc=com" hint="搜索基准 DN"/>
                <InputField label="Bind DN" value="" onChange={() => {
                }} placeholder="cn=admin,dc=company,dc=com" hint="绑定用户 DN"/>
                <InputField label="Bind 密码" value="" onChange={() => {
                }} type="password" placeholder="绑定密码" hint="绑定用户密码"/>
              </div>
              <div className="space-y-4">
                <InputField label="用户搜索过滤器" value="" onChange={() => {
                }} placeholder="(uid={username})" hint="用户搜索条件模板"/>
                <InputField label="用户属性映射" value="" onChange={() => {
                }} placeholder="uid,mail,cn" hint="需要获取的属性列表"/>
                <div className="p-4 bg-gray-50 dark:bg-gray-800 rounded-xl">
                  <p className="text-sm font-medium text-gray-900 dark:text-white mb-2">认证端点</p>
                  <p className="text-xs text-gray-500 font-mono">POST /api/v2/integrations/sso/ldap/authenticate</p>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

/* ════════════════════════════════════════════════════════════════
   Analytics Tab - 统计分析集成
   ════════════════════════════════════════════════════════════════ */
function AnalyticsTab({showToast}: { showToast: (msg: string, type?: 'success' | 'error' | 'info') => void }) {
  const qc = useQueryClient();
  const [showGAModal, setShowGAModal] = useState(false);
  const [showBaiduModal, setShowBaiduModal] = useState(false);
  const [editingBaidu, setEditingBaidu] = useState<BaiduConfig | null>(null);
  const [gaForm, setGAForm] = useState({
    tracking_id: '',
    measurement_id: '',
    api_secret: '',
    enable_page_view_tracking: true,
    enable_event_tracking: true,
    anonymize_ip: true,
    sample_rate: 100
  });
  const [baiduForm, setBaiduForm] = useState({
    site_token: '',
    api_key: '',
    enable_tracking: true,
    enable_data_sync: false
  });

  // GA Config
  const {data: gaConfig, isLoading: gaLoading} = useQuery({
    queryKey: ['integ-ga-config'],
    queryFn: async () => {
      const r = await apiClient.get<any>('/integrations/analytics/google/config');
      return r.success && r.data ? r.data as GAConfig : null;
    },
  });

  // Baidu Configs
  const {data: baiduConfigs, isLoading: baiduLoading} = useQuery({
    queryKey: ['integ-baidu-configs'],
    queryFn: async () => {
      const r = await apiClient.get<any>('/integrations/analytics/baidu/configs');
      const raw = r.success && r.data ? (r.data.configs || r.data) : [];
      return (Array.isArray(raw) ? raw : []) as BaiduConfig[];
    },
  });

  // GA Mutations
  const createGAMut = useMutation({
    mutationFn: (data: any) => apiClient.post('/integrations/analytics/google/config', data),
    onSuccess: (r) => {
      qc.invalidateQueries({queryKey: ['integ-ga-config']});
      setShowGAModal(false);
      showToast(r.message || 'Google Analytics 配置已创建');
    },
    onError: () => showToast('创建失败', 'error'),
  });

  const deleteGAMut = useMutation({
    mutationFn: (id: number) => apiClient.delete(`/integrations/analytics/google/config/${id}`),
    onSuccess: (r) => {
      qc.invalidateQueries({queryKey: ['integ-ga-config']});
      showToast(r.message || '已停用');
    },
    onError: () => showToast('操作失败', 'error'),
  });

  // Baidu Mutations
  const createBaiduMut = useMutation({
    mutationFn: (data: any) => apiClient.post('/integrations/analytics/baidu/config', data),
    onSuccess: (r) => {
      qc.invalidateQueries({queryKey: ['integ-baidu-configs']});
      setShowBaiduModal(false);
      showToast(r.message || '百度统计配置已创建');
    },
    onError: () => showToast('创建失败', 'error'),
  });

  const updateBaiduMut = useMutation({
    mutationFn: ({id, data}: {
      id: number;
      data: any
    }) => apiClient.put(`/integrations/analytics/baidu/config/${id}`, data),
    onSuccess: (r) => {
      qc.invalidateQueries({queryKey: ['integ-baidu-configs']});
      setEditingBaidu(null);
      showToast(r.message || '已更新');
    },
    onError: () => showToast('更新失败', 'error'),
  });

  const deleteBaiduMut = useMutation({
    mutationFn: (id: number) => apiClient.delete(`/integrations/analytics/baidu/config/${id}`),
    onSuccess: (r) => {
      qc.invalidateQueries({queryKey: ['integ-baidu-configs']});
      showToast(r.message || '已停用');
    },
    onError: () => showToast('操作失败', 'error'),
  });

  const handleCreateGA = () => {
    if (!gaForm.tracking_id) {
      showToast('请填写 Tracking ID', 'error');
      return;
    }
    createGAMut.mutate(gaForm);
  };

  const handleCreateBaidu = () => {
    if (!baiduForm.site_token) {
      showToast('请填写 Site Token', 'error');
      return;
    }
    createBaiduMut.mutate(baiduForm);
  };

  const baiduList = Array.isArray(baiduConfigs) ? baiduConfigs : [];

  return (
    <div className="space-y-6">
      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard icon={BarChart3} label="Google Analytics" value={gaConfig ? '已配置' : '未配置'}
                  color="from-orange-500 to-amber-500"/>
        <StatCard icon={BarChart3} label="百度统计" value={`${baiduList.length} 个配置`}
                  color="from-blue-500 to-indigo-500"/>
        <StatCard icon={Eye} label="页面追踪" value={gaConfig?.enable_page_view_tracking ? '启用' : '禁用'}
                  color="from-green-500 to-emerald-500"/>
        <StatCard icon={Activity} label="事件追踪" value={gaConfig?.enable_event_tracking ? '启用' : '禁用'}
                  color="from-purple-500 to-violet-500"/>
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        {/* Google Analytics */}
        <div
          className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 overflow-hidden">
          <div className="p-5 border-b border-gray-100 dark:border-gray-800 flex items-center justify-between">
            <SectionTitle icon={BarChart3} title="Google Analytics" subtitle="GA4 数据追踪"/>
            {!gaConfig && <ActionButton onClick={() => setShowGAModal(true)} icon={Plus} label="添加配置"/>}
          </div>
          {gaLoading ? (
            <div className="p-8 text-center"><Loader className="w-6 h-6 animate-spin mx-auto text-gray-400"/></div>
          ) : gaConfig ? (
            <div className="p-5 space-y-4">
              <div className="grid grid-cols-2 gap-3">
                {[
                  ['Tracking ID', gaConfig.tracking_id || '—'],
                  ['Measurement ID', gaConfig.measurement_id || '—'],
                  ['采样率', gaConfig.sample_rate ? `${gaConfig.sample_rate}%` : '100%'],
                  ['状态', gaConfig.is_active ? '活跃' : '未激活'],
                ].map(([label, val], i) => (
                  <div key={i} className="p-3 bg-gray-50 dark:bg-gray-800 rounded-xl">
                    <p className="text-[11px] text-gray-400 uppercase tracking-wider">{label}</p>
                    <p className="text-sm font-medium text-gray-900 dark:text-white mt-0.5">{val}</p>
                  </div>
                ))}
              </div>
              <div className="flex items-center gap-4">
                <div className="flex items-center gap-2">
                  <Toggle checked={gaConfig.enable_page_view_tracking || false} onChange={() => {
                  }} disabled/>
                  <span className="text-xs text-gray-500">页面追踪</span>
                </div>
                <div className="flex items-center gap-2">
                  <Toggle checked={gaConfig.enable_event_tracking || false} onChange={() => {
                  }} disabled/>
                  <span className="text-xs text-gray-500">事件追踪</span>
                </div>
                <div className="flex items-center gap-2">
                  <Toggle checked={gaConfig.anonymize_ip || false} onChange={() => {
                  }} disabled/>
                  <span className="text-xs text-gray-500">IP 匿名化</span>
                </div>
              </div>
              {gaConfig.id && (
                <div className="flex gap-2">
                  <ActionButton onClick={() => {
                    if (confirm('确定停用 Google Analytics?')) deleteGAMut.mutate(gaConfig.id!);
                  }} icon={Trash2} label="停用" variant="danger" size="sm"/>
                </div>
              )}
            </div>
          ) : (
            <EmptyState icon={BarChart3} title="尚未配置" desc="添加 GA4 配置以开始追踪访客数据"
                        action={<ActionButton onClick={() => setShowGAModal(true)} icon={Plus}
                                              label="添加 Google Analytics"/>}/>
          )}
        </div>

        {/* Baidu Analytics */}
        <div
          className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 overflow-hidden">
          <div className="p-5 border-b border-gray-100 dark:border-gray-800 flex items-center justify-between">
            <SectionTitle icon={BarChart3} title="百度统计" subtitle="百度数据追踪"/>
            <ActionButton onClick={() => {
              setBaiduForm({site_token: '', api_key: '', enable_tracking: true, enable_data_sync: false});
              setEditingBaidu(null);
              setShowBaiduModal(true);
            }} icon={Plus} label="添加配置"/>
          </div>
          {baiduLoading ? (
            <div className="p-8 text-center"><Loader className="w-6 h-6 animate-spin mx-auto text-gray-400"/></div>
          ) : baiduList.length > 0 ? (
            <div className="divide-y divide-gray-100 dark:divide-gray-800">
              {baiduList.map((cfg: BaiduConfig, i: number) => (
                <div key={cfg.id || i} className="p-4 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors">
                  <div className="flex items-center justify-between mb-2">
                    <div>
                      <p
                        className="text-sm font-medium text-gray-900 dark:text-white">{cfg.site_name || `配置 #${cfg.id || i + 1}`}</p>
                      <p className="text-xs text-gray-400 font-mono">{cfg.site_token || cfg.tracking_id || '—'}</p>
                    </div>
                    <StatusBadge active={cfg.is_active || false}/>
                  </div>
                  <div className="flex items-center gap-3 mt-2">
                    <div className="flex items-center gap-2">
                      <Toggle checked={cfg.enable_tracking || false} onChange={() => {
                      }} disabled/>
                      <span className="text-xs text-gray-500">追踪</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Toggle checked={cfg.enable_data_sync || false} onChange={() => {
                      }} disabled/>
                      <span className="text-xs text-gray-500">数据同步</span>
                    </div>
                    <div className="flex-1"/>
                    <ActionButton onClick={() => {
                      setBaiduForm({
                        site_token: cfg.site_token || '',
                        api_key: cfg.api_key || '',
                        enable_tracking: cfg.enable_tracking || false,
                        enable_data_sync: cfg.enable_data_sync || false
                      });
                      setEditingBaidu(cfg);
                      setShowBaiduModal(true);
                    }} icon={Edit3} label="编辑" variant="ghost" size="sm"/>
                    <ActionButton onClick={() => {
                      if (confirm('确定停用此百度统计配置?')) deleteBaiduMut.mutate(cfg.id!);
                    }} icon={Trash2} label="停用" variant="danger" size="sm"/>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState icon={BarChart3} title="尚未配置" desc="添加百度统计配置以追踪国内用户数据"
                        action={<ActionButton onClick={() => setShowBaiduModal(true)} icon={Plus}
                                              label="添加百度统计"/>}/>
          )}
        </div>
      </div>

      {/* GA Config Modal */}
      <Modal open={showGAModal} onClose={() => setShowGAModal(false)} title="添加 Google Analytics"
             subtitle="配置 GA4 追踪">
        <div className="space-y-4">
          <InputField label="Tracking ID *" value={gaForm.tracking_id}
                      onChange={v => setGAForm(f => ({...f, tracking_id: v}))} placeholder="G-XXXXXXXXXX"
                      hint="Google Analytics 4 的 Measurement ID"/>
          <InputField label="Measurement ID" value={gaForm.measurement_id}
                      onChange={v => setGAForm(f => ({...f, measurement_id: v}))} placeholder="G-XXXXXXXXXX"/>
          <InputField label="API Secret" value={gaForm.api_secret}
                      onChange={v => setGAForm(f => ({...f, api_secret: v}))} type="password"
                      hint="用于 Measurement Protocol 的密钥（可选）"/>
          <InputField label="采样率 (%)" value={String(gaForm.sample_rate)}
                      onChange={v => setGAForm(f => ({...f, sample_rate: Number(v) || 100}))} type="number"
                      placeholder="100"/>
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-700 dark:text-gray-300">页面浏览追踪</span>
              <Toggle checked={gaForm.enable_page_view_tracking}
                      onChange={v => setGAForm(f => ({...f, enable_page_view_tracking: v}))}/>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-700 dark:text-gray-300">事件追踪</span>
              <Toggle checked={gaForm.enable_event_tracking}
                      onChange={v => setGAForm(f => ({...f, enable_event_tracking: v}))}/>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-700 dark:text-gray-300">IP 匿名化</span>
              <Toggle checked={gaForm.anonymize_ip} onChange={v => setGAForm(f => ({...f, anonymize_ip: v}))}/>
            </div>
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <ActionButton onClick={() => setShowGAModal(false)} icon={X} label="取消" variant="ghost"/>
            <ActionButton onClick={handleCreateGA} icon={Save} label="保存配置" loading={createGAMut.isPending}/>
          </div>
        </div>
      </Modal>

      {/* Baidu Config Modal */}
      <Modal open={showBaiduModal} onClose={() => {
        setShowBaiduModal(false);
        setEditingBaidu(null);
      }}
             title={editingBaidu ? '编辑百度统计' : '添加百度统计'} subtitle="配置百度数据追踪">
        <div className="space-y-4">
          <InputField label="Site Token *" value={baiduForm.site_token}
                      onChange={v => setBaiduForm(f => ({...f, site_token: v}))} placeholder="UM-XXXXXXXX-X"
                      hint="百度统计站点 Token"/>
          <InputField label="API Key" value={baiduForm.api_key} onChange={v => setBaiduForm(f => ({...f, api_key: v}))}
                      type="password" hint="用于数据同步的 API Key（可选）"/>
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-700 dark:text-gray-300">启用追踪</span>
              <Toggle checked={baiduForm.enable_tracking}
                      onChange={v => setBaiduForm(f => ({...f, enable_tracking: v}))}/>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-700 dark:text-gray-300">数据同步</span>
              <Toggle checked={baiduForm.enable_data_sync}
                      onChange={v => setBaiduForm(f => ({...f, enable_data_sync: v}))}/>
            </div>
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <ActionButton onClick={() => {
              setShowBaiduModal(false);
              setEditingBaidu(null);
            }} icon={X} label="取消" variant="ghost"/>
            {editingBaidu ? (
              <ActionButton onClick={() => updateBaiduMut.mutate({id: editingBaidu.id!, data: baiduForm})} icon={Save}
                            label="更新配置" loading={updateBaiduMut.isPending}/>
            ) : (
              <ActionButton onClick={handleCreateBaidu} icon={Save} label="保存配置"
                            loading={createBaiduMut.isPending}/>
            )}
          </div>
        </div>
      </Modal>
    </div>
  );
}

/* ════════════════════════════════════════════════════════════════
   IPFS Tab - 去中心化存储管理
   ════════════════════════════════════════════════════════════════ */
function IPFSTab({showToast}: { showToast: (msg: string, type?: 'success' | 'error' | 'info') => void }) {
  const qc = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [showTextUpload, setShowTextUpload] = useState(false);
  const [textContent, setTextContent] = useState('');
  const [textFilename, setTextFilename] = useState('content.txt');
  const [showConfigModal, setShowConfigModal] = useState(false);
  const [ipfsGateway, setIpfsGateway] = useState('');

  const {data: ipfsFiles, isLoading} = useQuery({
    queryKey: ['integ-ipfs-files'],
    queryFn: async () => {
      const r = await apiClient.get<any>('/integrations/ipfs/files');
      const raw = r.success && r.data ? (r.data.files || r.data) : [];
      return (Array.isArray(raw) ? raw : []) as IPFSFile[];
    },
  });

  const uploadFileMut = useMutation({
    mutationFn: async (file: File) => {
      const formData = new FormData();
      formData.append('file', file);
      return apiClient.request('/integrations/ipfs/upload/file', {method: 'POST', body: formData});
    },
    onSuccess: (r) => {
      qc.invalidateQueries({queryKey: ['integ-ipfs-files']});
      showToast(r.message || '文件已上传到 IPFS');
      setUploading(false);
    },
    onError: () => {
      showToast('上传失败', 'error');
      setUploading(false);
    },
  });

  const uploadTextMut = useMutation({
    mutationFn: (data: { text: string; filename: string }) => apiClient.post('/integrations/ipfs/upload/text', data),
    onSuccess: (r) => {
      qc.invalidateQueries({queryKey: ['integ-ipfs-files']});
      setShowTextUpload(false);
      setTextContent('');
      showToast(r.message || '文本已上传到 IPFS');
    },
    onError: () => showToast('上传失败', 'error'),
  });

  const pinMut = useMutation({
    mutationFn: (cid: string) => apiClient.post(`/integrations/ipfs/pin/${cid}`),
    onSuccess: (r) => {
      qc.invalidateQueries({queryKey: ['integ-ipfs-files']});
      showToast(r.message || '已固定');
    },
    onError: () => showToast('操作失败', 'error'),
  });

  const unpinMut = useMutation({
    mutationFn: (cid: string) => apiClient.post(`/integrations/ipfs/unpin/${cid}`),
    onSuccess: (r) => {
      qc.invalidateQueries({queryKey: ['integ-ipfs-files']});
      showToast(r.message || '已取消固定');
    },
    onError: () => showToast('操作失败', 'error'),
  });

  const deleteMut = useMutation({
    mutationFn: (cid: string) => apiClient.delete(`/integrations/ipfs/file/${cid}`),
    onSuccess: (r) => {
      qc.invalidateQueries({queryKey: ['integ-ipfs-files']});
      showToast(r.message || '已删除');
    },
    onError: () => showToast('删除失败', 'error'),
  });

  const configureMut = useMutation({
    mutationFn: (config: any) => apiClient.post('/integrations/ipfs/configure', config),
    onSuccess: (r) => {
      setShowConfigModal(false);
      showToast(r.message || 'IPFS 配置已更新');
    },
    onError: () => showToast('配置失败', 'error'),
  });

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    uploadFileMut.mutate(file);
    e.target.value = '';
  };

  const handleDragDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (file) {
      setUploading(true);
      uploadFileMut.mutate(file);
    }
  }, []);

  const files = Array.isArray(ipfsFiles) ? ipfsFiles : [];

  return (
    <div className="space-y-6">
      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard icon={HardDrive} label="总文件数" value={files.length} color="from-purple-500 to-violet-500"/>
        <StatCard icon={Pin} label="已固定" value={files.filter(f => f.pinned).length}
                  color="from-green-500 to-emerald-500"/>
        <StatCard icon={Database} label="总大小"
                  value={files.reduce((s, f) => s + (f.size || 0), 0) > 0 ? `${(files.reduce((s, f) => s + (f.size || 0), 0) / 1024).toFixed(1)} KB` : '0 KB'}
                  color="from-blue-500 to-indigo-500"/>
        <StatCard icon={CloudUpload} label="存储网关" value="IPFS" color="from-orange-500 to-amber-500"/>
      </div>

      {/* Upload Area */}
      <div
        className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 overflow-hidden">
        <div className="p-5 border-b border-gray-100 dark:border-gray-800 flex items-center justify-between">
          <SectionTitle icon={Database} title="IPFS 文件管理" subtitle="上传、固定和管理去中心化存储的文件"/>
          <div className="flex gap-2">
            <ActionButton onClick={() => setShowTextUpload(true)} icon={FileText} label="上传文本" variant="ghost"/>
            <ActionButton onClick={() => fileInputRef.current?.click()} icon={FileUp} label="上传文件"
                          loading={uploading}/>
          </div>
        </div>

        {/* Drag & Drop Zone */}
        <div className="p-5">
          <div
            className="border-2 border-dashed border-gray-200 dark:border-gray-700 rounded-xl p-8 text-center hover:border-blue-400 transition-colors cursor-pointer"
            onDragOver={e => e.preventDefault()} onDrop={handleDragDrop} onClick={() => fileInputRef.current?.click()}>
            {uploading ? (
              <div className="flex flex-col items-center">
                <Loader className="w-8 h-8 text-blue-500 animate-spin mb-2"/>
                <p className="text-sm text-gray-500">正在上传到 IPFS...</p>
              </div>
            ) : (
              <div className="flex flex-col items-center">
                <CloudUpload className="w-10 h-10 text-gray-300 mb-2"/>
                <p className="text-sm text-gray-500">拖放文件到这里，或点击选择文件</p>
                <p className="text-xs text-gray-400 mt-1">支持任意类型文件</p>
              </div>
            )}
          </div>
          <input ref={fileInputRef} type="file" className="hidden" onChange={handleFileSelect}/>
        </div>

        {/* Files List */}
        <div className="border-t border-gray-100 dark:border-gray-800">
          {isLoading ? (
            <div className="p-8 text-center"><Loader className="w-6 h-6 animate-spin mx-auto text-gray-400"/></div>
          ) : files.length > 0 ? (
            <div className="divide-y divide-gray-100 dark:divide-gray-800 max-h-[400px] overflow-y-auto">
              {files.map((f: IPFSFile, i: number) => (
                <div key={f.cid || i}
                     className="flex items-center justify-between p-4 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors">
                  <div className="flex items-center gap-3 min-w-0 flex-1">
                    <div
                      className="w-9 h-9 rounded-xl bg-gradient-to-br from-purple-100 to-indigo-100 dark:from-purple-900/30 dark:to-indigo-900/30 flex items-center justify-center shrink-0">
                      <FileText className="w-4 h-4 text-purple-500"/>
                    </div>
                    <div className="min-w-0">
                      <p
                        className="text-sm font-medium text-gray-900 dark:text-white truncate">{f.name || f.filename || f.cid}</p>
                      <p className="text-xs text-gray-400 font-mono truncate">{f.cid}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 shrink-0 ml-3">
                    {f.size && <span className="text-xs text-gray-400">{(f.size / 1024).toFixed(1)} KB</span>}
                    {f.pinned ? (
                      <span
                        className="inline-flex items-center gap-1 px-2 py-0.5 text-[10px] font-medium bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400 rounded-full">
                        <Pin className="w-2.5 h-2.5"/>已固定
                      </span>
                    ) : (
                      <span
                        className="inline-flex items-center gap-1 px-2 py-0.5 text-[10px] font-medium bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400 rounded-full">
                        未固定
                      </span>
                    )}
                    <div className="flex gap-1">
                      {f.pinned ? (
                        <button onClick={() => unpinMut.mutate(f.cid)}
                                className="p-1.5 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-lg transition-colors"
                                title="取消固定">
                          <PinOff className="w-3.5 h-3.5 text-gray-400"/>
                        </button>
                      ) : (
                        <button onClick={() => pinMut.mutate(f.cid)}
                                className="p-1.5 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-lg transition-colors"
                                title="固定">
                          <Pin className="w-3.5 h-3.5 text-gray-400"/>
                        </button>
                      )}
                      {f.gateway_url && (
                        <a href={f.gateway_url} target="_blank" rel="noopener noreferrer"
                           className="p-1.5 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-lg transition-colors"
                           title="查看">
                          <Eye className="w-3.5 h-3.5 text-gray-400"/>
                        </a>
                      )}
                      <button onClick={() => {
                        navigator.clipboard.writeText(f.cid);
                        showToast('CID 已复制', 'info');
                      }} className="p-1.5 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-lg transition-colors"
                              title="复制 CID">
                        <Copy className="w-3.5 h-3.5 text-gray-400"/>
                      </button>
                      <button onClick={() => {
                        if (confirm(`确定删除 ${f.name || f.cid}？\n注意：IPFS 上的文件无法真正删除，仅删除记录。`)) deleteMut.mutate(f.cid);
                      }} className="p-1.5 hover:bg-red-100 dark:hover:bg-red-900/30 rounded-lg transition-colors"
                              title="删除">
                        <Trash2 className="w-3.5 h-3.5 text-red-400"/>
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState icon={Database} title="暂无 IPFS 文件" desc="上传文件到去中心化存储网络"/>
          )}
        </div>
      </div>

      {/* Text Upload Modal */}
      <Modal open={showTextUpload} onClose={() => setShowTextUpload(false)} title="上传文本到 IPFS"
             subtitle="将文本内容存储到去中心化网络">
        <div className="space-y-4">
          <InputField label="文件名" value={textFilename} onChange={setTextFilename} placeholder="content.txt"/>
          <div>
            <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1.5">内容</label>
            <textarea value={textContent} onChange={e => setTextContent(e.target.value)} rows={8}
                      placeholder="输入要上传的文本内容..."
                      className="w-full px-3 py-2 text-sm border border-gray-200 dark:border-gray-700 rounded-xl bg-white dark:bg-gray-800 text-gray-900 dark:text-white placeholder:text-gray-400 focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 outline-none transition-all resize-none"/>
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <ActionButton onClick={() => setShowTextUpload(false)} icon={X} label="取消" variant="ghost"/>
            <ActionButton onClick={() => {
              if (!textContent.trim()) {
                showToast('请输入内容', 'error');
                return;
              }
              uploadTextMut.mutate({text: textContent, filename: textFilename});
            }} icon={CloudUpload} label="上传" loading={uploadTextMut.isPending}/>
          </div>
        </div>
      </Modal>

      {/* IPFS Config Modal */}
      <Modal open={showConfigModal} onClose={() => setShowConfigModal(false)} title="IPFS 服务配置"
             subtitle="配置 IPFS 网关和 API">
        <div className="space-y-4">
          <InputField label="IPFS API 端点" value={ipfsGateway} onChange={setIpfsGateway}
                      placeholder="http://localhost:5001" hint="IPFS 节点 API 地址"/>
          <div className="flex justify-end gap-2 pt-2">
            <ActionButton onClick={() => setShowConfigModal(false)} icon={X} label="取消" variant="ghost"/>
            <ActionButton onClick={() => configureMut.mutate({api_url: ipfsGateway})} icon={Save} label="保存"
                          loading={configureMut.isPending}/>
          </div>
        </div>
      </Modal>
    </div>
  );
}

/* ════════════════════════════════════════════════════════════════
   Import Tab - 数据导入
   ════════════════════════════════════════════════════════════════ */
function ImportTab({showToast}: { showToast: (msg: string, type?: 'success' | 'error' | 'info') => void }) {
  const qc = useQueryClient();
  const wpFileRef = useRef<HTMLInputElement>(null);
  const [importing, setImporting] = useState(false);
  const [parseResult, setParseResult] = useState<any>(null);
  const [showImportConfirm, setShowImportConfirm] = useState(false);
  const [downloadMedia, setDownloadMedia] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const {data: wpTemplate} = useQuery({
    queryKey: ['integ-wp-template'],
    queryFn: async () => {
      const r = await apiClient.get<any>('/integrations/wordpress/template');
      return r.success && r.data ? r.data : null;
    },
  });

  const parseMut = useMutation({
    mutationFn: async (file: File) => {
      const formData = new FormData();
      formData.append('file', file);
      return apiClient.request('/integrations/wordpress/parse', {method: 'POST', body: formData});
    },
    onSuccess: (r) => {
      if (r.success) {
        setParseResult(r);
        setShowImportConfirm(true);
        showToast('文件解析成功，请确认导入');
      } else {
        showToast(r.error || '解析失败', 'error');
      }
      setImporting(false);
    },
    onError: () => {
      showToast('解析失败', 'error');
      setImporting(false);
    },
  });

  const importMut = useMutation({
    mutationFn: async ({file, downloadMedia}: { file: File; downloadMedia: boolean }) => {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('download_media', String(downloadMedia));
      return apiClient.request('/integrations/wordpress/import', {method: 'POST', body: formData});
    },
    onSuccess: (r) => {
      if (r.success) {
        showToast('WordPress 数据导入成功！');
        setParseResult(null);
        setShowImportConfirm(false);
      } else {
        showToast(r.error || '导入失败', 'error');
      }
      setImporting(false);
    },
    onError: () => {
      showToast('导入失败', 'error');
      setImporting(false);
    },
  });

  const handleWPFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setSelectedFile(file);
    setImporting(true);
    parseMut.mutate(file);
    e.target.value = '';
  };

  const handleWPImport = () => {
    if (!selectedFile) {
      showToast('请先选择文件', 'error');
      return;
    }
    setImporting(true);
    importMut.mutate({file: selectedFile, downloadMedia});
  };

  const importSources = [
    {name: 'Halo', desc: '从 Halo 博客导入文章和数据', icon: Globe, status: 'available'},
    {name: 'Jekyll', desc: '从 Jekyll 站点导入 Markdown 文章', icon: FileText, status: 'available'},
    {name: 'Hexo', desc: '从 Hexo 博客导入文章和配置', icon: FileText, status: 'available'},
    {name: 'Ghost', desc: '从 Ghost 平台导入内容和用户', icon: Ghost, status: 'coming'},
    {name: 'Medium', desc: '从 Medium 导出文章', icon: FileText, status: 'coming'},
    {name: 'JSON / CSV', desc: '通用 JSON/CSV 格式批量导入', icon: Database, status: 'available'},
  ];

  return (
    <div className="space-y-6">
      {/* WordPress Import - Primary */}
      <div
        className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 overflow-hidden">
        <div className="p-5 border-b border-gray-100 dark:border-gray-800">
          <SectionTitle icon={Upload} title="WordPress 导入" subtitle="从 WordPress WXR 导出文件迁移数据"/>
        </div>
        <div className="p-5">
          <div className="grid lg:grid-cols-2 gap-6">
            {/* Upload Area */}
            <div>
              <div
                className="border-2 border-dashed border-gray-200 dark:border-gray-700 rounded-xl p-8 text-center hover:border-blue-400 transition-colors cursor-pointer"
                onClick={() => wpFileRef.current?.click()}>
                {importing ? (
                  <div className="flex flex-col items-center">
                    <Loader className="w-8 h-8 text-blue-500 animate-spin mb-2"/>
                    <p className="text-sm text-gray-500">{parseResult ? '正在导入...' : '正在解析...'}</p>
                  </div>
                ) : (
                  <div className="flex flex-col items-center">
                    <FileUp className="w-10 h-10 text-gray-300 mb-2"/>
                    <p className="text-sm text-gray-500">选择 WordPress 导出文件 (.xml)</p>
                    <p className="text-xs text-gray-400 mt-1">在 WordPress 后台 → 工具 → 导出 获取</p>
                  </div>
                )}
              </div>
              <input ref={wpFileRef} type="file" accept=".xml,.wxr" className="hidden" onChange={handleWPFileSelect}/>

              {/* Import Options */}
              {showImportConfirm && parseResult && (
                <div
                  className="mt-4 p-4 bg-blue-50 dark:bg-blue-900/10 rounded-xl border border-blue-100 dark:border-blue-800/30">
                  <p className="text-sm font-medium text-blue-800 dark:text-blue-300 mb-3">确认导入</p>
                  {parseResult.stats && (
                    <div className="grid grid-cols-2 gap-2 mb-3">
                      {Object.entries(parseResult.stats).map(([key, val]) => (
                        <div key={key} className="flex justify-between text-xs">
                          <span className="text-blue-600 dark:text-blue-400">{key}</span>
                          <span className="font-medium text-blue-800 dark:text-blue-200">{String(val)}</span>
                        </div>
                      ))}
                    </div>
                  )}
                  <div className="flex items-center gap-2 mb-3">
                    <input type="checkbox" id="downloadMedia" checked={downloadMedia}
                           onChange={e => setDownloadMedia(e.target.checked)}
                           className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"/>
                    <label htmlFor="downloadMedia"
                           className="text-xs text-blue-700 dark:text-blue-300">同时下载媒体文件</label>
                  </div>
                  <div className="flex gap-2">
                    <ActionButton onClick={() => {
                      setShowImportConfirm(false);
                      setParseResult(null);
                      setSelectedFile(null);
                    }} icon={X} label="取消" variant="ghost" size="sm"/>
                    <ActionButton onClick={handleWPImport} icon={ArrowRight} label="开始导入" loading={importing}
                                  size="sm"/>
                  </div>
                </div>
              )}
            </div>

            {/* Instructions */}
            <div className="space-y-4">
              <div className="p-4 bg-gray-50 dark:bg-gray-800 rounded-xl">
                <p className="text-sm font-medium text-gray-900 dark:text-white mb-3">导入步骤</p>
                <ol className="space-y-2.5">
                  {[
                    '在 WordPress 后台进入 工具 → 导出',
                    '选择"所有内容"并下载导出文件 (.xml)',
                    '点击左侧区域上传文件',
                    '预览解析结果并确认导入',
                    '等待导入完成',
                  ].map((step, i) => (
                    <li key={i} className="flex items-start gap-2.5 text-xs text-gray-600 dark:text-gray-400">
                      <span
                        className="w-5 h-5 rounded-full bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 flex items-center justify-center shrink-0 text-[10px] font-bold">{i + 1}</span>
                      {step}
                    </li>
                  ))}
                </ol>
              </div>
              <div className="p-4 bg-gray-50 dark:bg-gray-800 rounded-xl">
                <p className="text-sm font-medium text-gray-900 dark:text-white mb-2">支持的内容</p>
                <div className="flex flex-wrap gap-1.5">
                  {['文章', '页面', '分类', '标签', '评论', '媒体引用'].map(item => (
                    <span key={item}
                          className="inline-flex items-center gap-1 px-2 py-0.5 text-[11px] font-medium bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400 rounded-full">
                      <Check className="w-2.5 h-2.5"/>{item}
                    </span>
                  ))}
                </div>
              </div>
              <div
                className="p-3 bg-amber-50 dark:bg-amber-900/10 rounded-xl border border-amber-100 dark:border-amber-800/30">
                <p className="text-xs text-amber-700 dark:text-amber-300">
                  <strong>注意：</strong>媒体文件默认不会自动下载，仅保留引用链接。勾选"同时下载媒体文件"可迁移媒体资源。
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Other Import Sources */}
      <div
        className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 overflow-hidden">
        <div className="p-5 border-b border-gray-100 dark:border-gray-800">
          <SectionTitle icon={Upload} title="其他导入源" subtitle="从其他平台迁移数据"/>
        </div>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 divide-x divide-y divide-gray-100 dark:divide-gray-800">
          {importSources.map((src, i) => {
            const Icon = src.icon;
            return (
              <div key={i} className="p-4 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors">
                <div className="flex items-center gap-3 mb-2">
                  <div
                    className="w-8 h-8 rounded-lg bg-gradient-to-br from-gray-100 to-gray-200 dark:from-gray-700 dark:to-gray-800 flex items-center justify-center">
                    <Icon className="w-4 h-4 text-gray-500"/>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-gray-900 dark:text-white">{src.name}</p>
                    {src.status === 'coming' &&
                      <span className="text-[10px] text-amber-500 font-medium">即将推出</span>}
                  </div>
                </div>
                <p className="text-xs text-gray-400">{src.desc}</p>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

// Placeholder for Ghost icon (not in lucide)
function Ghost(props: any) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor"
         strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <path d="M9 10h.01"/>
      <path d="M15 10h.01"/>
      <path d="M12 2a8 8 0 0 0-8 8v12l3-3 2.5 2.5L12 19l2.5 2.5L17 19l3 3V10a8 8 0 0 0-8-8z"/>
    </svg>
  );
}

export default function AdminIntegrations() {
  return <AuthGuard><QueryProvider><IntegrationsInner/></QueryProvider></AuthGuard>;
}
