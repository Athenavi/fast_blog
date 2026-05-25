import React, {useState} from 'react';
import AdminShell from '@/components/layouts/AdminShell';
import AuthGuard from '@/components/auth/AuthGuard';
import QueryProvider from '@/components/providers/QueryProvider';
import {useQuery} from '@tanstack/react-query';
import apiClient from '@/lib/api-client';
import {
    Shield, AlertTriangle, Activity, Users, Lock,
    Eye, Filter, Download, RefreshCw
} from 'lucide-react';

interface AuditLog {
    id: number;
    user_id?: number;
    action: string;
    resource_type?: string;
    resource_id?: number;
    ip_address?: string;
    user_agent?: string;
    request_data?: any;
    status: 'success' | 'failure';
    error_message?: string;
    created_at: string;
}

interface SecuritySummary {
    total_actions_24h: number;
    failed_logins_24h: number;
    suspicious_ips: string[];
    recent_critical_events: any[];
}

function SecurityDashboardInner() {
    const [selectedLog, setSelectedLog] = useState<AuditLog | null>(null);
    const [filterAction, setFilterAction] = useState<string>('all');
    const [filterStatus, setFilterStatus] = useState<string>('all');

    // 查询安全概览
    const {data: summary, isLoading: summaryLoading} = useQuery({
        queryKey: ['security-summary'],
        queryFn: async () => {
            const res = await apiClient.get('/security/dashboard/summary');
            return res.data || {};
        }
    });

    // 查询审计日志
    const {data: auditLogs, isLoading: logsLoading} = useQuery({
        queryKey: ['audit-logs', filterAction, filterStatus],
        queryFn: async () => {
            const params: any = {};
            if (filterAction !== 'all') params.action = filterAction;
            if (filterStatus !== 'all') params.status = filterStatus;
            const res = await apiClient.get('/security/audit/logs', {params});
            return res.data || [];
        }
    });

    const formatTime = (dateStr: string) => {
        return new Date(dateStr).toLocaleString('zh-CN');
    };

    const getStatusBadge = (status: string) => {
        return status === 'success' ? (
            <span className="px-2 py-1 bg-green-100 text-green-700 rounded-full text-xs font-medium">成功</span>
        ) : (
            <span className="px-2 py-1 bg-red-100 text-red-700 rounded-full text-xs font-medium">失败</span>
        );
    };

    const getActionIcon = (action: string) => {
        if (action.includes('login')) return <Lock className="w-4 h-4"/>;
        if (action.includes('create')) return <Activity className="w-4 h-4 text-green-600"/>;
        if (action.includes('delete')) return <AlertTriangle className="w-4 h-4 text-red-600"/>;
        return <Shield className="w-4 h-4"/>;
    };

    const exportLogs = () => {
        if (!auditLogs?.length) return;

        const csv = [
            ['ID', '用户ID', '动作', '资源类型', '资源ID', 'IP地址', '状态', '时间'].join(','),
            ...auditLogs.map((log: AuditLog) => [
                log.id,
                log.user_id || '',
                log.action,
                log.resource_type || '',
                log.resource_id || '',
                log.ip_address || '',
                log.status,
                log.created_at
            ].join(','))
        ].join('\n');

        const blob = new Blob([csv], {type: 'text/csv'});
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `audit-logs-${new Date().toISOString().split('T')[0]}.csv`;
        a.click();
        URL.revokeObjectURL(url);
    };

    return (
        <AdminShell title="安全监控面板">
            <div className="space-y-6">
                {/* 统计卡片 */}
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                    <div className="bg-white dark:bg-gray-900 rounded-xl border p-4">
                        <div className="flex items-center justify-between mb-2">
                            <div className="text-sm text-gray-500">24小时操作数</div>
                            <Activity className="w-5 h-5 text-blue-600"/>
                        </div>
                        <div className="text-2xl font-bold">
                            {summaryLoading ? '-' : summary?.total_actions_24h || 0}
                        </div>
                    </div>

                    <div className="bg-white dark:bg-gray-900 rounded-xl border p-4">
                        <div className="flex items-center justify-between mb-2">
                            <div className="text-sm text-gray-500">失败登录</div>
                            <Lock className="w-5 h-5 text-red-600"/>
                        </div>
                        <div className="text-2xl font-bold text-red-600">
                            {summaryLoading ? '-' : summary?.failed_logins_24h || 0}
                        </div>
                    </div>

                    <div className="bg-white dark:bg-gray-900 rounded-xl border p-4">
                        <div className="flex items-center justify-between mb-2">
                            <div className="text-sm text-gray-500">可疑 IP</div>
                            <AlertTriangle className="w-5 h-5 text-yellow-600"/>
                        </div>
                        <div className="text-2xl font-bold text-yellow-600">
                            {summaryLoading ? '-' : summary?.suspicious_ips?.length || 0}
                        </div>
                    </div>

                    <div className="bg-white dark:bg-gray-900 rounded-xl border p-4">
                        <div className="flex items-center justify-between mb-2">
                            <div className="text-sm text-gray-500">严重事件</div>
                            <Shield className="w-5 h-5 text-purple-600"/>
                        </div>
                        <div className="text-2xl font-bold text-purple-600">
                            {summaryLoading ? '-' : summary?.recent_critical_events?.length || 0}
                        </div>
                    </div>
                </div>

                {/* 可疑 IP 列表 */}
                {summary?.suspicious_ips && summary.suspicious_ips.length > 0 && (
                    <div
                        className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-xl p-4">
                        <div className="flex items-center gap-2 mb-2">
                            <AlertTriangle className="w-5 h-5 text-yellow-600"/>
                            <h3 className="font-semibold text-yellow-800 dark:text-yellow-200">可疑 IP 地址</h3>
                        </div>
                        <div className="flex flex-wrap gap-2">
                            {summary.suspicious_ips.map((ip: string, i: number) => (
                                <span key={i}
                                      className="px-3 py-1 bg-yellow-100 dark:bg-yellow-900/40 text-yellow-800 dark:text-yellow-200 rounded-full text-sm font-mono">
                  {ip}
                </span>
                            ))}
                        </div>
                    </div>
                )}

                {/* 审计日志 */}
                <div className="bg-white dark:bg-gray-900 rounded-xl border overflow-hidden">
                    <div className="px-6 py-4 border-b flex items-center justify-between flex-wrap gap-3">
                        <h3 className="font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                            <Eye className="w-5 h-5"/>
                            审计日志
                        </h3>
                        <div className="flex items-center gap-2">
                            <select
                                value={filterAction}
                                onChange={(e) => setFilterAction(e.target.value)}
                                className="px-3 py-1.5 border rounded-lg text-sm bg-white dark:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
                            >
                                <option value="all">所有动作</option>
                                <option value="login">登录</option>
                                <option value="create">创建</option>
                                <option value="update">更新</option>
                                <option value="delete">删除</option>
                            </select>
                            <select
                                value={filterStatus}
                                onChange={(e) => setFilterStatus(e.target.value)}
                                className="px-3 py-1.5 border rounded-lg text-sm bg-white dark:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
                            >
                                <option value="all">所有状态</option>
                                <option value="success">成功</option>
                                <option value="failure">失败</option>
                            </select>
                            <button
                                onClick={exportLogs}
                                className="px-3 py-1.5 border rounded-lg text-sm hover:bg-gray-50 dark:hover:bg-gray-800 transition flex items-center gap-1.5"
                            >
                                <Download className="w-4 h-4"/>
                                导出
                            </button>
                        </div>
                    </div>

                    {logsLoading ? (
                        <div className="p-12 text-center">
                            <div
                                className="animate-spin w-8 h-8 border-2 border-blue-600 border-t-transparent rounded-full mx-auto"/>
                        </div>
                    ) : !auditLogs?.length ? (
                        <div className="p-12 text-center text-gray-400">
                            <Shield className="w-16 h-16 mx-auto mb-4 opacity-30"/>
                            <p>暂无审计日志</p>
                        </div>
                    ) : (
                        <div className="overflow-x-auto">
                            <table className="w-full">
                                <thead className="bg-gray-50 dark:bg-gray-800">
                                <tr>
                                    <th className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase">动作</th>
                                    <th className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase hidden md:table-cell">资源</th>
                                    <th className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase hidden lg:table-cell">IP
                                        地址
                                    </th>
                                    <th className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase">状态</th>
                                    <th className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase hidden sm:table-cell">时间</th>
                                    <th className="px-5 py-3 text-right text-xs font-semibold text-gray-500 uppercase">操作</th>
                                </tr>
                                </thead>
                                <tbody className="divide-y">
                                {auditLogs.map((log: AuditLog) => (
                                    <tr key={log.id} className="hover:bg-gray-50 dark:hover:bg-gray-800/50 transition">
                                        <td className="px-5 py-4">
                                            <div className="flex items-center gap-2">
                                                {getActionIcon(log.action)}
                                                <span
                                                    className="text-sm font-medium text-gray-900 dark:text-white">{log.action}</span>
                                            </div>
                                        </td>
                                        <td className="px-5 py-4 text-sm text-gray-500 hidden md:table-cell">
                                            {log.resource_type && (
                                                <span>{log.resource_type} #{log.resource_id}</span>
                                            )}
                                        </td>
                                        <td className="px-5 py-4 text-sm text-gray-500 font-mono hidden lg:table-cell">
                                            {log.ip_address || '-'}
                                        </td>
                                        <td className="px-5 py-4">{getStatusBadge(log.status)}</td>
                                        <td className="px-5 py-4 text-sm text-gray-500 hidden sm:table-cell">
                                            {formatTime(log.created_at)}
                                        </td>
                                        <td className="px-5 py-4 text-right">
                                            <button
                                                onClick={() => setSelectedLog(log)}
                                                className="p-1.5 inline-block text-gray-400 hover:text-blue-600 transition"
                                            >
                                                <Eye className="w-4 h-4"/>
                                            </button>
                                        </td>
                                    </tr>
                                ))}
                                </tbody>
                            </table>
                        </div>
                    )}
                </div>
            </div>

            {/* 日志详情对话框 */}
            {selectedLog && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
                    <div
                        className="bg-white dark:bg-gray-900 rounded-2xl max-w-3xl w-full max-h-[80vh] overflow-hidden flex flex-col">
                        <div className="px-6 py-4 border-b flex items-center justify-between">
                            <h3 className="font-semibold text-lg">审计日志详情 #{selectedLog.id}</h3>
                            <button
                                onClick={() => setSelectedLog(null)}
                                className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg"
                            >
                                ✕
                            </button>
                        </div>
                        <div className="flex-1 overflow-y-auto p-6 space-y-4">
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <div className="text-sm font-medium text-gray-500 mb-1">动作</div>
                                    <div className="font-medium">{selectedLog.action}</div>
                                </div>
                                <div>
                                    <div className="text-sm font-medium text-gray-500 mb-1">状态</div>
                                    <div>{getStatusBadge(selectedLog.status)}</div>
                                </div>
                            </div>

                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <div className="text-sm font-medium text-gray-500 mb-1">用户 ID</div>
                                    <div>{selectedLog.user_id || 'N/A'}</div>
                                </div>
                                <div>
                                    <div className="text-sm font-medium text-gray-500 mb-1">IP 地址</div>
                                    <div className="font-mono">{selectedLog.ip_address || 'N/A'}</div>
                                </div>
                            </div>

                            {selectedLog.resource_type && (
                                <div>
                                    <div className="text-sm font-medium text-gray-500 mb-1">资源</div>
                                    <div>{selectedLog.resource_type} #{selectedLog.resource_id}</div>
                                </div>
                            )}

                            {selectedLog.user_agent && (
                                <div>
                                    <div className="text-sm font-medium text-gray-500 mb-1">User Agent</div>
                                    <div className="text-xs font-mono bg-gray-50 dark:bg-gray-800 p-2 rounded">
                                        {selectedLog.user_agent}
                                    </div>
                                </div>
                            )}

                            {selectedLog.request_data && (
                                <div>
                                    <div className="text-sm font-medium text-gray-500 mb-1">请求数据</div>
                                    <pre className="bg-gray-50 dark:bg-gray-800 p-3 rounded-lg text-xs overflow-x-auto">
                    {JSON.stringify(selectedLog.request_data, null, 2)}
                  </pre>
                                </div>
                            )}

                            {selectedLog.error_message && (
                                <div>
                                    <div className="text-sm font-medium text-gray-500 mb-1">错误信息</div>
                                    <div className="text-red-600 bg-red-50 dark:bg-red-900/20 p-3 rounded-lg text-sm">
                                        {selectedLog.error_message}
                                    </div>
                                </div>
                            )}

                            <div>
                                <div className="text-sm font-medium text-gray-500 mb-1">时间</div>
                                <div>{formatTime(selectedLog.created_at)}</div>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </AdminShell>
    );
}

export default function AdminSecurityDashboard() {
    return (
        <AuthGuard>
            <QueryProvider>
                <SecurityDashboardInner/>
            </QueryProvider>
        </AuthGuard>
    );
}
