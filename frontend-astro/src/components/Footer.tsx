/**
 * 页脚组件 - React 岛屿
 * 适配 Astro：使用 <a> 替代 next/link
 */

'use client';

import React from 'react';
import {Rss} from 'lucide-react';
import LanguageSwitcher from './LanguageSwitcher';

const Footer = () => {
    return (
        <footer className="border-t border-gray-200 dark:border-gray-700 py-8 bg-white dark:bg-gray-900">
            <div className="container mx-auto px-4">
                <div className="text-center text-gray-600 dark:text-gray-400">
                    <div className="mt-4 flex justify-center items-center gap-4">
                        <a href="/api/v2/feed/rss"
                            className="flex items-center gap-2 text-orange-600 hover:text-orange-700 dark:text-orange-500 dark:hover:text-orange-400 transition-colors"
                            target="_blank" rel="noopener noreferrer">
                            <Rss className="w-4 h-4"/>
                            <span className="text-sm">RSS 订阅</span>
                        </a>
                        <span className="text-gray-400">|</span>
                        <a href="/api/v2/feed/atom"
                            className="flex items-center gap-2 text-blue-600 hover:text-blue-700 dark:text-blue-500 dark:hover:text-blue-400 transition-colors"
                            target="_blank" rel="noopener noreferrer">
                            <Rss className="w-4 h-4"/>
                            <span className="text-sm">Atom 订阅</span>
                        </a>
                    </div>

                    <div className="mt-6 flex justify-center">
                        <LanguageSwitcher />
                    </div>
                </div>
            </div>
        </footer>
    );
};

export default Footer;
