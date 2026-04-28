/**
 * Magazine主题 - Footer组件
 * 杂志风格底部，多栏目布局
 */
'use client';

import React from 'react';
import Link from 'next/link';
import {useTheme} from '@/hooks/useTheme';

interface MagazineFooterProps {
    darkMode?: boolean;
}

export const MagazineFooter: React.FC<MagazineFooterProps> = ({darkMode = false}) => {
    const {config} = useTheme();

    // 获取主题配置
    const themeConfig = config?.config || {};
    const colors = (themeConfig as any).colors || {};

    const currentYear = new Date().getFullYear();

    return (
        <footer 
            className="py-12 transition-colors"
            style={{
                backgroundColor: darkMode ? '#0f172a' : colors.foreground || '#111827',
                color: '#ffffff'
            }}
        >
            <div className="container mx-auto max-w-7xl px-4">
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
                    {/* 关于我们 */}
                    <div>
                        <h3 
                            className="font-bold text-lg mb-4 uppercase tracking-wide"
                            style={{
                                fontFamily: themeConfig.typography?.headingFont || 'Montserrat, sans-serif',
                                color: colors.primary || '#dc2626'
                            }}
                        >
                            关于我们
                        </h3>
                        <p className="text-sm leading-relaxed" style={{color: 'rgba(255, 255, 255, 0.7)'}}>
                            FastBlog Magazine 致力于提供深度报道与专业分析，
                            为您带来最前沿的科技、商业和文化资讯。
                        </p>
                    </div>

                    {/* 快速链接 */}
                    <div>
                        <h3 
                            className="font-bold text-lg mb-4 uppercase tracking-wide"
                            style={{
                                fontFamily: themeConfig.typography?.headingFont || 'Montserrat, sans-serif',
                                color: colors.primary || '#dc2626'
                            }}
                        >
                            快速链接
                        </h3>
                        <ul className="space-y-2 text-sm">
                            {['首页', '分类', '标签', '归档', '关于'].map((item) => (
                                <li key={item}>
                                    <Link 
                                        href={`/${item === '首页' ? '' : item.toLowerCase()}`}
                                        className="hover:text-white transition-colors"
                                        style={{color: 'rgba(255, 255, 255, 0.7)'}}
                                    >
                                        {item}
                                    </Link>
                                </li>
                            ))}
                        </ul>
                    </div>

                    {/* 联系我们 */}
                    <div>
                        <h3 
                            className="font-bold text-lg mb-4 uppercase tracking-wide"
                            style={{
                                fontFamily: themeConfig.typography?.headingFont || 'Montserrat, sans-serif',
                                color: colors.primary || '#dc2626'
                            }}
                        >
                            联系我们
                        </h3>
                        <ul className="space-y-2 text-sm" style={{color: 'rgba(255, 255, 255, 0.7)'}}>
                            <li>Email: contact@fastblog.com</li>
                            <li>Tel: +86 123 4567 8900</li>
                            <li>Address: 北京市朝阳区xxx路xxx号</li>
                        </ul>
                    </div>

                    {/* 关注我们 */}
                    <div>
                        <h3 
                            className="font-bold text-lg mb-4 uppercase tracking-wide"
                            style={{
                                fontFamily: themeConfig.typography?.headingFont || 'Montserrat, sans-serif',
                                color: colors.primary || '#dc2626'
                            }}
                        >
                            关注我们
                        </h3>
                        <div className="flex flex-wrap gap-3">
                            {[
                                {name: 'Twitter', url: '#'},
                                {name: 'Weibo', url: '#'},
                                {name: 'GitHub', url: '#'},
                                {name: 'RSS', url: '/rss'}
                            ].map((social) => (
                                <a
                                    key={social.name}
                                    href={social.url}
                                    className="px-3 py-1 text-sm rounded transition-colors hover:bg-white hover:text-gray-900"
                                    style={{
                                        backgroundColor: 'rgba(255, 255, 255, 0.1)',
                                        color: 'rgba(255, 255, 255, 0.9)'
                                    }}
                                >
                                    {social.name}
                                </a>
                            ))}
                        </div>
                    </div>
                </div>

                {/* 版权信息 */}
                <div 
                    className="mt-12 pt-8 border-t text-center text-sm"
                    style={{borderColor: 'rgba(255, 255, 255, 0.2)'}}
                >
                    <p style={{color: 'rgba(255, 255, 255, 0.5)'}}>
                        © {currentYear} {config?.metadata?.name || 'FastBlog Magazine'}. All rights reserved.
                    </p>
                    <p className="mt-2" style={{color: 'rgba(255, 255, 255, 0.4)'}}>
                        Powered by FastBlog | Theme: Magazine
                    </p>
                </div>
            </div>
        </footer>
    );
};

export default MagazineFooter;
