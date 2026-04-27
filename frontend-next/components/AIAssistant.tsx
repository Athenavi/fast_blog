'use client';

import React, {useState} from 'react';
import {Card, CardContent, CardHeader, CardTitle} from '@/components/ui/card';
import {Button} from '@/components/ui/button';
import {ScrollArea} from '@/components/ui/scroll-area';
import {Check, Copy, Expand, FileText, Languages, Loader2, Minimize2, Sparkles, Wand2, X} from 'lucide-react';
import {aiWritingService} from '@/lib/ai-writing-service';
import {useToast} from '@/hooks/use-toast';

interface AIAssistantProps {
    selectedText: string;
    context?: string;
    onInsert: (text: string) => void;
    onReplace: (text: string) => void;
    onClose: () => void;
}

type AIAction = 'complete' | 'rewrite' | 'expand' | 'summarize' | 'translate' | 'titles';

export default function AIAssistant({
                                        selectedText,
                                        context = '',
                                        onInsert,
                                        onReplace,
                                        onClose
                                    }: AIAssistantProps) {
    const {toast} = useToast();
    const [activeAction, setActiveAction] = useState<AIAction | null>(null);
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState<string>('');
    const [copied, setCopied] = useState(false);

    const actions: { id: AIAction; label: string; icon: React.ReactNode; description: string }[] = [
        {
            id: 'complete',
            label: '智能补全',
            icon: <Sparkles className="w-4 h-4"/>,
            description: '根据上下文预测后续内容'
        },
        {
            id: 'rewrite',
            label: '重写优化',
            icon: <Wand2 className="w-4 h-4"/>,
            description: '改进表达方式和语气'
        },
        {
            id: 'expand',
            label: '扩展内容',
            icon: <Expand className="w-4 h-4"/>,
            description: '基于要点生成详细内容'
        },
        {
            id: 'summarize',
            label: '生成摘要',
            icon: <Minimize2 className="w-4 h-4"/>,
            description: '提取关键信息生成摘要'
        },
        {
            id: 'translate',
            label: '翻译',
            icon: <Languages className="w-4 h-4"/>,
            description: '翻译成其他语言'
        },
        {
            id: 'titles',
            label: '生成标题',
            icon: <FileText className="w-4 h-4"/>,
            description: '基于内容生成标题建议'
        },
    ];

    const handleAction = async (action: AIAction) => {
        setActiveAction(action);
        setLoading(true);
        setResult('');

        try {
            let output = '';

            switch (action) {
                case 'complete':
                    output = await aiWritingService.completeText(context || selectedText);
                    break;
                case 'rewrite':
                    output = await aiWritingService.rewriteText(selectedText);
                    break;
                case 'expand':
                    output = await aiWritingService.expandText(selectedText);
                    break;
                case 'summarize':
                    output = await aiWritingService.summarizeText(selectedText);
                    break;
                case 'translate':
                    output = await aiWritingService.translateText(selectedText, 'en');
                    break;
                case 'titles':
                    const titles = await aiWritingService.generateTitles(context || selectedText);
                    output = titles.map((t, i) => `${i + 1}. ${t}`).join('\n');
                    break;
            }

            setResult(output);
        } catch (error) {
            toast({
                title: 'AI助手错误',
                description: error instanceof Error ? error.message : '操作失败',
                variant: 'destructive'
            });
        } finally {
            setLoading(false);
        }
    };

    const handleCopy = () => {
        navigator.clipboard.writeText(result);
        setCopied(true);
        toast({
            title: '已复制',
            description: '结果已复制到剪贴板'
        });
        setTimeout(() => setCopied(false), 2000);
    };

    const handleInsert = () => {
        onInsert(result);
        toast({
            title: '已插入',
            description: 'AI生成的内容已插入到文档中'
        });
        onClose();
    };

    const handleReplace = () => {
        onReplace(result);
        toast({
            title: '已替换',
            description: '原文已被AI生成的内容替换'
        });
        onClose();
    };

    return (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
            <Card className="w-full max-w-2xl max-h-[80vh] flex flex-col">
                <CardHeader className="border-b">
                    <div className="flex items-center justify-between">
                        <CardTitle className="flex items-center gap-2">
                            <Sparkles className="w-5 h-5 text-purple-600"/>
                            AI写作助手
                        </CardTitle>
                        <Button variant="ghost" size="sm" onClick={onClose}>
                            <X className="w-4 h-4"/>
                        </Button>
                    </div>
                </CardHeader>

                <CardContent className="flex-1 overflow-hidden flex flex-col p-0">
                    {/* 选中的文本 */}
                    {selectedText && (
                        <div className="p-4 border-b bg-gray-50 dark:bg-gray-900">
                            <div className="text-xs font-semibold text-gray-500 dark:text-gray-400 mb-2">
                                选中的文本：
                            </div>
                            <div className="text-sm text-gray-700 dark:text-gray-300 line-clamp-3">
                                {selectedText}
                            </div>
                        </div>
                    )}

                    {/* 操作按钮 */}
                    <div className="p-4 border-b">
                        <div className="text-xs font-semibold text-gray-500 dark:text-gray-400 mb-3">
                            选择操作：
                        </div>
                        <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                            {actions.map((action) => (
                                <Button
                                    key={action.id}
                                    variant={activeAction === action.id ? 'default' : 'outline'}
                                    size="sm"
                                    onClick={() => handleAction(action.id)}
                                    disabled={loading}
                                    className="h-auto py-3 px-4 flex flex-col items-start gap-1"
                                >
                                    <div className="flex items-center gap-2">
                                        {action.icon}
                                        <span className="font-medium">{action.label}</span>
                                    </div>
                                    <span className="text-xs text-left opacity-70">
                                        {action.description}
                                    </span>
                                </Button>
                            ))}
                        </div>
                    </div>

                    {/* 结果显示 */}
                    <div className="flex-1 overflow-hidden flex flex-col">
                        <div className="p-4 border-b flex items-center justify-between">
                            <div className="text-xs font-semibold text-gray-500 dark:text-gray-400">
                                AI生成结果：
                            </div>
                            {result && (
                                <div className="flex gap-2">
                                    <Button
                                        size="sm"
                                        variant="outline"
                                        onClick={handleCopy}
                                        className="gap-2"
                                    >
                                        {copied ? (
                                            <>
                                                <Check className="w-4 h-4"/>
                                                已复制
                                            </>
                                        ) : (
                                            <>
                                                <Copy className="w-4 h-4"/>
                                                复制
                                            </>
                                        )}
                                    </Button>
                                    <Button
                                        size="sm"
                                        variant="outline"
                                        onClick={handleInsert}
                                        className="gap-2"
                                    >
                                        插入
                                    </Button>
                                    <Button
                                        size="sm"
                                        onClick={handleReplace}
                                        className="gap-2"
                                    >
                                        替换原文
                                    </Button>
                                </div>
                            )}
                        </div>

                        <ScrollArea className="flex-1 p-4">
                            {loading ? (
                                <div className="flex items-center justify-center h-32">
                                    <div className="text-center">
                                        <Loader2 className="w-8 h-8 animate-spin text-purple-600 mx-auto mb-2"/>
                                        <p className="text-sm text-gray-500">AI正在思考中...</p>
                                    </div>
                                </div>
                            ) : result ? (
                                <div className="prose prose-sm dark:prose-invert max-w-none">
                                    <pre className="whitespace-pre-wrap font-sans text-sm">
                                        {result}
                                    </pre>
                                </div>
                            ) : (
                                <div className="flex items-center justify-center h-32 text-gray-400">
                                    <div className="text-center">
                                        <Sparkles className="w-12 h-12 mx-auto mb-2 opacity-30"/>
                                        <p className="text-sm">选择一个操作开始使用AI助手</p>
                                    </div>
                                </div>
                            )}
                        </ScrollArea>
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}
