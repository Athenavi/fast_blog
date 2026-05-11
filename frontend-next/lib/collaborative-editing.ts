/**
 * 协同编辑服务
 * 基于WebSocket实现实时协作
 */

export interface CollaborativeUser {
    id: string;
    name: string;
    color: string;
    cursor?: {
        line: number;
        ch: number;
    };
    selection?: {
        from: number;
        to: number;
    };
}

export interface DocumentOperation {
    type: 'insert' | 'delete' | 'replace';
    position: number;
    content?: string;
    length?: number;
    userId: string;
    timestamp: number;
}

export class CollaborativeEditingService {
    // 回调函数
    onOperationReceived?: (operation: DocumentOperation) => void;
    onCursorUpdate?: (userId: string, position: { line: number; ch: number }) => void;
    onSelectionUpdate?: (userId: string, selection: { from: number; to: number }) => void;
    onDocumentSync?: (state: any) => void;
    onUserListChange?: (users: CollaborativeUser[]) => void;
    onConnectionFailed?: () => void;
    private ws: WebSocket | null = null;
    private users: Map<string, CollaborativeUser> = new Map();
    private pendingOperations: DocumentOperation[] = [];
    private isConnected: boolean = false;
    private reconnectAttempts: number = 0;
    private maxReconnectAttempts: number = 5;

    constructor(
        private documentId: string,
        private userId: string,
        private userName: string,
        private wsUrl: string = 'ws://localhost:8000/ws/collaborative'
    ) {
    }

    /**
     * 连接到协同编辑服务器
     */
    connect(): Promise<void> {
        return new Promise((resolve, reject) => {
            try {
                this.ws = new WebSocket(`${this.wsUrl}?doc=${this.documentId}&user=${this.userId}`);

                this.ws.onopen = () => {
                    console.log('协同编辑连接已建立');
                    this.isConnected = true;
                    this.reconnectAttempts = 0;

                    // 发送用户信息
                    this.send({
                        type: 'join',
                        userId: this.userId,
                        userName: this.userName,
                    });

                    resolve();
                };

                this.ws.onmessage = (event) => {
                    const data = JSON.parse(event.data);
                    this.handleMessage(data);
                };

                this.ws.onerror = (error) => {
                    console.error('WebSocket错误:', error);
                    reject(error);
                };

                this.ws.onclose = () => {
                    console.log('协同编辑连接已关闭');
                    this.isConnected = false;
                    this.attemptReconnect();
                };
            } catch (error) {
                reject(error);
            }
        });
    }

    /**
     * 断开连接
     */
    disconnect(): void {
        if (this.ws) {
            this.send({
                type: 'leave',
                userId: this.userId,
            });
            this.ws.close();
            this.ws = null;
        }
    }

    /**
     * 发送文档操作
     */
    sendOperation(operation: DocumentOperation): void {
        if (!this.isConnected) {
            this.pendingOperations.push(operation);
            return;
        }

        this.send({
            type: 'operation',
            operation,
        });
    }

    /**
     * 更新光标位置
     */
    updateCursor(position: { line: number; ch: number }): void {
        this.send({
            type: 'cursor',
            userId: this.userId,
            position,
        });
    }

    /**
     * 更新选区
     */
    updateSelection(from: number, to: number): void {
        this.send({
            type: 'selection',
            userId: this.userId,
            selection: {from, to},
        });
    }

    /**
     * 获取在线用户列表
     */
    getOnlineUsers(): CollaborativeUser[] {
        return Array.from(this.users.values());
    }

    /**
     * 处理接收到的消息
     */
    private handleMessage(data: any): void {
        switch (data.type) {
            case 'user_joined':
                this.users.set(data.user.id, data.user);
                this.notifyUserListChange();
                break;

            case 'user_left':
                this.users.delete(data.userId);
                this.notifyUserListChange();
                break;

            case 'operation':
                this.applyRemoteOperation(data.operation);
                break;

            case 'cursor_update':
                this.updateRemoteCursor(data.userId, data.position);
                break;

            case 'selection_update':
                this.updateRemoteSelection(data.userId, data.selection);
                break;

            case 'document_state':
                // 接收完整的文档状态（用于初始同步）
                this.syncDocumentState(data.state);
                break;
        }
    }

    /**
     * 应用远程操作
     */
    private applyRemoteOperation(operation: DocumentOperation): void {
        // 这里需要实现OT（Operational Transformation）或CRDT算法
        // 简化版本：直接应用操作
        console.log('应用远程操作:', operation);

        // 触发回调，让编辑器应用这个操作
        this.onOperationReceived?.(operation);
    }

    /**
     * 更新远程用户的光标
     */
    private updateRemoteCursor(userId: string, position: { line: number; ch: number }): void {
        const user = this.users.get(userId);
        if (user) {
            user.cursor = position;
            this.onCursorUpdate?.(userId, position);
        }
    }

    /**
     * 更新远程用户的选区
     */
    private updateRemoteSelection(userId: string, selection: { from: number; to: number }): void {
        const user = this.users.get(userId);
        if (user) {
            user.selection = selection;
            this.onSelectionUpdate?.(userId, selection);
        }
    }

    /**
     * 同步文档状态
     */
    private syncDocumentState(state: any): void {
        console.log('同步文档状态:', state);
        this.onDocumentSync?.(state);
    }

    /**
     * 通知用户列表变化
     */
    private notifyUserListChange(): void {
        this.onUserListChange?.(Array.from(this.users.values()));
    }

    /**
     * 尝试重新连接
     */
    private attemptReconnect(): void {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000);

            console.log(`尝试重新连接 (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`);

            setTimeout(() => {
                this.connect().catch(err => {
                    console.error('重新连接失败:', err);
                });
            }, delay);
        } else {
            console.error('达到最大重连次数，连接失败');
            this.onConnectionFailed?.();
        }
    }

    /**
     * 发送消息
     */
    private send(message: any): void {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(message));
        }
    }
}

// 生成随机颜色
export function generateUserColor(): string {
    const colors = [
        '#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A',
        '#98D8C8', '#F7DC6F', '#BB8FCE', '#82E0AA'
    ];
    return colors[Math.floor(Math.random() * colors.length)];
}
