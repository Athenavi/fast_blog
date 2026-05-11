'use client';

import {useEffect, useState} from 'react';
import {Card, CardContent, CardHeader, CardTitle} from '@/components/ui/card';
import {Button} from '@/components/ui/button';
import {Badge} from '@/components/ui/badge';
import {Table, TableBody, TableCell, TableHead, TableHeader, TableRow} from '@/components/ui/table';
import {Clock, Play} from 'lucide-react';
import {useToast} from '@/hooks/use-toast';

interface ScheduledArticle {
    id: number;
    title: string;
    scheduled_publish_at: string;
    status: number;
}

export default function ScheduledPublish() {
    const [articles, setArticles] = useState<ScheduledArticle[]>([]);
    const [loading, setLoading] = useState(true);
    const {toast} = useToast();

    useEffect(() => {
        fetchScheduledArticles();
    }, []);

    const fetchScheduledArticles = async () => {
        try {
            setLoading(true);
            const response = await fetch('/api/v1/scheduled-publish/pending');
            const data = await response.json();

            if (data.success) {
                setArticles(data.data.articles || []);
            }
        } catch (error) {
            toast({
                title: '网络错误',
                variant: 'destructive'
            });
        } finally {
            setLoading(false);
        }
    };

    const handleCheckAndPublish = async () => {
        try {
            const response = await fetch('/api/v1/scheduled-publish/check-and-publish', {
                method: 'POST'
            });

            const data = await response.json();

            if (data.success) {
                toast({
                    title: '检查完成',
                    description: `发布了 ${data.data.published_count} 篇文章`
                });
                fetchScheduledArticles();
            }
        } catch (error) {
            toast({
                title: '网络错误',
                variant: 'destructive'
            });
        }
    };

    const handleCancelSchedule = async (articleId: number) => {
        if (!confirm('确定要取消定时发布吗？')) return;

        try {
            const response = await fetch(`/api/v1/scheduled-publish/${articleId}/cancel`, {
                method: 'POST'
            });

            const data = await response.json();

            if (data.success) {
                toast({
                    title: '已取消',
                    description: data.data.message
                });
                fetchScheduledArticles();
            }
        } catch (error) {
            toast({
                title: '网络错误',
                variant: 'destructive'
            });
        }
    };

    return (
        <div className="space-y-6">
            <div className="flex justify-between items-center">
                <div>
                    <h1 className="text-3xl font-bold">定时发布管理</h1>
                    <p className="text-muted-foreground mt-1">
                        管理待发布的定时文章
                    </p>
                </div>

                <Button onClick={handleCheckAndPublish}>
                    <Play className="w-4 h-4 mr-2"/>
                    立即检查并发布
                </Button>
            </div>

            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center">
                        <Clock className="w-5 h-5 mr-2"/>
                        待发布文章列表
                    </CardTitle>
                </CardHeader>
                <CardContent>
                    {loading ? (
                        <div className="text-center py-8">加载中...</div>
                    ) : articles.length === 0 ? (
                        <div className="text-center py-8 text-muted-foreground">
                            暂无待发布的文章
                        </div>
                    ) : (
                        <Table>
                            <TableHeader>
                                <TableRow>
                                    <TableHead>文章标题</TableHead>
                                    <TableHead>计划发布时间</TableHead>
                                    <TableHead>状态</TableHead>
                                    <TableHead className="text-right">操作</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {articles.map((article) => (
                                    <TableRow key={article.id}>
                                        <TableCell className="font-medium">{article.title}</TableCell>
                                        <TableCell>
                                            {new Date(article.scheduled_publish_at).toLocaleString('zh-CN')}
                                        </TableCell>
                                        <TableCell>
                                            <Badge variant="secondary">待发布</Badge>
                                        </TableCell>
                                        <TableCell className="text-right">
                                            <Button
                                                size="sm"
                                                variant="outline"
                                                onClick={() => handleCancelSchedule(article.id)}
                                            >
                                                取消定时
                                            </Button>
                                        </TableCell>
                                    </TableRow>
                                ))}
                            </TableBody>
                        </Table>
                    )}
                </CardContent>
            </Card>
        </div>
    );
}
