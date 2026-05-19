/**
 * 活动流组件 - 显示最近的活动记录
 */
'use client';

import {useEffect, useState} from 'react';
import {Card, CardContent, CardDescription, CardHeader, CardTitle} from '@/components/ui/card';
import {Badge} from '@/components/ui/badge';
import {ScrollArea} from '@/components/ui/scroll-area';
import {Bell, Clock, FileText, MessageSquare} from 'lucide-react';
import apiClient from '@/lib/api-client';

interface ActivityItem {
    id: string;
    type: 'article' | 'comment' | 'user' | 'notification';
    title: string;
    description: string;
    timestamp: string;
    icon: React.ReactNode;
    badge?: string;
}

export default function ActivityStream() {
    const [activities, setActivities] = useState<ActivityItem[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchActivities();
    }, []);

    const fetchActivities = async () => {
        try {
            setLoading(true);

            // 并行获取各种活动数据
            const [articlesRes, commentsRes, notificationsRes] = await Promise.all([
                apiClient.get('/dashboard/recent-articles'),
                apiClient.get('/comments/admin/pending', {page: 1, per_page: 5}).catch(() => ({
                    success: false,
                    data: null
                })),
                apiClient.get('/notifications', {limit: 5}).catch(() => ({success: false, data: null}))
            ]);

            const activityList: ActivityItem[] = [];

            // 处理最近文章
            if (articlesRes.success && articlesRes.data) {
                articlesRes.data.forEach((article: any) => {
                    activityList.push({
                        id: `article-${article.id}`,
                        type: 'article',
                        title: article.title,
                        description: `浏览量: ${article.views || 0}`,
                        timestamp: article.created_at,
                        icon: <FileText className="h-4 w-4 text-blue-500"/>,
                        badge: article.status === 'published' ? '已发布' : '草稿'
                    });
                });
            }

            // 处理待审核评论
            if (commentsRes.success && (commentsRes.data as any)?.comments) {
                (commentsRes.data as any).comments.forEach((comment: any) => {
                    activityList.push({
                        id: `comment-${comment.id}`,
                        type: 'comment',
                        title: comment.content?.substring(0, 50) + '...' || '新评论',
                        description: `文章ID: ${comment.article_id}`,
                        timestamp: comment.created_at,
                        icon: <MessageSquare className="h-4 w-4 text-yellow-500"/>,
                        badge: '待审核'
                    });
                });
            }

            // 处理通知
            if (notificationsRes.success && (notificationsRes.data as any)?.notifications) {
                (notificationsRes.data as any).notifications.forEach((notif: any) => {
                    activityList.push({
                        id: `notification-${notif.id}`,
                        type: 'notification',
                        title: notif.title || '系统通知',
                        description: notif.message || '',
                        timestamp: notif.created_at,
                        icon: <Bell className="h-4 w-4 text-purple-500"/>,
                        badge: notif.type
                    });
                });
            }

            // 按时间排序
            activityList.sort((a, b) =>
                new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
            );

            setActivities(activityList.slice(0, 10)); // 只显示最近10条
        } catch (error) {
            console.error('Failed to fetch activities:', error);
        } finally {
            setLoading(false);
        }
    };

    const formatTimeAgo = (timestamp: string) => {
        const now = new Date();
        const date = new Date(timestamp);
        const diffMs = now.getTime() - date.getTime();
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMs / 3600000);
        const diffDays = Math.floor(diffMs / 86400000);

        if (diffMins < 1) return '刚刚';
        if (diffMins < 60) return `${diffMins}分钟前`;
        if (diffHours < 24) return `${diffHours}小时前`;
        if (diffDays < 7) return `${diffDays}天前`;
        return date.toLocaleDateString('zh-CN');
    };

    if (loading) {
        return (
            <Card>
                <CardHeader>
                    <CardTitle>最近活动</CardTitle>
                    <CardDescription>加载活动记录...</CardDescription>
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
                <CardTitle>最近活动</CardTitle>
                <CardDescription>文章、评论和系统通知</CardDescription>
            </CardHeader>
            <CardContent>
                <ScrollArea className="h-[400px] pr-4">
                    <div className="space-y-4">
                        {activities.length === 0 ? (
                            <div className="text-center text-muted-foreground py-8">
                                <Clock className="h-12 w-12 mx-auto mb-2 opacity-50"/>
                                <p>暂无活动记录</p>
                            </div>
                        ) : (
                            activities.map((activity) => (
                                <div
                                    key={activity.id}
                                    className="flex items-start space-x-3 p-3 rounded-lg hover:bg-muted transition-colors"
                                >
                                    <div className="flex-shrink-0 mt-1">
                                        {activity.icon}
                                    </div>
                                    <div className="flex-1 min-w-0">
                                        <div className="flex items-center justify-between">
                                            <p className="text-sm font-medium truncate">
                                                {activity.title}
                                            </p>
                                            {activity.badge && (
                                                <Badge variant="secondary" className="ml-2 flex-shrink-0">
                                                    {activity.badge}
                                                </Badge>
                                            )}
                                        </div>
                                        <p className="text-xs text-muted-foreground mt-1">
                                            {activity.description}
                                        </p>
                                        <p className="text-xs text-muted-foreground mt-1">
                                            {formatTimeAgo(activity.timestamp)}
                                        </p>
                                    </div>
                                </div>
                            ))
                        )}
                    </div>
                </ScrollArea>
            </CardContent>
        </Card>
    );
}
