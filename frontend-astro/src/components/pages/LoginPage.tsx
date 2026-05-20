'use client';

import React, {useEffect, useRef, useState} from 'react';
import {apiClient} from '@/lib/api';
import {LogIn, Eye, EyeOff, Smartphone, ArrowLeft, QrCode} from 'lucide-react';

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

export default function LoginPage() {
  const [mode, setMode] = useState<'password'|'qrcode'>('password');
  const [u, setU] = useState('');
  const [pw, setPw] = useState('');
  const [rm, setRm] = useState(false);
  const [pv, setPv] = useState(false);
  const [err, setErr] = useState('');
  const [busy, setBusy] = useState(false);

  // 2FA
  const [fa, setFa] = useState<{tempToken:string;userId:number}|null>(null);
  const [code, setCode] = useState('');
  const [backup, setBackup] = useState(false);

  // QR code
  const [qrDataUrl, setQrDataUrl] = useState('');
  const qrTimer = useRef<NodeJS.Timeout>();

  // Auto-redirect if already logged in
  const [checking, setChecking] = useState(true);
  useEffect(() => {
    (async () => {
      const t = getCookie('access_token');
      if (t) {
        const r = await apiClient.get('/users/me');
        if (r.success && r.data) { window.location.href = new URLSearchParams(window.location.search).get('next')||'/profile'; return; }
      }
      setChecking(false);
    })();
  }, []);

  const next = () => new URLSearchParams(window.location.search).get('next')||'/profile';

  // QR login simulation
  useEffect(() => {
    if (mode !== 'qrcode') return;
    const sessionId = 'qr_' + Date.now();
    const loginUrl = `${window.location.origin}/login?qr_session=${sessionId}`;
    import('qrcode').then(mod => {
      mod.toDataURL(loginUrl, {width:280,margin:2,color:{dark:'#1e40af',light:'#ffffff'}}).then(setQrDataUrl);
    });
    // Poll simulation — in production this polls a backend endpoint
    qrTimer.current = setTimeout(() => {
      setErr('扫码登录需要后端支持，目前仅作界面演示');
    }, 5000);
    return () => clearTimeout(qrTimer.current);
  }, [mode]);

  const login = async (e: React.FormEvent) => {
    e.preventDefault(); setBusy(true); setErr('');
    try {
      const r = await apiClient.postForm('/auth/login', {username: u, password: pw, remember_me: rm});
      if (!r.success) { setErr(r.error||r.message||'登录失败'); setBusy(false); return; }
      const d = r.data as any;
      if (d.requires_2fa && d.temp_token) { setFa({tempToken:d.temp_token, userId:d.user_id}); setBusy(false); return; }
      if (d.access_token) setCookie('access_token', d.access_token, 3600);
      if (d.refresh_token) setCookie('refresh_token', d.refresh_token, 604800);
      window.location.href = next();
    } catch { setErr('网络异常'); setBusy(false); }
  };

  const verify2FA = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!fa || code.length < 6) { setErr('请输入验证码'); return; }
    setBusy(true); setErr('');
    try {
      const r = await apiClient.post('/security/2fa/verify-login', {user_id: fa.userId, token: code});
      if (r.success && r.data) {
        const d = r.data as any;
        if (d.access_token) setCookie('access_token', d.access_token, 3600);
        if (d.refresh_token) setCookie('refresh_token', d.refresh_token, 604800);
        window.location.href = next();
      } else setErr(r.error||'验证失败');
    } catch { setErr('验证失败'); } finally { setBusy(false); }
  };

  if (checking) return <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-gray-950 dark:to-gray-900"><div className="animate-spin w-6 h-6 border-2 border-blue-600 border-t-transparent rounded-full"/></div>;

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-gray-950 dark:to-gray-900 p-4">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="w-14 h-14 mx-auto mb-4 bg-gradient-to-br from-blue-600 to-indigo-600 rounded-2xl flex items-center justify-center shadow-lg shadow-blue-200/50 dark:shadow-blue-900/30">
            <LogIn className="w-7 h-7 text-white"/>
          </div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">{fa ? '验证身份' : '欢迎回来'}</h1>
          <p className="text-sm text-gray-500 mt-1">{fa ? '请输入双重验证码' : '登录你的账户继续'}</p>
        </div>

        {err && <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl text-sm text-red-600 dark:text-red-400">{err}</div>}

        {/* 2FA step */}
        {fa ? (
          <form onSubmit={verify2FA} className="bg-white dark:bg-gray-900 rounded-2xl p-6 shadow-xl border border-gray-100 dark:border-gray-800 space-y-4">
            <div className="text-center">
              <div className="w-14 h-14 mx-auto mb-3 bg-indigo-50 dark:bg-indigo-900/30 rounded-full flex items-center justify-center">
                <Smartphone className="w-7 h-7 text-indigo-600"/>
              </div>
              <p className="text-sm text-gray-500">{backup ? '输入8位备用码' : '输入认证器中的6位验证码'}</p>
            </div>
            <input type="text" inputMode="numeric" autoFocus value={code} onChange={e=>setCode(e.target.value.replace(/\D/g,'').slice(0,backup?8:6))}
              placeholder={backup ? '备用码' : '000000'}
              className="w-full text-center text-3xl tracking-[0.4em] px-4 py-4 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white font-mono"/>
            <button type="submit" disabled={busy||code.length<(backup?8:6)}
              className="w-full py-3 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white font-medium rounded-xl transition-all disabled:opacity-50 shadow-lg shadow-blue-200/30">
              {busy ? '验证中...' : '验证'}
            </button>
            <button type="button" onClick={()=>setBackup(!backup)} className="w-full text-sm text-blue-600 hover:text-blue-700 font-medium">{backup ? '使用验证码' : '使用备用码'}</button>
            <button type="button" onClick={()=>setFa(null)} className="flex items-center justify-center gap-1 w-full text-sm text-gray-500 hover:text-gray-700"><ArrowLeft className="w-4 h-4"/>返回登录</button>
          </form>
        ) : (
          <>
            {/* Mode switch tabs */}
            <div className="flex bg-white/60 dark:bg-gray-800/60 backdrop-blur-sm rounded-xl p-1 border border-gray-200/60 dark:border-gray-700/60 mb-4">
              <button onClick={()=>setMode('password')} className={`flex-1 py-2.5 rounded-lg text-sm font-medium transition-all ${mode==='password' ? 'bg-white dark:bg-gray-700 shadow-sm text-gray-900 dark:text-white' : 'text-gray-500 hover:text-gray-700'}`}><LogIn className="w-4 h-4 inline mr-1.5"/>密码登录</button>
              <button onClick={()=>setMode('qrcode')} className={`flex-1 py-2.5 rounded-lg text-sm font-medium transition-all ${mode==='qrcode' ? 'bg-white dark:bg-gray-700 shadow-sm text-gray-900 dark:text-white' : 'text-gray-500 hover:text-gray-700'}`}><QrCode className="w-4 h-4 inline mr-1.5"/>扫码登录</button>
            </div>

            {/* Password mode */}
            {mode === 'password' && (
              <form onSubmit={login} className="bg-white dark:bg-gray-900 rounded-2xl p-6 shadow-xl border border-gray-100 dark:border-gray-800 space-y-4">
                <input type="text" value={u} onChange={e=>setU(e.target.value)} placeholder="用户名或邮箱" required autoFocus
                  className="w-full px-4 py-3 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white"/>
                <div className="relative">
                  <input type={pv?'text':'password'} value={pw} onChange={e=>setPw(e.target.value)} placeholder="密码" required
                    className="w-full px-4 py-3 pr-11 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white"/>
                  <button type="button" onClick={()=>setPv(!pv)} className="absolute right-3.5 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600">{pv ? <EyeOff className="w-4 h-4"/> : <Eye className="w-4 h-4"/>}</button>
                </div>
                <div className="flex items-center justify-between">
                  <label className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400 cursor-pointer">
                    <input type="checkbox" checked={rm} onChange={e=>setRm(e.target.checked)} className="h-4 w-4 text-blue-600 rounded border-gray-300"/>记住我
                  </label>
                </div>
                <button type="submit" disabled={busy||!u||!pw}
                  className="w-full py-3 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white font-medium rounded-xl transition-all disabled:opacity-60 shadow-lg shadow-blue-200/30">
                  {busy ? '登录中...' : '登录'}
                </button>
              </form>
            )}

            {/* QR mode */}
            {mode === 'qrcode' && (
              <div className="bg-white dark:bg-gray-900 rounded-2xl p-6 shadow-xl border border-gray-100 dark:border-gray-800">
                <div className="text-center space-y-4">
                  <p className="text-sm text-gray-600 dark:text-gray-400">使用手机扫描二维码登录</p>
                  <div className="flex justify-center">
                    {qrDataUrl ? (
                      <div className="p-3 bg-white rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm">
                        <img src={qrDataUrl} alt="Login QR Code" className="w-[200px] h-[200px]"/>
                      </div>
                    ) : (
                      <div className="w-[200px] h-[200px] bg-gray-50 dark:bg-gray-800 rounded-xl animate-pulse flex items-center justify-center text-gray-400 text-sm">生成中...</div>
                    )}
                  </div>
                  <p className="text-xs text-gray-400">打开手机 App → 扫码 → 确认登录</p>
                  <p className="text-xs text-amber-500 bg-amber-50 dark:bg-amber-900/20 rounded-lg p-2">当前为演示界面，请使用密码登录</p>
                </div>
              </div>
            )}
          </>
        )}

        {/* Only show footer when not in 2FA */}
        {!fa && (
          <div className="mt-6">
            <div className="flex items-center gap-3 mb-4"><div className="flex-1 h-px bg-gray-200 dark:bg-gray-800"/><span className="text-xs text-gray-400">或</span><div className="flex-1 h-px bg-gray-200 dark:bg-gray-800"/></div>
            <div className="grid grid-cols-2 gap-3 mb-6">
              <button className="py-2.5 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-xl text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors shadow-sm">Google</button>
              <button className="py-2.5 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-xl text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors shadow-sm">GitHub</button>
            </div>
            <p className="text-center text-sm text-gray-500">还没有账户？<a href="/register" className="text-blue-600 hover:underline font-medium">立即注册</a></p>
          </div>
        )}
      </div>
    </div>
  );
}
