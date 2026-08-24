'use client';

/**
 * 极简页脚（footer 槽位的 "minimal" 变体）
 * 主题契约 componentSlots.footer = "minimal" 时启用。
 * 仅保留品牌 + 版权 + 少量链接，无多列/订阅/社交区块。
 */
import React, {useState} from 'react';
import {Rss} from 'lucide-react';
import {FEED} from '@/lib/api/api-paths';

const LINKS = [
  {label: '首页', href: '/'},
  {label: '文章', href: '/articles'},
  {label: '搜索', href: '/search'},
];

export default function MinimalFooter() {
  const [year] = useState(() => new Date().getFullYear());

  return (
    <footer className="border-t theme-border py-8">
      <div className="max-w-7xl mx-auto px-6 sm:px-8 flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 gradient-primary rounded flex items-center justify-center">
            <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z"/>
            </svg>
          </div>
          <span className="text-sm font-medium text-gray-700 dark:text-gray-200">FastBlog</span>
          <span className="text-sm text-gray-400">© {year}</span>
        </div>

        <nav className="flex items-center gap-6">
          {LINKS.map((l) => (
            <a key={l.href} href={l.href}
               className="text-sm text-gray-500 dark:text-gray-400 hover:text-blue-600 dark:hover:text-blue-400 transition-colors">
              {l.label}
            </a>
          ))}
          <a href={FEED} aria-label="RSS 订阅" className="text-gray-400 hover:text-orange-500 transition-colors">
            <Rss className="w-4 h-4"/>
          </a>
        </nav>
      </div>
    </footer>
  );
}
