/**
 * Magazine主题 - Header组件
 */
'use client';

import React from 'react';
import {useThemeStyles} from '@/hooks/useThemeStyles';

export const MagazineHeader: React.FC = () => {
    const themeStyles = useThemeStyles();

    return (
        <header
            className="border-b-4 py-6"
            style={{borderColor: themeStyles.primary}}
        >
            <div className="container mx-auto max-w-7xl px-4">
                <h1
                    className="text-5xl font-black uppercase tracking-tighter text-center"
                    style={{
                        fontFamily: themeStyles.fontFamily,
                        color: themeStyles.foreground
                    }}
                >
                    FastBlog Magazine
                </h1>
                <nav className="mt-6 flex justify-center gap-8">
                    {['首页', '科技', '商业', '文化', '关于'].map(item => (
                        <a
                            key={item}
                            href="#"
                            className="text-sm font-bold uppercase tracking-wide hover:underline"
                            style={{color: themeStyles.foreground}}
                        >
                            {item}
                        </a>
                    ))}
                </nav>
            </div>
        </header>
    );
};

export default MagazineHeader;
