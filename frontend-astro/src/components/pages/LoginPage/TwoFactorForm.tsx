'use client';

import React from 'react';
import {Controller, FormProvider} from 'react-hook-form';
import {AlertCircle, ArrowLeft, Loader, Smartphone} from 'lucide-react';
import {useTranslation} from '@/lib/i18n';
import type {UseFormReturn} from 'react-hook-form';
import type {TwoFactorFormData} from '@/lib/schemas';

interface Props {
  twoFAForm: UseFormReturn<TwoFactorFormData>;
  backup: boolean;
  busy: boolean;
  err: string;
  onToggleBackup: () => void;
  onBack: () => void;
  onSubmit: (data: TwoFactorFormData) => void;
}

const TwoFactorForm: React.FC<Props> = ({twoFAForm, backup, busy, err, onToggleBackup, onBack, onSubmit}) => {
  const {t} = useTranslation();

  return (
    <FormProvider {...twoFAForm}>
      <div className="space-y-6">
        <div className="text-center p-6 bg-gradient-to-br from-indigo-50 to-blue-50 dark:from-indigo-900/20 dark:to-blue-900/20 rounded-2xl border border-indigo-100 dark:border-indigo-800/30">
          <div className="w-16 h-16 mx-auto mb-4 bg-gradient-to-br from-indigo-500 to-blue-500 rounded-2xl flex items-center justify-center shadow-lg">
            <Smartphone className="w-8 h-8 text-white"/>
          </div>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            {backup ? t('login.twoFactorBackupHint') : t('login.twoFactorCodeHint')}
          </p>
        </div>

        <form onSubmit={twoFAForm.handleSubmit(onSubmit)} className="space-y-4">
          <Controller
            name="code"
            control={twoFAForm.control}
            render={({field}) => (
              <div className="relative">
                <input
                  type="text" inputMode="numeric" autoFocus
                  value={field.value}
                  onChange={e => field.onChange(e.target.value.replace(/\D/g, '').slice(0, backup ? 8 : 6))}
                  placeholder={backup ? t('login.twoFactorPlaceholder') : '000000'}
                  className="w-full text-center text-3xl tracking-[0.5em] px-6 py-5 bg-white dark:bg-gray-800 border-2 border-gray-200 dark:border-gray-700 rounded-2xl focus:outline-none focus:border-indigo-500 focus:ring-4 focus:ring-indigo-500/10 dark:text-white font-mono transition-all"
                />
                {twoFAForm.formState.errors.code && (
                  <p className="text-xs text-red-500 dark:text-red-400 text-center mt-2">
                    {twoFAForm.formState.errors.code.message}
                  </p>
                )}
              </div>
            )}
          />

          <button type="submit" disabled={busy}
            className="w-full py-4 bg-gradient-to-r from-indigo-600 to-blue-600 hover:from-indigo-700 hover:to-blue-700 text-white font-semibold rounded-2xl transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-indigo-500/25 hover:shadow-xl hover:shadow-indigo-500/30 active:scale-[0.98]">
            {busy ? (
              <span className="flex items-center justify-center gap-2"><Loader className="w-5 h-5 animate-spin"/> {t('login.twoFactorVerifying')}</span>
            ) : t('login.verifyButton')}
          </button>

          <div className="flex items-center justify-between pt-2">
            <button type="button" onClick={onToggleBackup}
              className="text-sm text-indigo-600 hover:text-indigo-700 dark:text-indigo-400 font-medium">
              {backup ? t('login.twoFactorUseCode') : t('login.twoFactorUseBackup')}
            </button>
            <button type="button" onClick={onBack}
              className="flex items-center gap-1 text-sm text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300">
              <ArrowLeft className="w-4 h-4"/> {t('login.backToLogin')}
            </button>
          </div>
        </form>
      </div>
    </FormProvider>
  );
};

export default TwoFactorForm;
