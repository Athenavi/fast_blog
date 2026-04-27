'use client';

import React from 'react';
import Header from '@/components/Header';
import Footer from '@/components/Footer';

interface FrontendLayoutProps {
    children: React.ReactNode;
}

/**
 * 前端布局组件 - 仅负责 Header 和 Footer
 * 主题加载已由 ThemeProvider 在根 layout 中统一处理
 */
export const FrontendLayout: React.FC<FrontendLayoutProps> = ({children}) => {
    return (
        <div className="min-h-screen flex flex-col bg-gray-50 dark:bg-gray-900">
            <Header/>
            <main className="flex-grow">
                {children}
            </main>
            <Footer/>
        </div>
    );
};

export default FrontendLayout;
