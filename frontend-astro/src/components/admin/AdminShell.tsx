'use client';

import React, {useState} from 'react';
import {BarChart3, FileText, FolderTree, Image, Users, Shield, Settings, ChevronLeft, Menu, LogOut, MessageSquare, Puzzle, Database, TrendingUp, ScrollText, Server, AlertTriangle} from 'lucide-react';

const nav = [
  {label: '仪表盘', href: '/admin', icon: BarChart3},
  {label: '文章管理', href: '/admin/articles', icon: FileText},
  {label: '分类管理', href: '/admin/categories', icon: FolderTree},
  {label: '媒体库', href: '/admin/media', icon: Image},
  {label: '评论管理', href: '/admin/comments', icon: MessageSquare},
  {label: '用户管理', href: '/admin/users', icon: Users},
  {label: '角色权限', href: '/admin/roles', icon: Shield},
  {label: '插件管理', href: '/admin/plugins', icon: Puzzle},
  {label: '备份管理', href: '/admin/backup', icon: Database},
  {label: '敏感词', href: '/admin/sensitive-words', icon: AlertTriangle},
  {label: '数据分析', href: '/admin/analytics', icon: TrendingUp},
  {label: '审计日志', href: '/admin/audit-logs', icon: ScrollText},
  {label: '系统信息', href: '/admin/system', icon: Server},
  {label: '系统设置', href: '/admin/settings', icon: Settings},
];

export const AdminShell: React.FC<{title: string; children: React.ReactNode; actions?: React.ReactNode}> = ({title, children, actions}) => {
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  const isActive = (href: string) => typeof window !== 'undefined' && window.location.pathname === href;

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950 flex">
      {/* Desktop sidebar */}
      <aside className={`hidden lg:flex flex-col border-r border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 transition-all ${collapsed ? 'w-16' : 'w-56'} flex-shrink-0`}>
        <div className="flex items-center justify-between h-14 px-4 border-b border-gray-200 dark:border-gray-800">
          {!collapsed && <span className="font-bold text-gray-900 dark:text-white">FastBlog</span>}
          <button onClick={() => setCollapsed(!collapsed)} className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-400"><ChevronLeft className={`w-4 h-4 transition-transform ${collapsed ? 'rotate-180' : ''}`}/></button>
        </div>
        <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
          {nav.map(item => {
            const Icon = item.icon;
            const active = isActive(item.href);
            return (
              <a key={item.href} href={item.href}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-colors ${active ? 'bg-blue-50 text-blue-700 dark:bg-blue-900/20 dark:text-blue-400' : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800'}`}
                title={collapsed ? item.label : undefined}>
                <Icon className="w-5 h-5 flex-shrink-0"/>{!collapsed && <span>{item.label}</span>}
              </a>
            );
          })}
        </nav>
        <div className="p-3 border-t border-gray-200 dark:border-gray-800">
          <a href="/" className="flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800">
            <LogOut className="w-5 h-5"/>{!collapsed && <span>返回前台</span>}
          </a>
        </div>
      </aside>

      {/* Mobile sidebar overlay */}
      {mobileOpen && <div className="fixed inset-0 z-40 bg-black/50 lg:hidden" onClick={() => setMobileOpen(false)}/>}
      <aside className={`fixed inset-y-0 left-0 z-50 w-64 bg-white dark:bg-gray-900 border-r border-gray-200 dark:border-gray-800 transform transition-transform lg:hidden ${mobileOpen ? 'translate-x-0' : '-translate-x-full'}`}>
        <div className="flex items-center justify-between h-14 px-4 border-b"><span className="font-bold">FastBlog</span><button onClick={() => setMobileOpen(false)} className="p-1.5 rounded-lg hover:bg-gray-100"><Menu className="w-5 h-5"/></button></div>
        <nav className="p-3 space-y-1">
          {nav.map(item => {
            const Icon = item.icon;
            return (
              <a key={item.href} href={item.href} onClick={() => setMobileOpen(false)}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium ${isActive(item.href) ? 'bg-blue-50 text-blue-700' : 'text-gray-600 hover:bg-gray-100'}`}>
                <Icon className="w-5 h-5"/><span>{item.label}</span>
              </a>
            );
          })}
        </nav>
      </aside>

      {/* Main content */}
      <div className="flex-1 flex flex-col min-w-0">
        <header className="h-14 flex items-center justify-between px-4 lg:px-6 border-b border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 flex-shrink-0">
          <div className="flex items-center gap-3">
            <button onClick={() => setMobileOpen(true)} className="p-1.5 -ml-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 lg:hidden"><Menu className="w-5 h-5"/></button>
            <h1 className="text-lg font-bold text-gray-900 dark:text-white truncate">{title}</h1>
          </div>
          <div className="flex items-center gap-2">{actions}</div>
        </header>
        <main className="flex-1 overflow-y-auto p-4 lg:p-6">{children}</main>
      </div>
    </div>
  );
};
