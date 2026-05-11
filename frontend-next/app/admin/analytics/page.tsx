'use client';

import React, {useState} from 'react';
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

// 模拟数据 - 实际应该从API获取
const mockData = {
    overview: {
        totalViews: 125430,
        uniqueVisitors: 45230,
        avgDuration: 185,
        bounceRate: 32.5,
        pageViewsChange: 12.5,
        visitorsChange: 8.3,
    },
    dailyTrends: [
        {date: '2024-01-01', views: 3200, visitors: 1200},
        {date: '2024-01-02', views: 3500, visitors: 1350},
        {date: '2024-01-03', views: 4100, visitors: 1580},
        {date: '2024-01-04', views: 3800, visitors: 1420},
        {date: '2024-01-05', views: 4500, visitors: 1680},
        {date: '2024-01-06', views: 5200, visitors: 1950},
        {date: '2024-01-07', views: 4800, visitors: 1820},
    ],
    trafficSources: [
        {name: '直接访问', value: 35, color: '#3b82f6'},
        {name: '搜索引擎', value: 28, color: '#10b981'},
        {name: '社交媒体', value: 22, color: '#f59e0b'},
        {name: '外部链接', value: 15, color: '#ef4444'},
    ],
    deviceBreakdown: [
        {name: '桌面端', value: 55, color: '#8b5cf6'},
        {name: '移动端', value: 38, color: '#ec4899'},
        {name: '平板', value: 7, color: '#06b6d4'},
    ],
    topArticles: [
        {id: 1, title: '如何构建现代化博客系统', views: 15230, engagement: 85},
        {id: 2, title: 'React性能优化最佳实践', views: 12450, engagement: 78},
        {id: 3, title: 'TypeScript高级技巧', views: 10890, engagement: 82},
        {id: 4, title: 'Next.js 14新特性详解', views: 9560, engagement: 75},
        {id: 5, title: 'CSS Grid布局完全指南', views: 8340, engagement: 70},
    ],
    heatmap: {
        clicks: [
            {x: 20, y: 30, intensity: 8},
            {x: 50, y: 40, intensity: 10},
            {x: 80, y: 25, intensity: 6},
            {x: 30, y: 60, intensity: 7},
            {x: 70, y: 70, intensity: 9},
        ],
        scrollDepth: 72,
    }
};

export default function AnalyticsDashboardPage() {
    const [period, setPeriod] = useState('week');
    const [loading, setLoading] = useState(false);

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

            {/* 概览卡片 */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">总浏览量</CardTitle>
                        <Eye className="h-4 w-4 text-muted-foreground"/>
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{formatNumber(mockData.overview.totalViews)}</div>
                        <p className="text-xs text-muted-foreground">
                            <span className="text-green-600">+{mockData.overview.pageViewsChange}%</span> 较上期
                        </p>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">独立访客</CardTitle>
                        <Users className="h-4 w-4 text-muted-foreground"/>
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{formatNumber(mockData.overview.uniqueVisitors)}</div>
                        <p className="text-xs text-muted-foreground">
                            <span className="text-green-600">+{mockData.overview.visitorsChange}%</span> 较上期
                        </p>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">平均停留时间</CardTitle>
                        <Clock className="h-4 w-4 text-muted-foreground"/>
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{formatDuration(mockData.overview.avgDuration)}</div>
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
                        <div className="text-2xl font-bold">{mockData.overview.bounceRate}%</div>
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
                                    <LineChart data={mockData.dailyTrends}>
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
                                            data={mockData.trafficSources}
                                            cx="50%"
                                            cy="50%"
                                            labelLine={false}
                                            label={({name, percent}) => `${name} ${(percent * 100).toFixed(0)}%`}
                                            outerRadius={80}
                                            fill="#8884d8"
                                            dataKey="value"
                                        >
                                            {mockData.trafficSources.map((entry, index) => (
                                                <Cell key={`cell-${index}`} fill={entry.color}/>
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
                                            data={mockData.deviceBreakdown}
                                            cx="50%"
                                            cy="50%"
                                            labelLine={false}
                                            label={({name, percent}) => `${name} ${(percent * 100).toFixed(0)}%`}
                                            outerRadius={80}
                                            fill="#8884d8"
                                            dataKey="value"
                                        >
                                            {mockData.deviceBreakdown.map((entry, index) => (
                                                <Cell key={`cell-${index}`} fill={entry.color}/>
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
                                {mockData.topArticles.map((article, index) => (
                                    <div key={article.id}
                                         className="flex items-center justify-between p-4 border rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
                                        <div className="flex items-center gap-4">
                                            <Badge variant="secondary"
                                                   className="w-8 h-8 flex items-center justify-center">
                                                {index + 1}
                                            </Badge>
                                            <div>
                                                <p className="font-medium">{article.title}</p>
                                                <p className="text-sm text-muted-foreground">
                                                    参与度评分: {article.engagement}
                                                </p>
                                            </div>
                                        </div>
                                        <div className="text-right">
                                            <p className="font-semibold">{formatNumber(article.views)}</p>
                                            <p className="text-sm text-muted-foreground">浏览量</p>
                                        </div>
                                    </div>
                                ))}
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
                                    {mockData.heatmap.clicks.map((click, index) => (
                                        <div
                                            key={index}
                                            className="absolute rounded-full bg-red-500 opacity-50"
                                            style={{
                                                left: `${click.x}%`,
                                                top: `${click.y}%`,
                                                width: `${click.intensity * 10}px`,
                                                height: `${click.intensity * 10}px`,
                                                transform: 'translate(-50%, -50%)',
                                            }}
                                        />
                                    ))}
                                    <div className="absolute bottom-2 right-2 text-xs text-muted-foreground">
                                        平均滚动深度: {mockData.heatmap.scrollDepth}%
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
                                <BarChart data={mockData.trafficSources}>
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
        </div>
    );
}
