// 支持的语言列表
export const locales = ['zh-CN', 'en', 'ar', 'he'] as const;
export type Locale = (typeof locales)[number];

// 默认语言
export const defaultLocale: Locale = 'zh-CN';

// RTL语言列表(从右到左阅读的语言)
export const rtlLocales: Locale[] = ['ar', 'he']; // 阿拉伯语、希伯来语

/**
 * 检查语言是否为RTL
 * @param locale 语言代码
 * @returns 是否为RTL语言
 */
export function isRTL(locale: Locale): boolean {
  return rtlLocales.includes(locale);
}

/**
 * 获取HTML方向属性
 * @param locale 语言代码
 * @returns 'rtl' 或 'ltr'
 */
export function getDirection(locale: Locale): 'rtl' | 'ltr' {
  return isRTL(locale) ? 'rtl' : 'ltr';
}
