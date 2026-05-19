/**
 * 站点健康检查面板 - 显示系统健康状态
 */
'use client';

import {useEffect, useState} from 'react';
import {Card, CardContent, CardDescription, CardHeader, CardTitle} from '@/components/ui/card';
import {Badge} from '@/components/ui/badge';
import {Progress} from '@/components/ui/progress';
import {AlertCircle, CheckCircle2, Database, HardDrive, Server, Shield, XCircle} from 'lucide-react';
import apiClient from '@/lib/api-client';

interface HealthCheck {
    name: string;
    status: 'ok' | 'warning' | 'error';
    message: string;
    icon: React.ReactNode;
}

interface SystemInfo {
    python_version?: string;
    platform?: string;
    environment?: string;
    debug_mode?: boolean;
}

export default function SiteHealthPanel() {
    const [healthChecks, setHealthChecks] = useState<HealthCheck[]>([]);
    const [systemInfo, setSystemInfo] = useState<SystemInfo>({});
    const [diskUsage, setDiskUsage] = useState({used: 0, total: 100, percentage: 0});
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchHealthData();
    }, []);

    const fetchHealthData = async () => {
        try {
            setLoading(true);

            // 获取系统信息
            const systemRes = await apiClient.get('/system/info').catch(() => ({success: false, data: null}));
            if (systemRes.success && systemRes.data) {
                setSystemInfo(systemRes.data as any);
            }

            // 获取站点健康检查
            const healthRes = await apiClient.get('/system/health').catch(() => ({success: false, data: null}));

            const checks: HealthCheck[] = [];

            // Python版本检查
            if (systemRes.success && (systemRes.data as any)?.python_version) {
                const version = (systemRes.data as any).python_version;
                const [major, minor] = version.split('.').map(Number);

                if (major >= 3 && minor >= 9) {
                    checks.push({
                        name: 'Python 版本',
                        status: 'ok',
                        message: `版本 ${version} - 符合要求`,
                        icon: <Server className="h-4 w-4 text-green-500"/>
                    });
                } else {
                    checks.push({
                        name: 'Python 版本',
                        status: 'warning',
                        message: `版本 ${version} - 建议升级到 3.9+`,
                        icon: <AlertCircle className="h-4 w-4 text-yellow-500"/>
                    });
                }
            }

            // 数据库状态检查
            if (healthRes.success && (healthRes.data as any)?.checks) {
                const healthData = healthRes.data as any;
                const dbChecks = healthData.checks.database || [];
                const systemChecks = healthData.checks.system || [];
                const storageChecks = healthData.checks.storage || [];
                const securityChecks = healthData.checks.security || [];

                // 数据库连接
                const dbConnection = dbChecks.find((c: any) => c.name === '数据库连接');
                if (dbConnection) {
                    checks.push({
                        name: '数据库连接',
                        status: dbConnection.status === 'pass' ? 'ok' : 'error',
                        message: dbConnection.value || (dbConnection.status === 'pass' ? '连接正常' : '连接异常'),
                        icon: <Database
                            className={`h-4 w-4 ${dbConnection.status === 'pass' ? 'text-green-500' : 'text-red-500'}`}/>
                    });
                }

                // 磁盘空间
                const diskSpace = systemChecks.find((c: any) => c.name === '可用磁盘空间');
                if (diskSpace) {
                    // 解析磁盘空间信息
                    const valueStr = diskSpace.value || '0 GB';
                    const freeGB = parseFloat(valueStr);
                    const freeBytes = freeGB * 1024 * 1024 * 1024;

                    // 估算总空间（假设已用 + 可用）
                    const totalBytes = freeBytes * 3; // 粗略估计
                    const usedBytes = totalBytes - freeBytes;
                    const percentage = (usedBytes / totalBytes) * 100;

                    setDiskUsage({
                        used: usedBytes,
                        total: totalBytes,
                        percentage: percentage
                    });

                    let status: 'ok' | 'warning' | 'error' = diskSpace.status === 'pass' ? 'ok' : diskSpace.status === 'warning' ? 'warning' : 'error';

                    checks.push({
                        name: '磁盘空间',
                        status,
                        message: `${formatBytes(usedBytes)} / ${formatBytes(totalBytes)} (${percentage.toFixed(1)}%)`,
                        icon: <HardDrive
                            className={`h-4 w-4 ${status === 'ok' ? 'text-green-500' : status === 'warning' ? 'text-yellow-500' : 'text-red-500'}`}/>
                    });
                }

                // Debug模式检查
                const debugMode = securityChecks.find((c: any) => c.name === 'DEBUG模式');
                if (debugMode) {
                    checks.push({
                        name: '调试模式',
                        status: debugMode.status === 'pass' ? 'ok' : 'warning',
                        message: debugMode.value === '关闭' ? '调试模式已关闭' : '生产环境应关闭调试模式',
                        icon: <Shield
                            className={`h-4 w-4 ${debugMode.status === 'pass' ? 'text-green-500' : 'text-yellow-500'}`}/>
                    });
                }
            } else {
                // 如果健康检查失败，添加错误提示
                checks.push({
                    name: '系统健康检查',
                    status: 'error',
                    message: '无法获取健康检查数据，请检查API服务',
                    icon: <XCircle className="h-4 w-4 text-red-500"/>
                });
            }

            setHealthChecks(checks);
        } catch (error) {
            console.error('Failed to fetch health data:', error);
            // 设置错误状态
            setHealthChecks([
                {
                    name: '系统连接',
                    status: 'error',
                    message: '无法连接到系统API，请检查服务状态',
                    icon: <XCircle className="h-4 w-4 text-red-500"/>
                }
            ]);
        } finally {
            setLoading(false);
        }
    };

    const formatBytes = (bytes: number) => {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    };

    const getStatusColor = (status: string) => {
        switch (status) {
            case 'ok':
                return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200';
            case 'warning':
                return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200';
            case 'error':
                return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200';
            default:
                return 'bg-gray-100 text-gray-800';
        }
    };

    const getStatusIcon = (status: string) => {
        switch (status) {
            case 'ok':
                return <CheckCircle2 className="h-4 w-4 text-green-500"/>;
            case 'warning':
                return <AlertCircle className="h-4 w-4 text-yellow-500"/>;
            case 'error':
                return <XCircle className="h-4 w-4 text-red-500"/>;
            default:
                return null;
        }
    };

    if (loading) {
        return (
            <Card>
                <CardHeader>
                    <CardTitle>站点健康</CardTitle>
                    <CardDescription>检查中...</CardDescription>
                </CardHeader>
                <CardContent>
                    <div className="flex items-center justify-center h-32">
                        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900"></div>
                    </div>
                </CardContent>
            </Card>
        );
    }

    return (
        <Card>
            <CardHeader>
                <CardTitle>站点健康</CardTitle>
                <CardDescription>系统状态和资源配置</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
                {/* 健康检查列表 */}
                <div className="space-y-3">
                    {healthChecks.map((check, index) => (
                        <div key={index} className="flex items-center justify-between p-3 rounded-lg bg-muted/50">
                            <div className="flex items-center space-x-3">
                                {check.icon}
                                <div>
                                    <p className="text-sm font-medium">{check.name}</p>
                                    <p className="text-xs text-muted-foreground">{check.message}</p>
                                </div>
                            </div>
                            <Badge className={getStatusColor(check.status)}>
                                {getStatusIcon(check.status)}
                                <span className="ml-1 capitalize">{check.status}</span>
                            </Badge>
                        </div>
                    ))}
                </div>

                {/* 磁盘使用进度条 */}
                <div className="pt-4 border-t">
                    <div className="flex items-center justify-between mb-2">
                        <span className="text-sm font-medium">磁盘使用率</span>
                        <span className="text-sm text-muted-foreground">
                            {diskUsage.percentage.toFixed(1)}%
                        </span>
                    </div>
                    <Progress
                        value={diskUsage.percentage}
                        className={`h-2 ${
                            diskUsage.percentage > 90 ? '[&>div]:bg-red-500' :
                                diskUsage.percentage > 75 ? '[&>div]:bg-yellow-500' :
                                    '[&>div]:bg-green-500'
                        }`}
                    />
                    <p className="text-xs text-muted-foreground mt-2">
                        {formatBytes(diskUsage.used)} / {formatBytes(diskUsage.total)}
                    </p>
                </div>

                {/* 系统信息 */}
                {(systemInfo.platform || systemInfo.environment) && (
                    <div className="pt-4 border-t space-y-2">
                        {systemInfo.platform && (
                            <div className="flex justify-between text-sm">
                                <span className="text-muted-foreground">操作系统</span>
                                <span className="font-medium">{systemInfo.platform}</span>
                            </div>
                        )}
                        {systemInfo.environment && (
                            <div className="flex justify-between text-sm">
                                <span className="text-muted-foreground">运行环境</span>
                                <Badge variant="outline">{systemInfo.environment}</Badge>
                            </div>
                        )}
                    </div>
                )}
            </CardContent>
        </Card>
    );
}
