'use client';

import React, {useCallback, useEffect, useRef, useState} from 'react';
import {useCollaboration} from '@/hooks/useCollaboration';
import {Card} from '@/components/ui/card';
import {Badge} from '@/components/ui/badge';
import {Button} from '@/components/ui/button';
import {RefreshCw, Save, Users, Wifi, WifiOff} from 'lucide-react';

interface CollaborativeEditorProps {
    documentId: string;
    userId?: number;
    userName?: string;
    token?: string;
    initialContent?: string;
    onSave?: (content: string) => Promise<void>;
    readOnly?: boolean;
}

export function CollaborativeEditor({
                                        documentId,
                                        token,
                                        initialContent = '',
                                        onSave,
                                        readOnly = false,
                                    }: CollaborativeEditorProps) {
    const [localContent, setLocalContent] = useState(initialContent);
    const textareaRef = useRef<HTMLTextAreaElement>(null);
    const lastSelectionRef = useRef<{ start: number; end: number } | null>(null);

    const {
        isConnected,
        content,
        remoteCursors,
        clientCount,
        clientId,
        sendOperation,
        updateCursor,
        requestSync,
    } = useCollaboration({
        documentId,
        token,
        onContentChange: (newContent) => {
            setLocalContent(newContent);
        },
    });

    // 当远程内容变化时更新本地内容
    useEffect(() => {
        if (content !== localContent) {
            setLocalContent(content);
        }
    }, [content]);

    // 处理文本变化
    const handleTextChange = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
        const newText = e.target.value;
        const oldText = localContent;

        // 计算差异并发送操作
        if (newText.length > oldText.length) {
            // 插入操作
            const position = findInsertPosition(oldText, newText);
            const insertedText = newText.slice(position, position + (newText.length - oldText.length));

            sendOperation({
                type: 'insert',
                position,
                text: insertedText,
            });
        } else if (newText.length < oldText.length) {
            // 删除操作
            const position = findDeletePosition(oldText, newText);
            const deletedLength = oldText.length - newText.length;

            sendOperation({
                type: 'delete',
                position,
                length: deletedLength,
            });
        }

        setLocalContent(newText);
    }, [localContent, sendOperation]);

    // 查找插入位置
    const findInsertPosition = (oldText: string, newText: string): number => {
        for (let i = 0; i < Math.min(oldText.length, newText.length); i++) {
            if (oldText[i] !== newText[i]) {
                return i;
            }
        }
        return oldText.length;
    };

    // 查找删除位置
    const findDeletePosition = (oldText: string, newText: string): number => {
        for (let i = 0; i < newText.length; i++) {
            if (oldText[i] !== newText[i]) {
                return i;
            }
        }
        return newText.length;
    };

    // 处理光标/选区变化
    const handleSelect = useCallback(() => {
        const textarea = textareaRef.current;
        if (!textarea) return;

        const selection = {
            start: textarea.selectionStart,
            end: textarea.selectionEnd,
        };

        lastSelectionRef.current = selection;
        updateCursor(selection.start, selection);
    }, [updateCursor]);

    // 保存文档
    const handleSave = async () => {
        if (onSave) {
            try {
                await onSave(localContent);
            } catch (error) {
                console.error('Failed to save document:', error);
            }
        }
    };

    // 渲染远程光标
    const renderRemoteCursors = () => {
        if (!textareaRef.current) return null;

        const cursors: React.JSX.Element[] = [];
        remoteCursors.forEach((remoteCursor, id) => {
            if (id === clientId) return; // 不显示自己的光标

            const cursorStyle = {
                position: 'absolute' as const,
                left: `${(remoteCursor.cursor.position % 50) * 8}px`, // 简化计算
                top: `${Math.floor(remoteCursor.cursor.position / 50) * 20}px`,
                width: '2px',
                height: '20px',
                backgroundColor: remoteCursor.color || '#FF6B6B',
                pointerEvents: 'none' as const,
                zIndex: 10,
            };

            cursors.push(
                <div key={id} style={cursorStyle}>
                    <div
                        style={{
                            position: 'absolute',
                            top: '-20px',
                            left: '0',
                            backgroundColor: remoteCursor.color || '#FF6B6B',
                            color: 'white',
                            padding: '2px 6px',
                            borderRadius: '4px',
                            fontSize: '10px',
                            whiteSpace: 'nowrap' as const,
                        }}
                    >
                        User {id.slice(-4)}
                    </div>
                </div>
            );
        });

        return cursors;
    };

    return (
        <Card className="p-4">
            {/* 工具栏 */}
            <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                    {isConnected ? (
                        <Badge variant="default" className="gap-1">
                            <Wifi className="w-3 h-3"/>
                            已连接
                        </Badge>
                    ) : (
                        <Badge variant="destructive" className="gap-1">
                            <WifiOff className="w-3 h-3"/>
                            未连接
                        </Badge>
                    )}

                    <Badge variant="secondary" className="gap-1">
                        <Users className="w-3 h-3"/>
                        {clientCount} 人在线
                    </Badge>
                </div>

                <div className="flex gap-2">
                    <Button
                        variant="outline"
                        size="sm"
                        onClick={requestSync}
                        disabled={!isConnected}
                    >
                        <RefreshCw className="w-4 h-4 mr-1"/>
                        同步
                    </Button>

                    {onSave && (
                        <Button
                            variant="default"
                            size="sm"
                            onClick={handleSave}
                            disabled={!isConnected}
                        >
                            <Save className="w-4 h-4 mr-1"/>
                            保存
                        </Button>
                    )}
                </div>
            </div>

            {/* 编辑器区域 */}
            <div className="relative">
        <textarea
            ref={textareaRef}
            value={localContent}
            onChange={handleTextChange}
            onSelect={handleSelect}
            onKeyUp={handleSelect}
            onClick={handleSelect}
            readOnly={readOnly}
            className="w-full min-h-[400px] p-4 border rounded-lg font-mono text-sm resize-y focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="开始编辑..."
        />

                {/* 远程光标层 */}
                <div className="absolute inset-0 pointer-events-none">
                    {renderRemoteCursors()}
                </div>
            </div>

            {/* 状态信息 */}
            <div className="mt-4 text-xs text-gray-500">
                <p>文档ID: {documentId}</p>
                <p>客户端ID: {clientId}</p>
            </div>
        </Card>
    );
}
