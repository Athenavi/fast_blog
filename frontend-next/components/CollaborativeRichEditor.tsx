'use client';

import React, {useEffect, useRef, useState} from 'react';
import {EditorContent, useEditor} from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import {Card} from '@/components/ui/card';
import {Badge} from '@/components/ui/badge';
import {Button} from '@/components/ui/button';
import {Save, Users, Wifi, WifiOff} from 'lucide-react';

interface CollaborativeEditorProps {
    documentId: string;
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

export function CollaborativeEditor({
                                        documentId,
                                        token,
                                        onSave,
                                        readOnly = false,
                                    }: CollaborativeEditorProps) {
    const [awarenessUsers, setAwarenessUsers] = useState<any[]>([]);
    const [isConnected, setIsConnected] = useState(false);
    const [editorKey, setEditorKey] = useState(0);
    const wsRef = useRef<WebSocket | null>(null);
    const clientIdRef = useRef<string>('');

    // 加载文档内容的函数
    const loadDocumentContent = async () => {
        console.log('=== [Collaboration] loadDocumentContent called ===');
        console.log('[Collaboration] editor exists:', !!editor);
        console.log('[Collaboration] documentId:', documentId);

        if (!editor) {
            console.log('[Collaboration] Editor not ready, skipping load');
            return;
        }

        try {
            const url = `http://localhost:9421/api/v1/collaboration/document/${documentId}/state`;
            console.log('[Collaboration] Fetching from URL:', url);

            const response = await fetch(url, {
                credentials: 'include',
            });

            console.log('[Collaboration] Response status:', response.status);
            console.log('[Collaboration] Response ok:', response.ok);

            if (response.ok) {
                const data = await response.json();
                console.log('[Collaboration] Full response data:', JSON.stringify(data, null, 2));

                if (data.success && data.data) {
                    const content = data.data.content || '';
                    console.log('[Collaboration] Content type:', typeof content);
                    console.log('[Collaboration] Content length:', content.length);
                    console.log('[Collaboration] Content preview:', content.substring(0, 100));

                    // 如果协作文档有内容，使用它
                    if (content) {
                        console.log('[Collaboration] Setting content to editor...');
                        editor.commands.setContent(content);
                        console.log('[Collaboration] ✓ Content successfully set to editor');
                    } else {
                        console.log('[Collaboration] Collaboration document is empty, trying to load from article...');
                        // 尝试从文章API加载
                        await loadFromArticleAPI();
                    }
                } else {
                    console.warn('[Collaboration] Response success=false or no data:', data);
                }
            } else if (response.status === 404) {
                console.log('[Collaboration] ⚠ Document not found (404), trying to load from article...');
                // 尝试从文章API加载
                await loadFromArticleAPI();
            } else {
                console.error('[Collaboration] ✗ Failed to load document, status:', response.status);
                const text = await response.text();
                console.error('[Collaboration] Error response:', text);
            }
        } catch (error) {
            console.error('[Collaboration] ✗ Exception while loading document:', error);
            if (error instanceof Error) {
                console.error('[Collaboration] Error message:', error.message);
                console.error('[Collaboration] Error stack:', error.stack);
            }
        }
        console.log('=== [Collaboration] loadDocumentContent finished ===');
    };

    // 从文章API加载内容
    const loadFromArticleAPI = async () => {
        console.log('[Collaboration] Loading from article API...');
        const articleUrl = `http://localhost:9421/api/v1/articles/${documentId}`;
        console.log('[Collaboration] Fetching from article URL:', articleUrl);

        try {
            const articleResponse = await fetch(articleUrl, {
                credentials: 'include',
            });

            console.log('[Collaboration] Article response status:', articleResponse.status);

            if (articleResponse.ok) {
                const articleData = await articleResponse.json();
                console.log('[Collaboration] Article data keys:', Object.keys(articleData));
                console.log('[Collaboration] Full article data:', JSON.stringify(articleData, null, 2));

                // 检查不同的响应格式
                let articleContent = '';

                // 尝试多种可能的路径
                if (articleData.success && articleData.data) {
                    // 路径1: data.article.content
                    if (articleData.data.article && articleData.data.article.content) {
                        articleContent = articleData.data.article.content;
                        console.log('[Collaboration] Using path: data.article.content');
                    }
                    // 路径2: data.raw_content 或 data.markdown_content
                    else if (articleData.data.raw_content) {
                        articleContent = articleData.data.raw_content;
                        console.log('[Collaboration] Using path: data.raw_content');
                    } else if (articleData.data.markdown_content) {
                        articleContent = articleData.data.markdown_content;
                        console.log('[Collaboration] Using path: data.markdown_content');
                    }
                    // 路径3: data.content
                    else if (articleData.data.content) {
                        articleContent = articleData.data.content;
                        console.log('[Collaboration] Using path: data.content');
                    }
                }
                // 直接访问 content
                else if (articleData.content) {
                    articleContent = articleData.content;
                    console.log('[Collaboration] Using path: root content');
                }

                console.log('[Collaboration] Article content length:', articleContent.length);

                if (articleContent) {
                    console.log('[Collaboration] Article content preview:', articleContent.substring(0, 200));
                    console.log('[Collaboration] Setting article content to editor...');

                    // TipTap可以直接处理HTML
                    editor?.commands.setContent(articleContent);
                    console.log('[Collaboration] ✓ Article content successfully set to editor');

                    // 将文章内容同步到协作文档服务
                    console.log('[Collaboration] Syncing content to collaboration service...');
                    await fetch(`http://localhost:9421/api/v1/collaboration/document/${documentId}/save`, {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        credentials: 'include',
                        body: JSON.stringify({content: articleContent}),
                    });
                    console.log('[Collaboration] ✓ Content synced to collaboration service');
                } else {
                    console.log('[Collaboration] ⚠ No content found in article');
                    console.log('[Collaboration] Available fields in data:', Object.keys(articleData.data || {}));
                    if (articleData.data.article) {
                        console.log('[Collaboration] Available fields in data.article:', Object.keys(articleData.data.article));
                    }
                }
            } else if (articleResponse.status === 404) {
                console.log('[Collaboration] ⚠ Article not found (404)');
            } else {
                console.error('[Collaboration] ✗ Failed to load article, status:', articleResponse.status);
                const errorText = await articleResponse.text();
                console.error('[Collaboration] Error response:', errorText);
            }
        } catch (error) {
            console.error('[Collaboration] ✗ Exception while loading from article:', error);
            if (error instanceof Error) {
                console.error('[Collaboration] Error message:', error.message);
                console.error('[Collaboration] Error stack:', error.stack);
            }
        }
    };

    // 初始化编辑器 - 必须在顶层调用
    const editor = useEditor({
        extensions: [
            StarterKit,
        ],
        editable: !readOnly,
        immediatelyRender: false,
        autofocus: 'end',
    });

    // 初始化WebSocket连接
    useEffect(() => {
        const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsHost = process.env.NEXT_PUBLIC_WS_URL || `${wsProtocol}//localhost:9421`;
        const wsUrl = `${wsHost}/api/v1/collaboration/ws/${documentId}`;

        console.log('[Collaboration] Connecting to:', wsUrl);

        const ws = new WebSocket(wsUrl);
        wsRef.current = ws;

        ws.onopen = () => {
            console.log('[Collaboration] Connected');
            setIsConnected(true);
        };

        ws.onmessage = (event) => {
            try {
                const message = JSON.parse(event.data);
                console.log('[Collaboration] Received:', message.type);

                switch (message.type) {
                    case 'welcome':
                        clientIdRef.current = message.client_id;
                        console.log('[Collaboration] Client ID:', clientIdRef.current);
                        break;
                    case 'user_joined':
                    case 'user_left':
                        // 更新在线用户数
                        console.log('[Collaboration] User count:', message.client_count);
                        break;
                    case 'remote_operation':
                        // TODO: 处理远程操作
                        console.log('[Collaboration] Remote operation from:', message.client_id);
                        break;
                    case 'cursor_update':
                        // TODO: 更新远程光标
                        break;
                }
            } catch (error) {
                console.error('[Collaboration] Message parse error:', error);
            }
        };

        ws.onerror = (error) => {
            console.error('[Collaboration] WebSocket error:', error);
        };

        ws.onclose = () => {
            console.log('[Collaboration] Disconnected');
            setIsConnected(false);
        };

        return () => {
            if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {
                ws.close();
            }
        };
    }, [documentId]);

    // 当编辑器和连接都准备好时，加载文档内容
    useEffect(() => {
        if (editor && isConnected) {
            console.log('[Collaboration] Editor and connection ready, loading document...');
            // 延迟一下确保编辑器完全初始化
            const timer = setTimeout(() => {
                loadDocumentContent();
            }, 200);
            return () => clearTimeout(timer);
        }
    }, [editor, isConnected]);

    // 获取连接状态
    const userCount = awarenessUsers.length;

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
        console.log('=== [Collaboration] handleSave called ===');

        if (!editor) {
            console.warn('[Collaboration] Editor not available');
            alert('编辑器未初始化');
            return;
        }

        const content = editor.getHTML();
        console.log('[Collaboration] Content length:', content.length);
        console.log('[Collaboration] Content preview:', content.substring(0, 100));
        
        try {
            const url = `http://localhost:9421/api/v1/collaboration/document/${documentId}/save`;
            console.log('[Collaboration] Saving to URL:', url);
            console.log('[Collaboration] Request method: POST');
            console.log('[Collaboration] Request credentials: include');

            const response = await fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                credentials: 'include',
                body: JSON.stringify({content}),
            });

