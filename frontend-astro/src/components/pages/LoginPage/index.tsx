'use client';

import React, {useEffect, useState} from 'react';
import {useForm} from 'react-hook-form';
import {zodResolver} from '@hookform/resolvers/zod';
import {AlertCircle, BookOpen, Loader} from 'lucide-react';
import {useTranslation} from '@/lib/i18n';
import {useLoginState} from './useLoginState';
import LoginBranding from './LoginBranding';
import TwoFactorForm from './TwoFactorForm';
import LoginForm from './LoginForm';
import {type LoginFormData, loginSchema, type TwoFactorFormData, twoFactorSchema} from '@/lib/schemas';

const LoginPage: React.FC = () => {
  const {t} = useTranslation();
  const {state, submitCredentials, submit2FA} = useLoginState();

  // Visual-only state (no longer managed by the hook)
  const [pv, setPv] = useState(false);
  const [focusedField, setFocusedField] = useState<string | null>(null);
  const [backup, setBackup] = useState(false);

  const loginForm = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema) as any,
    defaultValues: {username: '', password: '', remember: false},
  });

  const twoFAForm = useForm<TwoFactorFormData>({
    resolver: zodResolver(twoFactorSchema),
    defaultValues: {code: ''},
  });

  const handleLoginSubmit = async (data: LoginFormData) => {
    await submitCredentials(data.username, data.password, data.remember);
  };

  const handle2FASubmit = async (data: TwoFactorFormData) => {
    await submit2FA(data.code, backup);
  };

  const handleBackToLogin = () => {
    twoFAForm.reset({code: ''});
    setBackup(false);
    // Reset the hook state
    window.location.reload();
  };

  // Redirect on successful login
  useEffect(() => {
    if (state.step === 'loggedin') {
      const timer = setTimeout(() => {
        const next = new URLSearchParams(window.location.search).get('next') || '/profile';
        window.location.href = next;
      }, 1500);
      return () => clearTimeout(timer);
    }
  }, [state.step]);

  // If logged in, show success / redirect
  if (state.step === 'loggedin') {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50 dark:from-gray-950 dark:via-gray-900 dark:to-gray-950">
        <div className="flex flex-col items-center gap-4">
          <div className="w-16 h-16 bg-green-500 rounded-full flex items-center justify-center">
            <svg className="w-8 h-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7"/>
            </svg>
          </div>
          <p className="text-lg font-semibold text-gray-900 dark:text-white">{t('login.loginSuccess')}</p>
          <div className="flex items-center gap-2 text-sm text-gray-500">
            <Loader className="w-4 h-4 animate-spin"/>
            <span>{t('login.redirecting')}</span>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50 dark:from-gray-950 dark:via-gray-900 dark:to-gray-950">
      <LoginBranding/>

      {/* ═══ Right Panel ═══ */}
      <div className="flex-1 flex items-center justify-center p-6 sm:p-8 lg:p-12">
        <div className="w-full max-w-md">
          {/* Mobile Logo */}
          <div className="lg:hidden flex items-center gap-3 mb-8">
            <div className="w-10 h-10 bg-gradient-to-br from-blue-600 to-indigo-600 rounded-xl flex items-center justify-center shadow-lg shadow-blue-200/50 dark:shadow-blue-900/30">
              <BookOpen className="w-5 h-5 text-white"/>
            </div>
            <span className="text-xl font-bold text-gray-900 dark:text-white">FastBlog</span>
          </div>

          {/* Header */}
          <div className="mb-8">
            <h1 className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-white mb-2">
              {state.step === 'twofactor' ? `🔐 ${t('login.twoFactorTitle')}` : `👋 ${t('login.title')}`}
            </h1>
            <p className="text-gray-500 dark:text-gray-400">
              {state.step === 'twofactor' ? t('login.twoFactorSubtitle') : t('login.subtitle')}
            </p>
          </div>

          {/* Error Message */}
          {state.error && (
            <div className="mb-6 flex items-start gap-3 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200/60 dark:border-red-800/40 rounded-2xl text-sm">
              <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5"/>
              <span className="text-red-600 dark:text-red-400">{state.error}</span>
            </div>
          )}

          {/* 2FA Form */}
          {state.step === 'twofactor' ? (
            <TwoFactorForm
              twoFAForm={twoFAForm}
              backup={backup}
              busy={state.loading}
              err={state.error || ''}
              onToggleBackup={() => { setBackup(b => !b); twoFAForm.reset({code: ''}); }}
              onBack={handleBackToLogin}
              onSubmit={handle2FASubmit}
            />
          ) : (
            <LoginForm
              loginForm={loginForm}
              busy={state.loading}
              pv={pv}
              focusedField={focusedField}
              onTogglePv={() => setPv(p => !p)}
              onFocusField={setFocusedField}
              onSubmit={handleLoginSubmit}
            />
          )}

          {/* Footer */}
          <div className="mt-8 text-center">
            <p className="text-xs text-gray-400 dark:text-gray-500">
              {t('login.agreeToTerms')}{' '}
              <a href="/terms" className="text-gray-500 dark:text-gray-400 hover:underline">{t('login.termsOfService')}</a>
              {' '}{t('common.and') || '和'}{' '}
              <a href="/privacy" className="text-gray-500 dark:text-gray-400 hover:underline">{t('login.privacyPolicy')}</a>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;
