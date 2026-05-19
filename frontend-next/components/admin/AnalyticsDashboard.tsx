'use client';

import {useEffect, useState} from 'react';
import {Card, CardContent, CardHeader, CardTitle} from '@/components/ui/card';
// @ts-ignore - Charts components are placeholders for now
import {LineChart} from '@/components/charts';

interface OverviewStats {
    total_articles: number;
    new_articles: number;
    total_comments: number;
    new_comments: number;
    total_users: number;
    new_users: number;
}

interface TrendData {
    date: string;
    views: number;
}

interface PopularArticle {
    id: number;
    title: string;
    slug: string;
    view_count: number;
}

export default function AnalyticsDashboard() {
    const [overview, setOverview] = useState<OverviewStats | null>(null);
    const [trend, setTrend] = useState<TrendData[]>([]);
    const [popularArticles, setPopularArticles] = useState<PopularArticle[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchAnalyticsData();
    }, []);

    const fetchAnalyticsData = async () => {
        try {
            // 获取概览数据
            const overviewRes = await fetch('/api/v2/analytics/overview?days=30');
            const overviewData = await overviewRes.json();
            if (overviewData.success) {
                setOverview(overviewData.data);
            }

            // 获取趋势数据
            const trendRes = await fetch('/api/v2/analytics/article-views-trend?days=30');
            const trendData = await trendRes.json();
            if (trendData.success) {
                setTrend(trendData.data);
            }

            // 获取热门文章
            const popularRes = await fetch('/api/v2/analytics/popular-articles?limit=5&days=7');
            const popularData = await popularRes.json();
            if (popularData.success) {
                setPopularArticles(popularData.data);
            }
        } catch (error) {
            console.error('Failed to fetch analytics data:', error);
        } finally {
            setLoading(false);
        }
    };

    if (loading) {
        return <div className="p-8 text-center">加载'..</div>;
    }

    return (
        <div className="space-y-6 p-6">
            <div>
                <h1 className="text-3xl font-bold tracking-tight">数据分析</h1>
                <p className="text-muted-foreground">网站性能和用户行为分</p>
            </div>

            {/* 概览统计卡片 */}
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">总文章数</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{overview?.total_articles || 0}</div>
                        <p className="text-xs text-muted-foreground">
                            +{overview?.new_articles || 0} '0' </p>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">总评论数</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{overview?.total_comments || 0}</div>
                        <p className="text-xs text-muted-foreground">
                            +{overview?.new_comments || 0} '0' </p>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">总用户数</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{overview?.total_users || 0}</div>
                        <p className="text-xs text-muted-foreground">
                            +{overview?.new_users || 0} '0' </p>
                    </CardContent>
                </Card>
            </div>

            {/* 浏览量趋势图 */}
            <Card>
                <CardHeader>
                    <CardTitle>浏览量趋势（30天）</CardTitle>
                </CardHeader>
                <CardContent>
                    <LineChart
                        data={trend.map(item => ({
                            label: item.date,
                            value: item.views,
                        }))}
                        title="每日浏览"
                    />
                </CardContent>
            </Card>

            {/* 热门文章列表 */}
            <Card>
                <CardHeader>
                    <CardTitle>热门文章天</CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="space-y-4">
                        {popularArticles.map((article, index) => (
                            <div key={article.id} className="flex items-center justify-between">
                                <div className="flex items-center space-x-4">
                  <span className="text-lg font-bold text-muted-foreground">
                    #{index + 1}
                  </span>
                                    <div>
                                        <p className="font-medium">{article.title}</p>
                                        <p className="text-sm text-muted-foreground">/{article.slug}</p>
                                    </div>
                                </div>
                                <div className="text-right">
                                    <p className="font-bold">{article.view_count}</p>
                                    <p className=" text-xs text-muted-foreground">次浏</p>
                                </div>
                            </div>
                        ))}
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}
