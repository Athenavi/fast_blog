'use client';

import {useEffect, useState} from 'react';
import {apiClient} from '@/lib/api/base-client';
import {AUTH} from '@/lib/api/api-paths';
import {CheckCircle, Loader, LogIn, Smartphone, XCircle} from 'lucide-react';

export default function MobileLoginPage() {
  const [status, setStatus] = useState<'checking'|'confirming'|'success'|'error'|'login_required'>('checking');
  const [msg, setMsg] = useState('');

  useEffect(() => {
    const token = new URLSearchParams(window.location.search).get('login_token') || new URLSearchParams(window.location.search).get('token');
    if (!token) { setStatus('error'); setMsg('缺少登录令牌'); return; }
    setStatus('confirming');
    (async () => {
      try {
        const r = await apiClient.post(AUTH.QR_CONFIRM, {login_token: token});
        if (r.success) { setStatus('success'); setMsg('登录确认成功，请返回电脑端继续'); }
        else if ((r as any).data?.requires_auth) {
          setStatus('login_required');
          setMsg('请先登录后再扫码确认');
        }
        else setStatus('error'), setMsg(r.error||'确认失败');
      } catch { setStatus('error'); setMsg('网络错误'); }
    })();
  }, []);

  // 携带 next 参数去登录页，登录后跳回当前确认页
  const [loginUrl, setLoginUrl] = useState('/login');

  useEffect(() => {
    // 在浏览器环境下才能访问 window.location
    if (typeof window !== 'undefined') {
      setLoginUrl(`/login?next=${encodeURIComponent(window.location.pathname + window.location.search)}`);
    }
  }, []);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-gray-950 dark:to-gray-900 p-4">
      <div className="text-center max-w-sm w-full">
        <div className="w-16 h-16 mx-auto mb-6 rounded-2xl bg-white dark:bg-gray-900 shadow-lg border flex items-center justify-center">
          <Smartphone className="w-8 h-8 text-blue-600"/>
        </div>

        {status === 'checking' && <><Loader className="w-6 h-6 animate-spin mx-auto text-blue-600"/><p className="mt-4 text-gray-600 dark:text-gray-400">检查登录状态...</p></>}

        {status === 'confirming' && <><Loader className="w-6 h-6 animate-spin mx-auto text-blue-600"/><p className="mt-4 text-gray-600 dark:text-gray-400">确认登录中...</p></>}

        {status === 'success' && <><CheckCircle className="w-12 h-12 mx-auto text-green-500"/><p className="mt-4 font-medium text-gray-900 dark:text-white">{msg}</p></>}

        {status === 'error' && <><XCircle className="w-12 h-12 mx-auto text-red-500"/><p className="mt-4 font-medium text-gray-900 dark:text-white">{msg}</p></>}

        {status === 'login_required' && (
          <>
            <XCircle className="w-12 h-12 mx-auto text-amber-500"/>
            <p className="mt-4 font-medium text-gray-900 dark:text-white mb-6">{msg}</p>
            <a
              href={loginUrl}
              className="inline-flex items-center justify-center gap-2 w-full px-6 py-3.5 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white font-semibold rounded-2xl transition-all shadow-lg shadow-blue-500/25 hover:shadow-xl active:scale-[0.98]"
            >
              <LogIn className="w-5 h-5"/>
              去登录
            </a>
            <p className="mt-3 text-xs text-gray-400">登录后将自动返回确认页面</p>
          </>
        )}
      </div>
    </div>
  );
}
