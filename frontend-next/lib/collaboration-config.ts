/**
 * 鍗忎綔缂栬緫閰嶇疆
 * 鎻愪緵 WebSocket URL 鍜屼繚瀛樻枃妗ｇ殑 API URL
 */

/**
 * 鑾峰彇 WebSocket 杩炴帴 URL
 * @param inviteId 閭€璇稩D锛圲UID锛? * @param token 璁よ瘉token锛堝彲閫夛級
 * @returns WebSocket URL
 */
export function getWebSocketUrl(inviteId: string, token?: string): string {
    const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:9421';
    const wsProtocol = baseUrl.startsWith('https') ? 'wss' : 'ws';
    const wsBaseUrl = baseUrl.replace(/^https?:\/\//, '');

    let url = `${wsProtocol}://${wsBaseUrl}/ws/collaborate/${inviteId}`;

    // 娣诲姞token鍙傛暟
    if (token) {
        url += `?token=${encodeURIComponent(token)}`;
    }

    return url;
}

/**
 * 鑾峰彇 Yjs WebSocket 杩炴帴 URL锛堜繚鐣欑敤浜庡吋瀹癸級
 * @deprecated 璇蜂娇鐢?getWebSocketUrl
 */
export function getYjsWebSocketUrl(documentId: string, articleId?: number, token?: string): string {
    // 杩欎釜鏂规硶宸插簾寮冿紝浣跨敤 getWebSocketUrl 浠ｆ浛
    return getWebSocketUrl(documentId);
}

/**
 * 鑾峰彇淇濆瓨鏂囨。鐨?API URL
 * @param documentId 鏂囨。ID
 * @returns API URL
 */
export function getSaveDocumentUrl(documentId: string): string {
    const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:9421';
    return `${baseUrl}/api/v2/collaboration/documents/${documentId}/save`;
}

/**
 * 获取邀请相关 API URL
 * @param path API 路径
 * @returns 完整的 API URL
 */
export function getInvitesApiUrl(path: string): string {
    const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:9421';
    return `${baseUrl}/api/v2/collaboration/invites${path}`;
}
