/**
 * 注册页面 - 完整实现（4步注册向导）
 * 适配 Astro：使用 window.location 替代 next/navigation
 */

'use client';

import React, {useEffect, useState} from 'react';
import {apiClient} from '@/lib/api';

const RegisterPage: React.FC = () => {
  const [currentStep, setCurrentStep] = useState(1);
  const totalSteps = 4;
  const [form, setForm] = useState({
    username: '', email: '', password: '', confirmPassword: '',
    displayName: '', bio: '', location: '', website: '',
    profilePrivate: false, newsletter: false, marketingEmails: false, terms: false, locale: 'zh_CN'
  });
  const [loading, setLoading] = useState(false);
  const [passwordVisible, setPasswordVisible] = useState(false);
  const [usernameFeedback, setUsernameFeedback] = useState<{message: string; type: 'success'|'error'} | null>(null);
  const [emailFeedback, setEmailFeedback] = useState<{message: string; type: 'success'|'error'} | null>(null);
  const [confirmFeedback, setConfirmFeedback] = useState<{message: string; type: 'success'|'error'} | null>(null);
  const [strengthPercent, setStrengthPercent] = useState(0);
  const [strengthText, setStrengthText] = useState('');
  const [strengthColor, setStrengthColor] = useState('#ccc');
  const [reqs, setReqs] = useState({length: false, uppercase: false, lowercase: false, number: false, special: false});
  const [error, setError] = useState('');

  const progressPct = (currentStep / totalSteps) * 100;

  const update = (field: string, value: string | boolean) => setForm(f => ({...f, [field]: value}));

  // 密码强度检测
  useEffect(() => {
    if (!form.password) {
      setStrengthPercent(0); setStrengthText(''); setStrengthColor('#ccc');
      setReqs({length: false, uppercase: false, lowercase: false, number: false, special: false});
      return;
    }
    const r = {
      length: form.password.length >= 8,
      uppercase: /[A-Z]/.test(form.password),
      lowercase: /[a-z]/.test(form.password),
      number: /\d/.test(form.password),
      special: /[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>/?]/.test(form.password),
    };
    setReqs(r);
    const score = Object.values(r).filter(Boolean).length;
    if (score <= 2) {setStrengthPercent(25); setStrengthText('弱'); setStrengthColor('#ef4444');}
    else if (score <= 3) {setStrengthPercent(50); setStrengthText('中等'); setStrengthColor('#f59e0b');}
    else if (score <= 4) {setStrengthPercent(75); setStrengthText('强'); setStrengthColor('#3b82f6');}
    else {setStrengthPercent(100); setStrengthText('很强'); setStrengthColor('#10b981');}
  }, [form.password]);

  const checkUsername = async (username: string) => {
    if (username.length < 3) {setUsernameFeedback({message: '用户名至少需要3个字符', type: 'error'}); return false;}
    try {
        const res = await apiClient.get<any>(`/auth/check-username?username=${username}`);
      if ((res as any).exists) {setUsernameFeedback({message: '用户名已被使用', type: 'error'}); return false;}
      setUsernameFeedback({message: '用户名可用', type: 'success'}); return true;
    } catch {setUsernameFeedback({message: '检查用户名失败', type: 'error'}); return false;}
  };

  const checkEmail = async (email: string) => {
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {setEmailFeedback({message: '邮箱格式不正确', type: 'error'}); return false;}
    try {
        const res = await apiClient.get<any>(`/auth/check-email?email=${email}`);
      if ((res as any).exists) {setEmailFeedback({message: '邮箱已被注册', type: 'error'}); return false;}
      setEmailFeedback({message: '邮箱可用', type: 'success'}); return true;
    } catch {setEmailFeedback({message: '检查邮箱失败', type: 'error'}); return false;}
  };

  const handleNext = async () => {
    if (currentStep === 1) {
      const u = await checkUsername(form.username);
      const e = await checkEmail(form.email);
      if (!u || !e) return;
    } else if (currentStep === 2) {
      if (form.password !== form.confirmPassword) {
        setConfirmFeedback({message: '密码不匹配', type: 'error'}); return;
      }
      setConfirmFeedback({message: '密码匹配', type: 'success'});
    }
    setCurrentStep(s => s + 1);
  };

  const handlePrev = () => {if (currentStep > 1) setCurrentStep(s => s - 1);};

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.username || !form.email || !form.password) {setError('请填写必填字段'); return;}
    if (form.password !== form.confirmPassword) {setError('密码不匹配'); return;}
    if (!form.terms) {setError('请同意服务条款和隐私政策'); return;}
    setLoading(true); setError('');
    try {
        const res = await apiClient.postForm<any>('/auth/register', {
        username: form.username, email: form.email, password: form.password
      });
      if (res && res.success) {
        const d = res.data as any;
        if (d?.access_token) {
          const exp = new Date(); exp.setTime(exp.getTime() + 3600000);
          document.cookie = `access_token=${d.access_token}; expires=${exp.toUTCString()}; path=/; SameSite=Strict`;
          if (d.refresh_token) {
            const rexp = new Date(); rexp.setTime(rexp.getTime() + 604800000);
            document.cookie = `refresh_token=${d.refresh_token}; expires=${rexp.toUTCString()}; path=/; SameSite=Strict`;
          }
          window.location.href = '/profile';
        } else {
          window.location.href = '/login?registered=true';
        }
      } else {
        setError(res?.error || res?.message || '注册失败');
      }
    } catch (err: any) { setError(err.message || '网络错误，请稍后重试'); }
    finally { setLoading(false); }
  };

  return (
    <div className="w-full max-w-md mx-auto bg-white dark:bg-gray-800 rounded-xl shadow-md p-8">
      <div className="text-center mb-8">
        <div className="w-12 h-12 bg-indigo-600 rounded-lg flex items-center justify-center mx-auto mb-4">
          <svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z"/></svg>
        </div>
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white">创建新账户</h2>
        <p className="mt-2 text-sm text-gray-600 dark:text-gray-300">
          已有账户？<a href="/login" className="font-medium text-indigo-600 hover:text-indigo-500">立即登录</a>
        </p>
      </div>

      {/* 进度条 */}
      <div className="mb-6">
        <div className="flex justify-between text-xs font-medium text-indigo-600 mb-2">
          <span>注册进度</span><span>{currentStep}/{totalSteps}</span>
        </div>
        <div className="w-full bg-gray-200 dark:bg-gray-600 rounded-full h-2">
          <div className="bg-indigo-600 h-2 rounded-full transition-all" style={{width: `${progressPct}%`}} />
        </div>
      </div>

      {error && <div className="mb-4 p-3 bg-red-100 border border-red-400 text-red-700 rounded-md text-sm">{error}</div>}

      <form onSubmit={handleRegister}>
        {/* Step 1: 基本信息 */}
        {currentStep === 1 && (
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">用户名</label>
              <input type="text" value={form.username} onChange={e => update('username', e.target.value)}
                placeholder="用户名" className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white" />
              {usernameFeedback && <p className={`mt-1 text-xs ${usernameFeedback.type === 'success' ? 'text-green-600' : 'text-red-600'}`}>{usernameFeedback.message}</p>}
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">邮箱地址</label>
              <input type="email" value={form.email} onChange={e => update('email', e.target.value)}
                placeholder="邮箱地址" className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white" />
              {emailFeedback && <p className={`mt-1 text-xs ${emailFeedback.type === 'success' ? 'text-green-600' : 'text-red-600'}`}>{emailFeedback.message}</p>}
            </div>
          </div>
        )}

        {/* Step 2: 密码设置 */}
        {currentStep === 2 && (
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">密码</label>
              <div className="relative">
                <input type={passwordVisible ? 'text' : 'password'} value={form.password}
                  onChange={e => update('password', e.target.value)}
                  placeholder="密码" className="w-full px-4 py-2.5 pr-12 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white" />
                <button type="button" onClick={() => setPasswordVisible(!passwordVisible)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400">{passwordVisible ? '🙈' : '👁️'}</button>
              </div>
              {/* 强度指示器 */}
              {form.password && (
                <div className="mt-3">
                  <div className="flex justify-between text-xs mb-1"><span className="text-gray-500">密码强度</span><span style={{color: strengthColor}}>{strengthText}</span></div>
                  <div className="w-full bg-gray-200 dark:bg-gray-600 rounded-full h-2"><div className="h-2 rounded-full transition-all" style={{width: `${strengthPercent}%`, backgroundColor: strengthColor}} /></div>
                  <div className="mt-3 space-y-1.5">
                    {[
                      {key: 'length' as const, label: '至少8个字符'},
                      {key: 'uppercase' as const, label: '包含大写字母'},
                      {key: 'lowercase' as const, label: '包含小写字母'},
                      {key: 'number' as const, label: '包含数字'},
                      {key: 'special' as const, label: '包含特殊字符'},
                    ].map(r => (
                      <div key={r.key} className="flex items-center gap-2">
                        <span className={`text-xs ${reqs[r.key] ? 'text-green-600' : 'text-gray-400'}`}>{reqs[r.key] ? '✅' : '⬜'}</span>
                        <span className={`text-xs ${reqs[r.key] ? 'text-green-600' : 'text-gray-400'}`}>{r.label}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">确认密码</label>
              <div className="relative">
                <input type="password" value={form.confirmPassword} onChange={e => update('confirmPassword', e.target.value)}
                  placeholder="确认密码" className="w-full px-4 py-2.5 pr-12 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white" />
                <span className="absolute right-3 top-1/2 -translate-y-1/2">
                  {form.confirmPassword ? (form.password === form.confirmPassword ? '✅' : '❌') : ''}
                </span>
              </div>
              {confirmFeedback && <p className={`mt-1 text-xs ${confirmFeedback.type === 'success' ? 'text-green-600' : 'text-red-600'}`}>{confirmFeedback.message}</p>}
            </div>
          </div>
        )}

        {/* Step 3: 个人信息 */}
        {currentStep === 3 && (
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">显示名称</label>
              <input type="text" value={form.displayName} onChange={e => update('displayName', e.target.value)} placeholder="显示名称" className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">个人简介</label>
              <textarea value={form.bio} onChange={e => update('bio', e.target.value)} placeholder="个人简介" rows={3} className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white" />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">位置</label>
                <input type="text" value={form.location} onChange={e => update('location', e.target.value)} placeholder="位置" className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">网站</label>
                <input type="text" value={form.website} onChange={e => update('website', e.target.value)} placeholder="网站" className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white" />
              </div>
            </div>
          </div>
        )}

        {/* Step 4: 偏好设置 */}
        {currentStep === 4 && (
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">语言偏好</label>
              <select value={form.locale} onChange={e => update('locale', e.target.value)} className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white">
                <option value="zh_CN">中文</option><option value="en">English</option>
              </select>
            </div>
            <div className="space-y-3">
              {[
                {key: 'profilePrivate' as const, label: '私密个人资料'},
                {key: 'newsletter' as const, label: '订阅新闻通讯'},
                {key: 'marketingEmails' as const, label: '接收营销邮件'},
              ].map(item => (
                <label key={item.key} className="flex items-center gap-2 cursor-pointer">
                  <input type="checkbox" checked={form[item.key]} onChange={e => update(item.key, e.target.checked)}
                    className="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded" />
                  <span className="text-sm text-gray-700 dark:text-gray-300">{item.label}</span>
                </label>
              ))}
              <label className="flex items-start gap-2 cursor-pointer">
                <input type="checkbox" checked={form.terms} onChange={e => update('terms', e.target.checked)}
                  className="mt-1 h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded" />
                <span className="text-sm text-gray-700 dark:text-gray-300">
                  我同意 <a href="#" className="text-indigo-600 hover:underline">服务条款</a> 和 <a href="#" className="text-indigo-600 hover:underline">隐私政策</a>
                </span>
              </label>
            </div>
          </div>
        )}

        {/* 导航按钮 */}
        <div className="mt-6 flex items-center justify-between">
          {currentStep > 1 && (
            <button type="button" onClick={handlePrev}
              className="px-4 py-2 border border-gray-300 dark:border-gray-600 text-sm font-medium rounded-lg text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors">
              ← 上一步
            </button>
          )}
          <div className="ml-auto">
            {currentStep < totalSteps ? (
              <button type="button" onClick={handleNext}
                className="px-6 py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 transition-colors">
                下一步 →
              </button>
            ) : (
              <button type="submit" disabled={loading}
                className="px-6 py-2 bg-green-600 text-white text-sm font-medium rounded-lg hover:bg-green-700 disabled:opacity-50 transition-colors">
                {loading ? '注册中...' : '✅ 创建账户'}
              </button>
            )}
          </div>
        </div>
      </form>

      {/* 社交注册 */}
      <div className="mt-6">
        <div className="flex items-center gap-4 mb-6">
          <div className="flex-1 border-t border-gray-300 dark:border-gray-600" />
          <span className="text-sm text-gray-500">或使用社交账号注册</span>
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

export default RegisterPage;
