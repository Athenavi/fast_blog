/**
 * 导航栏 - 浮动胶囊版
 * 设计（用户确认：参考 tasteskill.dev 的沉浸式风格）：
 * - 去除传统顶部导航条，改为两个独立浮动块：
 *   左：品牌 logo 胶囊
 *   右：精简胶囊按钮，点击展开多级菜单面板
 * - 菜单面板：导航树（支持多级 children 展开）+ 搜索 + 主题切换 + 通知 + 用户区
 * - 向下滚动隐藏、向上滚动立即显示
 * - 移动端保留底部导航
 */

'use client';

import React, {useEffect, useRef, useState} from 'react';
import {AnimatePresence, motion} from 'framer-motion';
import {
  Bell,
  BookOpen,
  ChevronDown,
  Command,
  FolderTree,
  Home,
  Image as ImageIcon,
  LogOut,
  Menu,
  Moon,
  PenSquare,
  Search,
  Settings,
  Sun,
  User,
  X
} from 'lucide-react';
import {useDarkMode} from '@/lib/dark-mode-manager';
import {getAccessTokenFromCookie, getLocalAuthState} from '@/lib/auth-utils';
import {MenuService, type MenuTreeItem} from '@/lib/api/menu-service';
import {SEARCH} from '@/lib/api/api-paths';
import {getConfig} from '@/lib/config';

