/**
 * 移动端手势组件 - React 岛屿
 * 性能优化: passive listeners, 触摸事件节流
 */

'use client';

import {useEffect, useRef} from 'react';

const MobileGestures = () => {
    const touchStartX = useRef(0);
    const touchStartY = useRef(0);
  const rafRef = useRef<number | null>(null);

    useEffect(() => {
        const handleTouchStart = (e: TouchEvent) => {
            touchStartX.current = e.touches[0].clientX;
            touchStartY.current = e.touches[0].clientY;
        };

        const handleTouchEnd = (e: TouchEvent) => {
          const changedTouch = e.changedTouches[0];
          const endX = changedTouch.clientX;
          const endY = changedTouch.clientY;

          if (rafRef.current !== null) {
            cancelAnimationFrame(rafRef.current);
          }

          rafRef.current = requestAnimationFrame(() => {
            const deltaX = endX - touchStartX.current;
            const deltaY = endY - touchStartY.current;
            const absDeltaX = Math.abs(deltaX);
            const absDeltaY = Math.abs(deltaY);

            // 右滑返回（在屏幕左边缘）
            if (deltaX > 80 && absDeltaX > absDeltaY && touchStartX.current < 50) {
              window.history.back();
            }
            rafRef.current = null;
          });
        };

      // passive: true 提升滚动性能
      window.addEventListener('touchstart', handleTouchStart, {passive: true});
      window.addEventListener('touchend', handleTouchEnd, {passive: true});

        return () => {
            window.removeEventListener('touchstart', handleTouchStart);
            window.removeEventListener('touchend', handleTouchEnd);
          if (rafRef.current !== null) {
            cancelAnimationFrame(rafRef.current);
          }
        };
    }, []);

    return null;
};

export default MobileGestures;
