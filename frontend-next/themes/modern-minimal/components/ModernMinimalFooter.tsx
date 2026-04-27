/**
 * Modern Minimal Theme Footer Component
 * 现代简约主题底部组件
 */
'use client';

import React from 'react';
import Link from 'next/link';
import {useTheme} from '@/hooks/useTheme';

const ModernMinimalFooter: React.FC = () => {
    const {config} = useTheme();
    const themeConfig = config?.config || {};
    const colors = (themeConfig as any).colors || {};
    const layout = (themeConfig as any).layout || {};

    const footerStyle = layout.footerStyle || 'simple';

    return (
        <footer
            className="py-8 border-t transition-colors duration-300"
            style={{
                borderColor: colors.border || '#e5e7eb',
                backgroundColor: colors.muted || '#f3f4f6',
            }}
        >
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                {footerStyle === 'simple' ? (
                    <div className="text-center">
                        <p style={{color: colors.secondary || '#64748b'}}>
                            © {new Date().getFullYear()} {config?.metadata?.name || 'Modern Minimal'}. All rights
                            reserved.
                        </p>
                    </div>
                ) : (
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                        <div>
                            <h3 className="font-bold mb-2" style={{color: colors.primary || '#3b82f6'}}>
                                关于
                            </h3>
                            <p style={{color: colors.foreground || '#1f2937'}}>
                                现代简约博客主题
                            </p>
                        </div>
                        <div>
                            <h3 className="font-bold mb-2" style={{color: colors.primary || '#3b82f6'}}>
                                链接
                            </h3>
                            <ul className="space-y-1">
                                <li><Link href="/" className="hover:opacity-80"
                                          style={{color: colors.foreground || '#1f2937'}}>首页</Link></li>
                                <li><Link href="/about" className="hover:opacity-80"
                                          style={{color: colors.foreground || '#1f2937'}}>关于</Link></li>
                                <li><Link href="/contact" className="hover:opacity-80"
                                          style={{color: colors.foreground || '#1f2937'}}>联系</Link></li>
                            </ul>
                        </div>
                        <div>
                            <h3 className="font-bold mb-2" style={{color: colors.primary || '#3b82f6'}}>
                                社交媒体
                            </h3>
                            <ul className="space-y-1">
                                <li><a href="#" className="hover:opacity-80"
                                       style={{color: colors.foreground || '#1f2937'}}>GitHub</a></li>
                                <li><a href="#" className="hover:opacity-80"
                                       style={{color: colors.foreground || '#1f2937'}}>Twitter</a></li>
                            </ul>
                        </div>
                    </div>
                )}
            </div>
        </footer>
    );
};

export default ModernMinimalFooter;
