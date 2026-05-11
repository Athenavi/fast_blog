/**
 * 实时监控仪表板
 * 显示在线用户、访问量、系统健康等实时数据
 */

'use client';

import React, {useEffect, useState} from 'react';
import {Card, CardContent, CardDescription, CardHeader, CardTitle} from '@/components/ui/card';
import {Badge} from '@/components/ui/badge';
import {Button} from '@/components/ui/button';
import {Progress} from '@/components/ui/progress';
import {
    Users,
    Activity,
    Server,
    TrendingUp,
    RefreshCw,
    AlertCircle,
    CheckCircle,
    AlertTriangle
} from 'lucide-react';
import apiClient from '@/lib/api-client';

interface OnlineUser {
    user_id: number;
    last_active: string;
    duration_seconds: number;
}

interface SystemMetrics {
    cpu: {
        percent: number;
        count: number;
        frequency: number;
    };
    memory: {
        total: number;
        available: number;
        used: number;
        percent: number;
    };
    disk: {
        total: number;
        used: number;
        free: number;
        percent: number;
    };
    network: {
        bytes_sent: number;
        bytes_recv: number;
        packets_sent: number;
        packets_recv: number;
    };
    timestamp: string;
}

interface HealthStatus {
    overall_status: 'healthy' | 'warning' | 'critical';
    issues: Array<{
        component: string;
        status: 'warning' | 'critical';
        message: string;
    }>;
    metrics: SystemMetrics;
    timestamp: string;
}

interface DashboardData {
    online_users: {
        count: number;
        list: OnlineUser[];
    };
    visits: {
        today: number;
        realtime_5min: number;
        popular_endpoints: Array<{
            endpoint: string;
            visits: number;
        }>;
    };
    trending_articles: any[];
    system_health: HealthStatus;
    timestamp: string;
}

