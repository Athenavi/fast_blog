'use client';

/**
 * 插件市场页面
 * 浏览、安装和管理插件
 */

import {useEffect, useState} from 'react';
import {Card, CardContent, CardDescription, CardHeader, CardTitle} from '@/components/ui/card';
import {Button} from '@/components/ui/button';
import {Input} from '@/components/ui/input';
import {Badge} from '@/components/ui/badge';
import {Tabs, TabsContent, TabsList, TabsTrigger} from '@/components/ui/tabs';
import {Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle} from '@/components/ui/dialog';
import {apiClient} from '@/lib/api-client';

interface Plugin {
    slug: string;
    name: string;
    description: string;
    version: string;
    author: string;
    rating: number;
    installs: number;
    category: string;
    icon?: string;
    installed?: boolean;
    has_update?: boolean;
}

export default function PluginMarketPage() {
    const [plugins, setPlugins] = useState<Plugin[]>([]);
    const [featured, setFeatured] = useState<Plugin[]>([]);
    const [categories, setCategories] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [searchQuery, setSearchQuery] = useState('');
    const [selectedCategory, setSelectedCategory] = useState('all');
    const [selectedPlugin, setSelectedPlugin] = useState<Plugin | null>(null);
    const [detailDialogOpen, setDetailDialogOpen] = useState(false);
    const [installing, setInstalling] = useState<string | null>(null);

    // 加载数据
    useEffect(() => {
        loadData();
    }, []);

    const loadData = async () => {
        try {
            setLoading(true);

            // 并行加载
            const [pluginsRes, featuredRes, categoriesRes] = await Promise.all([
                apiClient.get('/plugin-market/plugins'),
                apiClient.get('/plugin-market/featured'),
                apiClient.get('/plugin-market/categories'),
            ]);

            if (pluginsRes.success) {
                setPlugins((pluginsRes.data as any).plugins || []);
            }

            if (featuredRes.success) {
                setFeatured(featuredRes.data as Plugin[] || []);
            }

            if (categoriesRes.success) {
                setCategories(categoriesRes.data as any[] || []);
            }
        } catch (error) {
            console.error('Failed to load plugin market:', error);
        } finally {
            setLoading(false);
        }
    };

    // 搜索插件
    const handleSearch = async () => {
        try {
            setLoading(true);
            const response = await apiClient.get('/plugin-market/plugins', {
                params: {
                    search: searchQuery,
                    category: selectedCategory !== 'all' ? selectedCategory : undefined,
                }
            });

            if (response.success) {
                setPlugins((response.data as any).plugins || []);
            }
        } catch (error) {
            console.error('Search failed:', error);
        } finally {
            setLoading(false);
        }
    };

    // 安装插件
    const handleInstall = async (pluginSlug: string) => {
        try {
            setInstalling(pluginSlug);

            const response = await apiClient.post('/plugin-market/install', {
                plugin_slug: pluginSlug,
            });

            if (response.success) {
                alert('插件安装成功!');
                // 刷新列表
                await loadData();
            } else {
                alert('安装失败: ' + (response.error || '未知错误'));
            }
        } catch (error) {
            console.error('Install failed:', error);
            alert('安装失败,请重试');
        } finally {
            setInstalling(null);
        }
    };

    // 更新插件
    const handleUpdate = async (pluginSlug: string) => {
        try {
            setInstalling(pluginSlug);

            const response = await apiClient.post('/plugin-market/update', {
                plugin_slug: pluginSlug,
            });

            if (response.success) {
                alert('插件更新成功!');
                await loadData();
            } else {
                alert('更新失败: ' + (response.error || '未知错误'));
            }
        } catch (error) {
            console.error('Update failed:', error);
            alert('更新失败,请重试');
        } finally {
            setInstalling(null);
        }
    };

    // 卸载插件
    const handleUninstall = async (pluginSlug: string, pluginName: string) => {
        if (!confirm(`确定要卸载 ${pluginName} 吗?\n卸载后数据将被保留,但插件将不再可用。`)) {
            return;
        }

        try {
            setInstalling(pluginSlug);

            const response = await apiClient.post('/plugin-market/uninstall', {
                plugin_slug: pluginSlug,
            });

            if (response.success) {
                alert('插件卸载成功!');
                await loadData();
            } else {
                alert('卸载失败: ' + (response.error || '未知错误'));
            }
        } catch (error) {
            console.error('Uninstall failed:', error);
            alert('卸载失败,请重试');
        } finally {
            setInstalling(null);
        }
    };

    // 查看插件详情
    const viewPluginDetail = async (plugin: Plugin) => {
        try {
            const response = await apiClient.get(`/plugin-market/plugins/${plugin.slug}`);

            if (response.success) {
                setSelectedPlugin(response.data as Plugin);
                setDetailDialogOpen(true);
            }
        } catch (error) {
            console.error('Failed to get plugin detail:', error);
        }
    };

    // 渲染星级评分
    const renderRating = (rating: number) => {
        const stars: React.JSX.Element[] = [];
        for (let i = 1; i <= 5; i++) {
            stars.push(
                <span key={i} className={i <= rating ? 'text-yellow-400' : 'text-gray-300'}>
          ★
        </span>
            );
        }
        return <div className="flex items-center gap-1">{stars}</div>;
    };

    if (loading && plugins.length === 0) {
        return (
            <div className="flex items-center justify-center min-h-screen">
                <div className="text-center">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
                    <p className="text-gray-600 dark:text-gray-400">加载中...</p>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
            {/* 顶部栏 */}
            <div className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 sticky top-0 z-10">
                <div className="container mx-auto px-4 py-4">
                    <div className="flex items-center justify-between mb-4">
                        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">插件市场</h1>
                        <Button onClick={() => loadData()} variant="outline">
                            刷新
                        </Button>
                    </div>

                    {/* 搜索栏 */}
                    <div className="flex gap-2">
                        <Input
                            placeholder="搜索插件..."
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
                            className="flex-1"
                        />
                        <Button onClick={handleSearch}>搜索</Button>
                    </div>
                </div>
            </div>

            <div className="container mx-auto px-4 py-8">
                <Tabs defaultValue="browse">
                    <TabsList className="mb-6">
                        <TabsTrigger value="browse">浏览插件</TabsTrigger>
                        <TabsTrigger value="installed">已安装</TabsTrigger>
                        <TabsTrigger value="updates">更新</TabsTrigger>
                    </TabsList>

                    {/* 浏览插件 */}
                    <TabsContent value="browse">
                        {/* 推荐插件 */}
                        {featured.length > 0 && (
                            <div className="mb-8">
                                <h2 className="text-xl font-semibold mb-4 text-gray-900 dark:text-white">推荐插件</h2>
                                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                                    {featured.map((plugin) => (
                                        <Card key={plugin.slug} className="hover:shadow-lg transition cursor-pointer"
                                              onClick={() => viewPluginDetail(plugin)}>
                                            <CardHeader>
                                                <div className="flex items-start justify-between">
                                                    <div className="text-4xl">{plugin.icon || '📦'}</div>
                                                    {plugin.installed && <Badge variant="secondary">已安装</Badge>}
                                                </div>
                                                <CardTitle className="text-lg mt-2">{plugin.name}</CardTitle>
                                                <CardDescription
                                                    className="line-clamp-2">{plugin.description}</CardDescription>
                                            </CardHeader>
                                            <CardContent>
                                                <div
                                                    className="flex items-center justify-between text-sm text-gray-600 dark:text-gray-400 mb-3">
                                                    <div className="flex items-center gap-2">
                                                        {renderRating(plugin.rating)}
                                                        <span>({plugin.rating})</span>
                                                    </div>
                                                    <span>{plugin.installs?.toLocaleString()} 次安装</span>
                                                </div>
                                                <Button
                                                    className="w-full"
                                                    onClick={(e) => {
                                                        e.stopPropagation();
                                                        plugin.installed ? handleUpdate(plugin.slug) : handleInstall(plugin.slug);
                                                    }}
                                                    disabled={installing === plugin.slug}
                                                >
                                                    {installing === plugin.slug ? '处理中...' : plugin.installed ? '更新' : '安装'}
                                                </Button>
                                            </CardContent>
                                        </Card>
                                    ))}
                                </div>
                            </div>
                        )}

                        {/* 所有插件 */}
                        <div>
                            <h2 className="text-xl font-semibold mb-4 text-gray-900 dark:text-white">所有插件</h2>

                            {/* 分类筛选 */}
                            <div className="flex gap-2 mb-4 flex-wrap">
                                {categories.map((cat) => (
                                    <Button
                                        key={cat.slug}
                                        variant={selectedCategory === cat.slug ? 'default' : 'outline'}
                                        size="sm"
                                        onClick={() => {
                                            setSelectedCategory(cat.slug);
                                            handleSearch();
                                        }}
                                    >
                                        {cat.name}
                                    </Button>
                                ))}
                            </div>

                            {/* 插件列表 */}
                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                                {plugins.map((plugin) => (
                                    <Card key={plugin.slug} className="hover:shadow-lg transition cursor-pointer"
                                          onClick={() => viewPluginDetail(plugin)}>
                                        <CardHeader>
                                            <div className="flex items-start justify-between">
                                                <div className="text-4xl">{plugin.icon || '📦'}</div>
                                                <div className="flex gap-1">
                                                    {plugin.has_update && <Badge variant="destructive">有更新</Badge>}
                                                    {plugin.installed && <Badge variant="secondary">已安装</Badge>}
                                                </div>
                                            </div>
                                            <CardTitle className="text-lg mt-2">{plugin.name}</CardTitle>
                                            <CardDescription
                                                className="line-clamp-2">{plugin.description}</CardDescription>
                                        </CardHeader>
                                        <CardContent>
                                            <div
                                                className="flex items-center justify-between text-sm text-gray-600 dark:text-gray-400 mb-3">
                                                <div className="flex items-center gap-2">
                                                    {renderRating(plugin.rating)}
                                                </div>
                                                <span>v{plugin.version}</span>
                                            </div>
                                            <Button
                                                className="w-full"
                                                onClick={(e) => {
                                                    e.stopPropagation();
                                                    plugin.has_update ? handleUpdate(plugin.slug) : plugin.installed ? null : handleInstall(plugin.slug);
                                                }}
                                                disabled={installing === plugin.slug || (!plugin.has_update && plugin.installed)}
                                            >
                                                {installing === plugin.slug ? '处理中...' : plugin.has_update ? '更新' : plugin.installed ? '已安装' : '安装'}
                                            </Button>
                                        </CardContent>
                                    </Card>
                                ))}
                            </div>

                            {plugins.length === 0 && !loading && (
                                <div className="text-center py-12">
                                    <p className="text-gray-600 dark:text-gray-400">未找到插件</p>
                                </div>
                            )}
                        </div>
                    </TabsContent>

                    {/* 已安装插件 */}
                    <TabsContent value="installed">
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                            {plugins.filter(p => p.installed).map((plugin) => (
                                <Card key={plugin.slug}>
                                    <CardHeader>
                                        <div className="flex items-start justify-between">
                                            <div className="text-4xl">{plugin.icon || '📦'}</div>
                                            {plugin.has_update && <Badge variant="destructive">有更新</Badge>}
                                        </div>
                                        <CardTitle className="text-lg mt-2">{plugin.name}</CardTitle>
                                        <CardDescription>v{plugin.version}</CardDescription>
                                    </CardHeader>
                                    <CardContent>
                                        <div className="space-y-2">
                                            <Button
                                                className="w-full"
                                                variant={plugin.has_update ? 'default' : 'outline'}
                                                onClick={() => handleUpdate(plugin.slug)}
                                                disabled={installing === plugin.slug || !plugin.has_update}
                                            >
                                                {installing === plugin.slug ? '更新中...' : plugin.has_update ? '更新到最新版本' : '已是最新'}
                                            </Button>
                                            <Button
                                                className="w-full"
                                                variant="destructive"
                                                onClick={() => handleUninstall(plugin.slug, plugin.name)}
                                                disabled={installing === plugin.slug}
                                            >
                                                {installing === plugin.slug ? '卸载中...' : '卸载'}
                                            </Button>
                                        </div>
                                    </CardContent>
                                </Card>
                            ))}
                        </div>

                        {plugins.filter(p => p.installed).length === 0 && (
                            <div className="text-center py-12">
                                <p className="text-gray-600 dark:text-gray-400 mb-4">尚未安装任何插件</p>
                                <Button onClick={() => {
                                    const tabElement = document.querySelector('[value="browse"]') as HTMLElement;
                                    if (tabElement) (tabElement as any).click();
                                }}>
                                    浏览插件市场
                                </Button>
                            </div>
                        )}
                    </TabsContent>

                    {/* 更新 */}
                    <TabsContent value="updates">
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                            {plugins.filter(p => p.has_update).map((plugin) => (
                                <Card key={plugin.slug} className="border-yellow-500">
                                    <CardHeader>
                                        <div className="flex items-start justify-between">
                                            <div className="text-4xl">{plugin.icon || '📦'}</div>
                                            <Badge variant="destructive">可更新</Badge>
                                        </div>
                                        <CardTitle className="text-lg mt-2">{plugin.name}</CardTitle>
                                        <CardDescription>当前版本: v{plugin.version}</CardDescription>
                                    </CardHeader>
                                    <CardContent>
                                        <Button
                                            className="w-full"
                                            onClick={() => handleUpdate(plugin.slug)}
                                            disabled={installing === plugin.slug}
                                        >
                                            {installing === plugin.slug ? '更新中...' : '立即更新'}
                                        </Button>
                                    </CardContent>
                                </Card>
                            ))}
                        </div>

                        {plugins.filter(p => p.has_update).length === 0 && (
                            <div className="text-center py-12">
                                <p className="text-green-600 dark:text-green-400 mb-2">✓ 所有插件都是最新版本</p>
                                <p className="text-gray-600 dark:text-gray-400">无需更新</p>
                            </div>
                        )}
                    </TabsContent>
                </Tabs>
            </div>

            {/* 插件详情对话框 */}
            <Dialog open={detailDialogOpen} onOpenChange={setDetailDialogOpen}>
                <DialogContent className="max-w-2xl">
                    <DialogHeader>
                        <DialogTitle className="flex items-center gap-3">
                            <span className="text-4xl">{selectedPlugin?.icon || '📦'}</span>
                            <div>
                                <div>{selectedPlugin?.name}</div>
                                <div className="text-sm font-normal text-gray-600 dark:text-gray-400">
                                    by {selectedPlugin?.author}
                                </div>
                            </div>
                        </DialogTitle>
                        <DialogDescription>{selectedPlugin?.description}</DialogDescription>
                    </DialogHeader>

                    {selectedPlugin && (
                        <div className="space-y-4">
                            <div className="flex items-center gap-4 text-sm">
                                <div className="flex items-center gap-1">
                                    {renderRating(selectedPlugin.rating)}
                                    <span>({selectedPlugin.rating})</span>
                                </div>
                                <span>{selectedPlugin.installs?.toLocaleString()} 次安装</span>
                                <span>v{selectedPlugin.version}</span>
                            </div>

                            <div className="flex gap-2">
                                <Button
                                    className="flex-1"
                                    onClick={() => {
                                        selectedPlugin.has_update ? handleUpdate(selectedPlugin.slug) : handleInstall(selectedPlugin.slug);
                                        setDetailDialogOpen(false);
                                    }}
                                    disabled={installing === selectedPlugin.slug}
                                >
                                    {installing === selectedPlugin.slug ? '处理中...' : selectedPlugin.has_update ? '更新' : selectedPlugin.installed ? '已安装' : '安装'}
                                </Button>
                                <Button variant="outline" onClick={() => setDetailDialogOpen(false)}>
                                    关闭
                                </Button>
                            </div>
                        </div>
                    )}
                </DialogContent>
            </Dialog>
        </div>
    );
}
