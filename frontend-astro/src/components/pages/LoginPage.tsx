/**
 * 登录页面 - 完整认证实现
 * 路由对齐后端：/api/v2/auth/*, /api/v2/users/me, /api/v2/security/2fa/*
 */

'use client';

import React, {useEffect, useState} from 'react';
import {apiClient} from '@/lib/api';

const LoginPage: React.FC = () => {
  const [form, setForm] = useState({email: '', password: '', rememberMe: false});
  const [loading, setLoading] = useState(false);
  const [pwVisible, setPwVisible] = useState(false);
  const [error, setError] = useState('');
  const [checking, setChecking] = useState(true);
  const [requires2FA, setRequires2FA] = useState(false);
  const [tempToken, setTempToken] = useState('');
  const [userId, setUserId] = useState<number | null>(null);
  const [twoFACode, setTwoFACode] = useState('');
  const [twoFALoading, setTwoFALoading] = useState(false);
  const [useBackup, setUseBackup] = useState(false);

  // 检查已登录 → 自动跳转
  useEffect(() => {
    (async () => {
      try {
        const t = getCookie('access_token');
        const rt = getCookie('refresh_token');
        if (!t && rt) {
          const r = await apiClient.post('/auth/token/refresh', {refresh: rt});
          if (r.success && r.data) {
            const d = r.data as any;
            if (d.access_token) {
              setCookie('access_token', d.access_token, 3600);
              if (d.refresh_token) setCookie('refresh_token', d.refresh_token, 604800);
              const p = await apiClient.get('/users/me');
              if (p.success && p.data) {
                window.location.href = new URLSearchParams(window.location.search).get('next') || '/profile';
                return;
              }
            }
          }
          document.cookie = 'refresh_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/';
        } else if (t) {
          const p = await apiClient.get('/users/me');
          if (p.success && p.data) {
            window.location.href = new URLSearchParams(window.location.search).get('next') || '/profile';
            return;
          }
        }
      } catch {
      }
      setChecking(false);
    })();
  }, []);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      const res = await apiClient.postForm('/auth/login', {
        username: form.email, password: form.password, remember_me: form.rememberMe
      });
      if (res.success && res.data) {
        const d = res.data as any;
        if (d.requires_2fa && d.temp_token) {
          setRequires2FA(true);
          setTempToken(d.temp_token);
          setUserId(d.user_id || null);
          return;
        }
        if (d.access_token) {
          setCookie('access_token', d.access_token, 3600);
          if (d.refresh_token) setCookie('refresh_token', d.refresh_token, 604800);
        }
        const next = new URLSearchParams(window.location.search).get('next') || '/profile';
        setTimeout(() => window.location.href = next, 300);
      } else {
        setError(res.error || res.message || '登录失败');
      }
    } catch (err: any) {
      setError(err.status === 401 ? '用户名或密码错误' : (err.message || '登录错误'));
    } finally {
      setLoading(false);
    }
  };

  const handle2FA = async (e: React.FormEvent) => {
    e.preventDefault();
    const expected = useBackup ? 8 : 6;
    if (!twoFACode || twoFACode.length !== expected) {
      setError(useBackup ? '请输入8位备用码' : '请输入6位验证码');
      return;
    }
    if (!userId) {
      setError('用户信息丢失');
      return;
    }
    setTwoFALoading(true);
    setError('');
    try {
      const res = await apiClient.post('/security/2fa/verify-login', {user_id: userId, token: twoFACode});
      if (res.success && res.data) {
        const d = res.data as any;
        if (d.access_token) {
          setCookie('access_token', d.access_token, 3600);
          if (d.refresh_token) setCookie('refresh_token', d.refresh_token, 604800);
        }
        const next = new URLSearchParams(window.location.search).get('next') || '/profile';
        setTimeout(() => window.location.href = next, 300);
      } else setError(res.error || '2FA验证失败');
    } catch (err: any) {
      setError(err.message || '验证错误');
    }
    finally { setTwoFALoading(false); }
  };

  if (checking) {
    return (
      <div className="min-h-[80vh] flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-10 w-10 border-t-2 border-b-2 border-indigo-600 mb-4" />
          <p className="text-gray-600 dark:text-gray-300">正在检查登录状态...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full max-w-md mx-auto bg-white dark:bg-gray-800 rounded-xl shadow-md p-8">
      <div className="text-center mb-8">
        <div className="w-12 h-12 bg-indigo-600 rounded-lg flex items-center justify-center mx-auto mb-4">
          <svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"/></svg>
        </div>
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white">登录</h2>
        <p className="mt-2 text-sm text-gray-600 dark:text-gray-300">
          还没有账户？<a href="/register" className="font-medium text-indigo-600 hover:text-indigo-500">立即注册</a>
        </p>
      </div>

      {error &&
          <div className="mb-4 p-3 bg-red-100 border border-red-400 text-red-700 rounded-md text-sm">{error}</div>}

      {!requires2FA ? (
        <form onSubmit={handleLogin}>
          <div className="mb-4">
            <input type="text" value={form.email} onChange={e => setForm(f => ({...f, email: e.target.value}))}
              placeholder="用户名或邮箱"
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white" required />
          </div>
          <div className="mb-4 relative">
            <input type={pwVisible ? 'text' : 'password'} value={form.password}
                   onChange={e => setForm(f => ({...f, password: e.target.value}))}
              placeholder="密码"
                   className="w-full px-4 py-3 pr-12 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                   required/>
            <button type="button" onClick={() => setPwVisible(!pwVisible)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 text-sm">
              {pwVisible ? '🙈' : '👁️'}
            </button>
          </div>
          <div className="flex items-center justify-between mb-6">
            <label className="flex items-center gap-2">
              <input type="checkbox" checked={form.rememberMe}
                     onChange={e => setForm(f => ({...f, rememberMe: e.target.checked}))}
                     className="h-4 w-4 text-indigo-600 border-gray-300 rounded"/>
              <span className="text-sm text-gray-600 dark:text-gray-300">记住我</span>
            </label>
          </div>
          <button type="submit" disabled={loading}
            className="w-full py-3 bg-indigo-600 text-white rounded-lg font-semibold hover:bg-indigo-700 disabled:opacity-50 transition-colors">
            {loading ? '登录中...' : '登录'}
          </button>
        </form>
      ) : (
          <form onSubmit={handle2FA}>
          <div className="text-center mb-6">
            <div className="w-16 h-16 bg-indigo-100 dark:bg-indigo-900 rounded-full flex items-center justify-center mx-auto mb-4">
              <span className="text-3xl">🔐</span>
            </div>
            <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">双因素认证</h3>
            <p className="text-sm text-gray-500">{useBackup ? '请输入8位备用码' : '请输入身份验证器中的6位验证码'}</p>
          </div>
          <div className="mb-6">
            <input type="text" value={twoFACode}
                   onChange={e => setTwoFACode(e.target.value.replace(/\D/g, '').slice(0, useBackup ? 8 : 6))}
                   placeholder={useBackup ? '备用码' : '验证码'}
              className="w-full px-4 py-3 text-center text-2xl tracking-widest border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white" />
          </div>
          <button type="submit" disabled={twoFALoading}
                  className="w-full py-3 bg-indigo-600 text-white rounded-lg font-semibold hover:bg-indigo-700 disabled:opacity-50">
            {twoFALoading ? '验证中...' : '验证'}
          </button>
            <button type="button" onClick={() => setUseBackup(!useBackup)}
            className="w-full mt-2 text-sm text-indigo-600 hover:text-indigo-500">
              {useBackup ? '使用验证码' : '使用备用码'}
          </button>
        </form>
      )}

      <div className="mt-6">
        <div className="flex items-center gap-4 mb-6">
          <div className="flex-1 border-t border-gray-300 dark:border-gray-600" />
          <span className="text-sm text-gray-500">或使用社交账号</span>
          <div className="flex-1 border-t border-gray-300 dark:border-gray-600" />
        </div>
        <div className="grid grid-cols-2 gap-3">
          {['Google', 'GitHub'].map(name => (
            <button key={name} type="button"
              className="flex items-center justify-center gap-2 py-2.5 px-4 border border-gray-300 dark:border-gray-600 rounded-lg text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors">
              {name === 'Google' ? (
                <svg className="w-5 h-5" viewBox="0 0 24 24"><path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/><path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/><path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85 2.22.81-.62z"/><path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/></svg>
              ) : (
                <svg className="w-5 h-5" viewBox="0 0 24 24"><path fill="currentColor" d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/></svg>
              )}
              {name}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
};

function getCookie(name: string): string | null {
  if (typeof document === 'undefined') return null;
  for (const c of document.cookie.split(';')) {
    const [n, v] = c.trim().split('=');
    if (n === name && v) return decodeURIComponent(v);
  }
  return null;
}

function setCookie(name: string, value: string, maxAgeSec: number) {
  document.cookie = `${name}=${value}; path=/; max-age=${maxAgeSec}; SameSite=Lax`;
}

export default LoginPage;
