'use client';

import React, {useEffect, useRef, useState} from 'react';
import {Card} from '@/components/ui/card';
import {Badge} from '@/components/ui/badge';
import {getWebSocketUrl} from '@/lib/collaboration-config';

interface CollaborativeMarkdownEditorProps {
    documentId: string;
    articleId?: number;
    readOnly?: boolean;
}

// 协作文档编辑器 - 直接使用 SimpleMDE
export default function CollaborativeMarkdownEditor({
                                                        documentId,
                                                        articleId,
                                                        readOnly = false,
                                                    }: CollaborativeMarkdownEditorProps) {
    const [isConnected, setIsConnected] = useState(false);
    const wsRef = useRef<WebSocket | null>(null);
    const versionRef = useRef<number>(0);
    const editorRef = useRef<any>(null); // SimpleMDE 实例
    const isRemoteUpdate = useRef(false);
    const textareaRef = useRef<HTMLTextAreaElement>(null);

    // 初始化 WebSocket 连接
    useEffect(() => {
        console.log('[Collab Markdown] Connecting with documentId:', documentId);

        try {
            const getTokenFromCookie = (): string | null => {
                if (typeof document === 'undefined') return null;
                const cookies = document.cookie.split(';');
                for (const cookie of cookies) {
                    const [name, value] = cookie.trim().split('=');
                    if (name === 'access_token') {
                        return decodeURIComponent(value);
                    }
                }
                return null;
            };

            const token = getTokenFromCookie();
            const wsUrl = getWebSocketUrl(documentId, token || undefined);
            console.log('[Collab Markdown] WebSocket URL:', wsUrl);
            console.log('[Collab Markdown] Token present:', !!token);

            const ws = new WebSocket(wsUrl);
            wsRef.current = ws;

            ws.onopen = () => {
                console.log('[Collab Markdown] Connected');
                setIsConnected(true);
            };

            ws.onclose = (event) => {
                console.log('[Collab Markdown] Disconnected, code:', event.code, 'reason:', event.reason);
                setIsConnected(false);

                // 检查是否是重复连接的错误
                if (event.code === 4009) {
                    alert('您已有一个进行中的协作');
                    // 可以选择关闭页面或重定向
                    window.close();
                }
            };

            ws.onerror = (err) => {
                console.error('[Collab Markdown] Error:', err);
            };

            ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    console.log('[Collab Markdown] Received:', data.type);

                    if (data.type === 'init') {
                        if (data.content !== undefined && data.content !== null) {
                            console.log('[Collab Markdown] Setting initial content, length:', data.content.length);
                            if (editorRef.current) {
                                editorRef.current.value(data.content);
                            }
                        }
                        versionRef.current = data.version || 0;
                    } else if (data.type === 'receive_steps') {
                        if (data.steps && data.steps.length > 0) {
                            const step = data.steps[0];
                            console.log('[Collab Markdown] Received step from other user');

                            if (step.data && step.data.content) {
                                console.log('[Collab Markdown] Updating content, length:', step.data.content.length);
                                isRemoteUpdate.current = true;

                                if (editorRef.current) {
                                    // 保存光标位置
                                    const cm = editorRef.current.codemirror;
                                    const cursor = cm.getCursor();
                                    console.log('[Collab Markdown] Cursor position saved:', cursor);

                                    // 设置新内容
                                    editorRef.current.value(step.data.content);
                                    console.log('[Collab Markdown] Content updated');

                                    // 恢复光标位置（如果可能）
                                    try {
                                        cm.setCursor(cursor);
                                        console.log('[Collab Markdown] Cursor restored');
                                    } catch (e) {
                                        console.log('[Collab Markdown] Could not restore cursor:', e);
                                    }
                                } else {
                                    console.log('[Collab Markdown] Editor instance not available');
                                }

                                isRemoteUpdate.current = false;
                                console.log('[Collab Markdown] Remote update completed');
                            }
                        }
                        if (data.version) {
                            versionRef.current = data.version;
                        }
                    }
                } catch (error) {
                    console.error('[Collab Markdown] Message parse error:', error);
                }
            };

            return () => {
                console.log('[Collab Markdown] Cleaning up...');
                if (ws.readyState === WebSocket.OPEN) {
                    ws.close();
                }
            };
        } catch (error) {
            console.error('[Collab Markdown] Initialization failed:', error);
        }
    }, [documentId]);

    // 初始化 SimpleMDE 编辑器
    useEffect(() => {
        if (!textareaRef.current || editorRef.current) return;

        const loadEasyMDE = async () => {
            try {
                // 加载 CSS
                if (typeof document !== 'undefined') {
                    const existingLink = document.getElementById('easymde-css');
                    if (!existingLink) {
                        const link = document.createElement('link');
                        link.id = 'easymde-css';
                        link.rel = 'stylesheet';
                        link.href = 'https://cdn.jsdelivr.net/npm/easymde/dist/easymde.min.css';
                        document.head.appendChild(link);
                    }
                }

                // 动态导入 EasyMDE
                const EasyMDE = await import('easymde').then(m => m.default);

                const editor = new EasyMDE({
                    element: textareaRef.current!,
                    autofocus: false,
                    placeholder: '开始协作编辑...',
                    spellChecker: false,
                    status: ['autosave', 'lines', 'words'],
                    minHeight: '400px',
                    sideBySideFullscreen: false,
                    toolbar: [
                        'bold', 'italic', 'heading', '|',
                        'code', 'quote', 'unordered-list', 'ordered-list', '|',
                        'link', 'image', '|',
                        'preview', 'side-by-side', 'fullscreen', '|',
                        'guide'
                    ],
                    autoRefresh: {delay: 300},
                    inputStyle: 'textarea',
                    lineWrapping: true,
                });

                editorRef.current = editor;

                // 监听内容变化
                editor.codemirror.on('change', () => {
                    console.log('[Collab Markdown] CodeMirror change event triggered');

                    if (isRemoteUpdate.current) {
                        console.log('[Collab Markdown] Remote update in progress, skip sending');
                        return;
                    }

                    const ws = wsRef.current;
                    if (!ws || ws.readyState !== WebSocket.OPEN) {
                        console.log('[Collab Markdown] WebSocket not ready');
                        return;
                    }

                    const newContent = editor.value();
                    console.log('[Collab Markdown] Content changed, length:', newContent.length);

                    versionRef.current += 1;

                    const step = {
                        stepType: 'replace',
                        data: {content: newContent},
                        clientID: 'current_user',
                        version: versionRef.current
                    };

                    const message = {
                        type: 'step',
                        step: step,
                        content: newContent
                    };

                    console.log('[Collab Markdown] Sending step, version:', versionRef.current);
                    ws.send(JSON.stringify(message));
                });

                // 设置只读模式
                if (readOnly) {
                    editor.codemirror.setOption('readOnly', true);
                }

            } catch (error) {
                console.error('[Collab Markdown] Failed to load EasyMDE:', error);
            }
        };

        loadEasyMDE();

        return () => {
            if (editorRef.current) {
                editorRef.current.toTextArea();
                editorRef.current = null;
            }
        };
    }, [readOnly]);

    return (
        <Card className="p-4">
            <div className="mb-4 flex items-center justify-between">
                <div>
                    <h3 className="font-semibold">协作文档编辑器（Markdown）</h3>
                    <p className="text-sm text-gray-600">文档ID: {documentId}</p>
                    <p className="text-sm text-gray-600">只读模式: {readOnly ? '是' : '否'}</p>
                </div>
                <div className="flex items-center gap-2">
                    {isConnected ? (
                        <Badge variant="default">已连接</Badge>
                    ) : (
                        <Badge variant="destructive">未连接</Badge>
                    )}
                </div>
            </div>
            <div className="border rounded min-h-[400px]">
                <textarea ref={textareaRef}></textarea>
            </div>
        </Card>
    );
}
