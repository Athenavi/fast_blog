/**
 * useFontLoading - 字体加载优化 Hook
 * 使用 Font Loading API (document.fonts) 优化字体加载体验
 *
 * 功能：
 * 1. 预连接字体源 (preconnect)
 * 2. 预加载关键字体 (preload)
 * 3. 字体加载状态监控
 * 4. font-display 优化
 * 5. 弱网络下降级策略
 *
 * 使用示例:
 * ```tsx
 * const fonts = useFontLoading({
 *   fonts: [
 *     {family: 'Inter', url: '/fonts/inter.woff2'},
 *     {family: 'Noto Sans SC', url: '/fonts/noto-sans-sc.woff2'}
 *   ],
 *   preconnect: ['https://fonts.gstatic.com']
 * });
 *
 * if (!fonts.loaded) {
 *   // 字体未加载完成，可以使用 fallback 字体
 * }
 * ```
 */

import {useCallback, useEffect, useRef, useState} from 'react';
import {useNetworkState} from './useNetworkState';

interface FontConfig {
  family: string;
  url: string;
  /** 字体显示策略 */
  display?: 'swap' | 'fallback' | 'optional' | 'block';
  /** 字体权重 */
  weight?: string;
  /** 是否关键字体（首屏需要） */
  critical?: boolean;
}

interface FontLoadingState {
  /** 所有字体是否加载完成 */
  loaded: boolean;
  /** 关键字体是否加载完成 */
  criticalLoaded: boolean;
  /** 字体加载进度 */
  progress: number;
  /** 各字体加载状态 */
  fontStatus: Map<string, 'loading' | 'loaded' | 'failed' | 'skipped'>;
  /** 是否使用了 fallback */
  usingFallback: boolean;
}

export function useFontLoading(config: {
  fonts: FontConfig[];
  /** 字体源预连接 */
  preconnect?: string[];
}) {
  const {fonts, preconnect: preconnectOrigins = []} = config;
  const network = useNetworkState();
  const [state, setState] = useState<FontLoadingState>({
    loaded: false,
    criticalLoaded: false,
    progress: 0,
    fontStatus: new Map(),
    usingFallback: false
  });
  const initialized = useRef(false);

  // 设置 preconnect 和 preload
  useEffect(() => {
    if (initialized.current) return;
    initialized.current = true;

    // 设置 preconnect
    preconnectOrigins.forEach(origin => {
      if (!document.querySelector(`link[rel="preconnect"][href="${origin}"]`)) {
        const link = document.createElement('link');
        link.rel = 'preconnect';
        link.href = origin;
        link.crossOrigin = 'anonymous';
        document.head.appendChild(link);
      }
    });

    // 弱网络下字体降级
    if (network.isSlow || network.saveData) {
      setState(prev => ({
        ...prev,
        loaded: true,
        criticalLoaded: true,
        usingFallback: true
      }));
      return;
    }

    // 预加载关键字体
    fonts.filter(f => f.critical).forEach(font => {
      const existing = document.querySelector(`link[rel="preload"][href="${font.url}"]`);
      if (!existing) {
        const link = document.createElement('link');
        link.rel = 'preload';
        link.as = 'font';
        link.href = font.url;
        link.type = 'font/woff2';
        link.crossOrigin = 'anonymous';
        document.head.appendChild(link);
      }
    });

    // 注入 CSS font-face
    const styleId = 'font-loading-style';
    let style = document.getElementById(styleId);
    if (!style) {
      style = document.createElement('style');
      style.id = styleId;
      document.head.appendChild(style);
    }

    const cssRules = fonts.map(font => {
      const display = font.display || 'swap';
      return `@font-face {
  font-family: '${font.family}';
  src: url('${font.url}') format('woff2');
  font-display: ${display};
  font-weight: ${font.weight || 'normal'};
  font-style: normal;
  font-stretch: normal;
}`;
    }).join('\n');

    style.textContent = cssRules;
  }, [fonts, preconnectOrigins, network.isSlow, network.saveData, network.isOnline]);

  // 监控字体加载状态
  useEffect(() => {
    if (typeof document?.fonts === 'undefined') {
      setState(prev => ({...prev, loaded: true, criticalLoaded: true}));
      return;
    }

    const status = new Map<string, 'loading' | 'loaded' | 'failed' | 'skipped'>();
    const criticalFamilies = fonts.filter(f => f.critical).map(f => f.family);

    fonts.forEach(font => {
      status.set(font.family, 'loading');
    });

    const updateState = () => {
      const newStatus = new Map(status);
      let total = fonts.length;
      let loaded = 0;
      let criticalTotal = criticalFamilies.length;
      let criticalLoaded = 0;

      fonts.forEach(font => {
        if (newStatus.get(font.family) === 'loaded') {
          loaded++;
          if (criticalFamilies.includes(font.family)) criticalLoaded++;
        }
      });

      const allLoaded = loaded === total;
      const criticalDone = criticalLoaded === criticalTotal;

      setState({
        loaded: allLoaded,
        criticalLoaded: criticalDone,
        progress: total > 0 ? (loaded / total) : 1,
        fontStatus: newStatus,
        usingFallback: false
      });
    };

    fonts.forEach(font => {
      try {
        document.fonts.load(`1em '${font.family}`)
          .then(() => {
            status.set(font.family, 'loaded');
            updateState();
          })
          .catch(() => {
            status.set(font.family, 'failed');
            updateState();
          });
      } catch {
        status.set(font.family, 'skipped');
        updateState();
      }
    });
  }, [fonts]);

  // 应用字体类名
  const applyClass = useCallback(() => {
    const root = document.documentElement;
    if (state.loaded) {
      root.classList.add('fonts-loaded');
    } else {
      root.classList.remove('fonts-loaded');
    }
  }, [state.loaded]);

  useEffect(() => {
    applyClass();
  }, [applyClass]);

  return {
    ...state,
    /** 是否为关键字体加载完成的 */
    isReady: state.criticalLoaded,
    /** CSS 类名 */
    className: state.loaded ? 'fonts-loaded' : 'fonts-loading'
  };
}

/**
 * 字体加载优化组件
 * 在字体加载期间隐藏文字闪烁
 */
export const FontLoadingStyles: React.FC = () => {
  return (
    <style>{`
      /* 字体加载前使用 similar font 防止闪烁 */
      .fonts-loading {
        text-rendering: optimizeLegibility;
        -webkit-font-smoothing: antialiased;
        -moz-osx-font-smoothing: grayscale;
      }

      /* 字体切换过渡 */
      .fonts-loaded * {
        transition: opacity 0.1s ease-in;
      }

      /* 防止字体加载导致的布局偏移 */
      @supports (font-palette: light-dark(rgb(0 0 0), rgb(255 255 255))) {
        .fonts-loading .font-critical {
          opacity: 0;
        }
        .fonts-loaded .font-critical {
          opacity: 1;
        }
      }
    `
}
  </style>
)
  ;
};

export default useFontLoading;
