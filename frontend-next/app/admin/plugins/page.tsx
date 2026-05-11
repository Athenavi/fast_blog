/**
 * 插件市场 - 浏览、安装和管理插件
 */

'use client';

import React, {useEffect, useState} from 'react';
import {Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle} from '@/components/ui/card';
import {Button} from '@/components/ui/button';
import {Badge} from '@/components/ui/badge';
import {Input} from '@/components/ui/input';
import {Tabs, TabsContent, TabsList, TabsTrigger} from '@/components/ui/tabs';
import {
  AlertCircle,
  Calendar,
  Check,
  Database,
  Download,
  Package,
  RefreshCw,
  Search,
  Settings,
  Star,
  Users,
  X,
  Zap
} from 'lucide-react';
import apiClient from '@/lib/api-client';

interface Plugin {
  id: number;
  name: string;
  slug: string;
  version: string;
  description: string;
  author: string;
  icon?: string;
  rating: number;
  downloads: number;
  last_updated: string;
  is_installed: boolean;
  is_active: boolean;
  category: string;
  tags: string[];
  requires_version?: string;
  screenshot?: string;
}

const PluginMarketplace = () => {
  const [activeTab, setActiveTab] = useState('browse');
  const [plugins, setPlugins] = useState<Plugin[]>([]);
  const [installedPlugins, setInstalledPlugins] = useState<Plugin[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [loading, setLoading] = useState(false);
  const [installingPlugin, setInstallingPlugin] = useState<number | null>(null);
  const [syncingConfig, setSyncingConfig] = useState(false);
    const [syncResult, setSyncResult] = useState<{
        synced?: number;
        created?: number;
        updated?: number;
        settings_synced?: number;
        total_local_plugins?: number;
        total_db_plugins?: number;
    } | null>(null);

  useEffect(() => {
    loadPlugins();
    loadInstalledPlugins();
  }, []);

  // 加载可用插件
  const loadPlugins = async () => {
    try {
      const response = await apiClient.get('/api/v1/plugins/marketplace');
      if (response.success && response.data) {
        setPlugins((response.data as any).plugins || []);
      }
    } catch (error) {
      console.error('Failed to load plugins:', error);
    }
  };

  // 加载已安装插件
  const loadInstalledPlugins = async () => {
    try {
      const response = await apiClient.get('/api/v1/plugins');
      if (response.success && response.data) {
        setInstalledPlugins((response.data as any).plugins || []);
      }
    } catch (error) {
      console.error('Failed to load installed plugins:', error);
    }
  };

  // 安装插件
  const handleInstallPlugin = async (plugin: Plugin) => {
    if (!confirm(`确定要安装插件 "${plugin.name}" 吗？`)) {
      return;
    }

    setInstallingPlugin(plugin.id);
    try {
      const response = await apiClient.post('/api/v1/plugins/install', {
        plugin_slug: plugin.slug
      });

      if (response.success) {
        alert('插件安装成功');
        loadInstalledPlugins();
        loadPlugins();
      } else {
        alert(response.error || '安装失败');
      }
    } catch (error) {
      console.error('Failed to install plugin:', error);
      alert('安装失败');
    } finally {
      setInstallingPlugin(null);
    }
  };

  // 激活/停用插件
  const handleTogglePlugin = async (plugin: Plugin) => {
    try {
      const endpoint = plugin.is_active
          ? `/api/v1/plugins/${plugin.slug}/deactivate`
          : `/api/v1/plugins/${plugin.slug}/activate`;

      const response = await apiClient.post(endpoint);

      if (response.success) {
        loadInstalledPlugins();
        alert(plugin.is_active ? '插件已停用' : '插件已激活');
      } else {
        alert(response.error || '操作失败');
      }
    } catch (error) {
      console.error('Failed to toggle plugin:', error);
      alert('操作失败');
    }
  };

  // 卸载插件
  const handleUninstallPlugin = async (plugin: Plugin) => {
    if (!confirm(`确定要卸载插件 "${plugin.name}" 吗？此操作不可恢复。`)) {
      return;
    }

    try {
      const response = await apiClient.delete(`/api/v1/plugins/${plugin.slug}`);

      if (response.success) {
        loadInstalledPlugins();
        loadPlugins();
        alert('插件已卸载');
      } else {
        alert(response.error || '卸载失败');
      }
    } catch (error) {
      console.error('Failed to uninstall plugin:', error);
      alert('卸载失败');
    }
  };

  // 同步插件配置
  const handleSyncConfig = async () => {
    if (!confirm('确定要同步插件配置吗？\n\n此操作将：\n1. 扫描本地 plugins 目录\n2. 读取 plugin_state.json\n3. 同步状态到数据库')) {
      return;
    }

    setSyncingConfig(true);
    setSyncResult(null);

    try {
      const response = await apiClient.post('/api/v1/plugins/sync-config');

      if (response.success && response.data) {
          const data = response.data as any;
          setSyncResult(data);
        // 重新加载插件列表
        await loadInstalledPlugins();
        await loadPlugins();

        // 显示成功消息
        alert(
            `插件配置同步成功！\n\n` +
            `同步数量: ${data.synced}\n` +
            `新建记录: ${data.created}\n` +
            `更新记录: ${data.updated}\n` +
            `设置同步: ${data.settings_synced || 0}\n` +
            `本地插件: ${data.total_local_plugins}\n` +
            `数据库插件: ${data.total_db_plugins}`
        );
      } else {
        alert(response.error || '同步失败');
      }
    } catch (error) {
      console.error('Failed to sync plugin config:', error);
      alert('同步失败: ' + (error as Error).message);
    } finally {
      setSyncingConfig(false);
    }
  };



  // 过滤插件
  const filteredPlugins = plugins.filter(plugin => {
    const matchesSearch = plugin.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        plugin.description.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesCategory = selectedCategory === 'all' || plugin.category === selectedCategory;
    return matchesSearch && matchesCategory;
  });

  // 获取所有分类
  const categories = ['all', ...Array.from(new Set(plugins.map(p => p.category)))];

  // 格式化日期
  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('zh-CN');
  };

  // 渲染星级评分
  const renderRating = (rating: number) => {
    return (
        <div className="flex items-center gap-1">
          {[1, 2, 3, 4, 5].map((star) => (
              <Star
                  key={star}
                  className={`w-4 h-4 ${
                      star <= rating ? 'fill-yellow-400 text-yellow-400' : 'text-gray-300'
                  }`}
              />
          ))}
          <span className="text-sm text-gray-600 ml-1">{rating}</span>
        </div>
    );
  };

  return (
      <div className="space-y-6">
        {/* 页面标题和操作按钮 */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white">插件市场</h1>
            <p className="text-gray-600 dark:text-gray-400 mt-1">
              浏览、安装和管理插件，扩展系统功能
            </p>
          </div>
          <Button
              onClick={handleSyncConfig}
              disabled={syncingConfig}
              className="flex items-center gap-2"
          >
            {syncingConfig ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin"/>
                  同步中...
                </>
            ) : (
                <>
                  <Database className="w-4 h-4"/>
                  同步配置
                </>
            )}
          </Button>
        </div>

        {/* 同步结果提示 */}
        {syncResult && (
            <Card className="border-blue-200 bg-blue-50 dark:bg-blue-950 dark:border-blue-800">
              <CardContent className="pt-6">
                <div className="flex items-start gap-3">
                  <AlertCircle className="w-5 h-5 text-blue-600 dark:text-blue-400 mt-0.5"/>
                  <div className="flex-1">
                    <h3 className="font-medium text-blue-900 dark:text-blue-100 mb-2">
                      同步完成
                    </h3>
                    <div className="grid grid-cols-2 md:grid-cols-6 gap-4 text-sm">
                      <div>
                        <div className="text-gray-600 dark:text-gray-400">同步数量</div>
                        <div className="text-lg font-semibold text-blue-900 dark:text-blue-100">
                          {syncResult.synced}
                        </div>
                      </div>
                      <div>
                        <div className="text-gray-600 dark:text-gray-400">新建记录</div>
                        <div className="text-lg font-semibold text-green-600 dark:text-green-400">
                          {syncResult.created}
                        </div>
                      </div>
                      <div>
                        <div className="text-gray-600 dark:text-gray-400">更新记录</div>
                        <div className="text-lg font-semibold text-orange-600 dark:text-orange-400">
                          {syncResult.updated}
                        </div>
                      </div>
                      <div>
                        <div className="text-gray-600 dark:text-gray-400">设置同步</div>
                        <div className="text-lg font-semibold text-purple-600 dark:text-purple-400">
                          {syncResult.settings_synced || 0}
                        </div>
                      </div>
                      <div>
                        <div className="text-gray-600 dark:text-gray-400">本地插件</div>
                        <div className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                          {syncResult.total_local_plugins}
                        </div>
                      </div>
                      <div>
                        <div className="text-gray-600 dark:text-gray-400">数据库插件</div>
                        <div className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                          {syncResult.total_db_plugins}
                        </div>
                      </div>
                    </div>
                  </div>
                  <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setSyncResult(null)}
                      className="h-8 w-8 p-0"
                  >
                    <X className="w-4 h-4"/>
                  </Button>
                </div>
              </CardContent>
            </Card>
        )}

        {/* 标签页 */}
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="browse" className="flex items-center gap-2">
              <Package className="w-4 h-4"/>
              浏览插件
            </TabsTrigger>
            <TabsTrigger value="installed" className="flex items-center gap-2">
              <Check className="w-4 h-4"/>
              已安装 ({installedPlugins.length})
            </TabsTrigger>
          </TabsList>

          {/* 浏览插件 */}
          <TabsContent value="browse" className="space-y-4">
            {/* 搜索和过滤 */}
            <Card>
              <CardContent className="pt-6">
                <div className="flex flex-col md:flex-row gap-4">
                  <div className="flex-1 relative">
                    <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400"/>
                    <Input
                        placeholder="搜索插件..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className="pl-10"
                    />
                  </div>
                  <div className="flex gap-2 overflow-x-auto">
                    {categories.map((category) => (
                        <Button
                            key={category}
                            variant={selectedCategory === category ? "default" : "outline"}
                            size="sm"
                            onClick={() => setSelectedCategory(category)}
                            className="whitespace-nowrap"
                        >
                          {category === 'all' ? '全部' : category}
                        </Button>
                    ))}
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* 插件列表 */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {filteredPlugins.map((plugin) => (
                  <Card key={plugin.id} className="hover:shadow-lg transition-shadow">
                    <CardHeader>
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <CardTitle className="text-lg mb-1">{plugin.name}</CardTitle>
                          <CardDescription>by {plugin.author}</CardDescription>
                    </div>
                        {plugin.icon && (
                            <img
                                src={plugin.icon}
                                alt={plugin.name}
                                className="w-12 h-12 rounded-lg object-cover"
                            />
                        )}
                      </div>
                    </CardHeader>
                    <CardContent className="space-y-3">
                      <p className="text-sm text-gray-600 dark:text-gray-400 line-clamp-2">
                        {plugin.description}
                      </p>

                      <div className="flex items-center gap-4 text-sm text-gray-500">
                        <div className="flex items-center gap-1">
                          <Users className="w-4 h-4"/>
                          {plugin.downloads}
                        </div>
                        <div className="flex items-center gap-1">
                          <Calendar className="w-4 h-4"/>
                          {formatDate(plugin.last_updated)}
                        </div>
                      </div>

                      {renderRating(plugin.rating)}

                      <div className="flex flex-wrap gap-1">
                        {plugin.tags.slice(0, 3).map((tag) => (
                            <Badge key={tag} variant="secondary" className="text-xs">
                              {tag}
                            </Badge>
                        ))}
                      </div>

                      {plugin.requires_version && (
                          <div className="text-xs text-gray-500">
                            需要版本: {plugin.requires_version}
                          </div>
                      )}
                    </CardContent>
                    <CardFooter>
                      {plugin.is_installed ? (
                          <Badge variant="default" className="w-full justify-center">
                            <Check className="w-4 h-4 mr-2"/>
                            已安装
                          </Badge>
                      ) : (
                          <Button
                              className="w-full"
                              onClick={() => handleInstallPlugin(plugin)}
                              disabled={installingPlugin === plugin.id}
                          >
                            {installingPlugin === plugin.id ? (
                                <>
                                  <RefreshCw className="w-4 h-4 mr-2 animate-spin"/>
                                  安装中...
                                </>
                            ) : (
                                <>
                                  <Download className="w-4 h-4 mr-2"/>
                                  安装
                                </>
                            )}
                          </Button>
                      )}
                    </CardFooter>
                  </Card>
              ))}
            </div>

            {filteredPlugins.length === 0 && (
                <Card>
                  <CardContent className="py-12 text-center">
                    <Package className="w-16 h-16 mx-auto text-gray-300 mb-4"/>
                    <p className="text-gray-500">没有找到匹配的插件</p>
                  </CardContent>
                </Card>
            )}
          </TabsContent>

          {/* 已安装插件 */}
          <TabsContent value="installed" className="space-y-4">
            <div className="grid grid-cols-1 gap-4">
              {installedPlugins.map((plugin) => (
                  <Card key={plugin.id}>
                    <CardContent className="pt-6">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-4 flex-1">
                          {plugin.icon && (
                              <img
                                  src={plugin.icon}
                                  alt={plugin.name}
                                  className="w-16 h-16 rounded-lg object-cover"
                              />
                          )}
                          <div className="flex-1">
                            <div className="flex items-center gap-2 mb-1">
                              <h3 className="font-medium text-gray-900 dark:text-white">
                                {plugin.name}
                              </h3>
                              <Badge variant={plugin.is_active ? "default" : "secondary"}>
                                {plugin.is_active ? '已激活' : '已停用'}
                              </Badge>
                            </div>
                            <p className="text-sm text-gray-600 dark:text-gray-400">
                              {plugin.description}
                            </p>
                            <div className="flex items-center gap-4 mt-2 text-xs text-gray-500">
                              <span>版本: {plugin.version}</span>
                              <span>作者: {plugin.author}</span>
                            </div>
                          </div>
                        </div>

                        <div className="flex items-center gap-2">
                          <Button
                              size="sm"
                              variant="outline"
                              onClick={() => handleTogglePlugin(plugin)}
                          >
                            {plugin.is_active ? (
                                <>
                                  <X className="w-4 h-4 mr-2"/>
                                  停用
                                </>
                            ) : (
                                <>
                                  <Zap className="w-4 h-4 mr-2"/>
                                  激活
                                </>
                            )}
                          </Button>
                          <Button
                              size="sm"
                              variant="default"
                              onClick={() => window.location.href = `/admin/plugins/settings?slug=${plugin.slug}`}
                          >
                            <Settings className="w-4 h-4 mr-2"/>
                            配置
                          </Button>
                          <Button
                              size="sm"
                              variant="outline"
                              onClick={() => handleUninstallPlugin(plugin)}
                              className="text-red-600 hover:text-red-700"
                              title="卸载插件"
                          >
                            <X className="w-4 h-4"/>
                          </Button>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
              ))}
            </div>

            {installedPlugins.length === 0 && (
                <Card>
                  <CardContent className="py-12 text-center">
                    <Package className="w-16 h-16 mx-auto text-gray-300 mb-4"/>
                    <p className="text-gray-500 mb-4">还没有安装任何插件</p>
                    <Button onClick={() => setActiveTab('browse')}>
                      浏览插件市场
                    </Button>
                  </CardContent>
                </Card>
            )}
          </TabsContent>
        </Tabs>


      </div>
  );
};

export default PluginMarketplace;
