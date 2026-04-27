'use client';

import React, {useState} from 'react';
import Link from 'next/link';
import {usePathname} from 'next/navigation';
import {useAuth} from '@/hooks/useAuth';
import {useMenu} from '@/hooks/useMenu';
import UserDropdown from './UserDropdown';
import LanguageSwitcher from './LanguageSwitcher';
import {MenuTreeItem} from '@/lib/api/menu-service';
import {ChevronDown, Menu as MenuIcon, X} from 'lucide-react';

const Header = () => {
  const { user, loading, logout } = useAuth();
  const pathname = usePathname();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
    const [activeDropdown, setActiveDropdown] = useState<number | null>(null);

    // 使用自定义 Hook 获取菜单数据
    const {menuItems, isLoading: isMenuLoading} = useMenu();

  // 检查当前路径是否匹配菜单项
  const isActiveLink = (url: string) => {
    if (url === '/') {
      return pathname === '/';
    }
    return pathname.startsWith(url.replace(/\/$/, ''));
  };

    // 渲染菜单项及其子菜单（桌面端）
  const renderMenuItems = (items: MenuTreeItem[], depth = 0) => {
    if (!items || !Array.isArray(items)) {
      return null;
    }

    return items.map((item) => {
      const isActive = isActiveLink(item.url);
      const hasChildren = item.children && item.children.length > 0;

      return (
          <div key={item.id} className="relative group">
          {hasChildren ? (
              <div
                  onMouseEnter={() => setActiveDropdown(item.id)}
                  onMouseLeave={() => setActiveDropdown(null)}
              >
              <button
                  className={`flex items-center space-x-1 px-3 py-2 rounded-md text-sm font-medium transition-all duration-200 ${
                  isActive
                    ? 'text-blue-600 bg-blue-50 dark:bg-blue-900/30 dark:text-blue-400'
                      : 'text-gray-700 hover:text-blue-600 hover:bg-gray-50 dark:text-gray-300 dark:hover:text-blue-400 dark:hover:bg-gray-700'
                }`}
              >
                  <span>{item.title}</span>
                  <ChevronDown
                      className={`w-4 h-4 transition-transform duration-200 ${activeDropdown === item.id ? 'rotate-180' : ''}`}/>
              </button>

                  {/* 下拉菜单 - 带动画 */}
                  <div
                      className={`absolute left-0 mt-2 w-48 bg-white dark:bg-gray-800 rounded-md shadow-lg border border-gray-200 dark:border-gray-700 z-50 transition-all duration-200 origin-top ${
                          activeDropdown === item.id
                              ? 'opacity-100 visible scale-100 translate-y-0'
                              : 'opacity-0 invisible scale-95 -translate-y-2'
                      }`}
                  >
                      <div className="py-1">
                  {item.children && renderMenuItems(item.children, depth + 1)}
                </div>
              </div>
            </div>
          ) : (
            <Link
              href={item.url as any}
              target={item.target === '_blank' ? '_blank' : undefined}
              rel={item.target === '_blank' ? 'noopener noreferrer' : undefined}
              className={`block px-3 py-2 rounded-md text-sm font-medium transition-all duration-200 ${
                  isActive
                      ? 'text-blue-600 bg-blue-50 dark:bg-blue-900/30 dark:text-blue-400'
                      : 'text-gray-700 hover:text-blue-600 hover:bg-gray-50 dark:text-gray-300 dark:hover:text-blue-400 dark:hover:bg-gray-700'
              }`}
            >
                {item.title}
            </Link>
          )}
          </div>
      );
    });
  };

    // 渲染移动端菜单项
    const renderMobileMenuItems = (items: MenuTreeItem[], depth = 0) => {
        if (!items || !Array.isArray(items)) {
            return null;
        }

        return items.map((item) => {
            const isActive = isActiveLink(item.url);
            const hasChildren = item.children && item.children.length > 0;
            const [isExpanded, setIsExpanded] = useState(false);

            return (
                <div key={item.id} style={{paddingLeft: `${depth * 16}px`}}>
                    {hasChildren ? (
                        <div>
                            <button
                                onClick={() => setIsExpanded(!isExpanded)}
                                className={`w-full flex items-center justify-between px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                                    isActive
                                        ? 'text-blue-600 bg-blue-50 dark:bg-blue-900/30 dark:text-blue-400'
                                        : 'text-gray-700 hover:bg-gray-50 dark:text-gray-300 dark:hover:bg-gray-700'
                                }`}
                            >
                                <span>{item.title}</span>
                                <ChevronDown
                                    className={`w-4 h-4 transition-transform duration-200 ${isExpanded ? 'rotate-180' : ''}`}/>
                            </button>

                            {/* 子菜单 - 展开/折叠 */}
                            {isExpanded && item.children && (
                                <div className="mt-1 ml-4 border-l-2 border-gray-200 dark:border-gray-700 pl-2">
                                    {renderMobileMenuItems(item.children, depth + 1)}
                                </div>
                            )}
                        </div>
                    ) : (
                        <Link
                            href={item.url as any}
                            target={item.target === '_blank' ? '_blank' : undefined}
                            rel={item.target === '_blank' ? 'noopener noreferrer' : undefined}
                            onClick={() => setMobileMenuOpen(false)}
              className={`block px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                isActive
                  ? 'text-blue-600 bg-blue-50 dark:bg-blue-900/30 dark:text-blue-400'
                    : 'text-gray-700 hover:bg-gray-50 dark:text-gray-300 dark:hover:bg-gray-700'
              }`}
            >
                            {item.title}
            </Link>
          )}
        </div>
      );
    });
  };

  return (
      <header className="bg-white dark:bg-gray-800 shadow-md sticky top-0 z-40">
      <div className="container mx-auto px-4 py-4">
          <div className="flex justify-between items-center">
              <div className="flex items-center">
                  <Link href="/" className="text-xl font-bold text-blue-600 dark:text-blue-400">
              FastBlog
            </Link>
          </div>

          {/* 桌面端导航 */}
              <nav className="hidden md:flex items-center space-x-1">
            {isMenuLoading ? (
                <div className="px-4 py-2 text-sm text-gray-500">加载中...</div>
            ) : (
                <div className="flex items-center space-x-1">
                {renderMenuItems(menuItems)}
              </div>
            )}
          </nav>

              <div className="flex items-center space-x-4">
                  {/* 语言切换器 */}
                  <LanguageSwitcher/>

            {/* 移动端菜单按钮 */}
            <button
                className="md:hidden text-gray-700 dark:text-gray-300 focus:outline-none"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              aria-label="切换菜单"
            >
              {mobileMenuOpen ? <X className="w-6 h-6" /> : <MenuIcon className="w-6 h-6" />}
            </button>

            {loading ? (
                <div className="hidden md:flex space-x-4">
                    <div className="px-4 py-2 text-sm text-gray-500 rounded-md">加载中...</div>
              </div>
            ) : user ? (
                <div className="hidden md:flex items-center space-x-4">
                <div className="flex-shrink-0">
                  <UserDropdown user={user} />
                </div>
              </div>
            ) : (
                <div className="hidden md:flex items-center space-x-4">
                <Link
                  href="/login"
                  className="px-4 py-2 text-sm text-blue-600 hover:bg-blue-50 rounded-md dark:text-blue-400 dark:hover:bg-gray-700"
                >
                  登录
                </Link>
                <Link
                  href="/register"
                  className="px-4 py-2 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700 dark:bg-blue-700 dark:hover:bg-blue-800"
                >
                  注册
                </Link>
              </div>
            )}
          </div>
        </div>

          {/* 移动端导航菜单 - 带动画 */}
          <div
              className={`md:hidden overflow-hidden transition-all duration-300 ease-in-out ${
                  mobileMenuOpen ? 'max-h-screen opacity-100' : 'max-h-0 opacity-0'
              }`}
          >
              {mobileMenuOpen && (
                  <div className="py-4 border-t border-gray-200 dark:border-gray-700">
                      <nav className="flex flex-col space-y-2">
                          {isMenuLoading ? (
                  <div className="px-4 py-2 text-sm text-gray-500">加载中...</div>
                          ) : (
                              <>
                                  <div className="space-y-1">
                                      {renderMobileMenuItems(menuItems)}
                                  </div>

                                  {loading ? (
                      <div className="px-4 py-2 text-sm text-gray-500">加载中...</div>
                                  ) : user ? (
                      <div className="pt-4 border-t border-gray-200 dark:border-gray-700">
                          <div>
                              <UserDropdown user={user}/>
                          </div>
                      </div>
                                  ) : (
                      <div className="flex flex-col space-y-3 pt-4 border-t border-gray-200 dark:border-gray-700">
                          <Link
                              href="/login"
                              className="px-4 py-2 text-sm text-blue-600 hover:bg-blue-50 rounded-md dark:text-blue-400 dark:hover:bg-gray-700 text-center"
                              onClick={() => setMobileMenuOpen(false)}
                          >
                              登录
                          </Link>
                          <Link
                              href="/register"
                              className="px-4 py-2 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700 dark:bg-blue-700 dark:hover:bg-blue-800 text-center"
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
      </div>
    </header>
  );
};

export default Header;