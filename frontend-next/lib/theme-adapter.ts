/**
 * 主题适配器 - 将硬编码的 Tailwind 颜色映射到主题变量
 *
 * 这个模块会在主题切换时自动运行，扫描页面中所有使用硬编码颜色的元素，
 * 并将它们替换为主题变量的引用。
 */

interface ThemeColors {
    primary?: string;
    secondary?: string;
    accent?: string;
    background?: string;
    foreground?: string;
    muted?: string;
    border?: string;
}

/**
 * 颜色映射表 - Tailwind 默认颜色到主题变量的映射
 */
const COLOR_MAPPING: Record<string, string> = {
    // 背景色
    '#f9fafb': 'var(--color-background)',  // gray-50
    '#f3f4f6': 'var(--color-muted)',        // gray-100
    '#ffffff': 'var(--color-background)',   // white

    // 文字色
    '#111827': 'var(--color-foreground)',   // gray-900
    '#1f2937': 'var(--color-foreground)',   // gray-800
    '#374151': 'var(--color-foreground)',   // gray-700
    '#4b5563': 'var(--color-secondary)',    // gray-600
    '#6b7280': 'var(--color-secondary)',    // gray-500
    '#9ca3af': 'var(--color-secondary)',    // gray-400
    '#000000': 'var(--color-foreground)',   // black

    // 主题色
    '#2563eb': 'var(--color-primary)',      // blue-600
    '#4f46e5': 'var(--color-primary)',      // indigo-600
    '#9333ea': 'var(--color-primary)',      // purple-600
    '#dc2626': 'var(--color-primary)',      // red-600

    // 边框色
    '#d1d5db': 'var(--color-border)',       // gray-300
    '#e5e7eb': 'var(--color-border)',       // gray-200
};

/**
 * 渐变映射表
 */
const GRADIENT_MAPPING: Record<string, string> = {
    'linear-gradient(to bottom right, rgb(79, 70, 229), rgb(168, 85, 247), rgb(236, 72, 153))':
        'linear-gradient(to bottom right, var(--color-primary), var(--color-accent))',
    'linear-gradient(to right, rgb(37, 99, 235), rgb(147, 51, 234))':
        'linear-gradient(to right, var(--color-primary), var(--color-secondary))',
    'linear-gradient(to bottom right, rgb(239, 68, 68), rgb(249, 115, 22))':
        'linear-gradient(to bottom right, var(--color-primary), var(--color-accent))',
};

/**
 * 应用主题适配
 */
export function applyThemeAdaptation(colors: ThemeColors): void {
    if (!colors || Object.keys(colors).length === 0) {
        return;
    }

    console.log('[ThemeAdapter] 开始应用主题适配', colors);

    // 1. 注入CSS变量覆盖规则
    injectColorOverrides(colors);

    // 2. 扫描并替换内联样式
    replaceInlineStyles();

    console.log('[ThemeAdapter] 主题适配完成');
}

/**
 * 注入颜色覆盖规则
 */
function injectColorOverrides(colors: ThemeColors): void {
    const styleId = 'theme-color-overrides';
    let styleElement = document.getElementById(styleId) as HTMLStyleElement;

    if (!styleElement) {
        styleElement = document.createElement('style');
        styleElement.id = styleId;
        document.head.appendChild(styleElement);
    }

    const rules = generateOverrideRules(colors);
    styleElement.textContent = rules;
}

/**
 * 生成覆盖规则
 */
function generateOverrideRules(colors: ThemeColors): string {
    const primary = colors.primary || '#3b82f6';
    const secondary = colors.secondary || '#64748b';
    const accent = colors.accent || '#f59e0b';
    const background = colors.background || '#ffffff';
    const foreground = colors.foreground || '#1f2937';
    const muted = colors.muted || '#f3f4f6';
    const border = colors.border || '#e5e7eb';

    return `
        /* 动态生成的主题颜色覆盖 */
        
        /* 背景色 */
        .bg-gray-50, .bg-white { background-color: ${background} !important; }
        .bg-gray-100 { background-color: ${muted} !important; }
        [class*="dark:bg-gray-900"] { background-color: ${background} !important; }
        [class*="dark:bg-gray-800"] { background-color: ${muted} !important; }
        
        /* 文字色 */
        .text-gray-900, .text-gray-800, .text-gray-700 { color: ${foreground} !important; }
        .text-gray-600, .text-gray-500, .text-gray-400 { color: ${secondary} !important; }
        .text-white { color: ${background} !important; }
        
        /* 主题色 */
        [class*="bg-blue-600"], [class*="bg-indigo-600"], [class*="bg-purple-600"] { 
            background-color: ${primary} !important; 
        }
        [class*="text-blue-600"], [class*="text-indigo-600"] { 
            color: ${primary} !important; 
        }
        
        /* 边框 */
        [class*="border-gray-"] { border-color: ${border} !important; }
        
        /* 渐变背景 */
        [class*="from-indigo-600"][class*="via-purple-600"][class*="to-pink-500"] {
            background: linear-gradient(to bottom right, ${primary}, ${accent}) !important;
        }
        [class*="from-blue-600"][class*="to-purple-600"] {
            background: linear-gradient(to right, ${primary}, ${secondary}) !important;
        }
    `;
}

/**
 * 替换内联样式中的颜色值
 */
function replaceInlineStyles(): void {
    // 查找所有带有 style 属性的元素
    const elementsWithStyle = document.querySelectorAll('[style]');

    elementsWithStyle.forEach(element => {
        const htmlElement = element as HTMLElement;
        const inlineStyle = htmlElement.style.cssText;

        if (!inlineStyle) return;

        let newStyle = inlineStyle;

        // 替换背景色
        Object.entries(COLOR_MAPPING).forEach(([hexColor, cssVar]) => {
            const regex = new RegExp(hexColor, 'gi');
            newStyle = newStyle.replace(regex, cssVar);
        });

        // 替换渐变
        Object.entries(GRADIENT_MAPPING).forEach(([gradient, replacement]) => {
            if (newStyle.includes(gradient)) {
                newStyle = newStyle.replace(gradient, replacement);
            }
        });

        // 如果样式有变化，更新它
        if (newStyle !== inlineStyle) {
            htmlElement.style.cssText = newStyle;
        }
    });
}

/**
 * 监听DOM变化，自动适配新添加的元素
 */
export function observeThemeChanges(): void {
    const observer = new MutationObserver((mutations) => {
        mutations.forEach((mutation) => {
            if (mutation.addedNodes.length > 0) {
                // 有新节点添加，重新应用适配
                replaceInlineStyles();
            }
        });
    });

    observer.observe(document.body, {
        childList: true,
        subtree: true,
    });

    console.log('[ThemeAdapter] 已启动 DOM 观察器');
}
