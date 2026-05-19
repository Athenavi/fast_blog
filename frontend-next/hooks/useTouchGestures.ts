import {useEffect, useRef, useState} from 'react';

interface TouchGestureOptions {
    onSwipeLeft?: () => void;
    onSwipeRight?: () => void;
    onSwipeUp?: () => void;
    onSwipeDown?: () => void;
    onTap?: () => void;
    onDoubleTap?: () => void;
    onLongPress?: () => void;
    swipeThreshold?: number; // 滑动阈值（像素）
    tapThreshold?: number; // 点击时间阈值（毫秒）
    longPressDelay?: number; // 长按延迟（毫秒）
}

/**
 * 移动端触摸手势Hook
 * 支持：滑动、点击、双击、长按等手势
 */
export const useTouchGestures = (options: TouchGestureOptions = {}) => {
    const {
        onSwipeLeft,
        onSwipeRight,
        onSwipeUp,
        onSwipeDown,
        onTap,
        onDoubleTap,
        onLongPress,
        swipeThreshold = 50,
        tapThreshold = 300,
        longPressDelay = 500,
    } = options;

    const [isGestureActive, setIsGestureActive] = useState(false);

    const touchStartRef = useRef<{ x: number; y: number; time: number } | null>(null);
    const lastTapRef = useRef<number>(0);
    const longPressTimerRef = useRef<NodeJS.Timeout | null>(null);
    const elementRef = useRef<HTMLElement | null>(null);

    const handleTouchStart = (e: TouchEvent) => {
        const touch = e.touches[0];
        touchStartRef.current = {
            x: touch.clientX,
            y: touch.clientY,
            time: Date.now(),
        };
        setIsGestureActive(true);

        // 设置长按定时器
        if (onLongPress) {
            longPressTimerRef.current = setTimeout(() => {
                if (touchStartRef.current) {
                    onLongPress();
                    touchStartRef.current = null; // 防止触发其他手势
                }
            }, longPressDelay);
        }
    };

    const handleTouchMove = (e: TouchEvent) => {
        if (!touchStartRef.current) return;

        const touch = e.touches[0];
        const deltaX = touch.clientX - touchStartRef.current.x;
        const deltaY = touch.clientY - touchStartRef.current.y;

        // 如果移动距离超过阈值，取消长按
        if (Math.abs(deltaX) > 10 || Math.abs(deltaY) > 10) {
            if (longPressTimerRef.current) {
                clearTimeout(longPressTimerRef.current);
                longPressTimerRef.current = null;
            }
        }
    };

    const handleTouchEnd = (e: TouchEvent) => {
        if (!touchStartRef.current) return;

        // 清除长按定时器
        if (longPressTimerRef.current) {
            clearTimeout(longPressTimerRef.current);
            longPressTimerRef.current = null;
        }

        const touch = e.changedTouches[0];
        const deltaX = touch.clientX - touchStartRef.current.x;
        const deltaY = touch.clientY - touchStartRef.current.y;
        const deltaTime = Date.now() - touchStartRef.current.time;

        const absDeltaX = Math.abs(deltaX);
        const absDeltaY = Math.abs(deltaY);

        // 检测滑动
        if (absDeltaX > swipeThreshold || absDeltaY > swipeThreshold) {
            if (absDeltaX > absDeltaY) {
                // 水平滑动
                if (deltaX > 0 && onSwipeRight) {
                    onSwipeRight();
                } else if (deltaX < 0 && onSwipeLeft) {
                    onSwipeLeft();
                }
            } else {
                // 垂直滑动
                if (deltaY > 0 && onSwipeDown) {
                    onSwipeDown();
                } else if (deltaY < 0 && onSwipeUp) {
                    onSwipeUp();
                }
            }
        } else if (deltaTime < tapThreshold) {
            // 检测点击/双击
            const currentTime = Date.now();
            const timeSinceLastTap = currentTime - lastTapRef.current;

            if (timeSinceLastTap < tapThreshold && timeSinceLastTap > 0) {
                // 双击
                if (onDoubleTap) {
                    onDoubleTap();
                }
                lastTapRef.current = 0;
            } else {
                // 单击
                if (onTap) {
                    onTap();
                }
                lastTapRef.current = currentTime;
            }
        }

        touchStartRef.current = null;
        setIsGestureActive(false);
    };

    useEffect(() => {
        const element = elementRef.current;
        if (!element) return;

        // 添加触摸事件监听器
        element.addEventListener('touchstart', handleTouchStart, {passive: true});
        element.addEventListener('touchmove', handleTouchMove, {passive: true});
        element.addEventListener('touchend', handleTouchEnd, {passive: true});

        // 清理
        return () => {
            element.removeEventListener('touchstart', handleTouchStart);
            element.removeEventListener('touchmove', handleTouchMove);
            element.removeEventListener('touchend', handleTouchEnd);

            if (longPressTimerRef.current) {
                clearTimeout(longPressTimerRef.current);
            }
        };
    }, [onSwipeLeft, onSwipeRight, onSwipeUp, onSwipeDown, onTap, onDoubleTap, onLongPress]);

    return {
        ref: elementRef,
        isGestureActive,
    };
};

