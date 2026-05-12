'use client';

import {useEffect, useState} from 'react';
import {Card, CardContent, CardHeader, CardTitle} from '@/components/ui/card';
import {Button} from '@/components/ui/button';
import {Input} from '@/components/ui/input';
import {Label} from '@/components/ui/label';
import {Badge} from '@/components/ui/badge';
import {Table, TableBody, TableCell, TableHead, TableHeader, TableRow} from '@/components/ui/table';
import {Select, SelectContent, SelectItem, SelectTrigger, SelectValue} from '@/components/ui/select';
import {Tabs, TabsContent, TabsList, TabsTrigger} from '@/components/ui/tabs';
import {useToast} from '@/hooks/use-toast';
import {Activity, Download, LogIn, RefreshCw, Search, Shield, User} from 'lucide-react';

interface AuditLog {
    id: number;
    user_id?: number;
    username?: string;
    action: string;
    resource_type: string;
    resource_id?: number;
    ip_address?: string;
    user_agent?: string;
    details?: string;
    created_at: string;
}

interface LoginLog {
    id: number;
    username: string;
    ip_address: string;
    user_agent?: string;
    is_success: boolean;
    failure_reason?: string;
    created_at: string;
}

interface ChangeLog {
    id: number;
    user_id?: number;
    username?: string;
    action: string;
    resource_type: string;
    resource_id?: number;
    old_values?: Record<string, any>;
    new_values?: Record<string, any>;
    created_at: string;
}

