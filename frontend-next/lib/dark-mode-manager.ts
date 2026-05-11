/**
 * 深色模式管理器 - 统一管理深色模式的切换和状态
 */

export type Theme = 'light' | 'dark';

class DarkModeManager {
    private static instance: DarkModeManager;
    private currentTheme: Theme = 'light';
    private listeners: Array<(theme: Theme) => void> = [];

    private constructor() {
        // 初始化时从 cookie 或系统偏好读取
        if (typeof window !== 'undefined') {
            // ✅ 只在第一次初始化时清理 localStorage，避免重复操作
            const hasInitialized = sessionStorage.getItem('darkModeInitialized');
            if (!hasInitialized) {
                try {
                    localStorage.removeItem('theme');
                    sessionStorage.setItem('darkModeInitialized', 'true');
                } catch (e) {
                    // 忽略错误
                }
            }

            const savedTheme = this.getThemeFromCookie();
            if (savedTheme && (savedTheme === 'light' || savedTheme === 'dark')) {
                this.currentTheme = savedTheme;
            } else if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
                this.currentTheme = 'dark';
            }

            // 应用初始主题
            this.applyTheme(this.currentTheme);
        }
    }

    public static getInstance(): DarkModeManager {
        if (!DarkModeManager.instance) {
            DarkModeManager.instance = new DarkModeManager();
        }
        return DarkModeManager.instance;
    }

    /**
     * 获取当前主题
     */
    public getTheme(): Theme {
        return this.currentTheme;
    }

    /**
     * 设置主题
     */
    public setTheme(theme: Theme): void {
        if (this.currentTheme !== theme) {
            this.currentTheme = theme;
            this.applyTheme(theme);
            this.notifyListeners();
        }
    }

    /**
     * 切换主题
     */
    public toggleTheme(): void {
        const newTheme = this.currentTheme === 'light' ? 'dark' : 'light';
        this.setTheme(newTheme);
    }

    /**
     * 监听系统主题变化
     */
    public watchSystemTheme(): () => void {
        if (typeof window !== 'undefined') {
            const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');

            const handleChange = (e: MediaQueryListEvent) => {
                // 只有当用户没有手动设置主题时才跟随系统
                const savedTheme = this.getThemeFromCookie();
                if (!savedTheme) {
                    this.setTheme(e.matches ? 'dark' : 'light');
                }
            };

            mediaQuery.addEventListener('change', handleChange);

            // 返回清理函数
            return () => {
                mediaQuery.removeEventListener('change', handleChange);
            };
        }

        // 在非浏览器环境中返回空函数
        return () => {
        };
    }

    /**
     * 应用主题到 DOM
     */
    private applyTheme(theme: Theme): void {
        if (typeof document !== 'undefined') {
            const root = document.documentElement;

            if (theme === 'dark') {
                root.classList.add('dark');
            } else {
                root.classList.remove('dark');
            }

            // ✅ 只使用 cookie，不再使用 localStorage
            this.setThemeCookie(theme);
        }
    }

    /**
     * 设置主题 cookie
     */
    private setThemeCookie(theme: Theme): void {
        if (typeof document !== 'undefined') {
            // 设置 cookie，有效期 365 天
            const expires = new Date();
            expires.setFullYear(expires.getFullYear() + 1);
            document.cookie = `theme=${theme};expires=${expires.toUTCString()};path=/;SameSite=Lax`;
        }
    }

    /**
     * 添加主题变化监听器
     */
    public addListener(listener: (theme: Theme) => void): () => void {
        this.listeners.push(listener);

        // 返回取消订阅函数
        return () => {
            this.listeners = this.listeners.filter(l => l !== listener);
        };
    }

    /**
     * 通知所有监听器
     */
    private notifyListeners(): void {
        this.listeners.forEach(listener => listener(this.currentTheme));
    }

    /**
     * 从 cookie 获取主题
     */
    private getThemeFromCookie(): Theme | null {
        if (typeof document === 'undefined') return null;

        const cookies = document.cookie.split(';');
        for (const cookie of cookies) {
            const [name, value] = cookie.trim().split('=');
            if (name === 'theme') {
                return value as Theme;
            }
        }
        return null;
    }
}

// 导出单例实例
export const darkModeManager = DarkModeManager.getInstance();

// 导出 React Hook
import {useEffect, useState} from 'react';

export function useDarkMode() {
    const [theme, setTheme] = useState<Theme>(darkModeManager.getTheme());

    useEffect(() => {
        const unsubscribe = darkModeManager.addListener((newTheme) => {
            setTheme(newTheme);
        });

        return unsubscribe;
    }, []);

    const toggleTheme = () => {
        darkModeManager.toggleTheme();
    };

    const setManualTheme = (newTheme: Theme) => {
        darkModeManager.setTheme(newTheme);
    };

    return {
        theme,
        toggleTheme,
        setTheme: setManualTheme,
        isDark: theme === 'dark'
    };
}