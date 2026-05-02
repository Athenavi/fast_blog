import {useState, useEffect, useCallback, useRef} from 'react';

interface CursorPosition {
    position: number;
    selection?: {
        start: number;
        end: number;
    };
}

interface RemoteCursor {
    clientId: string;
    cursor: CursorPosition;
    color?: string;
}

interface Operation {
    type: 'insert' | 'delete' | 'replace';
    position?: number;
    text?: string;
    length?: number;
}

interface CollaborationState {
    isConnected: boolean;
    documentId: string;
    content: string;
    remoteCursors: Map<string, RemoteCursor>;
    clientCount: number;
    clientId: string;
}

interface UseCollaborationOptions {
    documentId: string;
    token?: string;
    onContentChange?: (content: string) => void;
    onUserJoin?: (clientId: string) => void;
    onUserLeave?: (clientId: string) => void;
}

export function useCollaboration({
                                     documentId,
                                     token,
                                     onContentChange,
                                     onUserJoin,
                                     onUserLeave,
                                 }: UseCollaborationOptions) {
    const [state, setState] = useState<CollaborationState>({
        isConnected: false,
        documentId,
        content: '',
        remoteCursors: new Map(),
        clientCount: 0,
        clientId: '',
    });

    const wsRef = useRef<WebSocket | null>(null);
    const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
    const isConnectingRef = useRef(false);

    // 生成随机颜色用于光标显示
    const generateColor = useCallback((clientId: string) => {
        const colors = [
            '#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A',
            '#98D8C8', '#F7DC6F', '#BB8FCE', '#85C1E2'
        ];
        let hash = 0;
        for (let i = 0; i < clientId.length; i++) {
            hash = clientId.charCodeAt(i) + ((hash << 5) - hash);
        }
        return colors[Math.abs(hash) % colors.length];
    }, []);

    // 连接WebSocket
    const connect = useCallback(() => {
        if (isConnectingRef.current || wsRef.current?.readyState === WebSocket.OPEN) {
            return;
        }

        isConnectingRef.current = true;

        const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:9421';
        const wsUrl = `${baseUrl.replace('http', 'ws')}/api/v1/collaboration/ws/${documentId}`;

        const params = new URLSearchParams();
        if (token) params.append('token', token);

        const ws = new WebSocket(`${wsUrl}?${params.toString()}`);
        wsRef.current = ws;

        ws.onopen = () => {
            console.log('[Collaboration] Connected');
            isConnectingRef.current = false;
            setState(prev => ({...prev, isConnected: true}));
        };

        ws.onmessage = (event) => {
            try {
                const message = JSON.parse(event.data);
                handleMessage(message);
            } catch (error) {
                console.error('[Collaboration] Failed to parse message:', error);
            }
        };

        ws.onclose = (event) => {
            console.log('[Collaboration] Disconnected:', event.code, event.reason);
            isConnectingRef.current = false;
            setState(prev => ({...prev, isConnected: false}));

            // 自动重连(除非是正常关闭)
            if (event.code !== 1000 && event.code !== 1001) {
                reconnectTimeoutRef.current = setTimeout(() => {
                    console.log('[Collaboration] Attempting to reconnect...');
                    connect();
                }, 3000);
            }
        };

        ws.onerror = (error) => {
            console.error('[Collaboration] WebSocket error:', error);
            isConnectingRef.current = false;
        };
    }, [documentId, token]);

    // 处理接收到的消息
    const handleMessage = useCallback((message: any) => {
        switch (message.type) {
            case 'welcome':
                setState(prev => ({
                    ...prev,
                    isConnected: true,
                    content: message.state?.content || '',
                    clientCount: message.state?.client_count || 0,
                    clientId: message.client_id,
                    remoteCursors: new Map(
                        Object.entries(message.state?.cursors || {}).map(([id, cursor]) => [
                            id,
                            {clientId: id, cursor: cursor as CursorPosition, color: generateColor(id)}
                        ])
                    ),
                }));
                break;

            case 'remote_operation':
                // 应用远程操作到本地内容
                setState(prev => {
                    const newContent = applyOperation(prev.content, message.operation);
                    if (onContentChange) {
                        onContentChange(newContent);
                    }
                    return {...prev, content: newContent};
                });
                break;

            case 'cursor_update':
                setState(prev => {
                    const newCursors = new Map(prev.remoteCursors);
                    newCursors.set(message.client_id, {
                        clientId: message.client_id,
                        cursor: message.cursor,
                        color: prev.remoteCursors.get(message.client_id)?.color || generateColor(message.client_id),
                    });
                    return {...prev, remoteCursors: newCursors};
                });
                break;

            case 'user_joined':
                setState(prev => ({...prev, clientCount: message.client_count}));
                if (onUserJoin) {
                    onUserJoin(message.client_id);
                }
                break;

            case 'user_left':
                setState(prev => {
                    const newCursors = new Map(prev.remoteCursors);
                    newCursors.delete(message.client_id);
                    return {...prev, remoteCursors: newCursors, clientCount: message.client_count};
                });
                if (onUserLeave) {
                    onUserLeave(message.client_id);
                }
                break;

            case 'sync_response':
                setState(prev => ({
                    ...prev,
                    content: message.state?.content || prev.content,
                    remoteCursors: new Map(
                        Object.entries(message.state?.cursors || {}).map(([id, cursor]) => [
                            id,
                            {clientId: id, cursor: cursor as CursorPosition, color: generateColor(id)}
                        ])
                    ),
                }));
                break;

            default:
                console.log('[Collaboration] Unknown message type:', message.type);
        }
    }, [onContentChange, onUserJoin, onUserLeave, generateColor]);

    // 应用操作到文本
    const applyOperation = (content: string, operation: Operation): string => {
        switch (operation.type) {
            case 'insert':
                if (operation.position !== undefined && operation.text) {
                    return content.slice(0, operation.position) + operation.text + content.slice(operation.position);
                }
                return content;

            case 'delete':
                if (operation.position !== undefined && operation.length) {
                    return content.slice(0, operation.position) + content.slice(operation.position + operation.length);
                }
                return content;

            case 'replace':
                if (operation.position !== undefined && operation.length !== undefined && operation.text) {
                    return content.slice(0, operation.position) + operation.text + content.slice(operation.position + operation.length);
                }
                return content;

            default:
                return content;
        }
    };

    // 发送编辑操作
    const sendOperation = useCallback((operation: Operation) => {
        if (wsRef.current?.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify({
                type: 'operation',
                operation,
            }));
        }
    }, []);

    // 更新光标位置
    const updateCursor = useCallback((position: number, selection?: { start: number; end: number }) => {
        if (wsRef.current?.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify({
                type: 'cursor',
                cursor: {position, selection},
            }));
        }
    }, []);

    // 请求同步
    const requestSync = useCallback(() => {
        if (wsRef.current?.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify({type: 'sync'}));
        }
    }, []);

    // 断开连接
    const disconnect = useCallback(() => {
        if (reconnectTimeoutRef.current) {
            clearTimeout(reconnectTimeoutRef.current);
        }
        if (wsRef.current) {
            wsRef.current.close(1000, 'Client disconnecting');
            wsRef.current = null;
        }
        setState(prev => ({...prev, isConnected: false}));
    }, []);

    // 组件挂载时连接,卸载时断开
    useEffect(() => {
        connect();
        return () => {
            disconnect();
        };
    }, [connect, disconnect]);

    return {
        ...state,
        sendOperation,
        updateCursor,
        requestSync,
        disconnect,
        reconnect: connect,
    };
}
