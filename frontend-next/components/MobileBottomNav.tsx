'use client';

import {useEffect, useState} from 'react';
import Link from 'next/link';
import {usePathname} from 'next/navigation';
import {Compass, Home, MessageSquare, PlusSquare, User} from 'lucide-react';

/**
 * 移动端底部导航栏
 * 提供快速导航和常用操作入口
 */
const MobileBottomNav = () => {
    const pathname = usePathname();
    const [showQuickActions, setShowQuickActions] = useState(false);

    // 检测是否为移动设备
    const [isMobile, setIsMobile] = useState(false);

    useEffect(() => {
        const checkMobile = () => {
            setIsMobile(window.innerWidth < 768);
        };

        checkMobile();
        window.addEventListener('resize', checkMobile);

        return () => window.removeEventListener('resize', checkMobile);
    }, []);

    // 如果不是移动设备，不显示
    if (!isMobile) {
        return null;
    }

    const navItems = [
        {
            id: 'home',
            label: '首页',
            icon: Home,
            href: '/',
            active: pathname === '/' || (pathname && pathname.startsWith('/articles')),
        },
        {
            id: 'discover',
            label: '发现',
            icon: Compass,
            href: '/explore',
            active: (pathname && pathname.startsWith('/explore')) || (pathname && pathname.startsWith('/fans/discover')),
        },
        {
            id: 'create',
            label: '发布',
            icon: PlusSquare,
            href: '/contribute',
            active: (pathname && pathname.startsWith('/contribute')) || (pathname && pathname.startsWith('/admin/blog')),
            isAction: true, // 特殊动作按钮
        },
        {
            id: 'messages',
            label: '消息',
            icon: MessageSquare,
            href: '/messages',
            active: pathname && pathname.startsWith('/messages'),
            badge: 0, // 未读消息数
        },
        {
            id: 'profile',
            label: '我的',
            icon: User,
            href: '/profile',
            active: (pathname && pathname.startsWith('/profile')) || (pathname && pathname.startsWith('/settings')),
        },
    ];

    return (
        <>
            {/* 底部导航栏 */}
            <nav
                className="fixed bottom-0 left-0 right-0 z-50 bg-white dark:bg-gray-900 border-t border-gray-200 dark:border-gray-800 md:hidden safe-area-bottom">
                <div className="flex items-center justify-around h-16">
                    {navItems.map((item) => {
                        const Icon = item.icon;

                        // 特殊的发布按钮
                        if (item.isAction) {
                            return (
                                <button
                                    key={item.id}
                                    onClick={() => setShowQuickActions(!showQuickActions)}
                                    className="relative -top-5 flex flex-col items-center justify-center"
                                >
                                    <div
                                        className="w-14 h-14 rounded-full bg-gradient-to-r from-blue-500 to-purple-600 flex items-center justify-center shadow-lg hover:shadow-xl transition-shadow">
                                        <Icon className="w-7 h-7 text-white"/>
                                    </div>
                                    <span className="text-xs mt-1 text-gray-600 dark:text-gray-400">
                    {item.label}
                  </span>
                                </button>
                            );
                        }

                        // 普通导航项
                        return (
                            <Link
                                key={item.id}
                                href={item.href}
                                className={`flex flex-col items-center justify-center flex-1 h-full relative ${
                                    item.active
                                        ? 'text-blue-600 dark:text-blue-400'
                                        : 'text-gray-600 dark:text-gray-400'
                                }`}
                            >
                                <div className="relative">
                                    <Icon className="w-6 h-6"/>
                                    {item.badge && item.badge > 0 && (
                                        <span
                                            className="absolute -top-1 -right-1 w-4 h-4 bg-red-500 text-white text-xs rounded-full flex items-center justify-center">
                      {item.badge > 9 ? '9+' : item.badge}
                    </span>
                                    )}
                                </div>
                                <span className="text-xs mt-1">{item.label}</span>

                                {/* 激活指示器 */}
                                {item.active && (
                                    <div
                                        className="absolute top-0 left-1/2 transform -translate-x-1/2 w-12 h-0.5 bg-blue-600 dark:bg-blue-400 rounded-full"/>
                                )}
                            </Link>
                        );
                    })}
                </div>
            </nav>

            {/* 快捷操作菜单 */}
            {showQuickActions && (
                <>
                    {/* 遮罩层 */}
                    <div
                        className="fixed inset-0 bg-black bg-opacity-50 z-40 md:hidden"
                        onClick={() => setShowQuickActions(false)}
                    />

                    {/* 快捷操作面板 */}
                    <div className="fixed bottom-20 left-4 right-4 z-50 md:hidden">
                        <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-2xl p-4 animate-slide-up">
                            <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3 px-2">
                                快捷操作
                            </h3>
                            <div className="grid grid-cols-3 gap-3">
                                <Link
                                    href="/contribute"
                                    onClick={() => setShowQuickActions(false)}
                                    className="flex flex-col items-center p-3 rounded-xl hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
                                >
                                    <div
                                        className="w-12 h-12 rounded-full bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center mb-2">
                                        <PlusSquare className="w-6 h-6 text-blue-600 dark:text-blue-400"/>
                                    </div>
                                    <span className="text-xs text-gray-700 dark:text-gray-300">写文章</span>
                                </Link>

                                <Link
                                    href="/admin/media"
                                    onClick={() => setShowQuickActions(false)}
                                    className="flex flex-col items-center p-3 rounded-xl hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
                                >
                                    <div
                                        className="w-12 h-12 rounded-full bg-green-100 dark:bg-green-900/30 flex items-center justify-center mb-2">
                                        <svg className="w-6 h-6 text-green-600 dark:text-green-400" fill="none"
                                             viewBox="0 0 24 24" stroke="currentColor">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                                                  d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"/>
                                        </svg>
                                    </div>
                                    <span className="text-xs text-gray-700 dark:text-gray-300">上传图片</span>
                                </Link>

                                <Link
                                    href="/admin/blog?autoRun=show_article_modal"
                                    onClick={() => setShowQuickActions(false)}
                                    className="flex flex-col items-center p-3 rounded-xl hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
                                >
                                    <div
                                        className="w-12 h-12 rounded-full bg-purple-100 dark:bg-purple-900/30 flex items-center justify-center mb-2">
                                        <svg className="w-6 h-6 text-purple-600 dark:text-purple-400" fill="none"
                                             viewBox="0 0 24 24" stroke="currentColor">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                                                  d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/>
                                        </svg>
                                    </div>
                                    <span className="text-xs text-gray-700 dark:text-gray-300">快速草稿</span>
                                </Link>
                            </div>
                        </div>
                    </div>
                </>
            )}

            {/* 添加底部安全区域间距 */}
            <div className="h-16 md:hidden"/>
        </>
    );
};

export default MobileBottomNav;
