'use client';

import {useState, useEffect} from 'react';

type Theme = 'light' | 'dark';

// 全局主题状态
let globalTheme: Theme = 'light';
let listeners: Array<(theme: Theme) => void> = [];

function setGlobalTheme(theme: Theme) {
    globalTheme = theme;
    listeners.forEach(listener => listener(theme));
}

export function useThemeToggle() {
    const [theme, setTheme] = useState<Theme>(() => {
        // 初始化时从 localStorage 或系统偏好读取
        if (typeof window !== 'undefined') {
            const savedTheme = localStorage.getItem('theme') as Theme;
            if (savedTheme) {
                globalTheme = savedTheme;
                return savedTheme;
            } else if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
                globalTheme = 'dark';
                return 'dark';
            }
        }
        return globalTheme;
    });

    // 订阅全局主题变化
    useEffect(() => {
        const listener = (newTheme: Theme) => {
            setTheme(newTheme);
        };
        listeners.push(listener);

        return () => {
            listeners = listeners.filter(l => l !== listener);
        };
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
        setGlobalTheme(theme);
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
