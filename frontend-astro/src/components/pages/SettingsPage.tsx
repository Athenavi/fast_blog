'use client';

import React, {useEffect, useRef, useState} from 'react';
import {apiClient} from '@/lib/api';
import {useDarkMode} from '@/lib/dark-mode-manager';
import {getAccessTokenFromCookie} from '@/lib/auth-utils';
import {motion} from 'framer-motion';
import {Bell, Camera, Laptop, LogOut, Moon, Palette, Save, Shield, Sun, Upload, User} from 'lucide-react';

type Tab = 'profile' | 'account' | 'appearance' | 'security' | 'sessions';

const SettingsPage: React.FC = () => {
  const {theme, setTheme} = useDarkMode();
  const [activeTab, setActiveTab] = useState<Tab>('profile');
  const [profile, setProfile] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [avatarUrl, setAvatarUrl] = useState('');
  const avatarRef = useRef<HTMLInputElement>(null);
  const [form, setForm] = useState({username: '', bio: '', locale: 'zh_CN', profilePrivate: false});
  const [pwForm, setPwForm] = useState({current: '', newPw: '', confirm: ''});
  const [twoFactorEnabled, setTwoFactorEnabled] = useState(false);
  const [showQR, setShowQR] = useState(false);
  const [qrCode, setQrCode] = useState('');
  const [totpSecret, setTotpSecret] = useState('');
  const [verifyCode, setVerifyCode] = useState('');
  const [backupCodes, setBackupCodes] = useState<string[]>([]);
  const [sessions, setSessions] = useState<any[]>([]);

  useEffect(() => {
    (async () => {
      try {
        const res = await apiClient.get('/users/me');
        if (res.success && res.data) {
          const u = (res.data as any).user || res.data;
          setProfile(u);
          setForm({username: u.username || '', bio: u.bio || '', locale: u.locale || 'zh_CN', profilePrivate: u.profile_private || false});
          let av = u.avatar_url || u.avatar;
          if (av && !av.startsWith('http')) {
            const config = await import('@/lib/config').then(m => m.getConfig());
            av = av.startsWith('/') ? `${config.API_BASE_URL}${av}` : `${config.API_BASE_URL}/static/avatar/${av}.webp`;
          }
          setAvatarUrl(av || `https://ui-avatars.com/api/?name=${encodeURIComponent(u.username||'User')}&background=random`);
        }
        const fa = await apiClient.get('/security/2fa/status');
        if (fa.success && fa.data) setTwoFactorEnabled((fa.data as any).is_2fa_enabled || false);
      } catch {} finally { setLoading(false); }
    })();
  }, []);

  const saveField = async (field: string, data: any) => {
    setSaving(true);
    try {
      const res = await apiClient.put('/users/me', {change_type: field, ...data});
      if (!res.success) alert(res.error || '保存失败');
    } catch {} finally { setSaving(false); }
  };

  const handleAvatar = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]; if (!file) return;
    if (!['image/jpeg','image/png','image/webp'].includes(file.type)) {alert('请上传 JPG/PNG/WEBP'); return;}
    if (file.size > 5*1024*1024) {alert('图片不能超过5MB'); return;}
    const fd = new FormData(); fd.append('file', file);
    try {
      setSaving(true);
      const config = await import('@/lib/config').then(m => m.getConfig());
      const token = getAccessTokenFromCookie();
      const headers: any = {};
      if (token) headers['Authorization'] = `Bearer ${token}`;
      const res = await fetch(`${config.API_BASE_URL}${config.API_PREFIX}/users/settings/profile/avatar`, {method:'POST', body: fd, credentials:'include', headers});
      const result = await res.json();
      if (res.ok && result.success) { const r = new FileReader(); r.onload = e2 => setAvatarUrl(e2.target?.result as string); r.readAsDataURL(file); }
      else alert(result.error || '头像更新失败');
    } catch {} finally { setSaving(false); }
  };

  const updatePassword = async () => {
    if (pwForm.newPw !== pwForm.confirm) {alert('密码不匹配'); return;}
    if (pwForm.newPw.length < 6) {alert('密码至少6位'); return;}
    setSaving(true);
    try {
      const config = await import('@/lib/config').then(m => m.getConfig());
      const fd = new FormData();
      fd.append('current_password', pwForm.current);
      fd.append('new_password', pwForm.newPw);
      fd.append('confirm_password', pwForm.confirm);
      const res = await fetch(`${config.API_BASE_URL}${config.API_PREFIX}/users/me/change-password`, {method:'POST', body: fd, credentials:'include'});
      const result = await res.json();
      if (res.ok && result.success) { alert('密码已更新，请重新登录'); window.location.href = '/login'; }
      else alert(result.error || '更新密码失败');
    } catch {} finally { setSaving(false); }
  };

  const setup2FA = async () => {
    const res = await apiClient.get('/security/2fa/setup');
    if (res.success && res.data) { setQrCode(res.data.qr_code); setTotpSecret(res.data.secret); setShowQR(true); }
    else alert(res.error || '获取2FA信息失败');
  };

  const enable2FA = async () => {
    if (verifyCode.length !== 6) {alert('请输入6位验证码'); return;}
    const res = await apiClient.post('/security/2fa/enable', {totp_token: verifyCode});
    if (res.success) { setTwoFactorEnabled(true); setShowQR(false); setBackupCodes((res.data as any)?.backup_codes || []); }
    else alert(res.error || '启用2FA失败');
  };

  const disable2FA = async () => {
    if (!confirm('确定禁用2FA？')) return;
    const res = await apiClient.post('/security/2fa/disable');
    if (res.success) { setTwoFactorEnabled(false); setQrCode(''); setTotpSecret(''); setBackupCodes([]); }
  };

  const loadSessions = async () => {
    const res = await apiClient.get('/sessions');
    if (res.success && res.data) setSessions((res.data as any).sessions || []);
  };

  useEffect(() => { if (activeTab === 'sessions') loadSessions(); }, [activeTab]);

  const logout = () => { document.cookie = 'access_token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 UTC'; window.location.href = '/login'; };

  if (loading) return <div className="min-h-screen flex items-center justify-center"><div className="animate-spin w-12 h-12 border-4 border-blue-600 border-t-transparent rounded-full" /></div>;

  const tabs: {id: Tab; label: string; icon: any}[] = [
    {id:'profile', label:'个人资料', icon: User}, {id:'account', label:'账户安全', icon: Shield},
    {id:'appearance', label:'外观设置', icon: Palette}, {id:'security', label:'双因素认证', icon: Shield},
    {id:'sessions', label:'会话管理', icon: Laptop},
  ];

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950 pt-24 pb-12">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        <h1 className="text-3xl font-black text-gray-900 dark:text-white mb-2">设置</h1>
        <p className="text-gray-600 dark:text-gray-400 mb-8">管理你的账户和个人信息</p>

        <div className="flex flex-col lg:flex-row gap-8">
          {/* Sidebar */}
          <nav className="lg:w-56 flex-shrink-0">
            <div className="bg-white dark:bg-gray-900 rounded-2xl border p-3 sticky top-24 space-y-1">
              {tabs.map(t => {
                const Icon = t.icon;
                return (
                  <button key={t.id} onClick={() => setActiveTab(t.id)}
                    className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all ${
                      activeTab === t.id ? 'bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400' : 'text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800'
                    }`}>
                    <Icon className="w-5 h-5"/><span>{t.label}</span>
                  </button>
                );
              })}
              <div className="pt-3 mt-3 border-t border-gray-200 dark:border-gray-700">
                <button onClick={logout} className="w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20"><LogOut className="w-5 h-5"/>注销登录</button>
              </div>
            </div>
          </nav>

          {/* Content */}
          <main className="flex-1 space-y-6">
            {/* Profile */}
            {activeTab === 'profile' && (
              <motion.div initial={{opacity:0,y:20}} animate={{opacity:1,y:0}} className="space-y-6">
                <div className="bg-white dark:bg-gray-900 rounded-2xl border p-8">
                  <h2 className="text-xl font-bold mb-6">头像</h2>
                  <div className="flex items-center gap-6">
                    <div className="relative">
                      <img src={avatarUrl} alt="avatar" className="w-24 h-24 rounded-2xl object-cover border-2 border-gray-200" onError={e => {(e.target as HTMLImageElement).src = `https://ui-avatars.com/api/?name=${encodeURIComponent(profile?.username||'U')}&background=random`}} />
                      <button onClick={() => avatarRef.current?.click()} className="absolute -bottom-2 -right-2 w-8 h-8 bg-blue-600 text-white rounded-full flex items-center justify-center shadow-lg"><Camera className="w-4 h-4"/></button>
                    </div>
                    <div>
                      <button onClick={() => avatarRef.current?.click()} className="px-4 py-2 bg-gray-100 dark:bg-gray-800 rounded-xl text-sm font-medium hover:bg-gray-200"><Upload className="w-4 h-4 inline mr-1"/>更换头像</button>
                      <p className="text-xs text-gray-500 mt-2">支持 JPG/PNG/WEBP，最大5MB</p>
                    </div>
                    <input ref={avatarRef} type="file" accept="image/jpeg,image/png,image/webp" onChange={handleAvatar} className="hidden" />
                  </div>
                </div>

                <div className="bg-white dark:bg-gray-900 rounded-2xl border p-8">
                  <h2 className="text-xl font-bold mb-6">用户名</h2>
                  <div className="flex gap-4">
                    <input type="text" value={form.username} onChange={e => setForm(f => ({...f, username: e.target.value}))} className="flex-1 px-4 py-3 bg-gray-50 dark:bg-gray-800 border rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white" />
                    <button onClick={() => saveField('username', {form_data: {username: form.username}})} disabled={saving} className="px-6 py-3 bg-blue-600 text-white rounded-xl font-medium hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2"><Save className="w-4 h-4"/>{saving ? '...' : '保存'}</button>
                  </div>
                </div>

                <div className="bg-white dark:bg-gray-900 rounded-2xl border p-8">
                  <h2 className="text-xl font-bold mb-6">个人简介</h2>
                  <textarea value={form.bio} onChange={e => setForm(f => ({...f, bio: e.target.value}))} rows={3} className="w-full px-4 py-3 bg-gray-50 dark:bg-gray-800 border rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white resize-none" />
                  <div className="flex justify-end mt-4">
                    <button onClick={() => saveField('bio', {form_data: {bio: form.bio}})} disabled={saving} className="px-6 py-3 bg-blue-600 text-white rounded-xl font-medium hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2"><Save className="w-4 h-4"/>{saving ? '...' : '保存'}</button>
                  </div>
                </div>

                <div className="bg-white dark:bg-gray-900 rounded-2xl border p-8">
                  <h2 className="text-xl font-bold mb-6">偏好设置</h2>
                  <div className="space-y-4">
                    <div><label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">语言</label>
                      <select value={form.locale} onChange={e => {setForm(f => ({...f, locale: e.target.value})); saveField('locale', {locale: e.target.value});}} className="w-full px-4 py-3 bg-gray-50 dark:bg-gray-800 border rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white">
                        <option value="zh_CN">简体中文</option><option value="en_US">English</option>
                      </select></div>
                    <label className="flex items-center gap-3 cursor-pointer">
                      <input type="checkbox" checked={form.profilePrivate} onChange={e => {setForm(f => ({...f, profilePrivate: e.target.checked})); saveField('privacy', {profile_private: e.target.checked});}} className="h-4 w-4 text-blue-600 rounded" />
                      <span className="text-sm text-gray-700 dark:text-gray-300">私密个人资料</span>
                    </label>
                  </div>
                </div>
              </motion.div>
            )}

            {/* Account Security */}
            {activeTab === 'account' && (
              <motion.div initial={{opacity:0,y:20}} animate={{opacity:1,y:0}} className="bg-white dark:bg-gray-900 rounded-2xl border p-8">
                <h2 className="text-xl font-bold mb-6">修改密码</h2>
                <div className="space-y-4 max-w-md">
                  <input type="password" value={pwForm.current} onChange={e => setPwForm(f => ({...f, current: e.target.value}))} placeholder="当前密码" className="w-full px-4 py-3 bg-gray-50 dark:bg-gray-800 border rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white" />
                  <input type="password" value={pwForm.newPw} onChange={e => setPwForm(f => ({...f, newPw: e.target.value}))} placeholder="新密码" className="w-full px-4 py-3 bg-gray-50 dark:bg-gray-800 border rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white" />
                  <input type="password" value={pwForm.confirm} onChange={e => setPwForm(f => ({...f, confirm: e.target.value}))} placeholder="确认新密码" className="w-full px-4 py-3 bg-gray-50 dark:bg-gray-800 border rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white" />
                  <button onClick={updatePassword} disabled={saving} className="px-6 py-3 bg-blue-600 text-white rounded-xl font-medium hover:bg-blue-700 disabled:opacity-50">{saving ? '保存中...' : '更新密码'}</button>
                </div>
              </motion.div>
            )}

            {/* Appearance */}
            {activeTab === 'appearance' && (
              <motion.div initial={{opacity:0,y:20}} animate={{opacity:1,y:0}} className="bg-white dark:bg-gray-900 rounded-2xl border p-8">
                <h2 className="text-xl font-bold mb-6">外观设置</h2>
                <div className="flex gap-4">
                  {[
                    {value:'light', label:'浅色', icon: Sun},
                    {value:'dark', label:'深色', icon: Moon},
                  ].map(t => {
                    const Icon = t.icon;
                    return (
                      <button key={t.value} onClick={() => setTheme(t.value as any)}
                        className={`flex-1 p-6 rounded-2xl border-2 text-center transition-all ${theme === t.value ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20' : 'border-gray-200 dark:border-gray-700 hover:border-gray-300'}`}>
                        <Icon className="w-8 h-8 mx-auto mb-2"/><span className="font-medium">{t.label}</span>
                      </button>
                    );
                  })}
                </div>
              </motion.div>
            )}

            {/* 2FA */}
            {activeTab === 'security' && (
              <motion.div initial={{opacity:0,y:20}} animate={{opacity:1,y:0}} className="bg-white dark:bg-gray-900 rounded-2xl border p-8">
                <h2 className="text-xl font-bold mb-6">双因素认证</h2>
                <div className="flex items-center justify-between mb-6">
                  <div><p className="font-medium">状态</p><p className="text-sm text-gray-500">{twoFactorEnabled ? '已启用 ✓' : '未启用'}</p></div>
                  {twoFactorEnabled ?
                    <button onClick={disable2FA} className="px-4 py-2 bg-red-100 text-red-700 rounded-xl text-sm font-medium hover:bg-red-200">禁用</button> :
                    <button onClick={setup2FA} className="px-4 py-2 bg-blue-600 text-white rounded-xl text-sm font-medium hover:bg-blue-700">启用</button>
                  }
                </div>
                {showQR && (
                  <div className="space-y-4">
                    <div className="flex justify-center"><img src={qrCode} alt="2FA QR" className="w-48 h-48"/></div>
                    {totpSecret && <p className="text-center text-sm text-gray-500">密钥: <code className="bg-gray-100 dark:bg-gray-800 px-2 py-1 rounded text-xs">{totpSecret}</code></p>}
                    <div className="flex gap-3 max-w-xs mx-auto">
                      <input type="text" value={verifyCode} onChange={e => setVerifyCode(e.target.value.replace(/\D/g,'').slice(0,6))} placeholder="6位验证码" className="flex-1 px-4 py-3 bg-gray-50 border rounded-xl text-center text-xl tracking-widest focus:outline-none focus:ring-2 focus:ring-blue-500" />
                      <button onClick={enable2FA} className="px-6 py-3 bg-blue-600 text-white rounded-xl font-medium hover:bg-blue-700">验证</button>
                    </div>
                  </div>
                )}
                {backupCodes.length > 0 && (
                  <div className="mt-6 p-4 bg-yellow-50 dark:bg-yellow-900/20 rounded-xl">
                    <p className="font-medium text-yellow-800 dark:text-yellow-200 mb-2">备用码（请妥善保存）</p>
                    <div className="grid grid-cols-2 gap-2"><code className="text-sm">{backupCodes.map(c => <span key={c} className="block font-mono">{c}</span>)}</code></div>
                  </div>
                )}
              </motion.div>
            )}

            {/* Sessions */}
            {activeTab === 'sessions' && (
              <motion.div initial={{opacity:0,y:20}} animate={{opacity:1,y:0}} className="bg-white dark:bg-gray-900 rounded-2xl border p-8">
                <div className="flex justify-between items-center mb-6">
                  <h2 className="text-xl font-bold">会话管理</h2>
                  <button onClick={loadSessions} className="text-sm text-blue-600 hover:underline">刷新</button>
                </div>
                {sessions.length > 0 ? (
                  <div className="space-y-3">
                    {sessions.map((s: any) => (
                      <div key={s.id} className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-800 rounded-xl">
                        <div className="flex items-center gap-3">
                          <Laptop className="w-5 h-5 text-gray-400"/>
                          <div><p className="font-medium text-sm">{s.device || s.user_agent?.slice(0,50) || '未知设备'}</p><p className="text-xs text-gray-500">{new Date(s.last_active || s.created_at).toLocaleString('zh-CN')}</p></div>
                        </div>
                        <button onClick={() => {/* revokeSession(s.id) */}} className="text-sm text-red-500 hover:underline">注销</button>
                      </div>
                    ))}
                  </div>
                ) : <div className="text-center py-12 text-gray-400"><Laptop className="w-12 h-12 mx-auto mb-3"/>暂无会话记录</div>}
              </motion.div>
            )}
          </main>
        </div>
      </div>
    </div>
  );
};

export default SettingsPage;