/**
 * 下拉刷新Hook - 优化版
 * 添加弹性动画和触觉反馈支持
 */
export const usePullToRefresh = (onRefresh: () => Promise<void>, threshold = 80) => {
    const [isRefreshing, setIsRefreshing] = useState(false);
    const [pullDistance, setPullDistance] = useState(0);

    const startYRef = useRef<number>(0);
    const currentYRef = useRef<number>(0);
    const isPullingRef = useRef(false);

    // 触发触觉反馈（如果支持）
    const triggerHapticFeedback = (type: 'light' | 'medium' | 'heavy' = 'light') => {
        if ('vibrate' in navigator) {
            const patterns = {
                light: 10,
                medium: 20,
                heavy: 40,
            };
            navigator.vibrate(patterns[type]);
        }
    };

    const handleTouchStart = (e: TouchEvent) => {
        // 只有在页面顶部时才启用下拉刷新
        if (window.scrollY === 0 && !isRefreshing) {
            startYRef.current = e.touches[0].clientY;
            isPullingRef.current = true;
        }
    };

    const handleTouchMove = (e: TouchEvent) => {
        if (!isPullingRef.current || isRefreshing) return;

        currentYRef.current = e.touches[0].clientY;
        const distance = currentYRef.current - startYRef.current;

        // 只处理向下拉
        if (distance > 0) {
            // 使用阻力效果，让拉动感觉更自然
            const resistanceDistance = Math.pow(distance, 0.85);
            setPullDistance(Math.min(resistanceDistance, threshold * 1.5));

            // 当达到阈值时提供触觉反馈
            if (distance >= threshold && pullDistance < threshold) {
                triggerHapticFeedback('medium');
            }
        }
    };

    const handleTouchEnd = async () => {
        if (!isPullingRef.current) return;

        isPullingRef.current = false;

        // 如果拉动距离超过阈值，触发刷新
        if (pullDistance >= threshold && !isRefreshing) {
            setIsRefreshing(true);
            triggerHapticFeedback('heavy');
            try {
                await onRefresh();
            } finally {
                setIsRefreshing(false);
            }
        }

        // 添加弹性回弹动画
        setPullDistance(0);
    };

    useEffect(() => {
        document.addEventListener('touchstart', handleTouchStart, {passive: true});
        document.addEventListener('touchmove', handleTouchMove, {passive: false});
        document.addEventListener('touchend', handleTouchEnd);

        return () => {
            document.removeEventListener('touchstart', handleTouchStart);
            document.removeEventListener('touchmove', handleTouchMove);
            document.removeEventListener('touchend', handleTouchEnd);
        };
    }, [onRefresh, threshold, isRefreshing, pullDistance]);

    return {
        isRefreshing,
        pullDistance,
    };
};

/**
 * 图片双指缩放Hook
 */
export const usePinchZoom = (options: { minScale?: number; maxScale?: number } = {}) => {
    const {minScale = 1, maxScale = 3} = options;

    const [scale, setScale] = useState(1);
    const [isZooming, setIsZooming] = useState(false);

    const initialDistanceRef = useRef<number>(0);
    const initialScaleRef = useRef<number>(1);

    const getDistance = (touch1: Touch, touch2: Touch) => {
        const dx = touch1.clientX - touch2.clientX;
        const dy = touch1.clientY - touch2.clientY;
        return Math.sqrt(dx * dx + dy * dy);
    };

    const handleTouchStart = (e: TouchEvent) => {
        if (e.touches.length === 2) {
            setIsZooming(true);
            initialDistanceRef.current = getDistance(e.touches[0], e.touches[1]);
            initialScaleRef.current = scale;
        }
    };

    const handleTouchMove = (e: TouchEvent) => {
        if (e.touches.length !== 2 || !isZooming) return;

        e.preventDefault();

        const currentDistance = getDistance(e.touches[0], e.touches[1]);
        const scaleFactor = currentDistance / initialDistanceRef.current;
        const newScale = Math.min(Math.max(initialScaleRef.current * scaleFactor, minScale), maxScale);

        setScale(newScale);
    };

    const handleTouchEnd = () => {
        setIsZooming(false);
    };

    useEffect(() => {
        document.addEventListener('touchstart', handleTouchStart, {passive: true});
        document.addEventListener('touchmove', handleTouchMove, {passive: false});
        document.addEventListener('touchend', handleTouchEnd);

        return () => {
            document.removeEventListener('touchstart', handleTouchStart);
            document.removeEventListener('touchmove', handleTouchMove);
            document.removeEventListener('touchend', handleTouchEnd);
        };
    }, [scale, isZooming]);

    return {
        scale,
        isZooming,
        setScale,
    };
};
