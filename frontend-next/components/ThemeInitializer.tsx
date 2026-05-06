'use client';

import {useEffect} from 'react';

/**
 * 极简主题初始化组件
 * 只负责确保深色模式类正确设置
 */
export default function ThemeInitializer({children}: { children: React.ReactNode }) {
    useEffect(() => {
        // 从 cookie 读取主题并应用
        const getThemeFromCookie = () => {
            const cookies = document.cookie.split(';');
            for (const cookie of cookies) {
                const [name, value] = cookie.trim().split('=');
                if (name === 'theme') {
                    return value;
                }
            }
            return null;
        };

        const theme = getThemeFromCookie();
        const root = document.documentElement;

        if (theme === 'dark') {
            root.classList.add('dark');
        } else if (theme === 'light') {
            root.classList.remove('dark');
        } else if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
            // 如果没有设置主题，使用系统偏好
            root.classList.add('dark');
        }
    }, []);

    return <>{children}</>;
}
