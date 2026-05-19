'use client';

/**
 * 高级搜索插件设置页面
 */

import {useEffect, useState} from 'react';
import {Card, CardContent, CardDescription, CardHeader, CardTitle} from '@/components/ui/card';
import {Button} from '@/components/ui/button';
import {Input} from '@/components/ui/input';
import {Label} from '@/components/ui/label';
import {Select, SelectContent, SelectItem, SelectTrigger, SelectValue} from '@/components/ui/select';
import {Badge} from '@/components/ui/badge';
import {apiClient} from '@/lib/api-client';

export default function AdvancedSearchSettingsPage() {
    const [settings, setSettings] = useState({
        engine: 'meilisearch',
        host: 'http://localhost:7700',
        api_key: '',
        index_name: 'articles',
    });
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [testResult, setTestResult] = useState<any>(null);
    const [indexStats, setIndexStats] = useState<any>(null);

    useEffect(() => {
        loadSettings();
    }, []);

    const loadSettings = async () => {
        try {
            setLoading(true);
            const response = await apiClient.get('/plugins/advanced-search/settings');

            if (response.success) {
                setSettings((response.data as any).settings || settings);
            }
        } catch (error) {
            console.error('Failed to load settings:', error);
        } finally {
            setLoading(false);
        }
    };

    const saveSettings = async () => {
        try {
            setSaving(true);
            const response = await apiClient.put('/plugins/advanced-search/settings', {
                settings,
            });

            if (response.success) {
                alert('设置已保存');
            } else {
                alert('保存失败: ' + response.error);
            }
        } catch (error) {
            console.error('Failed to save settings:', error);
            alert('保存失败');
        } finally {
            setSaving(false);
        }
    };

    const testConnection = async () => {
        try {
            setTestResult(null);
            const response = await apiClient.post('/plugins/advanced-search/action', {
                action: 'test_connection',
                params: settings,
            });

            if (response.success) {
                setTestResult({success: true, message: '连接成功!'});
                // 获取索引统计
                await loadIndexStats();
            } else {
                setTestResult({success: false, message: response.error});
            }
        } catch (error) {
            setTestResult({success: false, message: '连接测试失败'});
        }
    };

    const loadIndexStats = async () => {
        try {
            const response = await apiClient.post('/plugins/advanced-search/action', {
                action: 'get_index_stats',
                params: settings,
            });

            if (response.success) {
                setIndexStats(response.data);
            }
        } catch (error) {
            console.error('Failed to load index stats:', error);
        }
    };

    const rebuildIndex = async () => {
        if (!confirm('确定要重建索引吗?这可能需要一些时间。')) {
            return;
        }

        try {
            const response = await apiClient.post('/plugins/advanced-search/action', {
                action: 'rebuild_index',
                params: settings,
            });

            if (response.success) {
                alert('索引重建完成');
                await loadIndexStats();
            } else {
                alert('重建失败: ' + response.error);
            }
        } catch (error) {
            alert('重建失败');
        }
    };

    if (loading) {
        return <div className="flex justify-center p-8">加载中...</div>;
    }

    return (
        <div className="container mx-auto p-6 space-y-6">
            <div>
                <h1 className="text-3xl font-bold">高级搜索设置</h1>
                <p className="text-gray-600 dark:text-gray-400 mt-2">
                    配置Elasticsearch或Meilisearch搜索引擎
                </p>
            </div>

            <Card>
                <CardHeader>
                    <CardTitle>搜索引擎配置</CardTitle>
                    <CardDescription>选择并配置您的搜索引擎</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                    <div>
                        <Label>搜索引擎类型</Label>
                        <Select
                            value={settings.engine}
                            onValueChange={(value) => setSettings({...settings, engine: value})}
                        >
                            <SelectTrigger>
                                <SelectValue/>
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="meilisearch">Meilisearch (推荐)</SelectItem>
                                <SelectItem value="elasticsearch">Elasticsearch</SelectItem>
                            </SelectContent>
                        </Select>
                    </div>

                    <div>
                        <Label>服务器地址</Label>
                        <Input
                            value={settings.host}
                            onChange={(e) => setSettings({...settings, host: e.target.value})}
                            placeholder="http://localhost:7700"
                        />
                    </div>

                    <div>
                        <Label>API密钥 (可选)</Label>
                        <Input
                            type="password"
                            value={settings.api_key}
                            onChange={(e) => setSettings({...settings, api_key: e.target.value})}
                            placeholder="输入API密钥"
                        />
                    </div>

                    <div>
                        <Label>索引名称</Label>
                        <Input
                            value={settings.index_name}
                            onChange={(e) => setSettings({...settings, index_name: e.target.value})}
                            placeholder="articles"
                        />
                    </div>

                    <div className="flex gap-2">
                        <Button onClick={testConnection} variant="outline">
                            测试连接
                        </Button>
                        <Button onClick={saveSettings} disabled={saving}>
                            {saving ? '保存中...' : '保存设置'}
                        </Button>
                    </div>

                    {testResult && (
                        <div
                            className={`p-4 rounded ${testResult.success ? 'bg-green-50 text-green-800' : 'bg-red-50 text-red-800'}`}>
                            {testResult.message}
                        </div>
                    )}
                </CardContent>
            </Card>

            {indexStats && (
                <Card>
                    <CardHeader>
                        <CardTitle>索引统计</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                            <div>
                                <p className="text-sm text-gray-600">文档数量</p>
                                <p className="text-2xl font-bold">{indexStats.document_count || 0}</p>
                            </div>
                            <div>
                                <p className="text-sm text-gray-600">索引大小</p>
                                <p className="text-2xl font-bold">{indexStats.index_size || '0 MB'}</p>
                            </div>
                            <div>
                                <p className="text-sm text-gray-600">最后更新</p>
                                <p className="text-lg">{indexStats.last_updated || 'N/A'}</p>
                            </div>
                            <div>
                                <p className="text-sm text-gray-600">状态</p>
                                <Badge variant={indexStats.status === 'healthy' ? 'default' : 'destructive'}>
                                    {indexStats.status || 'Unknown'}
                                </Badge>
                            </div>
                        </div>

                        <div className="mt-4">
                            <Button onClick={rebuildIndex} variant="outline">
                                重建索引
                            </Button>
                        </div>
                    </CardContent>
                </Card>
            )}

            <Card>
                <CardHeader>
                    <CardTitle>使用说明</CardTitle>
                </CardHeader>
                <CardContent className="space-y-2 text-sm">
                    <p><strong>Meilisearch安装:</strong></p>
                    <pre className="bg-gray-100 dark:bg-gray-800 p-2 rounded">
            curl -L https://install.meilisearch.com | sh
          </pre>

                    <p><strong>Elasticsearch安装:</strong></p>
                    <pre className="bg-gray-100 dark:bg-gray-800 p-2 rounded">
            docker run -p 9200:9200 elasticsearch:8.11.0
          </pre>

                    <p className="text-gray-600 mt-4">
                        配置完成后,插件会自动同步文章内容到搜索引擎,提供强大的全文检索功能。
                    </p>
                </CardContent>
            </Card>
        </div>
    );
}
