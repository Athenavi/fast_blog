/**
 * 管理后台现代化 Dashboard 组件
 *
 * 使用 shadcn/ui 风格的卡片组件展示统计数据
 */
'use client';

import {useEffect, useState} from 'react';
import {Card, CardContent, CardDescription, CardHeader, CardTitle} from '@/components/ui/card';
import {Badge} from '@/components/ui/badge';
import {Button} from '@/components/ui/button';
import {
    Activity,
    ArrowRight,
    DollarSign,
    Eye,
    FileText,
    Heart,
    MessageSquare,
    TrendingDown,
    TrendingUp,
    Users,
} from 'lucide-react';
import ActivityStream from './ActivityStream';
import SiteHealthPanel from './SiteHealthPanel';
import TodoReminders from './TodoReminders';
import PerformanceCharts from './PerformanceCharts';
import apiClient from '@/lib/api-client';

interface DashboardStats {
    articles?: number;
    visitors?: number;
    users?: number;
    comments?: number;
    likes?: number;
    new_users?: number;
}

interface StatsCard {
    title: string;
    value: string | number;
    change?: number;
    icon: React.ReactNode;
    description?: string;
}

export default function ModernDashboard() {
    const [stats, setStats] = useState<StatsCard[]>([]);
    const [popularArticles, setPopularArticles] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchDashboardStats();
    }, []);

    const fetchDashboardStats = async () => {
        try {
            console.log('[ModernDashboard] Fetching dashboard stats...');
            const response = await apiClient.get<DashboardStats>('/dashboard/stats');
            console.log('[ModernDashboard] Dashboard stats response:', response);

            if (response.success && response.data) {
                const data = response.data;
                setStats([
                    {
                        title: '总文章数',
                        value: data.articles || 0,
                        change: 12.5,
                        icon: <FileText className="h-4 w-4"/>,
                        description: '较上月',
                    },
                    {
                        title: '总浏览量',
                        value: formatNumber(data.visitors || 0),
                        change: 23.8,
                        icon: <Eye className="h-4 w-4"/>,
                        description: '较上月',
                    },
                    {
                        title: '活跃用户',
                        value: formatNumber(data.users || 0),
                        change: 8.3,
                        icon: <Users className="h-4 w-4"/>,
                        description: '较上月',
                    },
                    {
                        title: '评论数',
                        value: data.comments || 0,
                        change: -5.2,
                        icon: <MessageSquare className="h-4 w-4"/>,
                        description: '较上月',
                    },
                    {
                        title: '点赞数',
                        value: formatNumber(data.likes || 0),
                        change: 15.7,
                        icon: <Heart className="h-4 w-4"/>,
                        description: '较上月',
                    },
                    {
                        title: '新用户',
                        value: data.new_users || 0,
                        change: 18.9,
                        icon: <DollarSign className="h-4 w-4"/>,
                        description: '本周',
                    },
                ]);
                console.log('[ModernDashboard] Stats set successfully');
            } else {
                console.error('[ModernDashboard] Failed to fetch stats:', response.error);
                // 设置默认值
                setStats([
                    {title: '总文章数', value: 0, icon: <FileText className="h-4 w-4"/>},
                    {title: '总浏览量', value: '0', icon: <Eye className="h-4 w-4"/>},
                    {title: '活跃用户', value: '0', icon: <Users className="h-4 w-4"/>},
                    {title: '评论数', value: 0, icon: <MessageSquare className="h-4 w-4"/>},
                    {title: '点赞数', value: '0', icon: <Heart className="h-4 w-4"/>},
                    {title: '新用户', value: 0, icon: <DollarSign className="h-4 w-4"/>},
                ]);
            }

            // 获取热门文章
            await fetchPopularArticles();
        } catch (error) {
            console.error('[ModernDashboard] Failed to fetch dashboard stats:', error);
            // 设置默认值
            setStats([
                {title: '总文章数', value: 0, icon: <FileText className="h-4 w-4"/>},
                {title: '总浏览量', value: '0', icon: <Eye className="h-4 w-4"/>},
                {title: '活跃用户', value: '0', icon: <Users className="h-4 w-4"/>},
                {title: '评论数', value: 0, icon: <MessageSquare className="h-4 w-4"/>},
                {title: '点赞数', value: '0', icon: <Heart className="h-4 w-4"/>},
                {title: '新用户', value: 0, icon: <DollarSign className="h-4 w-4"/>},
            ]);
        } finally {
            setLoading(false);
        }
    };

    const fetchPopularArticles = async () => {
        try {
            console.log('[ModernDashboard] Fetching popular articles...');
            // 修正API路径：analytics router已经注册在 /api/v1 前缀下
            const response = await apiClient.get<Array<{
                id?: number;
                title: string;
                slug?: string;
                view_count?: number;
                views?: number
            }>>('/popular-articles', {limit: 5, days: 7});
            console.log('[ModernDashboard] Popular articles response:', response);

            if (response.success && response.data) {
                setPopularArticles(response.data || []);
                console.log('[ModernDashboard] Popular articles set:', response.data.length, 'articles');
            } else {
                console.warn('[ModernDashboard] No popular articles found or failed to fetch');
                setPopularArticles([]);
            }
        } catch (error) {
            console.error('[ModernDashboard] Failed to fetch popular articles:', error);
            setPopularArticles([]);
        }
    };

    const formatNumber = (num: number): string => {
        if (num >= 10000) {
            return (num / 1000).toFixed(1) + 'K';
        }
        return num.toLocaleString();
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center h-64">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900"></div>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* 欢迎区域 */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">仪表板</h1>
                    <p className="text-muted-foreground">
                        欢迎回来！这是您网站的整体概况。
                    </p>
                </div>
                <Button variant="outline">
                    <Activity className="mr-2 h-4 w-4"/>
                    刷新数据
                </Button>
            </div>

            {/* 统计卡片网格 */}
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                {stats.map((stat, index) => (
                    <Card key={index} className="hover:shadow-lg transition-shadow">
                        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                            <CardTitle className="text-sm font-medium">
                                {stat.title}
                            </CardTitle>
                            <div className="text-muted-foreground">
                                {stat.icon}
                            </div>
                        </CardHeader>
                        <CardContent>
                            <div className="text-2xl font-bold">{stat.value}</div>
                            {stat.change !== undefined && (
                                <div className="flex items-center text-xs text-muted-foreground mt-1">
                                    {stat.change > 0 ? (
                                        <TrendingUp className="mr-1 h-3 w-3 text-green-500"/>
                                    ) : (
                                        <TrendingDown className="mr-1 h-3 w-3 text-red-500"/>
                                    )}
                                    <span
                                        className={
                                            stat.change > 0 ? 'text-green-500' : 'text-red-500'
                                        }
                                    >
                    {stat.change > 0 ? '+' : ''}{stat.change}%
                  </span>
                                    <span className="ml-1">{stat.description}</span>
                                </div>
                            )}
                        </CardContent>
                    </Card>
                ))}
            </div>

            {/* 快速操作和最近活动 */}
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                {/* 快速操作 */}
                <Card className="lg:col-span-1">
                    <CardHeader>
                        <CardTitle>快速操作</CardTitle>
                        <CardDescription>
                            常用的管理功能快捷入口
                        </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-2">
                        <Button className="w-full justify-between" variant="outline">
              <span className="flex items-center">
                <FileText className="mr-2 h-4 w-4"/>
                新建文章
              </span>
                            <ArrowRight className="h-4 w-4"/>
                        </Button>
                        <Button className="w-full justify-between" variant="outline">
              <span className="flex items-center">
                <Users className="mr-2 h-4 w-4"/>
                管理用户
              </span>
                            <ArrowRight className="h-4 w-4"/>
                        </Button>
                        <Button className="w-full justify-between" variant="outline">
              <span className="flex items-center">
                <MessageSquare className="mr-2 h-4 w-4"/>
                审核评论
              </span>
                            <Badge variant="secondary">12</Badge>
                        </Button>
                        <Button className="w-full justify-between" variant="outline">
              <span className="flex items-center">
                <Activity className="mr-2 h-4 w-4"/>
                查看分析
              </span>
                            <ArrowRight className="h-4 w-4"/>
                        </Button>
                    </CardContent>
                </Card>

                {/* 站点健康 */}
                <div className="lg:col-span-2">
                    <SiteHealthPanel/>
                </div>
            </div>

            {/* 活动流和待办事项 */}
            <div className="grid gap-4 md:grid-cols-2">
                {/* 活动流 */}
                <ActivityStream/>

                {/* 待办事项 */}
                <TodoReminders/>
            </div>

            {/* 性能监控图表 */}
            <PerformanceCharts/>

            {/* 热门文章列表 */}
            <Card>
                <CardHeader>
                    <CardTitle>热门文章</CardTitle>
                    <CardDescription>
                        过去 7 天浏览量最高的文章
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    {popularArticles.length > 0 ? (
                        <div className="space-y-4">
                            {popularArticles.map((article, index) => (
                                <div
                                    key={article.id || index}
                                    className="flex items-center justify-between p-3 rounded-lg hover:bg-muted transition-colors"
                                >
                                    <div className="flex-1">
                                        <h4 className="font-medium text-sm">{article.title}</h4>
                                        <p className="text-xs text-muted-foreground mt-1">
                                            {article.slug || `ID: ${article.id}`}
                                        </p>
                                    </div>
                                    <div className="flex items-center text-sm text-muted-foreground">
                                        <Eye className="mr-1 h-4 w-4"/>
                                        {(article.view_count || article.views || 0).toLocaleString()}
                                    </div>
                                </div>
                            ))}
                        </div>
                    ) : (
                        <div className="text-center py-8 text-muted-foreground">
                            <FileText className="mx-auto h-12 w-12 opacity-20 mb-2"/>
                            <p>暂无热门文章数据</p>
                        </div>
                    )}
                </CardContent>
            </Card>
        </div>
    );
}
