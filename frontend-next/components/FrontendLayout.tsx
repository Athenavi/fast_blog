'use client';

import React from 'react';
import Footer from '@/components/Footer';
import {useDarkMode} from '@/lib/dark-mode-manager';

interface FrontendLayoutProps {
    children: React.ReactNode;
}

/**
 * 前端布局组件 - 仅负责 Footer
 * 导航栏已由根 layout 中的 Navbar 统一提供
 */
export const FrontendLayout: React.FC<FrontendLayoutProps> = ({children}) => {
    const {theme} = useDarkMode();
    
    return (
        <div className="min-h-screen flex flex-col"
             style={{
                 backgroundColor: theme === 'dark' ? '#111827' : '#f9fafb'
             }}>
            <main className="flex-grow">
                {children}
            </main>
            <Footer/>
        </div>
    );
};

export default FrontendLayout;
