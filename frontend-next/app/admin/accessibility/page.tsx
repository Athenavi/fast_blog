/**
 * 无障碍性管理页面
 * 提供WCAG 2.1标准的自动化审计和修复建议
 */
'use client';

import {useEffect, useState} from 'react';
import {Card, CardContent, CardDescription, CardHeader, CardTitle} from '@/components/ui/card';
import {Badge} from '@/components/ui/badge';
import {Button} from '@/components/ui/button';
import {Tabs, TabsContent, TabsList, TabsTrigger} from '@/components/ui/tabs';
import {Progress} from '@/components/ui/progress';
import {ScrollArea} from '@/components/ui/scroll-area';
import {
    AlertTriangle,
    CheckCircle2,
    Code,
    ExternalLink,
    Eye,
    Keyboard,
    Palette,
    RefreshCw,
    Type,
    XCircle
} from 'lucide-react';
import apiClient from '@/lib/api-client';

interface AuditIssue {
    id: string;
    rule: string;
    impact: 'critical' | 'serious' | 'moderate' | 'minor';
    description: string;
    help: string;
    helpUrl: string;
    nodes: Array<{
        html: string;
        target: string[];
        failureSummary: string;
    }>;
}

interface AuditReport {
    url?: string;
    timestamp: string;
    level: string;
    violations: AuditIssue[];
    passes: Array<{ rule: string; description: string }>;
    incomplete: Array<{ rule: string; description: string }>;
    score: number;
}

