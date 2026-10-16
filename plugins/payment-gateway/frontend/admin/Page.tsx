'use client';

import React, {useState} from 'react';
import {useMutation, useQuery} from '@tanstack/react-query';
import {AdminShell} from '@/components/admin/AdminShell';
import {apiClient} from '@/lib/api/base-client';
import {ArrowRight, CheckCircle2, CreditCard, DollarSign, Loader2, RefreshCw} from 'lucide-react';

const PLUGIN_SLUG = 'payment-gateway';

function call(action: string, params: any = {}) {
  return apiClient.post(`/plugins/${PLUGIN_SLUG}/action`, {action, params});
}

function PaymentGatewayDashboard() {
  const [orderId, setOrderId] = useState('');
  const [amount, setAmount] = useState('');
  const [provider, setProvider] = useState('');

  const {data: settings, isLoading: loadSettings, refetch} = useQuery({
    queryKey: ['payment-gateway-settings'],
    queryFn: async () => {
      const r = await call('get_settings');
      return r.data || {};
    },
  });

  const testPaymentMut = useMutation({
    mutationFn: () => call('create_payment', {
      order_id: orderId || `test_${Date.now()}`,
      amount: parseInt(amount, 10) || 100,
      subject: '测试支付',
    }),
  });

  return (
    <AdminShell title="支付网关" actions={
      <button onClick={() => refetch()} disabled={loadSettings}
              className="flex items-center gap-1.5 px-4 py-2 border rounded-lg text-sm hover:bg-gray-50 dark:hover:bg-gray-800 disabled:opacity-50">
        <RefreshCw className={`w-4 h-4 ${loadSettings ? 'animate-spin' : ''}`}/> 刷新
      </button>
    }>
      {/* 当前配置状态 */}
      <div className="mb-6 grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white dark:bg-gray-900 rounded-xl border p-5">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-10 h-10 bg-blue-100 dark:bg-blue-900/30 rounded-lg flex items-center justify-center">
              <CreditCard className="w-5 h-5 text-blue-600 dark:text-blue-400"/>
            </div>
            <div>
              <p className="text-sm text-gray-500">当前提供商</p>
              <p className="text-lg font-semibold">{settings?.provider || '未配置'}</p>
            </div>
          </div>
        </div>
        <div className="bg-white dark:bg-gray-900 rounded-xl border p-5">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-10 h-10 bg-green-100 dark:bg-green-900/30 rounded-lg flex items-center justify-center">
              <DollarSign className="w-5 h-5 text-green-600 dark:text-green-400"/>
            </div>
            <div>
              <p className="text-sm text-gray-500">货币</p>
              <p className="text-lg font-semibold uppercase">{settings?.currency || 'cny'}</p>
            </div>
          </div>
        </div>
        <div className="bg-white dark:bg-gray-900 rounded-xl border p-5">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-10 h-10 bg-purple-100 dark:bg-purple-900/30 rounded-lg flex items-center justify-center">
              <CheckCircle2 className="w-5 h-5 text-purple-600 dark:text-purple-400"/>
            </div>
            <div>
              <p className="text-sm text-gray-500">沙箱模式</p>
              <p className="text-lg font-semibold">{settings?.alipay_sandbox ? '开启' : '关闭'}</p>
            </div>
          </div>
        </div>
      </div>

      {/* 测试支付 */}
      <div className="bg-white dark:bg-gray-900 rounded-xl border p-5 mb-6">
        <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-4">测试支付</h3>
        <div className="flex flex-wrap gap-3">
          <input value={orderId} onChange={e => setOrderId(e.target.value)}
                 placeholder="订单号（可选，自动生成）"
                 className="flex-1 min-w-[200px] px-3 py-2 border rounded-lg text-sm bg-white dark:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500"/>
          <input value={amount} onChange={e => setAmount(e.target.value)}
                 placeholder="金额（分）" type="number"
                 className="w-32 px-3 py-2 border rounded-lg text-sm bg-white dark:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500"/>
          <button onClick={() => testPaymentMut.mutate()} disabled={testPaymentMut.isPending}
                  className="flex items-center gap-1.5 px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 disabled:opacity-50">
            {testPaymentMut.isPending ? '处理中...' : <><ArrowRight className="w-4 h-4"/> 发起测试</>}
          </button>
        </div>
        {testPaymentMut.data && (
          <div className="mt-3 p-3 bg-gray-50 dark:bg-gray-800 rounded-lg text-xs">
            <pre
              className="whitespace-pre-wrap text-gray-600 dark:text-gray-400">{JSON.stringify(testPaymentMut.data, null, 2)}</pre>
          </div>
        )}
      </div>

      {/* 配置信息 */}
      <div className="bg-white dark:bg-gray-900 rounded-xl border p-5">
        <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">支付配置</h3>
        {loadSettings ? (
          <div className="flex justify-center py-8"><Loader2 className="w-6 h-6 animate-spin text-blue-500"/></div>
        ) : (
          <div className="text-sm text-gray-500 space-y-2">
            {settings?.alipay_app_id &&
              <p>支付宝 AppID: <code className="text-gray-700 dark:text-gray-300">{settings.alipay_app_id}</code></p>}
            {settings?.wechat_app_id &&
              <p>微信 AppID: <code className="text-gray-700 dark:text-gray-300">{settings.wechat_app_id}</code></p>}
            {settings?.stripe_secret_key &&
              <p>Stripe: <code className="text-gray-700 dark:text-gray-300">已配置</code></p>}
            {!settings?.alipay_app_id && !settings?.wechat_app_id && !settings?.stripe_secret_key &&
              <p>暂未配置支付参数，请在插件设置中配置</p>}
          </div>
        )}
      </div>
    </AdminShell>
  );
}

export default function PaymentGatewayPage() {
  return <PaymentGatewayDashboard/>;
}
