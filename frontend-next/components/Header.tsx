'use client';

import React, {useEffect, useState} from 'react';
import Link from 'next/link';
import {usePathname} from 'next/navigation';
import {useAuth} from '@/hooks/useAuth';
import UserDropdown from './UserDropdown';
import {MenuService, MenuTreeItem} from '@/lib/api/menu-service';
import {ChevronDown, Menu as MenuIcon, X} from 'lucide-react';

const Header = () => {
  const { user, loading, logout } = useAuth();
  const pathname = usePathname();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [menuItems, setMenuItems] = useState<MenuTreeItem[]>([]);
  const [isMenuLoading, setIsMenuLoading] = useState(true);

  // 获取菜单数据
  useEffect(() => {
    const fetchMenuData = async () => {
      try {
        setIsMenuLoading(true);
        const response = await MenuService.getMainMenu();
        if (response.success && response.data) {
          setMenuItems(response.data);
        } else {
          // 如果没有获取到菜单数据，使用默认菜单
          setMenuItems([
            { id: 1, title: '首页', url: '/', target: '_self', order_index: 1, is_active: true, menu_id: 1, children: [] },
            { id: 2, title: '分类', url: '/categories', target: '_self', order_index: 2, is_active: true, menu_id: 1, children: [] },
            { id: 3, title: '关于', url: '/about', target: '_self', order_index: 3, is_active: true, menu_id: 1, children: [] },
          ]);
        }
      } catch (error) {
        console.error('Failed to fetch menu data:', error);
        // 错误情况下使用默认菜单
        setMenuItems([
          { id: 1, title: '首页', url: '/', target: '_self', order_index: 1, is_active: true, menu_id: 1, children: [] },
          { id: 2, title: '分类', url: '/categories', target: '_self', order_index: 2, is_active: true, menu_id: 1, children: [] },
          { id: 3, title: '关于', url: '/about', target: '_self', order_index: 3, is_active: true, menu_id: 1, children: [] },
        ]);
      } finally {
        setIsMenuLoading(false);
      }
    };

    fetchMenuData();
  }, []);

  // 检查当前路径是否匹配菜单项
  const isActiveLink = (url: string) => {
    if (url === '/') {
      return pathname === '/';
    }
    return pathname.startsWith(url.replace(/\/$/, ''));
  };

  // 渲染菜单项及其子菜单
  const renderMenuItems = (items: MenuTreeItem[], depth = 0) => {
    if (!items || !Array.isArray(items)) {
      return null;
    }

    return items.map((item) => {
      const isActive = isActiveLink(item.url);
      const hasChildren = item.children && item.children.length > 0;

      return (
        <div key={item.id} className={`${depth === 0 ? 'relative group' : ''} overflow-hidden`}>
          {hasChildren ? (
            <div className="relative overflow-hidden">
              <button
                className={`flex items-center space-x-1 px-3 py-2 rounded-md text-sm font-medium transition-colors duration-200 whitespace-nowrap overflow-hidden ${
                  isActive
                    ? 'text-blue-600 bg-blue-50 dark:bg-blue-900/30 dark:text-blue-400'
                    : 'text-gray-700 hover:text-blue-600 dark:text-gray-300 dark:hover:text-blue-400'
                }`}
              >
                <span className="truncate">{item.title}</span>
                <ChevronDown className="w-4 h-4 flex-shrink-0" />
              </button>
              <div className="absolute left-0 mt-2 w-48 bg-white dark:bg-gray-800 rounded-md shadow-lg opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 z-50 overflow-hidden">
                <div className="py-1 overflow-hidden">
                  {item.children && renderMenuItems(item.children, depth + 1)}
                </div>
              </div>
            </div>
          ) : (
            <Link
              href={item.url as any}
              target={item.target === '_blank' ? '_blank' : undefined}
              rel={item.target === '_blank' ? 'noopener noreferrer' : undefined}
              className={`px-3 py-2 rounded-md text-sm font-medium transition-colors duration-200 whitespace-nowrap overflow-hidden ${
                isActive
                  ? 'text-blue-600 bg-blue-50 dark:bg-blue-900/30 dark:text-blue-400'
                  : 'text-gray-700 hover:text-blue-600 dark:text-gray-300 dark:hover:text-blue-400'
              }`}
            >
              <span className="truncate">{item.title}</span>
            </Link>
          )}
        </div>
      );
    });
  };

  return (
    <header className="bg-white dark:bg-gray-800 shadow-md sticky top-0 z-40 overflow-hidden">
      <div className="container mx-auto px-4 py-4">
        <div className="flex justify-between items-center overflow-hidden">
          <div className="flex items-center overflow-hidden">
            <Link href="/" className="text-xl font-bold text-blue-600 dark:text-blue-400 whitespace-nowrap overflow-hidden">
              FastBlog
            </Link>
          </div>

          {/* 桌面端导航 */}
          <nav className="hidden md:flex items-center space-x-1 overflow-hidden">
            {isMenuLoading ? (
              <div className="px-4 py-2 text-sm text-gray-500 whitespace-nowrap">加载中...</div>
            ) : (
              <div className="flex items-center space-x-1 overflow-hidden">
                {renderMenuItems(menuItems)}
              </div>
            )}
          </nav>

          <div className="flex items-center space-x-4 overflow-hidden">
            {/* 移动端菜单按钮 */}
            <button
              className="md:hidden text-gray-700 dark:text-gray-300 focus:outline-none flex-shrink-0"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              aria-label="切换菜单"
            >
              {mobileMenuOpen ? <X className="w-6 h-6" /> : <MenuIcon className="w-6 h-6" />}
            </button>

            {loading ? (
              // 加载状态时显示加载指示器
              <div className="hidden md:flex space-x-4 overflow-hidden">
                <div className="px-4 py-2 text-sm text-gray-500 rounded-md whitespace-nowrap">加载中...</div>
              </div>
            ) : user ? (
              // 用户已登录时显示用户下拉菜单
              <div className="hidden md:flex items-center space-x-4 overflow-hidden">
                <div className="flex-shrink-0">
                  <UserDropdown user={user} />
                </div>
              </div>
            ) : (
              // 用户未登录时显示登录和注册按钮
              <div className="hidden md:flex items-center space-x-4 overflow-hidden">
                <Link
                  href="/login"
                  className="px-4 py-2 text-sm text-blue-600 hover:bg-blue-50 rounded-md dark:text-blue-400 dark:hover:bg-gray-700 whitespace-nowrap flex-shrink-0"
                >
                  登录
                </Link>
                <Link
                  href="/register"
                  className="px-4 py-2 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700 dark:bg-blue-700 dark:hover:bg-blue-800 whitespace-nowrap flex-shrink-0"
                >
                  注册
                </Link>
              </div>
            )}
          </div>
        </div>

        {/* 移动端导航菜单 */}
        {mobileMenuOpen && (
          <div className="md:hidden py-4 border-t border-gray-200 dark:border-gray-700 overflow-hidden">
            <nav className="flex flex-col space-y-2 overflow-hidden">
              {isMenuLoading ? (
                <div className="px-4 py-2 text-sm text-gray-500 whitespace-nowrap">加载中...</div>
              ) : (
                <>
                  <div className="overflow-hidden">
                    {renderMenuItems(menuItems)}
                  </div>
                  
                  {/* 用户认证相关的移动端链接 */}
                  {loading ? (
                    <div className="px-4 py-2 text-sm text-gray-500 whitespace-nowrap">加载中...</div>
                  ) : user ? (
                    <div className="pt-4 border-t border-gray-200 dark:border-gray-700 overflow-hidden">
                      <div className="flex-shrink-0">
                        <UserDropdown user={user} />
                      </div>
                    </div>
                  ) : (
                    <div className="flex flex-col space-y-3 pt-4 border-t border-gray-200 dark:border-gray-700 overflow-hidden">
                      <Link
                        href="/login"
                        className="px-4 py-2 text-sm text-blue-600 hover:bg-blue-50 rounded-md dark:text-blue-400 dark:hover:bg-gray-700 text-center whitespace-nowrap"
                        onClick={() => setMobileMenuOpen(false)}
                      >
                        登录
                      </Link>
                      <Link
                        href="/register"
                        className="px-4 py-2 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700 dark:bg-blue-700 dark:hover:bg-blue-800 text-center whitespace-nowrap"
                        onClick={() => setMobileMenuOpen(false)}
                      >
                        注册
                      </Link>
                    </div>
                  )}
                </>
              )}
            </nav>
          </div>
        )}
      </div>
    </header>
  );
};

export default Header;