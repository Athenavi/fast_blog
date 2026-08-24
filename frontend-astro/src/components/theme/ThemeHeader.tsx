'use client';

/**
 * Header 槽位组件 — 由主题契约 componentSlots.header 决定渲染哪种头部：
 * - "floating"（默认）：现有浮动胶囊导航 Navbar
 * - "classic"：经典顶部导航条
 */
import {useThemeSlots} from '@/lib/theme-components';
import Navbar from '@/components/Navbar';
import ClassicHeader from './ClassicHeader';

export default function ThemeHeader() {
  const {header} = useThemeSlots();
  if (header === 'classic') return <ClassicHeader />;
  return <Navbar />;
}
