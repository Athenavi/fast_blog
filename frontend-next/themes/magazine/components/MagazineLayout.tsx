/**
 * Magazine主题 - 布局组件
 * 杂志风格布局，支持网格展示、特色文章和多栏目
 */
'use client';

import React, {useState, useEffect} from 'react';
import {MagazineHeader} from './MagazineHeader';
import {MagazineFooter} from './MagazineFooter';
import {useTheme} from '@/hooks/useTheme';

interface MagazineLayoutProps {
    children: React.ReactNode;
}

export const MagazineLayout: React.FC<MagazineLayoutProps> = ({children}) => {
    const {config} = useTheme();
    const [isMounted, setIsMounted] = useState(false);
    const [darkMode, setDarkMode] = useState(false);

    // 获取主题配置
    const themeConfig = config?.config || {};
    const colors = (themeConfig as any).colors || {};
    const features = (themeConfig as any).features || {};

    // 初始化挂载状态
    useEffect(() => {
        setIsMounted(true);
    }, []);

    // 暗色模式支持
    useEffect(() => {
        if (features.enableDarkMode) {
            const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
            const autoDarkMode = features.autoDarkMode ?? false;

            if (autoDarkMode) {
                setDarkMode(prefersDark);
                const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
                const handleChange = (e: MediaQueryListEvent) => setDarkMode(e.matches);
                mediaQuery.addEventListener('change', handleChange);
                return () => mediaQuery.removeEventListener('change', handleChange);
            }
        }
    }, [features]);

    if (!isMounted) {
        return <div className="min-h-screen bg-white">{children}</div>;
    }

    return (
        <div className={`min-h-screen flex flex-col transition-colors duration-300 ${
            darkMode ? 'bg-gray-900' : 'bg-white'
        }`}>
            {/* 全局样式注入 */}
            <style jsx global>{`
                :root {
                    --magazine-primary: ${colors.primary || '#dc2626'};
                    --magazine-secondary: ${colors.secondary || '#1f2937'};
                    --magazine-accent: ${colors.accent || '#f59e0b'};
                    --magazine-background: ${darkMode ? '#111827' : colors.background || '#ffffff'};
                    --magazine-foreground: ${darkMode ? '#f9fafb' : colors.foreground || '#111827'};
                    --magazine-muted: ${darkMode ? '#374151' : colors.muted || '#f9fafb'};
                    --magazine-border: ${darkMode ? '#4b5563' : colors.border || '#e5e7eb'};
                }

                body {
                    font-family: ${themeConfig.typography?.fontFamily || 'Merriweather, Georgia, serif'};
                    font-size: ${themeConfig.typography?.fontSize || '16px'};
                    line-height: ${themeConfig.typography?.lineHeight || 1.8};
                    color: var(--magazine-foreground);
                    background-color: var(--magazine-background);
                }

                h1, h2, h3, h4, h5, h6 {
                    font-family: ${themeConfig.typography?.headingFont || 'Montserrat, sans-serif'};
                    font-weight: ${themeConfig.typography?.headingWeight || 800};
                    letter-spacing: -0.02em;
                }
            `}</style>

            <MagazineHeader darkMode={darkMode} />
            <main className="flex-grow">
                {children}
            </main>
            <MagazineFooter darkMode={darkMode} />
        </div>
    );
};

export default MagazineLayout;
