'use client';

import React, {useEffect, useRef, useState} from 'react';
import {EditorContent, useEditor} from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import {Card} from '@/components/ui/card';
import {Badge} from '@/components/ui/badge';
import {Button} from '@/components/ui/button';
import {Save, Users, Wifi, WifiOff} from 'lucide-react';
import {getSaveDocumentUrl, getWebSocketUrl} from '@/lib/collaboration-config';

// 从 cookie 获取 token 的工具函数
const getTokenFromCookie = (): string => {
    if (typeof document === 'undefined') return '';
    const cookies = document.cookie.split(';');
    for (const cookie of cookies) {
        const [name, value] = cookie.trim().split('=');
        if (name === 'access_token') {
            return decodeURIComponent(value);
        }
    }
    return '';
};

interface CollaborativeEditorProps {
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

export default function CollaborativeEditor({
                                                documentId,
                                                articleId,
                                                token: propToken,
                                                onSave,
                                                readOnly = false,
                                            }: CollaborativeEditorProps) {
    const [token, setToken] = useState<string>(propToken || '');
    const [awarenessUsers, setAwarenessUsers] = useState<Array<{
        client_id?: string;
        name?: string;
        color?: string;
    }>>([]);
    const [isConnected, setIsConnected] = useState(false);
    const [isSaving, setIsSaving] = useState(false);
    const [lastSaved, setLastSaved] = useState<Date | null>(null);
    const [saveStatus, setSaveStatus] = useState<'idle' | 'saving' | 'success' | 'error'>('idle');
    const [version, setVersion] = useState<number>(0);
    const [reconnectAttempts, setReconnectAttempts] = useState<number>(0);
    const [errorMessage, setErrorMessage] = useState<string>('');

    const wsRef = useRef<WebSocket | null>(null);
    const clientIdRef = useRef<string>('');
    const isRemoteUpdate = useRef<boolean>(false);
    const reconnectTimerRef = useRef<NodeJS.Timeout | null>(null);

    // 在客户端初始化时获取 token
    useEffect(() => {
        if (!propToken && typeof window !== 'undefined') {
            const tokenValue = getTokenFromCookie() || localStorage.getItem('access_token') || '';
            setToken(tokenValue);
        } else if (propToken) {
            setToken(propToken);
        }
    }, [propToken]);

    // 初始化编辑器
    const editor = useEditor({
        extensions: [
            StarterKit.configure({
                history: true, // 启用历史记录
            }),
        ],
        editable: !readOnly,
        immediatelyRender: false,
        autofocus: 'end',
        onUpdate: ({editor}) => {
            // 本地编辑时发送步骤到服务器
            if (!isRemoteUpdate.current && wsRef.current?.readyState === WebSocket.OPEN) {
                const content = editor.getHTML();

                // 简化的步骤：发送完整内容而非增量
                wsRef.current.send(JSON.stringify({
                    type: 'send_steps',
                    steps: [{
                        stepType: 'replace',
                        data: {content},
                        version: version
                    }],
                    content: content,
                    clientID: clientIdRef.current
                }));
            }
            isRemoteUpdate.current = false;
        },
    });

    // 初始化WebSocket连接
    useEffect(() => {
        if (!editor || !token) return;

        const connectWebSocket = () => {
            const wsUrl = getWebSocketUrl(documentId, articleId);
            console.log('[Collab] Connecting to:', wsUrl);

            const ws = new WebSocket(wsUrl);
            wsRef.current = ws;

            ws.onopen = () => {
                console.log('[Collab] ✓ Connected successfully');
                setIsConnected(true);
                setReconnectAttempts(0); // 重置重连计数
                setErrorMessage(''); // 清除错误信息
            };

            ws.onmessage = (event) => {
                try {
                    const message = JSON.parse(event.data);
                    console.log('[Collab] Received:', message.type);

                    switch (message.type) {
                        case 'welcome':
                            clientIdRef.current = message.client_id;
                            setVersion(message.version || 0);

                            // 设置初始内容
                            if (message.content && editor) {
                                isRemoteUpdate.current = true;
                                editor.commands.setContent(message.content);
                            }

                            console.log('[Collab] Client ID:', clientIdRef.current);
                            break;

                        case 'receive_steps':
                            // 接收远程步骤
                            if (message.steps && message.steps.length > 0 && editor) {
                                isRemoteUpdate.current = true;
                                const newContent = message.steps[0].data?.content;
                                if (newContent) {
                                    editor.commands.setContent(newContent);
                                }
                                setVersion(message.version || 0);
                            }
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
                            console.log('[Collab] User count:', message.client_count);
                            break;

                        case 'save_result':
                            if (message.success) {
                                setSaveStatus('success');
                                setLastSaved(new Date());
                                setTimeout(() => setSaveStatus('idle'), 3000);
                            } else {
                                setSaveStatus('error');
                                setTimeout(() => setSaveStatus('idle'), 5000);
                            }
                            break;

                        case 'auto_save':
                            if (message.success) {
                                console.log('[Collab] Auto-saved');
                                setSaveStatus('success');
                                setLastSaved(new Date());
                                setTimeout(() => setSaveStatus('idle'), 2000);
                            }
                            break;

                        case 'pong':
                            // 心跳响应
                            break;
                    }
                } catch (error) {
                    console.error('[Collab] Message parse error:', error);
                }
            };

            ws.onerror = (error) => {
                console.error('[Collab] ✗ WebSocket error:', error);
            };

            ws.onclose = (event) => {
                console.log('[Collab] Disconnected - Code:', event.code, 'Reason:', event.reason || 'No reason');
                setIsConnected(false);

                // 清除之前的重连定时器
                if (reconnectTimerRef.current) {
                    clearTimeout(reconnectTimerRef.current);
                }

                // 自动重连（除非是正常关闭或认证失败）
                if (event.code !== 1000 && event.code !== 1001 && event.code !== 4001) {
                    // 指数退避重连策略：3s, 6s, 12s, 最多30s
                    const delay = Math.min(3000 * Math.pow(2, reconnectAttempts), 30000);
                    console.log(`[Collab] Attempting to reconnect in ${delay / 1000}s... (Attempt ${reconnectAttempts + 1})`);

                    reconnectTimerRef.current = setTimeout(() => {
                        setReconnectAttempts(prev => prev + 1);
                        if (editor) {
                            connectWebSocket();
                        }
                    }, delay);
                } else if (event.code === 4001) {
                    setErrorMessage('认证失败，请重新登录');
                    console.error('[Collab] Authentication failed. Please check your token.');
                } else {
                    setReconnectAttempts(0); // 重置重连计数
                }
            };

            // 发送心跳
            const pingInterval = setInterval(() => {
                if (ws.readyState === WebSocket.OPEN) {
                    ws.send(JSON.stringify({type: 'ping'}));
                }
            }, 30000);

            return () => {
                clearInterval(pingInterval);
                if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {
                    ws.close();
                }
            };
        };

        const cleanup = connectWebSocket();
        return () => {
            if (cleanup) cleanup();
            // 清除重连定时器
            if (reconnectTimerRef.current) {
                clearTimeout(reconnectTimerRef.current);
            }
        };
    }, [documentId, articleId, token, editor]);

    // 保存文档 - 带重试机制
    const handleSave = async (retryCount: number = 0) => {
        if (!editor) {
            setErrorMessage('编辑器未初始化');
            return;
        }

        setIsSaving(true);
        setSaveStatus('saving');
        const content = editor.getHTML();

        try {
            const url = getSaveDocumentUrl(documentId);

            const response = await fetch(url, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                credentials: 'include',
                body: JSON.stringify({
                    content,
                    change_summary: '协作编辑保存'
                }),
            });

            if (!response.ok) {
                throw new Error(`Save failed: ${response.status} ${response.statusText}`);
            }

            const data = await response.json();
            console.log('[Collab] Save successful:', data);
            setSaveStatus('success');
            setLastSaved(new Date());
            setErrorMessage('');
            setTimeout(() => setSaveStatus('idle'), 3000);
        } catch (error) {
            console.error('[Collab] Save error:', error);

            // 重试逻辑：最多重试3次
            if (retryCount < 3) {
                const retryDelay = 1000 * (retryCount + 1); // 1s, 2s, 3s
                console.log(`[Collab] Retrying save in ${retryDelay}ms... (Attempt ${retryCount + 1}/3)`);

                setTimeout(async () => {
                    await handleSave(retryCount + 1);
                }, retryDelay);
            } else {
                setSaveStatus('error');
                const errorMsg = error instanceof Error ? error.message : '保存失败';
                setErrorMessage(errorMsg);
                console.error('[Collab] Save failed after 3 retries');
                setTimeout(() => setSaveStatus('idle'), 5000);
            }
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

            {/* 编辑器内容 */}
            <div className="border rounded-lg p-4 min-h-[400px]">
                <EditorContent editor={editor}/>
            </div>

            {/* 在线用户列表 */}
            {awarenessUsers.length > 0 && (
                <div className="mt-4 flex items-center gap-2">
                    <span className="text-sm text-gray-500">在线用户:</span>
                    {awarenessUsers.map((user, index) => (
                        <div
                            key={user.client_id || index}
                            className="w-8 h-8 rounded-full flex items-center justify-center text-white text-xs font-bold"
                            style={{backgroundColor: user.color || getRandomColor(user.client_id || '')}}
                            title={user.name || `User ${user.client_id?.slice(-4)}`}
                        >
                            {(user.name || 'U').charAt(0).toUpperCase()}
                        </div>
                    ))}
                </div>
            )}
        </Card>
    );
}
