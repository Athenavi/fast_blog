'use client';

import React from 'react';
import {AdminShell} from '@/components/admin/AdminShell';
import {MessageSquare, Globe, ChevronRight} from 'lucide-react';

const LINKS = [
  {href: '/admin/chat-groups', label: '群聊管理', icon: MessageSquare, desc: '聊天群组、消息审核、成员管理', color: 'bg-blue-500'},
  {href: '/admin/integrations', label: '集成管理', icon: Globe, desc: '第三方集成、API 配置、OAuth 应用', color: 'bg-indigo-500'},
];

export default function AdminSocial() {
  return (
    <AdminShell title="社交管理">
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
