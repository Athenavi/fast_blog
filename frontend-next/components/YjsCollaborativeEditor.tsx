'use client';

import React, {useEffect, useRef, useState} from 'react';
import {EditorContent, useEditor} from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import {Card} from '@/components/ui/card';
import {Badge} from '@/components/ui/badge';
import {getYjsWebSocketUrl} from '@/lib/collaboration-config';

interface YjsCollaborativeEditorProps {
    documentId: string;
    articleId?: number;
    readOnly?: boolean;
}

export default function YjsCollaborativeEditor({
                                                   documentId,
                                                   articleId,
                                                   readOnly = false,
                                               }: YjsCollaborativeEditorProps) {
    const [isConnected, setIsConnected] = useState(false);
    const wsRef = useRef<WebSocket | null>(null);

    // 初始化 TipTap 编辑器 - 最简化配置
    const editor = useEditor({
        extensions: [
            StarterKit.configure({}),
        ],
        editable: !readOnly,
        content: '<p>开始编辑...</p>',
    });

    // WebSocket 连接
    useEffect(() => {
        if (!editor) return;

        console.log('[Yjs Editor] Connecting to:', documentId);

        try {
            const wsUrl = getYjsWebSocketUrl(documentId, articleId);
            const ws = new WebSocket(wsUrl);
            wsRef.current = ws;

            ws.onopen = () => {
                console.log('[Yjs Editor] Connected');
                setIsConnected(true);
            };

            ws.onclose = () => {
                console.log('[Yjs Editor] Disconnected');
                setIsConnected(false);
            };

            ws.onerror = (err) => {
                console.error('[Yjs Editor] Error:', err);
            };

            return () => {
                if (ws.readyState === WebSocket.OPEN) {
                    ws.close();
                }
            };
        } catch (error) {
            console.error('[Yjs Editor] Connection failed:', error);
        }
    }, [documentId, articleId]);

    if (!editor) {
        return <div>加载中...</div>;
    }

    return (
        <Card className="p-4">
            <div className="mb-4 flex items-center gap-2">
                {isConnected ? (
                    <Badge variant="default">已连接</Badge>
                ) : (
                    <Badge variant="destructive">未连接</Badge>
                )}
            </div>
            <div className="border rounded p-4 min-h-[400px]">
                <EditorContent editor={editor}/>
            </div>
        </Card>
    );
}
