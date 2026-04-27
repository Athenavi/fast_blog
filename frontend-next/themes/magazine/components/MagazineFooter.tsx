/**
 * Magazine主题 - Footer组件
 */
'use client';

import React from 'react';
import {useThemeStyles} from '@/hooks/useThemeStyles';

export const MagazineFooter: React.FC = () => {
    const themeStyles = useThemeStyles();

    return (
        <footer className="py-12" style={{backgroundColor: themeStyles.foreground}}>
            <div className="container mx-auto max-w-7xl px-4">
                <div className="grid grid-cols-1 md:grid-cols-4 gap-8 text-white">
                    <div>
                        <h3 className="font-bold mb-4">关于我们</h3>
                        <p className="text-sm text-white/70">
                            FastBlog Magazine - 深度报道与专业分析
                        </p>
                    </div>
                    <div>
                        <h3 className="font-bold mb-4">快速链接</h3>
                        <ul className="space-y-2 text-sm text-white/70">
                            <li><a href="#" className="hover:text-white">首页</a></li>
                            <li><a href="#" className="hover:text-white">分类</a></li>
                            <li><a href="#" className="hover:text-white">关于</a></li>
                        </ul>
                    </div>
                    <div>
                        <h3 className="font-bold mb-4">联系我们</h3>
                        <ul className="space-y-2 text-sm text-white/70">
                            <li>Email: contact@fastblog.com</li>
                            <li>Tel: +86 123 4567 8900</li>
                        </ul>
                    </div>
                    <div>
                        <h3 className="font-bold mb-4">关注我们</h3>
                        <div className="flex gap-4">
                            <a href="#" className="text-white/70 hover:text-white">Twitter</a>
                            <a href="#" className="text-white/70 hover:text-white">Weibo</a>
                        </div>
                    </div>
                </div>
                <div className="mt-8 pt-8 border-t border-white/20 text-center text-sm text-white/50">
                    © 2026 FastBlog Magazine. All rights reserved.
                </div>
            </div>
        </footer>
    );
};

export default MagazineFooter;
