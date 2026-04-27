/**
 * 主题样式Hook - 提供基于主题的内联样式
 * 用于替代硬编码的Tailwind颜色类
 */

import {useMemo} from 'react';
import useTheme from './useTheme';

/**
 * 获取主题渐变背景样式
 */
export function useThemeGradient(from: string = 'primary', to: string = 'accent') {
    const {config} = useTheme();

    return useMemo(() => {
        const colors = config?.config?.colors || {};
        const fromColor = colors[from] || colors.primary || '#3b82f6';
        const toColor = colors[to] || colors.accent || '#f59e0b';

        return {
            background: `linear-gradient(to bottom right, ${fromColor}, ${toColor})`,
        };
    }, [config, from, to]);
}

/**
 * 获取主题文字颜色样式
 */
export function useThemeTextColor(level: 'primary' | 'secondary' | 'muted' = 'primary') {
    const {config} = useTheme();

    return useMemo(() => {
        const colors = config?.config?.colors || {};

        const colorMap = {
            primary: colors.foreground || '#1f2937',
            secondary: colors.secondary || '#64748b',
            muted: colors.muted || '#f3f4f6',
        };

        return {
            color: colorMap[level],
        };
    }, [config, level]);
}

/**
 * 获取主题背景颜色样式
 */
export function useThemeBgColor(type: 'background' | 'muted' | 'primary' = 'background') {
    const {config} = useTheme();

    return useMemo(() => {
        const colors = config?.config?.colors || {};

        const colorMap = {
            background: colors.background || '#ffffff',
            muted: colors.muted || '#f3f4f6',
            primary: colors.primary || '#3b82f6',
        };

        return {
            backgroundColor: colorMap[type],
        };
    }, [config, type]);
}

/**
 * 获取完整的主题样式对象
 */
export function useThemeStyles() {
    const {config} = useTheme();

    return useMemo(() => {
        const colors = config?.config?.colors || {};

        return {
            // 颜色
            primary: colors.primary || '#3b82f6',
            secondary: colors.secondary || '#64748b',
            accent: colors.accent || '#f59e0b',
            background: colors.background || '#ffffff',
            foreground: colors.foreground || '#1f2937',
            muted: colors.muted || '#f3f4f6',
            border: colors.border || '#e5e7eb',

            // 排版
            fontFamily: config?.config?.typography?.fontFamily || 'system-ui',
            fontSize: config?.config?.typography?.fontSize || '16px',
            lineHeight: config?.config?.typography?.lineHeight || 1.6,

            // 布局
            contentWidth: config?.config?.layout?.contentWidth || 'max-w-4xl',
            borderRadius: config?.config?.components?.borderRadius || '0.5rem',
        };
    }, [config]);
}

/**
 * 生成CSS变量内联样式（用于单个元素）
 */
export function useThemeCSSVariables() {
    const styles = useThemeStyles();

    return useMemo(() => {
        return {
            '--color-primary': styles.primary,
            '--color-secondary': styles.secondary,
            '--color-accent': styles.accent,
            '--color-background': styles.background,
            '--color-foreground': styles.foreground,
            '--color-muted': styles.muted,
            '--color-border': styles.border,
            '--font-family': styles.fontFamily,
            '--font-size-base': styles.fontSize,
            '--line-height': String(styles.lineHeight),
            '--content-width': styles.contentWidth,
            '--border-radius': styles.borderRadius,
        } as React.CSSProperties;
    }, [styles]);
}