export default function AuditLogsPage() {
    const {toast} = useToast();
    const [loading, setLoading] = useState(true);
    const [activeTab, setActiveTab] = useState('audit');

    const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
    const [loginLogs, setLoginLogs] = useState<LoginLog[]>([]);
    const [changeLogs, setChangeLogs] = useState<ChangeLog[]>([]);

    const [searchTerm, setSearchTerm] = useState('');
    const [actionFilter, setActionFilter] = useState('all');
    const [resourceFilter, setResourceFilter] = useState('all');
    const [dateFrom, setDateFrom] = useState('');
    const [dateTo, setDateTo] = useState('');

    useEffect(() => {
        loadLogs();
    }, [activeTab]);

    const loadLogs = async () => {
        try {
            setLoading(true);
            const token = getAccessToken();

            if (activeTab === 'audit') {
                const response = await fetch('/api/v1/audit-logs', {
                    headers: {'Authorization': `Bearer ${token}`},
                });
                if (response.ok) {
                    const data = await response.json();
                    if (data.success) {
                        setAuditLogs(data.data.logs || []);
                    }
                }
            } else if (activeTab === 'login') {
                const response = await fetch('/api/v1/login-logs', {
                    headers: {'Authorization': `Bearer ${token}`},
                });
                if (response.ok) {
                    const data = await response.json();
                    if (data.success) {
                        setLoginLogs(data.data.logs || []);
                    }
                }
            } else if (activeTab === 'changes') {
                const response = await fetch('/api/v1/change-logs', {
                    headers: {'Authorization': `Bearer ${token}`},
                });
                if (response.ok) {
                    const data = await response.json();
                    if (data.success) {
                        setChangeLogs(data.data.logs || []);
                    }
                }
            }
        } catch (error) {
            console.error('Failed to load logs:', error);
            toast({
                title: '加载失败',
                description: '无法加载日志数据',
                variant: 'destructive',
            });
        } finally {
            setLoading(false);
        }
    };

    const exportLogs = async (format: 'json' | 'csv') => {
        try {
            const token = getAccessToken();
            const params = new URLSearchParams({
                format,
                action: actionFilter !== 'all' ? actionFilter : '',
                resource: resourceFilter !== 'all' ? resourceFilter : '',
                search: searchTerm,
                date_from: dateFrom,
                date_to: dateTo,
            });

            const response = await fetch(`/api/v1/audit-logs/export?${params}`, {
                headers: {'Authorization': `Bearer ${token}`},
            });

            if (response.ok) {
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `audit_logs_${new Date().toISOString().split('T')[0]}.${format}`;
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);

                toast({
                    title: '导出成功',
                    description: `日志已导出为 ${format.toUpperCase()} 格式`,
                });
            }
        } catch (error) {
            console.error('Export failed:', error);
            toast({
                title: '导出失败',
                description: '无法导出日志',
                variant: 'destructive',
            });
        }
    };

    const getAccessToken = () => {
        if (typeof document !== 'undefined') {
            const match = document.cookie.match(/access_token=([^;]+)/);
            return match ? match[1] : '';
        }
        return '';
    };

    const formatDate = (dateString: string) => {
        return new Date(dateString).toLocaleString('zh-CN');
    };

    const getActionBadge = (action: string) => {
        const colors: Record<string, string> = {
            CREATE: 'bg-green-600',
            UPDATE: 'bg-blue-600',
            DELETE: 'bg-red-600',
            LOGIN: 'bg-purple-600',
            LOGOUT: 'bg-gray-600',
        };
        return colors[action] || 'bg-gray-600';
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center py-12">
                <div className="text-center">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900 mx-auto mb-4"></div>
                    <p className="text-gray-600">加载中...</p>
                </div>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            <div>
                <h1 className="text-3xl font-bold text-gray-900 dark:text-white">审计日志</h1>
                <p className="text-gray-600 dark:text-gray-400 mt-2">
                    查看和管理系统操作日志、登录日志和数据变更历史
                </p>
            </div>

            <Tabs value={activeTab} onValueChange={setActiveTab}>
                <TabsList className="grid w-full grid-cols-3">
                    <TabsTrigger value="audit" className="flex items-center gap-2">
                        <Activity className="w-4 h-4"/>
                        操作日志
                    </TabsTrigger>
                    <TabsTrigger value="login" className="flex items-center gap-2">
                        <LogIn className="w-4 h-4"/>
                        登录日志
                    </TabsTrigger>
                    <TabsTrigger value="changes" className="flex items-center gap-2">
                        <Shield className="w-4 h-4"/>
                        变更历史
                    </TabsTrigger>
                </TabsList>

                <TabsContent value="audit" className="space-y-4 mt-6">
                    <Card>
                        <CardHeader>
                            <div className="flex items-center justify-between">
                                <CardTitle>操作日志</CardTitle>
                                <div className="flex gap-2">
                                    <Button
                                        variant="outline"
                                        size="sm"
                                        onClick={() => exportLogs('csv')}
                                    >
                                        <Download className="w-4 h-4 mr-2"/>
                                        导出CSV
                                    </Button>
                                    <Button
                                        variant="outline"
                                        size="sm"
                                        onClick={() => exportLogs('json')}
                                    >
                                        <Download className="w-4 h-4 mr-2"/>
                                        导出JSON
                                    </Button>
                                    <Button
                                        variant="outline"
                                        size="sm"
                                        onClick={loadLogs}
                                    >
                                        <RefreshCw className="w-4 h-4 mr-2"/>
                                        刷新
                                    </Button>
                                </div>
                            </div>
                        </CardHeader>
                        <CardContent>
                            <div className="space-y-4 mb-6">
                                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                                    <div>
                                        <Label>搜索</Label>
                                        <div className="relative">
                                            <Search
                                                className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400"/>
                                            <Input
                                                placeholder="搜索用户名或详情..."
                                                value={searchTerm}
                                                onChange={(e) => setSearchTerm(e.target.value)}
                                                className="pl-10"
                                            />
                                        </div>
                                    </div>
                                    <div>
                                        <Label>操作类型</Label>
                                        <Select value={actionFilter} onValueChange={setActionFilter}>
                                            <SelectTrigger>
                                                <SelectValue/>
                                            </SelectTrigger>
                                            <SelectContent>
                                                <SelectItem value="all">全部</SelectItem>
                                                <SelectItem value="CREATE">创建</SelectItem>
                                                <SelectItem value="UPDATE">更新</SelectItem>
                                                <SelectItem value="DELETE">删除</SelectItem>
                                                <SelectItem value="LOGIN">登录</SelectItem>
                                                <SelectItem value="LOGOUT">登出</SelectItem>
                                            </SelectContent>
                                        </Select>
                                    </div>
                                    <div>
                                        <Label>资源类型</Label>
                                        <Select value={resourceFilter} onValueChange={setResourceFilter}>
                                            <SelectTrigger>
                                                <SelectValue/>
                                            </SelectTrigger>
                                            <SelectContent>
                                                <SelectItem value="all">全部</SelectItem>
                                                <SelectItem value="article">文章</SelectItem>
                                                <SelectItem value="user">用户</SelectItem>
                                                <SelectItem value="category">分类</SelectItem>
                                                <SelectItem value="media">媒体</SelectItem>
                                                <SelectItem value="comment">评论</SelectItem>
                                            </SelectContent>
                                        </Select>
                                    </div>
                                    <div>
                                        <Label>日期范围</Label>
                                        <div className="flex gap-2">
                                            <Input
                                                type="date"
                                                value={dateFrom}
                                                onChange={(e) => setDateFrom(e.target.value)}
                                            />
                                            <Input
                                                type="date"
                                                value={dateTo}
                                                onChange={(e) => setDateTo(e.target.value)}
                                            />
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <div className="border rounded-lg">
                                <Table>
                                    <TableHeader>
                                        <TableRow>
                                            <TableHead>时间</TableHead>
                                            <TableHead>用户</TableHead>
                                            <TableHead>操作</TableHead>
                                            <TableHead>资源</TableHead>
                                            <TableHead>IP地址</TableHead>
                                            <TableHead>详情</TableHead>
                                        </TableRow>
                                    </TableHeader>
                                    <TableBody>
                                        {auditLogs.length === 0 ? (
                                            <TableRow>
                                                <TableCell colSpan={6} className="text-center py-8 text-gray-500">
                                                    暂无操作日志
                                                </TableCell>
                                            </TableRow>
                                        ) : (
                                            auditLogs.map((log) => (
                                                <TableRow key={log.id}>
                                                    <TableCell className="whitespace-nowrap">
                                                        {formatDate(log.created_at)}
                                                    </TableCell>
                                                    <TableCell>
                                                        <div className="flex items-center gap-2">
                                                            <User className="w-4 h-4 text-gray-400"/>
                                                            {log.username || '系统'}
                                                        </div>
                                                    </TableCell>
                                                    <TableCell>
                                                        <Badge className={getActionBadge(log.action)}>
                                                            {log.action}
                                                        </Badge>
                                                    </TableCell>
                                                    <TableCell>
                                                        {log.resource_type}
                                                        {log.resource_id && ` #${log.resource_id}`}
                                                    </TableCell>
                                                    <TableCell className="font-mono text-sm">
                                                        {log.ip_address || '-'}
                                                    </TableCell>
                                                    <TableCell className="max-w-xs truncate">
                                                        {log.details || '-'}
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

                <TabsContent value="login" className="space-y-4 mt-6">
                    <Card>
                        <CardHeader>
                            <div className="flex items-center justify-between">
                                <CardTitle>登录日志</CardTitle>
                                <Button variant="outline" size="sm" onClick={loadLogs}>
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
                                            <TableHead>时间</TableHead>
                                            <TableHead>用户名</TableHead>
                                            <TableHead>IP地址</TableHead>
                                            <TableHead>状态</TableHead>
                                            <TableHead>User Agent</TableHead>
                                        </TableRow>
                                    </TableHeader>
                                    <TableBody>
                                        {loginLogs.length === 0 ? (
                                            <TableRow>
                                                <TableCell colSpan={5} className="text-center py-8 text-gray-500">
                                                    暂无登录日志
                                                </TableCell>
                                            </TableRow>
                                        ) : (
                                            loginLogs.map((log) => (
                                                <TableRow key={log.id}>
                                                    <TableCell className="whitespace-nowrap">
                                                        {formatDate(log.created_at)}
                                                    </TableCell>
                                                    <TableCell>{log.username}</TableCell>
                                                    <TableCell className="font-mono text-sm">
                                                        {log.ip_address}
                                                    </TableCell>
                                                    <TableCell>
                                                        {log.is_success ? (
                                                            <Badge className="bg-green-600">成功</Badge>
                                                        ) : (
                                                            <Badge variant="destructive">
                                                                失败{log.failure_reason && `: ${log.failure_reason}`}
                                                            </Badge>
                                                        )}
                                                    </TableCell>
                                                    <TableCell className="max-w-xs truncate text-sm text-gray-500">
                                                        {log.user_agent || '-'}
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

                <TabsContent value="changes" className="space-y-4 mt-6">
                    <Card>
                        <CardHeader>
                            <div className="flex items-center justify-between">
                                <CardTitle>数据变更历史</CardTitle>
                                <Button variant="outline" size="sm" onClick={loadLogs}>
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
                                            <TableHead>时间</TableHead>
                                            <TableHead>用户</TableHead>
                                            <TableHead>操作</TableHead>
                                            <TableHead>资源</TableHead>
                                            <TableHead>变更内容</TableHead>
                                        </TableRow>
                                    </TableHeader>
                                    <TableBody>
                                        {changeLogs.length === 0 ? (
                                            <TableRow>
                                                <TableCell colSpan={5} className="text-center py-8 text-gray-500">
                                                    暂无变更记录
                                                </TableCell>
                                            </TableRow>
                                        ) : (
                                            changeLogs.map((log) => (
                                                <TableRow key={log.id}>
                                                    <TableCell className="whitespace-nowrap">
                                                        {formatDate(log.created_at)}
                                                    </TableCell>
                                                    <TableCell>{log.username || '系统'}</TableCell>
                                                    <TableCell>
                                                        <Badge className={getActionBadge(log.action)}>
                                                            {log.action}
                                                        </Badge>
                                                    </TableCell>
                                                    <TableCell>
                                                        {log.resource_type}
                                                        {log.resource_id && ` #${log.resource_id}`}
                                                    </TableCell>
                                                    <TableCell>
                                                        <div className="text-sm space-y-1">
                                                            {log.old_values && (
                                                                <div className="text-red-600">
                                                                    <span className="font-semibold">旧值:</span>{' '}
                                                                    {JSON.stringify(log.old_values)}
                                                                </div>
                                                            )}
                                                            {log.new_values && (
                                                                <div className="text-green-600">
                                                                    <span className="font-semibold">新值:</span>{' '}
                                                                    {JSON.stringify(log.new_values)}
                                                                </div>
                                                            )}
                                                        </div>
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
            </Tabs>
        </div>
    );
}
