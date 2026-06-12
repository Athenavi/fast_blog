'use client';

import React from 'react';
import {PermissionGuard} from '@/components/admin/PermissionGuard';
import {AdminShell} from '@/components/admin/AdminShell';
import {Banknote, Package, Crown, ChevronRight} from 'lucide-react';

const LINKS = [
  {href: '/admin/finance', label: '财务管理', icon: Banknote, desc: '支付网关、交易记录、税务、收益分成', color: 'bg-emerald-500'},
  {href: '/admin/ecommerce', label: '电商管理', icon: Package, desc: '商品管理、购物车、订单处理', color: 'bg-blue-500'},
  {href: '/admin/vip', label: 'VIP 管理', icon: Crown, desc: 'VIP 等级、套餐、功能配置', color: 'bg-amber-500'},
];

export default function AdminCommerce() {
  return (
    <AdminShell title="商业管理">
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
