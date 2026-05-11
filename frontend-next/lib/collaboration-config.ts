/**
 * 协作编辑配置
 * 提供 WebSocket URL 和保存文档的 API URL
 */

/**
 * 获取 WebSocket 连接 URL
 * @param inviteId 邀请ID（UUID）
 * @param token 认证token（可选）
 * @returns WebSocket URL
 */
export function getWebSocketUrl(inviteId: string, token?: string): string {
    const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:9421';
    const wsProtocol = baseUrl.startsWith('https') ? 'wss' : 'ws';
    const wsBaseUrl = baseUrl.replace(/^https?:\/\//, '');

    let url = `${wsProtocol}://${wsBaseUrl}/ws/collaborate/${inviteId}`;

    // 添加token参数
    if (token) {
        url += `?token=${encodeURIComponent(token)}`;
    }

    return url;
}

/**
 * 获取 Yjs WebSocket 连接 URL（保留用于兼容）
 * @deprecated 请使用 getWebSocketUrl
 */
export function getYjsWebSocketUrl(documentId: string, articleId?: number, token?: string): string {
    // 这个方法已废弃，使用 getWebSocketUrl 代替
    return getWebSocketUrl(documentId);
}

/**
 * 获取保存文档的 API URL
 * @param documentId 文档ID
 * @returns API URL
 */
export function getSaveDocumentUrl(documentId: string): string {
    const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:9421';
    return `${baseUrl}/api/v1/collaboration/documents/${documentId}/save`;
}
