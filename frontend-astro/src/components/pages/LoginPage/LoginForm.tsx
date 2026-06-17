'use client';

import React from 'react';
import {FormProvider} from 'react-hook-form';
import {AlertCircle, ChevronRight, Eye, EyeOff, GitBranch, Globe, Loader} from 'lucide-react';
import {useTranslation} from '@/lib/i18n';
import type {UseFormReturn} from 'react-hook-form';
import type {LoginFormData} from '@/lib/schemas';

interface Props {
  loginForm: UseFormReturn<LoginFormData>;
  busy: boolean;
  pv: boolean;
  focusedField: string | null;
  onTogglePv: () => void;
  onFocusField: (field: string | null) => void;
  onSubmit: (data: LoginFormData) => void;
}

const LoginForm: React.FC<Props> = ({loginForm, busy, pv, focusedField, onTogglePv, onFocusField, onSubmit}) => {
  const {t} = useTranslation();

  const handleOAuthLogin = (provider: string) => {
    window.location.href = `/api/v2/oauth/authorize/${provider}`;
  };

  return (
    <FormProvider {...loginForm}>
      <form onSubmit={loginForm.handleSubmit(onSubmit)} className="space-y-5">
        {/* Username */}
        <div className="space-y-1.5">
          <label className="text-sm font-medium text-gray-700 dark:text-gray-300 ml-1">{t('login.emailOrUsername')}</label>
          <div className="relative">
            <div className={`absolute left-4 top-1/2 -translate-y-1/2 transition-colors ${focusedField === 'username' ? 'text-blue-500' : 'text-gray-400'}`}>
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z"/>
              </svg>
            </div>
            <input
              type="text" autoFocus autoComplete="username"
              {...loginForm.register('username')}
              onFocus={() => onFocusField('username')}
              onBlur={() => onFocusField(null)}
              placeholder={t('login.emailPlaceholder')}
              className={`w-full pl-12 pr-4 py-4 bg-white dark:bg-gray-800 border-2 rounded-2xl text-sm text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-500/10 transition-all ${
                loginForm.formState.errors.username ? 'border-red-400 dark:border-red-500' : 'border-gray-200 dark:border-gray-700'
              }`}
            />
          </div>
          {loginForm.formState.errors.username && (
            <p className="text-xs text-red-500 dark:text-red-400 flex items-center gap-1 pl-1">
              <AlertCircle className="w-3 h-3"/>{loginForm.formState.errors.username.message}
            </p>
          )}
        </div>

        {/* Password */}
        <div className="space-y-1.5">
          <label className="text-sm font-medium text-gray-700 dark:text-gray-300 ml-1">{t('login.password')}</label>
          <div className="relative">
            <div className={`absolute left-4 top-1/2 -translate-y-1/2 transition-colors ${focusedField === 'password' ? 'text-blue-500' : 'text-gray-400'}`}>
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M16.5 10.5V6.75a4.5 4.5 0 10-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 002.25-2.25v-6.75a2.25 2.25 0 00-2.25-2.25H6.75a2.25 2.25 0 00-2.25 2.25v6.75a2.25 2.25 0 002.25 2.25z"/>
              </svg>
            </div>
            <input
              type={pv ? 'text' : 'password'}
              {...loginForm.register('password')}
              onFocus={() => onFocusField('password')}
              onBlur={() => onFocusField(null)}
              placeholder={t('login.passwordPlaceholder')}
              className={`w-full pl-12 pr-12 py-4 bg-white dark:bg-gray-800 border-2 rounded-2xl text-sm text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-500/10 transition-all ${
                loginForm.formState.errors.password ? 'border-red-400 dark:border-red-500' : 'border-gray-200 dark:border-gray-700'
              }`}
            />
            <button type="button" onClick={onTogglePv}
              className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors">
              {pv ? <EyeOff className="w-5 h-5"/> : <Eye className="w-5 h-5"/>}
            </button>
          </div>
          {loginForm.formState.errors.password && (
            <p className="text-xs text-red-500 dark:text-red-400 flex items-center gap-1 pl-1">
              <AlertCircle className="w-3 h-3"/>{loginForm.formState.errors.password.message}
            </p>
          )}
        </div>

        {/* Remember Me */}
        <label className="flex items-center gap-3 cursor-pointer group">
          <div className="relative">
            <input type="checkbox" {...loginForm.register('remember')} className="peer sr-only"/>
            <div className="w-5 h-5 border-2 border-gray-300 dark:border-gray-600 rounded-lg peer-checked:border-blue-500 peer-checked:bg-blue-500 transition-all flex items-center justify-center">
              {loginForm.watch('remember') && (
                <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7"/>
                </svg>
              )}
            </div>
          </div>
          <span className="text-sm text-gray-600 dark:text-gray-400 group-hover:text-gray-800 dark:group-hover:text-gray-200 transition-colors">
            {t('login.rememberMeStatus')}
          </span>
        </label>

        {/* Submit */}
        <button type="submit" disabled={busy}
          className="w-full py-4 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white font-semibold rounded-2xl transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-blue-500/25 hover:shadow-xl hover:shadow-blue-500/30 active:scale-[0.98] flex items-center justify-center gap-2">
          {busy ? (
            <><Loader className="w-5 h-5 animate-spin"/><span>{t('login.loggingIn')}</span></>
          ) : (
            <><span>{t('login.loginButton')}</span><ChevronRight className="w-5 h-5"/></>
          )}
        </button>

        {/* Divider */}
        <div className="relative flex items-center py-2">
          <div className="flex-1 border-t border-gray-200 dark:border-gray-700"/>
          <span className="px-4 text-xs text-gray-400 dark:text-gray-500 font-medium">{t('login.orOtherMethods')}</span>
          <div className="flex-1 border-t border-gray-200 dark:border-gray-700"/>
        </div>

        {/* Social Login */}
        <div className="grid grid-cols-2 gap-3">
          <button type="button" onClick={() => handleOAuthLogin('github')}
            className="flex items-center justify-center gap-2 py-3.5 bg-white dark:bg-gray-800 border-2 border-gray-200 dark:border-gray-700 rounded-2xl text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-750 hover:border-gray-300 dark:hover:border-gray-600 transition-all active:scale-[0.98]">
            <GitBranch className="w-5 h-5"/> GitHub
          </button>
          <button type="button" onClick={() => handleOAuthLogin('google')}
            className="flex items-center justify-center gap-2 py-3.5 bg-white dark:bg-gray-800 border-2 border-gray-200 dark:border-gray-700 rounded-2xl text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-750 hover:border-gray-300 dark:hover:border-gray-600 transition-all active:scale-[0.98]">
            <Globe className="w-5 h-5"/> Google
          </button>
        </div>

        {/* Register */}
        <p className="text-center text-sm text-gray-500 dark:text-gray-400 pt-2">
          {t('login.noAccount')}{' '}
          <a href="/register" className="text-blue-600 hover:text-blue-700 dark:text-blue-400 font-semibold hover:underline">
            {t('login.registerNow')}
          </a>
        </p>
      </form>
    </FormProvider>
  );
};

export default LoginForm;
