'use client';

import {useEffect, useState} from 'react';
import {Card, CardContent, CardDescription, CardHeader, CardTitle} from '@/components/ui/card';
import {Button} from '@/components/ui/button';
import {Input} from '@/components/ui/input';
import {Label} from '@/components/ui/label';
import {Switch} from '@/components/ui/switch';
import {Tabs, TabsContent, TabsList, TabsTrigger} from '@/components/ui/tabs';
import {Badge} from '@/components/ui/badge';
import {useToast} from '@/hooks/use-toast';
import {BarChart3, CheckCircle2, Globe, Mail, MessageSquare, Save, TestTube} from 'lucide-react';

interface IntegrationConfig {
    enabled: boolean;
    tracking_id?: string;
    api_key?: string;
    secret_key?: string;
    webhook_url?: string;
    settings?: Record<string, any>;
}

interface IntegrationsState {
    google_analytics: IntegrationConfig;
    baidu_analytics: IntegrationConfig;
    slack: IntegrationConfig;
    discord: IntegrationConfig;
    sendgrid: IntegrationConfig;
    mailgun: IntegrationConfig;
}

export default function IntegrationsPage() {
    const {toast} = useToast();
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [integrations, setIntegrations] = useState<IntegrationsState>({
        google_analytics: {enabled: false, tracking_id: ''},
        baidu_analytics: {enabled: false, tracking_id: ''},
        slack: {enabled: false, webhook_url: '', api_key: ''},
        discord: {enabled: false, webhook_url: ''},
        sendgrid: {enabled: false, api_key: '', settings: {}},
        mailgun: {enabled: false, api_key: '', secret_key: '', settings: {}},
    });

    useEffect(() => {
        loadIntegrations();
    }, []);

    const loadIntegrations = async () => {
        try {
            setLoading(true);
            const response = await fetch('/api/v2/integrations/config', {
                headers: {
                    'Authorization': `Bearer ${getAccessToken()}`,
                },
            });

            if (response.ok) {
                const data = await response.json();
                if (data.success && data.data) {
                    setIntegrations(data.data);
                }
            }
        } catch (error) {
            console.error('Failed to load integrations:', error);
            toast({
                title: '加载失败',
                description: '无法加载集成配置',
                variant: 'destructive',
            });
        } finally {
            setLoading(false);
        }
    };

    const saveIntegration = async (type: string, config: IntegrationConfig) => {
        try {
            setSaving(true);
            const response = await fetch(`/api/v2/integrations/${type}/config`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${getAccessToken()}`,
                },
                body: JSON.stringify(config),
            });

            const data = await response.json();

            if (data.success) {
                toast({
                    title: '保存成功',
                    description: `${getIntegrationName(type)}配置已保存`,
                });
            } else {
                throw new Error(data.error || '保存失败');
            }
        } catch (error) {
            console.error('Failed to save integration:', error);
            toast({
                title: '保存失败',
                description: error instanceof Error ? error.message : '未知错误',
                variant: 'destructive',
            });
        } finally {
            setSaving(false);
        }
    };

    const testIntegration = async (type: string) => {
        try {
            const response = await fetch(`/api/v2/integrations/${type}/test`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${getAccessToken()}`,
                },
            });

            const data = await response.json();

            if (data.success) {
                toast({
                    title: '测试成功',
                    description: data.message || '连接测试通过',
                });
            } else {
                throw new Error(data.error || '测试失败');
            }
        } catch (error) {
            console.error('Integration test failed:', error);
            toast({
                title: '测试失败',
                description: error instanceof Error ? error.message : '未知错误',
                variant: 'destructive',
            });
        }
    };

    const getIntegrationName = (type: string) => {
        const names: Record<string, string> = {
            google_analytics: 'Google Analytics',
            baidu_analytics: '百度统计',
            slack: 'Slack',
            discord: 'Discord',
            sendgrid: 'SendGrid',
            mailgun: 'Mailgun',
        };
        return names[type] || type;
    };

    const getAccessToken = () => {
        if (typeof document !== 'undefined') {
            const match = document.cookie.match(/access_token=([^;]+)/);
            return match ? match[1] : '';
        }
        return '';
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center py-12">
                <div className="text-center">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900 mx-auto mb-4"></div>
                    <p className="text-gray-600">加载�?..</p>
                </div>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            <div>
                <h1 className="text-3xl font-bold text-gray-900 dark:text-white">第三方服务集�?/h1>
                <p className="text-gray-600 dark:text-gray-400 mt-2">
                    配置和管理外部服务集成，包括分析工具、通知服务和邮件服�? </p>
            </div>

            <Tabs defaultValue="analytics" className="space-y-6">
                <TabsList className="grid w-full grid-cols-3">
                    <TabsTrigger value="analytics" className="flex items-center gap-2">
                        <BarChart3 className="w-4 h-4"/>
                        数据分析
                    </TabsTrigger>
                    <TabsTrigger value="notifications" className="flex items-center gap-2">
                        <MessageSquare className="w-4 h-4"/>
                        通知服务
                    </TabsTrigger>
                    <TabsTrigger value="email" className="flex items-center gap-2">
                        <Mail className="w-4 h-4"/>
                        邮件服务
                    </TabsTrigger>
                </TabsList>

                <TabsContent value="analytics" className="space-y-6">
                    <Card>
                        <CardHeader>
                            <div className="flex items-center justify-between">
                                <div className="flex items-center gap-3">
                                    <Globe className="w-5 h-5 text-blue-600"/>
                                    <div>
                                        <CardTitle>Google Analytics</CardTitle>
                                        <CardDescription>追踪网站访问数据和用户行�?/CardDescription>
                                    </div>
                                </div>
                                {integrations.google_analytics.enabled && (
                                    <Badge variant="default" className="bg-green-600">
                                        <CheckCircle2 className="w-3 h-3 mr-1"/>
                                        已启�? </Badge>
                                )}
                            </div>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <div className="flex items-center justify-between">
                                <Label htmlFor="ga-enabled">启用 Google Analytics</Label>
                                <Switch
                                    id="ga-enabled"
                                    checked={integrations.google_analytics.enabled}
                                    onCheckedChange={(checked) =>
                                        setIntegrations({
                                            ...integrations,
                                            google_analytics: {...integrations.google_analytics, enabled: checked},
                                        })
                                    }
                                />
                            </div>

                            {integrations.google_analytics.enabled && (
                                <>
                                    <div className="space-y-2">
                                        <Label htmlFor="ga-tracking-id">跟踪 ID</Label>
                                        <Input
                                            id="ga-tracking-id"
                                            placeholder="例如：G-XXXXXXXXXX"
                                            value={integrations.google_analytics.tracking_id || ''}
                                            onChange={(e) =>
                                                setIntegrations({
                                                    ...integrations,
                                                    google_analytics: {
                                                        ...integrations.google_analytics,
                                                        tracking_id: e.target.value,
                                                    },
                                                })
                                            }
                                        />
                                    </div>

                                    <div className="flex gap-2">
                                        <Button
                                            onClick={() => saveIntegration('google_analytics', integrations.google_analytics)}
                                            disabled={saving}
                                        >
                                            <Save className="w-4 h-4 mr-2"/>
                                            {saving ? '保存�?..' : '保存配置'}
                                        </Button>
                                        <Button
                                            variant="outline"
                                            onClick={() => testIntegration('google_analytics')}
                                        >
                                            <TestTube className="w-4 h-4 mr-2"/>
                                            测试连接
                                        </Button>
                                    </div>
                                </>
                            )}
                        </CardContent>
                    </Card>

                    <Card>
                        <CardHeader>
                            <div className="flex items-center justify-between">
                                <div className="flex items-center gap-3">
                                    <BarChart3 className="w-5 h-5 text-red-600"/>
                                    <div>
                                        <CardTitle>百度统计</CardTitle>
                                        <CardDescription>百度官方数据统计分析平台</CardDescription>
                                    </div>
                                </div>
                                {integrations.baidu_analytics.enabled && (
                                    <Badge variant="default" className="bg-green-600">
                                        <CheckCircle2 className="w-3 h-3 mr-1"/>
                                        已启�? </Badge>
                                )}
                            </div>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <div className="flex items-center justify-between">
                                <Label htmlFor="baidu-enabled">启用百度统计</Label>
                                <Switch
                                    id="baidu-enabled"
                                    checked={integrations.baidu_analytics.enabled}
                                    onCheckedChange={(checked) =>
                                        setIntegrations({
                                            ...integrations,
                                            baidu_analytics: {...integrations.baidu_analytics, enabled: checked},
                                        })
                                    }
                                />
                            </div>

                            {integrations.baidu_analytics.enabled && (
                                <>
                                    <div className="space-y-2">
                                        <Label htmlFor="baidu-tracking-id">站点 ID</Label>
                                        <Input
                                            id="baidu-tracking-id"
                                            placeholder="例如�?2345678"
                                            value={integrations.baidu_analytics.tracking_id || ''}
                                            onChange={(e) =>
                                                setIntegrations({
                                                    ...integrations,
                                                    baidu_analytics: {
                                                        ...integrations.baidu_analytics,
                                                        tracking_id: e.target.value,
                                                    },
                                                })
                                            }
                                        />
                                    </div>

                                    <div className="flex gap-2">
                                        <Button
                                            onClick={() => saveIntegration('baidu_analytics', integrations.baidu_analytics)}
                                            disabled={saving}
                                        >
                                            <Save className="w-4 h-4 mr-2"/>
                                            {saving ? '保存�?..' : '保存配置'}
                                        </Button>
                                        <Button
                                            variant="outline"
                                            onClick={() => testIntegration('baidu_analytics')}
                                        >
                                            <TestTube className="w-4 h-4 mr-2"/>
                                            测试连接
                                        </Button>
                                    </div>
                                </>
                            )}
                        </CardContent>
                    </Card>
                </TabsContent>

                <TabsContent value="notifications" className="space-y-6">
                    <Card>
                        <CardHeader>
                            <div className="flex items-center justify-between">
                                <div className="flex items-center gap-3">
                                    <MessageSquare className="w-5 h-5 text-purple-600"/>
                                    <div>
                                        <CardTitle>Slack</CardTitle>
                                        <CardDescription>发送通知�?Slack 频道</CardDescription>
                                    </div>
                                </div>
                                {integrations.slack.enabled && (
                                    <Badge variant="default" className="bg-green-600">
                                        <CheckCircle2 className="w-3 h-3 mr-1"/>
                                        已启�? </Badge>
                                )}
                            </div>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <div className="flex items-center justify-between">
                                <Label htmlFor="slack-enabled">启用 Slack</Label>
                                <Switch
                                    id="slack-enabled"
                                    checked={integrations.slack.enabled}
                                    onCheckedChange={(checked) =>
                                        setIntegrations({
                                            ...integrations,
                                            slack: {...integrations.slack, enabled: checked},
                                        })
                                    }
                                />
                            </div>

                            {integrations.slack.enabled && (
                                <>
                                    <div className="space-y-2">
                                        <Label htmlFor="slack-webhook">Webhook URL</Label>
                                        <Input
                                            id="slack-webhook"
                                            placeholder="https://hooks.slack.com/services/..."
                                            value={integrations.slack.webhook_url || ''}
                                            onChange={(e) =>
                                                setIntegrations({
                                                    ...integrations,
                                                    slack: {...integrations.slack, webhook_url: e.target.value},
                                                })
                                            }
                                        />
                                    </div>

                                    <div className="flex gap-2">
                                        <Button
                                            onClick={() => saveIntegration('slack', integrations.slack)}
                                            disabled={saving}
                                        >
                                            <Save className="w-4 h-4 mr-2"/>
                                            {saving ? '保存�?..' : '保存配置'}
                                        </Button>
                                        <Button
                                            variant="outline"
                                            onClick={() => testIntegration('slack')}
                                        >
                                            <TestTube className="w-4 h-4 mr-2"/>
                                            发送测试消�? </Button>
                                    </div>
                                </>
                            )}
                        </CardContent>
                    </Card>

                    <Card>
                        <CardHeader>
                            <div className="flex items-center justify-between">
                                <div className="flex items-center gap-3">
                                    <MessageSquare className="w-5 h-5 text-indigo-600"/>
                                    <div>
                                        <CardTitle>Discord</CardTitle>
                                        <CardDescription>发送通知�?Discord 服务�?/CardDescription>
                                    </div>
                                </div>
                                {integrations.discord.enabled && (
                                    <Badge variant="default" className="bg-green-600">
                                        <CheckCircle2 className="w-3 h-3 mr-1"/>
                                        已启�? </Badge>
                                )}
                            </div>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <div className="flex items-center justify-between">
                                <Label htmlFor="discord-enabled">启用 Discord</Label>
                                <Switch
                                    id="discord-enabled"
                                    checked={integrations.discord.enabled}
                                    onCheckedChange={(checked) =>
                                        setIntegrations({
                                            ...integrations,
                                            discord: {...integrations.discord, enabled: checked},
                                        })
                                    }
                                />
                            </div>

                            {integrations.discord.enabled && (
                                <>
                                    <div className="space-y-2">
                                        <Label htmlFor="discord-webhook">Webhook URL</Label>
                                        <Input
                                            id="discord-webhook"
                                            placeholder="https://discord.com/api/webhooks/..."
                                            value={integrations.discord.webhook_url || ''}
                                            onChange={(e) =>
                                                setIntegrations({
                                                    ...integrations,
                                                    discord: {...integrations.discord, webhook_url: e.target.value},
                                                })
                                            }
                                        />
                                    </div>

                                    <div className="flex gap-2">
                                        <Button
                                            onClick={() => saveIntegration('discord', integrations.discord)}
                                            disabled={saving}
                                        >
                                            <Save className="w-4 h-4 mr-2"/>
                                            {saving ? '保存�?..' : '保存配置'}
                                        </Button>
                                        <Button
                                            variant="outline"
                                            onClick={() => testIntegration('discord')}
                                        >
                                            <TestTube className="w-4 h-4 mr-2"/>
                                            发送测试消�? </Button>
                                    </div>
                                </>
                            )}
                        </CardContent>
                    </Card>
                </TabsContent>

                <TabsContent value="email" className="space-y-6">
                    <Card>
                        <CardHeader>
                            <div className="flex items-center justify-between">
                                <div className="flex items-center gap-3">
                                    <Mail className="w-5 h-5 text-orange-600"/>
                                    <div>
                                        <CardTitle>SendGrid</CardTitle>
                                        <CardDescription>专业的邮件发送服�?/CardDescription>
                                    </div>
                                </div>
                                {integrations.sendgrid.enabled && (
                                    <Badge variant="default" className="bg-green-600">
                                        <CheckCircle2 className="w-3 h-3 mr-1"/>
                                        已启�? </Badge>
                                )}
                            </div>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <div className="flex items-center justify-between">
                                <Label htmlFor="sendgrid-enabled">启用 SendGrid</Label>
                                <Switch
                                    id="sendgrid-enabled"
                                    checked={integrations.sendgrid.enabled}
                                    onCheckedChange={(checked) =>
                                        setIntegrations({
                                            ...integrations,
                                            sendgrid: {...integrations.sendgrid, enabled: checked},
                                        })
                                    }
                                />
                            </div>

                            {integrations.sendgrid.enabled && (
                                <>
                                    <div className="space-y-2">
                                        <Label htmlFor="sendgrid-api-key">API Key</Label>
                                        <Input
                                            id="sendgrid-api-key"
                                            type="password"
                                            placeholder="SG.xxxxxxxxxxxx"
                                            value={integrations.sendgrid.api_key || ''}
                                            onChange={(e) =>
                                                setIntegrations({
                                                    ...integrations,
                                                    sendgrid: {...integrations.sendgrid, api_key: e.target.value},
                                                })
                                            }
                                        />
                                    </div>

                                    <div className="flex gap-2">
                                        <Button
                                            onClick={() => saveIntegration('sendgrid', integrations.sendgrid)}
                                            disabled={saving}
                                        >
                                            <Save className="w-4 h-4 mr-2"/>
                                            {saving ? '保存�?..' : '保存配置'}
                                        </Button>
                                        <Button
                                            variant="outline"
                                            onClick={() => testIntegration('sendgrid')}
                                        >
                                            <TestTube className="w-4 h-4 mr-2"/>
                                            发送测试邮�? </Button>
                                    </div>
                                </>
                            )}
                        </CardContent>
                    </Card>

                    <Card>
                        <CardHeader>
                            <div className="flex items-center justify-between">
                                <div className="flex items-center gap-3">
                                    <Mail className="w-5 h-5 text-teal-600"/>
                                    <div>
                                        <CardTitle>Mailgun</CardTitle>
                                        <CardDescription>强大的邮件发�?API 服务</CardDescription>
                                    </div>
                                </div>
                                {integrations.mailgun.enabled && (
                                    <Badge variant="default" className="bg-green-600">
                                        <CheckCircle2 className="w-3 h-3 mr-1"/>
                                        已启�? </Badge>
                                )}
                            </div>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <div className="flex items-center justify-between">
                                <Label htmlFor="mailgun-enabled">启用 Mailgun</Label>
                                <Switch
                                    id="mailgun-enabled"
                                    checked={integrations.mailgun.enabled}
                                    onCheckedChange={(checked) =>
                                        setIntegrations({
                                            ...integrations,
                                            mailgun: {...integrations.mailgun, enabled: checked},
                                        })
                                    }
                                />
                            </div>

                            {integrations.mailgun.enabled && (
                                <>
                                    <div className="space-y-2">
                                        <Label htmlFor="mailgun-api-key">API Key</Label>
                                        <Input
                                            id="mailgun-api-key"
                                            type="password"
                                            placeholder="key-xxxxxxxxxxxx"
                                            value={integrations.mailgun.api_key || ''}
                                            onChange={(e) =>
                                                setIntegrations({
                                                    ...integrations,
                                                    mailgun: {...integrations.mailgun, api_key: e.target.value},
                                                })
                                            }
                                        />
                                    </div>

                                    <div className="space-y-2">
                                        <Label htmlFor="mailgun-domain">域名</Label>
                                        <Input
                                            id="mailgun-domain"
                                            placeholder="mg.yourdomain.com"
                                            value={integrations.mailgun.settings?.domain || ''}
                                            onChange={(e) =>
                                                setIntegrations({
                                                    ...integrations,
                                                    mailgun: {
                                                        ...integrations.mailgun,
                                                        settings: {
                                                            ...integrations.mailgun.settings,
                                                            domain: e.target.value,
                                                        },
                                                    },
                                                })
                                            }
                                        />
                                    </div>

                                    <div className="flex gap-2">
                                        <Button
                                            onClick={() => saveIntegration('mailgun', integrations.mailgun)}
                                            disabled={saving}
                                        >
                                            <Save className="w-4 h-4 mr-2"/>
                                            {saving ? '保存�?..' : '保存配置'}
                                        </Button>
                                        <Button
                                            variant="outline"
                                            onClick={() => testIntegration('mailgun')}
                                        >
                                            <TestTube className="w-4 h-4 mr-2"/>
                                            发送测试邮�? </Button>
                                    </div>
                                </>
                            )}
                        </CardContent>
                    </Card>
                </TabsContent>
            </Tabs>
        </div>
    );
}
