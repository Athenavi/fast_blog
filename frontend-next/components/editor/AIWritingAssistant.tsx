import React, {useCallback, useEffect, useRef, useState} from 'react';
import {Button} from '@/components/ui/button';
import {Card, CardContent, CardHeader, CardTitle} from '@/components/ui/card';
import {Badge} from '@/components/ui/badge';
import {ScrollArea} from '@/components/ui/scroll-area';
import {CheckCircle2, Copy, FileText, ListChecks, Loader2, PenTool, RefreshCw, Sparkles, Wand2, X} from 'lucide-react';
import {useToast} from '@/hooks/use-toast';
import {getConfig} from '@/lib/config';

interface AIFeature {
    id: string;
    name: string;
    icon: React.ReactNode;
    description: string;
    endpoint: string;
    method: 'POST' | 'GET';
}

interface AIWritingAssistantProps {
    editorInstance: any;
    selectedText: string;
    fullText: string;
    cursorPosition: { line: number; ch: number };
    onClose: () => void;
    onInsert: (text: string) => void;
}

const aiFeatures: AIFeature[] = [
    {
        id: 'continue',
        name: '智能续写',
        icon: <Sparkles className="w-4 h-4"/>,
        description: '基于上下文智能续写内容',
        endpoint: '/api/v2/ai/writing/continue',
        method: 'POST',
    },
    {
        id: 'polish',
        name: '文本润色',
        icon: <PenTool className="w-4 h-4"/>,
        description: '优化文本表达，提升可读',
        endpoint: '/api/v2/ai/writing/polish',
        method: 'POST',
    },
    {
        id: 'grammar',
        name: '语法检',
        icon: <CheckCircle2 className="w-4 h-4"/>,
        description: '检测并修正语法错误',
        endpoint: '/api/v2/ai/writing/check-grammar',
        method: 'POST',
    },
    {
        id: 'style-formal',
        name: '转为正式风格',
        icon: <FileText className="w-4 h-4"/>,
        description: '转换为专业正式的写作风格',
        endpoint: '/api/v2/ai/writing/transform-style',
        method: 'POST',
    },
    {
        id: 'style-casual',
        name: '转为随意风格',
        icon: <FileText className="w-4 h-4"/>,
        description: '转换为轻松随意的写作风格',
        endpoint: '/api/v2/ai/writing/transform-style',
        method: 'POST',
    },
    {
        id: 'style-concise',
        name: '精简内容',
        icon: <ListChecks className="w-4 h-4"/>,
        description: '去除冗余，使内容更简',
        endpoint: '/api/v2/ai/writing/transform-style',
        method: 'POST',
    },
];

