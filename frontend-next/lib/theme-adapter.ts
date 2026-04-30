/**
 * 主题适配器 - 将硬编码的 Tailwind 颜色映射到主题变量
 *
 * 这个模块会在主题切换时自动运行，扫描页面中所有使用硬编码颜色的元素，
 * 并将它们替换为主题变量的引用。
 */

import {darkModeManager} from './dark-mode-manager';

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
 * 深色模式颜色配置
 */
const DARK_MODE_COLORS: Record<string, string> = {
    background: '#0f172a',    // slate-900
    foreground: '#f1f5f9',    // slate-100
    muted: '#1e293b',         // slate-800
    border: '#334155',        // slate-700
    primary: '#3b82f6',       // blue-500 (保持主色调)
    secondary: '#94a3b8',     // slate-400
    accent: '#f59e0b',        // amber-500 (保持强调色)
};

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

    const isDark = darkModeManager.getTheme() === 'dark';
    console.log(`[ThemeAdapter] 开始应用主题适配 (${isDark ? '深色' : '浅色'}模式)`, colors);

    // 1. 注入CSS变量覆盖规则
    injectColorOverrides(colors, isDark);

    // 2. 扫描并替换内联样式
    replaceInlineStyles(isDark);

    console.log('[ThemeAdapter] 主题适配完成');
}

/**
 * 注入颜色覆盖规则
 */
function injectColorOverrides(colors: ThemeColors, isDark: boolean): void {
    const styleId = 'theme-color-overrides';
    let styleElement = document.getElementById(styleId) as HTMLStyleElement;

    if (!styleElement) {
        styleElement = document.createElement('style');
        styleElement.id = styleId;
        document.head.appendChild(styleElement);
    }

    const rules = generateOverrideRules(colors, isDark);
    // 只在客户端执行，避免服务端和客户端不一致
    if (typeof window !== 'undefined') {
        styleElement.textContent = rules;
    }
}

/**
 * 生成覆盖规则
 */
function generateOverrideRules(colors: ThemeColors, isDark: boolean): string {
    // 根据深色模式调整颜色
    const baseColors = isDark
        ? {...colors, ...DARK_MODE_COLORS}
        : colors;

    const primary = baseColors.primary || '#3b82f6';
    const secondary = baseColors.secondary || '#64748b';
    const accent = baseColors.accent || '#f59e0b';
    const background = baseColors.background || '#ffffff';
    const foreground = baseColors.foreground || '#1f2937';
    const muted = baseColors.muted || '#f3f4f6';
    const border = baseColors.border || '#e5e7eb';

    return `
        /* 动态生成的主题颜色覆盖 - ${isDark ? '深色' : '浅色'}模式 */
        
        /* 背景色 */
        .bg-gray-50, .bg-white { background-color: ${background} !important; }
        .bg-gray-100 { background-color: ${muted} !important; }
        [class*="dark:bg-gray-900"] { background-color: ${background} !important; }
        [class*="dark:bg-gray-800"] { background-color: ${muted} !important; }
        
        /* 文字色 */
        .text-gray-900, .text-gray-800, .text-gray-700 { color: ${foreground} !important; }
        .text-gray-600, .text-gray-500, .text-gray-400 { color: ${secondary} !important; }
        .text-white { color: ${isDark ? foreground : background} !important; }
        
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
        
        /* 卡片和容器背景 */
        .bg-card, [class*="bg-white"] { background-color: ${background} !important; }
        .dark .bg-card, .dark [class*="bg-white"] { background-color: ${isDark ? background : '#1f2937'} !important; }
    `;
}

/**
 * 替换内联样式中的颜色值
 */
function replaceInlineStyles(isDark: boolean): void {
    // 只在客户端执行，避免服务端和客户端不一致
    if (typeof window === 'undefined') return;
    
    // 查找所有带有 style 属性的元素
    const elementsWithStyle = document.querySelectorAll('[style]');

    elementsWithStyle.forEach(element => {
        const htmlElement = element as HTMLElement;
        const inlineStyle = htmlElement.style.cssText;

        if (!inlineStyle) return;

        let newStyle = inlineStyle;

        // 根据深色模式选择颜色映射
        const colorMapping = isDark
            ? {...COLOR_MAPPING, ...createDarkModeMapping()}
            : COLOR_MAPPING;

        // 替换背景色
        Object.entries(colorMapping).forEach(([hexColor, cssVar]) => {
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
 * 创建深色模式颜色映射
 */
function createDarkModeMapping(): Record<string, string> {
    return {
        // 深色模式下的背景色映射
        '#ffffff': 'var(--color-background)',   // white -> dark background
        '#f9fafb': 'var(--color-muted)',        // gray-50 -> dark muted
        '#f3f4f6': 'var(--color-muted)',        // gray-100 -> dark muted

        // 深色模式下的文字色映射
        '#111827': 'var(--color-foreground)',   // gray-900 -> light text
        '#1f2937': 'var(--color-foreground)',   // gray-800 -> light text
        '#374151': 'var(--color-foreground)',   // gray-700 -> light text
    };
}

/**
 * 监听DOM变化，自动适配新添加的元素
 */
export function observeThemeChanges(): void {
    // 只在客户端执行，避免服务端和客户端不一致
    if (typeof window === 'undefined') return;
    
    const observer = new MutationObserver((mutations) => {
        mutations.forEach((mutation) => {
            if (mutation.addedNodes.length > 0) {
                // 有新节点添加，重新应用适配
                const isDark = darkModeManager.getTheme() === 'dark';
                replaceInlineStyles(isDark);
            }
        });
    });

    observer.observe(document.body, {
        childList: true,
        subtree: true,
    });

    console.log('[ThemeAdapter] 已启动 DOM 观察器');
}
