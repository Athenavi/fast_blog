'use client';

import React, {useEffect, useState} from 'react';
import {Card, CardContent, CardDescription, CardHeader, CardTitle} from '@/components/ui/card';
import {Tabs, TabsContent, TabsList, TabsTrigger} from '@/components/ui/tabs';
import {Badge} from '@/components/ui/badge';
import {Select, SelectContent, SelectItem, SelectTrigger, SelectValue} from '@/components/ui/select';
import {
    Bar,
    BarChart,
    CartesianGrid,
    Cell,
    Legend,
    Line,
    LineChart,
    Pie,
    PieChart,
    ResponsiveContainer,
    Tooltip,
    XAxis,
    YAxis
} from 'recharts';
import {Clock, Eye, Globe, MousePointer, Smartphone, TrendingUp, Users} from 'lucide-react';
import {
    AnalyticsService,
    DailyTrend,
    DeviceStat,
    OverviewStats,
    PopularArticle,
    TrafficSource
} from '@/lib/api/analytics-service';

export default function AnalyticsDashboardPage() {
    const [period, setPeriod] = useState('week');
    const [loading, setLoading] = useState(false);

    // 数据状态
    const [overviewStats, setOverviewStats] = useState<OverviewStats | null>(null);
    const [dailyTrends, setDailyTrends] = useState<DailyTrend[]>([]);
    const [trafficSources, setTrafficSources] = useState<TrafficSource[]>([]);
    const [deviceStats, setDeviceStats] = useState<DeviceStat[]>([]);
    const [popularArticles, setPopularArticles] = useState<PopularArticle[]>([]);

    // 加载数据
    useEffect(() => {
        loadData();
    }, [period]);

    const loadData = async () => {
        setLoading(true);
        try {
            const daysMap: Record<string, number> = {
                'day': 1,
                'week': 7,
                'month': 30,
                'year': 365
            };
            const days = daysMap[period] || 7;

            // 并行加载所有数据
            const [overviewRes, trendsRes, sourcesRes, devicesRes, articlesRes] = await Promise.all([
                AnalyticsService.getOverviewStats(days),
                AnalyticsService.getArticleViewsTrend(days),
                AnalyticsService.getTrafficSources(days),
                AnalyticsService.getDeviceStats(days),
                AnalyticsService.getPopularArticles(10, days)
            ]);

            if (overviewRes.success && overviewRes.data) setOverviewStats(overviewRes.data);
            if (trendsRes.success) setDailyTrends(trendsRes.data || []);
            if (sourcesRes.success) setTrafficSources(sourcesRes.data || []);
            if (devicesRes.success) setDeviceStats(devicesRes.data || []);
            if (articlesRes.success) setPopularArticles(articlesRes.data || []);
        } catch (error) {
            console.error('Failed to load analytics data:', error);
        } finally {
            setLoading(false);
        }
    };

    const formatNumber = (num: number) => {
        return num.toLocaleString('zh-CN');
    };

    const formatDuration = (seconds: number) => {
        const mins = Math.floor(seconds / 60);
        const secs = seconds % 60;
        return `${mins}分${secs}秒`;
    };

    return (
        <div className="container mx-auto py-8 px-4">
            <div className="flex justify-between items-center mb-8">
                <div>
                    <h1 className="text-3xl font-bold">数据分析仪表板</h1>
                    <p className="text-muted-foreground mt-1">
                        实时监控网站表现和用户行为
                    </p>
                </div>
                <Select value={period} onValueChange={setPeriod}>
                    <SelectTrigger className="w-32">
                        <SelectValue/>
                    </SelectTrigger>
                    <SelectContent>
                        <SelectItem value="day">今天</SelectItem>
                        <SelectItem value="week">本周</SelectItem>
                        <SelectItem value="month">本月</SelectItem>
                        <SelectItem value="year">今年</SelectItem>
                    </SelectContent>
                </Select>
            </div>

            {/* 加载状态 */}
            {loading && (
                <div className="flex justify-center items-center py-12">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
                </div>
            )}

            {!loading && overviewStats && (
                <>
            {/* 概览卡片 */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">总浏览量</CardTitle>
                        <Eye className="h-4 w-4 text-muted-foreground"/>
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{formatNumber(overviewStats.total_views)}</div>
                        <p className="text-xs text-muted-foreground">
                            {overviewStats.page_views_change && (
                                <span className="text-green-600">+{overviewStats.page_views_change}%</span>
                            )}
                            {' '}较上期
                        </p>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">独立访客</CardTitle>
                        <Users className="h-4 w-4 text-muted-foreground"/>
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{formatNumber(overviewStats.unique_visitors)}</div>
                        <p className="text-xs text-muted-foreground">
                            {overviewStats.visitors_change && (
                                <span className="text-green-600">+{overviewStats.visitors_change}%</span>
                            )}
                            {' '}较上期
                        </p>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">平均停留时间</CardTitle>
                        <Clock className="h-4 w-4 text-muted-foreground"/>
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{formatDuration(overviewStats.avg_duration)}</div>
                        <p className="text-xs text-muted-foreground">
                            每用户平均浏览时长
                        </p>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">跳出率</CardTitle>
                        <TrendingUp className="h-4 w-4 text-muted-foreground"/>
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{overviewStats.bounce_rate}%</div>
                        <p className="text-xs text-muted-foreground">
                            单页访问占比
                        </p>
                    </CardContent>
                </Card>
            </div>

            <Tabs defaultValue="overview" className="space-y-6">
                <TabsList className="grid w-full max-w-2xl grid-cols-4">
                    <TabsTrigger value="overview">总览</TabsTrigger>
                    <TabsTrigger value="content">内容分析</TabsTrigger>
                    <TabsTrigger value="behavior">用户行为</TabsTrigger>
                    <TabsTrigger value="sources">流量来源</TabsTrigger>
                </TabsList>

                {/* 总览 */}
                <TabsContent value="overview" className="space-y-6">
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                        {/* 趋势图 */}
                        <Card className="lg:col-span-2">
                            <CardHeader>
                                <CardTitle>访问趋势</CardTitle>
                                <CardDescription>最近7天的浏览量和独立访客</CardDescription>
                            </CardHeader>
                            <CardContent>
                                <ResponsiveContainer width="100%" height={300}>
                                    <LineChart data={dailyTrends}>
                                        <CartesianGrid strokeDasharray="3 3"/>
                                        <XAxis dataKey="date"/>
                                        <YAxis/>
                                        <Tooltip/>
                                        <Legend/>
                                        <Line type="monotone" dataKey="views" stroke="#3b82f6" name="浏览量"/>
                                        <Line type="monotone" dataKey="visitors" stroke="#10b981" name="独立访客"/>
                                    </LineChart>
                                </ResponsiveContainer>
                            </CardContent>
                        </Card>

                        {/* 流量来源 */}
                        <Card>
                            <CardHeader>
                                <CardTitle className="flex items-center gap-2">
                                    <Globe className="h-5 w-5"/>
                                    流量来源分布
                                </CardTitle>
                            </CardHeader>
                            <CardContent>
                                <ResponsiveContainer width="100%" height={250}>
                                    <PieChart>
                                        <Pie
                                            data={trafficSources}
                                            cx="50%"
                                            cy="50%"
                                            labelLine={false}
                                            label={({name, percent}: {
                                                name: string;
                                                percent: number
                                            }) => `${name} ${(percent * 100).toFixed(0)}%`}
                                            outerRadius={80}
                                            fill="#8884d8"
                                            dataKey="value"
                                        >
                                            {trafficSources.map((entry, index) => (
                                                <Cell key={`cell-${index}`} fill={entry.color || '#3b82f6'}/>
                                            ))}
                                        </Pie>
                                        <Tooltip/>
                                    </PieChart>
                                </ResponsiveContainer>
                            </CardContent>
                        </Card>

                        {/* 设备分布 */}
                        <Card>
                            <CardHeader>
                                <CardTitle className="flex items-center gap-2">
                                    <Smartphone className="h-5 w-5"/>
                                    设备类型分布
                                </CardTitle>
                            </CardHeader>
                            <CardContent>
                                <ResponsiveContainer width="100%" height={250}>
                                    <PieChart>
                                        <Pie
                                            data={deviceStats}
                                            cx="50%"
                                            cy="50%"
                                            labelLine={false}
                                            label={({name, percent}: {
                                                name: string;
                                                percent: number
                                            }) => `${name} ${(percent * 100).toFixed(0)}%`}
                                            outerRadius={80}
                                            fill="#8884d8"
                                            dataKey="value"
                                        >
                                            {deviceStats.map((entry, index) => (
                                                <Cell key={`cell-${index}`} fill={entry.color || '#8b5cf6'}/>
                                            ))}
                                        </Pie>
                                        <Tooltip/>
                                    </PieChart>
                                </ResponsiveContainer>
                            </CardContent>
                        </Card>
                    </div>
                </TabsContent>

                {/* 内容分析 */}
                <TabsContent value="content" className="space-y-6">
                    <Card>
                        <CardHeader>
                            <CardTitle>热门文章排行</CardTitle>
                            <CardDescription>按浏览量和参与度排序</CardDescription>
                        </CardHeader>
                        <CardContent>
                            <div className="space-y-4">
                                {popularArticles.length > 0 ? (
                                    popularArticles.map((article, index) => (
                                        <div key={article.id}
                                             className="flex items-center justify-between p-4 border rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
                                            <div className="flex items-center gap-4">
                                                <Badge variant="secondary"
                                                       className="w-8 h-8 flex items-center justify-center">
                                                    {index + 1}
                                                </Badge>
                                                <div>
                                                    <p className="font-medium">{article.title}</p>
                                                    {article.engagement && (
                                                        <p className="text-sm text-muted-foreground">
                                                            参与度评分: {article.engagement}
                                                        </p>
                                                    )}
                                                </div>
                                            </div>
                                            <div className="text-right">
                                                <p className="font-semibold">{formatNumber(article.views)}</p>
                                                <p className="text-sm text-muted-foreground">浏览量</p>
                                            </div>
                                        </div>
                                    ))
                                ) : (
                                    <p className="text-center text-muted-foreground py-8">暂无数据</p>
                                )}
                            </div>
                        </CardContent>
                    </Card>
                </TabsContent>

                {/* 用户行为 */}
                <TabsContent value="behavior" className="space-y-6">
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                        <Card>
                            <CardHeader>
                                <CardTitle className="flex items-center gap-2">
                                    <MousePointer className="h-5 w-5"/>
                                    点击热力图
                                </CardTitle>
                                <CardDescription>页面点击分布情况</CardDescription>
                            </CardHeader>
                            <CardContent>
                                <div className="relative h-64 bg-gray-100 dark:bg-gray-800 rounded-lg overflow-hidden">
                                    {/* TODO: 实现真实的热力图数据 */}
                                    <div className="flex items-center justify-center h-full text-muted-foreground">
                                        点击热力图功能开发中
                                    </div>
                                    <div className="absolute bottom-2 right-2 text-xs text-muted-foreground">
                                        平均滚动深度: 待实现
                                    </div>
                                </div>
                            </CardContent>
                        </Card>

                        <Card>
                            <CardHeader>
                                <CardTitle>用户行为指标</CardTitle>
                                <CardDescription>关键行为数据统计</CardDescription>
                            </CardHeader>
                            <CardContent className="space-y-4">
                                <div
                                    className="flex justify-between items-center p-3 bg-gray-50 dark:bg-gray-800 rounded">
                                    <span className="text-sm">平均每次会话页数</span>
                                    <span className="font-semibold">3.2</span>
                                </div>
                                <div
                                    className="flex justify-between items-center p-3 bg-gray-50 dark:bg-gray-800 rounded">
                                    <span className="text-sm">分享率</span>
                                    <span className="font-semibold">2.8%</span>
                                </div>
                                <div
                                    className="flex justify-between items-center p-3 bg-gray-50 dark:bg-gray-800 rounded">
                                    <span className="text-sm">评论率</span>
                                    <span className="font-semibold">1.5%</span>
                                </div>
                                <div
                                    className="flex justify-between items-center p-3 bg-gray-50 dark:bg-gray-800 rounded">
                                    <span className="text-sm">收藏率</span>
                                    <span className="font-semibold">3.2%</span>
                                </div>
                            </CardContent>
                        </Card>
                    </div>
                </TabsContent>

                {/* 流量来源 */}
                <TabsContent value="sources" className="space-y-6">
                    <Card>
                        <CardHeader>
                            <CardTitle>详细流量来源分析</CardTitle>
                            <CardDescription>各渠道的表现对比</CardDescription>
                        </CardHeader>
                        <CardContent>
                            <ResponsiveContainer width="100%" height={300}>
                                <BarChart data={trafficSources}>
                                    <CartesianGrid strokeDasharray="3 3"/>
                                    <XAxis dataKey="name"/>
                                    <YAxis/>
                                    <Tooltip/>
                                    <Legend/>
                                    <Bar dataKey="value" fill="#3b82f6" name="占比%"/>
                                </BarChart>
                            </ResponsiveContainer>
                        </CardContent>
                    </Card>
                </TabsContent>
            </Tabs>
                </>
            )}
        </div>
    );
}
