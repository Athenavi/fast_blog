'use client';

import {useEffect, useRef, useState} from 'react';
import {useForm} from 'react-hook-form';
import {zodResolver} from '@hookform/resolvers/zod';
import {apiClient} from '@/lib/api/base-client';
import {AUTH, USERS, SECURITY} from '@/lib/api/api-paths';
import {getCookie, setCookie, dispatchAuthEvent} from '@/lib/auth-utils';
import {type LoginFormData, loginSchema, type TwoFactorFormData, twoFactorSchema} from '@/lib/schemas';
import {useTranslation} from '@/lib/i18n';

export function useLoginState() {
  const {t} = useTranslation();
  const [mode, setMode] = useState<'password' | 'qrcode'>('password');
  const [pv, setPv] = useState(false);
  const [err, setErr] = useState('');
  const [busy, setBusy] = useState(false);
  const [focusedField, setFocusedField] = useState<string | null>(null);

  // react-hook-form — 登录表单
  const loginForm = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema) as any,
    defaultValues: {username: '', password: '', remember: false},
  });

  // react-hook-form — 2FA 表单
  const twoFAForm = useForm<TwoFactorFormData>({
    resolver: zodResolver(twoFactorSchema),
    defaultValues: {code: ''},
  });

  // 2FA state
  const [fa, setFa] = useState<{ tempToken: string; userId: number } | null>(null);
  const [backup, setBackup] = useState(false);

  // QR code state
  const [qrImg, setQrImg] = useState('');
  const [qrToken, setQrToken] = useState('');
  const [qrStatus, setQrStatus] = useState<'idle' | 'loading' | 'ready' | 'pending' | 'success' | 'expired'>('idle');
  const pollRef = useRef<NodeJS.Timeout | undefined>(undefined);
  const cancelRef = useRef(false);
  const [countdown, setCountdown] = useState(0);
  const countdownTimerRef = useRef<NodeJS.Timeout | undefined>(undefined);
  const generateQRRef = useRef<(() => Promise<void>) | null>(null);

  // Auto-redirect if logged in
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const accessToken = getCookie('access_token');
        if (accessToken) {
          const r = await apiClient.get(USERS.ME);
          if (r.success && r.data) {
            window.location.href = new URLSearchParams(window.location.search).get('next') || '/profile';
            return;
          }
        }
        const refreshToken = getCookie('refresh_token');
        if (refreshToken) {
          const refreshResult = await apiClient.post(AUTH.REFRESH_TOKEN, {refresh: refreshToken});
          if (refreshResult.success && refreshResult.data) {
            const d = refreshResult.data as any;
            if (d.access_token) setCookie('access_token', d.access_token, 3600);
            if (d.refresh_token) setCookie('refresh_token', d.refresh_token, 604800);
            const r2 = await apiClient.get(USERS.ME);
            if (r2.success && r2.data) {
              dispatchAuthEvent(true);
              window.location.href = new URLSearchParams(window.location.search).get('next') || '/profile';
              return;
            }
          }
          setCookie('refresh_token', '', 0);
        }
      } catch { /* ignore */ }
      setChecking(false);
    })();
  }, []);

  const next = () => new URLSearchParams(window.location.search).get('next') || '/profile';

  // Cleanup
  useEffect(() => {
    return () => {
      cancelRef.current = true;
      if (pollRef.current) clearTimeout(pollRef.current);
      if (countdownTimerRef.current) clearInterval(countdownTimerRef.current);
    };
  }, []);

  // Keep generateQR ref current
  useEffect(() => {
    generateQRRef.current = generateQR;
  });

  // Countdown timer
  useEffect(() => {
    if (countdown <= 0 || qrStatus === 'success' || qrStatus === 'expired' || qrStatus === 'idle' || qrStatus === 'loading') return;
    countdownTimerRef.current = setInterval(() => {
      setCountdown(prev => {
        if (prev <= 1) { clearInterval(countdownTimerRef.current!); return 0; }
        return prev - 1;
      });
    }, 1000);
    return () => { if (countdownTimerRef.current) clearInterval(countdownTimerRef.current); };
  }, [countdown > 0, qrStatus]);

  // Auto-refresh QR on expiry
  useEffect(() => {
    if (countdown !== 0) return;
    if (qrStatus !== 'ready' && qrStatus !== 'pending') return;
    cancelRef.current = true;
    if (pollRef.current) clearTimeout(pollRef.current);
    setQrStatus('expired');
    const timer = setTimeout(() => {
      cancelRef.current = false;
      generateQRRef.current?.();
    }, 2000);
    return () => clearTimeout(timer);
  }, [countdown]);

  // QR Login Generator
  const generateQR = async () => {
    setErr(''); setQrStatus('loading'); setQrImg(''); setQrToken(''); cancelRef.current = false;
    try {
      const r = await apiClient.get(AUTH.QR_GENERATE);
      if (!r.success || !r.data) {
        setErr(r.error || t('login.qrGenerateFailed'));
        setQrStatus('idle');
        return;
      }
      const token = r.data.token || r.data.qr_token;
      const qrCodeDataUrl = r.data.qr_code || r.data.qr_data;
      setQrToken(token);
      if (qrCodeDataUrl && qrCodeDataUrl.startsWith('data:')) {
        setQrImg(qrCodeDataUrl);
      } else {
        try {
          const mod = await import('qrcode');
          const loginUrl = `${window.location.origin}/api/v2/mobile-login?login_token=${token}`;
          const dataUrl = await mod.toDataURL(loginUrl, {width: 280, margin: 2, color: {dark: '#1e40af', light: '#ffffff'}});
          setQrImg(dataUrl);
        } catch {
          setErr(t('login.qrGenerateFailed'));
          setQrStatus('idle');
          return;
        }
      }
      const expiresAt = r.data.expires_at ? parseInt(r.data.expires_at) * 1000 : Date.now() + 180000;
      setCountdown(Math.max(0, Math.floor((expiresAt - Date.now()) / 1000)));
      setQrStatus('ready');
      pollQR(token);
    } catch {
      setErr(t('login.qrGenerateFailed'));
      setQrStatus('idle');
    }
  };

  const pollQR = (token: string) => {
    if (cancelRef.current) return;
    pollRef.current = setTimeout(async () => {
      if (cancelRef.current) return;
      try {
        const r = await apiClient.get(AUTH.QR_STATUS, {token, 'no-cache': '1'});
        const data = r.success && r.data ? r.data : {status: 'pending'};
        const st = data.status;
        if (st === 'confirmed' || st === 'success') {
          setCountdown(0); setQrStatus('success');
          const refreshToken = data.refresh_token;
          if (refreshToken) setCookie('refresh_token', refreshToken, 604800);
          const accessR = await apiClient.post(AUTH.REFRESH_TOKEN, {refresh: refreshToken});
          if (accessR.success && accessR.data) {
            setCookie('access_token', (accessR.data as any).access_token || (accessR.data as any).access || '', 3600);
            dispatchAuthEvent(true);
            window.location.href = next();
            return;
          }
          setErr(t('login.qrScanSuccessButTokenFailed'));
          setQrStatus('idle');
          return;
        } else if (st === 'expired') {
          setCountdown(0); setQrStatus('expired'); setErr(t('login.qrExpired'));
          return;
        } else {
          setQrStatus('pending');
          pollQR(token);
        }
      } catch { if (!cancelRef.current) pollQR(token); }
    }, 2000);
  };

  // Password Login
  const onLoginSubmit = async (data: LoginFormData) => {
    setBusy(true); setErr('');
    try {
      const r = await apiClient.postForm(AUTH.LOGIN, {username: data.username, password: data.password, remember_me: data.remember});
      if (!r.success) { setErr(r.error || r.message || t('login.loginFailed')); setBusy(false); return; }
      const d = r.data as any;
      if (d.requires_2fa && d.temp_token) { setFa({tempToken: d.temp_token, userId: d.user_id}); setBusy(false); return; }
      if (d.access_token) setCookie('access_token', d.access_token, 3600);
      if (d.refresh_token) setCookie('refresh_token', d.refresh_token, 604800);
      dispatchAuthEvent(true);
      window.location.href = next();
    } catch { setErr(t('login.networkError')); setBusy(false); }
  };

  // 2FA
  const on2FASubmit = async (data: TwoFactorFormData) => {
    if (!fa) return;
    setBusy(true); setErr('');
    try {
      const r = await apiClient.post(SECURITY.TWO_FA_VERIFY_LOGIN, {user_id: fa.userId, token: data.code});
      if (r.success && r.data) {
        const d = r.data as any;
        if (d.access_token) setCookie('access_token', d.access_token, 3600);
        if (d.refresh_token) setCookie('refresh_token', d.refresh_token, 604800);
        dispatchAuthEvent(true);
        window.location.href = next();
      } else setErr(r.error || t('login.verificationFailed'));
    } catch { setErr(t('login.verificationFailed')); }
    finally { setBusy(false); }
  };

  return {
    t, mode, setMode, pv, setPv, err, setErr, busy, focusedField, setFocusedField,
    loginForm, twoFAForm, fa, setFa, backup, setBackup,
    qrImg, qrStatus, countdown, checking,
    generateQR, onLoginSubmit, on2FASubmit,
  };
}
