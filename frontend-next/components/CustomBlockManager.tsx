'use client';

import React, {useEffect, useState} from 'react';
import {Card, CardContent, CardDescription, CardHeader, CardTitle} from '@/components/ui/card';
import {Badge} from '@/components/ui/badge';
import {Button} from '@/components/ui/button';
import {Tabs, TabsContent, TabsList, TabsTrigger} from '@/components/ui/tabs';

interface BlockType {
    name: string;
    display_name: string;
    category: string;
    icon: string;
    description: string;
    attributes: Record<string, any>;
    is_inline: boolean;
}

interface PluginInfo {
    name: string;
    version: string;
    description: string;
    author: string;
    blocks_count: number;
    is_active: boolean;
}

export default function CustomBlockManager() {
    const [blocks, setBlocks] = useState<BlockType[]>([]);
    const [plugins, setPlugins] = useState<PluginInfo[]>([]);
    const [loading, setLoading] = useState(true);
    const [activeTab, setActiveTab] = useState('blocks');

    // 加载数据
    useEffect(() => {
        loadData();
    }, []);

    const loadData = async () => {
        try {
            setLoading(true);

            // 加载所有块
            const blocksResponse = await fetch('/api/v2/custom-blocks/blocks');
            if (blocksResponse.ok) {
                const blocksData = await blocksResponse.json();
                setBlocks(blocksData);
            }

            // 加载插件列表
            const pluginsResponse = await fetch('/api/v2/custom-blocks/plugins');
            if (pluginsResponse.ok) {
                const pluginsData = await pluginsResponse.json();
                setPlugins(pluginsData);
            }
        } catch (error) {
            console.error('加载数据失败:', error);
        } finally {
            setLoading(false);
        }
    };

    // 激�?停用插件
    const togglePlugin = async (pluginName: string, isActive: boolean) => {
        try {
            const endpoint = isActive ? 'deactivate' : 'activate';
            const response = await fetch(`/api/v2/custom-blocks/plugins/${pluginName}/${endpoint}`, {
                method: 'POST'
            });

            if (response.ok) {
                loadData(); // 重新加载数据
            }
        } catch (error) {
            console.error('操作失败:', error);
        }
    };

    // 按分类分组块
    const blocksByCategory = blocks.reduce((acc, block) => {
        if (!acc[block.category]) {
            acc[block.category] = [];
        }
        acc[block.category].push(block);
        return acc;
    }, {} as Record<string, BlockType[]>);

    // 分类图标映射
    const categoryIcons: Record<string, string> = {
        text: '📝',
        media: '🖼�?,
        layout: '📐',
        widget: '🧩',
        embed: '🔗'
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center h-64">
                <div className="text-center">
                    <div
                        className="inline-block animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-blue-500 mb-2"></div>
                    <p className="text-gray-600 dark:text-gray-400">加载�?..</p>
                </div>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* 统计卡片 */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <Card>
                    <CardHeader className="pb-2">
                        <CardTitle className="text-sm font-medium text-gray-600 dark:text-gray-400">
                            总块�? </CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="text-3xl font-bold">{blocks.length}</div>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="pb-2">
                        <CardTitle className="text-sm font-medium text-gray-600 dark:text-gray-400">
                            插件数量
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="text-3xl font-bold">{plugins.length}</div>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="pb-2">
                        <CardTitle className="text-sm font-medium text-gray-600 dark:text-gray-400">
                            活跃插件
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="text-3xl font-bold">
                            {plugins.filter(p => p.is_active).length}
                        </div>
                    </CardContent>
                </Card>
            </div>

            {/* 标签�?*/}
            <Tabs value={activeTab} onValueChange={setActiveTab}>
                <TabsList className="grid w-full grid-cols-2">
                    <TabsTrigger value="blocks">块类�?({blocks.length})</TabsTrigger>
                    <TabsTrigger value="plugins">插件管理 ({plugins.length})</TabsTrigger>
                </TabsList>

                {/* 块类型标签页 */}
                <TabsContent value="blocks" className="space-y-6">
                    {Object.entries(blocksByCategory).map(([category, categoryBlocks]) => (
                        <div key={category}>
                            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                                <span>{categoryIcons[category] || '📦'}</span>
                                <span className="capitalize">{category}</span>
                                <Badge variant="secondary">{categoryBlocks.length}</Badge>
                            </h3>

                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                                {categoryBlocks.map((block) => (
                                    <Card key={block.name} className="hover:shadow-md transition-shadow">
                                        <CardHeader className="pb-3">
                                            <div className="flex items-start justify-between">
                                                <div className="flex items-center gap-2">
                                                    <span className="text-2xl">{block.icon}</span>
                                                    <div>
                                                        <CardTitle className="text-base">
                                                            {block.display_name}
                                                        </CardTitle>
                                                        <CardDescription className="text-xs">
                                                            {block.name}
                                                        </CardDescription>
                                                    </div>
                                                </div>
                                                {block.is_inline && (
                                                    <Badge variant="outline" className="text-xs">
                                                        行内
                                                    </Badge>
                                                )}
                                            </div>
                                        </CardHeader>
                                        <CardContent>
                                            <p className="text-sm text-gray-600 dark:text-gray-400 mb-3">
                                                {block.description}
                                            </p>

                                            {Object.keys(block.attributes).length > 0 && (
                                                <div className="text-xs text-gray-500 dark:text-gray-500">
                                                    <div className="font-medium mb-1">属�?</div>
                                                    <div className="flex flex-wrap gap-1">
                                                        {Object.keys(block.attributes).slice(0, 3).map(attr => (
                                                            <Badge key={attr} variant="outline" className="text-xs">
                                                                {attr}
                                                            </Badge>
                                                        ))}
                                                        {Object.keys(block.attributes).length > 3 && (
                                                            <Badge variant="outline" className="text-xs">
                                                                +{Object.keys(block.attributes).length - 3}
                                                            </Badge>
                                                        )}
                                                    </div>
                                                </div>
                                            )}
                                        </CardContent>
                                    </Card>
                                ))}
                            </div>
                        </div>
                    ))}
                </TabsContent>

                {/* 插件管理标签�?*/}
                <TabsContent value="plugins" className="space-y-4">
                    {plugins.map((plugin) => (
                        <Card key={plugin.name}>
                            <CardHeader>
                                <div className="flex items-start justify-between">
                                    <div>
                                        <CardTitle className="text-lg flex items-center gap-2">
                                            {plugin.name}
                                            <Badge variant="outline">{plugin.version}</Badge>
                                        </CardTitle>
                                        <CardDescription className="mt-1">
                                            {plugin.description}
                                        </CardDescription>
                                        {plugin.author && (
                                            <p className="text-xs text-gray-500 dark:text-gray-500 mt-2">
                                                作�? {plugin.author}
                                            </p>
                                        )}
                                    </div>
                                    <Button
                                        variant={plugin.is_active ? "destructive" : "default"}
                                        size="sm"
                                        onClick={() => togglePlugin(plugin.name, plugin.is_active)}
                                    >
                                        {plugin.is_active ? '停用' : '激�?}
                                    </Button>
                                </div>
                            </CardHeader>
                            <CardContent>
                                <div className="flex items-center gap-4 text-sm">
                                    <div className="flex items-center gap-1">
                                            <span className="text-gray-600 dark:text-gray-400">块数�?</span>
                                        <Badge variant="secondary">{plugin.blocks_count}</Badge>
                                    </div>
                                    <div className="flex items-center gap-1">
                                        <span className="text-gray-600 dark:text-gray-400">状�?</span>
                                        <Badge variant={plugin.is_active ? "default" : "outline"}>
                                            {plugin.is_active ? '活跃' : '停用'}
                                        </Badge>
                                    </div>
                                </div>
                            </CardContent>
                        </Card>
                    ))}

                    {plugins.length === 0 && (
                        <div className="text-center py-12 text-gray-500 dark:text-gray-400">
                            <div className="text-4xl mb-4">📦</div>
                            <p>暂无插件</p>
                            <p className="text-sm mt-2">创建自定义块插件来扩展编辑器功能</p>
                        </div>
                    )}
                </TabsContent>
            </Tabs>

            {/* 帮助信息 */}
            <Card className="bg-blue-50 dark:bg-blue-950 border-blue-200 dark:border-blue-800">
                <CardContent className="pt-6">
                    <h4 className="font-semibold text-blue-900 dark:text-blue-100 mb-2">
                        💡 如何创建自定义块插件�? </h4>
                    <ol className="list-decimal list-inside space-y-2 text-sm text-blue-800 dark:text-blue-200">
                        <li>继承 <code
                            className="bg-white dark:bg-gray-800 px-2 py-1 rounded">CustomBlockPlugin</code> �?
                        </li>
                        <li>实现 <code
                            className="bg-white dark:bg-gray-800 px-2 py-1 rounded">register_blocks()</code> 方法注册块类�?
                        </li>
                        <li>可选：实现 <code
                            className="bg-white dark:bg-gray-800 px-2 py-1 rounded">render_{'{block_name}'}</code> 方法自定义渲�?
                        </li>
                        <li>将插件文件放�?<code
                            className="bg-white dark:bg-gray-800 px-2 py-1 rounded">shared/services/</code> 目录
                        </li>
                        <li>�?API 中导入并加载插件</li>
                    </ol>
                </CardContent>
            </Card>
        </div>
    );
}
