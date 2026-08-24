// 主题契约应用：把激活主题的 settings 映射为 CSS 变量与布局属性
// 供页面在运行时应用主题（颜色/排版/圆角/布局），组件据 data-* 属性响应布局开关。
export interface ThemeLayout {
  sidebarPosition?: 'left' | 'right' | 'none';
  contentWidth?: string;
  showHeader?: boolean;
  showFooter?: boolean;
}

export function applyThemeContract(contract: any): ThemeLayout {
  const layoutResult: ThemeLayout = {};
  if (typeof document === 'undefined') return layoutResult;

  const s = contract?.settings;
  if (!s) return layoutResult;

  const root = document.documentElement;
  const setVar = (name: string, val?: string | number) => {
    if (val !== undefined && val !== null && val !== '') root.style.setProperty(name, String(val));
  };

  // ── 颜色 → 设计 token ──
  const colors = s.colors || {};
  setVar('--color-primary', colors.primary);
  setVar('--color-primary-hover', colors.primary);
  setVar('--color-accent', colors.accent);
  setVar('--color-surface', colors.background);
  setVar('--color-surface-elevated', colors.muted);
  setVar('--color-text', colors.foreground);
  setVar('--color-text-secondary', colors.secondary);
  setVar('--color-text-muted', colors.muted);
  setVar('--color-muted', colors.muted);
  setVar('--color-border', colors.border);

  // ── 排版 → 字体 ──
  const typo = s.typography || {};
  if (typo.fontFamily) setVar('--font-sans', typo.fontFamily);

  // ── 组件 → 圆角 ──
  const comp = s.components || {};
  if (comp.borderRadius) {
    ['--radius-sm', '--radius-md', '--radius-lg', '--radius-xl', '--radius-2xl']
      .forEach((n) => setVar(n, comp.borderRadius));
  }

  // ── 布局 → data-* 属性 ──
  const layout = contract?.layout || s.layout || {};
  if (layout.sidebarPosition) {
    root.dataset.sidebar = layout.sidebarPosition;
    layoutResult.sidebarPosition = layout.sidebarPosition;
  }
  if (layout.contentWidth) {
    root.dataset.contentWidth = layout.contentWidth;
    layoutResult.contentWidth = layout.contentWidth;
  }
  if (typeof layout.showHeader === 'boolean') {
    root.dataset.showHeader = String(layout.showHeader);
    layoutResult.showHeader = layout.showHeader;
  }
  if (typeof layout.showFooter === 'boolean') {
    root.dataset.showFooter = String(layout.showFooter);
    layoutResult.showFooter = layout.showFooter;
  }

  return layoutResult;
}
