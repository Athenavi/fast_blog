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
        } catch (error) {
            console.error('[Yjs Collaboration] Save error:', error);
            alert('保存失败，请重试');
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
                </div>

                {onSave && (
                    <Button
                        variant="default"
                        size="sm"
                        onClick={handleSave}
                    >
                        <Save className="w-4 h-4 mr-1"/>
                        保存
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
                <p>提示: 多个用户可以同时编辑，所有更改会自动同步</p>
            </div>
        </Card>
    );
}

// 主组件
export function YjsCollaborativeEditor({
                                           documentId,
                                           articleId,
                                           token,
                                           onSave,
                                           readOnly = false,
                                       }: CollaborativeEditorProps) {
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

        const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsHost = process.env.NEXT_PUBLIC_WS_URL || `${wsProtocol}//localhost:9421`;
        const wsUrl = `${wsHost}/api/v1/collaboration/ws/${documentId}?token=${token}&article_id=${articleId || ''}`;

        console.log('[Yjs Collaboration] Connecting to:', wsUrl);

        const ws = new WebSocket(wsUrl);
        wsRef.current = ws;

        ws.onopen = () => {
            console.log('[Yjs Collaboration] Connected');
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
                console.log('[Yjs Collaboration] Received:', message.type);

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
                            alert('文档保存成功！');
                        } else {
                            alert('保存失败，请重试');
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
            console.error('[Yjs Collaboration] WebSocket error:', error);
        };

        ws.onclose = () => {
            console.log('[Yjs Collaboration] Disconnected');
            setIsConnected(false);
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
