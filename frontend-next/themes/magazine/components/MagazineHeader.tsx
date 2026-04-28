/**
 * Magazine主题 - Header组件
 * 杂志风格头部，支持Breaking News栏和粘性导航
 */
'use client';

import React, {useState, useEffect} from 'react';
import Link from 'next/link';
import {useTheme} from '@/hooks/useTheme';

interface MagazineHeaderProps {
    darkMode?: boolean;
}

export const MagazineHeader: React.FC<MagazineHeaderProps> = ({darkMode = false}) => {
    const {config} = useTheme();
    const [isScrolled, setIsScrolled] = useState(false);
    const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

    // 获取主题配置
    const themeConfig = config?.config || {};
    const colors = (themeConfig as any).colors || {};
    const features = (themeConfig as any).features || {};
    const layout = (themeConfig as any).layout || {};

    // 监听滚动，实现粘性头部效果
    useEffect(() => {
        const handleScroll = () => {
            setIsScrolled(window.scrollY > 50);
        };

        window.addEventListener('scroll', handleScroll);
        return () => window.removeEventListener('scroll', handleScroll);
    }, []);

    const navItems = ['首页', '科技', '商业', '文化', '生活', '关于'];

    return (
        <>
            {/* Breaking News Bar - 如果启用 */}
            {features.breakingNewsBar && (
                <div 
                    className="py-2 px-4 text-sm font-medium"
                    style={{
                        backgroundColor: colors.primary || '#dc2626',
                        color: '#ffffff'
                    }}
                >
                    <div className="container mx-auto max-w-7xl flex items-center gap-3">
                        <span className="font-bold uppercase tracking-wider">Breaking:</span>
                        <span className="truncate">欢迎来到 FastBlog Magazine - 深度报道与专业分析</span>
                    </div>
                </div>
            )}

            {/* 主头部 */}
            <header
                className={`transition-all duration-300 border-b-4 ${
                    isScrolled && features.stickyHeader ? 'sticky top-0 z-50 shadow-lg' : ''
                }`}
                style={{
                    borderColor: colors.primary || '#dc2626',
                    backgroundColor: darkMode ? '#1f2937' : colors.background || '#ffffff',
                    borderBottomColor: colors.primary || '#dc2626'
                }}
            >
                <div className="container mx-auto max-w-7xl px-4 py-6">
                    {/* Logo/标题区域 */}
                    <div className="text-center mb-6">
                        <Link href="/">
                            <h1
                                className="text-4xl md:text-5xl font-black uppercase tracking-tighter transition-colors"
                                style={{
                                    fontFamily: themeConfig.typography?.headingFont || 'Montserrat, sans-serif',
                                    color: darkMode ? '#f9fafb' : colors.foreground || '#111827'
                                }}
                            >
                                {config?.metadata?.name || 'FastBlog Magazine'}
                            </h1>
                        </Link>
                        <p 
                            className="mt-2 text-sm uppercase tracking-widest"
                            style={{color: darkMode ? '#9ca3af' : colors.secondary || '#6b7280'}}
                        >
                            深度报道 · 专业分析 · 权威资讯
                        </p>
                    </div>

                    {/* 导航菜单 */}
                    <nav className="flex items-center justify-between">
                        {/* 桌面端导航 */}
                        <div className="hidden md:flex justify-center flex-1 gap-1">
                            {navItems.map((item) => (
                                <Link
                                    key={item}
                                    href={`/${item === '首页' ? '' : item.toLowerCase()}`}
                                    className="px-4 py-2 text-sm font-bold uppercase tracking-wide transition-all hover:bg-opacity-10 rounded"
                                    style={{
                                        color: darkMode ? '#e5e7eb' : colors.foreground || '#111827',
                                        fontFamily: themeConfig.typography?.headingFont || 'Montserrat, sans-serif'
                                    }}
                                >
                                    {item}
                                </Link>
                            ))}
                        </div>

                        {/* 移动端菜单按钮 */}
                        <button
                            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
                            className="md:hidden p-2 rounded transition-colors"
                            style={{
                                backgroundColor: darkMode ? '#374151' : '#f3f4f6',
                                color: darkMode ? '#e5e7eb' : colors.foreground || '#111827'
                            }}
                        >
                            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                {mobileMenuOpen ? (
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                                ) : (
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                                )}
                            </svg>
                        </button>
                    </nav>

                    {/* 移动端菜单 */}
                    {mobileMenuOpen && (
                        <div 
                            className="md:hidden mt-4 py-4 border-t"
                            style={{borderColor: darkMode ? '#4b5563' : colors.border || '#e5e7eb'}}
                        >
                            {navItems.map((item) => (
                                <Link
                                    key={item}
                                    href={`/${item === '首页' ? '' : item.toLowerCase()}`}
                                    className="block px-4 py-3 text-sm font-bold uppercase tracking-wide transition-colors"
                                    style={{
                                        color: darkMode ? '#e5e7eb' : colors.foreground || '#111827',
                                        borderBottom: `1px solid ${darkMode ? '#374151' : '#f3f4f6'}`
                                    }}
                                    onClick={() => setMobileMenuOpen(false)}
                                >
                                    {item}
                                </Link>
                            ))}
                        </div>
                    )}
                </div>
            </header>
        </>
    );
};

export default MagazineHeader;
