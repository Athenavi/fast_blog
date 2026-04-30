'use client';

import React from 'react';
import Footer from '@/components/Footer';

interface FrontendLayoutProps {
    children: React.ReactNode;
}

/**
 * 前端布局组件 - 仅负责 Footer
 * 导航栏已由根 layout 中的 Navbar 统一提供
 */
export const FrontendLayout: React.FC<FrontendLayoutProps> = ({children}) => {
    return (
        <div className="min-h-screen flex flex-col bg-gray-50 dark:bg-gray-900">
            <main className="flex-grow">
                {children}
            </main>
            <Footer/>
        </div>
    );
};

export default FrontendLayout;
