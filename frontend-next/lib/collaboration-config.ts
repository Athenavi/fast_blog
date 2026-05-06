/**
 * 协作编辑配置
 * 提供 WebSocket URL 和保存文档的 API URL
 */

/**
 * 获取 Yjs WebSocket 连接 URL
 * @param documentId 文档ID
 * @param articleId 文章ID（可选）
 * @returns WebSocket URL
 */
export function getYjsWebSocketUrl(documentId: string, articleId?: number): string {
    const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:9421';
    const wsProtocol = baseUrl.startsWith('https') ? 'wss' : 'ws';
    const wsBaseUrl = baseUrl.replace(/^https?:\/\//, '');

    // 构建 WebSocket URL
    let url = `${wsProtocol}://${wsBaseUrl}/ws/collaboration/${documentId}`;

    // 添加文章ID参数
    if (articleId) {
        url += `?article_id=${articleId}`;
    }

    return url;
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
