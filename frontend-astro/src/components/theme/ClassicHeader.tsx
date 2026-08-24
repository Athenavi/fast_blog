'use client';

/**
 * 经典顶栏头部（header 槽位的 "classic" 变体）
 * 主题契约 componentSlots.header = "classic" 时启用。
 * 区别于默认的 floating 浮动胶囊导航，提供传统的顶部固定导航条。
 */
import React, {useEffect, useState} from 'react';
import {Menu, Moon, Sun, User} from 'lucide-react';
import {getLocalAuthState} from '@/lib/auth-utils';

const NAV_LINKS = [
  {label: '首页', href: '/'},
  {label: '文章', href: '/articles'},
  {label: '搜索', href: '/search'},
  {label: '关于', href: '/about'},
];

export default function ClassicHeader() {
  const [loggedIn, setLoggedIn] = useState(false);
  const [dark, setDark] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    setLoggedIn(getLocalAuthState());
    setDark(typeof document !== 'undefined' && document.documentElement.classList.contains('dark'));
    const onChange = () => setLoggedIn(getLocalAuthState());
    window.addEventListener('auth:changed', onChange);
    return () => window.removeEventListener('auth:changed', onChange);
  }, []);

  const toggleDark = () => {
    const root = document.documentElement;
    const next = !root.classList.contains('dark');
    root.classList.toggle('dark', next);
    try {
      if (next) localStorage.setItem('fastblog-theme', 'dark');
      else localStorage.removeItem('fastblog-theme');
    } catch (e) { /* ignore */ }
    setDark(next);
  };

  return (
    <header className="fixed top-0 inset-x-0 z-[9998] bg-white/80 dark:bg-gray-950/80 backdrop-blur-xl border-b theme-border">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* 品牌 */}
        <a href="/" className="flex items-center gap-2.5">
          <div className="w-8 h-8 gradient-primary rounded-lg flex items-center justify-center">
            <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z"/>
            </svg>
          </div>
          <span className="font-semibold text-gray-900 dark:text-white tracking-tight">FastBlog</span>
        </a>

        {/* 导航（桌面） */}
        <nav className="hidden md:flex items-center gap-7">
          {NAV_LINKS.map((l) => (
            <a key={l.href} href={l.href}
               className="text-sm text-gray-600 dark:text-gray-300 hover:text-blue-600 dark:hover:text-blue-400 transition-colors">
              {l.label}
            </a>
          ))}
        </nav>

        {/* 右侧操作 */}
        <div className="flex items-center gap-3">
          <button onClick={toggleDark} aria-label="切换明暗"
                  className="w-9 h-9 flex items-center justify-center rounded-lg theme-border hover:bg-gray-100 dark:hover:bg-gray-800 transition">
            {dark ? <Sun className="w-4 h-4"/> : <Moon className="w-4 h-4"/>}
          </button>
          <a href={loggedIn ? '/settings' : '/login'}
             className="hidden sm:flex items-center gap-2 px-4 py-2 rounded-lg bg-blue-600 text-white text-sm hover:bg-blue-700 transition">
            <User className="w-4 h-4"/>
            {loggedIn ? '个人中心' : '登录'}
          </a>
          <button onClick={() => setMobileOpen(!mobileOpen)} aria-label="菜单"
                  className="md:hidden w-9 h-9 flex items-center justify-center rounded-lg theme-border hover:bg-gray-100 dark:hover:bg-gray-800 transition">
            <Menu className="w-4 h-4"/>
          </button>
        </div>
      </div>

      {/* 移动端菜单 */}
      {mobileOpen && (
        <nav className="md:hidden border-t theme-border bg-white dark:bg-gray-950 px-4 py-3 space-y-1">
          {NAV_LINKS.map((l) => (
            <a key={l.href} href={l.href} onClick={() => setMobileOpen(false)}
               className="block px-3 py-2 rounded-lg text-sm text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800">
              {l.label}
            </a>
          ))}
          <a href={loggedIn ? '/settings' : '/login'} onClick={() => setMobileOpen(false)}
             className="block px-3 py-2 rounded-lg text-sm text-blue-600 dark:text-blue-400">
            {loggedIn ? '个人中心' : '登录'}
          </a>
        </nav>
      )}
    </header>
  );
}
