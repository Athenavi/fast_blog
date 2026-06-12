'use client';

import React from 'react';
import {AdminShell} from '@/components/admin/AdminShell';
import {Puzzle, Database, Server, ScrollText, AlertTriangle, ChevronRight} from 'lucide-react';

const LINKS = [
  {href: '/admin/plugins', label: '插件管理', icon: Puzzle, desc: '安装、激活、配置插件和主题', color: 'bg-blue-500'},
  {href: '/admin/backup', label: '备份管理', icon: Database, desc: '数据库备份、恢复与下载', color: 'bg-emerald-500'},
  {href: '/admin/system', label: '系统信息', icon: Server, desc: '版本信息、运行状态、环境配置', color: 'bg-purple-500'},
  {href: '/admin/audit-logs', label: '审计日志', icon: ScrollText, desc: '操作记录、权限审核、安全追踪', color: 'bg-amber-500'},
  {href: '/admin/sensitive-words', label: '敏感词管理', icon: AlertTriangle, desc: '敏感词过滤、替换规则', color: 'bg-red-500'},
];

export default function AdminSystemHub() {
  return (
    <AdminShell title="系统管理">
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
