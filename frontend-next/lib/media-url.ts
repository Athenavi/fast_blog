/**
 * 媒体URL工具函数
 *
 * 用于生成和获取媒体文件的URL
 */

import {getConfig} from '@/lib/config';

/**
 * 根据媒体ID或哈希生成媒体URL
 * @param mediaId - 媒体ID或哈希
 * @returns 完整的媒体URL
 */
export function getMediaUrl(mediaId: string): string {
    const config = getConfig();
    const baseUrl = config.API_BASE_URL.replace(/\/api\/v1$/, '');

    // 如果已经是完整URL，直接返回
    if (mediaId.startsWith('http://') || mediaId.startsWith('https://')) {
        return mediaId;
    }

    // 根据ID生成URL
    return `${baseUrl}/media/${mediaId}`;
}

/**
 * 同步版本 - 用于客户端组件
 * @param mediaId - 媒体ID或哈希
 * @returns 完整的媒体URL
 */
export function getMediaUrlSync(mediaId: string): string {
    return getMediaUrl(mediaId);
}

/**
 * 生成并获取封面URL
 * @param mediaId - 媒体ID
 * @returns 封面URL
 */
export async function generateAndGetCoverUrl(mediaId: string | number): Promise<string> {
    // 如果是数字ID，转换为字符串
    const id = String(mediaId);

    // 这里可以调用后端API生成优化的封面
    // 目前直接返回媒体URL
    return getMediaUrl(id);
}

/**
 * 获取缩略图URL
 * @param mediaId - 媒体ID
 * @returns 缩略图URL
 */
export function getThumbnailUrl(mediaId: string): string {
    const config = getConfig();
    const baseUrl = config.API_BASE_URL.replace(/\/api\/v1$/, '');

    if (mediaId.startsWith('http://') || mediaId.startsWith('https://')) {
        return mediaId;
    }

    return `${baseUrl}/media/thumbnails/${mediaId}`;
}
