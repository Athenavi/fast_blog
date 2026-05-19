'use client';

import {useEffect, useState} from 'react';
import {AnimatePresence, motion} from 'framer-motion';

/**
 * PWA 启动画面组件
 * 在应用首次加载时显示，提供原生 App 般的启动体验
 */
export default function Splashscreen() {
    const [isVisible, setIsVisible] = useState(true);
    const [isPWA, setIsPWA] = useState(false);

    useEffect(() => {
        // 检测是否为 PWA 模式
        const checkPWA = () => {
            const isStandalone = window.matchMedia('(display-mode: standalone)').matches;
            const isFullscreen = window.matchMedia('(display-mode: fullscreen)').matches;
            const isInWebAppiOS = (window.navigator as any).standalone === true;

            return isStandalone || isFullscreen || isInWebAppiOS;
        };

        const pwaMode = checkPWA();
        setIsPWA(pwaMode);

        // 如果不是 PWA 模式或已经访问过，不显示启动画面
        const hasSeenSplash = localStorage.getItem('has-seen-splash');

        if (!pwaMode || hasSeenSplash) {
            setIsVisible(false);
            return;
        }

        // 2秒后隐藏启动画面
        const timer = setTimeout(() => {
            setIsVisible(false);
            localStorage.setItem('has-seen-splash', 'true');
        }, 2000);

        return () => clearTimeout(timer);
    }, []);

    if (!isVisible) {
        return null;
    }

    return (
        <AnimatePresence>
            {isVisible && (
                <motion.div
                    initial={{opacity: 1}}
                    exit={{opacity: 0}}
                    transition={{duration: 0.5}}
                    className="fixed inset-0 z-[9999] bg-gradient-to-br from-blue-500 via-blue-600 to-purple-600 flex flex-col items-center justify-center"
                >
                    {/* Logo 动画 */}
                    <motion.div
                        initial={{scale: 0.8, opacity: 0}}
                        animate={{
                            scale: [0.8, 1.1, 1],
                            opacity: 1,
                        }}
                        transition={{
                            duration: 1.5,
                            times: [0, 0.6, 1],
                            ease: "easeOut",
                        }}
                        className="relative"
                    >
                        {/* Logo 容器 */}
                        <div className="w-32 h-32 bg-white rounded-3xl shadow-2xl flex items-center justify-center">
                            <svg
                                className="w-20 h-20 text-blue-600"
                                fill="none"
                                viewBox="0 0 24 24"
                                stroke="currentColor"
                            >
                                <path
                                    strokeLinecap="round"
                                    strokeLinejoin="round"
                                    strokeWidth={2}
                                    d="M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10a2 2 0 012 2v1m2 13a2 2 0 01-2-2V7m2 13a2 2 0 002-2V9a2 2 0 00-2-2h-2m-4-3H9M7 16h6M7 8h6v4H7V8z"
                                />
                            </svg>
                        </div>

                        {/* 光晕效果 */}
                        <motion.div
                            animate={{
                                scale: [1, 1.2, 1],
                                opacity: [0.5, 0, 0.5],
                            }}
                            transition={{
                                duration: 2,
                                repeat: Infinity,
                                ease: "easeInOut",
                            }}
                            className="absolute inset-0 bg-white rounded-3xl blur-xl -z-10"
                        />
                    </motion.div>

                    {/* 应用名称 */}
                    <motion.h1
                        initial={{y: 20, opacity: 0}}
                        animate={{y: 0, opacity: 1}}
                        transition={{delay: 0.3, duration: 0.5}}
                        className="mt-8 text-4xl font-bold text-white tracking-wide"
                    >
                        FastBlog
                    </motion.h1>

                    {/* 副标题 */}
                    <motion.p
                        initial={{y: 20, opacity: 0}}
                        animate={{y: 0, opacity: 1}}
                        transition={{delay: 0.5, duration: 0.5}}
                        className="mt-2 text-lg text-white/80"
                    >
                        现代化博客平台
                    </motion.p>

                    {/* 加载指示器 */}
                    <motion.div
                        initial={{opacity: 0}}
                        animate={{opacity: 1}}
                        transition={{delay: 0.8, duration: 0.5}}
                        className="mt-12 flex items-center gap-2"
                    >
                        <motion.div
                            animate={{
                                scale: [1, 1.2, 1],
                                opacity: [0.5, 1, 0.5],
                            }}
                            transition={{
                                duration: 1,
                                repeat: Infinity,
                                delay: 0,
                            }}
                            className="w-2 h-2 bg-white rounded-full"
                        />
                        <motion.div
                            animate={{
                                scale: [1, 1.2, 1],
                                opacity: [0.5, 1, 0.5],
                            }}
                            transition={{
                                duration: 1,
                                repeat: Infinity,
                                delay: 0.2,
                            }}
                            className="w-2 h-2 bg-white rounded-full"
                        />
                        <motion.div
                            animate={{
                                scale: [1, 1.2, 1],
                                opacity: [0.5, 1, 0.5],
                            }}
                            transition={{
                                duration: 1,
                                repeat: Infinity,
                                delay: 0.4,
                            }}
                            className="w-2 h-2 bg-white rounded-full"
                        />
                    </motion.div>

                    {/* PWA 提示（仅在 PWA 模式下显示） */}
                    {isPWA && (
                        <motion.div
                            initial={{opacity: 0}}
                            animate={{opacity: 1}}
                            transition={{delay: 1, duration: 0.5}}
                            className="absolute bottom-12 text-center"
                        >
                            <p className="text-white/60 text-sm">
                                已安装到主屏幕
                            </p>
                            <p className="text-white/40 text-xs mt-1">
                                享受原生应用体验
                            </p>
                        </motion.div>
                    )}
                </motion.div>
            )}
        </AnimatePresence>
    );
}
