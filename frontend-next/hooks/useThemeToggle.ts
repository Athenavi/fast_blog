'use client';

import {useState, useEffect} from 'react';

type Theme = 'light' | 'dark';

export function useThemeToggle() {
    const [theme, setTheme] = useState<Theme>('light');

    // 初始化主题
    useEffect(() => {
        // 检查 localStorage 或系统偏好
        const savedTheme = localStorage.getItem('theme') as Theme;
        if (savedTheme) {
            setTheme(savedTheme);
        } else if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
            setTheme('dark');
        }
    }, []);

    // 应用主题
    useEffect(() => {
        const root = document.documentElement;

        if (theme === 'dark') {
            root.classList.add('dark');
        } else {
            root.classList.remove('dark');
        }

        localStorage.setItem('theme', theme);
    }, [theme]);

    // 切换主题
    const toggleTheme = () => {
        setTheme(prev => prev === 'light' ? 'dark' : 'light');
    };

    return {
        theme,
        toggleTheme,
    };
}
