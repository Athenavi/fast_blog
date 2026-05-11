'use client';

/**
 * 邮件营销插件 - 订阅者管理页面
 */

import {useEffect, useState} from 'react';
import {Card, CardContent, CardDescription, CardHeader, CardTitle} from '@/components/ui/card';
import {Button} from '@/components/ui/button';
import {Input} from '@/components/ui/input';
import {Label} from '@/components/ui/label';
import {Textarea} from '@/components/ui/textarea';
import {Tabs, TabsContent, TabsList, TabsTrigger} from '@/components/ui/tabs';
import {Badge} from '@/components/ui/badge';
import {apiClient} from '@/lib/api-client';

interface Subscriber {
    id: number;
    email: string;
    name?: string;
    status: 'active' | 'unsubscribed' | 'pending';
    subscribed_at: string;
}

export default function EmailMarketingPage() {
    const [subscribers, setSubscribers] = useState<Subscriber[]>([]);
    const [stats, setStats] = useState<any>(null);
    const [loading, setLoading] = useState(true);
    const [emailForm, setEmailForm] = useState({
        subject: '',
        content: '',
    });
    const [sending, setSending] = useState(false);

    useEffect(() => {
        loadData();
    }, []);

    const loadData = async () => {
        try {
            setLoading(true);
            const [subsRes, statsRes] = await Promise.all([
                apiClient.get('/plugins/email-marketing/subscribers'),
                apiClient.post('/plugins/email-marketing/action', {
                    action: 'get_subscriber_stats',
                    params: {},
                }),
            ]);

            if (subsRes.success) {
                setSubscribers(subsRes.data as Subscriber[] || []);
            }

            if (statsRes.success) {
                setStats(statsRes.data);
            }
        } catch (error) {
            console.error('Failed to load data:', error);
        } finally {
            setLoading(false);
        }
    };

    const sendEmail = async () => {
        if (!emailForm.subject || !emailForm.content) {
            alert('请填写主题和内容');
            return;
        }

        if (!confirm(`确定要发送给 ${subscribers.filter(s => s.status === 'active').length} 个订阅者吗?`)) {
            return;
        }

        try {
            setSending(true);
            const response = await apiClient.post('/plugins/email-marketing/action', {
                action: 'send_bulk_email',
                params: {
                    subject: emailForm.subject,
                    content: emailForm.content,
                    recipients: subscribers.filter(s => s.status === 'active').map(s => s.email),
                },
            });

            if (response.success) {
                alert(`发送完成! 成功: ${(response.data as any).sent}, 失败: ${(response.data as any).failed}`);
                setEmailForm({subject: '', content: ''});
            } else {
                alert('发送失败: ' + response.error);
            }
        } catch (error) {
            alert('发送失败');
        } finally {
            setSending(false);
        }
    };

    const exportSubscribers = async () => {
        try {
            const response = await apiClient.post('/plugins/email-marketing/action', {
                action: 'export_subscribers',
                params: {format: 'csv'},
            });

            if (response.success) {
                // 下载CSV文件
                const blob = new Blob([(response.data as any).csv], {type: 'text/csv'});
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = 'subscribers.csv';
                a.click();
                window.URL.revokeObjectURL(url);
            }
        } catch (error) {
            alert('导出失败');
        }
    };

    if (loading) {
        return <div className="flex justify-center p-8">加载中...</div>;
    }

    return (
        <div className="container mx-auto p-6 space-y-6">
            <div>
                <h1 className="text-3xl font-bold">邮件营销</h1>
                <p className="text-gray-600 dark:text-gray-400 mt-2">
                    管理邮件订阅者和发送营销活动
                </p>
            </div>

            {/* 统计卡片 */}
            {stats && (
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                    <Card>
                        <CardContent className="pt-6">
                            <div className="text-2xl font-bold">{stats.total_subscribers || 0}</div>
                            <p className="text-sm text-gray-600">总订阅者</p>
                        </CardContent>
                    </Card>
                    <Card>
                        <CardContent className="pt-6">
                            <div className="text-2xl font-bold text-green-600">{stats.active_subscribers || 0}</div>
                            <p className="text-sm text-gray-600">活跃订阅者</p>
                        </CardContent>
                    </Card>
                    <Card>
                        <CardContent className="pt-6">
                            <div className="text-2xl font-bold text-blue-600">{stats.confirmed_subscribers || 0}</div>
                            <p className="text-sm text-gray-600">已确认</p>
                        </CardContent>
                    </Card>
                    <Card>
                        <CardContent className="pt-6">
                            <div className="text-2xl font-bold text-gray-600">{stats.total_emails_sent || 0}</div>
                            <p className="text-sm text-gray-600">已发送邮件</p>
                        </CardContent>
                    </Card>
                </div>
            )}

            <Tabs defaultValue="subscribers">
                <TabsList>
                    <TabsTrigger value="subscribers">订阅者管理</TabsTrigger>
                    <TabsTrigger value="compose">撰写邮件</TabsTrigger>
                    <TabsTrigger value="settings">SMTP设置</TabsTrigger>
                </TabsList>

                {/* 订阅者列表 */}
                <TabsContent value="subscribers" className="space-y-4">
                    <Card>
                        <CardHeader>
                            <div className="flex justify-between items-center">
                                <div>
                                    <CardTitle>订阅者列表</CardTitle>
                                    <CardDescription>管理所有邮件订阅者</CardDescription>
                                </div>
                                <Button onClick={exportSubscribers} variant="outline">
                                    导出CSV
                                </Button>
                            </div>
                        </CardHeader>
                        <CardContent>
                            <div className="overflow-x-auto">
                                <table className="w-full">
                                    <thead>
                                    <tr className="border-b">
                                        <th className="text-left p-2">邮箱</th>
                                        <th className="text-left p-2">姓名</th>
                                        <th className="text-left p-2">状态</th>
                                        <th className="text-left p-2">订阅时间</th>
                                    </tr>
                                    </thead>
                                    <tbody>
                                    {subscribers.map((sub) => (
                                        <tr key={sub.id} className="border-b hover:bg-gray-50 dark:hover:bg-gray-800">
                                            <td className="p-2">{sub.email}</td>
                                            <td className="p-2">{sub.name || '-'}</td>
                                            <td className="p-2">
                                                <Badge variant={sub.status === 'active' ? 'default' : 'secondary'}>
                                                    {sub.status}
                                                </Badge>
                                            </td>
                                            <td className="p-2 text-sm text-gray-600">
                                                {new Date(sub.subscribed_at).toLocaleDateString()}
                                            </td>
                                        </tr>
                                    ))}
                                    </tbody>
                                </table>

                                {subscribers.length === 0 && (
                                    <div className="text-center py-8 text-gray-600">
                                        暂无订阅者
                                    </div>
                                )}
                            </div>
                        </CardContent>
                    </Card>
                </TabsContent>

                {/* 撰写邮件 */}
                <TabsContent value="compose" className="space-y-4">
                    <Card>
                        <CardHeader>
                            <CardTitle>撰写邮件</CardTitle>
                            <CardDescription>
                                发送给 {subscribers.filter(s => s.status === 'active').length} 个活跃订阅者
                            </CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <div>
                                <Label>邮件主题</Label>
                                <Input
                                    value={emailForm.subject}
                                    onChange={(e) => setEmailForm({...emailForm, subject: e.target.value})}
                                    placeholder="输入邮件主题"
                                />
                            </div>

                            <div>
                                <Label>邮件内容 (HTML)</Label>
                                <Textarea
                                    value={emailForm.content}
                                    onChange={(e) => setEmailForm({...emailForm, content: e.target.value})}
                                    placeholder="<h1>您好!</h1><p>这是测试邮件内容...</p>"
                                    rows={10}
                                />
                            </div>

                            <div className="flex gap-2">
                                <Button onClick={sendEmail} disabled={sending}>
                                    {sending ? '发送中...' : '发送邮件'}
                                </Button>
                                <Button variant="outline" onClick={() => setEmailForm({subject: '', content: ''})}>
                                    清空
                                </Button>
                            </div>
                        </CardContent>
                    </Card>
                </TabsContent>

                {/* SMTP设置 */}
                <TabsContent value="settings">
                    <Card>
                        <CardHeader>
                            <CardTitle>SMTP配置</CardTitle>
                            <CardDescription>配置邮件发送服务器</CardDescription>
                        </CardHeader>
                        <CardContent>
                            <p className="text-gray-600">
                                请在插件管理页面配置SMTP设置。
                            </p>
                            <Button
                                className="mt-4"
                                variant="outline"
                                onClick={() => window.location.href = '/admin/plugins'}
                            >
                                前往插件管理
                            </Button>
                        </CardContent>
                    </Card>
                </TabsContent>
            </Tabs>
        </div>
    );
}
