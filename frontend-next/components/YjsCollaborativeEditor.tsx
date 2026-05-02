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
    '#958DF1',
    '#F98181',
    '#FBBC88',
    '#FAF594',
    '#70CFF8',
    '#94FADB',
    '#B9F18D',
];

// 获取随机颜色
const getRandomColor = (clientId: string) => {
    let hash = 0;
    for (let i = 0; i < clientId.length; i++) {
        hash = clientId.charCodeAt(i) + ((hash << 5) - hash);
    }
    return USER_COLORS[Math.abs(hash) % USER_COLORS.length];
};

// EditorWithYjs 组件 - 独立的组件，确保 Hooks 调用顺序一致
interface EditorWithYjsProps {
    ydoc: Y.Doc;
    isConnected: boolean;
    awarenessUsers: Array<{ client_id?: string; name?: string; color?: string }>;
    documentId: string;
    articleId?: number;
    readOnly: boolean;
    onSave?: (content: string) => Promise<void>;
    wsRef: React.MutableRefObject<WebSocket | null>;
    clientIdRef: React.MutableRefObject<string>;
}

function EditorWithYjs({
                           ydoc,
                           isConnected,
                           awarenessUsers,
                           documentId,
                           articleId,
                           readOnly,
                           onSave,
                           wsRef,
                           clientIdRef,
                       }: EditorWithYjsProps) {
    const [isSaving, setIsSaving] = useState(false);
    const [lastSaved, setLastSaved] = useState<Date | null>(null);
    const [saveStatus, setSaveStatus] = useState<'idle' | 'saving' | 'success' | 'error'>('idle');
    // 初始化TipTap编辑器 - ydoc 一定存在
    const editor = useEditor({
        extensions: [
            StarterKit.configure({
                history: false,
            }),
            Collaboration.configure({
                document: ydoc,
            }),
            // 暂时禁用 CollaborationCursor，因为我们使用自定义的光标管理
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

    // 如果还未连接,显示加载状态
    if (!isConnected) {
        return (
            <Card className="p-4">
                <div className="flex items-center justify-center min-h-[400px]">
                    <div className="text-center">
                        <div
                            className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900 mx-auto mb-2"></div>
                        <p className="text-sm text-gray-500">正在连接协作服务器...</p>
                    </div>
                </div>
            </Card>
        );
    }

    if (!editor) {
        return (
            <Card className="p-4">
                <div className="flex items-center justify-center min-h-[400px]">
                    <p className="text-sm text-gray-500">编辑器初始化中...</p>
                </div>
            </Card>
        );
    }

    // 保存文档
    const handleSave = async () => {
        if (!editor || !wsRef.current) return;

        setIsSaving(true);
        setSaveStatus('saving');
        const content = editor.getHTML();

        try {
            const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:9421';
            const url = `${baseUrl}/api/v1/collaboration/document/${documentId}/save`;

            const response = await fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                credentials: 'include',
                body: JSON.stringify({
                    content,
                    change_summary: '协作编辑保存'
                }),
            });

            if (!response.ok) {
                throw new Error(`Save failed: ${response.status}`);
            }

            const data = await response.json();
            console.log('[Yjs Collaboration] Save successful:', data);
            setSaveStatus('success');
            setLastSaved(new Date());

            // 3秒后重置状态
            setTimeout(() => {
                setSaveStatus('idle');
            }, 3000);
        } catch (error) {
            console.error('[Yjs Collaboration] Save error:', error);
            setSaveStatus('error');
            alert('保存失败，请重试');

            // 5秒后重置状态
            setTimeout(() => {
                setSaveStatus('idle');
            }, 5000);
        } finally {
            setIsSaving(false);
        }
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
                        {awarenessUsers.length + 1} 人在线
                    </Badge>

                    {/* 保存状态指示器 */}
                    {saveStatus === 'saving' && (
                        <Badge variant="outline" className="gap-1">
                            <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-gray-900"></div>
                            保存中...
                        </Badge>
                    )}
                    {saveStatus === 'success' && (
                        <Badge variant="default" className="gap-1 bg-green-500">
                            ✓ 已保存
                        </Badge>
                    )}
                    {saveStatus === 'error' && (
                        <Badge variant="destructive" className="gap-1">
                            ✗ 保存失败
                        </Badge>
                    )}
                </div>

                {onSave && (
                    <Button
                        variant="default"
                        size="sm"
                        onClick={handleSave}
                        disabled={isSaving || !isConnected}
                    >
                        <Save className="w-4 h-4 mr-1"/>
                        {isSaving ? '保存中...' : '保存'}
                    </Button>
                )}
            </div>

            {/* 在线用户列表 */}
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
                <p>文档ID: {documentId}</p>
                {articleId && <p>文章ID: {articleId}</p>}
                {lastSaved && <p>最后保存: {lastSaved.toLocaleTimeString()}</p>}
                <p>提示: 多个用户可以同时编辑，所有更改会自动同步</p>
                <p>自动保存: 每30秒自动保存一次</p>
            </div>
        </Card>
    );
}

// 主组件
export function YjsCollaborativeEditor({
                                           documentId,
                                           articleId,
                                           token: propToken,
                                           onSave,
                                           readOnly = false,
                                       }: CollaborativeEditorProps) {
    // 优先使用传入的token，否则从 cookie 或 localStorage 获取
    const [token, setToken] = useState<string>(propToken || '');

    // 在客户端初始化时获取 token
    useEffect(() => {
        if (!propToken && typeof window !== 'undefined') {
            console.log('[Yjs Collaboration] === Token Debug Start ===');

            // 优先从 cookie 获取
            let tokenValue = getTokenFromCookie();
            console.log('[Yjs Collaboration] Token from cookie:', tokenValue ? `Found (${tokenValue.substring(0, 20)}...)` : 'Not found');

            // 如果 cookie 中没有，尝试从 localStorage 获取
            if (!tokenValue) {
                tokenValue = localStorage.getItem('access_token') || '';
                console.log('[Yjs Collaboration] Token from localStorage:', tokenValue ? `Found (${tokenValue.substring(0, 20)}...)` : 'Not found');
            }

            // 检查所有 cookies
            console.log('[Yjs Collaboration] All cookies:', document.cookie);
            console.log('[Yjs Collaboration] Final token value:', tokenValue ? `Set (${tokenValue.length} chars)` : 'Empty');
            console.log('[Yjs Collaboration] === Token Debug End ===');

            setToken(tokenValue);
        } else if (propToken) {
            console.log('[Yjs Collaboration] Using propToken:', propToken ? `Provided (${propToken.length} chars)` : 'Empty');
            setToken(propToken);
        }
    }, []); // 移除 propToken 依赖，避免不必要的重新渲染
    const [awarenessUsers, setAwarenessUsers] = useState<Array<{
        client_id?: string;
        name?: string;
        color?: string
    }>>([]);
    const [isConnected, setIsConnected] = useState(false);
    const [ydoc, setYdoc] = useState<Y.Doc | null>(null);
    const wsRef = useRef<WebSocket | null>(null);
    const clientIdRef = useRef<string>('');

    // 初始化Yjs文档
    useEffect(() => {
        const doc = new Y.Doc();
        setYdoc(doc);

        return () => {
            doc.destroy();
        };
    }, []);

    // 初始化WebSocket连接并集成Yjs
    useEffect(() => {
        if (!ydoc) return;

        // 检查必要参数
        if (!token) {
            console.error('[Yjs Collaboration] Token is missing!');
            setIsConnected(false);
            return;
        }

        const connectWebSocket = () => {
            const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:9421';
            const wsProtocol = baseUrl.startsWith('https') ? 'wss:' : 'ws:';
            const wsHost = baseUrl.replace(/^https?:\/\//, '');
            // 不再需要传递 token，后端会从 cookie 自动读取
            const wsUrl = `${wsProtocol}//${wsHost}/api/v1/collaboration/ws/${documentId}?article_id=${articleId || ''}`;

            console.log('[Yjs Collaboration] Connecting to:', wsUrl);
            console.log('[Yjs Collaboration] Document ID:', documentId);
            console.log('[Yjs Collaboration] Article ID:', articleId);
            console.log('[Yjs Collaboration] Token will be read from cookie by backend');

            const ws = new WebSocket(wsUrl);
            wsRef.current = ws;

            ws.onopen = () => {
                console.log('[Yjs Collaboration] ✓ Connected successfully');
                setIsConnected(true);
            };

            ws.onmessage = (event) => {
                try {
                    // 检查是否是二进制数据（Yjs更新）
                    if (event.data instanceof ArrayBuffer || event.data instanceof Uint8Array) {
                        const update = new Uint8Array(event.data);
                        Y.applyUpdate(ydoc, update);
                        return;
                    }

                    // 处理JSON消息
                    const message = JSON.parse(typeof event.data === 'string' ? event.data : new TextDecoder().decode(event.data));
                    console.log('[Yjs Collaboration] Received message type:', message.type);

                    switch (message.type) {
                        case 'welcome':
                            clientIdRef.current = message.client_id;
                            console.log('[Yjs Collaboration] Client ID:', clientIdRef.current);

                            // 如果有初始状态，应用它
                            if (message.state && message.state.content) {
                                const ytext = ydoc.getText('content');
                                ytext.delete(0, ytext.length);
                                ytext.insert(0, message.state.content);
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
                            console.log('[Yjs Collaboration] User count:', message.client_count);
                            break;

                        case 'save_result':
                            if (message.success) {
                                setSaveStatus('success');
                                setLastSaved(new Date());
                                setTimeout(() => {
                                    setSaveStatus('idle');
                                }, 3000);
                            } else {
                                setSaveStatus('error');
                                setTimeout(() => {
                                    setSaveStatus('idle');
                                }, 5000);
                            }
                            break;

                        case 'auto_save':
                            // 自动保存通知
                            if (message.success) {
                                console.log('[Yjs Collaboration] Auto-saved');
                                setSaveStatus('success');
                                setLastSaved(new Date());
                                setTimeout(() => {
                                    setSaveStatus('idle');
                                }, 2000);
                            }
                            break;

                        case 'pong':
                            // 心跳响应
                            break;
                    }
                } catch (error) {
                    console.error('[Yjs Collaboration] Message parse error:', error);
                }
            };

            ws.onerror = (error) => {
                console.error('[Yjs Collaboration] ✗ WebSocket error:', error);
                console.error('[Yjs Collaboration] ReadyState:', ws.readyState);
            };

            ws.onclose = (event) => {
                console.log('[Yjs Collaboration] Disconnected - Code:', event.code, 'Reason:', event.reason || 'No reason provided');
                setIsConnected(false);

                // 自动重连（除非是正常关闭或认证失败）
                if (event.code !== 1000 && event.code !== 1001 && event.code !== 4001) {
                    console.log('[Yjs Collaboration] Attempting to reconnect in 3 seconds...');
                    setTimeout(() => {
                        if (ydoc) {
                            connectWebSocket();
                        }
                    }, 3000);
                } else if (event.code === 4001) {
                    console.error('[Yjs Collaboration] Authentication failed. Please check your token.');
                }
            };

            // 监听Yjs文档更新并发送到服务器
            const updateHandler = (update: Uint8Array) => {
                if (ws.readyState === WebSocket.OPEN) {
                    ws.send(update);
                }
            };

            ydoc.on('update', updateHandler);

            return () => {
                ydoc.off('update', updateHandler);
                if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {
                    ws.close();
                }
            };
        };

        const cleanup = connectWebSocket();
        return cleanup;
    }, [documentId, articleId, token]);

    // 如果 ydoc 还未初始化，显示加载状态
    if (!ydoc) {
        return (
            <Card className="p-4">
                <div className="flex items-center justify-center min-h-[400px]">
                    <div className="text-center">
                        <div
                            className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900 mx-auto mb-2"></div>
                        <p className="text-sm text-gray-500">正在初始化编辑器...</p>
                    </div>
                </div>
            </Card>
        );
    }

    // 如果没有token，显示错误提示
    if (!token) {
        return (
            <Card className="p-4">
                <div className="flex items-center justify-center min-h-[400px]">
                    <div className="text-center">
                        <div className="text-red-500 text-4xl mb-4">⚠️</div>
                        <p className="text-sm text-red-600 font-semibold mb-2">未登录或Token已过期</p>
                        <p className="text-xs text-gray-500 mb-4">请先登录后再使用协作编辑功能</p>
                        <p className="text-xs text-gray-400">Document ID: {documentId}</p>
                    </div>
                </div>
            </Card>
        );
    }

    // ydoc 已准备好，渲染编辑器组件
    return (
        <EditorWithYjs
            ydoc={ydoc}
            isConnected={isConnected}
            awarenessUsers={awarenessUsers}
            documentId={documentId}
            articleId={articleId}
            readOnly={readOnly}
            onSave={onSave}
            wsRef={wsRef}
            clientIdRef={clientIdRef}
        />
    );
}
