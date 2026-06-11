'use client';

import React from 'react';
import {AlertCircle, BookOpen, ChevronRight} from 'lucide-react';
import {useTranslation} from '@/lib/i18n';
import {useLoginState} from './useLoginState';
import LoginBranding from './LoginBranding';
import TwoFactorForm from './TwoFactorForm';
import LoginForm from './LoginForm';
import QRCodePanel from './QRCodePanel';

const LoginPage: React.FC = () => {
  const {t} = useTranslation();
  const s = useLoginState();

  if (s.checking) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50 dark:from-gray-950 dark:via-gray-900 dark:to-gray-950">
        <div className="flex flex-col items-center gap-4">
          <div className="relative">
            <div className="w-12 h-12 border-4 border-blue-200 dark:border-blue-800 rounded-full animate-spin"/>
            <div className="absolute inset-0 w-12 h-12 border-4 border-transparent border-t-blue-600 rounded-full animate-spin"/>
          </div>
          <p className="text-sm text-gray-500 dark:text-gray-400 animate-pulse">{t('login.verifyingStatus')}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50 dark:from-gray-950 dark:via-gray-900 dark:to-gray-950">
      <LoginBranding/>

      {/* ═══ Right Panel - Login Form ═══ */}
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
              {s.fa ? `🔐 ${t('login.twoFactorTitle')}` : s.mode === 'qrcode' ? `📱 ${t('login.qrLogin')}` : `👋 ${t('login.title')}`}
            </h1>
            <p className="text-gray-500 dark:text-gray-400">
              {s.fa ? t('login.twoFactorSubtitle') : s.mode === 'qrcode' ? t('login.scanQRCode') : t('login.subtitle')}
            </p>
          </div>

          {/* Error Message */}
          {s.err && (
            <div className="mb-6 flex items-start gap-3 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200/60 dark:border-red-800/40 rounded-2xl text-sm">
              <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5"/>
              <span className="text-red-600 dark:text-red-400">{s.err}</span>
            </div>
          )}

          {/* 2FA Form */}
          {s.fa ? (
            <TwoFactorForm
              twoFAForm={s.twoFAForm}
              backup={s.backup}
              busy={s.busy}
              err={s.err}
              onToggleBackup={() => { s.setBackup(!s.backup); s.twoFAForm.reset({code: ''}); }}
              onBack={() => { s.setFa(null); s.twoFAForm.reset({code: ''}); s.setErr(''); }}
              onSubmit={s.on2FASubmit}
            />
          ) : (
            <>
              {/* Mode Switch */}
              <div className="flex p-1.5 bg-gray-100 dark:bg-gray-800 rounded-2xl mb-6">
                <button onClick={() => s.setMode('password')}
                  className={`flex-1 py-2.5 text-sm font-semibold rounded-xl transition-all ${s.mode === 'password' ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm' : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'}`}>
                  {t('login.passwordLogin')}
                </button>
                <button onClick={() => { s.setMode('qrcode'); s.generateQR(); }}
                  className={`flex-1 py-2.5 text-sm font-semibold rounded-xl transition-all ${s.mode === 'qrcode' ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm' : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'}`}>
                  {t('login.qrLogin')}
                </button>
              </div>

              {/* Password Form */}
              {s.mode === 'password' && (
                <LoginForm
                  loginForm={s.loginForm}
                  busy={s.busy}
                  pv={s.pv}
                  focusedField={s.focusedField}
                  onTogglePv={() => s.setPv(!s.pv)}
                  onFocusField={s.setFocusedField}
                  onSubmit={s.onLoginSubmit}
                />
              )}

              {/* QR Code Panel */}
              {s.mode === 'qrcode' && (
                <QRCodePanel
                  qrImg={s.qrImg}
                  qrStatus={s.qrStatus}
                  countdown={s.countdown}
                  onGenerate={s.generateQR}
                />
              )}
            </>
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
