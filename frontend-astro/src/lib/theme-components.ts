'use client';

import {useEffect, useState} from 'react';

/**
 * 主题组件槽位 — 由激活主题契约的 componentSlots 驱动。
 * 主题可覆盖：header / articleCard / footer 的实现变体。
 *
 * 取值来源：Layout 内联脚本把契约 componentSlots 写到 <html> 的
 * data-theme-* 属性并在应用后派发 `theme:applied` 事件。
 * 因此本 hook 不依赖 react-query（SSR 安全），并在契约应用后触发重渲染。
 */
export interface ThemeSlots {
  header: 'floating' | 'classic';
  articleCard: 'default' | 'compact';
  footer: 'default' | 'minimal';
}

const DEFAULTS: ThemeSlots = {header: 'floating', articleCard: 'default', footer: 'default'};

export function useThemeSlots(): ThemeSlots {
  const [, setTick] = useState(0);

  useEffect(() => {
    const apply = () => setTick((t) => t + 1);
    window.addEventListener('theme:applied', apply);
    return () => window.removeEventListener('theme:applied', apply);
  }, []);

  const d = typeof document !== 'undefined' ? document.documentElement.dataset : undefined;
  return {
    header: (d?.themeHeader as ThemeSlots['header']) || DEFAULTS.header,
    articleCard: (d?.themeCard as ThemeSlots['articleCard']) || DEFAULTS.articleCard,
    footer: (d?.themeFooter as ThemeSlots['footer']) || DEFAULTS.footer,
  };
}
