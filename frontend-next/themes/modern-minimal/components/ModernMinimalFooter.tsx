/**
 * Modern Minimal Theme Footer Component
 * 现代简约主题底部组件 - 简洁优雅的页脚设计
 */
'use client';

import React from 'react';
import Link from 'next/link';
import {useTheme} from '@/hooks/useTheme';

interface ModernMinimalFooterProps {
    darkMode?: boolean;
}

const ModernMinimalFooter: React.FC<ModernMinimalFooterProps> = ({darkMode = false}) => {
    const {config} = useTheme();
    
    // 获取主题配置
    const themeConfig = config?.config || {};
    const colors = (themeConfig as any).colors || {};
    const layout = (themeConfig as any).layout || {};

    const footerStyle = layout.footerStyle || 'simple';
    const currentYear = new Date().getFullYear();

    return (
        <footer
            className="py-8 md:py-12 border-t transition-colors duration-300"
            style={{
                borderColor: darkMode ? colors.border || '#334155' : colors.border || '#e5e7eb',
                backgroundColor: darkMode ? colors.muted || '#1e293b' : colors.muted || '#f3f4f6',
            }}
        >
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                {footerStyle === 'simple' ? (
                    <div className="text-center">
                        <p 
                            className="text-sm"
                            style={{color: darkMode ? colors.secondary || '#94a3b8' : colors.secondary || '#64748b'}}
                        >
                            © {currentYear} {config?.metadata?.name || 'Modern Minimal'}. All rights reserved.
                        </p>
                        <p 
                            className="mt-2 text-xs"
                            style={{color: darkMode ? '#64748b' : '#9ca3af'}}
                        >
                            Powered by FastBlog | Theme: Modern Minimal
                        </p>
                    </div>
                ) : (
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-8 md:gap-12">
                        {/* 关于 */}
                        <div>
                            <h3 
                                className="font-bold mb-3 text-lg"
                                style={{color: colors.primary || '#3b82f6'}}
                            >
                                关于
                            </h3>
                            <p 
                                className="text-sm leading-relaxed"
                                style={{color: darkMode ? colors.foreground || '#e2e8f0' : colors.foreground || '#1f2937'}}
                            >
                                现代简约博客主题，注重内容呈现和阅读体验。
                                干净、优雅、响应式设计。
                            </p>
                        </div>

                        {/* 链接 */}
                        <div>
                            <h3 
                                className="font-bold mb-3 text-lg"
                                style={{color: colors.primary || '#3b82f6'}}
                            >
                                链接
                            </h3>
                            <ul className="space-y-2">
                                {[
                                    {label: '首页', href: '/'},
                                    {label: '文章', href: '/blog'},
                                    {label: '关于', href: '/about'},
                                    {label: '联系', href: '/contact'}
                                ].map((item) => (
                                    <li key={item.label}>
                                        <Link 
                                            href={item.href}
                                            className="text-sm hover:opacity-80 transition-opacity"
                                            style={{color: darkMode ? colors.foreground || '#e2e8f0' : colors.foreground || '#1f2937'}}
                                        >
                                            {item.label}
                                        </Link>
                                    </li>
                                ))}
                            </ul>
                        </div>

                        {/* 社交媒体 */}
                        <div>
                            <h3 
                                className="font-bold mb-3 text-lg"
                                style={{color: colors.primary || '#3b82f6'}}
                            >
                                社交媒体
                            </h3>
                            <div className="flex flex-wrap gap-2">
                                {[
                                    {name: 'GitHub', url: '#'},
                                    {name: 'Twitter', url: '#'},
                                    {name: 'RSS', url: '/rss'}
                                ].map((social) => (
                                    <a
                                        key={social.name}
                                        href={social.url}
                                        className="px-3 py-1.5 text-xs font-medium rounded transition-all hover:opacity-80"
                                        style={{
                                            backgroundColor: darkMode ? '#334155' : '#e5e7eb',
                                            color: darkMode ? '#e2e8f0' : colors.foreground || '#1f2937'
                                        }}
                                    >
                                        {social.name}
                                    </a>
                                ))}
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </footer>
    );
};

export default ModernMinimalFooter;
