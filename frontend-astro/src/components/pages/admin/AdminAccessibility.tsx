'use client';

import React from 'react';
import {useQuery} from '@tanstack/react-query';
import {AuthGuard} from '@/components/AuthGuard';
import {QueryProvider} from '@/components/QueryProvider';
import {AdminShell} from '@/components/admin/AdminShell';
import {apiClient} from '@/lib/api';
import {Eye, Check, X} from 'lucide-react';

function AccessInner() {
  const {data:audit} = useQuery({
    queryKey: ['admin-a11y-audit'], queryFn: async () => {
      const r = await apiClient.get<any>('/accessibility/audit'); return r.success&&r.data?r.data:{};
    },
  });
  const {data:checklist} = useQuery({
    queryKey: ['admin-a11y-checklist'], queryFn: async () => {
      const r = await apiClient.get<any[]>('/accessibility/audit/checklist'); return r.success&&r.data?(Array.isArray(r.data)?r.data:r.data.checklist||[]):[];
    },
  });

  const items = checklist?.length ? checklist : [
    {name:'图片替换文本', passed:true, wcag:'1.1.1'},
    {name:'颜色对比度', passed:true, wcag:'1.4.3'},
    {name:'键盘导航', passed:false, wcag:'2.1.1'},
    {name:'语义化标题', passed:true, wcag:'1.3.1'},
    {name:'ARIA 标签', passed:false, wcag:'4.1.2'},
  ];

  return (
    <AdminShell title="无障碍">
      <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 p-6 mb-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3"><Eye className="w-8 h-8 text-blue-600"/><div><p className="font-bold text-gray-900 dark:text-white">无障碍评分</p><p className="text-sm text-gray-500">WCAG 合规检查</p></div></div>
          <span className="text-3xl font-black text-gray-900 dark:text-white">{audit?.score||'—'}</span>
        </div>
      </div>
      <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 overflow-hidden">
        <table className="w-full"><thead className="bg-gray-50 dark:bg-gray-800 border-b"><tr><th className="px-5 py-3 text-xs font-semibold text-gray-500 uppercase text-left">检查项</th><th className="px-5 py-3 text-xs font-semibold text-gray-500 uppercase text-left hidden sm:table-cell">WCAG</th><th className="px-5 py-3 text-xs font-semibold text-gray-500 uppercase text-left">状态</th></tr></thead><tbody className="divide-y">
          {items.map((item:any,i:number) => (
            <tr key={i} className="hover:bg-gray-50 dark:hover:bg-gray-800/50">
              <td className="px-5 py-4 text-sm text-gray-900 dark:text-white">{item.name||item.check||'-'}</td>
              <td className="px-5 py-4 text-sm text-gray-500 font-mono hidden sm:table-cell">{item.wcag||item.guideline||'-'}</td>
              <td className="px-5 py-4">{item.passed ? <span className="flex items-center gap-1 text-green-600"><Check className="w-4 h-4"/>通过</span> : <span className="flex items-center gap-1 text-red-600"><X className="w-4 h-4"/>未通过</span>}</td>
            </tr>
          ))}
        </tbody></table>
      </div>
    </AdminShell>
  );
}
export default function AdminAccessibility() { return <AuthGuard><QueryProvider><AccessInner/></QueryProvider></AuthGuard>; }
