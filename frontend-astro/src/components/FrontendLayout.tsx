/**
 * 前端布局组件 - React 岛屿
 * 适配 Astro：移除了 Next.js 依赖，使用 props 接收 data
 */

'use client';

import React from 'react';

interface FrontendLayoutProps {
    children: React.ReactNode;
}

export const FrontendLayout: React.FC<FrontendLayoutProps> = ({children}) => {
    return (
      <div className="min-h-screen flex flex-col theme-bg">
            <main className="flex-grow">
                {children}
            </main>
        </div>
    );
};

export default FrontendLayout;