const Navbar: React.FC = () => {
  const {theme, toggleTheme} = useDarkMode();
  const [menuOpen, setMenuOpen] = useState(false);
  const [expandedUrl, setExpandedUrl] = useState<string | null>(null);
  const [notifExpanded, setNotifExpanded] = useState(false);
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<unknown[]>([]);
  const [searchLoading, setSearchLoading] = useState(false);
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [userAvatar, setUserAvatar] = useState<string | null>(null);
  const [username, setUsername] = useState('');
  const [pathname, setPathname] = useState('/');
  const [scrolled, setScrolled] = useState(false);
  const [navHidden, setNavHidden] = useState(false);
  const [navItems, setNavItems] = useState<MenuTreeItem[]>([]);
  const searchInputRef = useRef<HTMLInputElement>(null);
  const searchTimeoutRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const panelRef = useRef<HTMLDivElement>(null);

  // 首页固定深色基底
  const isHome = pathname === '/';

  // 根据菜单项标题/URL 匹配图标
  const getIconForMenuItem = (title: string, url: string): React.ComponentType<any> => {
    const t = (title || '').toLowerCase();
    const u = (url || '').toLowerCase();
    if (t.includes('首页') || t.includes('home') || u === '/') return Home;
    if (t.includes('文章') || t.includes('blog') || t.includes('article') || u.includes('/article')) return BookOpen;
    if (t.includes('分类') || t.includes('categor') || u.includes('/categor')) return FolderTree;
    if (t.includes('关于') || t.includes('about') || u.includes('/about')) return User;
    if (t.includes('标签') || t.includes('tag') || u.includes('/tag')) return Search;
    if (t.includes('设置') || t.includes('setting') || u.includes('/setting')) return Settings;
    return BookOpen; // 默认图标
  };

  // 默认导航项（作为后备）
  const defaultNavItems: MenuTreeItem[] = [
    {id: 1, title: '首页', url: '/', target: '_self', order_index: 1, is_active: true, menu_id: 1},
    {id: 2, title: '文章', url: '/articles', target: '_self', order_index: 2, is_active: true, menu_id: 1},
    {id: 3, title: '分类', url: '/categories', target: '_self', order_index: 3, is_active: true, menu_id: 1},
    {id: 4, title: '关于', url: '/about', target: '_self', order_index: 4, is_active: true, menu_id: 1},
  ];

  useEffect(() => {
    setPathname(window.location.pathname);

    // 双重检测：cookie + localStorage
    const checkAuth = () => {
      const hasToken = !!getAccessTokenFromCookie() || getLocalAuthState();
      setIsLoggedIn(hasToken);

      if (hasToken) {
        const token = getAccessTokenFromCookie();
        if (token) {
          import('@/lib/config').then(({getConfig}) => {
            const {API_BASE_URL} = getConfig();
            return fetch(`${API_BASE_URL}/api/v2/users/me`, {
              headers: {Authorization: `Bearer ${token}`}
            })
              .then(r => r.json())
              .then(data => {
                if (data?.data) {
                  setUserAvatar(data.data.avatar ? `${API_BASE_URL}${data.data.avatar}` : null);
                  setUsername(data.data.username || '');
                } else {
                  setIsLoggedIn(false);
                }
              })
              .catch(() => {});
          });
        } else {
          setIsLoggedIn(true);
        }
      }
    };

    checkAuth();

    const onAuthChanged = (e: Event) => {
      const detail = (e as CustomEvent).detail;
      if (detail?.loggedIn !== undefined) {
        setIsLoggedIn(detail.loggedIn);
        if (!detail.loggedIn) {
          setUserAvatar(null);
          setUsername('');
        }
      }
    };

    const onStorage = (e: StorageEvent) => {
      if (e.key === 'fastblog_auth') {
        checkAuth();
      }
    };

    const onFocus = () => checkAuth();

    window.addEventListener('auth:changed', onAuthChanged);
    window.addEventListener('storage', onStorage);
    window.addEventListener('focus', onFocus);
    window.addEventListener('popstate', checkAuth);

    return () => {
      window.removeEventListener('auth:changed', onAuthChanged);
      window.removeEventListener('storage', onStorage);
      window.removeEventListener('focus', onFocus);
      window.removeEventListener('popstate', checkAuth);
    };
  }, []);

  // 从 API 动态获取导航菜单（保留多级树结构）
  useEffect(() => {
    MenuService.getMainMenu().then(response => {
      if (response.success && response.data && response.data.length > 0) {
        const dynamicItems = response.data
          .filter((item: MenuTreeItem) => item.is_active !== false)
          .sort((a: MenuTreeItem, b: MenuTreeItem) => (a.order_index || 0) - (b.order_index || 0));
        if (dynamicItems.length > 0) {
          setNavItems(dynamicItems);
          return;
        }
      }
      setNavItems(defaultNavItems);
    }).catch(() => {
      setNavItems(defaultNavItems);
    });
  }, []);

  // 滚动检测：毛玻璃 + 向下隐藏/向上显示
  useEffect(() => {
    let lastY = window.scrollY;
    const handleScroll = () => {
      const y = window.scrollY;
      setScrolled(y > 10);
      setNavHidden(y > 120 && y > lastY);
      lastY = y;
    };
    window.addEventListener('scroll', handleScroll, {passive: true});
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  // 快捷键：⌘K 搜索，Esc 关闭
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setIsSearchOpen(true);
      }
      if (e.key === 'Escape') {
        setIsSearchOpen(false);
        setMenuOpen(false);
      }
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, []);

  // 搜索输入框自动聚焦
  useEffect(() => {
    if (isSearchOpen) {
      setTimeout(() => searchInputRef.current?.focus(), 100);
    }
  }, [isSearchOpen]);

  // 点击外部关闭菜单
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      const target = e.target as HTMLElement;
      if (panelRef.current && !panelRef.current.contains(target)) {
        setMenuOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // 搜索防抖
  const handleSearch = (value: string) => {
    setSearchQuery(value);
    if (searchTimeoutRef.current) clearTimeout(searchTimeoutRef.current);
    if (!value.trim()) {
      setSearchResults([]);
      return;
    }
    setSearchLoading(true);
    searchTimeoutRef.current = setTimeout(async () => {
      try {
        const res = await fetch(`${getConfig().API_BASE_URL}${SEARCH.QUICK}?q=${encodeURIComponent(value)}&per_page=5`);
        const data = await res.json();
        setSearchResults(data?.data?.articles || data?.data || []);
      } catch {
        setSearchResults([]);
      } finally {
        setSearchLoading(false);
      }
    }, 300);
  };

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      window.location.href = `/search?q=${encodeURIComponent(searchQuery)}`;
    }
  };

  const userMenuItems = isLoggedIn ? [
    {name: '写文章', href: '/my/posts/create', icon: PenSquare},
    {name: '我的文章', href: '/my/posts', icon: BookOpen},
    {name: '媒体库', href: '/media', icon: ImageIcon},
    {name: '设置', href: '/settings', icon: Settings},
    {name: '个人资料', href: '/profile', icon: User},
  ] : [];

  const handleLogout = () => {
    document.cookie = 'access_token=; path=/; expires=Thu, 01 Jan 1970 00:00:01 GMT';
    document.cookie = 'refresh_token=; path=/; expires=Thu, 01 Jan 1970 00:00:01 GMT';
    localStorage.removeItem('fastblog_auth');
    window.dispatchEvent(new CustomEvent('auth:changed', {detail: {loggedIn: false}}));
    window.location.href = '/';
  };

  /* ─── 沉浸式配色（浮动块 + 面板） ─── */
  const floatCls = isHome
    ? 'bg-[#05070f]/60 border-white/10'
    : 'bg-white/70 dark:bg-gray-950/70 border-black/5 dark:border-white/10';
  const panelCls = isHome
    ? 'bg-[#0b0f1a]/95 border-white/10 text-slate-200'
    : 'bg-white/95 dark:bg-gray-950/95 border-black/5 dark:border-white/10 text-slate-700 dark:text-slate-200';
  const itemHover = isHome
    ? 'hover:bg-white/10 hover:text-white'
    : 'hover:bg-black/5 dark:hover:bg-white/10 dark:hover:text-white hover:text-slate-900';
  const iconColor = isHome ? 'text-slate-400' : 'text-slate-500 dark:text-slate-400';

  const isActive = (href: string) =>
    href === '/' ? pathname === '/' : pathname.startsWith(href);

  /* ─── 递归渲染多级菜单项 ─── */
  const renderMenuItems = (items: MenuTreeItem[], level = 0) =>
    items.map(item => {
      const href = item.url || '#';
      const Icon = getIconForMenuItem(item.title || '', href);
      const hasChildren = !!(item.children && item.children.length > 0);
      const expanded = expandedUrl === href;
      return (
        <div key={href + level}>
          <div className="relative">
            <a
              href={hasChildren ? undefined : href}
              onClick={(e) => {
                if (hasChildren) {
                  e.preventDefault();
                  setExpandedUrl(expanded ? null : href);
                } else {
                  setMenuOpen(false);
                }
              }}
              className={`flex items-center gap-3 px-4 py-2.5 text-sm transition-colors duration-150 ${itemHover} ${
                isActive(href) ? (isHome ? 'text-blue-400' : 'text-blue-600 dark:text-blue-400') : ''
              } ${level > 0 ? 'pl-9' : ''}`}
            >
              {level === 0 && <Icon className={`w-4 h-4 ${iconColor}`}/>}
              <span className="flex-1 min-w-0 truncate">{item.title}</span>
              {hasChildren && (
                <ChevronDown
                  className={`w-3.5 h-3.5 ${iconColor} transition-transform duration-200 ${expanded ? 'rotate-180' : ''}`}/>
              )}
            </a>
          </div>
          {hasChildren && expanded && (
            <div className="py-0.5">{renderMenuItems(item.children!, level + 1)}</div>
          )}
        </div>
      );
    });

  return (
    <>
      {/* ─── 左浮动：品牌 logo 胶囊 ─── */}
      <motion.div
        animate={{y: navHidden ? -90 : 0}}
        transition={{duration: 0.35, ease: [0.22, 1, 0.36, 1]}}
        className="fixed top-4 left-4 z-[9999]"
      >
        <a href="/"
           className={`flex items-center gap-2.5 pl-2 pr-4 py-2 rounded-full border backdrop-blur-xl transition-colors duration-300 ${floatCls}`}>
          <div className="w-8 h-8 gradient-primary rounded-full flex items-center justify-center shadow-sm">
            <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                    d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"/>
            </svg>
          </div>
          <span
            className={`text-sm font-semibold tracking-tight ${isHome ? 'text-slate-100' : 'text-slate-800 dark:text-slate-100'}`}>FastBlog</span>
        </a>
      </motion.div>

      {/* ─── 右浮动：胶囊按钮 + 多级菜单面板 ─── */}
      <motion.div
        animate={{y: navHidden ? -90 : 0}}
        transition={{duration: 0.35, ease: [0.22, 1, 0.36, 1]}}
        className="fixed top-4 right-4 z-[9999]"
      >
        <div ref={panelRef} className="relative">
          <button
            onClick={() => {
              setMenuOpen(!menuOpen);
              setNotifExpanded(false);
            }}
            aria-label="打开菜单"
            className={`w-11 h-11 rounded-full border backdrop-blur-xl flex items-center justify-center transition-colors duration-300 ${floatCls} ${
              menuOpen ? (isHome ? 'bg-[#0b0f1a]/95' : 'bg-white/95 dark:bg-gray-950/95') : ''
            }`}
          >
            {isLoggedIn && userAvatar ? (
              <img src={userAvatar} alt="" className="w-7 h-7 rounded-full object-cover"/>
            ) : (
              <Menu className={`w-5 h-5 ${isHome ? 'text-slate-100' : 'text-slate-700 dark:text-slate-100'}`}/>
            )}
          </button>

          <AnimatePresence>
            {menuOpen && (
              <motion.div
                initial={{opacity: 0, y: -8, scale: 0.96}}
                animate={{opacity: 1, y: 0, scale: 1}}
                exit={{opacity: 0, y: -8, scale: 0.96}}
                transition={{duration: 0.18, ease: [0.22, 1, 0.36, 1]}}
                className={`absolute right-0 top-full mt-2 w-64 max-w-[calc(100vw-2rem)] rounded-2xl border shadow-2xl shadow-black/20 backdrop-blur-2xl overflow-hidden ${panelCls}`}
              >
                <div className="max-h-[70vh] overflow-y-auto py-2">
                  {/* 搜索入口 */}
                  <button
                    onClick={() => {
                      setIsSearchOpen(true);
                      setMenuOpen(false);
                    }}
                    className={`flex w-full items-center gap-3 px-4 py-2.5 text-sm transition-colors duration-150 ${itemHover}`}
                  >
                    <Search className={`w-4 h-4 ${iconColor}`}/>
                    <span className="flex-1 text-left">搜索</span>
                    <kbd
                      className={`px-1.5 py-0.5 rounded text-[10px] font-mono border ${isHome ? 'text-slate-500 border-white/15' : 'text-slate-500 dark:text-slate-400 border-black/10 dark:border-white/15'}`}>
                      <Command className="w-3 h-3 inline"/>K
                    </kbd>
                  </button>

                  <div
                    className={`my-1.5 mx-4 border-t ${isHome ? 'border-white/10' : 'border-black/5 dark:border-white/10'}`}/>

                  {/* 多级导航 */}
                  <nav>{renderMenuItems(navItems)}</nav>

                  <div
                    className={`my-1.5 mx-4 border-t ${isHome ? 'border-white/10' : 'border-black/5 dark:border-white/10'}`}/>

                  {/* 主题切换 */}
                  <button
                    onClick={toggleTheme}
                    className={`flex w-full items-center gap-3 px-4 py-2.5 text-sm transition-colors duration-150 ${itemHover}`}
                  >
                    {theme === 'dark'
                      ? <Sun className={`w-4 h-4 ${iconColor}`}/>
                      : <Moon className={`w-4 h-4 ${iconColor}`}/>}
                    <span className="flex-1 text-left">{theme === 'dark' ? '切换到亮色' : '切换到暗色'}</span>
                  </button>

                  {/* 通知 */}
                  <div>
                    <button
                      onClick={() => setNotifExpanded(!notifExpanded)}
                      className={`flex w-full items-center gap-3 px-4 py-2.5 text-sm transition-colors duration-150 ${itemHover}`}
                    >
                      <Bell className={`w-4 h-4 ${iconColor}`}/>
                      <span className="flex-1 text-left">通知</span>
                      {isLoggedIn && <span className="w-1.5 h-1.5 rounded-full bg-red-500"/>}
                    </button>
                    <AnimatePresence>
                      {notifExpanded && (
                        <motion.div
                          initial={{height: 0, opacity: 0}}
                          animate={{height: 'auto', opacity: 1}}
                          exit={{height: 0, opacity: 0}}
                          transition={{duration: 0.2}}
                          className="overflow-hidden"
                        >
                          <div
                            className={`py-6 text-center text-xs ${isHome ? 'text-slate-500' : 'text-slate-500 dark:text-slate-400'}`}>
                            <Bell className={`w-6 h-6 mx-auto mb-2 opacity-30 ${iconColor}`}/>
                            暂无新通知
                          </div>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </div>

                  <div
                    className={`my-1.5 mx-4 border-t ${isHome ? 'border-white/10' : 'border-black/5 dark:border-white/10'}`}/>

                  {/* 用户区 */}
                  {isLoggedIn ? (
                    <>
                      <div className={`px-4 py-2.5`}>
                        <p className="text-sm font-semibold truncate">{username || '用户'}</p>
                        <p
                          className={`text-xs mt-0.5 ${isHome ? 'text-slate-500' : 'text-slate-500 dark:text-slate-400'}`}>欢迎回来</p>
                      </div>
                      {userMenuItems.map((item) => {
                        const Icon = item.icon;
                        return (
                          <a
                            key={item.href}
                            href={item.href}
                            onClick={() => setMenuOpen(false)}
                            className={`flex items-center gap-3 px-4 py-2.5 text-sm transition-colors duration-150 ${itemHover}`}
                          >
                            <Icon className={`w-4 h-4 ${iconColor}`}/>
                            <span>{item.name}</span>
                          </a>
                        );
                      })}
                      <a
                        href="/admin"
                        onClick={() => setMenuOpen(false)}
                        className={`flex items-center gap-3 px-4 py-2.5 text-sm transition-colors duration-150 ${itemHover}`}
                      >
                        <Settings className={`w-4 h-4 ${iconColor}`}/>
                        <span>管理后台</span>
                      </a>
                      <div
                        className={`my-1.5 mx-4 border-t ${isHome ? 'border-white/10' : 'border-black/5 dark:border-white/10'}`}/>
                      <button
                        onClick={handleLogout}
                        className="flex w-full items-center gap-3 px-4 py-2.5 text-sm text-red-500 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-500/10 transition-colors"
                      >
                        <LogOut className="w-4 h-4"/>
                        <span>退出登录</span>
                      </button>
                    </>
                  ) : (
                    <div className="px-4 py-2.5">
                      <a
                        href="/login"
                        className={`flex w-full items-center justify-center gap-2 px-4 py-2.5 rounded-lg border text-sm font-medium transition-colors duration-200 ${
                          isHome
                            ? 'border-white/25 text-slate-100 hover:bg-white/10'
                            : 'border-black/15 dark:border-white/20 hover:bg-black/5 dark:hover:bg-white/10'
                        }`}
                      >
                        登录
                      </a>
                    </div>
                  )}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </motion.div>

      {/* ─── 移动端底部导航 ─── */}
      <nav
        className={`fixed bottom-0 left-0 right-0 z-[9998] md:hidden backdrop-blur-xl border-t ${
          isHome
            ? 'home-nav bg-[#05070f]/85 border-white/10'
            : 'bg-white/80 dark:bg-gray-950/80 border-black/5 dark:border-white/10'
        }`}
        style={{paddingBottom: 'env(safe-area-inset-bottom, 0px)'}}>
        <div className="flex items-center justify-around h-14">
          {navItems.map((item) => {
            const Icon = getIconForMenuItem(item.title || '', item.url || '');
            const active = isActive(item.url || '');
            return (
              <a
                key={item.url}
                href={item.url}
                className={`flex flex-col items-center gap-0.5 px-3 py-1 rounded-lg transition-colors min-w-[56px] ${
                  active
                    ? isHome ? 'text-blue-400' : 'text-blue-600 dark:text-blue-400'
                    : 'theme-text-secondary'
                }`}
              >
                <Icon className="w-5 h-5"/>
                <span className="text-[10px] font-medium">{item.title}</span>
                {active && (
                  <motion.div
                    layoutId="mobileActiveNav"
                    className={`w-4 h-0.5 rounded-full mt-0.5 ${isHome ? 'bg-blue-400' : 'bg-blue-600 dark:bg-blue-400'}`}
                  />
                )}
              </a>
            );
          })}
          {isLoggedIn ? (
            <a
              href="/settings"
              className={`flex flex-col items-center gap-0.5 px-3 py-1 rounded-lg transition-colors min-w-[56px] ${
                pathname.startsWith('/settings') || pathname.startsWith('/profile') || pathname.startsWith('/my')
                  ? isHome ? 'text-blue-400' : 'text-blue-600 dark:text-blue-400'
                  : 'theme-text-secondary'
              }`}
            >
              {userAvatar ? (
                <img src={userAvatar} alt="" className="w-5 h-5 rounded-full object-cover"/>
              ) : (
                <User className="w-5 h-5"/>
              )}
              <span className="text-[10px] font-medium">我的</span>
            </a>
          ) : (
            <a href="/login"
               className="flex flex-col items-center gap-0.5 px-3 py-1 rounded-lg theme-text-secondary min-w-[56px]">
              <User className="w-5 h-5"/>
              <span className="text-[10px] font-medium">登录</span>
            </a>
          )}
        </div>
      </nav>

      {/* ─── 搜索模态框 ─── */}
      <AnimatePresence>
        {isSearchOpen && (
          <motion.div
            initial={{opacity: 0}}
            animate={{opacity: 1}}
            exit={{opacity: 0}}
            className="fixed inset-0 z-[99999] flex items-start justify-center pt-[8vh] sm:pt-[15vh]"
            onClick={(e) => {
              if (e.target === e.currentTarget) setIsSearchOpen(false);
            }}
          >
            <div className="absolute inset-0 bg-black/50 backdrop-blur-sm"/>

            <motion.div
              initial={{opacity: 0, y: -20, scale: 0.96}}
              animate={{opacity: 1, y: 0, scale: 1}}
              exit={{opacity: 0, y: -20, scale: 0.96}}
              transition={{duration: 0.2}}
              className="relative w-full max-w-2xl mx-3 sm:mx-4 theme-bg rounded-xl sm:rounded-2xl shadow-2xl border theme-border overflow-hidden max-h-[80vh] sm:max-h-none flex flex-col"
            >
              <form onSubmit={handleSearchSubmit}
                    className="flex items-center gap-3 px-5 py-4 border-b theme-border">
                <Search className="w-5 h-5 theme-text-secondary flex-shrink-0"/>
                <input
                  ref={searchInputRef}
                  type="text"
                  value={searchQuery}
                  onChange={(e) => handleSearch(e.target.value)}
                  placeholder="搜索文章、分类、标签..."
                  className="flex-1 bg-transparent theme-text placeholder-gray-400 outline-none text-base min-h-[44px]"
                />
                <kbd
                  className="hidden sm:inline px-2 py-0.5 theme-bg-muted border theme-border rounded text-xs theme-text-secondary">ESC</kbd>
                <button type="button" onClick={() => setIsSearchOpen(false)}
                        className="sm:hidden p-2 theme-text-secondary hover:text-gray-600 dark:hover:text-gray-300">
                  <X className="w-5 h-5"/>
                </button>
              </form>

              <div className="max-h-[50vh] sm:max-h-[400px] overflow-y-auto flex-1">
                {searchLoading ? (
                  <div className="py-12 text-center">
                    <div
                      className="animate-spin w-6 h-6 border-2 border-blue-600 border-t-transparent rounded-full mx-auto"/>
                    <p className="text-sm theme-text-secondary mt-3">搜索中...</p>
                  </div>
                ) : searchResults.length > 0 ? (
                  <div className="py-2">
                    {searchResults.map((item: any, i: number) => (
                      <a
                        key={i}
                        href={`/view?slug=${item.slug || item.id}`}
                        onClick={() => setIsSearchOpen(false)}
                        className="flex items-start gap-3 px-5 py-3 theme-hover-bg-muted transition-colors"
                      >
                        <div
                          className="w-8 h-8 rounded-lg bg-blue-50 dark:bg-blue-900/20 flex items-center justify-center flex-shrink-0 mt-0.5">
                          <BookOpen className="w-4 h-4 text-blue-600 dark:text-blue-400"/>
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium theme-text truncate">{item.title}</p>
                          <p
                            className="text-xs theme-text-secondary mt-0.5 line-clamp-1">{item.excerpt || item.summary || ''}</p>
                        </div>
                      </a>
                    ))}
                    <a
                      href={`/search?q=${encodeURIComponent(searchQuery)}`}
                      onClick={() => setIsSearchOpen(false)}
                      className="flex items-center justify-center py-3 text-sm theme-text-primary theme-hover-bg-muted transition-colors border-t theme-border"
                    >
                      查看所有搜索结果 →
                    </a>
                  </div>
                ) : searchQuery ? (
                  <div className="py-12 text-center theme-text-secondary text-sm">
                    <Search className="w-8 h-8 mx-auto mb-2 opacity-30"/>
                    未找到相关内容
                  </div>
                ) : (
                  <div className="py-8 px-5">
                    <p className="text-xs font-semibold theme-text-secondary uppercase tracking-wider mb-3">快捷搜索</p>
                    <div className="flex flex-wrap gap-2">
                      {['技术', '前端', '后端', 'AI', '设计'].map(tag => (
                        <button
                          key={tag}
                          onClick={() => handleSearch(tag)}
                          className="px-3 py-1.5 text-sm theme-bg-muted text-gray-600 dark:theme-text-secondary rounded-lg theme-hover-bg-muted transition-colors"
                        >
                          {tag}
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
};

export default Navbar;
