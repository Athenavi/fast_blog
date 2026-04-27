'use client';

import {useEffect, useState} from 'react';
import {Badge} from '@/components/ui/badge';
import {Button} from '@/components/ui/button';
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
import {AlertCircle, Clock, Eye, FileText, GitCompare, History, RotateCcw, User, X} from 'lucide-react';
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

interface ArticleRevisionsSidebarProps {
    articleId: number | null;
    isOpen: boolean;
    onClose: () => void;
    onRollbackComplete?: () => void;
}

export default function ArticleRevisionsSidebar({
                                                    articleId,
                                                    isOpen,
                                                    onClose,
                                                    onRollbackComplete
                                                }: ArticleRevisionsSidebarProps) {
    const {toast} = useToast();

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
        if (isOpen && articleId) {
            fetchRevisions();
        }
    }, [isOpen, articleId]);

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

                // 通知父组件回滚完成
                if (onRollbackComplete) {
                    onRollbackComplete();
                }

                // 关闭侧边栏
                setTimeout(() => {
                    onClose();
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
                description: '无法执行回滚',
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
            case 1:
                return '已发布';
            case 0:
                return '草稿';
            case -1:
                return '已删除';
            default:
                return '未知';
        }
    };

    if (!isOpen) return null;

    return (
        <>
            {/* 遮罩层 */}
            <div
                className="fixed inset-0 bg-black/50 backdrop-blur-sm z-40"
                onClick={onClose}
            />

            {/* 侧边栏 */}
            <div
                className="fixed right-0 top-0 h-full w-full md:w-[600px] bg-white dark:bg-gray-900 shadow-2xl z-50 transform transition-transform duration-300 ease-in-out">
                <div className="flex flex-col h-full">
                    {/* 头部 */}
                    <div
                        className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
                        <div className="flex items-center gap-3">
                            <History className="w-6 h-6 text-blue-600"/>
                            <h2 className="text-xl font-bold text-gray-900 dark:text-white">
                                修订历史
                            </h2>
                            <Badge variant="secondary">{revisions.length} 个版本</Badge>
                        </div>
                        <Button
                            variant="ghost"
                            size="sm"
                            onClick={onClose}
                            className="text-gray-500 hover:text-gray-700"
                        >
                            <X className="w-5 h-5"/>
                        </Button>
                    </div>

                    {/* 内容区域 */}
                    <ScrollArea className="flex-1 p-6">
                        {loading ? (
                            <div className="flex items-center justify-center h-64">
                                <div className="text-center">
                                    <div
                                        className="inline-block animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-blue-500 mb-2"></div>
                                    <p className="text-gray-600 dark:text-gray-400">加载中...</p>
                                </div>
                            </div>
                        ) : revisions.length === 0 ? (
                            <div className="flex flex-col items-center justify-center h-64 text-gray-500">
                                <History className="w-16 h-16 mb-4 opacity-30"/>
                                <p>暂无修订历史</p>
                            </div>
                        ) : (
                            <div className="space-y-4">
                                {/* 比较模式提示 */}
                                {compareFrom && !comparisonMode && (
                                    <div
                                        className="bg-blue-50 dark:bg-blue-950 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
                                        <div className="flex items-center justify-between">
                                            <div className="flex items-center gap-2">
                                                <GitCompare className="w-5 h-5 text-blue-600"/>
                                                <span className="text-sm font-medium text-blue-900 dark:text-blue-100">
                                                    比较模式：已选择版本 #{revisions.find(r => r.id === compareFrom)?.revision_number}
                                                </span>
                                            </div>
                                            <Button
                                                size="sm"
                                                variant="outline"
                                                onClick={() => setCompareFrom(null)}
                                            >
                                                取消
                                            </Button>
                                        </div>
                                    </div>
                                )}

                                {/* 修订列表 */}
                                {revisions.map((revision, index) => (
                                    <div
                                        key={revision.id}
                                        className={`border rounded-lg p-4 transition-all hover:shadow-md ${
                                            compareFrom === revision.id || compareTo === revision.id
                                                ? 'border-blue-500 bg-blue-50 dark:bg-blue-950'
                                                : 'hover:border-gray-300 dark:hover:border-gray-600'
                                        }`}
                                    >
                                        <div className="flex items-start justify-between mb-3">
                                            <div className="flex items-center gap-2">
                                                <Badge variant="secondary" className="text-base">
                                                    v{revision.revision_number}
                                                </Badge>
                                                <Badge
                                                    variant={revision.status === 1 ? 'default' : 'outline'}
                                                >
                                                    {getStatusText(revision.status)}
                                                </Badge>
                                            </div>
                                            <div
                                                className="text-xs text-gray-500 dark:text-gray-400 flex items-center gap-1">
                                                <Clock className="w-3 h-3"/>
                                                {formatDate(revision.created_at)}
                                            </div>
                                        </div>

                                        <h3 className="text-lg font-semibold mb-2 text-gray-900 dark:text-white line-clamp-1">
                                            {revision.title}
                                        </h3>

                                        {revision.excerpt && (
                                            <p className="text-sm text-gray-600 dark:text-gray-400 mb-3 line-clamp-2">
                                                {revision.excerpt}
                                            </p>
                                        )}

                                        {revision.change_summary && (
                                            <div
                                                className="text-xs text-gray-500 dark:text-gray-400 mb-3 flex items-start gap-1">
                                                <FileText className="w-3 h-3 mt-0.5 flex-shrink-0"/>
                                                <span>{revision.change_summary}</span>
                                            </div>
                                        )}

                                        <div
                                            className="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400 mb-3">
                                            <User className="w-3 h-3"/>
                                            <span>{revision.author?.nickname || revision.author?.username || '未知用户'}</span>
                                        </div>

                                        <Separator className="my-3"/>

                                        <div className="flex gap-2">
                                            <Button
                                                size="sm"
                                                variant="outline"
                                                onClick={() => handlePreview(revision)}
                                                className="flex-1"
                                            >
                                                <Eye className="w-4 h-4 mr-2"/>
                                                预览
                                            </Button>
                                            <Button
                                                size="sm"
                                                variant="outline"
                                                onClick={() => handleStartCompare(revision.id)}
                                                className="flex-1"
                                            >
                                                <GitCompare className="w-4 h-4 mr-2"/>
                                                比较
                                            </Button>
                                            <Button
                                                size="sm"
                                                variant="default"
                                                onClick={() => handleRollbackClick(revision)}
                                                className="flex-1 bg-blue-600 hover:bg-blue-700"
                                            >
                                                <RotateCcw className="w-4 h-4 mr-2"/>
                                                回滚
                                            </Button>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </ScrollArea>
                </div>
            </div>

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
                    <ScrollArea className="max-h-[60vh]">
                        <div className="prose prose-sm sm:prose lg:prose-lg dark:prose-invert max-w-none">
                            {selectedRevision && (
                                <div dangerouslySetInnerHTML={{__html: selectedRevision.content}}/>
                            )}
                        </div>
                    </ScrollArea>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setPreviewDialogOpen(false)}>
                            关闭
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* 回滚确认对话框 */}
            <Dialog open={rollbackDialogOpen} onOpenChange={setRollbackDialogOpen}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle className="flex items-center gap-2">
                            <AlertCircle className="w-5 h-5 text-orange-500"/>
                            确认回滚
                        </DialogTitle>
                        <DialogDescription>
                            此操作将把文章内容恢复到版本 #{revisionToRollback?.revision_number}，当前内容将被保存为新的修订版本。
                        </DialogDescription>
                    </DialogHeader>
                    <div
                        className="bg-orange-50 dark:bg-orange-950 border border-orange-200 dark:border-orange-800 rounded-lg p-4">
                        <p className="text-sm text-orange-900 dark:text-orange-100">
                            <strong>警告：</strong>此操作不可撤销，请谨慎操作！
                        </p>
                    </div>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setRollbackDialogOpen(false)}>
                            取消
                        </Button>
                        <Button
                            variant="default"
                            onClick={handleConfirmRollback}
                            className="bg-orange-600 hover:bg-orange-700"
                        >
                            确认回滚
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </>
    );
}
