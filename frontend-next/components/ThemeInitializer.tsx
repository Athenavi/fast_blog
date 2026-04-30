'use client';

import {useEffect} from 'react';
import {darkModeManager} from '@/lib/dark-mode-manager';

/**
 * 主题初始化组件
 * 确保主题在客户端正确初始化和同步
 */
export default function ThemeInitializer({children}: { children: React.ReactNode }) {
    useEffect(() => {
        // 初始化深色模式管理器
        const currentTheme = darkModeManager.getTheme();

        // 确保 HTML 元素上的 dark 类与当前主题状态同步
        const root = document.documentElement;

        if (currentTheme === 'dark') {
            root.classList.add('dark');
        } else {
            root.classList.remove('dark');
        }

        // 启动系统主题监听
        darkModeManager.watchSystemTheme();
    }, []);

    return <>{children}</>;
}
