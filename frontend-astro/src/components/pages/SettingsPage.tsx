'use client';

import React, {useEffect, useRef, useState} from 'react';
import {apiClient} from '@/lib/api';
import {useDarkMode} from '@/lib/dark-mode-manager';
import {getAccessTokenFromCookie} from '@/lib/auth-utils';
import {AuthGuard} from '@/components/AuthGuard';
import {User, Shield, Moon, Monitor, LogOut, Camera, Check} from 'lucide-react';

const TABS = [
  {id:'profile', label:'资料', icon:User},
  {id:'security', label:'安全', icon:Shield},
  {id:'appearance', label:'外观', icon:Moon},
  {id:'sessions', label:'会话', icon:Monitor},
];

function Settings() {
  const {theme, setTheme} = useDarkMode();
  const [tab, setTab] = useState(0);
  const [p, setP] = useState<any>(null);
  const [av, setAv] = useState('');
  const [busy, setBusy] = useState(false);
  const [un, setUn] = useState('');
  const [bio, setBio] = useState('');
  const [loc, setLoc] = useState('zh_CN');
  const [priv, setPriv] = useState(false);
  const [pw, setPw] = useState({cur:'',new:'',con:''});
  const [fa, setFa] = useState(false);
  const [qr, setQr] = useState('');
  const [secret, setSecret] = useState('');
  const [vc, setVc] = useState('');
  const [codes, setCodes] = useState<string[]>([]);
  const [sessions, setSessions] = useState<any[]>([]);
  const avRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    (async () => {
      try {
        const r = await apiClient.get('/users/me');
        if (r.success && r.data) {
          const u = (r.data as any).user || r.data;
          setP(u); setUn(u.username||''); setBio(u.bio||''); setLoc(u.locale||'zh_CN'); setPriv(u.profile_private||false);
          let url = u.avatar_url || u.avatar || '';
          if (url && !url.startsWith('http')) {
            const c = await import('@/lib/config').then(m => m.getConfig());
            url = url.startsWith('/') ? `${c.API_BASE_URL}${url}` : `${c.API_BASE_URL}/static/avatar/${url}.webp`;
          }
          setAv(url||`https://ui-avatars.com/api/?name=${encodeURIComponent(u.username||'U')}&background=random`);
        }
        const f = await apiClient.get('/security/2fa/status');
        if (f.success && f.data) setFa((f.data as any).is_2fa_enabled||false);
      } catch {}
    })();
  }, []);

  const save = async (field: string, value: any) => {
    setBusy(true);
    try {
      const r = await apiClient.put('/users/me', {[field]: value});
      if(!r.success) alert(r.error||'保存失败');
    } catch { alert('网络错误'); }
    setBusy(false);
  };

  const uploadAv = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0]; if(!f) return;
    if(!['image/jpeg','image/png','image/webp'].includes(f.type)){alert('仅支持 JPG/PNG/WEBP');return;}
    if(f.size>5<<20){alert('不超过5MB');return;}
    const fd = new FormData(); fd.append('file', f);
    setBusy(true);
    try {
      const c = await import('@/lib/config').then(m => m.getConfig());
      const t = getAccessTokenFromCookie();
      const h:any = {}; if(t) h['Authorization']=`Bearer ${t}`;
      const r = await fetch(`${c.API_BASE_URL}${c.API_PREFIX}/users/me/avatar`,{method:'POST',body:fd,credentials:'include',headers:h});
      const d = await r.json();
      if(r.ok && d.success) { const rd = new FileReader(); rd.onload = e2 => setAv(e2.target?.result as string); rd.readAsDataURL(f); }
      else alert(d.error||'上传失败');
    } catch {} finally { setBusy(false); }
  };

  const changePw = async () => {
    if(pw.new!==pw.con){alert('两次密码不一致');return;}
    if(pw.new.length<6){alert('密码至少6位');return;}
    setBusy(true);
    try {
      const c = await import('@/lib/config').then(m => m.getConfig());
      const fd = new FormData(); fd.append('current_password',pw.cur); fd.append('new_password',pw.new); fd.append('confirm_password',pw.con);
      const r = await fetch(`${c.API_BASE_URL}${c.API_PREFIX}/users/me/change-password`,{method:'POST',body:fd,credentials:'include'});
      const d = await r.json();
      if(r.ok&&d.success){alert('密码已更新，请重新登录');window.location.href='/login';} else alert(d.error||'失败');
    } catch{} finally{setBusy(false);}
  };

  const setup2FA = async () => { const r = await apiClient.get('/security/2fa/setup'); if(r.success&&r.data){setQr(r.data.qr_code);setSecret(r.data.secret);} };
  const enable2FA = async () => { if(vc.length!==6){alert('输入6位验证码');return;} const r = await apiClient.post('/security/2fa/enable',{totp_token:vc}); if(r.success){setFa(true);setQr('');setCodes((r.data as any)?.backup_codes||[]);} };
  const disable2FA = async () => { if(!confirm('禁用2FA？'))return; const r = await apiClient.post('/security/2fa/disable'); if(r.success){setFa(false);setQr('');setSecret('');setCodes([]);} };

  const loadS = async () => { const r = await apiClient.get('/sessions'); if(r.success&&r.data) setSessions((r.data as any).sessions||[]); };
  useEffect(()=>{if(tab===3)loadS();},[tab]);

  const logout = () => { document.cookie='access_token=;path=/;expires=Thu,01 Jan 1970 00:00:00 UTC'; window.location.href='/login'; };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50 dark:from-gray-950 dark:to-gray-900">
      <div className="max-w-3xl mx-auto px-4 sm:px-6 py-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">设置</h1>
          <button onClick={logout} className="text-sm text-red-500 hover:text-red-600 flex items-center gap-1"><LogOut className="w-4 h-4"/>退出</button>
        </div>

        {/* Tab bar */}
        <div className="flex gap-1 mb-8 bg-white/60 dark:bg-gray-800/60 backdrop-blur-sm rounded-xl p-1 border border-gray-200/60 dark:border-gray-700/60 w-fit">
          {TABS.map((t,i) => {
            const Icon = t.icon;
            return (
              <button key={t.id} onClick={()=>setTab(i)}
                className={`flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium transition-all ${tab===i ? 'bg-white dark:bg-gray-700 shadow-sm text-gray-900 dark:text-white' : 'text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'}`}>
                <Icon className="w-4 h-4"/>{t.label}
              </button>
            );
          })}
        </div>

        {/* Profile */}
        {tab===0 && <div className="space-y-5 pb-12">
          {/* Avatar */}
          <div className="bg-white/70 dark:bg-gray-900/70 backdrop-blur-sm rounded-xl border border-gray-100 dark:border-gray-800 p-5">
            <p className="font-medium text-gray-900 dark:text-white mb-3">头像</p>
            <div className="flex items-center gap-4">
              <img src={av} alt="" className="w-16 h-16 rounded-xl object-cover bg-gray-100" onError={e=>{(e.target as HTMLImageElement).src=`https://ui-avatars.com/api/?name=${encodeURIComponent(p?.username||'U')}&background=random`}}/>
              <div>
                <button onClick={()=>avRef.current?.click()} className="text-sm px-3 py-1.5 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700"><Camera className="w-3.5 h-3.5 inline mr-1"/>更换</button>
                <p className="text-xs text-gray-400 mt-1">JPG/PNG/WEBP 最大5MB</p>
              </div>
              <input ref={avRef} type="file" accept="image/jpeg,image/png,image/webp" onChange={uploadAv} className="hidden"/>
            </div>
          </div>
          {/* Username */}
          <div className="bg-white/70 dark:bg-gray-900/70 backdrop-blur-sm rounded-xl border border-gray-100 dark:border-gray-800 p-5">
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">用户名</label>
            <div className="flex gap-2"><input value={un} onChange={e=>setUn(e.target.value)} className="flex-1 px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white"/><button onClick={()=>save('username',un)} disabled={busy} className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 disabled:opacity-50 shrink-0">{busy?'...':'保存'}</button></div>
          </div>
          {/* Bio */}
          <div className="bg-white/70 dark:bg-gray-900/70 backdrop-blur-sm rounded-xl border border-gray-100 dark:border-gray-800 p-5">
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">简介</label>
            <textarea value={bio} onChange={e=>setBio(e.target.value)} rows={2} className="w-full px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white resize-none mb-2"/>
            <button onClick={()=>save('bio',bio)} disabled={busy} className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 disabled:opacity-50">{busy?'...':'保存'}</button>
          </div>
          {/* Locale + Privacy */}
          <div className="bg-white/70 dark:bg-gray-900/70 backdrop-blur-sm rounded-xl border border-gray-100 dark:border-gray-800 p-5 flex flex-wrap items-center gap-4">
            <div className="flex items-center gap-2"><label className="text-sm text-gray-600 dark:text-gray-400">语言</label>
              <select value={loc} onChange={e=>{setLoc(e.target.value);save('locale',e.target.value)}} className="px-3 py-2 border border-gray-200 rounded-lg bg-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
                <option value="zh_CN">中文</option><option value="en_US">English</option>
              </select></div>
            <label className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300 cursor-pointer ml-auto">
              <input type="checkbox" checked={priv} onChange={e=>{setPriv(e.target.checked);save('privacy',e.target.checked)}} className="h-4 w-4 text-blue-600 rounded"/>私密资料
            </label>
          </div>
        </div>}

        {/* Security */}
        {tab===1 && <div className="space-y-5 pb-12">
          {/* Password */}
          <div className="bg-white/70 dark:bg-gray-900/70 backdrop-blur-sm rounded-xl border border-gray-100 dark:border-gray-800 p-5">
            <p className="font-medium text-gray-900 dark:text-white mb-3">修改密码</p>
            <div className="space-y-2 max-w-sm">
              <input type="password" value={pw.cur} onChange={e=>setPw(p=>({...p,cur:e.target.value}))} placeholder="当前密码" className="w-full px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white"/>
              <input type="password" value={pw.new} onChange={e=>setPw(p=>({...p,new:e.target.value}))} placeholder="新密码" className="w-full px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white"/>
              <input type="password" value={pw.con} onChange={e=>setPw(p=>({...p,con:e.target.value}))} placeholder="确认密码" className="w-full px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white"/>
              <button onClick={changePw} disabled={busy} className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 disabled:opacity-50">{busy?'...':'更新密码'}</button>
            </div>
          </div>

          {/* 2FA */}
          <div className="bg-white/70 dark:bg-gray-900/70 backdrop-blur-sm rounded-xl border border-gray-100 dark:border-gray-800 p-5">
            <div className="flex items-center justify-between mb-3">
              <div><p className="font-medium text-gray-900 dark:text-white">双重验证</p><p className="text-xs text-gray-500 mt-0.5">{fa ? '已启用 ✓' : '增加账户安全性'}</p></div>
              {fa ? (
                <button onClick={disable2FA} className="px-3 py-1.5 bg-red-50 dark:bg-red-900/20 text-red-600 text-sm rounded-lg hover:bg-red-100">禁用</button>
              ) : (
                <button onClick={setup2FA} disabled={busy} className="px-3 py-1.5 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 disabled:opacity-50">启用</button>
              )}
            </div>
            {qr && (
              <div className="mt-4 space-y-3 border-t border-gray-100 dark:border-gray-800 pt-4">
                <img src={qr} alt="2FA QR" className="w-36 h-36 mx-auto rounded-lg"/>
                {secret && <p className="text-center text-xs text-gray-500">密钥: <code className="bg-gray-100 dark:bg-gray-800 px-1.5 py-0.5 rounded text-xs font-mono">{secret}</code></p>}
                <div className="flex gap-2 max-w-xs mx-auto">
                  <input type="text" value={vc} onChange={e=>setVc(e.target.value.replace(/\D/g,'').slice(0,6))} placeholder="000000" className="flex-1 text-center text-lg tracking-widest px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-gray-50 dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white font-mono"/>
                  <button onClick={enable2FA} className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 shrink-0">验证</button>
                </div>
              </div>
            )}
            {codes.length > 0 && (
              <div className="mt-4 p-3 bg-yellow-50 dark:bg-yellow-900/20 rounded-xl border-t border-yellow-100 dark:border-yellow-900/30">
                <p className="text-xs font-medium text-yellow-800 dark:text-yellow-200 mb-1.5">备用码（请妥善保存）</p>
                <div className="grid grid-cols-2 gap-1 text-xs font-mono text-yellow-700 dark:text-yellow-300">{codes.map(c => <span key={c}>{c}</span>)}</div>
              </div>
            )}
          </div>
        </div>}

        {/* Appearance */}
        {tab===2 && <div className="space-y-5 pb-12">
          <div className="bg-white/70 dark:bg-gray-900/70 backdrop-blur-sm rounded-xl border border-gray-100 dark:border-gray-800 p-5">
            <p className="font-medium text-gray-900 dark:text-white mb-4">主题</p>
            <div className="flex gap-3">
              {['light','dark'].map(t => (
                <button key={t} onClick={()=>setTheme(t as any)}
                  className={`flex-1 py-4 rounded-xl border-2 text-center transition-all ${theme===t ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20' : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'}`}>
                  {t==='light' ? <span className="text-lg">☀️</span> : <span className="text-lg">🌙</span>}
                  <p className="text-sm font-medium mt-1 text-gray-900 dark:text-white">{t==='light'?'浅色':'深色'}</p>
                </button>
              ))}
            </div>
          </div>
        </div>}

        {/* Sessions */}
        {tab===3 && <div className="space-y-3 pb-12">
          {sessions.length===0 ? (
            <div className="bg-white/70 dark:bg-gray-900/70 backdrop-blur-sm rounded-xl border border-gray-100 dark:border-gray-800 p-8 text-center text-gray-400"><Monitor className="w-10 h-10 mx-auto mb-3 opacity-40"/><p className="text-sm">暂无</p></div>
          ) : sessions.map((s:any,i:number) => (
            <div key={i} className="bg-white/70 dark:bg-gray-900/70 backdrop-blur-sm rounded-xl border border-gray-100 dark:border-gray-800 p-4 flex items-center justify-between">
              <div className="flex items-center gap-3"><div className="w-8 h-8 rounded-lg bg-blue-50 dark:bg-blue-900/20 flex items-center justify-center"><Monitor className="w-4 h-4 text-blue-600"/></div><div><p className="text-sm font-medium text-gray-900 dark:text-white">{s.device||s.user_agent?.slice(0,40)||'未知'}</p><p className="text-xs text-gray-400">{s.last_active?new Date(s.last_active).toLocaleString('zh-CN'):''}</p></div></div>
            </div>
          ))}
          <button onClick={loadS} className="text-sm text-blue-600 hover:underline">刷新</button>
        </div>}
      </div>
    </div>
  );
}

export default function SettingsPageGuard() { return <AuthGuard><Settings/></AuthGuard>; }
