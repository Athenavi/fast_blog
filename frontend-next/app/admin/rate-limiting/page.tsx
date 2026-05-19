'use client';

import {useEffect, useState} from 'react';
import {Card, CardContent, CardDescription, CardHeader, CardTitle} from '@/components/ui/card';
import {Button} from '@/components/ui/button';
import {Input} from '@/components/ui/input';
import {Label} from '@/components/ui/label';
import {Switch} from '@/components/ui/switch';
import {Badge} from '@/components/ui/badge';
import {Table, TableBody, TableCell, TableHead, TableHeader, TableRow} from '@/components/ui/table';
import {Tabs, TabsContent, TabsList, TabsTrigger} from '@/components/ui/tabs';
import {useToast} from '@/hooks/use-toast';
import {Ban, Gauge, RefreshCw, Save, Shield, User, Users} from 'lucide-react';

interface RateLimitConfig {
    enabled: boolean;
    requests_per_minute: number;
    requests_per_hour: number;
    burst_size: number;
    whitelist_ips: string[];
}

interface IPRateLimit {
    id: number;
    ip_address: string;
    requests_count: number;
    blocked: boolean;
    blocked_until?: string;
    created_at: string;
    updated_at: string;
}

interface UserQuota {
    user_id: number;
    username: string;
    daily_limit: number;
    monthly_limit: number;
    current_daily_usage: number;
    current_monthly_usage: number;
}

