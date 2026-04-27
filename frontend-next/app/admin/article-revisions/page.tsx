'use client';

import {useEffect, useState} from 'react';
import {useRouter, useSearchParams} from 'next/navigation';
import {Card, CardContent, CardDescription, CardHeader, CardTitle} from '@/components/ui/card';
import {Badge} from '@/components/ui/badge';
import {Button} from '@/components/ui/button';
import {Tabs, TabsContent, TabsList, TabsTrigger} from '@/components/ui/tabs';
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle
} from '@/components/ui/dialog';
import {ScrollArea} from '@/components/ui/scroll-area';
import {Separator} from '@/components/ui/separator';
import {
    History,
    RotateCcw,
    Eye,
    GitCompare,
    ChevronRight,
    Clock,
    User,
    FileText,
    CheckCircle2,
    AlertCircle
} from 'lucide-react';
import {useToast} from '@/hooks/use-toast';

interface Revision {
    id: number;
    article_id: number;
    revision_number: number;
    title: string;
    excerpt: string;
    content: string;
    cover_image: string;
    tags_list: string;
    category_id: number | null;
    status: number;
    hidden: boolean;
    is_featured: boolean;
    is_vip_only: boolean;
    required_vip_level: number;
    author_id: number;
    change_summary: string | null;
    created_at: string;
    author?: {
        id: number;
        username: string;
        nickname: string;
    };
}

interface ComparisonResult {
    revision1: Revision;
    revision2: Revision;
    differences: {
        field: string;
        old_value: string;
        new_value: string;
    }[];
}