export default function RealtimeMonitorDashboard() {
    const [data, setData] = useState<DashboardData | null>(null);
    const [loading, setLoading] = useState(true);
    const [lastUpdate, setLastUpdate] = useState<Date | null>(null);
    const [autoRefresh, setAutoRefresh] = useState(true);

    // 加载仪表板数据
    const loadDashboard = async () => {
        try {
            setLoading(true);
            const response = await apiClient.get('/api/v1/monitor/dashboard');

            if (response.success && response.data) {
                setData(response.data as DashboardData);
                setLastUpdate(new Date());
            }
        } catch (error) {
            console.error('Failed to load dashboard:', error);
        } finally {
            setLoading(false);
        }
    };

    // 初始加载
    useEffect(() => {
        loadDashboard();
    }, []);

    // 自动刷新
    useEffect(() => {
        if (!autoRefresh) return;

        const interval = setInterval(() => {
            loadDashboard();
        }, 10000); // 每10秒刷新

        return () => clearInterval(interval);
    }, [autoRefresh]);

    // 格式化字节数
    const formatBytes = (bytes: number): string => {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return `${(bytes / Math.pow(k, i)).toFixed(2)} ${sizes[i]}`;
    };

    // 获取健康状态图标和颜色
    const getHealthIcon = (status: string) => {
        switch (status) {
            case 'healthy':
                return <CheckCircle className="w-6 h-6 text-green-500"/>;
            case 'warning':
                return <AlertTriangle className="w-6 h-6 text-yellow-500"/>;
            case 'critical':
                return <AlertCircle className="w-6 h-6 text-red-500"/>;
            default:
                return <Activity className="w-6 h-6 text-gray-500"/>;
        }
    };

    const getHealthColor = (status: string) => {
        switch (status) {
            case 'healthy':
                return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200';
            case 'warning':
                return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200';
            case 'critical':
                return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200';
            default:
                return 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200';
        }
    };

    if (loading && !data) {
        return (
            <div className="flex items-center justify-center h-96">
                <RefreshCw className="w-8 h-8 animate-spin text-blue-500"/>
            </div>
        );
    }

    if (!data) {
        return (
            <div className="text-center py-12">
                <AlertCircle className="w-12 h-12 mx-auto text-red-500 mb-4"/>
                <p className="text-lg text-gray-600">无法加载监控数据</p>
                <Button onClick={loadDashboard} className="mt-4">
                    重试
                </Button>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* 标题栏 */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold">实时监控仪表板</h1>
                    <p className="text-gray-600 dark:text-gray-400 mt-1">
                        {lastUpdate && `最后更新: ${lastUpdate.toLocaleTimeString()}`}
                    </p>
                </div>
                <div className="flex gap-2">
                    <Button
                        variant={autoRefresh ? 'default' : 'outline'}
                        size="sm"
                        onClick={() => setAutoRefresh(!autoRefresh)}
                    >
                        <Activity className="w-4 h-4 mr-2"/>
                        {autoRefresh ? '自动刷新中' : '开启自动刷新'}
                    </Button>
                    <Button variant="outline" size="sm" onClick={loadDashboard}>
                        <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`}/>
                        刷新
                    </Button>
                </div>
            </div>

            {/* 关键指标卡片 */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                {/* 在线用户 */}
                <Card>
                    <CardHeader className="pb-2">
                        <CardTitle className="text-sm font-medium flex items-center">
                            <Users className="w-4 h-4 mr-2 text-blue-500"/>
                            在线用户
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="text-3xl font-bold">{data.online_users.count}</div>
                        <p className="text-xs text-gray-600 dark:text-gray-400 mt-1">
                            当前在线
                        </p>
                    </CardContent>
                </Card>

                {/* 今日访问 */}
                <Card>
                    <CardHeader className="pb-2">
                        <CardTitle className="text-sm font-medium flex items-center">
                            <TrendingUp className="w-4 h-4 mr-2 text-green-500"/>
                            今日访问
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="text-3xl font-bold">{data.visits.today}</div>
                        <p className="text-xs text-gray-600 dark:text-gray-400 mt-1">
                            累计访问
                        </p>
                    </CardContent>
                </Card>

                {/* 实时访问 */}
                <Card>
                    <CardHeader className="pb-2">
                        <CardTitle className="text-sm font-medium flex items-center">
                            <Activity className="w-4 h-4 mr-2 text-purple-500"/>
                            实时访问
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="text-3xl font-bold">{data.visits.realtime_5min}</div>
                        <p className="text-xs text-gray-600 dark:text-gray-400 mt-1">
                            最近5分钟
                        </p>
                    </CardContent>
                </Card>

                {/* 系统健康 */}
                <Card>
                    <CardHeader className="pb-2">
                        <CardTitle className="text-sm font-medium flex items-center">
                            <Server className="w-4 h-4 mr-2 text-orange-500"/>
                            系统健康
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="flex items-center gap-2">
                            {getHealthIcon(data.system_health.overall_status)}
                            <Badge className={getHealthColor(data.system_health.overall_status)}>
                                {data.system_health.overall_status === 'healthy' ? '正常' :
                                    data.system_health.overall_status === 'warning' ? '警告' : '严重'}
                            </Badge>
                        </div>
                        <p className="text-xs text-gray-600 dark:text-gray-400 mt-2">
                            {data.system_health.issues.length} 个问题
                        </p>
                    </CardContent>
                </Card>
            </div>

            {/* 系统资源使用 */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                {/* CPU使用率 */}
                <Card>
                    <CardHeader>
                        <CardTitle>CPU 使用率</CardTitle>
                        <CardDescription>{data.system_health.metrics.cpu.count} 核心</CardDescription>
                    </CardHeader>
                    <CardContent>
                        <div className="text-3xl font-bold mb-2">
                            {data.system_health.metrics.cpu.percent.toFixed(1)}%
                        </div>
                        <Progress value={data.system_health.metrics.cpu.percent}/>
                    </CardContent>
                </Card>

                {/* 内存使用率 */}
                <Card>
                    <CardHeader>
                        <CardTitle>内存使用率</CardTitle>
                        <CardDescription>
                            {formatBytes(data.system_health.metrics.memory.used)} / {formatBytes(data.system_health.metrics.memory.total)}
                        </CardDescription>
                    </CardHeader>
                    <CardContent>
                        <div className="text-3xl font-bold mb-2">
                            {data.system_health.metrics.memory.percent.toFixed(1)}%
                        </div>
                        <Progress value={data.system_health.metrics.memory.percent}/>
                    </CardContent>
                </Card>

                {/* 磁盘使用率 */}
                <Card>
                    <CardHeader>
                        <CardTitle>磁盘使用率</CardTitle>
                        <CardDescription>
                            {formatBytes(data.system_health.metrics.disk.used)} / {formatBytes(data.system_health.metrics.disk.total)}
                        </CardDescription>
                    </CardHeader>
                    <CardContent>
                        <div className="text-3xl font-bold mb-2">
                            {data.system_health.metrics.disk.percent.toFixed(1)}%
                        </div>
                        <Progress value={data.system_health.metrics.disk.percent}/>
                    </CardContent>
                </Card>
            </div>

            {/* 告警信息 */}
            {data.system_health.issues.length > 0 && (
                <Card className="border-red-200 dark:border-red-800">
                    <CardHeader>
                        <CardTitle className="flex items-center text-red-600">
                            <AlertCircle className="w-5 h-5 mr-2"/>
                            系统告警
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="space-y-2">
                            {data.system_health.issues.map((issue, index) => (
                                <div key={index}
                                     className="flex items-start gap-2 p-3 bg-red-50 dark:bg-red-950 rounded-lg">
                                    <AlertTriangle className="w-5 h-5 text-red-500 mt-0.5"/>
                                    <div>
                                        <p className="font-medium">{issue.component}</p>
                                        <p className="text-sm text-gray-600 dark:text-gray-400">{issue.message}</p>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </CardContent>
                </Card>
            )}

            {/* 热门访问端点 */}
            <Card>
                <CardHeader>
                    <CardTitle>热门访问端点</CardTitle>
                    <CardDescription>最近60分钟的API访问统计</CardDescription>
                </CardHeader>
                <CardContent>
                    <div className="space-y-2">
                        {data.visits.popular_endpoints.map((endpoint, index) => (
                            <div key={index}
                                 className="flex items-center justify-between p-2 hover:bg-gray-50 dark:hover:bg-gray-800 rounded">
                                <code className="text-sm">{endpoint.endpoint}</code>
                                <Badge variant="secondary">{endpoint.visits} 次</Badge>
                            </div>
                        ))}
                        {data.visits.popular_endpoints.length === 0 && (
                            <p className="text-center text-gray-500 py-4">暂无数据</p>
                        )}
                    </div>
                </CardContent>
            </Card>

            {/* 在线用户列表 */}
            <Card>
                <CardHeader>
                    <CardTitle>在线用户列表</CardTitle>
                    <CardDescription>最近5分钟有活动的用户</CardDescription>
                </CardHeader>
                <CardContent>
                    <div className="space-y-2 max-h-96 overflow-y-auto">
                        {data.online_users.list.map((user) => (
                            <div key={user.user_id}
                                 className="flex items-center justify-between p-2 hover:bg-gray-50 dark:hover:bg-gray-800 rounded">
                                <span className="text-sm">用户 #{user.user_id}</span>
                                <div className="text-xs text-gray-500">
                                    在线 {Math.floor(user.duration_seconds / 60)} 分钟
                                </div>
                            </div>
                        ))}
                        {data.online_users.list.length === 0 && (
                            <p className="text-center text-gray-500 py-4">暂无在线用户</p>
                        )}
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}
