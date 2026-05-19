'use client';

/**
 * 文章审批工作流 - 审批管理页面
 */

import {useEffect, useState} from 'react';
import {Card, CardContent, CardDescription, CardHeader, CardTitle} from '@/components/ui/card';
import {Button} from '@/components/ui/button';
import {Badge} from '@/components/ui/badge';
import {Tabs, TabsContent, TabsList, TabsTrigger} from '@/components/ui/tabs';
import {Textarea} from '@/components/ui/textarea';
import {Dialog, DialogContent, DialogHeader, DialogTitle} from '@/components/ui/dialog';
import {Label} from '@/components/ui/label';
import {apiClient} from '@/lib/api-client';

interface Article {
    id: number;
    title: string;
    author: string;
    status: string;
    submitted_at: string;
    current_level: number;
    total_levels: number;
}

export default function ArticleWorkflowPage() {
    const [pendingArticles, setPendingArticles] = useState<Article[]>([]);
    const [allArticles, setAllArticles] = useState<Article[]>([]);
    const [loading, setLoading] = useState(true);
    const [selectedArticle, setSelectedArticle] = useState<Article | null>(null);
    const [reviewDialogOpen, setReviewDialogOpen] = useState(false);
    const [reviewComment, setReviewComment] = useState('');
    const [processing, setProcessing] = useState(false);

    useEffect(() => {
        loadData();
    }, []);

    const loadData = async () => {
        try {
            setLoading(true);
            const [pendingRes, allRes] = await Promise.all([
                apiClient.post('/plugins/article-workflow/action', {
                    action: 'get_pending_approvals',
                    params: {},
                }),
                apiClient.post('/plugins/article-workflow/action', {
                    action: 'get_all_articles_status',
                    params: {},
                }),
            ]);

            if (pendingRes.success) {
                setPendingArticles(pendingRes.data as Article[] || []);
            }

            if (allRes.success) {
                setAllArticles(allRes.data as Article[] || []);
            }
        } catch (error) {
            console.error('Failed to load data:', error);
        } finally {
            setLoading(false);
        }
    };

    const openReviewDialog = (article: Article) => {
        setSelectedArticle(article);
        setReviewComment('');
        setReviewDialogOpen(true);
    };

    const approveArticle = async () => {
        if (!selectedArticle) return;

        try {
            setProcessing(true);
            const response = await apiClient.post('/plugins/article-workflow/action', {
                action: 'approve_article',
                params: {
                    article_id: selectedArticle.id,
                    level: selectedArticle.current_level,
                    comment: reviewComment,
                },
            });

            if (response.success) {
                alert('审批通过');
                setReviewDialogOpen(false);
                await loadData();
            } else {
                alert('审批失败: ' + response.error);
            }
        } catch (error) {
            alert('审批失败');
        } finally {
            setProcessing(false);
        }
    };

    const rejectArticle = async () => {
        if (!selectedArticle || !reviewComment) {
            alert('请填写拒绝原因');
            return;
        }

        try {
            setProcessing(true);
            const response = await apiClient.post('/plugins/article-workflow/action', {
                action: 'reject_article',
                params: {
                    article_id: selectedArticle.id,
                    level: selectedArticle.current_level,
                    reason: reviewComment,
                },
            });

            if (response.success) {
                alert('已拒绝');
                setReviewDialogOpen(false);
                await loadData();
            } else {
                alert('操作失败: ' + response.error);
            }
        } catch (error) {
            alert('操作失败');
        } finally {
            setProcessing(false);
        }
    };

    const getStatusBadge = (status: string) => {
        const statusMap: Record<string, any> = {
            'draft': {variant: 'secondary', label: '草稿'},
            'pending_review': {variant: 'default', label: '待审核'},
            'in_review': {variant: 'default', label: '审核中'},
            'approved': {variant: 'default', label: '已通过'},
            'rejected': {variant: 'destructive', label: '已拒绝'},
            'needs_revision': {variant: 'secondary', label: '需修改'},
        };

        const config = statusMap[status] || {variant: 'secondary', label: status};
        return <Badge variant={config.variant}>{config.label}</Badge>;
    };

    if (loading) {
        return <div className="flex justify-center p-8">加载中...</div>;
    }

    return (
        <div className="container mx-auto p-6 space-y-6">
            <div>
                <h1 className="text-3xl font-bold">文章审批工作流</h1>
                <p className="text-gray-600 dark:text-gray-400 mt-2">
                    管理和审批文章发布流程
                </p>
            </div>

            {/* 统计卡片 */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <Card>
                    <CardContent className="pt-6">
                        <div className="text-2xl font-bold text-yellow-600">{pendingArticles.length}</div>
                        <p className="text-sm text-gray-600">待审批</p>
                    </CardContent>
                </Card>
                <Card>
                    <CardContent className="pt-6">
                        <div className="text-2xl font-bold text-blue-600">
                            {allArticles.filter(a => a.status === 'in_review').length}
                        </div>
                        <p className="text-sm text-gray-600">审核中</p>
                    </CardContent>
                </Card>
                <Card>
                    <CardContent className="pt-6">
                        <div className="text-2xl font-bold text-green-600">
                            {allArticles.filter(a => a.status === 'approved').length}
                        </div>
                        <p className="text-sm text-gray-600">已通过</p>
                    </CardContent>
                </Card>
                <Card>
                    <CardContent className="pt-6">
                        <div className="text-2xl font-bold text-red-600">
                            {allArticles.filter(a => a.status === 'rejected').length}
                        </div>
                        <p className="text-sm text-gray-600">已拒绝</p>
                    </CardContent>
                </Card>
            </div>

            <Tabs defaultValue="pending">
                <TabsList>
                    <TabsTrigger value="pending">待我审批 ({pendingArticles.length})</TabsTrigger>
                    <TabsTrigger value="all">所有文章</TabsTrigger>
                </TabsList>

                {/* 待审批列表 */}
                <TabsContent value="pending">
                    <Card>
                        <CardHeader>
                            <CardTitle>待审批文章</CardTitle>
                            <CardDescription>需要您审批的文章列表</CardDescription>
                        </CardHeader>
                        <CardContent>
                            {pendingArticles.length > 0 ? (
                                <div className="space-y-4">
                                    {pendingArticles.map((article) => (
                                        <div key={article.id}
                                             className="border rounded p-4 hover:bg-gray-50 dark:hover:bg-gray-800">
                                            <div className="flex justify-between items-start mb-2">
                                                <div>
                                                    <h3 className="font-semibold text-lg">{article.title}</h3>
                                                    <p className="text-sm text-gray-600">
                                                        作者: {article.author} ·
                                                        提交时间: {new Date(article.submitted_at).toLocaleString()}
                                                    </p>
                                                </div>
                                                <div className="flex items-center gap-2">
                                                    <Badge>
                                                        第 {article.current_level}/{article.total_levels} 级审批
                                                    </Badge>
                                                    {getStatusBadge(article.status)}
                                                </div>
                                            </div>

                                            <div className="flex gap-2 mt-3">
                                                <Button size="sm" onClick={() => openReviewDialog(article)}>
                                                    查看并审批
                                                </Button>
                                                <Button size="sm" variant="outline">
                                                    查看详情
                                                </Button>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            ) : (
                                <div className="text-center py-12 text-gray-600">
                                    <p className="text-lg mb-2">✓ 没有待审批的文章</p>
                                    <p className="text-sm">所有文章都已处理完毕</p>
                                </div>
                            )}
                        </CardContent>
                    </Card>
                </TabsContent>

                {/* 所有文章 */}
                <TabsContent value="all">
                    <Card>
                        <CardHeader>
                            <CardTitle>所有文章状态</CardTitle>
                            <CardDescription>查看所有文章的审批状态</CardDescription>
                        </CardHeader>
                        <CardContent>
                            <div className="overflow-x-auto">
                                <table className="w-full">
                                    <thead>
                                    <tr className="border-b">
                                        <th className="text-left p-2">标题</th>
                                        <th className="text-left p-2">作者</th>
                                        <th className="text-left p-2">状态</th>
                                        <th className="text-left p-2">审批级别</th>
                                        <th className="text-left p-2">提交时间</th>
                                        <th className="text-left p-2">操作</th>
                                    </tr>
                                    </thead>
                                    <tbody>
                                    {allArticles.map((article) => (
                                        <tr key={article.id}
                                            className="border-b hover:bg-gray-50 dark:hover:bg-gray-800">
                                            <td className="p-2 font-medium">{article.title}</td>
                                            <td className="p-2">{article.author}</td>
                                            <td className="p-2">{getStatusBadge(article.status)}</td>
                                            <td className="p-2">
                                                {article.current_level}/{article.total_levels}
                                            </td>
                                            <td className="p-2 text-sm text-gray-600">
                                                {new Date(article.submitted_at).toLocaleDateString()}
                                            </td>
                                            <td className="p-2">
                                                <Button
                                                    size="sm"
                                                    variant="outline"
                                                    onClick={() => openReviewDialog(article)}
                                                >
                                                    查看
                                                </Button>
                                            </td>
                                        </tr>
                                    ))}
                                    </tbody>
                                </table>

                                {allArticles.length === 0 && (
                                    <div className="text-center py-8 text-gray-600">
                                        暂无文章
                                    </div>
                                )}
                            </div>
                        </CardContent>
                    </Card>
                </TabsContent>
            </Tabs>

            {/* 审批对话框 */}
            <Dialog open={reviewDialogOpen} onOpenChange={setReviewDialogOpen}>
                <DialogContent className="max-w-2xl">
                    <DialogHeader>
                        <DialogTitle>审批文章</DialogTitle>
                    </DialogHeader>

                    {selectedArticle && (
                        <div className="space-y-4">
                            <div>
                                <h3 className="font-semibold text-lg mb-2">{selectedArticle.title}</h3>
                                <p className="text-sm text-gray-600">
                                    作者: {selectedArticle.author} ·
                                    当前级别: {selectedArticle.current_level}/{selectedArticle.total_levels}
                                </p>
                            </div>

                            <div>
                                <Label>审批意见</Label>
                                <Textarea
                                    value={reviewComment}
                                    onChange={(e) => setReviewComment(e.target.value)}
                                    placeholder="输入您的评论或修改建议..."
                                    rows={4}
                                />
                            </div>

                            <div className="flex gap-2 justify-end">
                                <Button variant="outline" onClick={() => setReviewDialogOpen(false)}>
                                    取消
                                </Button>
                                <Button
                                    variant="destructive"
                                    onClick={rejectArticle}
                                    disabled={processing || !reviewComment}
                                >
                                    拒绝
                                </Button>
                                <Button onClick={approveArticle} disabled={processing}>
                                    {processing ? '处理中...' : '通过'}
                                </Button>
                            </div>
                        </div>
                    )}
                </DialogContent>
            </Dialog>
        </div>
    );
}
