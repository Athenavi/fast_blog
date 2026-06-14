'use client';

import React, {useCallback, useEffect, useRef, useState} from 'react';
import {apiClient} from '@/lib/api/base-client';
import {useDarkMode} from '@/lib/dark-mode-manager';
import {getAccessTokenFromCookie} from '@/lib/auth-utils';
import {useConfirm} from '@/components/ui/confirm-provider';
import {Monitor, Smartphone} from 'lucide-react';
import {AUTH, USERS, SECURITY} from '@/lib/api/api-paths';

const TABS = [
  {id: 'profile', label: '个人资料', icon: 'User', desc: '管理你的基本信息'},
  {id: 'security', label: '安全设置', icon: 'Shield', desc: '密码、双重验证和会话'},
  {id: 'appearance', label: '外观偏好', icon: 'Palette', desc: '主题和显示设置'},
  {id: 'sessions', label: '登录设备', icon: 'Monitor', desc: '管理已登录的设备'},
];

const pwStrengthColors = ['bg-red-500', 'bg-orange-500', 'bg-yellow-500', 'bg-green-500', 'bg-emerald-500'];
const pwStrengthLabels = ['弱', '一般', '良好', '强', '非常强'];

export function useSettingsState() {
  const confirm = useConfirm();
  const {theme, setTheme} = useDarkMode();
  const [tab, setTab] = useState(0);
  const [p, setP] = useState<any>(null);
  const [av, setAv] = useState('');
  const [busy, setBusy] = useState(false);
  const [un, setUn] = useState('');
  const [bio, setBio] = useState('');
  const [loc, setLoc] = useState('zh_CN');
  const [priv, setPriv] = useState(false);
  const [pw, setPw] = useState({cur: '', new: '', con: ''});
  const [showPw, setShowPw] = useState({cur: false, new: false, con: false});
  const [fa, setFa] = useState(false);
  const [qr, setQr] = useState('');
  const [secret, setSecret] = useState('');
  const [vc, setVc] = useState('');
  const [codes, setCodes] = useState<string[]>([]);
  const [sessions, setSessions] = useState<any[]>([]);
  const [savedField, setSavedField] = useState<string | null>(null);
  const [pwStrength, setPwStrength] = useState(0);
  const avRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    (async () => {
      try {
        const r = await apiClient.get(USERS.ME);
        if (r.success && r.data) {
          const u = (r.data as any).user || r.data;
          setP(u);
          setUn(u.username || '');
          setBio(u.bio || '');
          setLoc(u.locale || 'zh_CN');
          setPriv(u.profile_private || false);
          let url = u.avatar_url || u.avatar || '';
          if (url && !url.startsWith('http')) {
            const c = await import('@/lib/config').then(m => m.getConfig());
            url = url.startsWith('/') ? `${c.API_BASE_URL}${url}` : `${c.API_BASE_URL}/api/v2/static/avatar/${url}.webp`;
          }
          setAv(url || `https://ui-avatars.com/api/?name=${encodeURIComponent(u.username || 'U')}&background=random`);
        }
        const f = await apiClient.get(SECURITY.TWO_FA_STATUS);
        if (f.success && f.data) setFa((f.data as any).is_2fa_enabled || false);
      } catch {}
    })();
  }, []);

  // Password strength calculator
  useEffect(() => {
    const p = pw.new;
    let s = 0;
    if (p.length >= 8) s++;
    if (p.length >= 12) s++;
    if (/[A-Z]/.test(p)) s++;
    if (/[0-9]/.test(p)) s++;
    if (/[^A-Za-z0-9]/.test(p)) s++;
    setPwStrength(s);
  }, [pw.new]);

  const flashSaved = useCallback((field: string) => {
    setSavedField(field);
    setTimeout(() => setSavedField(null), 2000);
  }, []);

  const save = async (field: string, value: any) => {
    setBusy(true);
    try {
      const r = await apiClient.put(USERS.ME, {[field]: value});
      if (r.success) flashSaved(field);
      else alert(r.error || '保存失败');
    } catch {
      alert('网络错误');
    }
    setBusy(false);
  };

  const uploadAv = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (!f) return;
    if (!['image/jpeg', 'image/png', 'image/webp'].includes(f.type)) {
      alert('仅支持 JPG/PNG/WEBP');
      return;
    }
    if (f.size > 5 << 20) {
      alert('不超过5MB');
      return;
    }
    const fd = new FormData();
    fd.append('file', f);
    setBusy(true);
    try {
      const c = await import('@/lib/config').then(m => m.getConfig());
      const t = getAccessTokenFromCookie();
      const h: any = {};
      if (t) h['Authorization'] = `Bearer ${t}`;
      const r = await fetch(`${c.API_BASE_URL}${c.API_PREFIX}/users/me/avatar`, {
        method: 'POST',
        body: fd,
        credentials: 'include',
        headers: h,
      });
      const d = await r.json();
      if (r.ok && d.success) {
        const rd = new FileReader();
        rd.onload = e2 => setAv(e2.target?.result as string);
        rd.readAsDataURL(f);
        flashSaved('avatar');
      } else alert(d.error || '上传失败');
    } catch {
    } finally {
      setBusy(false);
    }
  };

  const changePw = async () => {
    if (pw.new !== pw.con) {
      alert('两次密码不一致');
      return;
    }
    if (pw.new.length < 6) {
      alert('密码至少6位');
      return;
    }
    setBusy(true);
    try {
      const c = await import('@/lib/config').then(m => m.getConfig());
      const fd = new FormData();
      fd.append('current_password', pw.cur);
      fd.append('new_password', pw.new);
      fd.append('confirm_password', pw.con);
      const r = await fetch(`${c.API_BASE_URL}${c.API_PREFIX}/users/me/change-password`, {
        method: 'POST',
        body: fd,
        credentials: 'include',
      });
      const d = await r.json();
      if (r.ok && d.success) {
        alert('密码已更新，请重新登录');
        window.location.href = '/login';
      } else alert(d.error || '失败');
    } catch {
    } finally {
      setBusy(false);
    }
  };

  const setup2FA = async () => {
    const r = await apiClient.get(SECURITY.TWO_FA_SETUP);
    if (r.success && r.data) {
      setQr(r.data.qr_code);
      setSecret(r.data.secret);
    }
  };

  const enable2FA = async () => {
    if (vc.length !== 6) {
      alert('输入6位验证码');
      return;
    }
    const r = await apiClient.post(SECURITY.TWO_FA_ENABLE, {totp_token: vc});
    if (r.success) {
      setFa(true);
      setQr('');
      setCodes((r.data as any)?.backup_codes || []);
    }
  };

  const disable2FA = async () => {
    if (!(await confirm({message: '禁用2FA？', variant: 'warning'}))) return;
    const r = await apiClient.post(SECURITY.TWO_FA_DISABLE);
    if (r.success) {
      setFa(false);
      setQr('');
      setSecret('');
      setCodes([]);
    }
  };

  const loadS = async () => {
    const r = await apiClient.get(SECURITY.MY_SESSIONS);
    if (r.success && r.data) {
      const raw = r.data.sessions || r.data.data?.sessions || [];
      setSessions(Array.isArray(raw) ? raw : []);
    }
  };
  useEffect(() => {
    if (tab === 3) loadS();
  }, [tab]);

  const revokeSession = async (sessionId: string) => {
    const r = await apiClient.post(SECURITY.REVOKE_SESSION, {session_id: sessionId});
    if (r.success)
      setSessions(prev => prev.filter(s => s.session_id !== sessionId && s.id !== sessionId));
    else alert(r.error || '注销失败');
  };

  const revokeAllOther = async () => {
    if (!(await confirm({message: '这将注销所有其他设备，确定继续？', variant: 'warning'}))) return;
    const r = await apiClient.post(SECURITY.REVOKE_ALL_SESSIONS, {});
    if (r.success) loadS();
    else alert(r.error || '操作失败');
  };

  const handleLogout = async () => {
    try {
      await apiClient.post(AUTH.LOGOUT);
    } catch {}
    document.cookie = 'access_token=;path=/;expires=Thu,01 Jan 1970 00:00:00 UTC';
    document.cookie = 'refresh_token=;path=/;expires=Thu,01 Jan 1970 00:00:00 UTC';
    // 清除 localStorage 中可能缓存的数据
    localStorage.clear();
    window.location.href = '/login';
  };

  const formatDevice = (s: any): string => {
    const info = s.device_info || s;
    if (typeof info === 'string') return info;
    const parts: string[] = [];
    if (info.browser) parts.push(info.browser);
    if (info.platform) parts.push(info.platform);
    if (info.os) parts.push(info.os);
    return parts.length ? parts.join(' · ') : (s.device || s.user_agent?.slice(0, 50) || '未知设备');
  };

  const getDeviceIcon = (s: any) => {
    const info = s.device_info || s;
    const ua = (info.user_agent || info.browser || '').toLowerCase();
    if (ua.includes('mobile') || ua.includes('android') || ua.includes('iphone'))
      return <Smartphone className="w-4 h-4"/>;
    return <Monitor className="w-4 h-4"/>;
  };

  return {
    tab, setTab,
    p, setP,
    av, setAv,
    un, setUn,
    bio, setBio,
    loc, setLoc,
    priv, setPriv,
    pw, setPw,
    showPw, setShowPw,
    fa, setFa,
    qr, setQr,
    secret, setSecret,
    vc, setVc,
    codes, setCodes,
    sessions, setSessions,
    busy, savedField, pwStrength,
    avRef,
    save,
    uploadAv,
    changePw,
    setup2FA,
    enable2FA,
    disable2FA,
    loadS,
    revokeSession,
    revokeAllOther,
    handleLogout,
    formatDevice,
    getDeviceIcon,
    TABS,
    flashSaved,
    pwStrengthColors,
    pwStrengthLabels,
    theme, setTheme,
  };
}
