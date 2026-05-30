'use client';

import React, {useEffect, useRef, useState} from 'react';
import {apiClient} from '@/lib/api/api-client';
import {getAccessTokenFromCookie, getCookie, setCookie} from '@/lib/auth-utils';
import {
  ArrowLeft,
  Eye,
  EyeOff,
  Loader,
  LogIn,
  QrCode,
  Smartphone,
  Mail,
  Lock,
  User,
  GitBranch,
  Globe,
  Shield,
  Sparkles,
  Zap,
  BookOpen,
  ChevronRight,
  AlertCircle
} from 'lucide-react';

const features = [
  {icon: Sparkles, title: 'AI 智能写作', desc: 'AI 辅助创作，灵感永不枯竭'},
  {icon: Zap, title: '极速发布', desc: '一键多平台同步，触达全球读者'},
  {icon: BookOpen, title: '沉浸阅读', desc: '精心设计的阅读体验，专注内容'},
  {icon: Shield, title: '安全可靠', desc: '端到端加密，数据安全无忧'},
];

export default function LoginPage() {
  const [mode, setMode] = useState<'password'|'qrcode'>('password');
  const [u, setU] = useState(''); const [pw, setPw] = useState(''); const [rm, setRm] = useState(false);
  const [pv, setPv] = useState(false); const [err, setErr] = useState(''); const [busy, setBusy] = useState(false);
  const [focusedField, setFocusedField] = useState<string | null>(null);

  // 2FA
  const [fa, setFa] = useState<{tempToken:string;userId:number}|null>(null);
  const [code, setCode] = useState(''); const [backup, setBackup] = useState(false);

  // QR code
  const [qrImg, setQrImg] = useState(''); const [qrToken, setQrToken] = useState('');
  const [qrStatus, setQrStatus] = useState<'idle'|'loading'|'ready'|'pending'|'success'|'expired'>('idle');
  const pollRef = useRef<NodeJS.Timeout | undefined>(undefined);
  const cancelRef = useRef(false);

  // Auto-redirect if logged in
  const [checking, setChecking] = useState(true);
  useEffect(() => {(async()=>{const t=getCookie('access_token');if(t){const r=await apiClient.get('/users/me');if(r.success&&r.data){window.location.href=new URLSearchParams(window.location.search).get('next')||'/profile';return;}}setChecking(false);})();},[]);

  const next = () => new URLSearchParams(window.location.search).get('next')||'/profile';

  // Cleanup polling
  useEffect(() => { return () => { cancelRef.current = true; if (pollRef.current) clearTimeout(pollRef.current); }; }, []);

  // ═══ QR Login Generator (uses V2 backend) ═══
  const generateQR = async () => {
    setErr(''); setQrStatus('loading'); setQrImg(''); setQrToken(''); cancelRef.current = false;
    try {
      const r = await apiClient.get<any>('/auth/qr/generate');
      if (!r.success || !r.data) { setErr(r.error || '生成二维码失败'); setQrStatus('idle'); return; }
      const token = r.data.token || r.data.qr_token;
      const qrCodeDataUrl = r.data.qr_code || r.data.qr_data;
      setQrToken(token);
      if (qrCodeDataUrl && qrCodeDataUrl.startsWith('data:')) {
        setQrImg(qrCodeDataUrl);
      } else {
        try {
          const mod = await import('qrcode');
          const loginUrl = `${window.location.origin}/mobile-login?login_token=${token}`;
          const dataUrl = await mod.toDataURL(loginUrl, {width:280,margin:2,color:{dark:'#1e40af',light:'#ffffff'}});
          setQrImg(dataUrl);
        } catch { setErr('生成二维码失败'); setQrStatus('idle'); return; }
      }
      setQrStatus('ready');
      pollQR(token);
    } catch { setErr('生成二维码失败'); setQrStatus('idle'); }
  };

  const pollQR = (token: string) => {
    if (cancelRef.current) return;
    pollRef.current = setTimeout(async () => {
      if (cancelRef.current) return;
      try {
        const r = await apiClient.get<any>(`/auth/qr/status`, {token});
        const data = r.success && r.data ? r.data : {status: 'pending'};
        const st = data.status;
        if (st === 'confirmed' || st === 'success') {
          setQrStatus('success');
          const refreshToken = data.refresh_token;
          if (refreshToken) setCookie('refresh_token', refreshToken, 604800);
          const accessR = await apiClient.post('/auth/token/refresh', {refresh: refreshToken});
          if (accessR.success && accessR.data) {
            setCookie('access_token', (accessR.data as any).access_token || (accessR.data as any).access || '', 3600);
            window.location.href = next();
            return;
          }
          setErr('扫码成功，获取令牌失败'); setQrStatus('idle'); return;
        } else if (st === 'expired') {
          setQrStatus('expired'); setErr('二维码已过期，请重新生成'); return;
        } else {
          setQrStatus('pending');
          pollQR(token);
        }
      } catch {
        if (!cancelRef.current) pollQR(token);
      }
    }, 2000);
  };

  // ═══ Password Login ═══
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

  // ═══ 2FA ═══
  const verify2FA = async (e: React.FormEvent) => {
    e.preventDefault(); if (!fa || code.length < 6) { setErr('请输入验证码'); return; }
    setBusy(true); setErr('');
    try {
      const r = await apiClient.post('/security/2fa/verify-login', {user_id: fa.userId, token: code});
      if (r.success && r.data) {
        const d = r.data as any; if (d.access_token) setCookie('access_token', d.access_token, 3600);
        if (d.refresh_token) setCookie('refresh_token', d.refresh_token, 604800);
        window.location.href = next();
      } else setErr(r.error||'验证失败');
    } catch { setErr('验证失败'); } finally { setBusy(false); }
  };

  if (checking) return (
      <div
          className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50 dark:from-gray-950 dark:via-gray-900 dark:to-gray-950">
        <div className="flex flex-col items-center gap-4">
          <div className="relative">
            <div className="w-12 h-12 border-4 border-blue-200 dark:border-blue-800 rounded-full animate-spin"/>
            <div
                className="absolute inset-0 w-12 h-12 border-4 border-transparent border-t-blue-600 rounded-full animate-spin"/>
          </div>
          <p className="text-sm text-gray-500 dark:text-gray-400 animate-pulse">正在验证登录状态...</p>
        </div>
      </div>
  );

  return (
      <div
          className="min-h-screen flex bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50 dark:from-gray-950 dark:via-gray-900 dark:to-gray-950">
        {/* ═══ Left Panel - Branding ═══ */}
        <div className="hidden lg:flex lg:w-1/2 xl:w-[45%] relative overflow-hidden">
          {/* Gradient Background */}
          <div className="absolute inset-0 bg-gradient-to-br from-blue-600 via-indigo-600 to-purple-700"/>

          {/* Animated Orbs */}
          <div className="absolute inset-0 overflow-hidden">
            <div className="absolute -top-20 -left-20 w-80 h-80 bg-blue-400/20 rounded-full blur-3xl animate-pulse"
                 style={{animationDuration: '4s'}}/>
            <div className="absolute bottom-20 right-10 w-60 h-60 bg-purple-400/20 rounded-full blur-3xl animate-pulse"
                 style={{animationDuration: '6s'}}/>
            <div className="absolute top-1/3 left-1/3 w-40 h-40 bg-indigo-400/20 rounded-full blur-3xl animate-pulse"
                 style={{animationDuration: '5s'}}/>
          </div>

          {/* Grid Pattern */}
          <div className="absolute inset-0 opacity-10" style={{
            backgroundImage: 'radial-gradient(circle at 1px 1px, white 1px, transparent 0)',
            backgroundSize: '40px 40px'
          }}/>

          {/* Content */}
          <div className="relative z-10 flex flex-col justify-between p-12 xl:p-16 w-full">
            {/* Logo & Brand */}
            <div>
              <div className="flex items-center gap-3 mb-2">
                <div className="w-10 h-10 bg-white/20 backdrop-blur-sm rounded-xl flex items-center justify-center">
                  <BookOpen className="w-5 h-5 text-white"/>
                </div>
                <span className="text-xl font-bold text-white">FastBlog</span>
              </div>
            </div>

            {/* Main Content */}
            <div className="space-y-8">
              <div>
                <h2 className="text-3xl xl:text-4xl font-bold text-white leading-tight mb-4">
                  创作、分享、<br/>连接世界
                </h2>
                <p className="text-blue-100/80 text-lg leading-relaxed max-w-md">
                  FastBlog 是新一代智能博客平台，让每位创作者都能轻松表达思想、分享知识、与全球读者建立连接。
                </p>
              </div>

              {/* Features */}
              <div className="grid grid-cols-2 gap-4">
                {features.map((feat, i) => {
                  const Icon = feat.icon;
                  return (
                      <div key={i}
                           className="group p-4 rounded-2xl bg-white/10 backdrop-blur-sm border border-white/10 hover:bg-white/15 transition-all duration-300">
                        <Icon className="w-6 h-6 text-blue-200 mb-3 group-hover:scale-110 transition-transform"/>
                        <h3 className="text-sm font-semibold text-white mb-1">{feat.title}</h3>
                        <p className="text-xs text-blue-100/70 leading-relaxed">{feat.desc}</p>
                      </div>
                  );
                })}
              </div>
            </div>

            {/* Bottom Stats */}
            <div className="flex items-center gap-8">
              <div>
                <div className="text-2xl font-bold text-white">50K+</div>
                <div className="text-sm text-blue-100/70">活跃创作者</div>
              </div>
              <div className="w-px h-10 bg-white/20"/>
              <div>
                <div className="text-2xl font-bold text-white">1M+</div>
                <div className="text-sm text-blue-100/70">优质文章</div>
              </div>
              <div className="w-px h-10 bg-white/20"/>
              <div>
                <div className="text-2xl font-bold text-white">100+</div>
                <div className="text-sm text-blue-100/70">国家地区</div>
              </div>
          </div>
          </div>
        </div>

        {/* ═══ Right Panel - Login Form ═══ */}
        <div className="flex-1 flex items-center justify-center p-6 sm:p-8 lg:p-12">
          <div className="w-full max-w-md">
            {/* Mobile Logo */}
            <div className="lg:hidden flex items-center gap-3 mb-8">
              <div
                  className="w-10 h-10 bg-gradient-to-br from-blue-600 to-indigo-600 rounded-xl flex items-center justify-center shadow-lg shadow-blue-200/50 dark:shadow-blue-900/30">
                <BookOpen className="w-5 h-5 text-white"/>
              </div>
              <span className="text-xl font-bold text-gray-900 dark:text-white">FastBlog</span>
            </div>

            {/* Header */}
            <div className="mb-8">
              <h1 className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-white mb-2">
                {fa ? '🔐 验证身份' : mode === 'qrcode' ? '📱 扫码登录' : '👋 欢迎回来'}
              </h1>
              <p className="text-gray-500 dark:text-gray-400">
                {fa ? '请输入双重验证码以继续' : mode === 'qrcode' ? '使用 FastBlog App 扫描二维码' : '登录你的账户，继续创作之旅'}
              </p>
            </div>

            {/* Error Message */}
            {err && (
                <div
                    className="mb-6 flex items-start gap-3 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200/60 dark:border-red-800/40 rounded-2xl text-sm">
                  <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5"/>
                  <span className="text-red-600 dark:text-red-400">{err}</span>
                </div>
            )}

            {/* 2FA Form */}
            {fa ? (
                <div className="space-y-6">
                  <div
                      className="text-center p-6 bg-gradient-to-br from-indigo-50 to-blue-50 dark:from-indigo-900/20 dark:to-blue-900/20 rounded-2xl border border-indigo-100 dark:border-indigo-800/30">
                    <div
                        className="w-16 h-16 mx-auto mb-4 bg-gradient-to-br from-indigo-500 to-blue-500 rounded-2xl flex items-center justify-center shadow-lg">
                      <Smartphone className="w-8 h-8 text-white"/>
                    </div>
                    <p className="text-sm text-gray-600 dark:text-gray-400">
                      {backup ? '输入你的8位备用恢复码' : '打开认证器应用，输入6位验证码'}
                    </p>
                  </div>

                  <form onSubmit={verify2FA} className="space-y-4">
                    <div className="relative">
                      <input
                          type="text"
                          inputMode="numeric"
                          autoFocus
                          value={code}
                          onChange={e => setCode(e.target.value.replace(/\D/g, '').slice(0, backup ? 8 : 6))}
                          placeholder={backup ? '输入备用码' : '000000'}
                          className="w-full text-center text-3xl tracking-[0.5em] px-6 py-5 bg-white dark:bg-gray-800 border-2 border-gray-200 dark:border-gray-700 rounded-2xl focus:outline-none focus:border-indigo-500 focus:ring-4 focus:ring-indigo-500/10 dark:text-white font-mono transition-all"
                      />
                    </div>

                    <button
                        type="submit"
                        disabled={busy || code.length < (backup ? 8 : 6)}
                        className="w-full py-4 bg-gradient-to-r from-indigo-600 to-blue-600 hover:from-indigo-700 hover:to-blue-700 text-white font-semibold rounded-2xl transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-indigo-500/25 hover:shadow-xl hover:shadow-indigo-500/30 active:scale-[0.98]"
                    >
                      {busy ? (
                          <span className="flex items-center justify-center gap-2">
                      <Loader className="w-5 h-5 animate-spin"/> 验证中...
                    </span>
                      ) : '验证'}
                    </button>

                    <div className="flex items-center justify-between pt-2">
                      <button type="button" onClick={() => setBackup(!backup)}
                              className="text-sm text-indigo-600 hover:text-indigo-700 dark:text-indigo-400 font-medium">
                        {backup ? '使用验证码' : '使用备用码'}
                      </button>
                      <button type="button" onClick={() => {
                        setFa(null);
                        setCode('');
                        setErr('');
                      }}
                              className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 dark:hover:text-gray-300">
                        <ArrowLeft className="w-4 h-4"/> 返回登录
                      </button>
                    </div>
                  </form>
                </div>
            ) : (
                <>
                  {/* Mode Switch */}
                  <div className="flex p-1.5 bg-gray-100 dark:bg-gray-800 rounded-2xl mb-6">
                    <button
                        onClick={() => {
                          setMode('password');
                          setErr('');
                        }}
                        className={`flex-1 flex items-center justify-center gap-2 py-3 rounded-xl text-sm font-semibold transition-all duration-200 ${
                            mode === 'password'
                                ? 'bg-white dark:bg-gray-700 shadow-sm text-gray-900 dark:text-white'
                                : 'text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'
                        }`}
                    >
                      <Lock className="w-4 h-4"/> 密码登录
                    </button>
                    <button
                        onClick={() => {
                          setMode('qrcode');
                          setErr('');
                          if (!qrImg) generateQR();
                        }}
                        className={`flex-1 flex items-center justify-center gap-2 py-3 rounded-xl text-sm font-semibold transition-all duration-200 ${
                            mode === 'qrcode'
                                ? 'bg-white dark:bg-gray-700 shadow-sm text-gray-900 dark:text-white'
                                : 'text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'
                        }`}
                    >
                      <QrCode className="w-4 h-4"/> 扫码登录
                    </button>
                  </div>

                  {/* Password Form */}
                  {mode === 'password' && (
                      <form onSubmit={login} className="space-y-5">
                        {/* Username Field */}
                        <div className="space-y-2">
                          <label className="text-sm font-medium text-gray-700 dark:text-gray-300">用户名 / 邮箱</label>
                          <div
                              className={`relative group transition-all duration-200 ${focusedField === 'username' ? 'scale-[1.01]' : ''}`}>
                            <div className="absolute left-4 top-1/2 -translate-y-1/2">
                              <User
                                  className={`w-5 h-5 transition-colors ${focusedField === 'username' ? 'text-blue-500' : 'text-gray-400'}`}/>
                            </div>
                            <input
                                type="text"
                                value={u}
                                onChange={e => setU(e.target.value)}
                                onFocus={() => setFocusedField('username')}
                                onBlur={() => setFocusedField(null)}
                                placeholder="输入用户名或邮箱"
                                required
                                autoFocus
                                className="w-full pl-12 pr-4 py-4 bg-white dark:bg-gray-800 border-2 border-gray-200 dark:border-gray-700 rounded-2xl text-sm text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-500/10 transition-all"
                            />
                          </div>
                        </div>

                        {/* Password Field */}
                        <div className="space-y-2">
                          <div className="flex items-center justify-between">
                            <label className="text-sm font-medium text-gray-700 dark:text-gray-300">密码</label>
                            <a href="/forgot-password"
                               className="text-xs text-blue-600 hover:text-blue-700 dark:text-blue-400 font-medium">
                              忘记密码？
                            </a>
                          </div>
                          <div
                              className={`relative group transition-all duration-200 ${focusedField === 'password' ? 'scale-[1.01]' : ''}`}>
                            <div className="absolute left-4 top-1/2 -translate-y-1/2">
                              <Lock
                                  className={`w-5 h-5 transition-colors ${focusedField === 'password' ? 'text-blue-500' : 'text-gray-400'}`}/>
                            </div>
                            <input
                                type={pv ? 'text' : 'password'}
                                value={pw}
                                onChange={e => setPw(e.target.value)}
                                onFocus={() => setFocusedField('password')}
                                onBlur={() => setFocusedField(null)}
                                placeholder="输入密码"
                                required
                                className="w-full pl-12 pr-12 py-4 bg-white dark:bg-gray-800 border-2 border-gray-200 dark:border-gray-700 rounded-2xl text-sm text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-500/10 transition-all"
                            />
                            <button
                                type="button"
                                onClick={() => setPv(!pv)}
                                className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
                            >
                              {pv ? <EyeOff className="w-5 h-5"/> : <Eye className="w-5 h-5"/>}
                            </button>
                          </div>
                        </div>

                        {/* Remember Me */}
                        <label className="flex items-center gap-3 cursor-pointer group">
                          <div className="relative">
                            <input
                                type="checkbox"
                                checked={rm}
                                onChange={e => setRm(e.target.checked)}
                                className="peer sr-only"
                            />
                            <div
                                className="w-5 h-5 border-2 border-gray-300 dark:border-gray-600 rounded-lg peer-checked:border-blue-500 peer-checked:bg-blue-500 transition-all flex items-center justify-center">
                              {rm && (
                                  <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24"
                                       stroke="currentColor" strokeWidth={3}>
                                    <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7"/>
                                  </svg>
                              )}
                            </div>
                          </div>
                          <span
                              className="text-sm text-gray-600 dark:text-gray-400 group-hover:text-gray-800 dark:group-hover:text-gray-200 transition-colors">
                      记住我的登录状态
                    </span>
                        </label>

                        {/* Submit Button */}
                        <button
                            type="submit"
                            disabled={busy || !u || !pw}
                            className="w-full py-4 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white font-semibold rounded-2xl transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-blue-500/25 hover:shadow-xl hover:shadow-blue-500/30 active:scale-[0.98] flex items-center justify-center gap-2"
                        >
                          {busy ? (
                              <>
                                <Loader className="w-5 h-5 animate-spin"/>
                                <span>登录中...</span>
                              </>
                          ) : (
                              <>
                                <span>登录</span>
                                <ChevronRight className="w-5 h-5"/>
                              </>
                          )}
                        </button>

                        {/* Divider */}
                        <div className="relative flex items-center py-2">
                          <div className="flex-1 border-t border-gray-200 dark:border-gray-700"/>
                          <span
                              className="px-4 text-xs text-gray-400 dark:text-gray-500 font-medium">或使用其他方式</span>
                          <div className="flex-1 border-t border-gray-200 dark:border-gray-700"/>
                        </div>

                        {/* Social Login */}
                        <div className="grid grid-cols-2 gap-3">
                          <button
                              type="button"
                              className="flex items-center justify-center gap-2 py-3.5 bg-white dark:bg-gray-800 border-2 border-gray-200 dark:border-gray-700 rounded-2xl text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-750 hover:border-gray-300 dark:hover:border-gray-600 transition-all active:scale-[0.98]"
                          >
                            <GitBranch className="w-5 h-5"/> GitHub
                          </button>
                          <button
                              type="button"
                              className="flex items-center justify-center gap-2 py-3.5 bg-white dark:bg-gray-800 border-2 border-gray-200 dark:border-gray-700 rounded-2xl text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-750 hover:border-gray-300 dark:hover:border-gray-600 transition-all active:scale-[0.98]"
                          >
                            <Globe className="w-5 h-5"/> Google
                          </button>
                        </div>

                        {/* Register Link */}
                        <p className="text-center text-sm text-gray-500 dark:text-gray-400 pt-2">
                          还没有账户？{' '}
                          <a href="/register"
                             className="text-blue-600 hover:text-blue-700 dark:text-blue-400 font-semibold hover:underline">
                            立即注册
                          </a>
                        </p>
                      </form>
                  )}

                  {/* QR Code Panel */}
                  {mode === 'qrcode' && (
                      <div className="space-y-6">
                        <div
                            className="bg-white dark:bg-gray-800 rounded-3xl p-8 border border-gray-100 dark:border-gray-700 shadow-sm">
                          <div className="text-center space-y-5">
                            {/* QR Display */}
                            <div className="flex justify-center">
                              {qrStatus === 'loading' ? (
                                  <div
                                      className="w-[220px] h-[220px] bg-gray-50 dark:bg-gray-900 rounded-2xl animate-pulse flex items-center justify-center">
                                    <div className="flex flex-col items-center gap-3">
                                      <Loader className="w-8 h-8 animate-spin text-blue-500"/>
                                      <span className="text-sm text-gray-400">生成中...</span>
                                    </div>
                                  </div>
                              ) : qrImg ? (
                                  <div className="relative p-4 bg-white rounded-2xl border-2 border-gray-100 shadow-lg">
                                    <img src={qrImg} alt="Login QR Code" className="w-[200px] h-[200px]"/>
                                    {qrStatus === 'success' && (
                                        <div
                                            className="absolute inset-0 bg-green-500/90 rounded-2xl flex items-center justify-center">
                                          <svg className="w-16 h-16 text-white" fill="none" viewBox="0 0 24 24"
                                               stroke="currentColor" strokeWidth={2.5}>
                                            <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7"/>
                                          </svg>
                                        </div>
                                    )}
                                  </div>
                              ) : (
                                  <div
                                      className="w-[220px] h-[220px] bg-gray-50 dark:bg-gray-900 rounded-2xl border-2 border-dashed border-gray-200 dark:border-gray-700 flex flex-col items-center justify-center gap-3 cursor-pointer hover:border-blue-300 dark:hover:border-blue-700 transition-colors"
                                      onClick={generateQR}>
                                    <QrCode className="w-10 h-10 text-gray-300 dark:text-gray-600"/>
                                    <span className="text-sm text-gray-400">点击生成二维码</span>
                                  </div>
                              )}
                            </div>

                            {/* Status Text */}
                            <div className="space-y-2">
                              <p className="text-sm font-medium text-gray-700 dark:text-gray-300">
                                {qrStatus === 'loading' ? '正在生成二维码...' :
                                    qrStatus === 'ready' || qrStatus === 'pending' ? (
                                            <span className="flex items-center justify-center gap-2">
                              <span className="w-2 h-2 bg-blue-500 rounded-full animate-pulse"/>
                              等待扫码确认...
                            </span>
                                        ) :
                                        qrStatus === 'success' ? '✅ 扫码成功！正在登录...' :
                                            qrStatus === 'expired' ? '⏰ 二维码已过期' :
                                                '使用 FastBlog App 扫描二维码'}
                              </p>
                            </div>

                            {/* Action Buttons */}
                            {(qrStatus === 'expired' || qrStatus === 'idle') && (
                                <button
                                    onClick={generateQR}
                                    className="px-6 py-3 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white text-sm font-semibold rounded-xl transition-all shadow-md hover:shadow-lg active:scale-[0.98]"
                                >
                                  {qrStatus === 'expired' ? '重新生成' : '生成二维码'}
                                </button>
                            )}
                          </div>
                        </div>

                        {/* Instructions */}
                        <div
                            className="bg-gray-50 dark:bg-gray-800/50 rounded-2xl p-5 border border-gray-100 dark:border-gray-800">
                          <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">扫码步骤</h3>
                          <ol className="space-y-2.5">
                            {['打开 FastBlog 手机应用', '进入"我的" → "扫一扫"', '扫描上方二维码', '在手机上确认登录'].map((step, i) => (
                                <li key={i}
                                    className="flex items-center gap-3 text-sm text-gray-600 dark:text-gray-400">
                          <span
                              className="w-6 h-6 bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0">
                            {i + 1}
                          </span>
                                  {step}
                                </li>
                            ))}
                          </ol>
                        </div>
                      </div>
                  )}
                </>
            )}

            {/* Footer */}
            <div className="mt-8 text-center">
              <p className="text-xs text-gray-400 dark:text-gray-500">
                登录即表示同意{' '}
                <a href="/terms" className="text-gray-500 dark:text-gray-400 hover:underline">服务条款</a>
                {' '}和{' '}
                <a href="/privacy" className="text-gray-500 dark:text-gray-400 hover:underline">隐私政策</a>
              </p>
            </div>
          </div>
      </div>
    </div>
  );
}
