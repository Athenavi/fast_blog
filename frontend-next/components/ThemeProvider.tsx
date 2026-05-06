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

    const {cssVariables, stylesheetUrl, isLoading} = theme;

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

            if (linkElement.href !== stylesheetUrl) {
                linkElement.href = stylesheetUrl;
            }
        }
    }, [stylesheetUrl, isAdminPage]);

    // 管理后台直接渲染
    if (isAdminPage) {
        return <>{children}</>;
    }

    // 加载中状态
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

    // 渲染主题 CSS 变量和子组件
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
