'use client';

import React from 'react';
import {useQuery, useMutation} from '@tanstack/react-query';
import {AuthGuard} from '@/components/AuthGuard';
import {QueryProvider} from '@/components/QueryProvider';
import {AdminShell} from '@/components/admin/AdminShell';
import {apiClient} from '@/lib/api';
import {Shield, Download, Trash2, Check} from 'lucide-react';

function GDPRInner() {
  const {data:checklist} = useQuery({
    queryKey: ['admin-gdpr'], queryFn: async () => {
      const r = await apiClient.get<any>('/gdpr/compliance-checklist');
      return r.success&&r.data?r.data:{};
    },
  });
  const exportMut = useMutation({mutationFn:()=>apiClient.post('/gdpr/data-export')});
  const deleteMut = useMutation({mutationFn:()=>apiClient.post('/gdpr/data-deletion')});

  const items = Array.isArray(checklist?.items) ? checklist.items : [
    {name:'隐私政策更新', done:true},
    {name:'Cookie 同意', done:true},
    {name:'数据保留策略', done:false},
    {name:'用户数据导出功能', done:true},
    {name:'账户删除功能', done:true},
    {name:'数据处理记录', done:false},
  ];

  return (
    <AdminShell title="GDPR 合规">
      <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 p-6 mb-6">
        <h3 className="font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2"><Shield className="w-5 h-5"/>合规检查表</h3>
        <div className="space-y-2">
          {items.map((item:any,i:number) => (
            <div key={i} className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded-xl">
              <span className="text-sm text-gray-700 dark:text-gray-300">{item.name||item.check||'-'}</span>
              <span className={`flex items-center gap-1 text-xs ${item.done?'text-green-600':'text-red-500'}`}>{item.done ? <><Check className="w-3.5 h-3.5"/>已完成</> : <><XIcon className="w-3.5 h-3.5"/>待处理</>}</span>
            </div>
          ))}
        </div>
      </div>
      <div className="flex gap-3">
        <button onClick={()=>exportMut.mutate()} className="px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded-xl flex items-center gap-2"><Download className="w-4 h-4"/>导出用户数据</button>
        <button onClick={()=>{if(confirm('确认删除所有用户数据？'))deleteMut.mutate();}} className="px-5 py-2.5 border border-red-200 text-red-600 text-sm rounded-xl hover:bg-red-50 flex items-center gap-2"><Trash2 className="w-4 h-4"/>删除用户数据</button>
      </div>
    </AdminShell>
  );
}
const XIcon = ({className}:{className?:string})=><svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12"/></svg>;
export default function AdminGDPR() { return <AuthGuard><QueryProvider><GDPRInner/></QueryProvider></AuthGuard>; }
