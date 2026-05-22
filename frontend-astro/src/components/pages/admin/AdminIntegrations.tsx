'use client';

import React, {useState} from 'react';
import {useQuery, useMutation, useQueryClient} from '@tanstack/react-query';
import {AuthGuard} from '@/components/AuthGuard';
import {QueryProvider} from '@/components/QueryProvider';
import {AdminShell} from '@/components/admin/AdminShell';
import {apiClient} from '@/lib/api';
import {
  Globe, Link, Unlink, Check, X, Loader, Shield, FileText,
  BarChart3, Database, Upload, ExternalLink, Plus, Trash2,
} from 'lucide-react';

// ─── Tabs ────────────────────────────────────────────
const TABS = [
  {key:'oauth', label:'OAuth 登录', icon:Globe},
  {key:'sso', label:'SSO / 企业认证', icon:Shield},
  {key:'analytics', label:'统计分析', icon:BarChart3},
  {key:'ipfs', label:'IPFS 存储', icon:Database},
  {key:'import', label:'数据导入', icon:Upload},
];

// ─── Helpers ─────────────────────────────────────────
const ProviderIcon: React.FC<{name: string; icon?: string}> = ({name, icon}) => {
  const short = icon || name?.charAt(0) || '?';
  const bgMap: Record<string, string> = {
    github: 'bg-gray-900 text-white',
    google: 'bg-blue-500 text-white',
    wechat: 'bg-green-500 text-white',
    qq: 'bg-blue-400 text-white',
  };
  return (
    <div className={`w-8 h-8 rounded-lg flex items-center justify-center text-xs font-bold shrink-0 ${bgMap[icon||name.toLowerCase()] || 'bg-blue-100 text-blue-600'}`}>
      {typeof short === 'string' && short.length <= 2 ? short : short?.charAt(0)?.toUpperCase()}
    </div>
  );
};

