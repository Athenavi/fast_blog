'use client';


import {useQuery, useQueryClient} from '@tanstack/react-query';
import {QueryProvider} from '@/components/QueryProvider';
import {VIPService} from '@/lib/api/vip-services';
import {Check, Crown, Loader2} from 'lucide-react';
import {useState} from 'react';
import {useTranslation} from '@/lib/i18n';

function VipInner() {
  const {t} = useTranslation();
  const queryClient = useQueryClient();
  const [subscribing, setSubscribing] = useState<number | null>(null);
  const [subscribeMsg, setSubscribeMsg] = useState<{type: 'success'|'error', text: string} | null>(null);

  const {data: featuresData} = useQuery({
    queryKey: ['vip-features'],
    queryFn: async () => {
      const r = await VIPService.getVipFeatures();
      return r.success && r.data ? r.data : null;
    },
  });
  const {data: plansData} = useQuery({
    queryKey: ['vip-plans'],
    queryFn: async () => {
      const r = await VIPService.getVipPlans();
      return r.success && r.data ? r.data : [];
    },
  });
  const {data: status} = useQuery({
    queryKey: ['vip-status'],
    queryFn: async () => {
      const r = await VIPService.getVipStatus();
      return r.success && r.data ? r.data : {};
    },
  });

  const plans = Array.isArray(plansData) ? plansData : [];
  const tiers = plans.map(p => ({
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
    id: p.id,
  }));

  const hasTiers = tiers.length > 0;

  const handleSubscribe = async (planId: number, planPrice: number) => {
    setSubscribing(planId);
    setSubscribeMsg(null);
    try {
      // 先尝试通过支付网关创建支付订单
      const payment = await VIPService.createPayment({plan_id: planId, provider: undefined});
      if (payment.success && payment.data?.payment_url) {
        // 支付网关可用，跳转到支付页面
        window.location.href = payment.data.payment_url;
        return;
      }
      // 支付网关不可用或无实际支付URL，直接调用订阅（免费套餐或测试模式）
      const r = await VIPService.subscribe(planId, planPrice);
      if (r.success) {
        setSubscribeMsg({type: 'success', text: t('vip.subscriptionSuccess')});
        queryClient.invalidateQueries({queryKey: ['vip-status']});
        queryClient.invalidateQueries({queryKey: ['vip-plans']});
        queryClient.invalidateQueries({queryKey: ['user']});
      } else {
        setSubscribeMsg({type: 'error', text: r.message || t('vip.subscriptionFailed')});
      }
    } catch (e: any) {
      setSubscribeMsg({type: 'error', text: e?.message || t('vip.subscriptionFailed')});
    } finally {
      setSubscribing(null);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-purple-50 dark:from-gray-950 dark:via-gray-900 dark:to-gray-950">
      <div className="max-w-5xl mx-auto px-4 py-16 sm:py-24 text-center">
        <div className="inline-flex items-center gap-2 px-4 py-1.5 bg-purple-100 dark:bg-purple-900/30 rounded-full text-sm font-medium text-purple-700 dark:text-purple-300 mb-6"><Crown className="w-4 h-4"/>{t('vip.title')}</div>
        <h1 className="text-4xl sm:text-5xl font-black text-gray-900 dark:text-white mb-4">{t('vip.unlockAll')}</h1>
        <p className="text-lg text-gray-500 dark:text-gray-400 mb-12 max-w-xl mx-auto">{t('vip.upgradeDesc')}</p>

        {status?.is_vip && <div className="inline-flex items-center gap-2 px-5 py-2.5 bg-green-100 dark:bg-green-900/20 rounded-xl text-green-700 dark:text-green-300 mb-12"><Crown className="w-5 h-5"/>{t('vip.activeStatus')} {new Date(status.expires_at).toLocaleDateString()}</div>}

        {subscribeMsg && (
          <div className={`mb-6 px-4 py-2 rounded-xl text-sm font-medium ${
            subscribeMsg.type === 'success' ? 'bg-green-100 dark:bg-green-900/20 text-green-700 dark:text-green-300' : 'bg-red-100 dark:bg-red-900/20 text-red-700 dark:text-red-300'
          }`}>
            {subscribeMsg.text}
          </div>
        )}

        {hasTiers ? (
          <div className="grid md:grid-cols-3 gap-6 max-w-4xl mx-auto">
            {tiers.map(t => (
              <div key={t.id || t.name} className="relative bg-white dark:bg-gray-900 rounded-2xl p-6 border-2 border-gray-100 dark:border-gray-800 transition-all hover:shadow-lg">
                <Crown className="w-8 h-8 mx-auto mb-3 text-blue-600"/>
                <h2 className="text-lg font-bold text-gray-900 dark:text-white">{t.name}</h2>
                {t.description && <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 mb-3">{t.description}</p>}
                <div className="my-4"><span className="text-3xl font-black text-gray-900 dark:text-white">{t.price}</span><span className="text-sm text-gray-400">{t.period}</span></div>
                <ul className="space-y-2.5 mb-6 text-left">
                  {t.features.map((f: any, i: number) => (
                    <li key={i} className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400"><Check className="w-4 h-4 text-green-500 shrink-0"/>{f}</li>
                  ))}
                </ul>
                <button
                  onClick={() => handleSubscribe(t.id!, parseFloat(t.price.replace('¥', '')) || 0)}
                  disabled={subscribing === t.id}
                  className="w-full py-2.5 rounded-xl text-sm font-medium transition-colors disabled:opacity-60 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-900 dark:text-white"
                >
                  {subscribing === t.id ? (
                    <span className="inline-flex items-center gap-2"><Loader2 className="w-4 h-4 animate-spin"/>{t('common.loading')}</span>
                  ) : (
                    t.price === '¥0' ? t('vip.currentPlan') : t('vip.upgrade')
                  )}
                </button>
              </div>
            ))}
          </div>
        ) : (
          <div className="max-w-md mx-auto py-16 text-center">
            <Crown className="w-16 h-16 mx-auto mb-4 text-gray-300 dark:text-gray-600"/>
            <p className="text-lg font-medium text-gray-500 dark:text-gray-400">{t('vip.noPlans')}</p>
            <p className="text-sm text-gray-400 dark:text-gray-500 mt-1">{t('vip.contactAdmin')}</p>
          </div>
        )}
      </div>
    </div>
  );
}

export default function VipPage() { return <QueryProvider><VipInner/></QueryProvider>; }
