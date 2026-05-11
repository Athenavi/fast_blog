/**
 * 协作者光标管理
 * 用于实时协作编辑中显示其他用户的光标位置
 */

export interface Collaborator {
    id: string;
    name: string;
    color: string;
    position?: number;
    selection?: { from: number; to: number };
}

export interface CursorPosition {
    userId: string;
    position: number;
    selection?: { from: number; to: number };
    timestamp: number;
}

// 预定义的协作者光标颜色
const COLLABORATOR_COLORS = [
    '#FF6B6B', // 红色
    '#4ECDC4', // 青色
    '#45B7D1', // 蓝色
    '#FFA07A', // 橙色
    '#98D8C8', // 绿色
    '#F7DC6F', // 黄色
    '#BB8FCE', // 紫色
    '#85C1E2', // 浅蓝
];

export class CollaboratorCursorManager {
    private collaborators: Map<string, Collaborator> = new Map();
    private cursorPositions: Map<string, CursorPosition> = new Map();
    private colorIndex: number = 0;

    /**
     * 添加协作者
     */
    addCollaborator(id: string, name: string): Collaborator {
        const color = COLLABORATOR_COLORS[this.colorIndex % COLLABORATOR_COLORS.length];
        this.colorIndex++;

        const collaborator: Collaborator = {
            id,
            name,
            color,
        };

        this.collaborators.set(id, collaborator);
        return collaborator;
    }

    /**
     * 移除协作者
     */
    removeCollaborator(id: string): void {
        this.collaborators.delete(id);
        this.cursorPositions.delete(id);
    }

    /**
     * 更新协作者光标位置
     */
    updateCursorPosition(userId: string, position: number, selection?: { from: number; to: number }): void {
        this.cursorPositions.set(userId, {
            userId,
            position,
            selection,
            timestamp: Date.now(),
        });
    }

    /**
     * 获取所有活跃协作者及其光标位置
     */
    getActiveCollaborators(): Array<Collaborator & { position?: number; selection?: { from: number; to: number } }> {
        const result: Array<Collaborator & { position?: number; selection?: { from: number; to: number } }> = [];

        this.collaborators.forEach((collaborator) => {
            const cursorPos = this.cursorPositions.get(collaborator.id);
            result.push({
                ...collaborator,
                position: cursorPos?.position,
                selection: cursorPos?.selection,
            });
        });

        return result;
    }

    /**
     * 清理过期的光标位置（超过5秒未更新）
     */
    cleanupStaleCursors(maxAge: number = 5000): void {
        const now = Date.now();
        const staleUsers: string[] = [];

        this.cursorPositions.forEach((position, userId) => {
            if (now - position.timestamp > maxAge) {
                staleUsers.push(userId);
            }
        });

        staleUsers.forEach(userId => this.cursorPositions.delete(userId));
    }

    /**
     * 获取协作者数量
     */
    getCollaboratorCount(): number {
        return this.collaborators.size;
    }

    /**
     * 清空所有协作者
     */
    clearAll(): void {
        this.collaborators.clear();
        this.cursorPositions.clear();
        this.colorIndex = 0;
    }
}

// 全局实例
export const collaboratorCursorManager = new CollaboratorCursorManager();
