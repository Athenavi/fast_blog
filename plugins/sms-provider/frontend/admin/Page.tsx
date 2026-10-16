'use client';

import React, {useState} from 'react';
import {useMutation, useQuery} from '@tanstack/react-query';
import {AdminShell} from '@/components/admin/AdminShell';
import {apiClient} from '@/lib/api/base-client';
import {CheckCircle2, Loader2, MessageSquare, RefreshCw, Send, Smartphone, XCircle} from 'lucide-react';

const PLUGIN_SLUG = 'sms-provider';

function call(action: string, params: any = {}) {
  return apiClient.post(`/plugins/${PLUGIN_SLUG}/action`, {action, params});
}

function SmsProviderDashboard() {
  const [phone, setPhone] = useState('');
  const [code, setCode] = useState('');

  const {data: settings, isLoading: loadSettings, refetch} = useQuery({
    queryKey: ['sms-provider-settings'],
    queryFn: async () => {
      const r = await call('get_settings');
      return r.data || {};
    },
  });

  const sendTestMut = useMutation({
    mutationFn: () => call('send_sms', {phone, code: code || '123456'}),
  });

  const providerLabel = (p: string) => {
    switch (p) {
      case 'aliyun':
        return '阿里云';
      case 'tencent':
        return '腾讯云';
      case 'twilio':
        return 'Twilio';
      default:
        return '未配置';
    }
  };

  return (
    <AdminShell title="短信服务" actions={
      <button onClick={() => refetch()} disabled={loadSettings}
              className="flex items-center gap-1.5 px-4 py-2 border rounded-lg text-sm hover:bg-gray-50 dark:hover:bg-gray-800 disabled:opacity-50">
        <RefreshCw className={`w-4 h-4 ${loadSettings ? 'animate-spin' : ''}`}/> 刷新
      </button>
    }>
      {/* 当前服务商状态 */}
      <div className="mb-6 grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white dark:bg-gray-900 rounded-xl border p-5">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-blue-100 dark:bg-blue-900/30 rounded-lg flex items-center justify-center">
              <MessageSquare className="w-5 h-5 text-blue-600 dark:text-blue-400"/>
            </div>
            <div>
              <p className="text-sm text-gray-500">当前服务商</p>
              <p className="text-lg font-semibold">{providerLabel(settings?.provider)}</p>
            </div>
          </div>
        </div>
        <div className="bg-white dark:bg-gray-900 rounded-xl border p-5">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-green-100 dark:bg-green-900/30 rounded-lg flex items-center justify-center">
              <Smartphone className="w-5 h-5 text-green-600 dark:text-green-400"/>
            </div>
            <div>
              <p className="text-sm text-gray-500">签名</p>
              <p
                className="text-lg font-semibold">{settings?.aliyun_sign_name || settings?.tencent_sign_name || '—'}</p>
            </div>
          </div>
        </div>
        <div className="bg-white dark:bg-gray-900 rounded-xl border p-5">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-purple-100 dark:bg-purple-900/30 rounded-lg flex items-center justify-center">
              {settings?.provider ? <CheckCircle2 className="w-5 h-5 text-green-600 dark:text-green-400"/> :
                <XCircle className="w-5 h-5 text-gray-400"/>}
            </div>
            <div>
              <p className="text-sm text-gray-500">状态</p>
              <p className="text-lg font-semibold">{settings?.provider ? '已配置' : '未配置'}</p>
            </div>
          </div>
        </div>
      </div>

      {/* 测试发送 */}
      <div className="bg-white dark:bg-gray-900 rounded-xl border p-5 mb-6">
        <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-4">测试短信发送</h3>
        <div className="flex flex-wrap gap-3">
          <input value={phone} onChange={e => setPhone(e.target.value)}
                 placeholder="手机号"
                 className="flex-1 min-w-[200px] px-3 py-2 border rounded-lg text-sm bg-white dark:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500"/>
          <input value={code} onChange={e => setCode(e.target.value)}
                 placeholder="验证码（默认 123456）"
                 className="w-40 px-3 py-2 border rounded-lg text-sm bg-white dark:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500"/>
          <button onClick={() => sendTestMut.mutate()} disabled={sendTestMut.isPending || !phone}
                  className="flex items-center gap-1.5 px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 disabled:opacity-50">
            {sendTestMut.isPending ? '发送中...' : <><Send className="w-4 h-4"/> 发送测试</>}
          </button>
        </div>
        {sendTestMut.data && (
          <div
            className={`mt-3 p-3 rounded-lg text-xs ${sendTestMut.data.success ? 'bg-green-50 dark:bg-green-900/10 text-green-700 dark:text-green-400' : 'bg-red-50 dark:bg-red-900/10 text-red-700 dark:text-red-400'}`}>
            {sendTestMut.data.success ? '✓ 发送成功' : `✗ 发送失败: ${sendTestMut.data.error || '未知错误'}`}
          </div>
        )}
      </div>

      {/* 配置信息 */}
      <div className="bg-white dark:bg-gray-900 rounded-xl border p-5">
        <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">短信配置</h3>
        {loadSettings ? (
          <div className="flex justify-center py-8"><Loader2 className="w-6 h-6 animate-spin text-blue-500"/></div>
        ) : (
          <div className="text-sm text-gray-500 space-y-2">
            {settings?.aliyun_access_key_id &&
              <p>阿里云: <code className="text-gray-700 dark:text-gray-300">已配置</code></p>}
            {settings?.tencent_secret_id &&
              <p>腾讯云: <code className="text-gray-700 dark:text-gray-300">已配置</code></p>}
            {settings?.twilio_account_sid &&
              <p>Twilio: <code className="text-gray-700 dark:text-gray-300">已配置</code></p>}
            {!settings?.aliyun_access_key_id && !settings?.tencent_secret_id && !settings?.twilio_account_sid &&
              <p>暂未配置短信参数，请在插件设置中配置</p>}
          </div>
        )}
      </div>
    </AdminShell>
  );
}

export default function SmsProviderPage() {
  return <SmsProviderDashboard/>;
}
