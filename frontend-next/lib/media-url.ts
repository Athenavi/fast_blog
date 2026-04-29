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

/**
 * 生成封面图片 URL（公开访问，无需认证）
 * @param mediaId 媒体 ID
 * @param fileHash 文件哈希值
 * @param extension 文件扩展名（默认 .jpg）
 * @returns 封面图片 URL
 */
export function getCoverImageUrl(mediaId: string | number, fileHash: string, extension: string = '.jpg'): string {
    const config = window as any;
    const apiConfig = config.runtimeConfig || {
        API_BASE_URL: 'http://localhost:8000',
        API_PREFIX: '/api/v1'
    };
    // 文件名格式：{media_id}_{hash前16位}.{ext}
    const filename = `${mediaId}_${fileHash.substring(0, 16)}${extension}`;
    return `${apiConfig.API_BASE_URL}${apiConfig.API_PREFIX}/media/cover/${filename}`;
}

/**
 * 异步版本：生成封面图片 URL 并确保封面已生成
 * @param mediaId 媒体 ID
 * @returns 封面图片 URL
 */
export async function generateAndGetCoverUrl(mediaId: string | number): Promise<string> {
    const config = await import('@/lib/config');
    const apiConfig = config.getConfig();

    try {
        // 调用后端API生成封面
        const response = await fetch(
            `${apiConfig.API_BASE_URL}${apiConfig.API_PREFIX}/media/generate-cover/${mediaId}`,
            {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    // 需要携带认证信息
                    'Authorization': `Bearer ${document.cookie.split('; ').find(row => row.startsWith('access_token='))?.split('=')[1]}`
                },
                credentials: 'include'
            }
        );

        if (!response.ok) {
            throw new Error(`生成封面失败: ${response.status}`);
        }

        const result = await response.json();
        if (result.success && result.data?.cover_url) {
            // 返回完整的URL
            return `${apiConfig.API_BASE_URL}${result.data.cover_url}`;
        }

        throw new Error('生成封面失败');
    } catch (error) {
        console.error('生成封面URL失败:', error);
        throw error;
    }
}
