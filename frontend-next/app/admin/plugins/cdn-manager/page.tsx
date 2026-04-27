'use client';

/**
 * CDN管理插件 - 缓存管理页面
 */

import {useEffect, useState} from 'react';
import {Card, CardContent, CardDescription, CardHeader, CardTitle} from '@/components/ui/card';
import {Button} from '@/components/ui/button';
import {Input} from '@/components/ui/input';
import {Label} from '@/components/ui/label';
import {Select, SelectContent, SelectItem, SelectTrigger, SelectValue} from '@/components/ui/select';
import {Switch} from '@/components/ui/switch';
import {apiClient} from '@/lib/api-client';

export default function CDNManagerPage() {
    const [settings, setSettings] = useState({
        provider: 'cloudflare',
        api_key: '',
        zone_id: '',
        cdn_domain: '',
        auto_purge: true,
    });
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [stats, setStats] = useState<any>(null);
    const [purgeUrls, setPurgeUrls] = useState('');
    const [purging, setPurging] = useState(false);
    const [testResult, setTestResult] = useState<any>(null);

    useEffect(() => {
        loadSettings();
    }, []);

    const loadSettings = async () => {
        try {
            setLoading(true);
            const response = await apiClient.get('/plugins/cdn-manager/settings');

            if (response.success) {
                setSettings((response.data as any).settings || settings);
                await loadStats();
            }
        } catch (error) {
            console.error('Failed to load settings:', error);
        } finally {
            setLoading(false);
        }
    };

    const loadStats = async () => {
        try {
            const response = await apiClient.post('/plugins/cdn-manager/action', {
                action: 'get_cdn_stats',
                params: {},
            });

            if (response.success) {
                setStats(response.data);
            }
        } catch (error) {
            console.error('Failed to load stats:', error);
        }
    };

    const saveSettings = async () => {
        try {
            setSaving(true);
            const response = await apiClient.put('/plugins/cdn-manager/settings', {
                settings,
            });

            if (response.success) {
                alert('设置已保存');
            } else {
                alert('保存失败: ' + response.error);
            }
        } catch (error) {
            alert('保存失败');
        } finally {
            setSaving(false);
        }
    };

    const testConnection = async () => {
        try {
            setTestResult(null);
            const response = await apiClient.post('/plugins/cdn-manager/action', {
                action: 'test_connection',
                params: settings,
            });

            setTestResult(response);
        } catch (error) {
            setTestResult({success: false, error: '连接测试失败'});
        }
    };

    const purgeCache = async () => {
        if (!purgeUrls.trim()) {
            alert('请输入要刷新的URL');
            return;
        }

        const urls = purgeUrls.split('\n').map(url => url.trim()).filter(url => url);

        try {
            setPurging(true);
            const response = await apiClient.post('/plugins/cdn-manager/action', {
                action: 'purge_cache',
                params: {urls},
            });

            if (response.success) {
                alert(`成功刷新 ${(response.data as any).purged_urls} 个URL`);
                setPurgeUrls('');
            } else {
                alert('刷新失败: ' + response.error);
            }
        } catch (error) {
            alert('刷新失败');
        } finally {
            setPurging(false);
        }
    };

    const purgeAll = async () => {
        if (!confirm('确定要清除所有CDN缓存吗?这可能会影响网站性能。')) {
            return;
        }

        try {
            setPurging(true);
            const response = await apiClient.post('/plugins/cdn-manager/action', {
                action: 'purge_cache',
                params: {purge_all: true},
            });

            if (response.success) {
                alert('所有缓存已清除');
            } else {
                alert('清除失败: ' + response.error);
            }
        } catch (error) {
            alert('清除失败');
        } finally {
            setPurging(false);
        }
    };

    if (loading) {
        return <div className="flex justify-center p-8">加载中...</div>;
    }

    return (
        <div className="container mx-auto p-6 space-y-6">
            <div>
                <h1 className="text-3xl font-bold">CDN管理</h1>
                <p className="text-gray-600 dark:text-gray-400 mt-2">
                    配置和管理CDN加速服务
                </p>
            </div>

            {/* 统计信息 */}
            {stats && (
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <Card>
                        <CardContent className="pt-6">
                            <div className="text-2xl font-bold">{stats.bandwidth || '0 GB'}</div>
                            <p className="text-sm text-gray-600">带宽使用</p>
                        </CardContent>
                    </Card>
                    <Card>
                        <CardContent className="pt-6">
                            <div className="text-2xl font-bold">{stats.requests || 0}</div>
                            <p className="text-sm text-gray-600">总请求数</p>
                        </CardContent>
                    </Card>
                    <Card>
                        <CardContent className="pt-6">
                            <div className="text-2xl font-bold text-green-600">
                                {stats.cache_hit_ratio ? `${stats.cache_hit_ratio}%` : '0%'}
                            </div>
                            <p className="text-sm text-gray-600">缓存命中率</p>
                        </CardContent>
                    </Card>
                </div>
            )}

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* CDN配置 */}
                <Card>
                    <CardHeader>
                        <CardTitle>CDN配置</CardTitle>
                        <CardDescription>配置CDN服务商和认证信息</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div>
                            <Label>CDN服务商</Label>
                            <Select
                                value={settings.provider}
                                onValueChange={(value) => setSettings({...settings, provider: value})}
                            >
                                <SelectTrigger>
                                    <SelectValue/>
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="cloudflare">Cloudflare</SelectItem>
                                    <SelectItem value="keycdn">KeyCDN</SelectItem>
                                    <SelectItem value="custom">自定义</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>

                        <div>
                            <Label>API密钥</Label>
                            <Input
                                type="password"
                                value={settings.api_key}
                                onChange={(e) => setSettings({...settings, api_key: e.target.value})}
                                placeholder="输入API密钥"
                            />
                        </div>

                        {settings.provider === 'cloudflare' && (
                            <div>
                                <Label>Zone ID</Label>
                                <Input
                                    value={settings.zone_id}
                                    onChange={(e) => setSettings({...settings, zone_id: e.target.value})}
                                    placeholder="Cloudflare Zone ID"
                                />
                            </div>
                        )}

                        <div>
                            <Label>CDN域名</Label>
                            <Input
                                value={settings.cdn_domain}
                                onChange={(e) => setSettings({...settings, cdn_domain: e.target.value})}
                                placeholder="cdn.example.com"
                            />
                        </div>

                        <div className="flex items-center justify-between">
                            <Label>自动刷新缓存</Label>
                            <Switch
                                checked={settings.auto_purge}
                                onCheckedChange={(checked) => setSettings({...settings, auto_purge: checked})}
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
                                className={`p-3 rounded text-sm ${testResult.success ? 'bg-green-50 text-green-800' : 'bg-red-50 text-red-800'}`}>
                                {testResult.success ? '✓ 连接成功' : `✗ ${testResult.error}`}
                            </div>
                        )}
                    </CardContent>
                </Card>

                {/* 缓存管理 */}
                <Card>
                    <CardHeader>
                        <CardTitle>缓存管理</CardTitle>
                        <CardDescription>手动刷新CDN缓存</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div>
                            <Label>刷新指定URL (每行一个)</Label>
                            <textarea
                                className="w-full min-h-[150px] p-2 border rounded"
                                value={purgeUrls}
                                onChange={(e) => setPurgeUrls(e.target.value)}
                                placeholder="/article/1&#10;/article/2&#10;/page/about"
                            />
                        </div>

                        <div className="flex gap-2">
                            <Button onClick={purgeCache} disabled={purging || !purgeUrls.trim()}>
                                {purging ? '刷新中...' : '刷新选中URL'}
                            </Button>
                            <Button onClick={purgeAll} variant="destructive" disabled={purging}>
                                清除所有缓存
                            </Button>
                        </div>

                        <div className="bg-blue-50 dark:bg-blue-900/20 p-4 rounded text-sm">
                            <p className="font-semibold mb-2">💡 提示:</p>
                            <ul className="list-disc list-inside space-y-1 text-gray-700 dark:text-gray-300">
                                <li>文章更新时会自动刷新相关缓存</li>
                                <li>批量刷新时建议不超过100个URL</li>
                                <li>清除所有缓存会影响网站性能,请谨慎操作</li>
                            </ul>
                        </div>
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}
