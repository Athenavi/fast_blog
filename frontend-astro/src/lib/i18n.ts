// 支持的语言列表
export const locales = ['zh-CN', 'en', 'ar', 'he'] as const;
export type Locale = (typeof locales)[number];

// 默认语言
export const defaultLocale: Locale = 'zh-CN';

// RTL语言列表
export const rtlLocales: Locale[] = ['ar', 'he'];

/**
 * 检查语言是否为RTL
 */
export function isRTL(locale: Locale): boolean {
    return rtlLocales.includes(locale);
}

/**
 * 获取HTML方向属性
 */
export function getDirection(locale: Locale): 'rtl' | 'ltr' {
    return isRTL(locale) ? 'rtl' : 'ltr';
}
