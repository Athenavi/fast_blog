'use client';

/**
 * Footer 槽位组件 — 由主题契约 componentSlots.footer 决定渲染哪种页脚：
 * - "default"（默认）：现有多列页脚 Footer
 * - "minimal"：极简页脚
 */
import {useThemeSlots} from '@/lib/theme-components';
import Footer from '@/components/Footer';
import MinimalFooter from './MinimalFooter';

export default function ThemeFooter() {
  const {footer} = useThemeSlots();
  if (footer === 'minimal') return <MinimalFooter />;
  return <Footer />;
}
