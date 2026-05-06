'use client';

import React, {useEffect} from 'react';
import {usePathname} from 'next/navigation';
import {ThemeDataProvider, useTheme} from '@/hooks/useTheme';

interface ThemeProviderProps {
    children: React.ReactNode;
}

/**
 * 极简主题提供者 - 重构版
 * 核心原则：
 * 1. 不修改 DOM（除了注入 CSS 变量和样式表）
 * 2. 不使用复杂的依赖项
 * 3. 不调用任何会修改元素样式的函数
 */
export const ThemeProvider: React.FC<ThemeProviderProps> = ({children}) => {
    return (
        <ThemeDataProvider>
            <ThemeInjector>{children}</ThemeInjector>
        </ThemeDataProvider>
    );
};

// 内部组件：只负责注入 CSS，不做其他操作
const ThemeInjector: React.FC<{ children: React.ReactNode }> = ({children}) => {
    const pathname = usePathname();
    const isAdminPage = pathname?.startsWith('/admin');
    const theme = useTheme();

    const {cssVariables, stylesheetUrl} = theme;

    // 只在客户端注入样式表
    useEffect(() => {
        if (isAdminPage || typeof window === 'undefined') return;
        
        if (stylesheetUrl) {
            let linkElement = document.getElementById('theme-stylesheet') as HTMLLinkElement;

            if (!linkElement) {
                linkElement = document.createElement('link');
                linkElement.id = 'theme-stylesheet';
                linkElement.rel = 'stylesheet';
                document.head.appendChild(linkElement);
            }

            // 只有当 URL 真正不同时才更新，避免不必要的重渲染
            if (linkElement.href !== stylesheetUrl && !linkElement.href.endsWith(stylesheetUrl)) {
                linkElement.href = stylesheetUrl;
            }
        }
    }, [stylesheetUrl, isAdminPage]);

    // 管理后台直接渲染
    if (isAdminPage) {
        return <>{children}</>;
    }

    // ✅ 始终渲染子组件，不再显示加载状态
    // 主题变量会在后台加载，加载完成后自动应用
    return (
        <>
            {/* 注入主题CSS变量 */}
            {cssVariables && (
                <style
                    id="theme-variables"
                    dangerouslySetInnerHTML={{__html: cssVariables}}
                    suppressHydrationWarning
                />
            )}
            {children}
        </>
    );
};

export default ThemeProvider;
