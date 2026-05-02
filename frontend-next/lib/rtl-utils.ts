/**
 * RTL (Right-to-Left) 支持工具
 *
 * 参考 Bootstrap RTL 和 TailwindCSS RTL 插件的设计
 */

import {isRTL, getDirection, type Locale} from '@/i18n';

/**
 * RTL CSS 属性映射
 * 将 LTR 的 CSS 属性转换为 RTL
 */
export const rtlPropertyMap: Record<string, string> = {
    'left': 'right',
    'right': 'left',
    'margin-left': 'margin-right',
    'margin-right': 'margin-left',
    'padding-left': 'padding-right',
    'padding-right': 'padding-left',
    'border-left': 'border-right',
    'border-right': 'border-left',
    'border-radius-tl': 'border-radius-tr',
    'border-radius-tr': 'border-radius-tl',
    'border-radius-bl': 'border-radius-br',
    'border-radius-br': 'border-radius-bl',
    'text-align: left': 'text-align: right',
    'text-align: right': 'text-align: left',
    'float: left': 'float: right',
    'float: right': 'float: left',
};

/**
 * 获取 RTL 感知的 CSS 类名
 *
 * @param locale 当前语言
 * @param ltrClass LTR 模式的类名
 * @param rtlClass RTL 模式的类名（可选，默认自动转换）
 * @returns 适合当前语言的类名
 */
export function getRTLClass(
    locale: Locale,
    ltrClass: string,
    rtlClass?: string
): string {
    if (!isRTL(locale)) {
        return ltrClass;
    }

    // 如果提供了 RTL 类名，直接使用
    if (rtlClass) {
        return rtlClass;
    }

    // 否则尝试自动转换常见的 Tailwind 类
    return convertTailwindClassToRTL(ltrClass);
}

/**
 * 转换 Tailwind CSS 类名为 RTL 版本
 */
function convertTailwindClassToRTL(className: string): string {
    // Tailwind RTL 转换规则
    const conversions: Array<[RegExp, string]> = [
        [/\.ml-(\d+)/g, '.mr-$1'],      // margin-left -> margin-right
        [/\.mr-(\d+)/g, '.ml-$1'],      // margin-right -> margin-left
        [/\.pl-(\d+)/g, '.pr-$1'],      // padding-left -> padding-right
        [/\.pr-(\d+)/g, '.pl-$1'],      // padding-right -> padding-left
        [/\.left-(\d+)/g, '.right-$1'], // left -> right
        [/\.right-(\d+)/g, '.left-$1'], // right -> left
        [/\.text-left/g, '.text-right'],
        [/\.text-right/g, '.text-left'],
        [/\.float-left/g, '.float-right'],
        [/\.float-right/g, '.float-left'],
        [/\.rounded-tl/g, '.rounded-tr'],
        [/\.rounded-tr/g, '.rounded-tl'],
        [/\.rounded-bl/g, '.rounded-br'],
        [/\.rounded-br/g, '.rounded-bl'],
    ];

    let result = className;
    for (const [pattern, replacement] of conversions) {
        result = result.replace(pattern, replacement);
    }

    return result;
}

/**
 * 生成 RTL 感知的内联样式
 *
 * @param locale 当前语言
 * @param styles 样式对象
 * @returns 适合当前语言的样式对象
 */
export function getRTLStyles(
    locale: Locale,
    styles: React.CSSProperties
): React.CSSProperties {
    if (!isRTL(locale)) {
        return styles;
    }

    const rtlStyles: React.CSSProperties = {...styles};

    // 转换方向相关的属性
    if (rtlStyles.marginLeft !== undefined) {
        rtlStyles.marginRight = rtlStyles.marginLeft;
        delete rtlStyles.marginLeft;
    }

    if (rtlStyles.marginRight !== undefined) {
        rtlStyles.marginLeft = rtlStyles.marginRight;
        delete rtlStyles.marginRight;
    }

    if (rtlStyles.paddingLeft !== undefined) {
        rtlStyles.paddingRight = rtlStyles.paddingLeft;
        delete rtlStyles.paddingLeft;
    }

    if (rtlStyles.paddingRight !== undefined) {
        rtlStyles.paddingLeft = rtlStyles.paddingRight;
        delete rtlStyles.paddingRight;
    }

    if (rtlStyles.left !== undefined) {
        rtlStyles.right = rtlStyles.left;
        delete rtlStyles.left;
    }

    if (rtlStyles.right !== undefined) {
        rtlStyles.left = rtlStyles.right;
        delete rtlStyles.right;
    }

    if (rtlStyles.textAlign === 'left') {
        rtlStyles.textAlign = 'right';
    } else if (rtlStyles.textAlign === 'right') {
        rtlStyles.textAlign = 'left';
    }

    return rtlStyles;
}

/**
 * RTL 感知的 Flexbox 方向
 *
 * @param locale 当前语言
 * @param direction Flex 方向
 * @returns 适合当前语言的 Flex 方向
 */
export function getRTLFlexDirection(
    locale: Locale,
    direction: 'row' | 'row-reverse' | 'column' | 'column-reverse'
): 'row' | 'row-reverse' | 'column' | 'column-reverse' {
    if (!isRTL(locale)) {
        return direction;
    }

    // 在 RTL 模式下，反转 row 方向
    if (direction === 'row') {
        return 'row-reverse';
    }
    if (direction === 'row-reverse') {
        return 'row';
    }

    return direction;
}

/**
 * 获取 HTML dir 属性
 *
 * @param locale 当前语言
 * @returns 'rtl' 或 'ltr'
 */
export function getHTMLDir(locale: Locale): 'rtl' | 'ltr' {
    return getDirection(locale);
}

/**
 * 检查是否需要镜像图标
 *
 * @param locale 当前语言
 * @param iconName 图标名称
 * @returns 是否需要镜像
 */
export function shouldMirrorIcon(locale: Locale, iconName: string): boolean {
    if (!isRTL(locale)) {
        return false;
    }

    // 需要镜像的图标类型（方向性图标）
    const directionalIcons = [
        'arrow', 'chevron', 'angle', 'caret',
        'back', 'forward', 'next', 'previous',
        'left', 'right',
    ];

    return directionalIcons.some(type =>
        iconName.toLowerCase().includes(type)
    );
}

/**
 * RTL 安全的字符串截断
 *
 * @param text 文本
 * @param maxLength 最大长度
 * @param locale 当前语言
 * @returns 截断后的文本
 */
export function truncateTextRTL(
    text: string,
    maxLength: number,
    locale: Locale
): string {
    if (text.length <= maxLength) {
        return text;
    }

    const truncated = text.substring(0, maxLength - 3);

    // RTL 语言的省略号在左边
    if (isRTL(locale)) {
        return '...' + truncated;
    }

    return truncated + '...';
}

/**
 * 应用 RTL 到 document
 *
 * @param locale 当前语言
 */
export function applyRTLToDocument(locale: Locale): void {
    const dir = getHTMLDir(locale);

    if (typeof document !== 'undefined') {
        document.documentElement.dir = dir;
        document.documentElement.lang = locale;

        // 添加 RTL 类到 body
        if (dir === 'rtl') {
            document.body.classList.add('rtl');
            document.body.classList.remove('ltr');
        } else {
            document.body.classList.add('ltr');
            document.body.classList.remove('rtl');
        }
    }
}
