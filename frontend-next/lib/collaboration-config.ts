/**
 * 协作文档 API 配置
 * 统一管理协作功能的 API 地址
 */

// 获取基础 API URL
export const getCollaborationBaseUrl = (): string => {
    return process.env.NEXT_PUBLIC_API_URL || 'http://localhost:9421';
};

// 获取 WebSocket URL
export const getWebSocketUrl = (documentId: string, articleId?: number): string => {
    const baseUrl = getCollaborationBaseUrl();
    const wsProtocol = baseUrl.startsWith('https') ? 'wss:' : 'ws:';
    const wsHost = baseUrl.replace(/^https?:\/\//, '');
    const articleParam = articleId ? `&article_id=${articleId}` : '';
    return `${wsProtocol}//${wsHost}/api/v1/collaboration/ws/${documentId}?${articleParam}`;
};

// 获取文档状态 API URL
export const getDocumentStateUrl = (documentId: string): string => {
    const baseUrl = getCollaborationBaseUrl();
    return `${baseUrl}/api/v1/collaboration/document/${documentId}/state`;
};

// 获取保存文档 API URL
export const getSaveDocumentUrl = (documentId: string): string => {
    const baseUrl = getCollaborationBaseUrl();
    return `${baseUrl}/api/v1/collaboration/document/${documentId}/save`;
};

// 获取 Yjs WebSocket URL
export const getYjsWebSocketUrl = (documentId: string, articleId?: number): string => {
    const baseUrl = getCollaborationBaseUrl();
    const wsProtocol = baseUrl.startsWith('https') ? 'wss:' : 'ws:';
    const wsHost = baseUrl.replace(/^https?:\/\//, '');
    const articleParam = articleId ? `&article_id=${articleId}` : '';
    return `${wsProtocol}//${wsHost}/api/v1/collaboration/yjs/ws/${documentId}?${articleParam}`;
};

// 获取邀请管理 API URL
export const getInvitesApiUrl = (path: string = ''): string => {
    const baseUrl = getCollaborationBaseUrl();
    return `${baseUrl}/api/v1/collaboration/invites${path}`;
};
