'use client';


import {useQuery} from '@tanstack/react-query';
import {QueryProvider} from '@/components/QueryProvider';
import {apiClient} from '@/lib/api/base-client';
import {MEMBERSHIP} from '@/lib/api/api-paths';
import {Check, Crown} from 'lucide-react';

function VipInner() {
  const {data: features} = useQuery({
    queryKey: ['vip-features'],
    queryFn: async () => {
      const r = await apiClient.get<any[]>(MEMBERSHIP.FEATURES);
      return r.success && r.data ? (Array.isArray(r.data) ? r.data : []) : [];
    },
  });
  const {data: status} = useQuery({
    queryKey: ['vip-status'],
    queryFn: async () => {
      const r = await apiClient.get(MEMBERSHIP.STATUS);
      return r.success && r.data ? r.data : {};
    },
  });

  const tiers = Array.isArray(features) ? features.map(p => ({
    name: p.name || '',
    price: p.price ? `¥${p.price}` : '¥0',
    period: p.duration_days ? `/ ${p.duration_days}天` : '',
    features: (() => {
      try {
        const parsed = typeof p.features === 'string' ? JSON.parse(p.features) : p.features;
        return Array.isArray(parsed) ? parsed : [];
      } catch { return []; }
    })(),
    description: p.description || '',
    level: p.level || 1,
  })) : [];

  const hasTiers = tiers.length > 0;

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-purple-50 dark:from-gray-950 dark:via-gray-900 dark:to-gray-950">
      <div className="max-w-5xl mx-auto px-4 py-16 sm:py-24 text-center">
        <div className="inline-flex items-center gap-2 px-4 py-1.5 bg-purple-100 dark:bg-purple-900/30 rounded-full text-sm font-medium text-purple-700 dark:text-purple-300 mb-6"><Crown className="w-4 h-4"/>VIP 会员</div>
        <h1 className="text-4xl sm:text-5xl font-black text-gray-900 dark:text-white mb-4">解锁全部功能</h1>
        <p className="text-lg text-gray-500 dark:text-gray-400 mb-12 max-w-xl mx-auto">升级到
          VIP，享受更强大的写作和分析工具</p>

        {status?.is_vip && <div className="inline-flex items-center gap-2 px-5 py-2.5 bg-green-100 dark:bg-green-900/20 rounded-xl text-green-700 dark:text-green-300 mb-12"><Crown className="w-5 h-5"/>您是 VIP 会员，有效期至 {new Date(status.expires_at).toLocaleDateString('zh-CN')}</div>}

        {hasTiers ? (
          <div className="grid md:grid-cols-3 gap-6 max-w-4xl mx-auto">
            {tiers.map(t => (
              <div key={t.name} className="relative bg-white dark:bg-gray-900 rounded-2xl p-6 border-2 border-gray-100 dark:border-gray-800 transition-all hover:shadow-lg">
                <Crown className="w-8 h-8 mx-auto mb-3 text-blue-600"/>
                <h2 className="text-lg font-bold text-gray-900 dark:text-white">{t.name}</h2>
                {t.description && <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 mb-3">{t.description}</p>}
                <div className="my-4"><span className="text-3xl font-black text-gray-900 dark:text-white">{t.price}</span><span className="text-sm text-gray-400">{t.period}</span></div>
                <ul className="space-y-2.5 mb-6 text-left">
                  {t.features.map((f: any, i: number) => (
                    <li key={i} className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400"><Check className="w-4 h-4 text-green-500 shrink-0"/>{f}</li>
                  ))}
                </ul>
                <button className="w-full py-2.5 rounded-xl text-sm font-medium transition-colors bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-900 dark:text-white">
                  {t.price === '¥0' ? '当前计划' : '立即升级'}
                </button>
              </div>
            ))}
          </div>
        ) : (
          <div className="max-w-md mx-auto py-16 text-center">
            <Crown className="w-16 h-16 mx-auto mb-4 text-gray-300 dark:text-gray-600"/>
            <p className="text-lg font-medium text-gray-500 dark:text-gray-400">暂无可用套餐</p>
            <p className="text-sm text-gray-400 dark:text-gray-500 mt-1">请联系管理员配置 VIP 套餐</p>
          </div>
        )}
      </div>
    </div>
  );
}

export default function VipPage() { return <QueryProvider><VipInner/></QueryProvider>; }
