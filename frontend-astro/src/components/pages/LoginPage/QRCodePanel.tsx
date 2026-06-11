'use client';

import React from 'react';
import {Loader, QrCode} from 'lucide-react';
import {useTranslation} from '@/lib/i18n';

interface Props {
  qrImg: string;
  qrStatus: 'idle' | 'loading' | 'ready' | 'pending' | 'success' | 'expired';
  countdown: number;
  onGenerate: () => void;
}

const QRCodePanel: React.FC<Props> = ({qrImg, qrStatus, countdown, onGenerate}) => {
  const {t} = useTranslation();

  return (
    <div className="space-y-6">
      <div className="bg-white dark:bg-gray-800 rounded-3xl p-8 border border-gray-100 dark:border-gray-700 shadow-sm">
        <div className="text-center space-y-5">
          {/* QR Display */}
          <div className="flex justify-center">
            {qrStatus === 'loading' ? (
              <div className="w-[220px] h-[220px] bg-gray-50 dark:bg-gray-900 rounded-2xl animate-pulse flex items-center justify-center">
                <div className="flex flex-col items-center gap-3">
                  <Loader className="w-8 h-8 animate-spin text-blue-500"/>
                  <span className="text-sm text-gray-400">{t('login.qrGenerating')}</span>
                </div>
              </div>
            ) : qrImg ? (
              <div className="relative p-4 bg-white rounded-2xl border-2 border-gray-100 shadow-lg">
                <img src={qrImg} alt="Login QR Code" className="w-[200px] h-[200px]"/>
                {qrStatus === 'success' && (
                  <div className="absolute inset-0 bg-green-500/90 rounded-2xl flex items-center justify-center">
                    <svg className="w-16 h-16 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7"/>
                    </svg>
                  </div>
                )}
                {qrStatus === 'expired' && (
                  <div className="absolute inset-0 bg-orange-500/85 rounded-2xl flex flex-col items-center justify-center gap-2">
                    <svg className="w-14 h-14 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>
                    </svg>
                    <span className="text-white text-sm font-medium">{t('login.qrExpiredAutoRefresh')}</span>
                  </div>
                )}
              </div>
            ) : (
              <div className="w-[220px] h-[220px] bg-gray-50 dark:bg-gray-900 rounded-2xl border-2 border-dashed border-gray-200 dark:border-gray-700 flex flex-col items-center justify-center gap-3 cursor-pointer hover:border-blue-300 dark:hover:border-blue-700 transition-colors" onClick={onGenerate}>
                <QrCode className="w-10 h-10 text-gray-300 dark:text-gray-600"/>
                <span className="text-sm text-gray-400">{t('login.qrClickToGenerate')}</span>
              </div>
            )}
          </div>

          {/* Status Text */}
          <div className="space-y-2">
            <p className="text-sm font-medium text-gray-700 dark:text-gray-300">
              {qrStatus === 'loading' ? t('login.generatingQR') :
                qrStatus === 'ready' || qrStatus === 'pending' ? (
                  <span className="flex flex-col items-center gap-1">
                    <span className="flex items-center justify-center gap-2">
                      <span className="w-2 h-2 bg-blue-500 rounded-full animate-pulse"/>
                      {t('login.qrWaitingScan')}
                    </span>
                    {countdown > 0 && (
                      <span className={`text-xs ${countdown <= 30 ? 'text-orange-500 font-semibold' : 'text-gray-400 dark:text-gray-500'}`}>
                        {t('login.qrExpiresIn', {seconds: countdown})}
                      </span>
                    )}
                  </span>
                ) : qrStatus === 'success' ? `✅ ${t('login.qrScanSuccess')}` :
                  qrStatus === 'expired' ? t('login.qrExpiredAutoRefresh') : t('login.scanQRCode')}
            </p>
          </div>

          {/* Action Buttons */}
          {(qrStatus === 'expired' || qrStatus === 'idle') && (
            <button onClick={onGenerate}
              className="px-6 py-3 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white text-sm font-semibold rounded-xl transition-all shadow-md hover:shadow-lg active:scale-[0.98]">
              {qrStatus === 'expired' ? t('login.qrRegenerate') : t('login.qrGenerate')}
            </button>
          )}
        </div>
      </div>

      {/* Instructions */}
      <div className="bg-gray-50 dark:bg-gray-800/50 rounded-2xl p-5 border border-gray-100 dark:border-gray-800">
        <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">{t('login.scanSteps')}</h3>
        <ol className="space-y-2.5">
          {[t('login.scanStep1'), t('login.scanStep2'), t('login.scanStep3'), t('login.scanStep4')].map((step, i) => (
            <li key={i} className="flex items-center gap-3 text-sm text-gray-600 dark:text-gray-400">
              <span className="w-6 h-6 bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0">{i + 1}</span>
              {step}
            </li>
          ))}
        </ol>
      </div>
    </div>
  );
};

export default QRCodePanel;