export default function ArticleRevisionsPage() {
    const router = useRouter();
    const searchParams = useSearchParams();
    const {toast} = useToast();

    const articleId = searchParams.get('article_id');

    const [revisions, setRevisions] = useState<Revision[]>([]);
    const [loading, setLoading] = useState(false);
    const [selectedRevision, setSelectedRevision] = useState<Revision | null>(null);
    const [comparisonMode, setComparisonMode] = useState(false);
    const [compareFrom, setCompareFrom] = useState<number | null>(null);
    const [compareTo, setCompareTo] = useState<number | null>(null);
    const [comparisonResult, setComparisonResult] = useState<ComparisonResult | null>(null);
    const [previewDialogOpen, setPreviewDialogOpen] = useState(false);
    const [rollbackDialogOpen, setRollbackDialogOpen] = useState(false);
    const [revisionToRollback, setRevisionToRollback] = useState<Revision | null>(null);

    // 加载修订历史
    useEffect(() => {
        if (articleId) {
            fetchRevisions();
        }
    }, [articleId]);

    const fetchRevisions = async () => {
        if (!articleId) return;

        try {
            setLoading(true);
            const response = await fetch(`/api/v1/articles/${articleId}/revisions`);
            const data = await response.json();

            if (data.success) {
                setRevisions(data.data.revisions || []);
            } else {
                toast({
                    title: '加载失败',
                    description: data.error,
                    variant: 'destructive'
                });
            }
        } catch (error) {
            toast({
                title: '网络错误',
                description: '无法加载修订历史',
                variant: 'destructive'
            });
        } finally {
            setLoading(false);
        }
    };

    // 预览修订版本
    const handlePreview = (revision: Revision) => {
        setSelectedRevision(revision);
        setPreviewDialogOpen(true);
    };

    // 开始比较模式
    const handleStartCompare = (revisionId: number) => {
        if (!compareFrom) {
            setCompareFrom(revisionId);
            toast({
                title: '已选择第一个版本',
                description: '请选择要比较的第二个版本'
            });
        } else {
            setCompareTo(revisionId);
            performComparison(compareFrom, revisionId);
        }
    };

    // 执行版本比较
    const performComparison = async (rev1Id: number, rev2Id: number) => {
        try {
            const response = await fetch(
                `/api/v1/articles/revisions/compare?revision1_id=${rev1Id}&revision2_id=${rev2Id}`
            );
            const data = await response.json();

            if (data.success) {
                setComparisonResult(data.data);
                setComparisonMode(true);
            } else {
                toast({
                    title: '比较失败',
                    description: data.error,
                    variant: 'destructive'
                });
            }
        } catch (error) {
            toast({
                title: '网络错误',
                description: '无法比较版本',
                variant: 'destructive'
            });
        }
    };

    // 取消比较模式
    const handleCancelCompare = () => {
        setComparisonMode(false);
        setCompareFrom(null);
        setCompareTo(null);
        setComparisonResult(null);
    };

    // 打开回滚确认对话框
    const handleRollbackClick = (revision: Revision) => {
        setRevisionToRollback(revision);
        setRollbackDialogOpen(true);
    };

    // 执行回滚
    const handleConfirmRollback = async () => {
        if (!revisionToRollback || !articleId) return;

        try {
            const response = await fetch(
                `/api/v1/articles/${articleId}/revisions/${revisionToRollback.id}/rollback`,
                {method: 'POST'}
            );
            const data = await response.json();

            if (data.success) {
                toast({
                    title: '回滚成功',
                    description: `已回滚到版本 #${revisionToRollback.revision_number}`
                });
                setRollbackDialogOpen(false);
                setRevisionToRollback(null);
                fetchRevisions(); // 刷新列表

                // 延迟跳转到编辑页面
                setTimeout(() => {
                    router.push(`/my/posts/edit?id=${articleId}`);
                }, 1500);
            } else {
                toast({
                    title: '回滚失败',
                    description: data.error,
                    variant: 'destructive'
                });
            }
        } catch (error) {
            toast({
                title: '网络错误',
                description: '回滚操作失败',
                variant: 'destructive'
            });
        }
    };

    // 格式化日期
    const formatDate = (dateString: string) => {
        const date = new Date(dateString);
        return date.toLocaleString('zh-CN', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit'
        });
    };

    // 获取状态文本
    const getStatusText = (status: number) => {
        switch (status) {
            case 0:
                return '草稿';
            case 1:
                return '已发布';
            case -1:
                return '已删除';
            default:
                return '未知';
        }
    };

    if (!articleId) {
        return (
            <div className="container mx-auto px-4 py-8 max-w-6xl">
                <Card>
                    <CardHeader>
                        <CardTitle className="flex items-center">
                            <AlertCircle className="w-5 h-5 mr-2 text-yellow-500"/>
                            未指定文章
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        <p className="text-muted-foreground mb-4">
                            请从文章编辑页面访问修订历史
                        </p>
                        <Button onClick={() => router.push('/my/posts')}>
                            返回文章列表
                        </Button>
                    </CardContent>
                </Card>
            </div>
        );
    }

    return (
        <div className="container mx-auto px-4 py-8 max-w-7xl">
            {/* 页面头部 */}
            <div className="mb-8">
                <div className="flex items-center justify-between">
                    <div>
                        <h1 className="text-3xl font-bold flex items-center">
                            <History className="w-8 h-8 mr-3 text-blue-600"/>
                            文章修订历史
                        </h1>
                        <p className="text-muted-foreground mt-2">
                            查看、比较和恢复文章的历史版本
                        </p>
                    </div>
                    <div className="flex gap-2">
                        {comparisonMode && (
                            <Button variant="outline" onClick={handleCancelCompare}>
                                退出比较模式
                            </Button>
                        )}
                        <Button variant="outline" onClick={() => router.push(`/my/posts/edit?id=${articleId}`)}>
                            返回编辑
                        </Button>
                    </div>
                </div>
            </div>

            {/* 比较模式提示 */}
            {comparisonMode && compareFrom && !compareTo && (
                <Card className="mb-6 border-blue-200 bg-blue-50 dark:bg-blue-950">
                    <CardContent className="pt-6">
                        <div className="flex items-center">
                            <GitCompare className="w-5 h-5 mr-2 text-blue-600"/>
                            <span className="text-sm">
                                已选择版本 #{revisions.find(r => r.id === compareFrom)?.revision_number}，
                                请选择另一个版本进行比较
                            </span>
                        </div>
                    </CardContent>
                </Card>
            )}

            {/* 比较结果 */}
            {comparisonMode && comparisonResult && (
                <Card className="mb-6">
                    <CardHeader>
                        <CardTitle className="flex items-center">
                            <GitCompare className="w-5 h-5 mr-2"/>
                            版本对比结果
                        </CardTitle>
                        <CardDescription>
                            比较版本 #{comparisonResult.revision1.revision_number} 和
                            #{comparisonResult.revision2.revision_number}
                        </CardDescription>
                    </CardHeader>
                    <CardContent>
                        <ScrollArea className="h-96">
                            <div className="space-y-4">
                                {comparisonResult.differences.map((diff, index) => (
                                    <div key={index} className="border rounded-lg p-4">
                                        <h4 className="font-semibold mb-2 capitalize">{diff.field}</h4>
                                        <div className="grid grid-cols-2 gap-4">
                                            <div className="bg-red-50 dark:bg-red-950 p-3 rounded">
                                                <div className="text-xs text-red-600 mb-1">旧版本</div>
                                                <div className="text-sm break-all">{diff.old_value || '(空)'}</div>
                                            </div>
                                            <div className="bg-green-50 dark:bg-green-950 p-3 rounded">
                                                <div className="text-xs text-green-600 mb-1">新版本</div>
                                                <div className="text-sm break-all">{diff.new_value || '(空)'}</div>
                                            </div>
                                        </div>
                                    </div>
                                ))}
                                {comparisonResult.differences.length === 0 && (
                                    <div className="text-center py-8 text-muted-foreground">
                                        两个版本没有差异
                                    </div>
                                )}
                            </div>
                        </ScrollArea>
                    </CardContent>
                </Card>
            )}

            {/* 修订历史列表 */}
            <Card>
                <CardHeader>
                    <CardTitle>修订版本列表</CardTitle>
                    <CardDescription>
                        共 {revisions.length} 个版本
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    {loading ? (
                        <div className="text-center py-12">
                            <div
                                className="inline-block animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-blue-500 mb-2"/>
                            <p className="text-muted-foreground">加载中...</p>
                        </div>
                    ) : revisions.length === 0 ? (
                        <div className="text-center py-12 text-muted-foreground">
                            <History className="w-12 h-12 mx-auto mb-4 opacity-50"/>
                            <p>暂无修订记录</p>
                            <p className="text-sm mt-2">文章的每次修改都会自动保存修订版本</p>
                        </div>
                    ) : (
                        <div className="space-y-4">
                            {revisions.map((revision, index) => (
                                <div
                                    key={revision.id}
                                    className={`border rounded-lg p-4 transition-all hover:shadow-md ${
                                        compareFrom === revision.id || compareTo === revision.id
                                            ? 'border-blue-500 bg-blue-50 dark:bg-blue-950'
                                            : 'hover:border-gray-300'
                                    }`}
                                >
                                    <div className="flex items-start justify-between">
                                        <div className="flex-1">
                                            <div className="flex items-center gap-3 mb-2">
                                                <Badge variant="secondary" className="text-base">
                                                    v{revision.revision_number}
                                                </Badge>
                                                <Badge variant={revision.status === 1 ? 'default' : 'outline'}>
                                                    {getStatusText(revision.status)}
                                                </Badge>
                                                {revision.is_featured && (
                                                    <Badge variant="outline"
                                                           className="text-yellow-600 border-yellow-600">
                                                        精选
                                                    </Badge>
                                                )}
                                            </div>

                                            <h3 className="text-lg font-semibold mb-2">{revision.title}</h3>

                                            {revision.excerpt && (
                                                <p className="text-sm text-muted-foreground mb-3 line-clamp-2">
                                                    {revision.excerpt}
                                                </p>
                                            )}

                                            <div className="flex items-center gap-4 text-sm text-muted-foreground">
                                                <div className="flex items-center">
                                                    <User className="w-4 h-4 mr-1"/>
                                                    {revision.author?.nickname || revision.author?.username || '未知用户'}
                                                </div>
                                                <div className="flex items-center">
                                                    <Clock className="w-4 h-4 mr-1"/>
                                                    {formatDate(revision.created_at)}
                                                </div>
                                                {revision.change_summary && (
                                                    <div className="flex items-center">
                                                        <FileText className="w-4 h-4 mr-1"/>
                                                        {revision.change_summary}
                                                    </div>
                                                )}
                                            </div>
                                        </div>

                                        <div className="flex gap-2 ml-4">
                                            <Button
                                                size="sm"
                                                variant="outline"
                                                onClick={() => handlePreview(revision)}
                                            >
                                                <Eye className="w-4 h-4 mr-2"/>
                                                预览
                                            </Button>

                                            {!comparisonMode && (
                                                <Button
                                                    size="sm"
                                                    variant="outline"
                                                    onClick={() => handleStartCompare(revision.id)}
                                                >
                                                    <GitCompare className="w-4 h-4 mr-2"/>
                                                    比较
                                                </Button>
                                            )}

                                            <Button
                                                size="sm"
                                                variant="default"
                                                onClick={() => handleRollbackClick(revision)}
                                            >
                                                <RotateCcw className="w-4 h-4 mr-2"/>
                                                回滚到此版本
                                            </Button>
                                        </div>
                                    </div>

                                    {/* 时间线连接符（除了最后一个） */}
                                    {index < revisions.length - 1 && (
                                        <div className="flex justify-center mt-4">
                                            <ChevronRight className="w-5 h-5 text-muted-foreground rotate-90"/>
                                        </div>
                                    )}
                                </div>
                            ))}
                        </div>
                    )}
                </CardContent>
            </Card>

            {/* 预览对话框 */}
            <Dialog open={previewDialogOpen} onOpenChange={setPreviewDialogOpen}>
                <DialogContent className="max-w-4xl max-h-[80vh]">
                    <DialogHeader>
                        <DialogTitle>
                            预览版本 #{selectedRevision?.revision_number}
                        </DialogTitle>
                        <DialogDescription>
                            {selectedRevision && formatDate(selectedRevision.created_at)}
                        </DialogDescription>
                    </DialogHeader>

                    {selectedRevision && (
                        <ScrollArea className="h-[60vh]">
                            <div className="space-y-4 pr-4">
                                <div>
                                    <h2 className="text-2xl font-bold mb-2">{selectedRevision.title}</h2>
                                    {selectedRevision.excerpt && (
                                        <p className="text-muted-foreground italic">{selectedRevision.excerpt}</p>
                                    )}
                                </div>

                                <Separator/>

                                <div className="prose dark:prose-invert max-w-none">
                                    <div dangerouslySetInnerHTML={{__html: selectedRevision.content}}/>
                                </div>
                            </div>
                        </ScrollArea>
                    )}

                    <DialogFooter>
                        <Button variant="outline" onClick={() => setPreviewDialogOpen(false)}>
                            关闭
                        </Button>
                        {selectedRevision && (
                            <Button onClick={() => {
                                setPreviewDialogOpen(false);
                                handleRollbackClick(selectedRevision);
                            }}>
                                <RotateCcw className="w-4 h-4 mr-2"/>
                                回滚到此版本
                            </Button>
                        )}
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* 回滚确认对话框 */}
            <Dialog open={rollbackDialogOpen} onOpenChange={setRollbackDialogOpen}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle className="flex items-center">
                            <AlertCircle className="w-5 h-5 mr-2 text-orange-500"/>
                            确认回滚
                        </DialogTitle>
                        <DialogDescription>
                            此操作将恢复文章到指定的历史版本
                        </DialogDescription>
                    </DialogHeader>

                    {revisionToRollback && (
                        <div className="space-y-4 py-4">
                            <div
                                className="bg-orange-50 dark:bg-orange-950 border border-orange-200 dark:border-orange-800 rounded-lg p-4">
                                <div className="flex items-start">
                                    <AlertCircle className="w-5 h-5 mr-2 text-orange-600 mt-0.5"/>
                                    <div>
                                        <h4 className="font-semibold text-orange-900 dark:text-orange-100 mb-1">
                                            警告
                                        </h4>
                                        <p className="text-sm text-orange-800 dark:text-orange-200">
                                            回滚后，当前文章内容将被替换为历史版本。
                                            系统会自动创建一个新的修订版本记录此次回滚操作。
                                        </p>
                                    </div>
                                </div>
                            </div>

                            <div className="space-y-2">
                                <div className="text-sm">
                                    <span className="font-medium">目标版本：</span>
                                    <Badge>v{revisionToRollback.revision_number}</Badge>
                                </div>
                                <div className="text-sm">
                                    <span className="font-medium">标题：</span>
                                    {revisionToRollback.title}
                                </div>
                                <div className="text-sm">
                                    <span className="font-medium">创建时间：</span>
                                    {formatDate(revisionToRollback.created_at)}
                                </div>
                                {revisionToRollback.change_summary && (
                                    <div className="text-sm">
                                        <span className="font-medium">变更说明：</span>
                                        {revisionToRollback.change_summary}
                                    </div>
                                )}
                            </div>
                        </div>
                    )}

                    <DialogFooter>
                        <Button variant="outline" onClick={() => setRollbackDialogOpen(false)}>
                            取消
                        </Button>
                        <Button variant="destructive" onClick={handleConfirmRollback}>
                            <RotateCcw className="w-4 h-4 mr-2"/>
                            确认回滚
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    );
}
