/**
 * Magazine主题 - 布局组件
 */
'use client';

import React from 'react';
import {MagazineHeader} from './MagazineHeader';
import {MagazineFooter} from './MagazineFooter';

export const MagazineLayout: React.FC<{ children: React.ReactNode }> = ({children}) => {
    return (
        <div className="min-h-screen flex flex-col bg-white">
            <MagazineHeader/>
            <main className="flex-grow">
                {children}
            </main>
            <MagazineFooter/>
        </div>
    );
};

export default MagazineLayout;
