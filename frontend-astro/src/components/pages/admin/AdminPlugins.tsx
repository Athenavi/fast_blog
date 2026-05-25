'use client';

import React, {useState} from 'react';
import {useQuery, useMutation, useQueryClient} from '@tanstack/react-query';
import AuthGuard from '@/components/auth/AuthGuard';
import QueryProvider from '@/components/providers/QueryProvider';
import AdminShell from '@/components/layouts/AdminShell';
import apiClient from '@/lib/api-client';
import {
  Puzzle, Download, Upload, Settings, Trash2, RefreshCw,
  Search, Filter, Star, ExternalLink, Info
} from 'lucide-react';

interface Plugin {
  slug: string;
  name: string;
  version: string;
  description?: string;
  author?: string;
  author_url?: string;
  is_active: boolean;
  is_installed: boolean;
  capabilities?: string[];
  created_at?: string;
  updated_at?: string;
}

function PluginsInner() {
  const qc = useQueryClient();
  const [activeTab, setActiveTab] = useState<'installed' | 'marketplace'>('installed');
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedPlugin, setSelectedPlugin] = useState<Plugin | null>(null);
  const [showConfig, setShowConfig] = useState(false);

  // 查询已安装插件
  const {data: installedPlugins, isLoading: installedLoading} = useQuery({
    queryKey: ['plugins-installed'],
    queryFn: async () => {
      const res = await apiClient.get('/plugins/active');
      return res.data || [];
    },
    enabled: activeTab === 'installed'
  });

  // 查询插件市场
  const {data: marketplacePlugins, isLoading: marketplaceLoading} = useQuery({
    queryKey: ['plugins-marketplace'],
    queryFn: async () => {
      const res = await apiClient.get('/plugins/marketplace');
      return res.data || [];
    },
    enabled: activeTab === 'marketplace'
  });

  // 安装插件
  const installMut = useMutation({
    mutationFn: (slug: string) => apiClient.post('/plugins/install', {slug, capabilities: []}),
    onSuccess: () => {
      qc.invalidateQueries({queryKey: ['plugins-installed']});
      qc.invalidateQueries({queryKey: ['plugins-marketplace']});
      alert('插件安装成功！');
    }
  });

  // 激活/停用插件
  const toggleMut = useMutation({
    mutationFn: ({slug, activate}: { slug: string; activate: boolean }) =>
        activate ? apiClient.post(`/plugins/${slug}/activate`) : apiClient.post(`/plugins/${slug}/deactivate`),
    onSuccess: () => {
      qc.invalidateQueries({queryKey: ['plugins-installed']});
    }
  });

  // 卸载插件
  const uninstallMut = useMutation({
    mutationFn: (slug: string) => apiClient.delete(`/plugins/${slug}/uninstall`),
    onSuccess: () => {
      qc.invalidateQueries({queryKey: ['plugins-installed']});
      qc.invalidateQueries({queryKey: ['plugins-marketplace']});
      alert('插件已卸载！');
    }
  });

  const handleInstall = (slug: string) => {
    if (confirm('确定要安装此插件吗？')) {
      installMut.mutate(slug);
    }
  };

  const handleUninstall = (slug: string) => {
    if (confirm('确定要卸载此插件吗？此操作不可恢复。')) {
      uninstallMut.mutate(slug);
    }
  };

  const filteredPlugins = (plugins: Plugin[]) => {
    return plugins.filter((plugin: Plugin) => {
      return !searchTerm ||
          plugin.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
          plugin.description?.toLowerCase().includes(searchTerm.toLowerCase());
    });
  };

  const renderPluginCard = (plugin: Plugin, isInstalled: boolean = false) => (
      <div key={plugin.slug}
           className="bg-white dark:bg-gray-900 rounded-xl border overflow-hidden hover:shadow-lg transition">
        <div className="p-5">
          <div className="flex items-start justify-between mb-3">
            <div className="flex-1">
              <h3 className="font-semibold text-gray-900 dark:text-white">{plugin.name}</h3>
              <p className="text-xs text-gray-500 mt-0.5">v{plugin.version} · by {plugin.author || 'Unknown'}</p>
            </div>
            {isInstalled && (
                <button
                    onClick={() => toggleMut.mutate({slug: plugin.slug, activate: !plugin.is_active})}
                    className={`px-3 py-1 rounded-full text-xs font-medium transition ${
                        plugin.is_active
                            ? 'bg-green-100 text-green-700 hover:bg-green-200'
                            : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                    }`}
                >
                  {plugin.is_active ? '已启用' : '已禁用'}
                </button>
            )}
          </div>

          <p className="text-sm text-gray-600 dark:text-gray-400 mb-4 line-clamp-2">
            {plugin.description || '暂无描述'}
          </p>

          {/* 能力标签 */}
          {plugin.capabilities && plugin.capabilities.length > 0 && (
              <div className="flex flex-wrap gap-1 mb-4">
                {plugin.capabilities.slice(0, 3).map((cap: string, i: number) => (
                    <span key={i}
                          className="px-2 py-0.5 bg-blue-50 dark:bg-blue-900/20 text-blue-600 text-[10px] rounded">
                {cap}
              </span>
                ))}
              </div>
          )}

          {/* 操作按钮 */}
          <div className="flex gap-2">
            {!isInstalled ? (
                <button
                    onClick={() => handleInstall(plugin.slug)}
                    disabled={installMut.isPending}
                    className="flex-1 px-3 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 transition flex items-center justify-center gap-1.5"
                >
                  <Download className="w-4 h-4"/>
                  安装
                </button>
            ) : (
                <>
                  <button
                      onClick={() => {
                        setSelectedPlugin(plugin);
                        setShowConfig(true);
                      }}
                      className="px-3 py-2 border text-sm rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition"
                  >
                    <Settings className="w-4 h-4"/>
                  </button>
                  {!plugin.is_active && (
                      <button
                          onClick={() => handleUninstall(plugin.slug)}
                          disabled={uninstallMut.isPending}
                          className="px-3 py-2 border text-red-600 text-sm rounded-lg hover:bg-red-50 dark:hover:bg-red-900/20 transition"
                      >
                        <Trash2 className="w-4 h-4"/>
                      </button>
                  )}
                </>
            )}
          </div>
        </div>
      </div>
  );

  return (
      <AdminShell title="插件市场">
        <div className="space-y-6">
          {/* 标签页 */}
          <div className="flex gap-2">
            <button
                onClick={() => setActiveTab('installed')}
                className={`px-4 py-2 rounded-lg font-medium transition ${
                    activeTab === 'installed'
                        ? 'bg-blue-600 text-white'
                        : 'bg-white dark:bg-gray-900 border hover:bg-gray-50 dark:hover:bg-gray-800'
                }`}
            >
              <Puzzle className="w-4 h-4 inline mr-1.5"/>
              已安装
            </button>
            <button
                onClick={() => setActiveTab('marketplace')}
                className={`px-4 py-2 rounded-lg font-medium transition ${
                    activeTab === 'marketplace'
                        ? 'bg-blue-600 text-white'
                        : 'bg-white dark:bg-gray-900 border hover:bg-gray-50 dark:hover:bg-gray-800'
                }`}
            >
              <Download className="w-4 h-4 inline mr-1.5"/>
              插件市场
            </button>
          </div>

          {/* 搜索栏 */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400"/>
            <input
                type="text"
                placeholder="搜索插件..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border rounded-lg bg-white dark:bg-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {/* 插件网格 */}
          {activeTab === 'installed' ? (
              installedLoading ? (
                  <div className="text-center py-12">
                    <div
                        className="animate-spin w-8 h-8 border-2 border-blue-600 border-t-transparent rounded-full mx-auto"/>
                  </div>
              ) : !installedPlugins?.length ? (
                  <div className="text-center py-12 text-gray-400">
                    <Puzzle className="w-16 h-16 mx-auto mb-4 opacity-30"/>
                    <p>尚未安装任何插件</p>
                    <button
                        onClick={() => setActiveTab('marketplace')}
                        className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
                    >
                      浏览插件市场
              </button>
            </div>
              ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {filteredPlugins(installedPlugins).map((plugin: Plugin) => renderPluginCard(plugin, true))}
            </div>
              )
          ) : (
              marketplaceLoading ? (
                  <div className="text-center py-12">
                    <div
                        className="animate-spin w-8 h-8 border-2 border-blue-600 border-t-transparent rounded-full mx-auto"/>
                  </div>
              ) : !marketplacePlugins?.length ? (
                  <div className="text-center py-12 text-gray-400">
                    <Download className="w-16 h-16 mx-auto mb-4 opacity-30"/>
                    <p>暂无可用插件</p>
                  </div>
              ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {filteredPlugins(marketplacePlugins).map((plugin: Plugin) => renderPluginCard(plugin, false))}
                  </div>
              )
          )}
        </div>

        {/* 配置对话框 */}
        {showConfig && selectedPlugin && (
            <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
              <div className="bg-white dark:bg-gray-900 rounded-2xl max-w-2xl w-full">
                <div className="px-6 py-4 border-b flex items-center justify-between">
                  <h3 className="font-semibold text-lg">插件配置: {selectedPlugin.name}</h3>
                  <button
                      onClick={() => setShowConfig(false)}
                      className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg"
                  >
                    ✕
                  </button>
                </div>
                <div className="p-6 space-y-4">
                  <div>
                    <div className="text-sm font-medium text-gray-500 mb-1">插件信息</div>
                    <div className="bg-gray-50 dark:bg-gray-800 p-3 rounded-lg text-sm space-y-1">
                      <div><span className="text-gray-500">名称:</span> {selectedPlugin.name}</div>
                      <div><span className="text-gray-500">版本:</span> v{selectedPlugin.version}</div>
                      <div><span className="text-gray-500">作者:</span> {selectedPlugin.author || 'N/A'}</div>
                      <div><span className="text-gray-500">状态:</span> {selectedPlugin.is_active ? '已启用' : '已禁用'}
                      </div>
                    </div>
                  </div>

                  {selectedPlugin.capabilities && selectedPlugin.capabilities.length > 0 && (
                      <div>
                        <div className="text-sm font-medium text-gray-500 mb-1">权限能力</div>
                        <div className="flex flex-wrap gap-2">
                          {selectedPlugin.capabilities.map((cap: string, i: number) => (
                              <span key={i}
                                    className="px-2 py-1 bg-blue-50 dark:bg-blue-900/20 text-blue-600 text-xs rounded">
                        {cap}
                      </span>
                          ))}
                        </div>
                      </div>
                  )}

                  <div
                      className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-3">
                    <div className="flex items-start gap-2">
                      <Info className="w-4 h-4 text-yellow-600 mt-0.5"/>
                      <p className="text-sm text-yellow-800 dark:text-yellow-200">
                        此插件的配置选项将在后续版本中提供。当前版本仅支持启用/禁用操作。
                      </p>
                    </div>
                  </div>
                </div>
                <div className="px-6 py-4 border-t flex justify-end">
                  <button
                      onClick={() => setShowConfig(false)}
                      className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
                  >
                    关闭
                  </button>
                </div>
          </div>
            </div>
        )}
    </AdminShell>
  );
}

export default function AdminPlugins() {
  return (
      <AuthGuard>
        <QueryProvider>
          <PluginsInner/>
        </QueryProvider>
      </AuthGuard>
  );
}
