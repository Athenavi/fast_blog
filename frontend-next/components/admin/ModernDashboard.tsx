/**
 * 管理后台现代化 Dashboard 组件
 *
 * 使用 shadcn/ui 风格的卡片组件展示统计数据
 */
'use client';

import {useState, useEffect} from 'react';
import {Card, CardContent, CardDescription, CardHeader, CardTitle} from '@/components/ui/card';
import {Badge} from '@/components/ui/badge';
import {Button} from '@/components/ui/button';
import {Progress} from '@/components/ui/progress';
import {
    TrendingUp,
    TrendingDown,
    Users,
    FileText,
    Eye,
    Heart,
    MessageSquare,
    DollarSign,
    Activity,
    ArrowRight,
} from 'lucide-react';

interface StatsCard {
    title: string;
    value: string | number;
    change?: number;
    icon: React.ReactNode;
    description?: string;
}

export default function ModernDashboard() {
    const [stats, setStats] = useState<StatsCard[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchDashboardStats();
    }, []);

    const fetchDashboardStats = async () => {
        try {
            // TODO: 替换为实际的 API 调用
            // const response = await fetch('/api/v1/dashboard/stats');
            // const data = await response.json();

            // 模拟数据
            setStats([
                {
                    title: '总文章数',
                    value: 156,
                    change: 12.5,
                    icon: <FileText className="h-4 w-4"/>,
                    description: '较上月',
                },
                {
                    title: '总浏览量',
                    value: '45.2K',
                    change: 23.8,
                    icon: <Eye className="h-4 w-4"/>,
                    description: '较上月',
                },
                {
                    title: '活跃用户',
                    value: '1,234',
                    change: 8.3,
                    icon: <Users className="h-4 w-4"/>,
                    description: '较上月',
                },
                {
                    title: '评论数',
                    value: 892,
                    change: -5.2,
                    icon: <MessageSquare className="h-4 w-4"/>,
                    description: '较上月',
                },
                {
                    title: '点赞数',
                    value: '3.4K',
                    change: 15.7,
                    icon: <Heart className="h-4 w-4"/>,
                    description: '较上月',
                },
                {
                    title: '收入',
                    value: '¥12,450',
                    change: 18.9,
                    icon: <DollarSign className="h-4 w-4"/>,
                    description: '本月',
                },
            ]);
        } catch (error) {
            console.error('Failed to fetch dashboard stats:', error);
        } finally {
            setLoading(false);
        }
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
            <div className="grid gap-4 md:grid-cols-2">
                {/* 快速操作 */}
                <Card>
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

                {/* 系统状态 */}
                <Card>
                    <CardHeader>
                        <CardTitle>系统状态</CardTitle>
                        <CardDescription>
                            服务器和资源使用情况
                        </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div className="space-y-2">
                            <div className="flex items-center justify-between text-sm">
                                <span>CPU 使用率</span>
                                <span className="font-medium">45%</span>
                            </div>
                            <Progress value={45} className="h-2"/>
                        </div>
                        <div className="space-y-2">
                            <div className="flex items-center justify-between text-sm">
                                <span>内存使用率</span>
                                <span className="font-medium">68%</span>
                            </div>
                            <Progress value={68} className="h-2"/>
                        </div>
                        <div className="space-y-2">
                            <div className="flex items-center justify-between text-sm">
                                <span>存储空间</span>
                                <span className="font-medium">32%</span>
                            </div>
                            <Progress value={32} className="h-2"/>
                        </div>
                        <div className="pt-2">
                            <div className="flex items-center justify-between text-sm">
                                <span className="text-muted-foreground">运行时间</span>
                                <Badge variant="outline" className="text-green-600 border-green-600">
                                    正常运行
                                </Badge>
                            </div>
                        </div>
                    </CardContent>
                </Card>
            </div>

            {/* 热门文章列表 */}
            <Card>
                <CardHeader>
                    <CardTitle>热门文章</CardTitle>
                    <CardDescription>
                        过去 7 天浏览量最高的文章
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    <div className="space-y-4">
                        {[
                            {title: 'React 性能优化最佳实践', views: 2345, date: '2天前'},
                            {title: 'TypeScript 高级技巧', views: 1892, date: '3天前'},
                            {title: 'Next.js 14 新特性解析', views: 1567, date: '5天前'},
                            {title: 'Tailwind CSS 完全指南', views: 1234, date: '1周前'},
                        ].map((article, index) => (
                            <div
                                key={index}
                                className="flex items-center justify-between p-3 rounded-lg hover:bg-muted transition-colors"
                            >
                                <div className="flex-1">
                                    <h4 className="font-medium text-sm">{article.title}</h4>
                                    <p className="text-xs text-muted-foreground mt-1">
                                        {article.date}
                                    </p>
                                </div>
                                <div className="flex items-center text-sm text-muted-foreground">
                                    <Eye className="mr-1 h-4 w-4"/>
                                    {article.views.toLocaleString()}
                                </div>
                            </div>
                        ))}
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}
