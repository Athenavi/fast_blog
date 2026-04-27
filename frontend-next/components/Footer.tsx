import React from 'react';
import Link from 'next/link';
import {Rss} from 'lucide-react';
import LanguageSwitcher from './LanguageSwitcher';

const Footer = () => {
  return (
    <footer className="bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700 py-8">
      <div className="container mx-auto px-4">
        <div className="text-center text-gray-600 dark:text-gray-400">
          {/* RSS/Atom Feed 订阅链接 */}
          <div className="mt-4 flex justify-center items-center gap-4">
            <Link 
              href="/api/v1/feed/rss" 
              className="flex items-center gap-2 text-orange-600 hover:text-orange-700 dark:text-orange-500 dark:hover:text-orange-400 transition-colors"
              target="_blank"
              rel="noopener noreferrer"
            >
              <Rss className="w-4 h-4" />
              <span className="text-sm">RSS 订阅</span>
            </Link>
            <span className="text-gray-400">|</span>
            <Link 
              href="/api/v1/feed/atom" 
              className="flex items-center gap-2 text-blue-600 hover:text-blue-700 dark:text-blue-500 dark:hover:text-blue-400 transition-colors"
              target="_blank"
              rel="noopener noreferrer"
            >
              <Rss className="w-4 h-4" />
              <span className="text-sm">Atom 订阅</span>
            </Link>
          </div>

          {/* 语言切换器 */}
          <div className="mt-6 flex justify-center">
            <LanguageSwitcher />
          </div>
        </div>
      </div>
    </footer>
  );
};

export default Footer;