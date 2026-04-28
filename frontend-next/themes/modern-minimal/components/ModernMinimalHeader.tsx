/**
 * Modern Minimal Theme Header Component
 * 现代简约主题头部组件 - 简洁、优雅的导航设计
 */
'use client';

import React, {useState, useEffect} from 'react';
import Link from 'next/link';
import {useTheme} from '@/hooks/useTheme';

interface ModernMinimalHeaderProps {
    darkMode?: boolean;
}

const ModernMinimalHeader: React.FC<ModernMinimalHeaderProps> = ({darkMode = false}) => {
    const {config} = useTheme();
    const [isScrolled, setIsScrolled] = useState(false);
    const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

    // 获取主题配置
    const themeConfig = config?.config || {};
    const colors = (themeConfig as any).colors || {};
    const layout = (themeConfig as any).layout || {};
    const features = (themeConfig as any).features || {};

    // 监听滚动，实现粘性头部效果
    useEffect(() => {
        const handleScroll = () => {
            setIsScrolled(window.scrollY > 20);
        };

        window.addEventListener('scroll', handleScroll);
        return () => window.removeEventListener('scroll', handleScroll);
    }, []);

    // 根据主题配置调整头部样式
    const headerStyle = layout.headerStyle || 'centered';

    const navItems = [
        {label: '首页', href: '/'},
        {label: '文章', href: '/blog'},
        {label: '分类', href: '/categories'},
        {label: '关于', href: '/about'},
        {label: '联系', href: '/contact'}
    ];

    return (
        <header
            className={`transition-all duration-300 border-b ${
                isScrolled ? 'sticky top-0 z-50 backdrop-blur-md shadow-sm' : ''
            }`}
            style={{
                borderColor: darkMode ? colors.border || '#334155' : colors.border || '#e5e7eb',
                backgroundColor: isScrolled 
                    ? (darkMode ? 'rgba(15, 23, 42, 0.9)' : 'rgba(255, 255, 255, 0.9)')
                    : (darkMode ? colors.background || '#0f172a' : colors.background || '#ffffff'),
            }}
        >
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                <div className="flex items-center justify-between h-16 md:h-20">
                    {/* Logo/标题 */}
                    <Link
                        href="/"
                        className="text-xl md:text-2xl font-bold hover:opacity-80 transition-opacity tracking-tight"
                        style={{color: colors.primary || '#3b82f6'}}
                    >
                        {config?.metadata?.name || 'Modern Minimal'}
                    </Link>

                    {/* 桌面端导航 */}
                    <nav className="hidden md:flex items-center space-x-1">
                        {navItems.map((item) => (
                            <Link
                                key={item.label}
                                href={item.href}
                                className="px-4 py-2 text-sm font-medium rounded-lg transition-all hover:bg-opacity-10"
                                style={{
                                    color: darkMode ? colors.foreground || '#e2e8f0' : colors.foreground || '#1f2937',
                                }}
                            >
                                {item.label}
                            </Link>
                        ))}
                    </nav>

                    {/* 移动端菜单按钮 */}
                    <button
                        onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
                        className="md:hidden p-2 rounded-lg transition-colors"
                        style={{
                            backgroundColor: darkMode ? '#1e293b' : '#f3f4f6',
                            color: darkMode ? '#e2e8f0' : colors.foreground || '#1f2937'
                        }}
                        aria-label="Toggle menu"
                    >
                        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            {mobileMenuOpen ? (
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                            ) : (
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                            )}
                        </svg>
                    </button>
                </div>

                {/* 移动端菜单 */}
                {mobileMenuOpen && (
                    <nav className="md:hidden py-4 border-t" 
                         style={{borderColor: darkMode ? colors.border || '#334155' : colors.border || '#e5e7eb'}}>
                        {navItems.map((item) => (
                            <Link
                                key={item.label}
                                href={item.href}
                                className="block px-4 py-3 text-sm font-medium rounded-lg transition-colors mb-1"
                                style={{
                                    color: darkMode ? colors.foreground || '#e2e8f0' : colors.foreground || '#1f2937',
                                    backgroundColor: darkMode ? 'transparent' : 'transparent'
                                }}
                                onClick={() => setMobileMenuOpen(false)}
                            >
                                {item.label}
                            </Link>
                        ))}
                    </nav>
                )}
            </div>
        </header>
    );
};

export default ModernMinimalHeader;
