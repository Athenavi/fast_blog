/**
 * 数据库 URL 替换工具页面
 * 用于网站迁移时批量替换数据库中的URL
 */
'use client';

import {useState} from 'react';
import {Card, CardContent, CardDescription, CardHeader, CardTitle} from '@/components/ui/card';
import {Button} from '@/components/ui/button';
import {Input} from '@/components/ui/input';
import {Label} from '@/components/ui/label';
import {Badge} from '@/components/ui/badge';
import {Alert, AlertDescription, AlertTitle} from '@/components/ui/alert';
import {Tabs, TabsContent, TabsList, TabsTrigger} from '@/components/ui/tabs';
import {Checkbox} from '@/components/ui/checkbox';
import {ScrollArea} from '@/components/ui/scroll-area';
import {AlertTriangle, CheckCircle2, Code, Eye, Info, List, Replace, Search, XCircle} from 'lucide-react';
import apiClient from '@/lib/api-client';

export default function DatabaseMigrationTool() {
    const [activeTab, setActiveTab] = useState('replace');
    const [loading, setLoading] = useState(false);

    // URL替换表单
    const [searchUrl, setSearchUrl] = useState('');
    const [replaceUrl, setReplaceUrl] = useState('');
    const [useRegex, setUseRegex] = useState(false);
    const [caseSensitive, setCaseSensitive] = useState(true);
    const [excludeTables, setExcludeTables] = useState<string[]>([]);

    // 预览结果
    const [previewResult, setPreviewResult] = useState<any>(null);
    const [validationResult, setValidationResult] = useState<any>(null);
    const [commonPatterns, setCommonPatterns] = useState<any>(null);

    // 加载常见模式
    const loadCommonPatterns = async () => {
        try {
            const response = await apiClient.get('/migration/url-replace/common-patterns');
            if (response.data?.success) {
                setCommonPatterns(response.data.data);
            }
        } catch (error) {
            console.error('Failed to load common patterns:', error);
        }
    };

    // 预览URL替换
    const handlePreview = async () => {
        if (!searchUrl || !replaceUrl) {
            alert('请输入搜索和替换URL');
            return;
        }

        try {
            setLoading(true);
            setPreviewResult(null);

            const response = await apiClient.post('/migration/url-replace/preview', {
                search: searchUrl,
                replace: replaceUrl,
                use_regex: useRegex,
                case_sensitive: caseSensitive,
                exclude_tables: excludeTables.length > 0 ? excludeTables : undefined
            });

            if (response.data?.success) {
                setPreviewResult(response.data.data);
            } else {
                alert('预览失败: ' + (response.data?.error || '未知错误'));
            }
        } catch (error) {
            console.error('Preview failed:', error);
            alert('预览失败，请重试');
        } finally {
            setLoading(false);
        }
    };

    // 执行URL替换
    const handleExecute = async () => {
        if (!previewResult) {
            alert('请先运行预览');
            return;
        }

        if (!confirm(`确认执行替换？这将修改 ${previewResult.total_replacements} 处数据。`)) {
            return;
        }

        try {
            setLoading(true);

            const response = await apiClient.post('/migration/url-replace/execute', {
                search: searchUrl,
                replace: replaceUrl,
                use_regex: useRegex,
                case_sensitive: caseSensitive,
                exclude_tables: excludeTables.length > 0 ? excludeTables : undefined
            });

            if (response.data?.success) {
                alert(`替换成功！共替换 ${response.data.data.total_replacements} 处`);
                setPreviewResult(response.data.data);
            } else {
                alert('替换失败: ' + (response.data?.error || '未知错误'));
            }
        } catch (error) {
            console.error('Execute failed:', error);
            alert('替换失败，请重试');
        } finally {
            setLoading(false);
        }
    };

    // 验证URL替换
    const handleValidate = async () => {
        if (!searchUrl || !replaceUrl) {
            alert('请输入旧URL和新URL');
            return;
        }

        try {
            setLoading(true);
            setValidationResult(null);

            const response = await apiClient.post('/migration/url-replace/validate', {
                old_url: searchUrl,
                new_url: replaceUrl,
                sample_size: 10
            });

            if (response.data?.success) {
                setValidationResult(response.data.data);
            } else {
                alert('验证失败: ' + (response.data?.error || '未知错误'));
            }
        } catch (error) {
            console.error('Validate failed:', error);
            alert('验证失败，请重试');
        } finally {
            setLoading(false);
        }
    };

    // 应用常见模式
    const applyPattern = (search: string, replace: string, regex: boolean = false) => {
        setSearchUrl(search);
        setReplaceUrl(replace);
        setUseRegex(regex);
    };

    return (
        <div className="space-y-6">
            {/* 页面标题 */}
            <div>
                <h1 className="text-3xl font-bold tracking-tight">数据库迁移工具</h1>
                <p className="text-muted-foreground mt-2">
                    URL替换、数据导出导入、迁移验证
                </p>
            </div>

            {/* 主标签页 */}
            <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
                <TabsList className="grid w-full grid-cols-3">
                    <TabsTrigger value="replace">URL替换</TabsTrigger>
                    <TabsTrigger value="patterns">常见模式</TabsTrigger>
                    <TabsTrigger value="validate">验证工具</TabsTrigger>
                </TabsList>

                {/* URL替换 */}
                <TabsContent value="replace" className="space-y-4">
                    <Card>
                        <CardHeader>
                            <CardTitle className="flex items-center gap-2">
                                <Replace className="h-5 w-5"/>
                                URL替换工具
                            </CardTitle>
                            <CardDescription>
                                批量替换数据库中的URL（类似WordPress的Search Replace DB）
                            </CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            {/* 搜索和替换输入 */}
                            <div className="grid gap-4 md:grid-cols-2">
                                <div>
                                    <Label htmlFor="search">搜索字符串 *</Label>
                                    <Input
                                        id="search"
                                        value={searchUrl}
                                        onChange={(e) => setSearchUrl(e.target.value)}
                                        placeholder="http://old-domain.com"
                                    />
                                </div>
                                <div>
                                    <Label htmlFor="replace">替换为 *</Label>
                                    <Input
                                        id="replace"
                                        value={replaceUrl}
                                        onChange={(e) => setReplaceUrl(e.target.value)}
                                        placeholder="https://new-domain.com"
                                    />
                                </div>
                            </div>

                            {/* 选项 */}
                            <div className="flex items-center space-x-4">
                                <div className="flex items-center space-x-2">
                                    <Checkbox
                                        id="regex"
                                        checked={useRegex}
                                        onCheckedChange={(checked) => setUseRegex(checked as boolean)}
                                    />
                                    <Label htmlFor="regex" className="text-sm">
                                        使用正则表达式
                                    </Label>
                                </div>
                                <div className="flex items-center space-x-2">
                                    <Checkbox
                                        id="case"
                                        checked={caseSensitive}
                                        onCheckedChange={(checked) => setCaseSensitive(checked as boolean)}
                                    />
                                    <Label htmlFor="case" className="text-sm">
                                        区分大小写
                                    </Label>
                                </div>
                            </div>

                            {/* 操作按钮 */}
                            <div className="flex gap-2">
                                <Button onClick={handlePreview} disabled={loading}>
                                    <Eye className="mr-2 h-4 w-4"/>
                                    {loading ? '处理中...' : '预览'}
                                </Button>
                                <Button
                                    onClick={handleExecute}
                                    disabled={loading || !previewResult}
                                    variant="destructive"
                                >
                                    <CheckCircle2 className="mr-2 h-4 w-4"/>
                                    执行替换
                                </Button>
                            </div>

                            {/* 警告提示 */}
                            <Alert>
                                <AlertTriangle className="h-4 w-4"/>
                                <AlertTitle>重要提示</AlertTitle>
                                <AlertDescription>
                                    • 执行前请务必先运行"预览"查看影响范围<br/>
                                    • 建议先备份数据库<br/>
                                    • 替换操作不可撤销（除非从备份恢复）
                                </AlertDescription>
                            </Alert>
                        </CardContent>
                    </Card>

                    {/* 预览结果 */}
                    {previewResult && (
                        <Card>
                            <CardHeader>
                                <CardTitle className="flex items-center gap-2">
                                    <List className="h-5 w-5"/>
                                    预览结果
                                </CardTitle>
                            </CardHeader>
                            <CardContent className="space-y-4">
                                {/* 总览 */}
                                <div className="grid grid-cols-3 gap-4">
                                    <div className="text-center p-4 bg-blue-50 dark:bg-blue-950 rounded-lg">
                                        <p className="text-2xl font-bold text-blue-600">
                                            {previewResult.tables_processed}
                                        </p>
                                        <p className="text-xs text-muted-foreground">处理的表</p>
                                    </div>
                                    <div className="text-center p-4 bg-green-50 dark:bg-green-950 rounded-lg">
                                        <p className="text-2xl font-bold text-green-600">
                                            {previewResult.total_replacements}
                                        </p>
                                        <p className="text-xs text-muted-foreground">匹配项</p>
                                    </div>
                                    <div className="text-center p-4 bg-purple-50 dark:bg-purple-950 rounded-lg">
                                        <p className="text-2xl font-bold text-purple-600">
                                            {previewResult.dry_run ? '预览' : '已执行'}
                                        </p>
                                        <p className="text-xs text-muted-foreground">模式</p>
                                    </div>
                                </div>

                                {/* 详细报告 */}
                                {previewResult.table_reports?.length > 0 && (
                                    <div>
                                        <h4 className="font-medium mb-2">详细报告：</h4>
                                        <ScrollArea className="h-[300px] border rounded-lg p-4">
                                            <div className="space-y-2">
                                                {previewResult.table_reports.map((report: any, idx: number) => (
                                                    report.replacements > 0 && (
                                                        <div key={idx} className="p-3 bg-muted rounded">
                                                            <div className="flex items-center justify-between mb-2">
                                                                <span className="font-medium">{report.table}</span>
                                                                <Badge>{report.replacements} 处</Badge>
                                                            </div>
                                                            {report.column_details?.map((col: any, colIdx: number) => (
                                                                <div key={colIdx}
                                                                     className="text-sm text-muted-foreground ml-4">
                                                                    • {col.column}: {col.replacements} 处
                                                                </div>
                                                            ))}
                                                        </div>
                                                    )
                                                ))}
                                            </div>
                                        </ScrollArea>
                                    </div>
                                )}

                                {/* 警告 */}
                                {previewResult.warnings?.length > 0 && (
                                    <Alert variant="destructive">
                                        <XCircle className="h-4 w-4"/>
                                        <AlertTitle>警告</AlertTitle>
                                        <AlertDescription>
                                            <ul className="list-disc list-inside">
                                                {previewResult.warnings.map((warning: string, idx: number) => (
                                                    <li key={idx}>{warning}</li>
                                                ))}
                                            </ul>
                                        </AlertDescription>
                                    </Alert>
                                )}
                            </CardContent>
                        </Card>
                    )}
                </TabsContent>

                {/* 常见模式 */}
                <TabsContent value="patterns" className="space-y-4">
                    <Card>
                        <CardHeader>
                            <CardTitle className="flex items-center gap-2">
                                <Code className="h-5 w-5"/>
                                常见替换模式
                            </CardTitle>
                            <CardDescription>
                                点击模式自动填充搜索和替换字段
                            </CardDescription>
                        </CardHeader>
                        <CardContent>
                            {!commonPatterns ? (
                                <Button onClick={loadCommonPatterns} variant="outline">
                                    加载常见模式
                                </Button>
                            ) : (
                                <div className="space-y-4">
                                    {Object.entries(commonPatterns).map(([key, category]: [string, any]) => (
                                        <div key={key}>
                                            <h3 className="font-medium mb-2 flex items-center gap-2">
                                                {category.name}
                                                <Badge variant="secondary">{category.examples.length}</Badge>
                                            </h3>
                                            <p className="text-sm text-muted-foreground mb-3">
                                                {category.description}
                                            </p>
                                            <div className="space-y-2">
                                                {category.examples.map((example: any, idx: number) => (
                                                    <div
                                                        key={idx}
                                                        className="p-3 border rounded-lg hover:bg-muted cursor-pointer transition-colors"
                                                        onClick={() => applyPattern(
                                                            example.search,
                                                            example.replace,
                                                            example.use_regex || false
                                                        )}
                                                    >
                                                        <div className="flex items-center justify-between mb-1">
                                                            <code className="text-sm bg-muted px-2 py-1 rounded">
                                                                {example.search}
                                                            </code>
                                                            <span className="text-muted-foreground">→</span>
                                                            <code className="text-sm bg-muted px-2 py-1 rounded">
                                                                {example.replace}
                                                            </code>
                                                        </div>
                                                        <p className="text-xs text-muted-foreground">
                                                            {example.note}
                                                        </p>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </CardContent>
                    </Card>
                </TabsContent>

                {/* 验证工具 */}
                <TabsContent value="validate" className="space-y-4">
                    <Card>
                        <CardHeader>
                            <CardTitle className="flex items-center gap-2">
                                <Info className="h-5 w-5"/>
                                URL验证工具
                            </CardTitle>
                            <CardDescription>
                                检查数据库中是否包含指定的URL
                            </CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <div className="grid gap-4 md:grid-cols-2">
                                <div>
                                    <Label htmlFor="old-url">旧URL</Label>
                                    <Input
                                        id="old-url"
                                        value={searchUrl}
                                        onChange={(e) => setSearchUrl(e.target.value)}
                                        placeholder="http://old-domain.com"
                                    />
                                </div>
                                <div>
                                    <Label htmlFor="new-url">新URL</Label>
                                    <Input
                                        id="new-url"
                                        value={replaceUrl}
                                        onChange={(e) => setReplaceUrl(e.target.value)}
                                        placeholder="https://new-domain.com"
                                    />
                                </div>
                            </div>

                            <Button onClick={handleValidate} disabled={loading}>
                                <Search className="mr-2 h-4 w-4"/>
                                {loading ? '验证中...' : '验证'}
                            </Button>

                            {/* 验证结果 */}
                            {validationResult && (
                                <div className="space-y-4">
                                    <Alert>
                                        <CheckCircle2 className="h-4 w-4"/>
                                        <AlertTitle>验证结果</AlertTitle>
                                        <AlertDescription>
                                            找到 {validationResult.samples_found} 个包含旧URL的位置
                                        </AlertDescription>
                                    </Alert>

                                    {validationResult.samples?.length > 0 && (
                                        <ScrollArea className="h-[400px] border rounded-lg p-4">
                                            <div className="space-y-3">
                                                {validationResult.samples.map((sample: any, idx: number) => (
                                                    <div key={idx} className="p-3 bg-muted rounded">
                                                        <div className="flex items-center gap-2 mb-2">
                                                            <Badge variant="outline">{sample.table}</Badge>
                                                            <span className="text-sm text-muted-foreground">
                                                                {sample.column}
                                                            </span>
                                                        </div>
                                                        <div className="space-y-1">
                                                            {sample.samples.map((s: string, sIdx: number) => (
                                                                <div key={sIdx}
                                                                     className="text-xs font-mono bg-background p-2 rounded overflow-x-auto">
                                                                    {s}
                                                                </div>
                                                            ))}
                                                        </div>
                                                    </div>
                                                ))}
                                            </div>
                                        </ScrollArea>
                                    )}
                                </div>
                            )}
                        </CardContent>
                    </Card>
                </TabsContent>
            </Tabs>
        </div>
    );
}
