/**
 * 简化的i18n工具 - 用于在不重构路由的情况下提供翻译功能
 *
 * 注意：这是临时方案，完整迁移到next-intl后应使用useTranslations hook
 */

import zhCN from '@/messages/zh-CN.json';
import en from '@/messages/en.json';

const messages: Record<string, any> = {
    'zh-CN': zhCN,
    'en': en,
};

// 从localStorage获取当前语言
export function getLocale(): string {
    if (typeof window === 'undefined') return 'zh-CN';
    return localStorage.getItem('preferred_language') || 'zh-CN';
}

// 设置语言
export function setLocale(locale: string): void {
    if (typeof window !== 'undefined') {
        localStorage.setItem('preferred_language', locale);
    }
}

// 获取翻译值（支持嵌套key，如 "common.loading"）
export function t(key: string, locale?: string): string {
    const currentLocale = locale || getLocale();
    const message = messages[currentLocale];

    if (!message) {
        console.warn(`Messages not found for locale: ${currentLocale}`);
        return key;
    }

    // 支持嵌套key
    const keys = key.split('.');
    let value: any = message;

    for (const k of keys) {
        if (value === undefined || value === null) {
            console.warn(`Translation key not found: ${key}`);
            return key;
        }
        value = value[k];
    }

    if (typeof value !== 'string') {
        console.warn(`Translation value is not a string: ${key}`);
        return key;
    }

    return value;
}

// React Hook版本（用于客户端组件）
export function useSimpleI18n() {
    const locale = getLocale();

    return {
        locale,
        t: (key: string) => t(key, locale),
        setLocale,
    };
}