export default function AIWritingAssistant({
                                               editorInstance,
                                               selectedText,
                                               fullText,
                                               cursorPosition,
                                               onClose,
                                               onInsert,
                                           }: AIWritingAssistantProps) {
    const [loading, setLoading] = useState<string | null>(null);
    const [result, setResult] = useState<string>('');
    const [issues, setIssues] = useState<any[]>([]);
    const {toast} = useToast();
    const resultRef = useRef<HTMLDivElement>(null);

    // 执行 AI 功能
    const executeFeature = useCallback(async (feature: AIFeature) => {
        setLoading(feature.id);
        setResult('');
        setIssues([]);

        try {
            let response;
            let data;

            // 获取 API 配置
            const config = getConfig();
            const apiUrl = `${config.API_BASE_URL}${feature.endpoint}`;

            if (feature.id === 'continue') {
                // 智能续写 - 使用光标前的文本作为上下文
                const textBeforeCursor = getTextBeforeCursor(fullText, cursorPosition);
                response = await fetch(apiUrl, {
                    method: feature.method,
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        text: textBeforeCursor || fullText,
                        max_length: 200,
                    }),
                });

                // 检查响应状态
                if (!response.ok) {
                    const errorText = await response.text();
                    console.error('API Error:', response.status, errorText);
                    throw new Error(`API 请求失败 (${response.status}): ${errorText.substring(0, 200)}`);
                }

                data = await response.json();

                if (data.success) {
                    setResult(data.data.continuation);
                }
            } else if (feature.id === 'grammar') {
                // 语法检查
                const requestBody = {
                    text: selectedText || fullText,
                };
                console.log('[AI Assistant] Grammar check request:', requestBody);

                response = await fetch(apiUrl, {
                    method: feature.method,
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(requestBody),
                });

                if (!response.ok) {
                    const errorText = await response.text();
                    console.error('API Error:', response.status, errorText);
                    throw new Error(`API 请求失败 (${response.status}): ${errorText.substring(0, 200)}`);
                }

                data = await response.json();

                if (data.success) {
                    setIssues(data.data.issues || []);
                    setResult(data.data.issues?.length === 0 ? '✓ 未发现语法问题' : `发现 ${data.data.count} 个问题`);
                }
            } else if (feature.id.startsWith('style-')) {
                // 风格转换
                const styleMap: Record<string, string> = {
                    'style-formal': 'formal',
                    'style-casual': 'casual',
                    'style-concise': 'concise',
                };

                response = await fetch(apiUrl, {
                    method: feature.method,
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        text: selectedText || fullText,
                        target_style: styleMap[feature.id] || 'formal',
                    }),
                });

                if (!response.ok) {
                    const errorText = await response.text();
                    console.error('API Error:', response.status, errorText);
                    throw new Error(`API 请求失败 (${response.status}): ${errorText.substring(0, 200)}`);
                }

                data = await response.json();

                if (data.success) {
                    setResult(data.data.transformed);
                }
            } else {
                // 其他功能（如润色）
                const requestBody = {
                    text: selectedText || fullText,
                };
                console.log('[AI Assistant] Polish request:', requestBody);

                response = await fetch(apiUrl, {
                    method: feature.method,
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(requestBody),
                });

                if (!response.ok) {
                    const errorText = await response.text();
                    console.error('API Error:', response.status, errorText);
                    throw new Error(`API 请求失败 (${response.status}): ${errorText.substring(0, 200)}`);
                }

                data = await response.json();

                if (data.success) {
                    setResult(data.data.polished || data.data.result || '');
                }
            }

            if (!data?.success) {
                throw new Error(data?.error || 'AI 服务调用失败');
            }
        } catch (error) {
            console.error('AI feature error:', error);
            toast({
                title: '错误',
                description: error instanceof Error ? error.message : 'AI 服务调用失败',
                variant: 'destructive',
            });
        } finally {
            setLoading(null);
        }
    }, [selectedText, fullText, cursorPosition, toast]);

    // 获取光标前的文本
    const getTextBeforeCursor = (text: string, cursor: { line: number; ch: number }) => {
        const lines = text.split('\n');
        let beforeText = '';

        for (let i = 0; i < cursor.line; i++) {
            beforeText += lines[i] + '\n';
        }
        beforeText += lines[cursor.line].substring(0, cursor.ch);

        return beforeText;
    };

    // 复制结果到剪贴板
    const copyToClipboard = useCallback(() => {
        navigator.clipboard.writeText(result);
        toast({
            title: '已复制',
            description: '结果已复制到剪贴板',
        });
    }, [result, toast]);

    // 插入结果到编辑器
    const insertResult = useCallback(() => {
        if (result) {
            onInsert(result);
            onClose();
        }
    }, [result, onInsert, onClose]);

    // 替换选中的文本
    const replaceSelection = useCallback(() => {
        if (result && selectedText) {
            onInsert(result);
            onClose();
        }
    }, [result, selectedText, onInsert, onClose]);

    // 滚动到结果区域
    useEffect(() => {
        if (result && resultRef.current) {
            resultRef.current.scrollIntoView({behavior: 'smooth'});
        }
    }, [result]);

    return (
        <Card className="w-full max-w-2xl shadow-lg">
            <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        <Wand2 className="w-5 h-5 text-purple-500"/>
                        <CardTitle className="text-lg">AI 写作助手</CardTitle>
                    </div>
                    <Button
                        variant="ghost"
                        size="sm"
                        onClick={onClose}
                        className="h-8 w-8 p-0"
                    >
                        <X className="w-4 h-4"/>
                    </Button>
                </div>
            </CardHeader>

            <CardContent className="space-y-4">
                {/* 功能选择 */}
                <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                    {aiFeatures.map((feature) => (
                        <Button
                            key={feature.id}
                            variant={loading === feature.id ? 'default' : 'outline'}
                            size="sm"
                            onClick={() => executeFeature(feature)}
                            disabled={loading !== null}
                            className="h-auto py-2 px-3 flex flex-col items-start gap-1"
                        >
                            <div className="flex items-center gap-2">
                                {feature.icon}
                                <span className="text-sm font-medium">{feature.name}</span>
                            </div>
                            <span className="text-xs text-muted-foreground text-left w-full truncate">
                {feature.description}
              </span>
                        </Button>
                    ))}
                </div>

                {/* 加载状态 */}
                {loading && (
                    <div className="flex items-center justify-center py-8">
                        <Loader2 className="w-6 h-6 animate-spin text-purple-500 mr-2"/>
                        <span className="text-sm text-muted-foreground">AI 正在处理中...</span>
                    </div>
                )}

                {/* 结果显示 */}
                {(result || issues.length > 0) && !loading && (
                    <div ref={resultRef} className="space-y-3">
                        <div className="flex items-center justify-between">
                            <Badge variant="secondary" className="text-xs">
                                AI 生成结果
                            </Badge>
                            <div className="flex gap-2">
                                <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={copyToClipboard}
                                    className="h-7 px-2"
                                >
                                    <Copy className="w-3 h-3 mr-1"/>
                                    <span className="text-xs">复制</span>
                                </Button>
                                {selectedText && (
                                    <Button
                                        variant="outline"
                                        size="sm"
                                        onClick={replaceSelection}
                                        className="h-7 px-2"
                                    >
                                        <RefreshCw className="w-3 h-3 mr-1"/>
                                        <span className="text-xs">替换选中</span>
                                    </Button>
                                )}
                                <Button
                                    variant="default"
                                    size="sm"
                                    onClick={insertResult}
                                    className="h-7 px-2 bg-purple-600 hover:bg-purple-700"
                                >
                                    <span className="text-xs">插入到光标处</span>
                                </Button>
                            </div>
                        </div>

                        {/* 语法检查结果 */}
                        {issues.length > 0 && (
                            <ScrollArea className="h-48 rounded-md border p-3">
                                <div className="space-y-2">
                                    {issues.map((issue, index) => (
                                        <div key={index} className="text-sm space-y-1">
                                            <div className="flex items-start gap-2">
                                                <Badge variant="destructive" className="text-xs">
                                                    问题 {index + 1}
                                                </Badge>
                                                <span className="font-medium">{issue.message}</span>
                                            </div>
                                            {issue.suggestion && (
                                                <div className="text-muted-foreground ml-16">
                                                    建议：{issue.suggestion}
                                                </div>
                                            )}
                                        </div>
                                    ))}
                                </div>
                            </ScrollArea>
                        )}

                        {/* 文本结果 */}
                        {result && issues.length === 0 && (
                            <ScrollArea className="h-48 rounded-md border p-3 bg-gray-50 dark:bg-gray-900">
                <pre className="whitespace-pre-wrap text-sm font-mono">
                  {result}
                </pre>
                            </ScrollArea>
                        )}
                    </div>
                )}

                {/* 提示信息 */}
                {!result && !loading && issues.length === 0 && (
                    <div className="text-center py-8 text-muted-foreground text-sm">
                        <Wand2 className="w-8 h-8 mx-auto mb-2 opacity-50"/>
                        <p>选择一个功能开始使用 AI 写作助手</p>
                        {selectedText && (
                            <p className="text-xs mt-1">已选中 {selectedText.length} 个字符</p>
                        )}
                    </div>
                )}
            </CardContent>
        </Card>
    );
}