            console.log('[Collaboration] Save response status:', response.status);
            console.log('[Collaboration] Save response ok:', response.ok);
                    
            if (!response.ok) {
                const errorText = await response.text();
                console.error('[Collaboration] Save failed with status:', response.status);
                console.error('[Collaboration] Error response text:', errorText);
                throw new Error(`Save failed: ${response.status} - ${errorText}`);
            }

            const data = await response.json();
            console.log('[Collaboration]  Save successful:', data);
            alert('文档保存成功!');
        } catch (error) {
            console.error('[Collaboration]  Save error:', error);
            if (error instanceof Error) {
                console.error('[Collaboration] Error name:', error.name);
                console.error('[Collaboration] Error message:', error.message);
                console.error('[Collaboration] Error stack:', error.stack);

                // 检查是否是网络错误
                if (error.message === 'Failed to fetch') {
                    console.error('[Collaboration] This is likely a CORS or network issue.');
                    console.error('[Collaboration] Please check:');
                    console.error('[Collaboration] 1. Backend server is running on http://localhost:9421');
                    console.error('[Collaboration] 2. CORS is properly configured');
                    console.error('[Collaboration] 3. Network connection is stable');
                    alert('保存失败：无法连接到服务器。请检查后端服务是否正在运行。');
                } else {
                    alert(`保存失败：${error.message}`);
                }
            } else {
                console.error('[Collaboration] Unknown error type:', error);
                alert('保存失败，发生未知错误');
            }
        }
        console.log('=== [Collaboration] handleSave finished ===');
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
                        {userCount} 人在线
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
                    {awarenessUsers.map((state: any, index: number) => (
                        <div
                            key={index}
                            className="flex items-center gap-1 px-2 py-1 rounded text-xs"
                            style={{
                                backgroundColor: state.user?.color + '20',
                                color: state.user?.color,
                            }}
                        >
                            <div
                                className="w-2 h-2 rounded-full"
                                style={{backgroundColor: state.user?.color}}
                            />
                            {state.user?.name || 'Anonymous'}
                        </div>
                    ))}
                </div>
            )}

            {/* 编辑器区域 */}
            <div className="border rounded-lg p-4 min-h-[400px] prose max-w-none">
                <EditorContent key={editorKey} editor={editor}/>
            </div>

            {/* 提示信息 */}
            <div className="mt-4 text-xs text-gray-500">
                <p>文档ID: {documentId}</p>
                <p>提示: 多个用户可以同时编辑,光标和选区会实时显示</p>
                <button
                    onClick={() => {
                        console.log('[DEBUG] Testing article API...');
                        fetch(`http://localhost:9421/api/v1/articles/${documentId}`, {
                            credentials: 'include'
                        })
                            .then(r => {
                                console.log('[DEBUG] Response status:', r.status);
                                return r.json();
                            })
                            .then(d => {
                                console.log('[DEBUG] Article data:', d);
                                console.log('[DEBUG] Content:', d.data?.content || d.content);
                            })
                            .catch(e => console.error('[DEBUG] Error:', e));
                    }}
                    className="text-blue-500 hover:underline mt-2"
                >
                    🔍 测试文章API
                </button>
            </div>
        </Card>
    );
}
