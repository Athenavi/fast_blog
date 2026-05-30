'use client';

import React, {useState} from 'react';
import {
  AlertTriangle,
  ArrowRightLeft,
  Award,
  BarChart3,
  Bell,
  Brain,
  CheckSquare,
  ChevronLeft,
  Coins,
  CreditCard,
  Crown,
  Database,
  Diamond,
  Eye,
  FileEdit,
  FileText,
  FolderTree,
  GitBranch,
  Globe,
  Handshake,
  Image,
  Lock,
  LogOut,
  Medal,
  Menu,
  MessageSquare,
  Newspaper,
  Package,
  PenLine,
  PieChart,
  Puzzle,
  Radio,
  ScrollText,
  Search,
  Server,
  Settings,
  Shield,
  Star,
  TrendingUp,
  Users,
  X,
  Zap
} from 'lucide-react';
import {ErrorBoundary} from '@/components/ui/ErrorBoundary';

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
  {label: 'VIP 管理', href: '/admin/vip', icon: Crown},
  {label: '广告管理', href: '/admin/ads', icon: Newspaper},
  {label: '模板管理', href: '/admin/templates', icon: GitBranch},
  {label: '通知管理', href: '/admin/notifications', icon: Bell},
  {label: '协作管理', href: '/admin/collaboration', icon: Handshake},
  {label: '集成管理', href: '/admin/integrations', icon: Globe},
  {label: 'AI 工具', href: '/admin/ai', icon: Brain},
  {label: 'CDN 管理', href: '/admin/cdn', icon: Radio},
  {label: '无障碍', href: '/admin/accessibility', icon: Eye},
  {label: 'GDPR 合规', href: '/admin/gdpr', icon: Shield},
  {sep: '高级管理'},
  {label: '支付管理', href: '/admin/payment', icon: CreditCard},
  {label: '迁移管理', href: '/admin/migration', icon: ArrowRightLeft},
  {label: '内容扩展', href: '/admin/content-ext', icon: FileEdit},
  {label: '用户安全', href: '/admin/user-security', icon: Lock},
  {label: '搜索与媒体', href: '/admin/search-media', icon: Zap},
  {label: '电商管理', href: '/admin/ecommerce', icon: Package},
  {label: '收益分成', href: '/admin/revenue', icon: PieChart},
  {label: '多站点', href: '/admin/multisite', icon: Globe},
  {label: '群聊管理', href: '/admin/chat-groups', icon: MessageSquare},
  {label: 'SEO 管理', href: '/admin/seo', icon: Search},
  {label: '内容审批', href: '/admin/approval', icon: CheckSquare},
  {sep:'扩展功能'},
  {label: '徽章系统', href: '/admin/ext/badges', icon: Award},
  {label: '积分系统', href: '/admin/ext/points', icon: Coins},
  {label: '打赏系统', href: '/admin/ext/tipping', icon: Diamond},
  {label: 'AI 写作', href: '/admin/ext/ai-writing', icon: PenLine},
  {label: '专家认证', href: '/admin/ext/certification', icon: Medal},
  {label: 'NFT 管理', href: '/admin/ext/nft', icon: Diamond},
  {label: '推荐系统', href: '/admin/ext/recommendations', icon: Star},
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
          {nav.map((item,i) => {
            if ('sep' in item) return <div key={`sep-${i}`} className={`pt-3 pb-1 text-xs font-semibold text-gray-400 uppercase tracking-wider ${collapsed ? 'text-center text-[10px]' : 'px-3'}`}>{collapsed ? '··' : item.sep}</div>;
            const Icon = item.icon!;
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
      {mobileOpen && <div className="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm lg:hidden"
                          onClick={() => setMobileOpen(false)}/>}
      <aside
          className={`fixed inset-y-0 left-0 z-50 w-72 bg-white dark:bg-gray-900 border-r border-gray-200 dark:border-gray-800 transform transition-transform lg:hidden safe-top ${mobileOpen ? 'translate-x-0' : '-translate-x-full'}`}>
        <div className="flex items-center justify-between h-14 px-4 border-b border-gray-200 dark:border-gray-800">
          <span className="font-bold text-gray-900 dark:text-white">FastBlog</span>
          <button onClick={() => setMobileOpen(false)}
                  className="p-2 min-w-[44px] min-h-[44px] flex items-center justify-center rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800">
            <X className="w-5 h-5 text-gray-500 dark:text-gray-400"/></button>
        </div>
        <nav className="p-3 space-y-1 overflow-y-auto"
             style={{maxHeight: 'calc(100vh - 3.5rem - env(safe-area-inset-bottom, 0px))'}}>
          {nav.map((item,i) => {
            if ('sep' in item) return <div key={`sep-${i}`} className="pt-3 pb-1 px-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">{item.sep}</div>;
            const Icon = item.icon!;
            return (
              <a key={item.href} href={item.href} onClick={() => setMobileOpen(false)}
                 className={`flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium min-h-[44px] ${isActive(item.href) ? 'bg-blue-50 text-blue-700 dark:bg-blue-900/20 dark:text-blue-400' : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800'}`}>
                <Icon className="w-5 h-5"/><span>{item.label}</span>
              </a>
            );
          })}
        </nav>
      </aside>

      {/* Main content */}
      <div className="flex-1 flex flex-col min-w-0">
        <header
            className="h-14 flex items-center justify-between px-4 lg:px-6 border-b border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 flex-shrink-0 safe-top">
          <div className="flex items-center gap-3">
            <button onClick={() => setMobileOpen(true)}
                    className="p-2 min-w-[44px] min-h-[44px] -ml-1 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 lg:hidden flex items-center justify-center">
              <Menu className="w-5 h-5"/></button>
            <h1 className="text-base sm:text-lg font-bold text-gray-900 dark:text-white truncate">{title}</h1>
          </div>
          <div className="flex items-center gap-2">{actions}</div>
        </header>
        <main className="flex-1 overflow-y-auto p-4 lg:p-6"><ErrorBoundary>{children}</ErrorBoundary></main>
      </div>
    </div>
  );
};
