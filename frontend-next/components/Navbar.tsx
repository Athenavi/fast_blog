'use client';

import React, {useEffect, useState} from 'react';
import Link from 'next/link';
import {usePathname} from 'next/navigation';
import {motion} from 'framer-motion';
import {Bell, Home, Image as ImageIcon, LogOut, Moon, Search, Settings, Sun, User} from 'lucide-react';
import {useDarkMode} from '@/lib/dark-mode-manager';
import {getAccessTokenFromCookie} from '@/lib/auth-utils';

interface NavbarProps {
    title?: string;
    subtitle?: string;
    showBackButton?: boolean;
    rightActions?: React.ReactNode;
}

const Navbar: React.FC<NavbarProps> = ({
                                           title,
                                           subtitle,
                                           showBackButton = false,
                                           rightActions
                                       }) => {
    const pathname = usePathname();
    const {theme, toggleTheme} = useDarkMode(); // 使用新的深色模式管理器
    const [isUserMenuOpen, setIsUserMenuOpen] = useState(false);
    const [isLoggedIn, setIsLoggedIn] = useState(false);

    // 调试：记录主题变化（仅在开发环境）
    useEffect(() => {
        if (process.env.NODE_ENV === 'development') {
            console.log('[Navbar] 当前主题:', theme);
            console.log('[Navbar] HTML 元素的类:', document.documentElement.classList.toString());
        }
    }, [theme]);

    // 检查用户是否登录
    useEffect(() => {
        const checkLoginStatus = () => {
            const token = getAccessTokenFromCookie();
            const isLoggedIn = !!token;
            console.log('[Navbar] 登录状态检查:', {
                hasToken: isLoggedIn,
                cookie: document.cookie.substring(0, 50) + '...',
                pathname,
                windowWidth: typeof window !== 'undefined' ? window.innerWidth : 0
            });
            setIsLoggedIn(isLoggedIn);
        };

        checkLoginStatus();

        // 监听路由变化，重新检查登录状态
        return () => {
            // 清理函数
        };
    }, [pathname]);

    // 点击外部关闭下拉菜单
    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            const target = event.target as unknown as HTMLElement;
            if (!target.closest('.user-menu-container')) {
                setIsUserMenuOpen(false);
            }
        };

        if (isUserMenuOpen) {
            document.addEventListener('mousedown', handleClickOutside);
        }

        return () => {
            document.removeEventListener('mousedown', handleClickOutside);
        };
    }, [isUserMenuOpen]);

    // 导航菜单项
    const navItems = [
        {name: '首页', href: '/', icon: Home},
    ];

    // 用户菜单项（仅登录时显示）
    const userMenuItems = isLoggedIn ? [
        {name: '媒体库', href: '/media', icon: ImageIcon},
        {name: '设置', href: '/settings', icon: Settings},
        {name: '个人资料', href: '/profile', icon: User},
        {name: '退出登录', href: '/auth/logout', icon: LogOut, action: true},
    ] : [
        {name: '登录', href: '/login', icon: User},
    ];

    return (
        <>
            <header
                className="border-b border-gray-200 dark:border-gray-800 shadow-sm fixed top-0 left-0 right-0 z-[9999] w-full bg-white dark:bg-gray-900"
                suppressHydrationWarning // ✅ 抑制 hydration 警告
            >
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="flex items-center justify-between h-16">
                        {/* 左侧：Logo 和标题 */}
                        <div className="flex items-center gap-4">
                            {/* Logo */}
                            <Link href="/" className="flex items-center gap-2 hover:opacity-80 transition-opacity">
                                <div
                                    className="w-8 h-8 bg-gradient-to-br from-blue-600 to-purple-600 rounded-lg flex items-center justify-center">
                                    <ImageIcon className="w-5 h-5 text-white"/>
                                </div>
                                <span className="text-xl font-bold text-gray-900 dark:text-white hidden sm:block">
                                    FastBlog
                                </span>
                            </Link>

                            {/* 页面标题（如果提供） */}
                            {title && (
                                <div className="hidden md:block">
                                    <h1 className="text-lg font-semibold text-gray-900 dark:text-white">
                                        {title}
                                    </h1>
                                    {subtitle && (
                                        <p className="text-xs text-gray-500 dark:text-gray-400">
                                            {subtitle}
                                        </p>
                                    )}
                                </div>
                            )}
                        </div>

                        {/* 中间：导航菜单 */}
                        <nav className="flex items-center gap-1">
                            {navItems.map((item) => {
                                const Icon = item.icon;
                                const isActive = pathname === item.href;

                                return (
                                    <Link
                                        key={item.href}
                                        href={item.href}
                                        className={`relative px-4 py-2 rounded-lg transition-colors flex items-center gap-2 ${
                                            isActive
                                                ? 'text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/20'
                                                : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800'
                                        }`}
                                    >
                                        <Icon className="w-4 h-4"/>
                                        <span className="font-medium">{item.name}</span>
                                        {isActive && (
                                            <motion.div
                                                layoutId="activeNav"
                                                className="absolute bottom-0 left-0 right-0 h-0.5 bg-blue-600 dark:bg-blue-400"
                                            />
                                        )}
                                    </Link>
                                );
                            })}
                        </nav>

                        {/* 右侧：操作按钮 */}
                        <div className="flex items-center gap-2">
                            {/* 搜索、通知、主题切换 */}
                            <div className="flex items-center gap-2">
                                {/* 搜索按钮 */}
                                <button
                                    className="p-2 rounded-lg text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
                                    title="搜索"
                                >
                                    <Search className="w-5 h-5"/>
                                </button>

                                {/* 通知按钮 */}
                                <button
                                    className="p-2 rounded-lg text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors relative"
                                    title="通知"
                                >
                                    <Bell className="w-5 h-5"/>
                                    <span className="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full"></span>
                                </button>

                                {/* 主题切换 */}
                                <button
                                    onClick={toggleTheme}
                                    className="p-2 rounded-lg text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
                                    suppressHydrationWarning // ✅ 抑制 hydration 警告
                                >
                                    <span className="dark:hidden">
                                        <Moon className="w-5 h-5"/>
                                    </span>
                                    <span className="hidden dark:inline">
                                        <Sun className="w-5 h-5"/>
                                    </span>
                                </button>
                            </div>

                            {/* 用户菜单 - 下拉菜单 */}
                            <div className="block relative user-menu-container">
                                <button
                                    onClick={() => setIsUserMenuOpen(!isUserMenuOpen)}
                                    className="p-2 rounded-lg text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
                                    title="用户菜单"
                                >
                                    <User className="w-5 h-5"/>
                                </button>

                                {/* 下拉菜单 */}
                                {isUserMenuOpen && (
                                    <motion.div
                                        initial={{opacity: 0, y: -10}}
                                        animate={{opacity: 1, y: 0}}
                                        exit={{opacity: 0, y: -10}}
                                        className="absolute right-0 mt-2 w-48 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 py-2 z-50 bg-white dark:bg-gray-900"
                                        suppressHydrationWarning // ✅ 抑制 hydration 警告
                                    >
                                        {userMenuItems.map((item) => {
                                            const Icon = item.icon;

                                            if (item.action) {
                                                return (
                                                    <button
                                                        key={item.href}
                                                        onClick={() => {
                                                            document.cookie = 'access_token=; path=/; expires=Thu, 01 Jan 1970 00:00:01 GMT';
                                                            window.location.href = '/';
                                                        }}
                                                        className="w-full px-4 py-2 text-left text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors flex items-center gap-3"
                                                    >
                                                        <Icon className="w-4 h-4"/>
                                                        <span>{item.name}</span>
                                                    </button>
                                                );
                                            }

                                            return (
                                                <Link
                                                    key={item.href}
                                                    href={item.href}
                                                    onClick={() => setIsUserMenuOpen(false)}
                                                    className="block px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors flex items-center gap-3"
                                                >
                                                    <Icon className="w-4 h-4"/>
                                                    <span>{item.name}</span>
                                                </Link>
                                            );
                                        })}
                                    </motion.div>
                                )}
                            </div>

                        </div>
                    </div>
                </div>
            </header>

            {/* 自定义右侧操作区域（如果提供） */}
            {rightActions && (
                <div className="border-b border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900"
                     suppressHydrationWarning // ✅ 抑制 hydration 警告
                >
                    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-2">
                        {rightActions}
                    </div>
                </div>
            )}
        </>
    );
};

export default Navbar;
