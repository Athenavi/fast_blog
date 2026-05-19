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
import {
    AlertCircle,
    ChevronDown,
    Clock,
    Eye,
    FileText,
    GitCompare,
    History,
    RotateCcw,
    Save,
    Trash2,
    Upload,
    User,
    X
} from 'lucide-react';
import {useToast} from '@/hooks/use-toast';
import {apiClient} from '@/lib/api/base-client';
import type {LocalDraft} from '@/lib/draft-service';
import {draftService} from '@/lib/draft-service';
import {computeDiff, exportDiffAsMarkdown, exportDiffAsText, formatDiffAsHtml, getDiffSummary} from '@/lib/diff-utils';

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
        title_changed: boolean;
        excerpt_changed: boolean;
        content_changed: boolean;
        cover_image_changed: boolean;
        tags_changed: boolean;
        category_changed: boolean;
        status_changed: boolean;
    };
}

// 差异对比组件
interface DiffSectionProps {
    label: string;
    oldValue: string;
    newValue: string;
    isImage?: boolean;
}

const DiffSection: React.FC<DiffSectionProps> = ({label, oldValue, newValue, isImage = false}) => {
    return (
        <div className="border rounded-lg overflow-hidden">
            <div className="bg-gray-100 dark:bg-gray-800 px-4 py-2 border-b">
                <h4 className="font-semibold text-gray-900 dark:text-white">{label}</h4>
            </div>
            <div className="grid grid-cols-2 divide-x">
                <div className="p-4 bg-red-50 dark:bg-red-950/20">
                    <div className="text-xs font-semibold text-red-700 dark:text-red-400 mb-2">旧版本</div>
                    {isImage ? (
                        oldValue !== '无' ? (
                            <img src={oldValue} alt="旧版本" className="max-w-full h-auto rounded"/>
                        ) : (
                            <p className="text-gray-400 text-sm">无</p>
                        )
                    ) : (
                        <p className="text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap">{oldValue || '无'}</p>
                    )}
                </div>
                <div className="p-4 bg-green-50 dark:bg-green-950/20">
                    <div className="text-xs font-semibold text-green-700 dark:text-green-400 mb-2">新版本</div>
                    {isImage ? (
                        newValue !== '无' ? (
                            <img src={newValue} alt="新版本" className="max-w-full h-auto rounded"/>
                        ) : (
                            <p className="text-gray-400 text-sm">无</p>
                        )
                    ) : (
                        <p className="text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap">{newValue || '无'}</p>
                    )}
                </div>
            </div>
        </div>
    );
};

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
    const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
    const [revisionToDelete, setRevisionToDelete] = useState<Revision | null>(null);

    // 比较菜单状态
    const [compareMenuOpen, setCompareMenuOpen] = useState<number | null>(null);

    // 本地草稿状态
    const [localDraft, setLocalDraft] = useState<LocalDraft | null>(null);

    // Diff视图状态
    const [showDiffView, setShowDiffView] = useState(false);

    // 加载修订历史
    useEffect(() => {
        if (isOpen && articleId) {
            fetchRevisions();
            checkLocalDraft();
        }
    }, [isOpen, articleId]);

    // 检查本地草稿
    const checkLocalDraft = async () => {
        if (!articleId) return;
        const draft = draftService.getDraft(articleId);
        setLocalDraft(draft);
    };

    const fetchRevisions = async () => {
        if (!articleId) return;

        try {
            setLoading(true);
            const result = await apiClient.get(`/articles/${articleId}/revisions`);

            if (result.success) {
                const revisionsData = result.data as { revisions?: Revision[] };
                setRevisions(revisionsData?.revisions || []);
            } else {
                toast({
                    title: '加载失败',
                    description: result.error,
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

    // 与当前编辑器内容比较
    const handleCompareWithEditor = async (revision: Revision) => {
        console.log('开始与编辑器比较...', revision.id);
        try {
            // 请求获取当前编辑器内容
            const editorContent = await new Promise<string>((resolve) => {
                const event = new CustomEvent('getEditorContent', {
                    detail: {
                        callback: (content: string) => {
                            console.log('收到编辑器内容，长度:', content?.length);
                            resolve(content);
                        }
                    }
                });
                window.dispatchEvent(event);
                console.log('已发送getEditorContent事件');

                // 超时处理
                setTimeout(() => {
                    console.log('获取编辑器内容超时');
                    resolve('');
                }, 1000);
            });

            if (!editorContent) {
                toast({
                    title: '无法获取编辑器内容',
                    description: '请确保编辑器已加载',
                    variant: 'destructive'
                });
                return;
            }

            console.log('设置比较结果...');

            // 创建虚拟修订对象用于比较
            const virtualRevision: Revision = {
                ...revision,
                id: -1,
                revision_number: 0,
                content: editorContent,
                created_at: new Date().toISOString()
            };

            // 直接设置比较结果
            setComparisonResult({
                revision1: revision,
                revision2: virtualRevision,
                differences: {
                    title_changed: false,
                    excerpt_changed: false,
                    content_changed: revision.content !== editorContent,
                    cover_image_changed: false,
                    tags_changed: false,
                    category_changed: false,
                    status_changed: false
                }
            });
            setComparisonMode(true);
            setCompareMenuOpen(null);
            console.log('比较模式已开启');

        } catch (error) {
            console.error('比较失败:', error);
            toast({
                title: '比较失败',
                description: '无法获取编辑器内容',
                variant: 'destructive'
            });
        }
    };

    // 与指定版本比较
    const handleCompareWithVersion = (revisionId: number) => {
        console.log('🔵 与指定版本比较:', revisionId, '当前compareFrom:', compareFrom);

        if (!compareFrom) {
            // 第一次选择，设置为第一个版本
            setCompareFrom(revisionId);
            setCompareMenuOpen(null);
            toast({
                title: '✅ 已选择第一个版本',
                description: `版本 #${revisions.find(r => r.id === revisionId)?.revision_number}，请选择第二个版本`,
                duration: 3000
            });
        } else if (compareFrom === revisionId) {
            // 选择了同一个版本，取消选择
            setCompareFrom(null);
            setCompareTo(null);
            setCompareMenuOpen(null);
            toast({
                title: '已取消选择',
                description: '请重新选择要比较的版本'
            });
        } else {
            // 第二次选择，设置第二个版本并自动开始比较
            setCompareTo(revisionId);
            setCompareMenuOpen(null);
            toast({
                title: '✅ 已选择第二个版本',
                description: '正在自动比较...',
                duration: 2000
            });
            // 自动执行比较
            setTimeout(() => {
                performComparison(compareFrom, revisionId);
            }, 500);
        }
    };

    // 开始执行比较
    const handleStartComparison = async () => {
        console.log('🔵 点击开始比较按钮', 'compareFrom:', compareFrom, 'compareTo:', compareTo);

        if (!compareFrom || !compareTo) {
            console.log('❌ 缺少版本选择');
            toast({
                title: '⚠️ 提示',
                description: '请先选择两个版本',
                variant: 'destructive'
            });
            return;
        }

        console.log('✅ 开始执行比较...', compareFrom, compareTo);
        toast({
            title: '🔄 正在比较...',
            description: '正在加载比较结果'
        });
        performComparison(compareFrom, compareTo);
    };

    // 执行版本比较
    const performComparison = async (rev1Id: number, rev2Id: number) => {
        console.log('🔵 performComparison被调用', 'rev1Id:', rev1Id, 'rev2Id:', rev2Id);
        try {
            console.log('📡 发送API请求到:', `/articles/revisions/compare?revision1_id=${rev1Id}&revision2_id=${rev2Id}`);
            const result = await apiClient.get(`/articles/revisions/compare`, {
                revision1_id: rev1Id,
                revision2_id: rev2Id
            });

            console.log('📨 API响应:', result);

            if (result.success) {
                setComparisonResult(result.data as ComparisonResult);
                setComparisonMode(true);
                console.log('✅ 状态已更新，对话框应该打开');
            } else {
                console.log('❌ API返回失败:', result.error);
                toast({
                    title: '比较失败',
                    description: result.error,
                    variant: 'destructive'
                });
            }
        } catch (error) {
            console.error('❌ 比较出错:', error);
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
        setShowDiffView(false);
    };

    // 导出差异为文本
    const handleExportText = () => {
        if (!comparisonResult) return;

        const diff = computeDiff(
            comparisonResult.revision1.content || '',
            comparisonResult.revision2.content || ''
        );

        const text = exportDiffAsText(
            diff,
            `版本 #${comparisonResult.revision1.revision_number}`,
            `版本 #${comparisonResult.revision2.revision_number}`
        );

        downloadFile(text, 'diff-report.txt', 'text/plain');
        toast({
            title: '导出成功',
            description: '差异报告已下载'
        });
    };

    // 导出差异为 Markdown
    const handleExportMarkdown = () => {
        if (!comparisonResult) return;

        const diff = computeDiff(
            comparisonResult.revision1.content || '',
            comparisonResult.revision2.content || ''
        );

        const md = exportDiffAsMarkdown(
            diff,
            `版本 #${comparisonResult.revision1.revision_number}`,
            `版本 #${comparisonResult.revision2.revision_number}`
        );

        downloadFile(md, 'diff-report.md', 'text/markdown');
        toast({
            title: '导出成功',
            description: 'Markdown 报告已下载'
        });
    };

    // 下载文件辅助函数
    const downloadFile = (content: string, filename: string, mimeType: string) => {
        const blob = new Blob([content], {type: mimeType});
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
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
            const result = await apiClient.post(`/articles/${articleId}/revisions/${revisionToRollback.id}/rollback`, {});

            if (result.success) {
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
                    description: result.error,
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

    // 打开删除确认对话框
    const handleDeleteClick = (revision: Revision) => {
        setRevisionToDelete(revision);
        setDeleteDialogOpen(true);
    };

    // 执行删除
    const handleConfirmDelete = async () => {
        if (!revisionToDelete || !articleId) return;

        try {
            const result = await apiClient.delete(`/articles/${articleId}/revisions/${revisionToDelete.id}`);

            if (result.success) {
                toast({
                    title: '删除成功',
                    description: `版本 #${revisionToDelete.revision_number} 已删除`
                });
                setDeleteDialogOpen(false);
                setRevisionToDelete(null);
                fetchRevisions(); // 刷新列表
            } else {
                toast({
                    title: '删除失败',
                    description: result.error,
                    variant: 'destructive'
                });
            }
        } catch (error) {
            toast({
                title: '网络错误',
                description: '无法删除修订版本',
                variant: 'destructive'
            });
        }
    };

    // 加载本地草稿到编辑器
    const handleLoadLocalDraft = () => {
        if (!localDraft || !articleId) return;

        // 通过自定义事件通知父组件加载草稿
        const event = new CustomEvent('loadLocalDraft', {
            detail: {
                articleId,
                draft: localDraft
            }
        });
        window.dispatchEvent(event);

        toast({
            title: '已加载本地草稿',
            description: '草稿内容已填充到编辑器'
        });

        // 关闭侧边栏
        onClose();
    };

    // 删除本地草稿
    const handleDeleteLocalDraft = async () => {
        if (!articleId) return;

        draftService.deleteDraft(articleId);
        setLocalDraft(null);

        toast({
            title: '已删除本地草稿',
            description: '本地草稿已被清除'
        });
    };

    // 同步本地草稿到云端
    const handleSyncLocalDraft = async () => {
        if (!localDraft || !articleId) return;

        if (!confirm(`确定要将本地草稿同步到云端吗？\n\n保存时间：${new Date(localDraft.savedAt).toLocaleString()}\n\n这将在云端创建一个新的修订版本。`)) {
            return;
        }

        try {
            const result = await apiClient.post(`/articles/${articleId}/revisions`, {
                change_summary: `从本地草稿同步 (${new Date(localDraft.savedAt).toLocaleString()})`
            });

            if (result.success) {
                toast({
                    title: '同步成功',
                    description: '本地草稿已同步到云端并创建修订版本'
                });

                // 删除本地草稿
                draftService.deleteDraft(articleId);
                setLocalDraft(null);

                // 刷新修订历史
                fetchRevisions();
            } else {
                toast({
                    title: '同步失败',
                    description: result.error,
                    variant: 'destructive'
                });
            }
        } catch (error) {
            toast({
                title: '网络错误',
                description: '同步失败，请稍后重试',
                variant: 'destructive'
            });
        }
    };

    // 获取字段标签
    const getFieldLabel = (field: string) => {
        const labels: Record<string, string> = {
            title_changed: '标题',
            excerpt_changed: '摘要',
            content_changed: '内容',
            cover_image_changed: '封面图',
            tags_changed: '标签',
            category_changed: '分类',
            status_changed: '状态'
        };
        return labels[field] || field;
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
                                {(compareFrom || compareTo) && !comparisonMode && (
                                    <div
                                        className="bg-gradient-to-r from-blue-50 to-purple-50 dark:from-blue-950 dark:to-purple-950 border-2 border-blue-300 dark:border-blue-700 rounded-xl p-4 shadow-md">
                                        <div className="flex items-center justify-between">
                                            <div className="flex items-center gap-3">
                                                <GitCompare className="w-6 h-6 text-blue-600 animate-pulse"/>
                                                <div>
                                                    <span
                                                        className="text-sm font-bold text-blue-900 dark:text-blue-100">
                                                        📊 比较模式
                                                    </span>
                                                    <div className="flex items-center gap-2 mt-1">
                                                        {compareFrom && (
                                                            <Badge variant="default" className="bg-blue-600">
                                                                版本
                                                                #{revisions.find(r => r.id === compareFrom)?.revision_number}
                                                            </Badge>
                                                        )}
                                                        {compareTo && (
                                                            <>
                                                                <span className="text-gray-500 font-bold">VS</span>
                                                                <Badge variant="default" className="bg-purple-600">
                                                                    版本
                                                                    #{revisions.find(r => r.id === compareTo)?.revision_number}
                                                                </Badge>
                                                            </>
                                                        )}
                                                        {!compareTo && compareFrom && (
                                                            <span
                                                                className="text-xs text-gray-600 dark:text-gray-400 ml-2">
                                                                👈 请选择第二个版本
                                                            </span>
                                                        )}
                                                    </div>
                                                </div>
                                            </div>
                                            <div className="flex items-center gap-2">
                                                {compareTo && (
                                                    <Button
                                                        size="sm"
                                                        onClick={handleStartComparison}
                                                        className="bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white font-semibold shadow-md"
                                                    >
                                                        <GitCompare className="w-4 h-4 mr-1"/>
                                                        开始比较
                                                    </Button>
                                                )}
                                                <Button
                                                    size="sm"
                                                    variant="outline"
                                                    onClick={handleCancelCompare}
                                                    className="border-red-300 text-red-600 hover:bg-red-50 dark:hover:bg-red-950"
                                                >
                                                    <X className="w-4 h-4 mr-1"/>
                                                    取消
                                                </Button>
                                            </div>
                                        </div>
                                    </div>
                                )}

                                {/* 本地草稿条目 */}
                                {localDraft && (
                                    <div
                                        className="border-2 border-yellow-400 dark:border-yellow-600 rounded-lg p-4 bg-yellow-50 dark:bg-yellow-950 transition-all hover:shadow-md">
                                        <div className="flex items-start justify-between mb-3">
                                            <div className="flex items-center gap-2">
                                                <Badge variant="default" className="text-base bg-yellow-600">
                                                    <Save className="w-3 h-3 mr-1"/>
                                                    本地草稿
                                                </Badge>
                                                <Badge variant="outline"
                                                       className="text-yellow-700 dark:text-yellow-400 border-yellow-600">
                                                    未同步
                                                </Badge>
                                            </div>
                                            <div
                                                className="text-xs text-gray-500 dark:text-gray-400 flex items-center gap-1">
                                                <Clock className="w-3 h-3"/>
                                                {formatDate(localDraft.savedAt)}
                                            </div>
                                        </div>

                                        <h3 className="text-lg font-semibold mb-2 text-gray-900 dark:text-white line-clamp-1">
                                            {localDraft.title}
                                        </h3>

                                        {localDraft.excerpt && (
                                            <p className="text-sm text-gray-600 dark:text-gray-400 mb-3 line-clamp-2">
                                                {localDraft.excerpt}
                                            </p>
                                        )}

                                        <div
                                            className="text-xs text-yellow-700 dark:text-yellow-400 mb-3 flex items-start gap-1">
                                            <FileText className="w-3 h-3 mt-0.5 flex-shrink-0"/>
                                            <span>自动保存的本地草稿</span>
                                        </div>

                                        <Separator className="my-3 border-yellow-300 dark:border-yellow-700"/>

                                        <div className="flex gap-2">
                                            <Button
                                                size="sm"
                                                variant="outline"
                                                onClick={handleLoadLocalDraft}
                                                className="flex-1 border-yellow-600 text-yellow-700 hover:bg-yellow-100 dark:hover:bg-yellow-900"
                                            >
                                                <Eye className="w-4 h-4 mr-2"/>
                                                加载
                                            </Button>
                                            <Button
                                                size="sm"
                                                variant="outline"
                                                onClick={handleDeleteLocalDraft}
                                                className="flex-1 border-red-600 text-red-700 hover:bg-red-100 dark:hover:bg-red-900"
                                            >
                                                <Trash2 className="w-4 h-4 mr-2"/>
                                                删除
                                            </Button>
                                            <Button
                                                size="sm"
                                                variant="default"
                                                onClick={handleSyncLocalDraft}
                                                className="flex-1 bg-purple-600 hover:bg-purple-700"
                                            >
                                                <Upload className="w-4 h-4 mr-2"/>
                                                同步到云端
                                            </Button>
                                        </div>
                                    </div>
                                )}

                                {/* 修订列表 */}
                                {revisions.map((revision, index) => (
                                    <div
                                        key={revision.id}
                                        className={`border-2 rounded-xl p-5 transition-all hover:shadow-lg ${
                                            compareFrom === revision.id
                                                ? 'border-blue-500 bg-gradient-to-br from-blue-50 to-white dark:from-blue-950/30 dark:to-gray-900 shadow-md'
                                                : compareTo === revision.id
                                                    ? 'border-purple-500 bg-gradient-to-br from-purple-50 to-white dark:from-purple-950/30 dark:to-gray-900 shadow-md'
                                                    : 'hover:border-gray-300 dark:hover:border-gray-600 border-gray-200 dark:border-gray-700'
                                        }`}
                                    >
                                        <div className="flex items-start justify-between mb-3">
                                            <div className="flex items-center gap-2">
                                                <Badge variant="secondary" className="text-base">
                                                    v{revision.revision_number}
                                                </Badge>
                                                {compareFrom === revision.id && (
                                                    <Badge variant="default" className="bg-blue-600 animate-pulse">
                                                        第一个版本
                                                    </Badge>
                                                )}
                                                {compareTo === revision.id && (
                                                    <Badge variant="default" className="bg-purple-600 animate-pulse">
                                                        第二个版本
                                                    </Badge>
                                                )}
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

                                            {/* 比较下拉菜单 */}
                                            <div className="relative flex-1">
                                                <Button
                                                    size="sm"
                                                    variant="outline"
                                                    onClick={() => setCompareMenuOpen(compareMenuOpen === revision.id ? null : revision.id)}
                                                    className="w-full"
                                                >
                                                    <GitCompare className="w-4 h-4 mr-2"/>
                                                    比较
                                                    <ChevronDown className="w-3 h-3 ml-1"/>
                                                </Button>

                                                {compareMenuOpen === revision.id && (
                                                    <>
                                                        <div
                                                            className="fixed inset-0 z-10"
                                                            onClick={() => setCompareMenuOpen(null)}
                                                        />
                                                        <div
                                                            className="absolute right-0 mt-2 w-48 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 z-20 overflow-hidden">
                                                            <button
                                                                onClick={(e) => {
                                                                    e.stopPropagation();
                                                                    handleCompareWithEditor(revision);
                                                                }}
                                                                className="w-full px-4 py-2 text-left text-sm hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center gap-2 transition-colors"
                                                            >
                                                                <FileText className="w-4 h-4 text-blue-600"/>
                                                                <span>与当前编辑器比较</span>
                                                            </button>
                                                            <button
                                                                onClick={(e) => {
                                                                    e.stopPropagation();
                                                                    handleCompareWithVersion(revision.id);
                                                                }}
                                                                className="w-full px-4 py-2 text-left text-sm hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center gap-2 transition-colors border-t border-gray-200 dark:border-gray-700"
                                                            >
                                                                <GitCompare className="w-4 h-4 text-purple-600"/>
                                                                <span>与指定版本比较</span>
                                                            </button>
                                                        </div>
                                                    </>
                                                )}
                                            </div>
                                            
                                            <Button
                                                size="sm"
                                                variant="default"
                                                onClick={() => handleRollbackClick(revision)}
                                                className="flex-1 bg-blue-600 hover:bg-blue-700"
                                            >
                                                <RotateCcw className="w-4 h-4 mr-2"/>
                                                回滚
                                            </Button>
                                            <Button
                                                size="sm"
                                                variant="outline"
                                                onClick={() => handleDeleteClick(revision)}
                                                className="flex-1 border-red-600 text-red-700 hover:bg-red-100 dark:hover:bg-red-900"
                                            >
                                                <Trash2 className="w-4 h-4 mr-2"/>
                                                删除
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

            {/* 删除确认对话框 */}
            <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle className="flex items-center gap-2">
                            <AlertCircle className="w-5 h-5 text-red-500"/>
                            确认删除
                        </DialogTitle>
                        <DialogDescription>
                            您确定要删除版本 #{revisionToDelete?.revision_number} 吗？
                        </DialogDescription>
                    </DialogHeader>
                    <div
                        className="bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800 rounded-lg p-4">
                        <p className="text-sm text-red-900 dark:text-red-100">
                            <strong>警告：</strong>删除后无法恢复，请谨慎操作！
                        </p>
                    </div>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setDeleteDialogOpen(false)}>
                            取消
                        </Button>
                        <Button
                            variant="default"
                            onClick={handleConfirmDelete}
                            className="bg-red-600 hover:bg-red-700"
                        >
                            确认删除
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* 比较结果对话框 */}
            <Dialog open={comparisonMode && comparisonResult !== null} onOpenChange={(open) => {
                if (!open) handleCancelCompare();
            }}>
                <DialogContent className="max-w-7xl max-h-[95vh] w-[95vw]">
                    <DialogHeader>
                        <DialogTitle className="flex items-center gap-2 text-xl">
                            <GitCompare className="w-6 h-6 text-blue-600"/>
                            版本比较
                        </DialogTitle>
                        <DialogDescription className="text-base">
                            {comparisonResult && (
                                <span className="font-medium">
                                    比较版本 #{comparisonResult.revision1.revision_number} 和 #{comparisonResult.revision2.revision_number}
                                </span>
                            )}
                        </DialogDescription>
                    </DialogHeader>

                    {comparisonResult && (
                        <ScrollArea className="max-h-[75vh] pr-4">
                            <div className="space-y-6">
                                {/* 差异摘要 - 优化样式 */}
                                <div
                                    className="bg-gradient-to-r from-gray-50 to-gray-100 dark:from-gray-800 dark:to-gray-900 rounded-xl p-5 border border-gray-200 dark:border-gray-700 shadow-sm">
                                    <h4 className="font-semibold mb-4 text-gray-900 dark:text-white flex items-center gap-2">
                                        <FileText className="w-5 h-5"/>
                                        变更摘要
                                    </h4>

                                    {/* 差异统计 */}
                                    {comparisonResult.differences.content_changed && (
                                        <div
                                            className="mb-4 p-3 bg-blue-50 dark:bg-blue-950/30 rounded-lg border border-blue-200 dark:border-blue-800">
                                            {(() => {
                                                const diff = computeDiff(
                                                    comparisonResult.revision1.content || '',
                                                    comparisonResult.revision2.content || ''
                                                );
                                                return (
                                                    <div className="flex items-center gap-4 text-sm">
                                                        <span className="text-gray-700 dark:text-gray-300">
                                                            <strong>内容变更：</strong>
                                                        </span>
                                                        <Badge variant="outline"
                                                               className="bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 border-green-300">
                                                            +{diff.addedCount} 行新增
                                                        </Badge>
                                                        <Badge variant="outline"
                                                               className="bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300 border-red-300">
                                                            -{diff.removedCount} 行删除
                                                        </Badge>
                                                        <span className="text-gray-500 dark:text-gray-400 ml-auto">
                                                            {getDiffSummary(diff)}
                                                        </span>
                                                    </div>
                                                );
                                            })()}
                                        </div>
                                    )}
                                    
                                    <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3">
                                        {Object.entries(comparisonResult.differences).map(([field, changed]) => (
                                            <div
                                                key={field}
                                                className={`flex items-center gap-2 px-3 py-2 rounded-lg transition-all ${
                                                    changed
                                                        ? 'bg-red-100 dark:bg-red-950/50 border border-red-300 dark:border-red-800'
                                                        : 'bg-green-100 dark:bg-green-950/50 border border-green-300 dark:border-green-800'
                                                }`}
                                            >
                                                <div
                                                    className={`w-2.5 h-2.5 rounded-full flex-shrink-0 ${changed ? 'bg-red-500 animate-pulse' : 'bg-green-500'}`}/>
                                                <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                                                    {getFieldLabel(field)}
                                                </span>
                                                {changed && <Badge variant="destructive"
                                                                   className="text-xs ml-auto">已修改</Badge>}
                                            </div>
                                        ))}
                                    </div>
                                </div>

                                {/* 标题对比 */}
                                {comparisonResult.differences.title_changed && (
                                    <DiffSection
                                        label="标题"
                                        oldValue={comparisonResult.revision1.title}
                                        newValue={comparisonResult.revision2.title}
                                    />
                                )}

                                {/* 摘要对比 */}
                                {comparisonResult.differences.excerpt_changed && (
                                    <DiffSection
                                        label="摘要"
                                        oldValue={comparisonResult.revision1.excerpt}
                                        newValue={comparisonResult.revision2.excerpt}
                                    />
                                )}

                                {/* 内容对比 - 优化样式 */}
                                {comparisonResult.differences.content_changed && (
                                    <div
                                        className="border-2 border-gray-200 dark:border-gray-700 rounded-xl overflow-hidden shadow-lg">
                                        <div
                                            className="bg-gradient-to-r from-gray-100 to-gray-50 dark:from-gray-800 dark:to-gray-900 px-6 py-3 border-b-2 border-gray-200 dark:border-gray-700 flex items-center justify-between">
                                            <h4 className="font-bold text-lg text-gray-900 dark:text-white flex items-center gap-2">
                                                <FileText className="w-5 h-5"/>
                                                文章内容对比
                                            </h4>
                                            <div className="flex gap-2">
                                                <Button
                                                    size="sm"
                                                    variant={!showDiffView ? "default" : "outline"}
                                                    onClick={() => setShowDiffView(false)}
                                                    className="text-xs"
                                                >
                                                    并排视图
                                                </Button>
                                                <Button
                                                    size="sm"
                                                    variant={showDiffView ? "default" : "outline"}
                                                    onClick={() => {
                                                        setShowDiffView(true);
                                                    }}
                                                    className="text-xs"
                                                >
                                                    差异视图
                                                </Button>
                                            </div>
                                        </div>

                                        {!showDiffView ? (
                                            // 并排视图
                                            <div
                                                className="grid grid-cols-2 divide-x-2 divide-gray-200 dark:divide-gray-700">
                                                <div
                                                    className="p-6 bg-gradient-to-b from-red-50 to-white dark:from-red-950/20 dark:to-gray-900">
                                                    <div
                                                        className="text-sm font-bold text-red-700 dark:text-red-400 mb-3 flex items-center gap-2 pb-2 border-b-2 border-red-200 dark:border-red-800">
                                                        <span className="w-2 h-2 rounded-full bg-red-500"></span>
                                                        旧版本 (v{comparisonResult.revision1.revision_number})
                                                    </div>
                                                    <div
                                                        className="prose prose-sm md:prose-base dark:prose-invert max-w-none"
                                                        dangerouslySetInnerHTML={{__html: comparisonResult.revision1.content || '<p class="text-gray-400 italic">无内容</p>'}}
                                                    />
                                                </div>
                                                <div
                                                    className="p-6 bg-gradient-to-b from-green-50 to-white dark:from-green-950/20 dark:to-gray-900">
                                                    <div
                                                        className="text-sm font-bold text-green-700 dark:text-green-400 mb-3 flex items-center gap-2 pb-2 border-b-2 border-green-200 dark:border-green-800">
                                                        <span className="w-2 h-2 rounded-full bg-green-500"></span>
                                                        {comparisonResult.revision2.revision_number === 0 ? '当前编辑器' : `新版本 (v${comparisonResult.revision2.revision_number})`}
                                                    </div>
                                                    <div
                                                        className="prose prose-sm md:prose-base dark:prose-invert max-w-none"
                                                        dangerouslySetInnerHTML={{__html: comparisonResult.revision2.content || '<p class="text-gray-400 italic">无内容</p>'}}
                                                    />
                                                </div>
                                            </div>
                                        ) : (
                                            // 差异视图
                                            <div className="p-6 bg-gray-50 dark:bg-gray-900">
                                                <div
                                                    className="mb-4 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
                                                    <p className="text-sm text-blue-900 dark:text-blue-200">
                                                        <strong>差异说明：</strong>
                                                        <span
                                                            className="ml-2 text-red-600 dark:text-red-400">红色背景</span>表示删除的行，
                                                        <span
                                                            className="ml-2 text-green-600 dark:text-green-400">绿色背景</span>表示新增的行
                                                    </p>
                                                </div>
                                                <div
                                                    className="border border-gray-300 dark:border-gray-700 rounded-lg overflow-auto max-h-[500px] bg-white dark:bg-gray-900"
                                                    dangerouslySetInnerHTML={{
                                                        __html: formatDiffAsHtml(computeDiff(
                                                            comparisonResult.revision1.content || '',
                                                            comparisonResult.revision2.content || ''
                                                        ))
                                                    }}
                                                />
                                            </div>
                                        )}
                                    </div>
                                )}

                                {/* 封面图对比 */}
                                {comparisonResult.differences.cover_image_changed && (
                                    <DiffSection
                                        label="封面图"
                                        oldValue={comparisonResult.revision1.cover_image || '无'}
                                        newValue={comparisonResult.revision2.cover_image || '无'}
                                        isImage={true}
                                    />
                                )}

                                {/* 标签对比 */}
                                {comparisonResult.differences.tags_changed && (
                                    <DiffSection
                                        label="标签"
                                        oldValue={comparisonResult.revision1.tags_list || '无'}
                                        newValue={comparisonResult.revision2.tags_list || '无'}
                                    />
                                )}
                            </div>
                        </ScrollArea>
                    )}

                    <DialogFooter className="flex-col sm:flex-row gap-2">
                        <div className="flex gap-2 flex-1">
                            <Button
                                variant="outline"
                                size="sm"
                                onClick={handleExportText}
                                className="flex-1"
                            >
                                <FileText className="w-4 h-4 mr-2"/>
                                导出 TXT
                            </Button>
                            <Button
                                variant="outline"
                                size="sm"
                                onClick={handleExportMarkdown}
                                className="flex-1"
                            >
                                <FileText className="w-4 h-4 mr-2"/>
                                导出 MD
                            </Button>
                        </div>
                        <Button variant="outline" onClick={handleCancelCompare}>
                            关闭
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </>
    );
}