export default function RateLimitingPage() {
    const {toast} = useToast();
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [activeTab, setActiveTab] = useState('config');

    const [rateLimitConfig, setRateLimitConfig] = useState<RateLimitConfig>({
        enabled: true,
        requests_per_minute: 60,
        requests_per_hour: 1000,
        burst_size: 10,
        whitelist_ips: [],
    });

    const [ipLimits, setIPLimits] = useState<IPRateLimit[]>([]);
    const [userQuotas, setUserQuotas] = useState<UserQuota[]>([]);

    const [newWhitelistIP, setNewWhitelistIP] = useState('');
    const [blockIP, setBlockIP] = useState('');

    useEffect(() => {
        loadData();
    }, [activeTab]);

    const loadData = async () => {
        try {
            setLoading(true);
            const token = getAccessToken();

            if (activeTab === 'config') {
                const response = await fetch('/api/v2/rate-limit/config', {
                    headers: {'Authorization': `Bearer ${token}`},
                });
                if (response.ok) {
                    const data = await response.json();
                    if (data.success) {
                        setRateLimitConfig(data.data);
                    }
                }
            } else if (activeTab === 'ips') {
                const response = await fetch('/api/v2/rate-limit/ips', {
                    headers: {'Authorization': `Bearer ${token}`},
                });
                if (response.ok) {
                    const data = await response.json();
                    if (data.success) {
                        setIPLimits(data.data.ips || []);
                    }
                }
            } else if (activeTab === 'quotas') {
                const response = await fetch('/api/v2/rate-limit/quotas', {
                    headers: {'Authorization': `Bearer ${token}`},
                });
                if (response.ok) {
                    const data = await response.json();
                    if (data.success) {
                        setUserQuotas(data.data.quotas || []);
                    }
                }
            }
        } catch (error) {
            console.error('Failed to load data:', error);
            toast({
                title: '加载失败',
                description: '无法加载限流配置',
                variant: 'destructive',
            });
        } finally {
            setLoading(false);
        }
    };

    const saveConfig = async () => {
        try {
            setSaving(true);
            const token = getAccessToken();
            const response = await fetch('/api/v2/rate-limit/config', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`,
                },
                body: JSON.stringify(rateLimitConfig),
            });

            const data = await response.json();

            if (data.success) {
                toast({
                    title: '保存成功',
                    description: '限流配置已更',
                });
            } else {
                throw new Error(data.error || '保存失败');
            }
        } catch (error) {
            console.error('Failed to save config:', error);
            toast({
                title: '保存失败',
                description: error instanceof Error ? error.message : '未知错误',
                variant: 'destructive',
            });
        } finally {
            setSaving(false);
        }
    };

    const addToWhitelist = () => {
        if (!newWhitelistIP || !isValidIP(newWhitelistIP)) {
            toast({
                title: '无效的IP地址',
                description: '请输入有效的IP地址',
                variant: 'destructive',
            });
            return;
        }

        if (rateLimitConfig.whitelist_ips.includes(newWhitelistIP)) {
            toast({
                title: 'IP已存',
                description: '该IP已在白名单中',
                variant: 'destructive',
            });
            return;
        }

        setRateLimitConfig({
            ...rateLimitConfig,
            whitelist_ips: [...rateLimitConfig.whitelist_ips, newWhitelistIP],
        });
        setNewWhitelistIP('');
    };

    const removeFromWhitelist = (ip: string) => {
        setRateLimitConfig({
            ...rateLimitConfig,
            whitelist_ips: rateLimitConfig.whitelist_ips.filter(item => item !== ip),
        });
    };

    const blockIPAddress = async () => {
        if (!blockIP || !isValidIP(blockIP)) {
            toast({
                title: '无效的IP地址',
                description: '请输入有效的IP地址',
                variant: 'destructive',
            });
            return;
        }

        try {
            const token = getAccessToken();
            const response = await fetch('/api/v2/rate-limit/block', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`,
                },
                body: JSON.stringify({ip_address: blockIP}),
            });

            const data = await response.json();

            if (data.success) {
                toast({
                    title: '封禁成功',
                    description: `IP ${blockIP} 已被封禁`,
                });
                setBlockIP('');
                loadData();
            } else {
                throw new Error(data.error || '封禁失败');
            }
        } catch (error) {
            console.error('Failed to block IP:', error);
            toast({
                title: '封禁失败',
                description: error instanceof Error ? error.message : '未知错误',
                variant: 'destructive',
            });
        }
    };

    const unblockIP = async (ip: string) => {
        try {
            const token = getAccessToken();
            const response = await fetch(`/api/v2/rate-limit/unblock/${ip}`, {
                method: 'POST',
                headers: {'Authorization': `Bearer ${token}`},
            });

            const data = await response.json();

            if (data.success) {
                toast({
                    title: '解封成功',
                    description: `IP ${ip} 已解封`,
                });
                loadData();
            }
        } catch (error) {
            console.error('Failed to unblock IP:', error);
            toast({
                title: '解封失败',
                variant: 'destructive',
            });
        }
    };

    const isValidIP = (ip: string) => {
        const pattern = /^(\d{1,3}\.){3}\d{1,3}$/;
        if (!pattern.test(ip)) return false;

        const parts = ip.split('.');
        return parts.every(part => {
            const num = parseInt(part);
            return num >= 0 && num <= 255;
        });
    };

    const getAccessToken = () => {
        if (typeof document !== 'undefined') {
            const match = document.cookie.match(/access_token=([^;]+)/);
            return match ? match[1] : '';
        }
        return '';
    };

    const formatDate = (dateString?: string) => {
        if (!dateString) return '';
        return new Date(dateString).toLocaleString('zh-CN');
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center py-12">
                <div className="text-center">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900 mx-auto mb-4"></div>
                    <p className="text-gray-600">加载'..</p>
                </div>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            <div>
                <h1 className="text-3xl font-bold text-gray-900 dark:text-white">API限流管理</h1>
                <p className="text-gray-600 dark:text-gray-400 mt-2">
                    配置API请求频率限制、IP封禁和用户配额管' </p>
            </div>

            <Tabs value={activeTab} onValueChange={setActiveTab}>
                <TabsList className="grid w-full grid-cols-3">
                    <TabsTrigger value="config" className="flex items-center gap-2">
                        <Gauge className="w-4 h-4"/>
                        限流配置
                    </TabsTrigger>
                    <TabsTrigger value="ips" className="flex items-center gap-2">
                        <Shield className="w-4 h-4"/>
                        IP管理
                    </TabsTrigger>
                    <TabsTrigger value="quotas" className="flex items-center gap-2">
                        <Users className="w-4 h-4"/>
                        用户配额
                    </TabsTrigger>
                </TabsList>

                <TabsContent value="config" className="space-y-6 mt-6">
                    <Card>
                        <CardHeader>
                            <CardTitle>全局限流配置</CardTitle>
                            <CardDescription>设置API请求频率限制和白名单</CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-6">
                            <div className="flex items-center justify-between">
                                <Label htmlFor="rate-limit-enabled">启用限流</Label>
                                <Switch
                                    id="rate-limit-enabled"
                                    checked={rateLimitConfig.enabled}
                                    onCheckedChange={(checked) =>
                                        setRateLimitConfig({...rateLimitConfig, enabled: checked})
                                    }
                                />
                            </div>

                            {rateLimitConfig.enabled && (
                                <>
                                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                                        <div className="space-y-2">
                                            <Label htmlFor="rpm">每分钟请求数</Label>
                                            <Input
                                                id="rpm"
                                                type="number"
                                                value={rateLimitConfig.requests_per_minute}
                                                onChange={(e) =>
                                                    setRateLimitConfig({
                                                        ...rateLimitConfig,
                                                        requests_per_minute: parseInt(e.target.value) || 0,
                                                    })
                                                }
                                            />
                                        </div>
                                        <div className="space-y-2">
                                            <Label htmlFor="rph">每小时请求数</Label>
                                            <Input
                                                id="rph"
                                                type="number"
                                                value={rateLimitConfig.requests_per_hour}
                                                onChange={(e) =>
                                                    setRateLimitConfig({
                                                        ...rateLimitConfig,
                                                        requests_per_hour: parseInt(e.target.value) || 0,
                                                    })
                                                }
                                            />
                                        </div>
                                        <div className="space-y-2">
                                            <Label htmlFor="burst">突发大小</Label>
                                            <Input
                                                id="burst"
                                                type="number"
                                                value={rateLimitConfig.burst_size}
                                                onChange={(e) =>
                                                    setRateLimitConfig({
                                                        ...rateLimitConfig,
                                                        burst_size: parseInt(e.target.value) || 0,
                                                    })
                                                }
                                            />
                                        </div>
                                    </div>

                                    <div className="space-y-4">
                                        <Label>IP白名</Label>
                                        <div className="flex gap-2">
                                            <Input
                                                placeholder="输入IP地址，例如：192.168.1.1"
                                                value={newWhitelistIP}
                                                onChange={(e) => setNewWhitelistIP(e.target.value)}
                                                onKeyPress={(e) => e.key === 'Enter' && addToWhitelist()}
                                            />
                                            <Button onClick={addToWhitelist}>添加</Button>
                                        </div>

                                        <div className="flex flex-wrap gap-2">
                                            {rateLimitConfig.whitelist_ips.map((ip) => (
                                                <Badge key={ip} variant="secondary" className="gap-1">
                                                    {ip}
                                                    <button
                                                        onClick={() => removeFromWhitelist(ip)}
                                                        className="ml-1 hover:text-red-600"
                                                    >
                                                        ×
                                                    </button>
                                                </Badge>
                                            ))}
                                            {rateLimitConfig.whitelist_ips.length === 0 && (
                                                <span className="text-sm text-gray-500">暂无白名单IP</span>
                                            )}
                                        </div>
                                    </div>

                                    <Button onClick={saveConfig} disabled={saving}>
                                        <Save className="w-4 h-4 mr-2"/>
                                        {saving ? '保存' : '保存配置'}
                                    </Button>
                                </>
                            )}
                        </CardContent>
                    </Card>
                </TabsContent>

                <TabsContent value="ips" className="space-y-6 mt-6">
                    <Card>
                        <CardHeader>
                            <CardTitle>IP封禁管理</CardTitle>
                            <CardDescription>查看和管理被封禁的IP地址</CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <div className="flex gap-2">
                                <Input
                                    placeholder="输入要封禁的IP地址"
                                    value={blockIP}
                                    onChange={(e) => setBlockIP(e.target.value)}
                                />
                                <Button onClick={blockIPAddress}>
                                    <Ban className="w-4 h-4 mr-2"/>
                                    封禁IP
                                </Button>
                            </div>

                            <div className="border rounded-lg">
                                <Table>
                                    <TableHeader>
                                        <TableRow>
                                            <TableHead>IP地址</TableHead>
                                            <TableHead>请求次数</TableHead>
                                            <TableHead>状</TableHead>
                                            <TableHead>封禁</TableHead>
                                            <TableHead>操作</TableHead>
                                        </TableRow>
                                    </TableHeader>
                                    <TableBody>
                                        {ipLimits.length === 0 ? (
                                            <TableRow>
                                                <TableCell colSpan={5} className="text-center py-8 text-gray-500">
                                                    暂无IP记录
                                                </TableCell>
                                            </TableRow>
                                        ) : (
                                            ipLimits.map((ip) => (
                                                <TableRow key={ip.id}>
                                                    <TableCell className="font-mono">{ip.ip_address}</TableCell>
                                                    <TableCell>{ip.requests_count}</TableCell>
                                                    <TableCell>
                                                        {ip.blocked ? (
                                                            <Badge variant="destructive">已封</Badge>
                                                        ) : (
                                                            <Badge variant="default">正常</Badge>
                                                        )}
                                                    </TableCell>
                                                    <TableCell>{formatDate(ip.blocked_until)}</TableCell>
                                                    <TableCell>
                                                        {ip.blocked && (
                                                            <Button
                                                                variant="outline"
                                                                size="sm"
                                                                onClick={() => unblockIP(ip.ip_address)}
                                                            >
                                                                解封
                                                            </Button>
                                                        )}
                                                    </TableCell>
                                                </TableRow>
                                            ))
                                        )}
                                    </TableBody>
                                </Table>
                            </div>
                        </CardContent>
                    </Card>
                </TabsContent>

                <TabsContent value="quotas" className="space-y-6 mt-6">
                    <Card>
                        <CardHeader>
                            <div className="flex items-center justify-between">
                                <div>
                                    <CardTitle>用户配额管理</CardTitle>
                                    <CardDescription>查看和管理用户的API使用配额</CardDescription>
                                </div>
                                <Button variant="outline" size="sm" onClick={loadData}>
                                    <RefreshCw className="w-4 h-4 mr-2"/>
                                    刷新
                                </Button>
                            </div>
                        </CardHeader>
                        <CardContent>
                            <div className="border rounded-lg">
                                <Table>
                                    <TableHeader>
                                        <TableRow>
                                            <TableHead>用户</TableHead>
                                            <TableHead>日限</TableHead>
                                            <TableHead>月限</TableHead>
                                            <TableHead>今日使用</TableHead>
                                            <TableHead>本月使用</TableHead>
                                            <TableHead>使用</TableHead>
                                        </TableRow>
                                    </TableHeader>
                                    <TableBody>
                                        {userQuotas.length === 0 ? (
                                            <TableRow>
                                                <TableCell colSpan={6} className="text-center py-8 text-gray-500">
                                                    暂无用户配额数据
                                                </TableCell>
                                            </TableRow>
                                        ) : (
                                            userQuotas.map((quota) => {
                                                const dailyUsage = quota.daily_limit > 0
                                                    ? (quota.current_daily_usage / quota.daily_limit) * 100
                                                    : 0;
                                                return (
                                                    <TableRow key={quota.user_id}>
                                                        <TableCell>
                                                            <div className="flex items-center gap-2">
                                                                <User className="w-4 h-4 text-gray-400"/>
                                                                {quota.username}
                                                            </div>
                                                        </TableCell>
                                                        <TableCell>{quota.daily_limit}</TableCell>
                                                        <TableCell>{quota.monthly_limit}</TableCell>
                                                        <TableCell>{quota.current_daily_usage}</TableCell>
                                                        <TableCell>{quota.current_monthly_usage}</TableCell>
                                                        <TableCell>
                                                            <div className="flex items-center gap-2">
                                                                <div className="w-24 bg-gray-200 rounded-full h-2">
                                                                    <div
                                                                        className={`h-2 rounded-full ${
                                                                            dailyUsage > 90 ? 'bg-red-600' :
                                                                                dailyUsage > 70 ? 'bg-yellow-600' :
                                                                                    'bg-green-600'
                                                                        }`}
                                                                        style={{width: `${Math.min(dailyUsage, 100)}%`}}
                                                                    />
                                                                </div>
                                                                <span
                                                                    className="text-sm">{dailyUsage.toFixed(1)}%</span>
                                                            </div>
                                                        </TableCell>
                                                    </TableRow>
                                                );
                                            })
                                        )}
                                    </TableBody>
                                </Table>
                            </div>
                        </CardContent>
                    </Card>
                </TabsContent>
            </Tabs>
        </div>
    );
}
