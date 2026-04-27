/**
 * Modern Minimal Theme Layout Component
 * 现代简约主题布局组件
 */
'use client';

import React, {useState, useEffect} from 'react';
import {useTheme} from '@/hooks/useTheme';
import {useThemeStyles} from '@/hooks/useThemeStyles';

interface ModernMinimalLayoutProps {
    children: React.ReactNode;
}

const ModernMinimalLayout: React.FC<ModernMinimalLayoutProps> = ({children}) => {
    const {config} = useTheme();
    const [isMounted, setIsMounted] = useState(false);

    // 初始化主题样式
    useEffect(() => {
        setIsMounted(true);
    }, []);

    if (!isMounted) {
        return <div className="min-h-screen">{children}</div>;
    }

    // 获取主题配置
    const themeConfig = config?.config || {};
    const colors = (themeConfig as any).colors || {};
    const features = (themeConfig as any).features || {};

    // 应用暗色模式
    const [darkMode, setDarkMode] = useState(false);

    useEffect(() => {
        const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        const autoDarkMode = features.autoDarkMode ?? true;

        if (autoDarkMode) {
            setDarkMode(prefersDark);

            const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
            const handleChange = (e: MediaQueryListEvent) => setDarkMode(e.matches);

            mediaQuery.addEventListener('change', handleChange);
            return () => mediaQuery.removeEventListener('change', handleChange);
        }
    }, [features]);

    return (
        <div
            className={`min-h-screen transition-colors duration-300 ${
                darkMode
                    ? 'bg-gray-900 text-gray-100'
                    : 'bg-white text-gray-900'
            }`}
            style={{
                backgroundColor: darkMode ? colors.background || '#0f172a' : colors.background || '#ffffff',
                color: darkMode ? colors.foreground || '#e2e8f0' : colors.foreground || '#1f2937',
            }}
        >
            {/* 全局样式 */}
            <style jsx global>{`
                :root {
                    --color-primary: ${colors.primary || '#3b82f6'};
                    --color-secondary: ${colors.secondary || '#64748b'};
                    --color-accent: ${colors.accent || '#f59e0b'};
                    --color-background: ${colors.background || '#ffffff'};
                    --color-foreground: ${colors.foreground || '#1f2937'};
                    --color-muted: ${colors.muted || '#f3f4f6'};
                    --color-border: ${colors.border || '#e5e7eb'};
                    --color-code-background: ${colors.code_background || '#1e293b'};
                    --color-code-text: ${colors.code_text || '#e2e8f0'};
                }

                body {
                    font-family: ${themeConfig?.typography?.fontFamily || 'Inter, system-ui, sans-serif'};
                    font-size: ${themeConfig?.typography?.fontSize || '16px'};
                    line-height: ${themeConfig?.typography?.lineHeight || 1.75};
                }

                .code-block {
                    background-color: var(--color-code-background);
                    color: var(--color-code-text);
                    font-family: ${themeConfig.typography?.codeFont || 'monospace'};
                }
            `}</style>

            <div className="max-w-7xl mx-auto">
                {children}
            </div>
        </div>
    );
};

export default ModernMinimalLayout;
