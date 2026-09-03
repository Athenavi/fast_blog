/**
 * 移动端底部导航栏 - React 岛屿
 * 适配 Astro：使用 <a> 替代 next/link, window.location 替代 usePathname
 * 性能优化：React.memo, 触摸适配, 安全区域
 */

'use client';

import {memo, useEffect, useState} from 'react';
import {Compass, Home, MessageSquare, PlusSquare, User} from 'lucide-react';

const navItems = [
  {name: '首页', href: '/', icon: Home},
  {name: '探索', href: '/articles', icon: Compass},
  {name: '消息', href: '/messages', icon: MessageSquare},
  {name: '创建', href: '/admin/editor', icon: PlusSquare},
  {name: '我的', href: '/profile', icon: User},
];

const NavItem = memo(({item, isActive}: { item: typeof navItems[0]; isActive: boolean }) => {
  const Icon = item.icon;
  return (
    <a
      href={item.href}
      aria-current={isActive ? 'page' : undefined}
      className={`flex flex-col items-center justify-center px-3 py-2 text-xs transition-colors touch-manipulation ${
        isActive ? 'text-blue-600 dark:text-blue-400' : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
      }`}
    >
      <Icon className="w-6 h-6 mb-1" stroke-width={isActive ? 2.5 : 2}/>
      <span>{item.name}</span>
    </a>
  );
});

NavItem.displayName = 'NavItem';

const MobileBottomNav = () => {
  const [pathname, setPathname] = useState(() => typeof window !== 'undefined' ? window.location.pathname : '/');
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const checkMobile = () => setIsMobile(window.innerWidth < 768);
    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  if (!isMobile) return null;

  return (
    <nav
      className="fixed bottom-0 left-0 right-0 z-50 bg-white dark:bg-gray-900 border-t border-gray-200 dark:border-gray-800 md:hidden mobile-bottom-nav touch-manipulation"
      role="navigation"
      aria-label="移动端导航"
    >
      <div className="flex items-center justify-around h-16 safe-pb">
        {navItems.map((item) => (
          <NavItem key={item.href} item={item} isActive={pathname === item.href}/>
        ))}
            </div>
        </nav>
    );
};

export default memo(MobileBottomNav);
