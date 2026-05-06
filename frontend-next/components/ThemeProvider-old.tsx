'use client';

import React, {useEffect, useRef} from 'react';
import {usePathname} from 'next/navigation';
import useTheme, {ThemeContext} from '@/hooks/useTheme';
import {darkModeManager} from '@/lib/dark-mode-manager';

interface ThemeProviderProps {
    children: React.ReactNode;
}

/**
 * 主题提供者组件
 * 确保所有页面都能正确加载和应用主题样式
 * 注意：/admin/* 路径下的页面会跳过主题加载
 */
export const ThemeProvider: React.FC<ThemeProviderProps> = ({children}) => {
    // ✅ 在 TSX 文件中创建 Provider，调用 useTheme
    const theme = useTheme();

    return (
        <ThemeContext.Provider value={theme}>
            <ThemeProviderContent>{children}</ThemeProviderContent>
        </ThemeContext.Provider>
    );
};

// ✅ 内部组件，使用 Context
const ThemeProviderContent: React.FC<ThemeProviderProps> = ({children}) => {
    const pathname = usePathname();
    const isAdminPage = pathname?.startsWith('/admin');

    // ✅ 使用 Context，确保全局共享同一个实例
    const themeHook = React.useContext(ThemeContext);
    if (!themeHook) {
        throw new Error('ThemeProviderContent must be used within ThemeProvider');
    }

    const {cssVariables, stylesheetUrl, isLoading, config} = themeHook;

    // ✅ 使用 ref 跟踪是否已经应用过主题，避免重复应用
    const hasAppliedTheme = useRef(false);
    const previousColorsRef = useRef<string>('');

    // 应用主题样式表
    useEffect(() => {
        // 如果是管理后台页面，不加载主题
        if (isAdminPage) return;

        // 只在客户端执行
        if (typeof window === 'undefined') return;

        if (stylesheetUrl) {
            let linkElement = document.getElementById('theme-stylesheet') as HTMLLinkElement;

            if (!linkElement) {
                linkElement = document.createElement('link');
                linkElement.id = 'theme-stylesheet';
                linkElement.rel = 'stylesheet';
                document.head.appendChild(linkElement);
            }

            // 只有当URL真正变化时才更新
            if (linkElement.href !== stylesheetUrl) {
                linkElement.href = stylesheetUrl;
            }
        }
    }, [stylesheetUrl, isAdminPage]);

    // ✅ 简化的主题应用逻辑 - 只注入 CSS 变量，不再修改 DOM
    useEffect(() => {
        // 如果是管理后台页面，不加载主题
        if (isAdminPage) return;

        // 只在客户端执行
        if (typeof window === 'undefined') return;

        if (config && config.config && config.config.colors) {
            const colors = config.config.colors;
            const colorsString = JSON.stringify(colors);

            // ✅ 只有当颜色真正变化时才重新应用
            if (previousColorsRef.current === colorsString && hasAppliedTheme.current) {
                console.log('[ThemeProvider] 主题颜色未变化，跳过应用');
                return;
            }

            console.log('[ThemeProvider] 应用主题颜色:', colors);
            previousColorsRef.current = colorsString;
            hasAppliedTheme.current = true;

            // ✅ 只通过 CSS 变量来应用主题，不直接修改 DOM 元素样式
            // CSS 变量已经在第 172 行的 style 标签中注入，这里不需要额外操作
            // applyThemeAdaptation 会修改 DOM，导致无限循环，已移除
        }
    }, [config, isAdminPage]);

    // 监听深色模式变化并重新应用主题
    useEffect(() => {
        // 如果是管理后台页面，不加载主题
        if (isAdminPage) return;

        const unsubscribe = darkModeManager.addListener((newTheme) => {
            console.log('[ThemeProvider] 深色模式变化为:', newTheme);
            // ✅ 深色模式通过 CSS 的 .dark 类处理，不需要额外操作
            // CSS 变量会自动适配，因为我们在 CSS 中定义了 .dark 下的变量值
        });

        return unsubscribe;
    }, [isAdminPage]);

    // 如果是管理后台页面，直接渲染子组件，不加载主题
    if (isAdminPage) {
        return <>{children}</>;
    }

    // 如果正在加载主题，显示简单的加载状态
    if (isLoading) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
                <div className="text-center">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
                    <p className="text-gray-600 dark:text-gray-400">加载中...</p>
                </div>
            </div>
        );
    }

    return (
        <>
            {/* 注入主题CSS变量 */}
            <style id="theme-variables" dangerouslySetInnerHTML={{__html: cssVariables}} suppressHydrationWarning/>
            {children}
        </>
    );
};

export default ThemeProvider;
