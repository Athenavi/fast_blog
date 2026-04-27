/**
 * 媒体资源 URL 生成工具
 *
 * 用于生成完整的后端媒体资源 URL
 */

/**
 * 生成媒体资源完整 URL
 * @param mediaId 媒体 ID
 * @returns 完整的媒体资源 URL
 */
export async function getMediaUrl(mediaId: string): Promise<string> {
    const config = await import('@/lib/config');
    const apiConfig = config.getConfig();
    return `${apiConfig.API_BASE_URL}${apiConfig.API_PREFIX}/media/${mediaId}`;
}

/**
 * 生成缩略图完整 URL
 * @param mediaId 媒体 ID
 * @returns 完整的缩略图 URL
 */
export async function getThumbnailUrl(mediaId: string): Promise<string> {
    const config = await import('@/lib/config');
    const apiConfig = config.getConfig();
    return `${apiConfig.API_BASE_URL}${apiConfig.API_PREFIX}/thumbnail/${mediaId}`;
}

/**
 * 同步版本的媒体 URL 生成（使用默认配置）
 * @param mediaId 媒体 ID
 * @returns 媒体资源 URL
 */
export function getMediaUrlSync(mediaId: string | number): string {
    const config = window as any;
    const apiConfig = config.runtimeConfig || {
        API_BASE_URL: 'http://localhost:8000',
        API_PREFIX: '/api/v1'
    };
    return `${apiConfig.API_BASE_URL}${apiConfig.API_PREFIX}/media/${mediaId}`;
}

/**
 * 同步版本的缩略图 URL 生成（使用默认配置）
 * @param mediaId 媒体 ID
 * @returns 缩略图 URL
 */
export function getThumbnailUrlSync(mediaId: string | number): string {
    const config = window as any;
    const apiConfig = config.runtimeConfig || {
        API_BASE_URL: 'http://localhost:8000',
        API_PREFIX: '/api/v1'
    };
    return `${apiConfig.API_BASE_URL}${apiConfig.API_PREFIX}/thumbnail/${mediaId}`;
}
