'use client';

import React, {useState} from 'react';
import {apiClient} from '@/lib/api';
import {UserPlus, Eye, EyeOff, Check} from 'lucide-react';

export default function RegisterPage() {
  const [step, setStep] = useState(0);
  const [f, setF] = useState({username:'', email:'', password:'', confirm:'', locale:'zh_CN', terms:false});
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');
  const [pv, setPv] = useState(false);
  const [uOk, setUOk] = useState<boolean|null>(null);
  const [eOk, setEOk] = useState<boolean|null>(null);

  const u = (field: string, val: any) => setF(p => ({...p, [field]: val}));

  const checkU = async () => {
    if (f.username.length < 3) { setUOk(false); return; }
    try { const r = await apiClient.get(`/auth/check-username?username=${f.username}`); setUOk(!(r as any).exists); }
    catch { setUOk(false); }
  };
  const checkE = async () => {
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(f.email)) { setEOk(false); return; }
    try { const r = await apiClient.get(`/auth/check-email?email=${f.email}`); setEOk(!(r as any).exists); }
    catch { setEOk(false); }
  };

  const next = async () => {
    if (step === 0) { await checkU(); await checkE(); if (uOk && eOk) setStep(1); return; }
    if (step === 1) { if (f.password !== f.confirm) {setErr('密码不匹配');return;} setStep(2); }
  };

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!f.terms) { setErr('请同意条款'); return; }
    setBusy(true); setErr('');
    try {
      const r = await apiClient.postForm('/auth/register', {username: f.username, email: f.email, password: f.password});
      if (r?.success) {
        const d = r.data as any;
        if (d?.access_token) {
          document.cookie = `access_token=${d.access_token}; path=/; max-age=3600; SameSite=Lax`;
          window.location.href = '/profile';
        } else window.location.href = '/login?registered=true';
      } else setErr(r?.error || r?.message || '注册失败');
    } catch { setErr('网络错误'); } finally { setBusy(false); }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-gray-950 dark:to-gray-900 p-4">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <div className="w-12 h-12 mx-auto mb-4 bg-gradient-to-br from-blue-600 to-indigo-600 rounded-2xl flex items-center justify-center shadow-lg shadow-blue-200 dark:shadow-blue-900/30">
            <UserPlus className="w-6 h-6 text-white"/>
          </div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">创建账户</h1>
          <p className="text-sm text-gray-500 mt-1">加入我们</p>
        </div>

        {err && <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl text-sm text-red-600">{err}</div>}

        {/* Steps indicator */}
        <div className="flex gap-1.5 mb-6 justify-center">
          {[0,1,2].map(i => (
            <div key={i} className={`w-8 h-1.5 rounded-full transition-colors ${i <= step ? 'bg-blue-600' : 'bg-gray-200 dark:bg-gray-700'}`}/>
          ))}
        </div>

        <form onSubmit={submit} className="bg-white dark:bg-gray-900 rounded-2xl p-6 shadow-xl shadow-gray-200/50 dark:shadow-black/20 border border-gray-100 dark:border-gray-800 space-y-4">
          {/* Step 0: Basic */}
          {step === 0 && <>
            <div>
              <input type="text" value={f.username} onChange={e=>{u('username',e.target.value);setUOk(null)}} onBlur={checkU}
                placeholder="用户名" className="w-full px-4 py-3 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white"/>
              {uOk !== null && <p className={`text-xs mt-1 ${uOk ? 'text-green-600' : 'text-red-500'}`}>{uOk ? '可用' : '不可用或已存在'}</p>}
            </div>
            <div>
              <input type="email" value={f.email} onChange={e=>{u('email',e.target.value);setEOk(null)}} onBlur={checkE}
                placeholder="邮箱地址" className="w-full px-4 py-3 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white"/>
              {eOk !== null && <p className={`text-xs mt-1 ${eOk ? 'text-green-600' : 'text-red-500'}`}>{eOk ? '可用' : '已被注册'}</p>}
            </div>
            <button type="button" onClick={next} className="w-full py-3 bg-gradient-to-r from-blue-600 to-indigo-600 text-white font-medium rounded-xl hover:from-blue-700 hover:to-indigo-700 transition-all shadow-lg shadow-blue-200">下一步</button>
          </>}

          {/* Step 1: Password */}
          {step === 1 && <>
            <div className="relative">
              <input type={pv?'text':'password'} value={f.password} onChange={e=>u('password',e.target.value)}
                placeholder="密码 (至少8位)" className="w-full px-4 py-3 pr-10 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white"/>
              <button type="button" onClick={()=>setPv(!pv)} className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400">{pv ? <EyeOff className="w-4 h-4"/> : <Eye className="w-4 h-4"/>}</button>
            </div>
            <div className="relative">
              <input type="password" value={f.confirm} onChange={e=>u('confirm',e.target.value)}
                placeholder="确认密码" className="w-full px-4 py-3 pr-10 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white"/>
              {f.confirm && <span className="absolute right-3 top-1/2 -translate-y-1/2 text-sm">{f.password===f.confirm ? <Check className="w-4 h-4 text-green-500"/> : '❌'}</span>}
            </div>
            <div className="flex gap-2">
              <button type="button" onClick={()=>setStep(0)} className="flex-1 py-3 border border-gray-200 dark:border-gray-700 rounded-xl text-sm font-medium hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">上一步</button>
              <button type="button" onClick={next} className="flex-1 py-3 bg-gradient-to-r from-blue-600 to-indigo-600 text-white font-medium rounded-xl hover:from-blue-700 hover:to-indigo-700 transition-all">下一步</button>
            </div>
          </>}

          {/* Step 2: Preferences */}
          {step === 2 && <>
            <select value={f.locale} onChange={e=>u('locale',e.target.value)}
              className="w-full px-4 py-3 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white">
              <option value="zh_CN">简体中文</option><option value="en_US">English</option>
            </select>
            <label className="flex items-start gap-2 cursor-pointer">
              <input type="checkbox" checked={f.terms} onChange={e=>u('terms',e.target.checked)} className="mt-0.5 h-4 w-4 text-blue-600 rounded border-gray-300"/>
              <span className="text-sm text-gray-600 dark:text-gray-400">我同意<a href="#" className="text-blue-600 hover:underline">服务条款</a>和<a href="#" className="text-blue-600 hover:underline">隐私政策</a></span>
            </label>
            <div className="flex gap-2">
              <button type="button" onClick={()=>setStep(1)} className="flex-1 py-3 border border-gray-200 dark:border-gray-700 rounded-xl text-sm font-medium hover:bg-gray-50 dark:hover:bg-gray-800">上一步</button>
              <button type="submit" disabled={busy||!f.terms}
                className="flex-1 py-3 bg-gradient-to-r from-green-600 to-emerald-600 text-white font-medium rounded-xl hover:from-green-700 hover:to-emerald-700 disabled:opacity-50 transition-all shadow-lg shadow-green-200">
                {busy ? '注册中...' : '创建账户'}
              </button>
            </div>
          </>}
        </form>

        <p className="text-center text-sm text-gray-500 mt-6">已有账户？<a href="/login" className="text-blue-600 hover:underline font-medium">登录</a></p>
      </div>
    </div>
  );
}
