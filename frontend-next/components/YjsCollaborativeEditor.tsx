'use client';

import React, {useEffect, useRef, useState} from 'react';
import {Card} from '@/components/ui/card';
import CollaborationBar from '@/components/CollaborationBar';
import {getWebSocketUrl} from '@/lib/collaboration-config';

interface CollaborativeMarkdownEditorProps {
  documentId: string;
  articleId?: number;
  readOnly?: boolean;
}

export default function CollaborativeMarkdownEditor({
                                                      documentId,
                                                      articleId,
                                                      readOnly = false,
                                                    }: CollaborativeMarkdownEditorProps) {
  const [isConnected, setIsConnected] = useState(false);
  const [pendingInitContent, setPendingInitContent] = useState<string | null>(null);
  const [onlineUsers, setOnlineUsers] = useState<Array<{ client_id?: string; name?: string; color?: string }>>([]);
  const wsRef = useRef<WebSocket | null>(null);
  const versionRef = useRef<number>(0);
  const editorRef = useRef<any>(null);
  const isRemoteUpdate = useRef(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const changeHandlerRef = useRef<(() => void) | null>(null);

  // 获取当前用户信息（从 cookie 或 localStorage）
  const getCurrentUserInfo = () => {
    if (typeof window === 'undefined') {
      return {userId: 'anonymous', userName: '匿名用户'};
    }

    // 尝试从 localStorage 获取用户信息
    const userInfo = localStorage.getItem('user_info');
    if (userInfo) {
      try {
        const parsed = JSON.parse(userInfo);
        return {
          userId: parsed.id?.toString() || 'anonymous',
          userName: parsed.nickname || parsed.username || '匿名用户'
        };
      } catch (e) {
        console.error('Failed to parse user info:', e);
      }
    }

    return {userId: 'anonymous', userName: '匿名用户'};
  };

  const {userId, userName} = getCurrentUserInfo();

  // 统一安全地应用远程内容
  const applyRemoteContent = (content: string) => {
    if (!editorRef.current || typeof content !== 'string') return;
    isRemoteUpdate.current = true;
    try {
      editorRef.current.value(content);
    } finally {
      // 使用 setTimeout 保证 change 事件已经处理完
      setTimeout(() => {
        isRemoteUpdate.current = false;
      }, 0);
    }
  };

  // 初始化 WebSocket 连接
  useEffect(() => {
    console.log('[Collab Markdown] Connecting with documentId:', documentId);

    const getTokenFromCookie = (): string | null => {
      if (typeof document === 'undefined') return null;
      const cookies = document.cookie.split(';');
      for (const cookie of cookies) {
        const [name, value] = cookie.trim().split('=');
        if (name === 'access_token') return decodeURIComponent(value);
      }
      return null;
    };

    const token = getTokenFromCookie();
    const wsUrl = getWebSocketUrl(documentId, token || undefined);
    console.log('[Collab Markdown] WebSocket URL:', wsUrl);

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log('[Collab Markdown] Connected');
      setIsConnected(true);
    };

    ws.onclose = (event) => {
      console.log('[Collab Markdown] Disconnected, code:', event.code, 'reason:', event.reason);
      setIsConnected(false);

      // 4009 表示已有进行中的协作，不再自动处理
      if (event.code === 4009) {
        alert('您已有一个进行中的协作，请先关闭现有会话。');
      }
    };

    ws.onerror = (err) => {
      console.error('[Collab Markdown] WebSocket error:', err);
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        console.log('[Collab Markdown] Received message type:', data.type);

        if (data.type === 'init') {
          console.log('[Collab Markdown] Init message received');
          if (data.content !== undefined && data.content !== null) {
            if (editorRef.current) {
              applyRemoteContent(data.content);
            } else {
              setPendingInitContent(data.content);
            }
          }
          versionRef.current = data.version || 0;
        } else if (data.type === 'receive_steps') {
          if (data.steps?.length > 0) {
            const content = data.steps[0].data?.content;
            if (content !== undefined && content !== null) {
              applyRemoteContent(content);
            }
          }
          if (data.version) versionRef.current = data.version;
        } else if (data.type === 'user_joined' || data.type === 'user_left') {
          // 更新在线用户列表
          console.log('[Collab Markdown] User event received:', data.type);
          console.log('[Collab Markdown] Users data:', data.users);
          console.log('[Collab Markdown] Client count:', data.client_count);
          
          if (data.users) {
            console.log('[Collab Markdown] Updating user list with', data.users.length, 'users');
            setOnlineUsers(data.users);
          } else {
            console.warn('[Collab Markdown] No users data in message');
          }
        }
      } catch (error) {
        console.error('[Collab Markdown] Message parse error:', error);
      }
    };

    return () => {
      console.log('[Collab Markdown] Cleaning up WebSocket...');
      if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {
        ws.close(1000, 'Component unmounted');
      }
    };
  }, [documentId]);

  // 初始化 SimpleMDE 编辑器（仅一次）
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

        const EasyMDE = await import('easymde').then((m) => m.default);
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
            'guide',
          ],
          autoRefresh: {delay: 300},
          inputStyle: 'textarea',
          lineWrapping: true,
        });

        editorRef.current = editor;

        // 定义内容变更处理器
        const onChange = () => {
          if (isRemoteUpdate.current) {
            console.log('[Collab Markdown] Skipping remote update');
            return;
          }

          const ws = wsRef.current;
          if (!ws || ws.readyState !== WebSocket.OPEN) {
            console.log('[Collab Markdown] WebSocket not ready');
            return;
          }

          const newContent = editor.value();
          versionRef.current += 1;

          const message = {
            type: 'step',
            step: {
              stepType: 'replace',
              data: {content: newContent},
              clientID: 'current_user',
              version: versionRef.current,
            },
            content: newContent,
          };

          ws.send(JSON.stringify(message));
        };

        editor.codemirror.on('change', onChange);
        changeHandlerRef.current = onChange;

        // 如果有待处理的初始内容，现在应用
        if (pendingInitContent !== null) {
          applyRemoteContent(pendingInitContent);
          setPendingInitContent(null);
        }

        // 设置只读状态
        editor.codemirror.setOption('readOnly', readOnly);
      } catch (error) {
        console.error('[Collab Markdown] Failed to load EasyMDE:', error);
      }
    };

    loadEasyMDE();

    return () => {
      console.log('[Collab Markdown] Destroying editor...');
      if (editorRef.current && changeHandlerRef.current) {
        editorRef.current.codemirror.off('change', changeHandlerRef.current);
      }
      if (editorRef.current) {
        editorRef.current.toTextArea();
        editorRef.current = null;
      }
      changeHandlerRef.current = null;
    };
  }, []); // 仅挂载一次

  // 同步 readOnly 属性
  useEffect(() => {
    if (editorRef.current) {
      editorRef.current.codemirror.setOption('readOnly', readOnly);
    }
  }, [readOnly]);

  return (
      <div className="min-h-screen bg-gray-50">
        {/* 协作工具栏 */}
        {!readOnly && (
            <CollaborationBar
                documentId={documentId}
                userId={userId}
                userName={userName}
                articleId={articleId}
                editor={editorRef.current}
                isConnected={isConnected}
                onlineUsers={onlineUsers}
            />
        )}

        <div className="container mx-auto px-4 py-6">
          <Card className="p-4">
            <div className="mb-4">
              <h3 className="font-semibold">协作文档编辑器（Markdown）</h3>
              <p className="text-sm text-gray-600">文档ID: {documentId}</p>
              {readOnly && (
                  <p className="text-sm text-gray-600">只读模式</p>
              )}
            </div>
            <div className="border rounded min-h-[400px]">
              <textarea ref={textareaRef}></textarea>
            </div>
          </Card>
        </div>
      </div>
  );
}