// ─── Main ────────────────────────────────────────────
function IntegrationsInner() {
  const qc = useQueryClient();
  const [activeTab, setActiveTab] = useState('oauth');

  // ── Queries ──
  const {data: oauthProviders} = useQuery({
    queryKey: ['integ-oauth-providers'],
    queryFn: async () => {
      const r = await apiClient.get<any>('/integrations/oauth/providers');
      const raw = r.success && r.data ? (r.data.providers || r.data) : [];
      return Array.isArray(raw) ? raw : [];
    },
  });

  const {data: linkedAccounts} = useQuery({
    queryKey: ['integ-oauth-linked'],
    queryFn: async () => {
      const r = await apiClient.get<any>('/integrations/oauth/linked-accounts');
      const raw = r.success && r.data ? (r.data.linked_accounts || r.data.accounts || r.data) : [];
      return Array.isArray(raw) ? raw : [];
    },
  });

  const {data: ssoConfig} = useQuery({
    queryKey: ['integ-sso-config'],
    queryFn: async () => {
      const r = await apiClient.get<any>('/integrations/sso/config');
      return r.success && r.data ? r.data : {};
    },
    enabled: activeTab === 'sso',
  });

  const {data: baiduConfigs} = useQuery({
    queryKey: ['integ-baidu-configs'],
    queryFn: async () => {
      const r = await apiClient.get<any>('/integrations/analytics/baidu/configs');
      const raw = r.success && r.data ? (r.data.configs || r.data) : [];
      return Array.isArray(raw) ? raw : [];
    },
    enabled: activeTab === 'analytics',
  });

  const {data: gaConfig} = useQuery({
    queryKey: ['integ-ga-config'],
    queryFn: async () => {
      const r = await apiClient.get<any>('/integrations/analytics/google/config');
      return r.success && r.data ? r.data : null;
    },
    enabled: activeTab === 'analytics',
  });

  const {data: ipfsFiles} = useQuery({
    queryKey: ['integ-ipfs-files'],
    queryFn: async () => {
      const r = await apiClient.get<any>('/integrations/ipfs/files');
      const raw = r.success && r.data ? (r.data.files || r.data) : [];
      return Array.isArray(raw) ? raw : [];
    },
    enabled: activeTab === 'ipfs',
  });

  const {data: wpTemplate} = useQuery({
    queryKey: ['integ-wp-template'],
    queryFn: async () => {
      const r = await apiClient.get<any>('/integrations/wordpress/template');
      return r.success && r.data ? r.data : null;
    },
    enabled: activeTab === 'import',
  });

  // ── Mutations ──
  const unlinkMut = useMutation({
    mutationFn: (provider: string) => apiClient.post(`/integrations/oauth/unlink/${provider}`),
    onSuccess: () => qc.invalidateQueries({queryKey:['integ-oauth-linked']}),
  });

  // ── Hub ──
  const renderTab = () => {
    switch (activeTab) {
      // ═══════════ OAuth ═══════════
      case 'oauth': {
        // Filter out weibo from any dynamic provider list too
        const providers = (Array.isArray(oauthProviders) ? oauthProviders : []).filter((p: any) =>
          (p.name || p.provider || '').toLowerCase() !== 'weibo' && (p.icon || '').toLowerCase() !== 'weibo'
        );
        const linked = Array.isArray(linkedAccounts) ? linkedAccounts : [];
        return (
          <div className="grid lg:grid-cols-2 gap-6">
            {/* Providers */}
            <div className="bg-white dark:bg-gray-900 rounded-2xl border p-6">
              <h3 className="font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2"><Globe className="w-5 h-5"/>OAuth 登录提供商</h3>
              <div className="space-y-3">
                {providers.length > 0 ? providers.map((p: any, i: number) => {
                  const name = p.name || p.provider || p;
                  const isLinked = linked.some((l: any) => (l.provider || l.name || '').toLowerCase() === name.toLowerCase());
                  return (
                    <div key={i} className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded-xl">
                      <div className="flex items-center gap-3">
                        <ProviderIcon name={name} icon={p.icon}/>
                        <span className="text-sm font-medium text-gray-900 dark:text-white">{name}</span>
                      </div>
                      <span className={`px-2 py-0.5 text-xs rounded-full ${isLinked ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
                        {isLinked ? '已连接' : '未连接'}
                      </span>
                    </div>
                  );
                }) : (
                  <p className="text-sm text-gray-400 text-center py-8">暂无提供商</p>
                )}
              </div>
            </div>

            {/* Linked accounts */}
            <div className="bg-white dark:bg-gray-900 rounded-2xl border p-6">
              <h3 className="font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2"><Link className="w-5 h-5"/>已关联账号</h3>
              {linked.length > 0 ? (
                <div className="space-y-3">
                  {linked.map((a: any, i: number) => (
                    <div key={i} className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded-xl">
                      <div className="flex items-center gap-3 min-w-0">
                        <ProviderIcon name={a.provider || a.name} icon={a.icon}/>
                        <div className="min-w-0">
                          <p className="text-sm font-medium text-gray-900 dark:text-white">{a.provider_name || a.provider || a.name}</p>
                          <p className="text-xs text-gray-400 truncate">{a.provider_user_id || a.email || a.username || ''}</p>
                        </div>
                      </div>
                      <button onClick={() => { if(confirm('解绑该账号？')) unlinkMut.mutate(a.provider); }}
                        className="px-3 py-1 text-xs border border-red-200 text-red-500 rounded-lg hover:bg-red-50 shrink-0 ml-2">
                        {unlinkMut.isPending ? <Loader className="w-3 h-3 animate-spin"/> : '解绑'}
                      </button>
                    </div>
                  ))}
                </div>
              ) : <p className="text-sm text-gray-400 text-center py-8">暂无关联账号</p>}
            </div>
          </div>
        );
      }

      // ═══════════ SSO ═══════════
      case 'sso':
        return (
          <div className="bg-white dark:bg-gray-900 rounded-2xl border p-6">
            <h3 className="font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2"><Shield className="w-5 h-5"/>SSO / 企业认证配置</h3>
            {ssoConfig && Object.keys(ssoConfig).length > 0 ? (
              <div className="space-y-3">
                {Object.entries(ssoConfig).map(([key, val]: [string, any]) => (
                  <div key={key} className="flex items-center justify-between py-2.5 border-b border-gray-100 dark:border-gray-800 last:border-0">
                    <span className="text-sm text-gray-700 dark:text-gray-300">{key}</span>
                    <span className="text-sm text-gray-900 dark:text-white font-mono">{typeof val === 'object' ? JSON.stringify(val) : String(val)}</span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="space-y-6">
                <div className="p-6 bg-gray-50 dark:bg-gray-800 rounded-xl text-center">
                  <Shield className="w-10 h-10 text-gray-300 mx-auto mb-3"/>
                  <p className="text-sm text-gray-500">SSO 支持 OAuth2.0 (Google/GitHub/Microsoft)、SAML 2.0、LDAP</p>
                  <p className="text-xs text-gray-400 mt-2">通过 /integrations/sso/oauth/{'{provider}'}/authorize 等端点使用</p>
                </div>
                <div className="grid sm:grid-cols-3 gap-4">
                  <div className="border border-gray-200 dark:border-gray-700 rounded-xl p-4">
                    <p className="text-sm font-medium text-gray-900 dark:text-white">OAuth2.0</p>
                    <p className="text-xs text-gray-400 mt-1">Google / GitHub / Microsoft</p>
                  </div>
                  <div className="border border-gray-200 dark:border-gray-700 rounded-xl p-4">
                    <p className="text-sm font-medium text-gray-900 dark:text-white">SAML 2.0</p>
                    <p className="text-xs text-gray-400 mt-1">Okta / Azure AD / OneLogin</p>
                  </div>
                  <div className="border border-gray-200 dark:border-gray-700 rounded-xl p-4">
                    <p className="text-sm font-medium text-gray-900 dark:text-white">LDAP</p>
                    <p className="text-xs text-gray-400 mt-1">OpenLDAP / Active Directory</p>
                  </div>
                </div>
              </div>
            )}
          </div>
        );

      // ═══════════ Analytics ═══════════
      case 'analytics':
        return (
          <div className="grid lg:grid-cols-2 gap-6">
            {/* Google Analytics */}
            <div className="bg-white dark:bg-gray-900 rounded-2xl border p-6">
              <h3 className="font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
                <BarChart3 className="w-5 h-5"/>Google Analytics
              </h3>
              {gaConfig ? (
                <div className="space-y-2">
                  {[
                    ['Tracking ID', gaConfig.tracking_id],
                    ['Measurement ID', gaConfig.measurement_id],
                    ['页面浏览追踪', gaConfig.enable_page_view_tracking ? '✅ 启用' : '❌ 禁用'],
                    ['事件追踪', gaConfig.enable_event_tracking ? '✅ 启用' : '❌ 禁用'],
                    ['IP 匿名化', gaConfig.anonymize_ip ? '✅ 启用' : '❌ 禁用'],
                    ['采样率', gaConfig.sample_rate ? `${gaConfig.sample_rate}%` : '默认'],
                    ['状态', gaConfig.is_active ? '✅ 活跃' : '❌ 未激活'],
                  ].map(([label, val], i) => (
                    <div key={i} className="flex items-center justify-between py-2 border-b border-gray-100 dark:border-gray-800 last:border-0">
                      <span className="text-sm text-gray-500">{label}</span>
                      <span className="text-sm text-gray-900 dark:text-white">{String(val ?? '—')}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8">
                  <BarChart3 className="w-10 h-10 text-gray-300 mx-auto mb-3"/>
                  <p className="text-sm text-gray-500">尚未配置 Google Analytics</p>
                  <p className="text-xs text-gray-400 mt-1">通过 POST /integrations/analytics/google/config 配置</p>
                </div>
              )}
            </div>

            {/* Baidu Analytics */}
            <div className="bg-white dark:bg-gray-900 rounded-2xl border p-6">
              <h3 className="font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
                <BarChart3 className="w-5 h-5"/>百度统计
              </h3>
              {Array.isArray(baiduConfigs) && baiduConfigs.length > 0 ? (
                <div className="space-y-3">
                  {baiduConfigs.map((cfg: any, i: number) => (
                    <div key={i} className="p-4 bg-gray-50 dark:bg-gray-800 rounded-xl space-y-1">
                      <p className="text-sm font-medium text-gray-900 dark:text-white">{cfg.site_name || cfg.name || `配置 ${i + 1}`}</p>
                      <p className="text-xs text-gray-400 font-mono">{cfg.tracking_id || cfg.site_id || '—'}</p>
                      <span className={`text-[10px] px-1.5 py-0.5 rounded ${cfg.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-200 text-gray-500'}`}>
                        {cfg.is_active ? '活跃' : '未激活'}
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8">
                  <BarChart3 className="w-10 h-10 text-gray-300 mx-auto mb-3"/>
                  <p className="text-sm text-gray-500">尚未配置百度统计</p>
                  <p className="text-xs text-gray-400 mt-1">通过 POST /integrations/analytics/baidu/config 配置</p>
                </div>
              )}
            </div>
          </div>
        );

      // ═══════════ IPFS ═══════════
      case 'ipfs':
        return (
          <div className="grid lg:grid-cols-2 gap-6">
            <div className="bg-white dark:bg-gray-900 rounded-2xl border p-6">
              <h3 className="font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2"><Database className="w-5 h-5"/>IPFS 文件</h3>
              {Array.isArray(ipfsFiles) && ipfsFiles.length > 0 ? (
                <div className="space-y-2">
                  {ipfsFiles.map((f: any, i: number) => (
                    <div key={f.cid || i} className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded-xl">
                      <div className="min-w-0 flex-1">
                        <p className="text-sm text-gray-700 dark:text-gray-300 truncate">{f.name || f.filename || f.cid || '—'}</p>
                        <p className="text-xs text-gray-400 font-mono truncate">{f.cid || ''}</p>
                      </div>
                      <span className="text-[10px] text-gray-400 shrink-0 ml-2">{f.size ? `${(f.size / 1024).toFixed(1)} KB` : ''}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8">
                  <Database className="w-10 h-10 text-gray-300 mx-auto mb-3"/>
                  <p className="text-sm text-gray-500">暂无 IPFS 文件</p>
                  <p className="text-xs text-gray-400 mt-1">通过 POST /integrations/ipfs/upload/file 上传</p>
                </div>
              )}
            </div>
            <div className="bg-white dark:bg-gray-900 rounded-2xl border p-6">
              <h3 className="font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2"><Database className="w-5 h-5"/>关于 IPFS</h3>
              <div className="space-y-3 text-sm text-gray-500">
                <p>IPFS（星际文件系统）用于去中心化存储文章附件和媒体文件。</p>
                <div className="border border-gray-200 dark:border-gray-700 rounded-xl p-4">
                  <p className="text-gray-900 dark:text-white font-medium mb-1">可用操作</p>
                  <ul className="space-y-1 text-xs">
                    <li className="flex items-center gap-2"><Check className="w-3 h-3 text-green-500"/>上传文件</li>
                    <li className="flex items-center gap-2"><Check className="w-3 h-3 text-green-500"/>上传文本</li>
                    <li className="flex items-center gap-2"><Check className="w-3 h-3 text-green-500"/>上传文章</li>
                    <li className="flex items-center gap-2"><Check className="w-3 h-3 text-green-500"/>下载 / 固定文件</li>
                  </ul>
                </div>
                <p className="text-xs text-gray-400">API 端点: /integrations/ipfs/upload/file, /integrations/ipfs/upload/text, /integrations/ipfs/upload/article</p>
              </div>
            </div>
          </div>
        );

      // ═══════════ Import ═══════════
      case 'import':
        return (
          <div className="grid lg:grid-cols-2 gap-6">
            <div className="bg-white dark:bg-gray-900 rounded-2xl border p-6">
              <h3 className="font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2"><Upload className="w-5 h-5"/>WordPress 导入</h3>
              <div className="space-y-4">
                <div className="p-4 bg-gray-50 dark:bg-gray-800 rounded-xl">
                  <p className="text-sm text-gray-700 dark:text-gray-300">从 WordPress WXR 文件导入文章、页面、分类和标签。</p>
                  <p className="text-xs text-gray-400 mt-1">支持标准 WordPress 导出格式 (.xml)</p>
                </div>
                <div className="border border-gray-200 dark:border-gray-700 rounded-xl p-4">
                  <p className="text-sm font-medium text-gray-900 dark:text-white mb-2">导入步骤</p>
                  <ol className="text-xs text-gray-500 space-y-1.5 list-decimal list-inside">
                    <li>在 WordPress 后台导出 WXR 文件</li>
                    <li>POST /integrations/wordpress/parse 解析文件</li>
                    <li>POST /integrations/wordpress/import 导入数据</li>
                  </ol>
                </div>
                {wpTemplate && (
                  <div className="p-4 bg-blue-50 dark:bg-blue-900/10 rounded-xl">
                    <p className="text-xs font-medium text-blue-700">模板信息</p>
                    <pre className="text-xs mt-1 text-blue-600 whitespace-pre-wrap">{JSON.stringify(wpTemplate, null, 2).slice(0, 300)}</pre>
                  </div>
                )}
              </div>
            </div>

            <div className="bg-white dark:bg-gray-900 rounded-2xl border p-6">
              <h3 className="font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2"><Upload className="w-5 h-5"/>其他导入源</h3>
              <div className="space-y-3">
                {[
                  {name:'Halo', desc:'从 Halo 博客导入文章和数据', endpoint:'POST /integrations/halo/*'},
                  {name:'Jekyll', desc:'从 Jekyll 站点导入 Markdown', endpoint:'shared/services/integrations/'},
                  {name:'Hexo', desc:'从 Hexo 站点导入文章', endpoint:'shared/services/integrations/'},
                  {name:'Ghost', desc:'从 Ghost 平台导入数据', endpoint:'shared/services/integrations/'},
                  {name:'Medium', desc:'从 Medium 导出导入文章', endpoint:'shared/services/integrations/'},
                  {name:'JSON/CSV', desc:'通用 JSON/CSV 格式导入', endpoint:'shared/services/integrations/'},
                ].map((src, i) => (
                  <div key={i} className="flex items-center justify-between p-3 border border-gray-100 dark:border-gray-800 rounded-xl">
                    <div>
                      <p className="text-sm font-medium text-gray-900 dark:text-white">{src.name}</p>
                      <p className="text-xs text-gray-400">{src.desc}</p>
                    </div>
                    <span className="text-[10px] text-gray-400 font-mono">{src.endpoint}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        );
    }
  };

  return (
    <AdminShell title="集成管理">
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

      {renderTab()}
    </AdminShell>
  );
}

export default function AdminIntegrations() {
  return <AuthGuard><QueryProvider><IntegrationsInner/></QueryProvider></AuthGuard>;
}