export default function AccessibilityManager() {
    const [activeTab, setActiveTab] = useState('audit');
    const [loading, setLoading] = useState(false);
    const [report, setReport] = useState<AuditReport | null>(null);
    const [guidelines, setGuidelines] = useState<any>(null);
    const [checklist, setChecklist] = useState<any>(null);
    const [tools, setTools] = useState<any>(null);
    const [htmlContent, setHtmlContent] = useState('');
    const [testUrl, setTestUrl] = useState('');

    useEffect(() => {
        loadReferenceData();
    }, []);

    const loadReferenceData = async () => {
        try {
            const [guidelinesRes, checklistRes, toolsRes] = await Promise.all([
                apiClient.get('/accessibility/guidelines').catch(() => ({data: {success: false}})),
                apiClient.get('/accessibility/checklist').catch(() => ({data: {success: false}})),
                apiClient.get('/accessibility/tools').catch(() => ({data: {success: false}}))
            ]);

            // @ts-expect-error - API response type inference
            if (guidelinesRes.data?.success) {
                setGuidelines(guidelinesRes.data.data);
            }
            // @ts-expect-error - API response type inference
            if (checklistRes.data?.success) {
                setChecklist(checklistRes.data.data);
            }
            // @ts-expect-error - API response type inference
            if (toolsRes.data?.success) {
                setTools(toolsRes.data.data);
            }
        } catch (error) {
            console.error('Failed to load reference data:', error);
        }
    };

    const runAudit = async () => {
        if (!htmlContent.trim()) {
            alert('请输入HTML内容');
            return;
        }

        try {
            setLoading(true);
            const response = await apiClient.post('/accessibility/audit', {
                html_content: htmlContent,
                url: testUrl || undefined,
                level: 'AA'
            });

            // @ts-expect-error - API response type inference
            if (response.data?.success) {
                setReport(response.data.data);
                setActiveTab('results');
            } else {
                alert('审计失败: ' + (response.data?.error || '未知错误'));
            }
        } catch (error) {
            console.error('Audit failed:', error);
            alert('审计失败，请重试');
        } finally {
            setLoading(false);
        }
    };

    const getImpactColor = (impact: string) => {
        switch (impact) {
            case 'critical':
                return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200';
            case 'serious':
                return 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200';
            case 'moderate':
                return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200';
            case 'minor':
                return 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200';
            default:
                return 'bg-gray-100 text-gray-800';
        }
    };

    const getImpactIcon = (impact: string) => {
        switch (impact) {
            case 'critical':
                return <XCircle className="h-4 w-4 text-red-500"/>;
            case 'serious':
                return <AlertTriangle className="h-4 w-4 text-orange-500"/>;
            case 'moderate':
                return <AlertTriangle className="h-4 w-4 text-yellow-500"/>;
            case 'minor':
                return <CheckCircle2 className="h-4 w-4 text-blue-500"/>;
            default:
                return null;
        }
    };

    const getScoreColor = (score: number) => {
        if (score >= 90) return 'text-green-600';
        if (score >= 70) return 'text-yellow-600';
        return 'text-red-600';
    };

    return (
        <div className="space-y-6">
            {/* 页面标题 */}
            <div>
                <h1 className="text-3xl font-bold tracking-tight">无障碍性管理</h1>
                <p className="text-muted-foreground mt-2">
                    WCAG 2.1标准自动化审计和修复建议
                </p>
            </div>

            {/* 主标签页 */}
            <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
                <TabsList className="grid w-full grid-cols-4">
                    <TabsTrigger value="audit">运行审计</TabsTrigger>
                    <TabsTrigger value="results" disabled={!report}>审计结果</TabsTrigger>
                    <TabsTrigger value="guidelines">WCAG指南</TabsTrigger>
                    <TabsTrigger value="checklist">检查清单</TabsTrigger>
                </TabsList>

                {/* 运行审计 */}
                <TabsContent value="audit" className="space-y-4">
                    <Card>
                        <CardHeader>
                            <CardTitle>页面审计</CardTitle>
                            <CardDescription>
                                输入HTML内容进行无障碍性检查
                            </CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <div>
                                <label className="text-sm font-medium mb-2 block">
                                    页面URL（可选）
                                </label>
                                <input
                                    type="text"
                                    value={testUrl}
                                    onChange={(e) => setTestUrl(e.target.value)}
                                    placeholder="https://example.com/page"
                                    className="w-full px-3 py-2 border rounded-md"
                                />
                            </div>

                            <div>
                                <label className="text-sm font-medium mb-2 block">
                                    HTML内容 *
                                </label>
                                <textarea
                                    value={htmlContent}
                                    onChange={(e) => setHtmlContent(e.target.value)}
                                    placeholder="粘贴HTML代码..."
                                    rows={10}
                                    className="w-full px-3 py-2 border rounded-md font-mono text-sm"
                                />
                            </div>

                            <Button onClick={runAudit} disabled={loading}>
                                {loading ? (
                                    <>
                                        <RefreshCw className="mr-2 h-4 w-4 animate-spin"/>
                                        审计中...
                                    </>
                                ) : (
                                    <>
                                        <Eye className="mr-2 h-4 w-4"/>
                                        运行审计
                                    </>
                                )}
                            </Button>
                        </CardContent>
                    </Card>

                    {/* 快速提示 */}
                    <Card>
                        <CardHeader>
                            <CardTitle className="text-sm">💡 提示</CardTitle>
                        </CardHeader>
                        <CardContent className="text-sm space-y-2">
                            <p>• 可以粘贴完整的HTML页面或单个组件</p>
                            <p>• 审计基于WCAG 2.1 AA级别标准</p>
                            <p>• 重点关注关键和严重级别的问题</p>
                            <p>• 查看"WCAG指南"了解详细标准</p>
                        </CardContent>
                    </Card>
                </TabsContent>

                {/* 审计结果 */}
                <TabsContent value="results">
                    {report && (
                        <div className="space-y-4">
                            {/* 总览卡片 */}
                            <Card>
                                <CardHeader>
                                    <CardTitle>审计总览</CardTitle>
                                </CardHeader>
                                <CardContent className="space-y-4">
                                    <div className="flex items-center justify-between">
                                        <div>
                                            <p className="text-sm text-muted-foreground">无障碍性评分</p>
                                            <p className={`text-4xl font-bold ${getScoreColor(report.score)}`}>
                                                {report.score}/100
                                            </p>
                                        </div>
                                        <div className="text-right">
                                            <p className="text-sm text-muted-foreground">审计时间</p>
                                            <p className="text-sm font-medium">
                                                {new Date(report.timestamp).toLocaleString('zh-CN')}
                                            </p>
                                        </div>
                                    </div>

                                    <Progress value={report.score} className="h-2"/>

                                    <div className="grid grid-cols-3 gap-4 pt-4">
                                        <div className="text-center p-4 bg-red-50 dark:bg-red-950 rounded-lg">
                                            <p className="text-2xl font-bold text-red-600">
                                                {report.violations.length}
                                            </p>
                                            <p className="text-xs text-muted-foreground">违规项</p>
                                        </div>
                                        <div className="text-center p-4 bg-green-50 dark:bg-green-950 rounded-lg">
                                            <p className="text-2xl font-bold text-green-600">
                                                {report.passes.length}
                                            </p>
                                            <p className="text-xs text-muted-foreground">通过项</p>
                                        </div>
                                        <div className="text-center p-4 bg-yellow-50 dark:bg-yellow-950 rounded-lg">
                                            <p className="text-2xl font-bold text-yellow-600">
                                                {report.incomplete.length}
                                            </p>
                                            <p className="text-xs text-muted-foreground">待确认</p>
                                        </div>
                                    </div>
                                </CardContent>
                            </Card>

                            {/* 违规项列表 */}
                            {report.violations.length > 0 && (
                                <Card>
                                    <CardHeader>
                                        <CardTitle className="flex items-center gap-2">
                                            <XCircle className="h-5 w-5 text-red-500"/>
                                            违规项 ({report.violations.length})
                                        </CardTitle>
                                        <CardDescription>
                                            需要修复的无障碍性问题
                                        </CardDescription>
                                    </CardHeader>
                                    <CardContent>
                                        <ScrollArea className="h-[600px] pr-4">
                                            <div className="space-y-4">
                                                {report.violations.map((issue, index) => (
                                                    <div
                                                        key={index}
                                                        className="p-4 border rounded-lg space-y-3"
                                                    >
                                                        <div className="flex items-start justify-between">
                                                            <div className="flex items-center gap-2">
                                                                {getImpactIcon(issue.impact)}
                                                                <h4 className="font-medium">{issue.rule}</h4>
                                                                <Badge className={getImpactColor(issue.impact)}>
                                                                    {issue.impact}
                                                                </Badge>
                                                            </div>
                                                            <a
                                                                href={issue.helpUrl}
                                                                target="_blank"
                                                                rel="noopener noreferrer"
                                                                className="text-blue-600 hover:underline text-sm flex items-center gap-1"
                                                            >
                                                                帮助文档
                                                                <ExternalLink className="h-3 w-3"/>
                                                            </a>
                                                        </div>

                                                        <p className="text-sm text-muted-foreground">
                                                            {issue.description}
                                                        </p>

                                                        <div className="bg-muted p-3 rounded text-sm">
                                                            <p className="font-medium mb-2">修复建议：</p>
                                                            <p>{issue.help}</p>
                                                        </div>

                                                        {issue.nodes.length > 0 && (
                                                            <div className="space-y-2">
                                                                <p className="text-sm font-medium">
                                                                    受影响元素 ({issue.nodes.length}):
                                                                </p>
                                                                {issue.nodes.slice(0, 3).map((node, nodeIndex) => (
                                                                    <div
                                                                        key={nodeIndex}
                                                                        className="bg-red-50 dark:bg-red-950 p-2 rounded text-xs font-mono overflow-x-auto"
                                                                    >
                                                                        <p className="text-red-600 mb-1">
                                                                            {node.failureSummary}
                                                                        </p>
                                                                        <p className="text-muted-foreground truncate">
                                                                            {node.html}
                                                                        </p>
                                                                    </div>
                                                                ))}
                                                                {issue.nodes.length > 3 && (
                                                                    <p className="text-xs text-muted-foreground">
                                                                        还有 {issue.nodes.length - 3} 个元素...
                                                                    </p>
                                                                )}
                                                            </div>
                                                        )}
                                                    </div>
                                                ))}
                                            </div>
                                        </ScrollArea>
                                    </CardContent>
                                </Card>
                            )}
                        </div>
                    )}
                </TabsContent>

                {/* WCAG指南 */}
                <TabsContent value="guidelines">
                    {guidelines ? (
                        <div className="space-y-4">
                            {Object.entries(guidelines).map(([key, guideline]: [string, any]) => (
                                <Card key={key}>
                                    <CardHeader>
                                        <CardTitle className="flex items-center gap-2">
                                            {key === 'perceivable' && <Eye className="h-5 w-5"/>}
                                            {key === 'operable' && <Keyboard className="h-5 w-5"/>}
                                            {key === 'understandable' && <Type className="h-5 w-5"/>}
                                            {key === 'robust' && <Code className="h-5 w-5"/>}
                                            {guideline.title}
                                        </CardTitle>
                                        <CardDescription>{guideline.description}</CardDescription>
                                    </CardHeader>
                                    <CardContent>
                                        <div className="space-y-3">
                                            {guideline.principles?.map((principle: any, idx: number) => (
                                                <div key={idx} className="p-3 bg-muted rounded-lg">
                                                    <p className="font-medium text-sm mb-1">
                                                        {principle.id}: {principle.name}
                                                    </p>
                                                    <p className="text-xs text-muted-foreground">
                                                        {principle.description}
                                                    </p>
                                                </div>
                                            ))}
                                        </div>
                                    </CardContent>
                                </Card>
                            ))}
                        </div>
                    ) : (
                        <Card>
                            <CardContent className="py-8 text-center text-muted-foreground">
                                加载中...
                            </CardContent>
                        </Card>
                    )}
                </TabsContent>

                {/* 检查清单 */}
                <TabsContent value="checklist">
                    {checklist ? (
                        <div className="space-y-4">
                            {Object.entries(checklist).map(([key, category]: [string, any]) => (
                                <Card key={key}>
                                    <CardHeader>
                                        <CardTitle className="flex items-center gap-2">
                                            {key === 'perceivable' && <Palette className="h-5 w-5"/>}
                                            {key === 'operable' && <Keyboard className="h-5 w-5"/>}
                                            {key === 'understandable' && <Type className="h-5 w-5"/>}
                                            {key === 'robust' && <Code className="h-5 w-5"/>}
                                            {category.title}
                                        </CardTitle>
                                    </CardHeader>
                                    <CardContent>
                                        <div className="space-y-2">
                                            {category.items?.map((item: any, idx: number) => (
                                                <div
                                                    key={idx}
                                                    className="flex items-start gap-3 p-3 border rounded-lg"
                                                >
                                                    <div className="flex-shrink-0 mt-0.5">
                                                        {item.priority === 'high' ? (
                                                            <XCircle className="h-4 w-4 text-red-500"/>
                                                        ) : (
                                                            <AlertTriangle className="h-4 w-4 text-yellow-500"/>
                                                        )}
                                                    </div>
                                                    <div className="flex-1">
                                                        <div className="flex items-center gap-2 mb-1">
                                                            <p className="text-sm font-medium">{item.task}</p>
                                                            <Badge variant="outline" className="text-xs">
                                                                WCAG {item.wcag_criterion}
                                                            </Badge>
                                                            <Badge
                                                                variant={item.priority === 'high' ? 'destructive' : 'secondary'}
                                                                className="text-xs"
                                                            >
                                                                {item.priority === 'high' ? '高优先级' : '中优先级'}
                                                            </Badge>
                                                        </div>
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                    </CardContent>
                                </Card>
                            ))}
                        </div>
                    ) : (
                        <Card>
                            <CardContent className="py-8 text-center text-muted-foreground">
                                加载中...
                            </CardContent>
                        </Card>
                    )}
                </TabsContent>
            </Tabs>
        </div>
    );
}
