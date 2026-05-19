/**
 * 导航栏组件 - React 岛屿
 * 适配 Astro：使用 window.location 替代 next/navigation
 */

'use client';

import React, {useEffect, useState} from 'react';
import {motion} from 'framer-motion';
import {Bell, Home, Image as ImageIcon, LogOut, Moon, Search, Settings, Sun, User} from 'lucide-react';
import {useDarkMode} from '@/lib/dark-mode-manager';

interface NavbarProps {
    title?: string;
    subtitle?: string;
    showBackButton?: boolean;
    rightActions?: React.ReactNode;
}

const Navbar: React.FC<NavbarProps> = ({title, subtitle, showBackButton = false, rightActions}) => {
    const {theme, toggleTheme} = useDarkMode();
    const [isUserMenuOpen, setIsUserMenuOpen] = useState(false);
    const [isLoggedIn, setIsLoggedIn] = useState(false);
    const [pathname, setPathname] = useState('/');

    useEffect(() => {
        setPathname(window.location.pathname);

        const token = getAccessTokenFromCookie();
        setIsLoggedIn(!!token);
    }, []);

    // 点击外部关闭下拉菜单
    useEffect(() => {
        const handleClickOutside = (e: MouseEvent) => {
            const target = e.target as HTMLElement;
            if (!target.closest('.user-menu-container')) {
                setIsUserMenuOpen(false);
            }
        };

        if (isUserMenuOpen) {
            document.addEventListener('mousedown', handleClickOutside);
        }
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, [isUserMenuOpen]);

    const navItems = [
        {name: '首页', href: '/', icon: Home},
    ];

    const userMenuItems = isLoggedIn ? [
        {name: '媒体库', href: '/media', icon: ImageIcon},
        {name: '设置', href: '/settings', icon: Settings},
        {name: '个人资料', href: '/profile', icon: User},
        {name: '退出登录', href: '#', icon: LogOut, action: true},
    ] : [
        {name: '登录', href: '/login', icon: User},
    ];

    return (
        <>
            <header className="border-b border-gray-200 dark:border-gray-800 shadow-sm fixed top-0 left-0 right-0 z-[9999] w-full bg-white dark:bg-gray-900"
                    suppressHydrationWarning>
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="flex items-center justify-between h-16">
                        {/* Logo */}
                        <div className="flex items-center gap-4">
                            <a href="/" className="flex items-center gap-2 hover:opacity-80 transition-opacity">
                                <div className="w-8 h-8 bg-gradient-to-br from-blue-600 to-purple-600 rounded-lg flex items-center justify-center">
                                    <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"/></svg>
                                </div>
                                <span className="text-xl font-bold text-gray-900 dark:text-white hidden sm:block">FastBlog</span>
                            </a>

                            {title && (
                                <div className="hidden md:block">
                                    <h1 className="text-lg font-semibold text-gray-900 dark:text-white">{title}</h1>
                                    {subtitle && <p className="text-xs text-gray-500 dark:text-gray-400">{subtitle}</p>}
                                </div>
                            )}
                        </div>

                        {/* 导航菜单 */}
                        <nav className="flex items-center gap-1">
                            {navItems.map((item) => {
                                const Icon = item.icon;
                                const isActive = pathname === item.href;
                                return (
                                    <a key={item.href} href={item.href}
                                        className={`relative px-4 py-2 rounded-lg transition-colors flex items-center gap-2 ${isActive ? 'text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/20' : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800'}`}>
                                        <Icon className="w-4 h-4"/>
                                        <span className="font-medium">{item.name}</span>
                                        {isActive && <motion.div layoutId="activeNav" className="absolute bottom-0 left-0 right-0 h-0.5 bg-blue-600 dark:bg-blue-400"/>}
                                    </a>
                                );
                            })}
                        </nav>

                        {/* 右侧按钮 */}
                        <div className="flex items-center gap-2">
                            <div className="flex items-center gap-2">
                                <button className="p-2 rounded-lg text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors" title="搜索">
                                    <Search className="w-5 h-5"/>
                                </button>
                                <button className="p-2 rounded-lg text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors relative" title="通知">
                                    <Bell className="w-5 h-5"/>
                                    <span className="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full"></span>
                                </button>
                                <button onClick={toggleTheme} className="p-2 rounded-lg text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors" suppressHydrationWarning>
                                    <span className="dark:hidden"><Moon className="w-5 h-5"/></span>
                                    <span className="hidden dark:inline"><Sun className="w-5 h-5"/></span>
                                </button>
                            </div>

                            {/* 用户菜单 */}
                            <div className="block relative user-menu-container">
                                <button onClick={() => setIsUserMenuOpen(!isUserMenuOpen)}
                                    className="p-2 rounded-lg text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors" title="用户菜单">
                                    <User className="w-5 h-5"/>
                                </button>

                                {isUserMenuOpen && (
                                    <motion.div initial={{opacity: 0, y: -10}} animate={{opacity: 1, y: 0}}
                                        className="absolute right-0 mt-2 w-48 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 py-2 z-50 bg-white dark:bg-gray-900">
                                        {userMenuItems.map((item) => {
                                            const Icon = item.icon;
                                            if (item.action) {
                                                return (
                                                    <button key={item.href} onClick={() => {
                                                        document.cookie = 'access_token=; path=/; expires=Thu, 01 Jan 1970 00:00:01 GMT';
                                                        window.location.href = '/';
                                                    }} className="w-full px-4 py-2 text-left text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors flex items-center gap-3">
                                                        <Icon className="w-4 h-4"/><span>{item.name}</span>
                                                    </button>
                                                );
                                            }
                                            return (
                                                <a key={item.href} href={item.href} onClick={() => setIsUserMenuOpen(false)}
                                                    className="block px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors flex items-center gap-3">
                                                    <Icon className="w-4 h-4"/><span>{item.name}</span>
                                                </a>
                                            );
                                        })}
                                    </motion.div>
                                )}
                            </div>
                        </div>
                    </div>
                </div>
            </header>

            {rightActions && (
                <div className="border-b border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900" suppressHydrationWarning>
                    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-2">{rightActions}</div>
                </div>
            )}
        </>
    );
};

function getAccessTokenFromCookie(): string | null {
    if (typeof document === 'undefined') return null;
    const cookies = document.cookie.split(';');
    for (const cookie of cookies) {
        const [name, value] = cookie.trim().split('=');
        if (name === 'access_token' && value) return decodeURIComponent(value);
    }
    return null;
}

export default Navbar;
