/**
 * Modern Minimal Theme Layout Component
 * 现代简约主题布局组件 - 干净、优雅、响应式设计
 */
'use client';

import React, {useState, useEffect} from 'react';
import {useTheme} from '@/hooks/useTheme';
import ModernMinimalHeader from './ModernMinimalHeader';
import ModernMinimalFooter from './ModernMinimalFooter';

interface ModernMinimalLayoutProps {
    children: React.ReactNode;
}

const ModernMinimalLayout: React.FC<ModernMinimalLayoutProps> = ({children}) => {
    const {config} = useTheme();
    const [isMounted, setIsMounted] = useState(false);
    const [darkMode, setDarkMode] = useState(false);

    // 获取主题配置
    const themeConfig = config?.config || {};
    const colors = (themeConfig as any).colors || {};
    const features = (themeConfig as any).features || {};
    const layout = (themeConfig as any).layout || {};

    // 初始化挂载状态
    useEffect(() => {
        setIsMounted(true);
    }, []);

    // 暗色模式逻辑
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

    if (!isMounted) {
        return <div className="min-h-screen bg-white">{children}</div>;
    }

    return (
        <div
            className={`min-h-screen flex flex-col transition-colors duration-300 ${
                darkMode ? 'bg-gray-900' : 'bg-white'
            }`}
            style={{
                backgroundColor: darkMode ? colors.background || '#0f172a' : colors.background || '#ffffff',
                color: darkMode ? colors.foreground || '#e2e8f0' : colors.foreground || '#1f2937',
            }}
        >
            {/* 全局样式注入 */}
            <style jsx global>{`
                :root {
                    --modern-primary: ${colors.primary || '#3b82f6'};
                    --modern-secondary: ${colors.secondary || '#64748b'};
                    --modern-accent: ${colors.accent || '#f59e0b'};
                    --modern-background: ${darkMode ? colors.background || '#0f172a' : colors.background || '#ffffff'};
                    --modern-foreground: ${darkMode ? colors.foreground || '#e2e8f0' : colors.foreground || '#1f2937'};
                    --modern-muted: ${darkMode ? colors.muted || '#1e293b' : colors.muted || '#f3f4f6'};
                    --modern-border: ${darkMode ? colors.border || '#334155' : colors.border || '#e5e7eb'};
                    --modern-code-background: ${colors.code_background || '#1e293b'};
                    --modern-code-text: ${colors.code_text || '#e2e8f0'};
                }

                body {
                    font-family: ${themeConfig.typography?.fontFamily || 'Inter, system-ui, -apple-system, sans-serif'};
                    font-size: ${themeConfig.typography?.fontSize || '16px'};
                    line-height: ${themeConfig.typography?.lineHeight || 1.75};
                    -webkit-font-smoothing: antialiased;
                    -moz-osx-font-smoothing: grayscale;
                }

                h1, h2, h3, h4, h5, h6 {
                    font-weight: ${themeConfig.typography?.headingWeight || 600};
                    letter-spacing: ${themeConfig.typography?.headingLetterSpacing || '-0.025em'};
                    line-height: 1.2;
                }

                .code-block, pre, code {
                    background-color: var(--modern-code-background);
                    color: var(--modern-code-text);
                    font-family: ${themeConfig.typography?.codeFont || 'Fira Code, JetBrains Mono, monospace'};
                }

                /* 平滑滚动 */
                ${features.smoothScroll ? 'html { scroll-behavior: smooth; }' : ''}

                /* 图片懒加载优化 */
                ${features.lazyLoadImages ? 'img { loading: lazy; }' : ''}
            `}</style>

            <ModernMinimalHeader darkMode={darkMode} />
            
            <main className="flex-grow">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                    {children}
                </div>
            </main>
            
            <ModernMinimalFooter darkMode={darkMode} />
        </div>
    );
};

export default ModernMinimalLayout;
