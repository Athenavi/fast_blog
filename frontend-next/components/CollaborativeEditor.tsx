'use client';

import {useEffect, useRef, useState} from 'react';
import * as Y from 'yjs';
import {WebsocketProvider} from 'y-websocket';
import {EditorContent, useEditor} from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';

interface CollaborativeEditorProps {
    documentId: string;
    userId: number;
    userName: string;
}

export default function CollaborativeEditor({
                                                documentId,
                                                userId,
                                                userName,
                                            }: CollaborativeEditorProps) {
    const [onlineUsers, setOnlineUsers] = useState<string[]>([]);
    const providerRef = useRef<WebsocketProvider | null>(null);
    const docRef = useRef<Y.Doc | null>(null);

    // 初始化 Yjs 文档和 WebSocket 提供者
    useEffect(() => {
        const ydoc = new Y.Doc();
        docRef.current = ydoc;

        // 连接到 WebSocket 服务器
        const wsUrl = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:9421';
        const provider = new WebsocketProvider(
            `${wsUrl}/ws/collaborate/${documentId}`,
            `article-${documentId}`,
            ydoc,
            {
                params: {
                    user_id: userId.toString(),
                },
            }
        );

        providerRef.current = provider;

        // 监听用户列表变化
        provider.awareness.on('change', () => {
            const states = provider.awareness.getStates();
            const users = Array.from(states.values()).map((state: any) => state.user?.name || 'Anonymous');
            setOnlineUsers(users);
        });

        // 清理
        return () => {
            provider.destroy();
            ydoc.destroy();
        };
    }, [documentId, userId]);

    // 初始化 TipTap 编辑器
    const editor = useEditor({
        extensions: [
            StarterKit.configure({
                history: false, // 禁用本地历史，使用 Yjs 的协同历史
            }),
        ],
        content: '',
        editorProps: {
            attributes: {
                class: 'prose prose-sm sm:prose lg:prose-lg xl:prose-2xl mx-auto focus:outline-none min-h-[500px]',
            },
        },
    });

    // 将 Yjs 绑定到 TipTap
    useEffect(() => {
        if (!editor || !docRef.current) return;

        // 这里需要集成 y-prosemirror
        // 由于篇幅限制，简化实现
        console.log('Editor initialized with Yjs');
    }, [editor]);

    return (
        <div className="space-y-4">
            {/* 在线用户列表 */}
            <div className="flex items-center space-x-2 p-3 bg-gray-50 rounded-lg">
                <span className="text-sm text-gray-600">在线用户:</span>
                <div className="flex -space-x-2">
                    {onlineUsers.map((user, index) => (
                        <div
                            key={index}
                            className="w-8 h-8 rounded-full bg-blue-500 flex items-center justify-center text-white text-xs border-2 border-white"
                            title={user}
                        >
                            {user.charAt(0).toUpperCase()}
                        </div>
                    ))}
                </div>
                <span className="text-sm text-gray-500">
          {onlineUsers.length} 人正在编辑
        </span>
            </div>

            {/* 编辑器 */}
            <div className="border rounded-lg p-4 bg-white">
                {editor && <EditorContent editor={editor}/>}
            </div>

            {/* 状态指示器 */}
            <div className="flex items-center justify-between text-sm text-gray-500">
        <span>
          {providerRef.current?.wsconnected ? (
              <span className="text-green-600">● 已连接</span>
          ) : (
              <span className="text-yellow-600">● 连接中...</span>
          )}
        </span>
                <span>最后保存: {new Date().toLocaleTimeString()}</span>
            </div>
        </div>
    );
}
