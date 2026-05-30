'use client';

import React, {useState} from 'react';
import {apiClient} from '@/lib/api/api-client';
import {
    Check,
    Eye,
    EyeOff,
    UserPlus,
    Mail,
    Lock,
    User,
    Globe,
    ArrowLeft,
    ArrowRight,
    AlertCircle,
    BookOpen,
    Sparkles,
    Loader,
    Shield,
    CheckCircle2
} from 'lucide-react';

const passwordStrength = (pw: string): { level: number; label: string; color: string } => {
    let score = 0;
    if (pw.length >= 8) score++;
    if (pw.length >= 12) score++;
    if (/[A-Z]/.test(pw)) score++;
    if (/[0-9]/.test(pw)) score++;
    if (/[^A-Za-z0-9]/.test(pw)) score++;
    if (score <= 1) return {level: 1, label: '弱', color: 'bg-red-500'};
    if (score <= 2) return {level: 2, label: '一般', color: 'bg-orange-500'};
    if (score <= 3) return {level: 3, label: '良好', color: 'bg-yellow-500'};
    if (score <= 4) return {level: 4, label: '强', color: 'bg-green-500'};
    return {level: 5, label: '非常强', color: 'bg-emerald-500'};
};

const benefits = [
    {icon: '✍️', title: 'AI 辅助创作', desc: '智能写作助手，提升创作效率'},
    {icon: '🌍', title: '全球发布', desc: '一键多平台同步分发'},
    {icon: '📊', title: '数据分析', desc: '深度了解读者行为和偏好'},
    {icon: '💰', title: '内容变现', desc: '多种收益模式，让创作更有价值'},
];

