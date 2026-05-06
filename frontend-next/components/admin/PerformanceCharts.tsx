/**
 * 性能监控图表组件 - 显示Core Web Vitals和页面性能数据
 */
'use client';

import {useEffect, useState} from 'react';
import {Card, CardContent, CardDescription, CardHeader, CardTitle} from '@/components/ui/card';
import {Badge} from '@/components/ui/badge';
import {Progress} from '@/components/ui/progress';
import {Activity, AlertCircle, CheckCircle2, Clock, Layout, TrendingUp, Zap} from 'lucide-react';
import apiClient from '@/lib/api-client';

interface PerformanceMetrics {
    avg_load_time: number;
    avg_first_contentful_paint: number;
    avg_largest_contentful_paint: number;
    avg_first_input_delay: number;
    avg_cumulative_layout_shift: number;
    cwv_pass_rate: number;
    total_pages: number;
    total_samples: number;
}

interface ServerMetrics {
    cpu_usage: number;
    memory_usage: number;
    disk_usage: number;
    active_connections: number;
}

export default function PerformanceCharts() {
    const [metrics, setMetrics] = useState<PerformanceMetrics | null>(null);
    const [serverMetrics, setServerMetrics] = useState<ServerMetrics | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchPerformanceData();
    }, []);

    const fetchPerformanceData = async () => {
        try {
            setLoading(true);

            // 获取整体性能统计 - 修正API路径
            const statsRes = await apiClient.get('/performance-tracking/overall', {hours: 24}).catch(() => ({
                success: false,
                data: null
            }));
            if (statsRes.success && statsRes.data) {
                // 后端返回的是扁平结构，直接使用
                const rawData = statsRes.data;
                console.log('[PerformanceCharts] Raw performance data:', rawData);

                setMetrics({
                    avg_load_time: rawData.avg_load_time || 0,
                    avg_first_contentful_paint: (rawData.avg_first_contentful_paint || 0) * 1000, // 秒转毫秒
                    avg_largest_contentful_paint: (rawData.avg_largest_contentful_paint || 0) * 1000,
                    avg_first_input_delay: (rawData.avg_first_input_delay || 0) * 1000,
                    avg_cumulative_layout_shift: rawData.avg_cumulative_layout_shift || 0,
                    cwv_pass_rate: rawData.cwv_pass_rate || 0,
                    total_pages: rawData.total_pages || 0,
                    total_samples: rawData.total_samples || 0,
                });
                console.log('[PerformanceCharts] Processed metrics:', {
                    avg_load_time: rawData.avg_load_time,
                    avg_first_contentful_paint: rawData.avg_first_contentful_paint,
                    has_data: rawData.total_samples > 0
                });
            } else {
                console.warn('[PerformanceCharts] No performance data available');
            }

            // 获取服务器指标 - 修正API路径
            const serverRes = await apiClient.get('/performance-monitor/server-metrics').catch(() => ({
                success: false,
                data: null
            }));
            if (serverRes.success && serverRes.data) {
                console.log('[PerformanceCharts] Server metrics raw:', serverRes.data);

                // 后端返回的是嵌套结构，需要转换为前端期望的扁平结构
                const rawData = serverRes.data;
                setServerMetrics({
                    cpu_usage: rawData.cpu?.percent || 0,
                    memory_usage: rawData.memory?.percent || 0,
                    disk_usage: rawData.disk?.percent || 0,
                    active_connections: rawData.processes || 0,
                });
                console.log('[PerformanceCharts] Processed server metrics:', {
                    cpu_usage: rawData.cpu?.percent,
                    memory_usage: rawData.memory?.percent,
                    disk_usage: rawData.disk?.percent,
                });
            } else {
                console.warn('[PerformanceCharts] No server metrics available');
            }
        } catch (error) {
            console.error('Failed to fetch performance data:', error);
        } finally {
            setLoading(false);
        }
    };

    // 获取Core Web Vitals评级
    const getCWVRating = (metric: string, value: number): { rating: string; color: string } => {
        switch (metric) {
            case 'fcp':
                if (value < 1800) return {rating: 'Good', color: 'text-green-500'};
                if (value < 3000) return {rating: 'Needs Improvement', color: 'text-yellow-500'};
                return {rating: 'Poor', color: 'text-red-500'};
            case 'lcp':
                if (value < 2500) return {rating: 'Good', color: 'text-green-500'};
                if (value < 4000) return {rating: 'Needs Improvement', color: 'text-yellow-500'};
                return {rating: 'Poor', color: 'text-red-500'};
            case 'fid':
                if (value < 100) return {rating: 'Good', color: 'text-green-500'};
                if (value < 300) return {rating: 'Needs Improvement', color: 'text-yellow-500'};
                return {rating: 'Poor', color: 'text-red-500'};
            case 'cls':
                if (value < 0.1) return {rating: 'Good', color: 'text-green-500'};
                if (value < 0.25) return {rating: 'Needs Improvement', color: 'text-yellow-500'};
                return {rating: 'Poor', color: 'text-red-500'};
            default:
                return {rating: 'N/A', color: 'text-gray-500'};
        }
    };

    // 格式化时间
    const formatTime = (ms: number): string => {
        if (ms < 1000) return `${ms.toFixed(0)}ms`;
        return `${(ms / 1000).toFixed(2)}s`;
    };

    if (loading) {
        return (
            <Card>
                <CardHeader>
                    <CardTitle>性能监控</CardTitle>
                    <CardDescription>加载中...</CardDescription>
                </CardHeader>
                <CardContent>
                    <div className="flex items-center justify-center h-64">
                        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900"></div>
                    </div>
                </CardContent>
            </Card>
        );
    }

    return (
        <div className="space-y-6">
            {/* Core Web Vitals概览 */}
            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                        <Zap className="h-5 w-5"/>
                        Core Web Vitals
                    </CardTitle>
                    <CardDescription>
                        Google核心网页指标 - 过去24小时
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    {metrics ? (
                        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                            {/* FCP - First Contentful Paint */}
                            <div className="p-4 rounded-lg border space-y-2">
                                <div className="flex items-center justify-between">
                                    <span className="text-sm font-medium">FCP</span>
                                    <Badge
                                        variant={getCWVRating('fcp', metrics.avg_first_contentful_paint || 0).rating === 'Good' ? 'default' : 'secondary'}>
                                        {getCWVRating('fcp', metrics.avg_first_contentful_paint || 0).rating}
                                    </Badge>
                                </div>
                                <div
                                    className={`text-2xl font-bold ${getCWVRating('fcp', metrics.avg_first_contentful_paint || 0).color}`}>
                                    {formatTime(metrics.avg_first_contentful_paint || 0)}
                                </div>
                                <p className="text-xs text-muted-foreground">首次内容绘制</p>
                                <Progress
                                    value={Math.min(((metrics.avg_first_contentful_paint || 0) / 3000) * 100, 100)}
                                    className="h-2"
                                />
                            </div>

                            {/* LCP - Largest Contentful Paint */}
                            <div className="p-4 rounded-lg border space-y-2">
                                <div className="flex items-center justify-between">
                                    <span className="text-sm font-medium">LCP</span>
                                    <Badge
                                        variant={getCWVRating('lcp', metrics.avg_largest_contentful_paint || 0).rating === 'Good' ? 'default' : 'secondary'}>
                                        {getCWVRating('lcp', metrics.avg_largest_contentful_paint || 0).rating}
                                    </Badge>
                                </div>
                                <div
                                    className={`text-2xl font-bold ${getCWVRating('lcp', metrics.avg_largest_contentful_paint || 0).color}`}>
                                    {formatTime(metrics.avg_largest_contentful_paint || 0)}
                                </div>
                                <p className="text-xs text-muted-foreground">最大内容绘制</p>
                                <Progress
                                    value={Math.min(((metrics.avg_largest_contentful_paint || 0) / 4000) * 100, 100)}
                                    className="h-2"
                                />
                            </div>

                            {/* FID - First Input Delay */}
                            <div className="p-4 rounded-lg border space-y-2">
                                <div className="flex items-center justify-between">
                                    <span className="text-sm font-medium">FID</span>
                                    <Badge
                                        variant={getCWVRating('fid', metrics.avg_first_input_delay || 0).rating === 'Good' ? 'default' : 'secondary'}>
                                        {getCWVRating('fid', metrics.avg_first_input_delay || 0).rating}
                                    </Badge>
                                </div>
                                <div
                                    className={`text-2xl font-bold ${getCWVRating('fid', metrics.avg_first_input_delay || 0).color}`}>
                                    {formatTime(metrics.avg_first_input_delay || 0)}
                                </div>
                                <p className="text-xs text-muted-foreground">首次输入延迟</p>
                                <Progress
                                    value={Math.min(((metrics.avg_first_input_delay || 0) / 300) * 100, 100)}
                                    className="h-2"
                                />
                            </div>

                            {/* CLS - Cumulative Layout Shift */}
                            <div className="p-4 rounded-lg border space-y-2">
                                <div className="flex items-center justify-between">
                                    <span className="text-sm font-medium">CLS</span>
                                    <Badge
                                        variant={getCWVRating('cls', metrics.avg_cumulative_layout_shift || 0).rating === 'Good' ? 'default' : 'secondary'}>
                                        {getCWVRating('cls', metrics.avg_cumulative_layout_shift || 0).rating}
                                    </Badge>
                                </div>
                                <div
                                    className={`text-2xl font-bold ${getCWVRating('cls', metrics.avg_cumulative_layout_shift || 0).color}`}>
                                    {(metrics.avg_cumulative_layout_shift || 0).toFixed(3)}
                                </div>
                                <p className="text-xs text-muted-foreground">累积布局偏移</p>
                                <Progress
                                    value={Math.min(((metrics.avg_cumulative_layout_shift || 0) / 0.25) * 100, 100)}
                                    className="h-2"
                                />
                            </div>
                        </div>
                    ) : (
                        <div className="text-center py-8 text-muted-foreground">
                            <Activity className="mx-auto h-12 w-12 opacity-20 mb-2"/>
                            <p>暂无性能数据</p>
                        </div>
                    )}
                </CardContent>
            </Card>

            {/* 整体性能和服务器指标 */}
            <div className="grid gap-4 md:grid-cols-2">
                {/* 整体性能统计 */}
                <Card>
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <TrendingUp className="h-5 w-5"/>
                            整体性能
                        </CardTitle>
                        <CardDescription>网站性能概览</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        {metrics && (
                            <>
                                <div className="flex items-center justify-between p-3 rounded-lg bg-muted/50">
                                    <div className="flex items-center gap-2">
                                        <CheckCircle2 className="h-4 w-4 text-green-500"/>
                                        <span className="text-sm font-medium">CWV达标率</span>
                                    </div>
                                    <span
                                        className="text-lg font-bold">{(metrics.cwv_pass_rate || 0).toFixed(1)}%</span>
                                </div>

                                <div className="flex items-center justify-between p-3 rounded-lg bg-muted/50">
                                    <div className="flex items-center gap-2">
                                        <Clock className="h-4 w-4"/>
                                        <span className="text-sm font-medium">平均加载时间</span>
                                    </div>
                                    <span className="text-lg font-bold">{formatTime(metrics.avg_load_time || 0)}</span>
                                </div>

                                <div className="flex items-center justify-between p-3 rounded-lg bg-muted/50">
                                    <div className="flex items-center gap-2">
                                        <Layout className="h-4 w-4"/>
                                        <span className="text-sm font-medium">监控页面数</span>
                                    </div>
                                    <span className="text-lg font-bold">{metrics.total_pages || 0}</span>
                                </div>

                                <div className="flex items-center justify-between p-3 rounded-lg bg-muted/50">
                                    <div className="flex items-center gap-2">
                                        <Activity className="h-4 w-4"/>
                                        <span className="text-sm font-medium">总样本数</span>
                                    </div>
                                    <span
                                        className="text-lg font-bold">{(metrics.total_samples || 0).toLocaleString()}</span>
                                </div>
                            </>
                        )}
                    </CardContent>
                </Card>

                {/* 服务器资源监控 */}
                <Card>
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <Activity className="h-5 w-5"/>
                            服务器资源
                        </CardTitle>
                        <CardDescription>实时系统资源使用</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        {serverMetrics ? (
                            <>
                                <div className="space-y-2">
                                    <div className="flex justify-between text-sm">
                                        <span>CPU使用率</span>
                                        <span
                                            className="font-medium">{(serverMetrics.cpu_usage || 0).toFixed(1)}%</span>
                                    </div>
                                    <Progress
                                        value={serverMetrics.cpu_usage || 0}
                                        className={`h-2 ${(serverMetrics.cpu_usage || 0) > 80 ? '[&>div]:bg-red-500' : (serverMetrics.cpu_usage || 0) > 60 ? '[&>div]:bg-yellow-500' : '[&>div]:bg-green-500'}`}
                                    />
                                </div>

                                <div className="space-y-2">
                                    <div className="flex justify-between text-sm">
                                        <span>内存使用率</span>
                                        <span
                                            className="font-medium">{(serverMetrics.memory_usage || 0).toFixed(1)}%</span>
                                    </div>
                                    <Progress
                                        value={serverMetrics.memory_usage || 0}
                                        className={`h-2 ${(serverMetrics.memory_usage || 0) > 80 ? '[&>div]:bg-red-500' : (serverMetrics.memory_usage || 0) > 60 ? '[&>div]:bg-yellow-500' : '[&>div]:bg-green-500'}`}
                                    />
                                </div>

                                <div className="space-y-2">
                                    <div className="flex justify-between text-sm">
                                        <span>磁盘使用率</span>
                                        <span
                                            className="font-medium">{(serverMetrics.disk_usage || 0).toFixed(1)}%</span>
                                    </div>
                                    <Progress
                                        value={serverMetrics.disk_usage || 0}
                                        className={`h-2 ${(serverMetrics.disk_usage || 0) > 90 ? '[&>div]:bg-red-500' : (serverMetrics.disk_usage || 0) > 75 ? '[&>div]:bg-yellow-500' : '[&>div]:bg-green-500'}`}
                                    />
                                </div>

                                <div className="flex items-center justify-between p-3 rounded-lg bg-muted/50">
                                    <span className="text-sm font-medium">活跃连接数</span>
                                    <span className="text-lg font-bold">{serverMetrics.active_connections || 0}</span>
                                </div>
                            </>
                        ) : (
                            <div className="text-center py-8 text-muted-foreground">
                                <AlertCircle className="mx-auto h-12 w-12 opacity-20 mb-2"/>
                                <p>无法获取服务器指标</p>
                            </div>
                        )}
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}
