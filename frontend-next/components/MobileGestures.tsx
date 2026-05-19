'use client';

import {useEffect, useRef} from 'react';
import {useRouter} from 'next/navigation';
import {usePullToRefresh} from '@/hooks/useTouchGestures';

/**
 * 全局移动端手势组件 - 优化版
 * 提供：左滑返回、下拉刷新、滚动吸附等功能
 */
const MobileGestures = () => {
    const router = useRouter();
    const touchStartXRef = useRef(0);
    const touchStartYRef = useRef(0);
    const isSwipeGestureRef = useRef(false);

    // 下拉刷新功能
    const handleRefresh = async () => {
        // 刷新当前页面
        window.location.reload();
    };

    const {isRefreshing, pullDistance} = usePullToRefresh(handleRefresh);

    // 左滑返回功能 - 优化版
    useEffect(() => {
        const swipeThreshold = 100; // 滑动阈值
        const maxVerticalDelta = 50; // 允许的最大垂直偏移

        const handleTouchStart = (e: TouchEvent) => {
            // 只在屏幕左侧边缘开始滑动时触发
            if (e.touches[0].clientX < 30) {
                touchStartXRef.current = e.touches[0].clientX;
                touchStartYRef.current = e.touches[0].clientY;
                isSwipeGestureRef.current = true;
            }
        };

        const handleTouchMove = (e: TouchEvent) => {
            if (!isSwipeGestureRef.current) return;

            const currentX = e.touches[0].clientX;
            const currentY = e.touches[0].clientY;
            const deltaX = currentX - touchStartXRef.current;
            const deltaY = Math.abs(currentY - touchStartYRef.current);

            // 如果垂直移动过大，取消滑动手势
            if (deltaY > maxVerticalDelta) {
                isSwipeGestureRef.current = false;
            }

            // 如果向右滑动超过一定距离，提供视觉反馈（可以通过CSS实现）
            if (deltaX > 0 && deltaX < swipeThreshold) {
                // 可以添加页面跟随手指移动的视觉效果
                const progress = deltaX / swipeThreshold;
                document.body.style.transform = `translateX(${progress * 50}px)`;
            }
        };

        const handleTouchEnd = (e: TouchEvent) => {
            if (!isSwipeGestureRef.current) {
                document.body.style.transform = '';
                return;
            }

            const touchEndX = e.changedTouches[0].clientX;
            const deltaX = touchEndX - touchStartXRef.current;

            // 重置样式
            document.body.style.transition = 'transform 0.3s ease-out';
            document.body.style.transform = '';
            setTimeout(() => {
                document.body.style.transition = '';
            }, 300);

            // 检测右滑（从左向右滑动）
            if (deltaX > swipeThreshold) {
                // 如果不在首页，执行返回
                if (window.history.length > 1) {
                    router.back();
                }
            }

            isSwipeGestureRef.current = false;
            touchStartXRef.current = 0;
            touchStartYRef.current = 0;
        };

        document.addEventListener('touchstart', handleTouchStart, {passive: true});
        document.addEventListener('touchmove', handleTouchMove, {passive: true});
        document.addEventListener('touchend', handleTouchEnd, {passive: true});

        return () => {
            document.removeEventListener('touchstart', handleTouchStart);
            document.removeEventListener('touchmove', handleTouchMove);
            document.removeEventListener('touchend', handleTouchEnd);
        };
    }, [router]);

    // 渲染下拉刷新指示器 - 优化版
    if (isRefreshing || pullDistance > 0) {
        const opacity = Math.min(pullDistance / 80, 1);
        const rotate = pullDistance * 2;
        const scale = 0.8 + (pullDistance / 80) * 0.2;

        return (
            <div
                className="fixed top-0 left-0 right-0 z-50 flex items-center justify-center pointer-events-none"
                style={{
                    height: `${Math.min(pullDistance, 100)}px`,
                    opacity,
                    transition: 'all 0.2s ease-out',
                }}
            >
                <div
                    className="bg-white dark:bg-gray-800 rounded-full p-3 shadow-lg"
                    style={{
                        transform: `scale(${scale})`,
                        transition: 'transform 0.2s ease-out',
                    }}
                >
                    <svg
                        className={`w-6 h-6 text-blue-600 ${isRefreshing ? 'animate-spin' : ''}`}
                        style={{transform: `rotate(${rotate}deg)`, transition: 'transform 0.1s ease-out'}}
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
