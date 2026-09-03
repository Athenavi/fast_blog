/**
 * useMediaQuery - 响应式媒体查询 Hook
 * 用于检测屏幕尺寸、设备类型、系统偏好等
 *
 * 使用示例:
 * ```tsx
 * const isMobile = useMediaQuery('(max-width: 767px)');
 * const isTablet = useMediaQuery('(min-width: 768px) and (max-width: 1023px)');
 * const isDark = useMediaQuery('(prefers-color-scheme: dark)');
 * const reducesMotion = useMediaQuery('(prefers-reduced-motion: reduce)');
 * ```
 */

import React, {useCallback, useEffect, useState} from 'react';

/** 常用断点常量 */
export const BREAKPOINTS = {
  sm: 640,    // 小屏手机
  md: 768,    // 平板/大屏手机
  lg: 1024,   // 小笔记本
  xl: 1280,   // 桌面
  '2xl': 1536 // 大屏桌面
} as const;

/** 常用媒体查询快捷方法 */
export function useIsMobile() {
  return useMediaQuery(`(max-width: ${BREAKPOINTS.md - 1}px)`);
}

export function useIsTablet() {
  return useMediaQuery(
    `(min-width: ${BREAKPOINTS.md}px) and (max-width: ${BREAKPOINTS.lg - 1}px)`
  );
}

export function useIsDesktop() {
  return useMediaQuery(`(min-width: ${BREAKPOINTS.lg}px)`);
}

export function useIsSmall() {
  return useMediaQuery(`(max-width: ${BREAKPOINTS.sm - 1}px)`);
}

export function useIsDark() {
  return useMediaQuery('(prefers-color-scheme: dark)');
}

export function useReducedMotion() {
  return useMediaQuery('(prefers-reduced-motion: reduce)');
}

export function useIsTouchDevice() {
  return useMediaQuery('(hover: none) and (pointer: coarse)');
}

export function useIsLandscape() {
  return useMediaQuery('(orientation: landscape)');
}

/**
 * 通用媒体查询 Hook
 * 支持 matchMedia API，回退到 ResizeObserver
 */
export function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState(() => {
    if (typeof window === 'undefined') return false;
    try {
      return window.matchMedia(query).matches;
    } catch {
      return false;
    }
  });

  useEffect(() => {
    if (typeof window === 'undefined') return;

    try {
      const mql = window.matchMedia(query);

      // 优先使用 addEventListener (现代浏览器)
      const handler = (e: MediaQueryListEvent) => setMatches(e.matches);

      if (typeof mql.addEventListener === 'function') {
        mql.addEventListener('change', handler);
      } else if (typeof mql.addListener === 'function') {
        // 回退到旧版 API
        mql.addListener(handler);
      }

      // 初始值以 listener 为准
      setMatches(mql.matches);

      return () => {
        if (typeof mql.removeEventListener === 'function') {
          mql.removeEventListener('change', handler);
        } else if (typeof mql.removeListener === 'function') {
          mql.removeListener(handler);
        }
      };
    } catch {
      // matchMedia 不可用时回退到 resize 检测
      const check = () => {
        try {
          // 简单的回退：通过 CSS 临时元素检测
          const elem = document.createElement('div');
          elem.style.cssText = `display:none;${query.replace(/[\(\)]/g, '')}`;
          document.body.appendChild(elem);
          const computed = window.getComputedStyle(elem);
          document.body.removeChild(elem);
          setMatches(computed.display !== 'none');
        } catch {
          setMatches(false);
        }
      };

      window.addEventListener('resize', check, {passive: true});
      check();
      return () => window.removeEventListener('resize', check);
    }
  }, [query]);

  return matches;
}

/**
 * 响应式容器宽度 Hook
 * 返回当前视口宽度适配的栏目数量
 */
export function useResponsiveColumns(minWidth: number = 280): number {
  const [columns, setColumns] = useState(1);
  const containerRef = useCallback((node: HTMLDivElement | null) => {
    if (!node) return;

    const update = () => {
      const width = node.clientWidth;
      const cols = Math.max(1, Math.floor(width / minWidth));
      setColumns(cols);
    };

    const ro = new ResizeObserver(update);
    ro.observe(node);
    update();

    return () => ro.disconnect();
  }, [minWidth]);

  return {columns, containerRef};
}

