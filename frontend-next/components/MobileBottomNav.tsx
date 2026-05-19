'use client';

import {useEffect, useState} from 'react';
import Link from 'next/link';
import {usePathname} from 'next/navigation';
import {Compass, Home, MessageSquare, PlusSquare, User} from 'lucide-react';
import {AnimatePresence, motion} from 'framer-motion';

/**
 * 移动端底部导航栏 - 优化版
 * 使用 framer-motion 实现流畅动画和原生级交互体验
 */
const MobileBottomNav = () => {
    const pathname = usePathname();
    const [showQuickActions, setShowQuickActions] = useState(false);
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
            isAction: true,
        },
        {
            id: 'messages',
            label: '消息',
            icon: MessageSquare,
            href: '/messages',
            active: pathname && pathname.startsWith('/messages'),
            badge: 0,
        },
        {
            id: 'profile',
            label: '我的',
            icon: User,
            href: '/profile',
            active: (pathname && pathname.startsWith('/profile')) || (pathname && pathname.startsWith('/settings')),
        },
    ];

    // 动画变体
    const containerVariants = {
        hidden: {y: 100, opacity: 0},
        visible: {
            y: 0,
            opacity: 1,
            transition: {
                type: 'spring',
                stiffness: 300,
                damping: 30,
            },
        },
    };

    const itemVariants = {
        hidden: {scale: 0.8, opacity: 0},
        visible: (i: number) => ({
            scale: 1,
            opacity: 1,
            transition: {
                delay: i * 0.1,
                type: 'spring',
                stiffness: 300,
                damping: 20,
            },
        }),
    };

    const quickActionsVariants = {
        hidden: {opacity: 0, y: 20, scale: 0.95},
        visible: {
            opacity: 1,
            y: 0,
            scale: 1,
            transition: {
                type: 'spring',
                stiffness: 400,
                damping: 25,
            },
        },
        exit: {
            opacity: 0,
            y: 20,
            scale: 0.95,
            transition: {
                duration: 0.2,
            },
        },
    };

    return (
        <>
            {/* 底部导航栏 */}
            <motion.nav
                initial="hidden"
                animate="visible"
                variants={containerVariants}
                className="fixed bottom-0 left-0 right-0 z-50 bg-white/95 dark:bg-gray-900/95 backdrop-blur-lg border-t border-gray-200 dark:border-gray-800 md:hidden safe-area-bottom shadow-lg"
            >
                <div className="flex items-center justify-around h-16">
                    {navItems.map((item, index) => {
                        const Icon = item.icon;

                        // 特殊的发布按钮
                        if (item.isAction) {
                            return (
                                <motion.button
                                    key={item.id}
                                    custom={index}
                                    variants={itemVariants}
                                    whileTap={{scale: 0.9}}
                                    whileHover={{scale: 1.1}}
                                    onClick={() => setShowQuickActions(!showQuickActions)}
                                    className="relative -top-5 flex flex-col items-center justify-center"
                                >
                                    <motion.div
                                        className="w-14 h-14 rounded-full bg-gradient-to-r from-blue-500 to-purple-600 flex items-center justify-center shadow-lg hover:shadow-xl transition-shadow"
                                        whileHover={{
                                            boxShadow: '0 10px 25px rgba(59, 130, 246, 0.5)',
                                        }}
                                    >
                                        <Icon className="w-7 h-7 text-white"/>
                                    </motion.div>
                                    <span className="text-xs mt-1 text-gray-600 dark:text-gray-400">
                                        {item.label}
                                    </span>
                                </motion.button>
                            );
                        }

                        // 普通导航项
                        return (
                            <motion.div
                                key={item.id}
                                custom={index}
                                variants={itemVariants}
                                className="flex-1"
                            >
                                <Link
                                    href={item.href}
                                    className={`flex flex-col items-center justify-center h-full relative ${
                                        item.active
                                            ? 'text-blue-600 dark:text-blue-400'
                                            : 'text-gray-600 dark:text-gray-400'
                                    }`}
                                >
                                    <motion.div
                                        className="relative"
                                        whileTap={{scale: 0.9}}
                                    >
                                        <Icon className="w-6 h-6"/>
                                        {item.badge && item.badge > 0 && (
                                            <motion.span
                                                initial={{scale: 0}}
                                                animate={{scale: 1}}
                                                className="absolute -top-1 -right-1 w-4 h-4 bg-red-500 text-white text-xs rounded-full flex items-center justify-center"
                                            >
                                                {item.badge > 9 ? '9+' : item.badge}
                                            </motion.span>
                                        )}
                                    </motion.div>
                                    <span className="text-xs mt-1">{item.label}</span>

                                    {/* 激活指示器 */}
                                    {item.active && (
                                        <motion.div
                                            layoutId="activeTab"
                                            className="absolute top-0 left-1/2 transform -translate-x-1/2 w-12 h-0.5 bg-blue-600 dark:bg-blue-400 rounded-full"
                                            transition={{
                                                type: 'spring',
                                                stiffness: 380,
                                                damping: 30,
                                            }}
                                        />
                                    )}
                                </Link>
                            </motion.div>
                        );
                    })}
                </div>
            </motion.nav>

            {/* 快捷操作菜单 */}
            <AnimatePresence>
                {showQuickActions && (
                    <>
                        {/* 遮罩层 */}
                        <motion.div
                            initial={{opacity: 0}}
                            animate={{opacity: 1}}
                            exit={{opacity: 0}}
                            className="fixed inset-0 bg-black/50 backdrop-blur-sm z-40 md:hidden"
                            onClick={() => setShowQuickActions(false)}
                        />

                        {/* 快捷操作面板 */}
                        <motion.div
                            variants={quickActionsVariants}
                            initial="hidden"
                            animate="visible"
                            exit="exit"
                            className="fixed bottom-20 left-4 right-4 z-50 md:hidden"
                        >
                            <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-2xl p-4">
                                <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3 px-2">
                                    快捷操作
                                </h3>
                                <div className="grid grid-cols-3 gap-3">
                                    <motion.div
                                        whileTap={{scale: 0.95}}
                                        whileHover={{scale: 1.05}}
                                    >
                                        <Link
                                            href="/my/posts/create"
                                            onClick={() => setShowQuickActions(false)}
                                            className="flex flex-col items-center p-3 rounded-xl hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
                                        >
                                            <div
                                                className="w-12 h-12 rounded-full bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center mb-2">
                                                <PlusSquare className="w-6 h-6 text-blue-600 dark:text-blue-400"/>
                                            </div>
                                            <span className="text-xs text-gray-700 dark:text-gray-300">写文章</span>
                                        </Link>
                                    </motion.div>

                                    <motion.div
                                        whileTap={{scale: 0.95}}
                                        whileHover={{scale: 1.05}}
                                    >
                                        <Link
                                            href="/media"
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
                                    </motion.div>

                                    <motion.div
                                        whileTap={{scale: 0.95}}
                                        whileHover={{scale: 1.05}}
                                    >
                                        <Link
                                            href="/settings"
                                            onClick={() => setShowQuickActions(false)}
                                            className="flex flex-col items-center p-3 rounded-xl hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
                                        >
                                            <div
                                                className="w-12 h-12 rounded-full bg-purple-100 dark:bg-purple-900/30 flex items-center justify-center mb-2">
                                                <svg className="w-6 h-6 text-purple-600 dark:text-purple-400"
                                                     fill="none"
                                                     viewBox="0 0 24 24" stroke="currentColor">
                                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                                                          d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/>
                                                </svg>
                                            </div>
                                            <span className="text-xs text-gray-700 dark:text-gray-300">资料编辑</span>
                                        </Link>
                                    </motion.div>
                                </div>
                            </div>
                        </motion.div>
                    </>
                )}
            </AnimatePresence>

            {/* 添加底部安全区域间距 */}
            <div className="h-16 md:hidden"/>
        </>
    );
};

export default MobileBottomNav;
