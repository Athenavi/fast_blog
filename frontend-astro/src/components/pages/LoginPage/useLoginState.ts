'use client';

import { useState, useCallback } from 'react';
import { apiClient } from '@/lib/api/base-client';

interface LoginState {
  step: 'credentials' | 'twofactor' | 'qrcode' | 'loggedin' | 'error';
  loading: boolean;
  error: string | null;
  sessionToken?: string;
  rememberMe: boolean;
  needs2FA: boolean;
  user?: any;
}

interface UseLoginStateReturn {
  state: LoginState;
  submitCredentials: (username: string, password: string, rememberMe?: boolean) => Promise<void>;
  submit2FA: (code: string, isBackup?: boolean) => Promise<void>;
  submitQRCode: (token: string) => Promise<void>;
  logout: () => void;
  reset: () => void;
}

export function useLoginState(): UseLoginStateReturn {
  const [state, setState] = useState<LoginState>({
    step: 'credentials',
    loading: false,
    error: null,
    rememberMe: false,
    needs2FA: false,
  });

  const submitCredentials = useCallback(async (username: string, password: string, rememberMe?: boolean) => {
    setState(prev => ({ ...prev, loading: true, error: null }));
    try {
      const res = await apiClient.post('/auth/login', { username, password, rememberMe });
      const data = res.data;
      
      if (data?.requires_2fa) {
        // User has 2FA enabled - go to 2FA step
        setState(prev => ({
          ...prev,
          step: 'twofactor',
          loading: false,
          sessionToken: data.session_token,
          rememberMe: rememberMe ?? false,
          needs2FA: true,
        }));
      } else if (data?.token || data?.access_token) {
        // Login successful
        const token = data.token || data.access_token;
        localStorage.setItem('auth_token', token);
        if (data.user) {
          localStorage.setItem('user', JSON.stringify(data.user));
        }
        setState(prev => ({
          ...prev,
          step: 'loggedin',
          loading: false,
          user: data.user,
        }));
      } else {
        setState(prev => ({
          ...prev,
          step: 'error',
          loading: false,
          error: data?.message || '登录失败，请重试',
        }));
      }
    } catch (err: any) {
      const msg = err?.response?.data?.detail || err?.response?.data?.message || err.message || '登录失败';
      setState(prev => ({
        ...prev,
        step: 'error',
        loading: false,
        error: msg,
      }));
    }
  }, []);

  const submit2FA = useCallback(async (code: string, isBackup?: boolean) => {
    setState(prev => ({ ...prev, loading: true, error: null }));
    try {
      const res = await apiClient.post('/auth/2fa/verify', {
        code,
        session_token: state.sessionToken,
        is_backup: isBackup,
      });
      const data = res.data;
      
      if (data?.token || data?.access_token) {
        const token = data.token || data.access_token;
        localStorage.setItem('auth_token', token);
        if (data.user) {
          localStorage.setItem('user', JSON.stringify(data.user));
        }
        setState(prev => ({
          ...prev,
          step: 'loggedin',
          loading: false,
          user: data.user,
        }));
      } else {
        setState(prev => ({
          ...prev,
          step: 'twofactor',
          loading: false,
          error: data?.message || '验证码错误',
        }));
      }
    } catch (err: any) {
      const msg = err?.response?.data?.detail || err?.response?.data?.message || '验证失败';
      setState(prev => ({
        ...prev,
        step: 'twofactor',
        loading: false,
        error: msg,
      }));
    }
  }, [state.sessionToken]);

  const submitQRCode = useCallback(async (token: string) => {
    setState(prev => ({ ...prev, loading: true, error: null }));
    try {
      const res = await apiClient.post('/auth/qr/verify', { token });
      const data = res.data;
      if (data?.token || data?.access_token) {
        const t = data.token || data.access_token;
        localStorage.setItem('auth_token', t);
        setState(prev => ({ ...prev, step: 'loggedin', loading: false, user: data.user }));
      } else {
        setState(prev => ({ ...prev, step: 'qrcode', loading: false, error: '二维码验证失败' }));
      }
    } catch (err: any) {
      setState(prev => ({ ...prev, step: 'qrcode', loading: false, error: '二维码验证失败' }));
    }
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem('auth_token');
    localStorage.removeItem('user');
    setState({
      step: 'credentials',
      loading: false,
      error: null,
      rememberMe: false,
      needs2FA: false,
    });
  }, []);

  const reset = useCallback(() => {
    setState({
      step: 'credentials',
      loading: false,
      error: null,
      rememberMe: false,
      needs2FA: false,
    });
  }, []);

  return { state, submitCredentials, submit2FA, submitQRCode, logout, reset };
}
