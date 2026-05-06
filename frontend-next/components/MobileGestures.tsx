'use client';

import {useEffect} from 'react';
import {useRouter} from 'next/navigation';
import {usePullToRefresh} from '@/hooks/useTouchGestures';

/**
 * 全局移动端手势组件
 * 提供：左滑返回、下拉刷新等功能
 */
const MobileGestures = () => {
    const router = useRouter();

    // 下拉刷新功能
    const handleRefresh = async () => {
        // 刷新当前页面
        window.location.reload();
    };

    const {isRefreshing, pullDistance} = usePullToRefresh(handleRefresh);

    // 左滑返回功能
    useEffect(() => {
        let touchStartX = 0;
        let touchEndX = 0;
        const swipeThreshold = 100; // 滑动阈值

        const handleTouchStart = (e: TouchEvent) => {
            // 只在屏幕左侧边缘开始滑动时触发
            if (e.touches[0].clientX < 30) {
                touchStartX = e.touches[0].clientX;
            }
        };

        const handleTouchEnd = (e: TouchEvent) => {
            touchEndX = e.changedTouches[0].clientX;

            // 检测左滑（从左向右滑动）
            if (touchStartX > 0 && touchEndX - touchStartX > swipeThreshold) {
                // 如果不在首页，执行返回
                if (window.history.length > 1) {
                    router.back();
                }
            }

            touchStartX = 0;
            touchEndX = 0;
        };

        document.addEventListener('touchstart', handleTouchStart, {passive: true});
        document.addEventListener('touchend', handleTouchEnd, {passive: true});

        return () => {
            document.removeEventListener('touchstart', handleTouchStart);
            document.removeEventListener('touchend', handleTouchEnd);
        };
    }, [router]);

    // 渲染下拉刷新指示器
    if (isRefreshing || pullDistance > 0) {
        const opacity = Math.min(pullDistance / 80, 1);
        const rotate = pullDistance * 2;

        return (
            <div
                className="fixed top-0 left-0 right-0 z-50 flex items-center justify-center pointer-events-none"
                style={{
                    height: `${Math.min(pullDistance, 100)}px`,
                    opacity,
                }}
            >
                <div className="bg-white dark:bg-gray-800 rounded-full p-3 shadow-lg">
                    <svg
                        className={`w-6 h-6 text-blue-600 ${isRefreshing ? 'animate-spin' : ''}`}
                        style={{transform: `rotate(${rotate}deg)`}}
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                    >
                        <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                        />
                    </svg>
                </div>
            </div>
        );
    }

    return null;
};

export default MobileGestures;
