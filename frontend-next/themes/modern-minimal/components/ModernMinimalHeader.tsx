/**
 * Modern Minimal Theme Header Component
 * 现代简约主题头部组件
 */
'use client';

import React from 'react';
import Link from 'next/link';
import {useTheme} from '@/hooks/useTheme';
import {useThemeStyles} from '@/hooks/useThemeStyles';

const ModernMinimalHeader: React.FC = () => {
    const {config} = useTheme();
    const themeConfig = config?.config || {};
    const colors = (themeConfig as any).colors || {};
    const layout = (themeConfig as any).layout || {};

    // 根据主题配置调整头部样式
    const headerStyle = layout.headerStyle || 'centered';

    return (
        <header
            className={`
        py-6 border-b transition-colors duration-300
        ${headerStyle === 'centered' ? 'text-center' : ''}
      `}
            style={{
                borderColor: colors.border || '#e5e7eb',
                backgroundColor: colors.background || '#ffffff',
            }}
        >
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                <div className={headerStyle === 'centered' ? 'flex flex-col items-center' : 'flex items-center'}>
                    <Link
                        href="/"
                        className="text-2xl font-bold hover:opacity-80 transition-opacity"
                        style={{color: colors.primary || '#3b82f6'}}
                    >
                        {config?.metadata?.name || 'Modern Minimal'}
                    </Link>

                    {headerStyle !== 'centered' && (
                        <nav className="ml-auto pl-6 hidden md:flex space-x-8">
                            <Link href="/" className="hover:opacity-80 transition-opacity"
                                  style={{color: colors.foreground || '#1f2937'}}>
                                首页
                            </Link>
                            <Link href="/about" className="hover:opacity-80 transition-opacity"
                                  style={{color: colors.foreground || '#1f2937'}}>
                                关于
                            </Link>
                            <Link href="/contact" className="hover:opacity-80 transition-opacity"
                                  style={{color: colors.foreground || '#1f2937'}}>
                                联系
                            </Link>
                        </nav>
                    )}
                </div>

                {headerStyle === 'centered' && (
                    <nav className="mt-4 hidden md:flex justify-center space-x-8">
                        <Link href="/" className="hover:opacity-80 transition-opacity"
                              style={{color: colors.foreground || '#1f2937'}}>
                            首页
                        </Link>
                        <Link href="/about" className="hover:opacity-80 transition-opacity"
                              style={{color: colors.foreground || '#1f2937'}}>
                            关于
                        </Link>
                        <Link href="/contact" className="hover:opacity-80 transition-opacity"
                              style={{color: colors.foreground || '#1f2937'}}>
                            联系
                        </Link>
                    </nav>
                )}
            </div>
        </header>
    );
};

export default ModernMinimalHeader;