/**
 * 当前断点检测 Hook
 * 返回当前视口所属的断点名称 (sm/md/lg/xl/2xl)
 */
export function useBreakpoint(): keyof typeof BREAKPOINTS {
  const [breakpoint, setBreakpoint] = useState<keyof typeof BREAKPOINTS>(() => {
    if (typeof window === 'undefined') return 'sm';
    const w = window.innerWidth;
    if (w >= BREAKPOINTS['2xl']) return '2xl';
    if (w >= BREAKPOINTS.xl) return 'xl';
    if (w >= BREAKPOINTS.lg) return 'lg';
    if (w >= BREAKPOINTS.md) return 'md';
    return 'sm';
  });

  useEffect(() => {
    if (typeof window === 'undefined') return;

    const check = () => {
      const w = window.innerWidth;
      if (w >= BREAKPOINTS['2xl']) setBreakpoint('2xl');
      else if (w >= BREAKPOINTS.xl) setBreakpoint('xl');
      else if (w >= BREAKPOINTS.lg) setBreakpoint('lg');
      else if (w >= BREAKPOINTS.md) setBreakpoint('md');
      else setBreakpoint('sm');
    };

    // 使用 ResizeObserver 监听视口变化比 resize 事件更高效
    const ro = new ResizeObserver(check);
    ro.observe(document.documentElement);
    check();
    return () => ro.disconnect();
  }, []);

  return breakpoint;
}

/**
 * 响应式值 Hook
 * 根据断点返回不同值
 */
export function useResponsiveValue<T>(values: {
  sm: T;
  md?: T;
  lg?: T;
  xl?: T;
  '2xl'?: T;
}): T {
  const bp = useBreakpoint();
  // 从大到小查找第一个有值的断点
  const bpOrder: (keyof typeof values)[] = ['2xl', 'xl', 'lg', 'md', 'sm'];
  for (const b of bpOrder) {
    if ((values as any)[b] !== undefined) {
      // 当前断点 >= b 时返回
      const currentIdx = bpOrder.indexOf(bp);
      const bIdx = bpOrder.indexOf(b);
      if (currentIdx >= bIdx) {
        return (values as any)[b];
      }
    }
  }
  return values.sm;
}

/**
 * 容器查询 Hook (Container Queries API)
 * 如果浏览器不支持则回退到视口查询
 */
export function useContainerQuery(
  targetRef: React.RefObject<HTMLElement>,
  query: string
): boolean {
  const [matches, setMatches] = useState(false);

  useEffect(() => {
    const el = targetRef.current;
    if (!el) return;

    // 尝试 Container Queries API
    if ('ResizeObserver' in window && 'CSSContainerRule' in window) {
      try {
        // 需要在父容器设置 container-type
        const observer = new ResizeObserver(() => {
          // 简化回退：基于元素宽度计算
          const w = el.clientWidth;
          // 解析 min-width / max-width
          const minMatch = query.match(/min-width:\s*(\d+)px/);
          const maxMatch = query.match(/max-width:\s*(\d+)px/);
          let result = true;
          if (minMatch) result = result && w >= parseInt(minMatch[1]);
          if (maxMatch) result = result && w <= parseInt(maxMatch[1]);
          setMatches(result);
        });
        observer.observe(el);
        observer.entries().forEach(() => {
          const w = el.clientWidth;
          const minMatch = query.match(/min-width:\s*(\d+)px/);
          const maxMatch = query.match(/max-width:\s*(\d+)px/);
          let result = true;
          if (minMatch) result = result && w >= parseInt(minMatch[1]);
          if (maxMatch) result = result && w <= parseInt(maxMatch[1]);
          setMatches(result);
        });
        return () => observer.disconnect();
      } catch {
        // fallback below
      }
    }

    // 回退到 ResizeObserver
    const observer = new ResizeObserver(() => {
      const w = el.clientWidth;
      const minMatch = query.match(/min-width:\s*(\d+)px/);
      const maxMatch = query.match(/max-width:\s*(\d+)px/);
      let result = true;
      if (minMatch) result = result && w >= parseInt(minMatch[1]);
      if (maxMatch) result = result && w <= parseInt(maxMatch[1]);
      setMatches(result);
    });
    observer.observe(el);
    return () => observer.disconnect();
  }, [targetRef, query]);

  return matches;
}

export default useMediaQuery;
