'use client';

import React, {useEffect, useRef, useState} from 'react';
import {EditorContent, useEditor} from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import Collaboration from '@tiptap/extension-collaboration';
import * as Y from 'yjs';
import {Card} from '@/components/ui/card';
import {Badge} from '@/components/ui/badge';
import {Button} from '@/components/ui/button';
import {Save, Users, Wifi, WifiOff} from 'lucide-react';
import {getSaveDocumentUrl, getYjsWebSocketUrl} from '@/lib/collaboration-config';

interface YjsCollaborativeEditorProps {
    documentId: string;
    articleId?: number;
    token?: string;
    onSave?: (content: string) => Promise<void>;
    readOnly?: boolean;
}

// 用户颜色列表
const USER_COLORS = [
    '#958DF1', '#F98181', '#FBBC88', '#FAF594', '#70CFF8', '#94FADB', '#B9F18D',
];

const getRandomColor = (clientId: string) => {
    let hash = 0;
    for (let i = 0; i < clientId.length; i++) {
        hash = clientId.charCodeAt(i) + ((hash << 5) - hash);
    }
    return USER_COLORS[Math.abs(hash) % USER_COLORS.length];
};

export default function YjsCollaborativeEditor({
                                                   documentId,
                                                   articleId,
                                                   token: propToken,
                                                   onSave,
                                                   readOnly = false,
                                               }: YjsCollaborativeEditorProps) {
    const [awarenessUsers, setAwarenessUsers] = useState<Array<{
        client_id?: string;
        name?: string;
        color?: string;
    }>>([]);
    const [isConnected, setIsConnected] = useState(false);
    const [isSaving, setIsSaving] = useState(false);
    const [lastSaved, setLastSaved] = useState<Date | null>(null);
    const [saveStatus, setSaveStatus] = useState<'idle' | 'saving' | 'success' | 'error'>('idle');
    const [errorMessage, setErrorMessage] = useState<string>('');
    const [reconnectAttempts, setReconnectAttempts] = useState<number>(0);

    const wsRef = useRef<WebSocket | null>(null);
    const clientIdRef = useRef<string>('');
    const reconnectTimerRef = useRef<NodeJS.Timeout | null>(null);

    // 初始化 Yjs 文档
    const [ydoc] = useState(() => new Y.Doc());

    // 初始化 TipTap 编辑器（集成 Yjs）
    const editor = useEditor({
        extensions: [
            StarterKit.configure({
                history: false, // 禁用历史记录，使用 Yjs 的历史
            }),
            Collaboration.configure({
                document: ydoc,
            }),
            // 暂时禁用 CollaborationCursor，等待 clientId 设置后再启用
            // CollaborationCursor.configure({
            //     provider: null,
            //     user: {
            //         name: `User ${clientIdRef.current?.slice(-4) || 'Unknown'}`,
            //         color: getRandomColor(clientIdRef.current || 'default'),
            //     },
            // }),
        ],
        editable: !readOnly,
        immediatelyRender: false,
        autofocus: 'end',
    });

    // 保存 editor 引用（必须在 editor 声明之后）
    const editorRef = useRef(editor);

    // 初始化 WebSocket 连接 - 当 editor 就绪时执行
    useEffect(() => {
        console.log('[Yjs Editor] useEffect triggered, editor:', !!editor, 'documentId:', documentId);

        if (!editor) {
            console.log('[Yjs Editor] Editor not ready yet, skipping WebSocket connection');
            return;
        }

        console.log('[Yjs Editor] Editor is ready, starting WebSocket connection...');

        const connectWebSocket = () => {
            const wsUrl = getYjsWebSocketUrl(documentId, articleId);
            console.log('[Yjs Editor] ====== WebSocket Connection Start ======');
            console.log('[Yjs Editor] Document ID:', documentId);
            console.log('[Yjs Editor] Article ID:', articleId);
            console.log('[Yjs Editor] WebSocket URL:', wsUrl);

            const ws = new WebSocket(wsUrl);
            wsRef.current = ws;

            ws.onopen = () => {
                console.log('[Yjs Editor] ✓ Connected successfully');
                setIsConnected(true);
                setReconnectAttempts(0);
                setErrorMessage('');
            };

            ws.onmessage = (event) => {
                try {
                    // 检查是否是二进制数据（Yjs 更新）
                    if (event.data instanceof ArrayBuffer || event.data instanceof Uint8Array) {
                        const update = new Uint8Array(event.data);
                        Y.applyUpdate(ydoc, update);
                        return;
                    }

                    // 处理 Blob 类型的二进制数据
                    if (event.data instanceof Blob) {
                        event.data.arrayBuffer().then((buffer: ArrayBuffer) => {
                            const update = new Uint8Array(buffer);
                            Y.applyUpdate(ydoc, update);
                        });
                        return;
                    }

                    // 处理 JSON 消息（字符串类型）
                    if (typeof event.data === 'string') {
                        const message = JSON.parse(event.data);

                        switch (message.type) {
                            case 'welcome':
                                clientIdRef.current = message.client_id;
                                console.log('[Yjs Editor] Client ID:', clientIdRef.current);
                                break;

                            case 'awareness':
                                // 更新感知状态
                                if (message.state) {
                                    setAwarenessUsers(prev => {
                                        const exists = prev.find(u => u.client_id === message.state.client_id);
                                        if (exists) {
                                            return prev.map(u =>
                                                u.client_id === message.state.client_id ? message.state : u
                                            );
                                        } else {
                                            return [...prev, message.state];
                                        }
                                    });
                                }
                                break;

                            case 'user_joined':
                            case 'user_left':
                                console.log('[Yjs Editor] User count:', message.client_count);
                                break;

                            case 'save_result':
                                if (message.success) {
                                    setSaveStatus('success');
                                    setLastSaved(new Date());
                                    setTimeout(() => setSaveStatus('idle'), 3000);
                                } else {
                                    setSaveStatus('error');
                                    setErrorMessage(message.message || '保存失败');
                                    setTimeout(() => setSaveStatus('idle'), 5000);
                                }
                                break;

                            case 'pong':
                                // 心跳响应
                                break;
                        }
                    }
                } catch (error) {
                    console.error('[Yjs Editor] Message parse error:', error);
                }
            };

            ws.onerror = (error) => {
                console.error('[Yjs Editor] ✗ WebSocket error:', error);
                console.error('[Yjs Editor] ReadyState:', ws.readyState);
                console.error('[Yjs Editor] URL:', ws.url);
            };

            ws.onclose = (event) => {
                console.log('[Yjs Editor] Disconnected - Code:', event.code, 'Reason:', event.reason || 'No reason');
                setIsConnected(false);

                // 清除之前的重连定时器
                if (reconnectTimerRef.current) {
                    clearTimeout(reconnectTimerRef.current);
                }

                // 自动重连（除非是正常关闭）
                if (event.code !== 1000 && event.code !== 1001) {
                    const delay = Math.min(3000 * Math.pow(2, reconnectAttempts), 30000);
                    console.log(`[Yjs Editor] Reconnecting in ${delay / 1000}s... (Attempt ${reconnectAttempts + 1})`);

                    reconnectTimerRef.current = setTimeout(() => {
                        setReconnectAttempts(prev => prev + 1);
                        connectWebSocket();
                    }, delay);
                }
            };

            // 监听 Yjs 文档更新并发送到服务器
            const updateHandler = (update: Uint8Array, origin: any) => {
                // 如果是来自 WebSocket 的更新，不需要再发送回去
                if (origin === ws) return;

                if (ws.readyState === WebSocket.OPEN) {
                    ws.send(update);
                }
            };

            ydoc.on('update', updateHandler);

            // 发送心跳
            const pingInterval = setInterval(() => {
                if (ws.readyState === WebSocket.OPEN) {
                    ws.send(JSON.stringify({type: 'ping'}));
                }
            }, 30000);

            return () => {
                ydoc.off('update', updateHandler);
                clearInterval(pingInterval);
                if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {
                    ws.close();
                }
            };
        };

        const cleanup = connectWebSocket();
        return () => {
            if (cleanup) cleanup();
            if (reconnectTimerRef.current) {
                clearTimeout(reconnectTimerRef.current);
            }
        };
    }, [documentId, articleId, ydoc, editor]); // 添加 editor 依赖，当 editor 就绪时重新执行

    // 保存文档
    const handleSave = async () => {
        if (!editor) {
            setErrorMessage('编辑器未初始化');
            return;
        }

        setIsSaving(true);
        setSaveStatus('saving');
        const content = editor.getHTML();

        try {
            const url = getSaveDocumentUrl(documentId);

            // 从 cookie 获取 token
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
            const headers: Record<string, string> = {
                'Content-Type': 'application/json',
            };

            if (token) {
                headers['Authorization'] = `Bearer ${token}`;
            }

            const response = await fetch(url, {
                method: 'POST',
                headers,
                credentials: 'include',
                body: JSON.stringify({
                    content,
                    change_summary: 'Yjs 协作编辑保存'
                }),
            });

            if (!response.ok) {
                throw new Error(`Save failed: ${response.status} ${response.statusText}`);
            }

            const data = await response.json();
            console.log('[Yjs Editor] Save successful:', data);
            setSaveStatus('success');
            setLastSaved(new Date());
            setErrorMessage('');
            setTimeout(() => setSaveStatus('idle'), 3000);
        } catch (error) {
            console.error('[Yjs Editor] Save error:', error);
            setSaveStatus('error');
            const errorMsg = error instanceof Error ? error.message : '保存失败';
            setErrorMessage(errorMsg);
            setTimeout(() => setSaveStatus('idle'), 5000);
        } finally {
            setIsSaving(false);
        }
    };

    if (!editor) {
        return (
            <Card className="p-4">
                <div className="flex items-center justify-center min-h-[400px]">
                    <p className="text-sm text-gray-500">编辑器初始化中...</p>
                </div>
            </Card>
        );
    }

    return (
        <Card className="p-4">
            {/* 工具栏 */}
            <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                    {isConnected ? (
                        <Badge variant="default" className="gap-1">
                            <Wifi className="w-3 h-3"/>
                            已连接 (Yjs)
                        </Badge>
                    ) : (
                        <Badge variant="destructive" className="gap-1">
                            <WifiOff className="w-3 h-3"/>
                            未连接
                        </Badge>
                    )}

                    <Badge variant="secondary" className="gap-1">
                        <Users className="w-3 h-3"/>
                        {awarenessUsers.length + 1} 人在线
                    </Badge>

                    {saveStatus === 'saving' && (
                        <Badge variant="outline" className="gap-1">
                            <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-current"></div>
                            保存中...
                        </Badge>
                    )}

                    {saveStatus === 'success' && (
                        <Badge variant="outline" className="gap-1 text-green-600">
                            <Save className="w-3 h-3"/>
                            已保存
                        </Badge>
                    )}

                    {lastSaved && (
                        <span className="text-xs text-gray-500">
                            最后保存: {lastSaved.toLocaleTimeString()}
                        </span>
                    )}
                </div>

                <Button onClick={handleSave} disabled={isSaving || !isConnected} size="sm">
                    <Save className="w-4 h-4 mr-2"/>
                    保存
                </Button>
            </div>

            {/* 错误提示 */}
            {errorMessage && (
                <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
                    <p className="text-sm text-red-600">{errorMessage}</p>
                </div>
            )}

            {/* 在线用户光标 */}
            {awarenessUsers.length > 0 && (
                <div className="flex items-center gap-2 mb-4 flex-wrap">
                    {awarenessUsers.map((state, index) => (
                        <div
                            key={index}
                            className="flex items-center gap-1 px-2 py-1 rounded text-xs"
                            style={{
                                backgroundColor: (state.color || '#958DF1') + '20',
                                color: state.color || '#958DF1',
                            }}
                        >
                            <div
                                className="w-2 h-2 rounded-full"
                                style={{backgroundColor: state.color || '#958DF1'}}
                            />
                            {state.name || `User ${state.client_id?.slice(-4)}`}
                        </div>
                    ))}
                </div>
            )}

            {/* 编辑器区域 */}
            <div className="border rounded-lg p-4 min-h-[400px] prose max-w-none">
                <EditorContent editor={editor}/>
            </div>

            {/* 提示信息 */}
            <div className="mt-4 text-xs text-gray-500">
                <p>✓ 使用 Yjs CRDT 算法实现真正的实时协作</p>
                <p>✓ 支持离线编辑和自动合并</p>
                <p>✓ 多人同时编辑不会冲突</p>
            </div>
        </Card>
    );
}
