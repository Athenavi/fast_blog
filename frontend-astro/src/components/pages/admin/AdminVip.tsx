'use client';

import React, {useState} from 'react';
import {useQuery} from '@tanstack/react-query';
import {AuthGuard} from '@/components/AuthGuard';
import {QueryProvider} from '@/components/QueryProvider';
import {AdminShell} from '@/components/admin/AdminShell';
import {apiClient} from '@/lib/api';
import {Crown, Users, TrendingUp, DollarSign, Search} from 'lucide-react';

function VipAdminInner() {
  const [search, setSearch] = useState('');
  const {data: mgmt, isLoading} = useQuery({
    queryKey: ['admin-vip'],
    queryFn: async () => {
      const r = await apiClient.get<any>('/dashboard/vip-management');
      return r.success && r.data ? r.data : {};
    },
  });
  const stats = mgmt?.stats || {};
  const members = Array.isArray(mgmt?.members) ? mgmt.members : [];

  return (
    <AdminShell title="VIP 管理">
      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 p-5"><div className="flex items-center gap-2 text-sm text-gray-500 mb-1"><Crown className="w-4 h-4"/>VIP 总数</div><p className="text-2xl font-bold">{stats.total_vip_count ?? '—'}</p></div>
        <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 p-5"><div className="flex items-center gap-2 text-sm text-gray-500 mb-1"><Users className="w-4 h-4"/>本月新增</div><p className="text-2xl font-bold">{stats.monthly_new ?? '—'}</p></div>
        <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 p-5"><div className="flex items-center gap-2 text-sm text-gray-500 mb-1"><DollarSign className="w-4 h-4"/>月收入</div><p className="text-2xl font-bold">{stats.monthly_revenue ?? '—'}</p></div>
        <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 p-5"><div className="flex items-center gap-2 text-sm text-gray-500 mb-1"><TrendingUp className="w-4 h-4"/>续费率</div><p className="text-2xl font-bold">{stats.renewal_rate ? `${stats.renewal_rate}%` : '—'}</p></div>
      </div>
      {/* Search */}
      <div className="relative mb-4"><Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400"/><input type="text" value={search} onChange={e=>setSearch(e.target.value)} placeholder="搜索会员..." className="w-full pl-10 pr-4 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl bg-white dark:bg-gray-900 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white"/></div>
      {/* Table */}
      <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 overflow-hidden">
        {isLoading ? (
          <div className="p-12 text-center"><div className="animate-spin w-6 h-6 border-2 border-blue-600 border-t-transparent rounded-full mx-auto"/></div>
        ) : !members.length ? (
          <div className="p-12 text-center text-gray-400"><Crown className="w-10 h-10 mx-auto mb-3 opacity-40"/><p>暂无 VIP 会员</p></div>
        ) : (
          <table className="w-full"><thead className="bg-gray-50 dark:bg-gray-800 border-b"><tr><th className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase">用户</th><th className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase hidden sm:table-cell">等级</th><th className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase hidden md:table-cell">到期</th><th className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase">状态</th></tr></thead><tbody className="divide-y">
            {members.filter((m:any)=>!search||m.username?.includes(search)).map((m:any,i:number) => (
              <tr key={m.id||i} className="hover:bg-gray-50 dark:hover:bg-gray-800/50">
                <td className="px-5 py-4"><div className="flex items-center gap-3"><div className="w-8 h-8 rounded-full bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center text-white text-xs font-bold">{m.username?.charAt(0)||'?'}</div><span className="font-medium text-sm text-gray-900 dark:text-white">{m.username}</span></div></td>
                <td className="px-5 py-4 text-sm hidden sm:table-cell"><span className="px-2 py-0.5 text-xs rounded-full bg-purple-100 dark:bg-purple-900/20 text-purple-700">{m.level||'VIP'}</span></td>
                <td className="px-5 py-4 text-sm text-gray-500 hidden md:table-cell">{m.expires_at ? new Date(m.expires_at).toLocaleDateString('zh-CN') : '-'}</td>
                <td className="px-5 py-4"><span className={`px-2 py-0.5 text-xs rounded-full ${m.is_active !== false ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>{m.is_active !== false ? '有效' : '过期'}</span></td>
              </tr>
            ))}
          </tbody></table>
        )}
      </div>
    </AdminShell>
  );
}

export default function AdminVip() { return <AuthGuard><QueryProvider><VipAdminInner /></QueryProvider></AuthGuard>; }
