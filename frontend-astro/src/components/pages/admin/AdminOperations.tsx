'use client';

import React from 'react';
import {AdminShell} from '@/components/admin/AdminShell';
import {Bell, Search, Newspaper, Globe, TrendingUp, Shield, ChevronRight} from 'lucide-react';

const LINKS = [
  {href: '/admin/notifications', label: '通知管理', icon: Bell, desc: '系统通知、邮件推送、Webhook', color: 'bg-blue-500'},
  {href: '/admin/seo', label: 'SEO 管理', icon: Search, desc: 'SEO 优化、站点地图、结构化数据', color: 'bg-green-500'},
  {href: '/admin/ads', label: '广告管理', icon: Newspaper, desc: '广告位管理、投放策略、统计', color: 'bg-orange-500'},
  {href: '/admin/multisite', label: '多站点管理', icon: Globe, desc: '多站点配置、域名绑定、站点切换', color: 'bg-purple-500'},
  {href: '/admin/analytics', label: '数据分析', icon: TrendingUp, desc: '访问统计、趋势分析、用户行为', color: 'bg-cyan-500'},
  {href: '/admin/gdpr', label: 'GDPR 合规', icon: Shield, desc: '隐私政策、数据导出、用户权利', color: 'bg-rose-500'},
];

export default function AdminOperations() {
  return (
    <AdminShell title="运营管理">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {LINKS.map(link => (
          <a key={link.href} href={link.href}
            className="group bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 p-5 hover:shadow-md hover:border-gray-300 dark:hover:border-gray-600 transition-all">
            <div className="flex items-start gap-4">
              <div className={`w-12 h-12 rounded-xl ${link.color} flex items-center justify-center flex-shrink-0`}>
                <link.icon className="w-6 h-6 text-white"/>
              </div>
              <div className="flex-1 min-w-0">
                <h3 className="font-semibold text-gray-900 dark:text-white text-sm flex items-center gap-1">
                  {link.label}
                  <ChevronRight className="w-4 h-4 text-gray-400 group-hover:translate-x-0.5 transition-transform"/>
                </h3>
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">{link.desc}</p>
              </div>
            </div>
          </a>
        ))}
      </div>
    </AdminShell>
  );
}