export default function RegisterPage() {
  const [step, setStep] = useState(0);
  const [f, setF] = useState({username:'', email:'', password:'', confirm:'', locale:'zh_CN', terms:false});
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');
  const [pv, setPv] = useState(false);
  const [uOk, setUOk] = useState<boolean|null>(null);
  const [eOk, setEOk] = useState<boolean|null>(null);
    const [focusedField, setFocusedField] = useState<string | null>(null);

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

    const canProceedStep0 = f.username.length >= 3 && /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(f.email);
    const canProceedStep1 = f.password.length >= 8 && f.password === f.confirm;
    const strength = passwordStrength(f.password);

  const next = async () => {
      if (step === 0) {
          setErr('');
          await checkU();
          await checkE();
          // Need to check after async
          if (f.username.length < 3) {
              setErr('用户名至少3个字符');
              return;
          }
          if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(f.email)) {
              setErr('请输入有效的邮箱地址');
              return;
          }
          setStep(1);
          return;
      }
      if (step === 1) {
          if (f.password.length < 8) {
              setErr('密码至少8位');
              return;
          }
          if (f.password !== f.confirm) {
              setErr('两次密码不匹配');
              return;
          }
          setErr('');
          setStep(2);
      }
  };

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
      if (!f.terms) {
          setErr('请同意服务条款和隐私政策');
          return;
      }
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

    const stepLabels = ['基本信息', '设置密码', '完成注册'];

  return (
      <div
          className="min-h-screen flex bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50 dark:from-gray-950 dark:via-gray-900 dark:to-gray-950">
          {/* ═══ Left Panel - Branding ═══ */}
          <div className="hidden lg:flex lg:w-1/2 xl:w-[45%] relative overflow-hidden">
              <div className="absolute inset-0 bg-gradient-to-br from-indigo-600 via-purple-600 to-pink-600"/>

              {/* Animated Orbs */}
              <div className="absolute inset-0 overflow-hidden">
                  <div
                      className="absolute -top-20 -right-20 w-80 h-80 bg-purple-400/20 rounded-full blur-3xl animate-pulse"
                      style={{animationDuration: '5s'}}/>
                  <div
                      className="absolute bottom-10 left-10 w-60 h-60 bg-pink-400/20 rounded-full blur-3xl animate-pulse"
                      style={{animationDuration: '7s'}}/>
                  <div
                      className="absolute top-1/2 right-1/3 w-40 h-40 bg-indigo-400/20 rounded-full blur-3xl animate-pulse"
                      style={{animationDuration: '4s'}}/>
              </div>

              {/* Grid Pattern */}
              <div className="absolute inset-0 opacity-10" style={{
                  backgroundImage: 'radial-gradient(circle at 1px 1px, white 1px, transparent 0)',
                  backgroundSize: '40px 40px'
              }}/>

              <div className="relative z-10 flex flex-col justify-between p-12 xl:p-16 w-full">
                  {/* Logo */}
                  <div>
                      <div className="flex items-center gap-3 mb-2">
                          <div
                              className="w-10 h-10 bg-white/20 backdrop-blur-sm rounded-xl flex items-center justify-center">
                              <BookOpen className="w-5 h-5 text-white"/>
                          </div>
                          <span className="text-xl font-bold text-white">FastBlog</span>
                      </div>
                  </div>

                  {/* Main Content */}
                  <div className="space-y-8">
            <div>
                <h2 className="text-3xl xl:text-4xl font-bold text-white leading-tight mb-4">
                    开始你的<br/>创作旅程
                </h2>
                <p className="text-purple-100/80 text-lg leading-relaxed max-w-md">
                    加入 50,000+ 创作者的行列，用 FastBlog 讲述你的故事，让思想触达世界的每个角落。
                </p>
            </div>

                      {/* Benefits */}
                      <div className="grid grid-cols-2 gap-4">
                          {benefits.map((b, i) => (
                              <div key={i}
                                   className="group p-4 rounded-2xl bg-white/10 backdrop-blur-sm border border-white/10 hover:bg-white/15 transition-all duration-300">
                                  <span className="text-2xl block mb-2">{b.icon}</span>
                                  <h3 className="text-sm font-semibold text-white mb-1">{b.title}</h3>
                                  <p className="text-xs text-purple-100/70 leading-relaxed">{b.desc}</p>
                              </div>
                          ))}
                      </div>
                  </div>

                  {/* Testimonial */}
                  <div className="p-5 rounded-2xl bg-white/10 backdrop-blur-sm border border-white/10">
                      <p className="text-white/90 text-sm italic mb-3">
                          "FastBlog 彻底改变了我的创作方式。AI 辅助写作让我效率提升了 3 倍，平台的分发能力让我的文章被更多人看到。"
                      </p>
                      <div className="flex items-center gap-3">
                          <div
                              className="w-8 h-8 bg-gradient-to-br from-amber-400 to-orange-400 rounded-full flex items-center justify-center text-xs font-bold text-white">L
                          </div>
                          <div>
                              <p className="text-sm font-medium text-white">李明</p>
                              <p className="text-xs text-purple-100/60">全栈开发者 · 技术博主</p>
                          </div>
                      </div>
                  </div>
              </div>
          </div>

          {/* ═══ Right Panel - Registration Form ═══ */}
          <div className="flex-1 flex items-center justify-center p-6 sm:p-8 lg:p-12">
              <div className="w-full max-w-md">
                  {/* Mobile Logo */}
                  <div className="lg:hidden flex items-center gap-3 mb-8">
                      <div
                          className="w-10 h-10 bg-gradient-to-br from-indigo-600 to-purple-600 rounded-xl flex items-center justify-center shadow-lg">
                          <BookOpen className="w-5 h-5 text-white"/>
            </div>
                      <span className="text-xl font-bold text-gray-900 dark:text-white">FastBlog</span>
                  </div>

                  {/* Header */}
                  <div className="mb-8">
                      <h1 className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-white mb-2">
                          {step === 0 ? '🚀 创建账户' : step === 1 ? '🔐 设置密码' : '🎉 即将完成'}
                      </h1>
                      <p className="text-gray-500 dark:text-gray-400">
                          {step === 0 ? '填写基本信息开始注册' : step === 1 ? '创建一个安全的密码' : '确认信息并完成注册'}
                      </p>
                  </div>

                  {/* Steps Indicator */}
                  <div className="flex items-center gap-2 mb-8">
                      {stepLabels.map((label, i) => (
                          <React.Fragment key={i}>
                              <div className="flex items-center gap-2">
                                  <div
                                      className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold transition-all duration-300 ${
                                          i < step ? 'bg-green-500 text-white' :
                                              i === step ? 'bg-gradient-to-br from-indigo-500 to-purple-500 text-white shadow-md' :
                                                  'bg-gray-200 dark:bg-gray-700 text-gray-400'
                                      }`}>
                                      {i < step ? <Check className="w-4 h-4"/> : i + 1}
                                  </div>
                                  <span className={`text-xs font-medium hidden sm:block ${
                                      i <= step ? 'text-gray-700 dark:text-gray-300' : 'text-gray-400'
                                  }`}>{label}</span>
                              </div>
                              {i < stepLabels.length - 1 && (
                                  <div
                                      className={`flex-1 h-0.5 rounded-full transition-all ${i < step ? 'bg-green-500' : 'bg-gray-200 dark:bg-gray-700'}`}/>
                              )}
                          </React.Fragment>
                      ))}
                  </div>

                  {/* Error */}
                  {err && (
                      <div
                          className="mb-6 flex items-start gap-3 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200/60 dark:border-red-800/40 rounded-2xl text-sm">
                          <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5"/>
                          <span className="text-red-600 dark:text-red-400">{err}</span>
                      </div>
                  )}

                  <div
                      className="bg-white dark:bg-gray-800 rounded-3xl p-6 sm:p-8 shadow-xl border border-gray-100 dark:border-gray-700">
                      {/* Step 0: Basic Info */}
                      {step === 0 && (
                          <div className="space-y-5">
                              {/* Username */}
                              <div className="space-y-2">
                                  <label className="text-sm font-medium text-gray-700 dark:text-gray-300">用户名</label>
                                  <div
                                      className={`relative transition-all duration-200 ${focusedField === 'username' ? 'scale-[1.01]' : ''}`}>
                                      <div className="absolute left-4 top-1/2 -translate-y-1/2">
                                          <User
                                              className={`w-5 h-5 transition-colors ${focusedField === 'username' ? 'text-indigo-500' : 'text-gray-400'}`}/>
                                      </div>
                                      <input
                                          type="text"
                                          value={f.username}
                                          onChange={e => {
                                              u('username', e.target.value);
                                              setUOk(null);
                                              setErr('');
                                          }}
                                          onFocus={() => setFocusedField('username')}
                                          onBlur={() => {
                                              setFocusedField(null);
                                              checkU();
                                          }}
                                          placeholder="选择一个独特的用户名"
                                          autoFocus
                                          className="w-full pl-12 pr-12 py-4 bg-gray-50 dark:bg-gray-900 border-2 border-gray-200 dark:border-gray-600 rounded-2xl text-sm text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:border-indigo-500 focus:ring-4 focus:ring-indigo-500/10 transition-all"
                                      />
                                      <div className="absolute right-4 top-1/2 -translate-y-1/2">
                                          {uOk === true && <CheckCircle2 className="w-5 h-5 text-green-500"/>}
                                          {uOk === false && <AlertCircle className="w-5 h-5 text-red-500"/>}
                                      </div>
                                  </div>
                                  {uOk !== null && (
                                      <p className={`text-xs flex items-center gap-1 ${uOk ? 'text-green-600 dark:text-green-400' : 'text-red-500'}`}>
                                          {uOk ? '✓ 用户名可用' : '✗ 用户名不可用或已被占用'}
                                      </p>
                                  )}
                              </div>

                              {/* Email */}
                              <div className="space-y-2">
                                  <label
                                      className="text-sm font-medium text-gray-700 dark:text-gray-300">邮箱地址</label>
                                  <div
                                      className={`relative transition-all duration-200 ${focusedField === 'email' ? 'scale-[1.01]' : ''}`}>
                                      <div className="absolute left-4 top-1/2 -translate-y-1/2">
                                          <Mail
                                              className={`w-5 h-5 transition-colors ${focusedField === 'email' ? 'text-indigo-500' : 'text-gray-400'}`}/>
                                      </div>
                                      <input
                                          type="email"
                                          value={f.email}
                                          onChange={e => {
                                              u('email', e.target.value);
                                              setEOk(null);
                                              setErr('');
                                          }}
                                          onFocus={() => setFocusedField('email')}
                                          onBlur={() => {
                                              setFocusedField(null);
                                              checkE();
                                          }}
                                          placeholder="your@email.com"
                                          className="w-full pl-12 pr-12 py-4 bg-gray-50 dark:bg-gray-900 border-2 border-gray-200 dark:border-gray-600 rounded-2xl text-sm text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:border-indigo-500 focus:ring-4 focus:ring-indigo-500/10 transition-all"
                                      />
                                      <div className="absolute right-4 top-1/2 -translate-y-1/2">
                                          {eOk === true && <CheckCircle2 className="w-5 h-5 text-green-500"/>}
                                          {eOk === false && <AlertCircle className="w-5 h-5 text-red-500"/>}
                                      </div>
                                  </div>
                                  {eOk !== null && (
                                      <p className={`text-xs flex items-center gap-1 ${eOk ? 'text-green-600 dark:text-green-400' : 'text-red-500'}`}>
                                          {eOk ? '✓ 邮箱可用' : '✗ 邮箱格式不正确或已被注册'}
                                      </p>
                                  )}
                              </div>

                              <button
                                  type="button"
                                  onClick={next}
                                  disabled={!canProceedStep0}
                                  className="w-full py-4 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700 text-white font-semibold rounded-2xl transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-indigo-500/25 hover:shadow-xl active:scale-[0.98] flex items-center justify-center gap-2"
                              >
                                  下一步 <ArrowRight className="w-5 h-5"/>
                              </button>
                          </div>
                      )}

                      {/* Step 1: Password */}
                      {step === 1 && (
                          <div className="space-y-5">
                              {/* Password */}
                              <div className="space-y-2">
                                  <label className="text-sm font-medium text-gray-700 dark:text-gray-300">密码</label>
                                  <div
                                      className={`relative transition-all duration-200 ${focusedField === 'password' ? 'scale-[1.01]' : ''}`}>
                                      <div className="absolute left-4 top-1/2 -translate-y-1/2">
                                          <Lock
                                              className={`w-5 h-5 transition-colors ${focusedField === 'password' ? 'text-indigo-500' : 'text-gray-400'}`}/>
                                      </div>
                                      <input
                                          type={pv ? 'text' : 'password'}
                                          value={f.password}
                                          onChange={e => {
                                              u('password', e.target.value);
                                              setErr('');
                                          }}
                                          onFocus={() => setFocusedField('password')}
                                          onBlur={() => setFocusedField(null)}
                                          placeholder="至少8位，包含字母和数字"
                                          autoFocus
                                          className="w-full pl-12 pr-12 py-4 bg-gray-50 dark:bg-gray-900 border-2 border-gray-200 dark:border-gray-600 rounded-2xl text-sm text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:border-indigo-500 focus:ring-4 focus:ring-indigo-500/10 transition-all"
                                      />
                                      <button type="button" onClick={() => setPv(!pv)}
                                              className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300">
                                          {pv ? <EyeOff className="w-5 h-5"/> : <Eye className="w-5 h-5"/>}
                                      </button>
                                  </div>
                                  {/* Password Strength */}
                                  {f.password && (
                                      <div className="space-y-1.5">
                                          <div className="flex gap-1">
                                              {[1, 2, 3, 4, 5].map(i => (
                                                  <div key={i}
                                                       className={`h-1.5 flex-1 rounded-full transition-all duration-300 ${i <= strength.level ? strength.color : 'bg-gray-200 dark:bg-gray-700'}`}/>
                                              ))}
                                          </div>
                                          <p className="text-xs text-gray-500">密码强度: <span
                                              className="font-medium">{strength.label}</span></p>
                                      </div>
                                  )}
                              </div>

                              {/* Confirm Password */}
                              <div className="space-y-2">
                                  <label
                                      className="text-sm font-medium text-gray-700 dark:text-gray-300">确认密码</label>
                                  <div
                                      className={`relative transition-all duration-200 ${focusedField === 'confirm' ? 'scale-[1.01]' : ''}`}>
                                      <div className="absolute left-4 top-1/2 -translate-y-1/2">
                                          <Lock
                                              className={`w-5 h-5 transition-colors ${focusedField === 'confirm' ? 'text-indigo-500' : 'text-gray-400'}`}/>
                                      </div>
                                      <input
                                          type="password"
                                          value={f.confirm}
                                          onChange={e => {
                                              u('confirm', e.target.value);
                                              setErr('');
                                          }}
                                          onFocus={() => setFocusedField('confirm')}
                                          onBlur={() => setFocusedField(null)}
                                          placeholder="再次输入密码"
                                          className="w-full pl-12 pr-12 py-4 bg-gray-50 dark:bg-gray-900 border-2 border-gray-200 dark:border-gray-600 rounded-2xl text-sm text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:border-indigo-500 focus:ring-4 focus:ring-indigo-500/10 transition-all"
                                      />
                                      {f.confirm && (
                                          <div className="absolute right-4 top-1/2 -translate-y-1/2">
                                              {f.password === f.confirm ?
                                                  <CheckCircle2 className="w-5 h-5 text-green-500"/> :
                                                  <AlertCircle className="w-5 h-5 text-red-500"/>}
                                          </div>
                                      )}
                                  </div>
                                  {f.confirm && f.password !== f.confirm && (
                                      <p className="text-xs text-red-500">✗ 两次密码不匹配</p>
                                  )}
                              </div>

                              {/* Password Requirements */}
                              <div
                                  className="p-4 bg-gray-50 dark:bg-gray-900 rounded-2xl border border-gray-100 dark:border-gray-700">
                                  <p className="text-xs font-medium text-gray-600 dark:text-gray-400 mb-2">密码要求:</p>
                                  <div className="grid grid-cols-2 gap-1.5">
                                      {[
                                          {met: f.password.length >= 8, text: '至少8个字符'},
                                          {met: /[A-Z]/.test(f.password), text: '包含大写字母'},
                                          {met: /[0-9]/.test(f.password), text: '包含数字'},
                                          {met: /[^A-Za-z0-9]/.test(f.password), text: '包含特殊字符'},
                                      ].map((req, i) => (
                                          <div key={i}
                                               className={`flex items-center gap-1.5 text-xs ${req.met ? 'text-green-600 dark:text-green-400' : 'text-gray-400'}`}>
                                              {req.met ? <Check className="w-3.5 h-3.5"/> : <div
                                                  className="w-3.5 h-3.5 rounded-full border border-gray-300 dark:border-gray-600"/>}
                                              {req.text}
                                          </div>
                                      ))}
                                  </div>
                              </div>

                              <div className="flex gap-3">
                                  <button type="button" onClick={() => {
                                      setStep(0);
                                      setErr('');
                                  }}
                                          className="flex-1 py-4 border-2 border-gray-200 dark:border-gray-600 rounded-2xl text-sm font-semibold hover:bg-gray-50 dark:hover:bg-gray-750 transition-colors flex items-center justify-center gap-2 text-gray-700 dark:text-gray-300">
                                      <ArrowLeft className="w-4 h-4"/> 上一步
                                  </button>
                                  <button
                                      type="button"
                                      onClick={next}
                                      disabled={!canProceedStep1}
                                      className="flex-1 py-4 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700 text-white font-semibold rounded-2xl transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-indigo-500/25 active:scale-[0.98] flex items-center justify-center gap-2"
                                  >
                                      下一步 <ArrowRight className="w-4 h-4"/>
                                  </button>
                              </div>
                          </div>
                      )}

                      {/* Step 2: Confirm & Terms */}
                      {step === 2 && (
                          <form onSubmit={submit} className="space-y-5">
                              {/* Summary */}
                              <div
                                  className="p-5 bg-gradient-to-br from-indigo-50 to-purple-50 dark:from-indigo-900/20 dark:to-purple-900/20 rounded-2xl border border-indigo-100 dark:border-indigo-800/30">
                                  <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3 flex items-center gap-2">
                                      <CheckCircle2 className="w-4 h-4 text-green-500"/> 注册信息确认
                                  </h3>
                                  <div className="space-y-2">
                                      <div className="flex items-center gap-3 text-sm">
                                          <User className="w-4 h-4 text-gray-400"/>
                                          <span className="text-gray-500 dark:text-gray-400">用户名:</span>
                                          <span
                                              className="font-medium text-gray-900 dark:text-white">{f.username}</span>
                                      </div>
                                      <div className="flex items-center gap-3 text-sm">
                                          <Mail className="w-4 h-4 text-gray-400"/>
                                          <span className="text-gray-500 dark:text-gray-400">邮箱:</span>
                                          <span className="font-medium text-gray-900 dark:text-white">{f.email}</span>
                                      </div>
                                      <div className="flex items-center gap-3 text-sm">
                                          <Lock className="w-4 h-4 text-gray-400"/>
                                          <span className="text-gray-500 dark:text-gray-400">密码:</span>
                                          <span
                                              className="font-medium text-gray-900 dark:text-white">{'•'.repeat(f.password.length)}</span>
                                      </div>
                                  </div>
                              </div>

                              {/* Language */}
                              <div className="space-y-2">
                                  <label
                                      className="text-sm font-medium text-gray-700 dark:text-gray-300 flex items-center gap-2">
                                      <Globe className="w-4 h-4"/> 界面语言
                                  </label>
                                  <select
                                      value={f.locale}
                                      onChange={e => u('locale', e.target.value)}
                                      className="w-full px-4 py-3.5 bg-gray-50 dark:bg-gray-900 border-2 border-gray-200 dark:border-gray-600 rounded-2xl text-sm text-gray-900 dark:text-white focus:outline-none focus:border-indigo-500 focus:ring-4 focus:ring-indigo-500/10 transition-all"
                                  >
                                      <option value="zh_CN">🇨🇳 简体中文</option>
                                      <option value="en_US">🇺🇸 English</option>
                                  </select>
                              </div>

                              {/* Terms */}
                              <label
                                  className="flex items-start gap-3 cursor-pointer group p-4 rounded-2xl bg-gray-50 dark:bg-gray-900 border border-gray-100 dark:border-gray-700 hover:border-indigo-200 dark:hover:border-indigo-800 transition-colors">
                                  <div className="relative mt-0.5">
                                      <input type="checkbox" checked={f.terms}
                                             onChange={e => u('terms', e.target.checked)} className="peer sr-only"/>
                                      <div
                                          className="w-5 h-5 border-2 border-gray-300 dark:border-gray-600 rounded-lg peer-checked:border-indigo-500 peer-checked:bg-indigo-500 transition-all flex items-center justify-center">
                                          {f.terms &&
                                              <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24"
                                                   stroke="currentColor" strokeWidth={3}>
                                                  <path strokeLinecap="round" strokeLinejoin="round"
                                                        d="M5 13l4 4L19 7"/>
                                              </svg>}
                                      </div>
                                  </div>
                                  <span className="text-sm text-gray-600 dark:text-gray-400 leading-relaxed">
                    我已阅读并同意{' '}
                                      <a href="/terms"
                                         className="text-indigo-600 hover:underline dark:text-indigo-400 font-medium">服务条款</a>
                                      {' '}和{' '}
                                      <a href="/privacy"
                                         className="text-indigo-600 hover:underline dark:text-indigo-400 font-medium">隐私政策</a>
                  </span>
                              </label>

                              <div className="flex gap-3">
                                  <button type="button" onClick={() => {
                                      setStep(1);
                                      setErr('');
                                  }}
                                          className="flex-1 py-4 border-2 border-gray-200 dark:border-gray-600 rounded-2xl text-sm font-semibold hover:bg-gray-50 dark:hover:bg-gray-750 transition-colors flex items-center justify-center gap-2 text-gray-700 dark:text-gray-300">
                                      <ArrowLeft className="w-4 h-4"/> 上一步
                                  </button>
                                  <button
                                      type="submit"
                                      disabled={busy || !f.terms}
                                      className="flex-1 py-4 bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700 text-white font-semibold rounded-2xl transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-green-500/25 hover:shadow-xl active:scale-[0.98] flex items-center justify-center gap-2"
                                  >
                                      {busy ? (
                                          <><Loader className="w-5 h-5 animate-spin"/> 创建中...</>
                                      ) : (
                                          <><Sparkles className="w-5 h-5"/> 创建账户</>
                                      )}
                                  </button>
                              </div>
                          </form>
                      )}
                  </div>

                  {/* Login Link */}
                  <p className="text-center text-sm text-gray-500 dark:text-gray-400 mt-6">
                      已有账户？{' '}
                      <a href="/login"
                         className="text-indigo-600 hover:text-indigo-700 dark:text-indigo-400 font-semibold hover:underline">
                          立即登录
                      </a>
                  </p>

                  {/* Footer */}
                  <div className="mt-6 text-center">
                      <p className="text-xs text-gray-400 dark:text-gray-500">
                          注册即表示同意我们的服务条款和隐私政策
                      </p>
                  </div>
              </div>
      </div>
    </div>
  );
}
