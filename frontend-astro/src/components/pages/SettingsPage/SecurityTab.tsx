'use client';

import React from 'react';
import {AlertCircle, Check, CheckCircle2, Copy, Eye, EyeOff, Fingerprint, Lock, Shield} from 'lucide-react';

interface Props {
  pw: { cur: string; new: string; con: string };
  showPw: { cur: boolean; new: boolean; con: boolean };
  busy: boolean;
  pwStrength: number;
  fa: boolean;
  qr: string;
  secret: string;
  vc: string;
  codes: string[];
  onPwChange: (field: 'cur' | 'new' | 'con', value: string) => void;
  onShowPwToggle: (field: 'cur' | 'new' | 'con') => void;
  onChangePw: () => void;
  onSetup2FA: () => void;
  onEnable2FA: () => void;
  onDisable2FA: () => void;
  onVcChange: (value: string) => void;
  pwStrengthColors: string[];
  pwStrengthLabels: string[];
}

const SecurityTab: React.FC<Props> = ({
  pw, showPw, busy, pwStrength, fa, qr, secret, vc, codes,
  onPwChange, onShowPwToggle, onChangePw, onSetup2FA, onEnable2FA, onDisable2FA,
  onVcChange, pwStrengthColors, pwStrengthLabels,
}) => {
  const pwFields = [
    {key: 'cur' as const, label: '当前密码', placeholder: '输入当前密码'},
    {key: 'new' as const, label: '新密码', placeholder: '输入新密码'},
    {key: 'con' as const, label: '确认密码', placeholder: '再次输入新密码'},
  ];

  return (
    <div className="space-y-6">
      {/* Password Section */}
      <div className="bg-white dark:bg-gray-800 rounded-2xl border border-gray-100 dark:border-gray-700 shadow-sm p-6">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 bg-red-100 dark:bg-red-900/30 rounded-xl flex items-center justify-center">
            <Lock className="w-5 h-5 text-red-600 dark:text-red-400"/>
          </div>
          <div>
            <h3 className="font-semibold text-gray-900 dark:text-white">修改密码</h3>
            <p className="text-xs text-gray-500 dark:text-gray-400">定期更换密码可以提高账户安全性</p>
          </div>
        </div>

        <div className="space-y-4">
          {pwFields.map(f => (
            <div key={f.key}>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">{f.label}</label>
              <div className="relative">
                <input
                  type={showPw[f.key] ? 'text' : 'password'}
                  value={pw[f.key]}
                  onChange={e => onPwChange(f.key, e.target.value)}
                  placeholder={f.placeholder}
                  className="w-full pr-10 pl-4 py-2.5 bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-600 rounded-xl text-sm text-gray-900 dark:text-white focus:outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-500/10 transition-all"
                />
                <button
                  onClick={() => onShowPwToggle(f.key)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                >
                  {showPw[f.key] ? <EyeOff className="w-4 h-4"/> : <Eye className="w-4 h-4"/>}
                </button>
              </div>
            </div>
          ))}

          {/* Password Strength Bar */}
          {pw.new && (
            <div>
              <div className="flex items-center gap-2 mb-1.5">
                <div className="flex-1 h-1.5 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all duration-300 ${pwStrengthColors[pwStrength] || 'bg-gray-300'}`}
                    style={{width: `${(pwStrength / 5) * 100}%`}}
                  />
                </div>
                <span className="text-xs font-medium text-gray-500 dark:text-gray-400 w-12 text-right">
                  {pwStrengthLabels[pwStrength] || ''}
                </span>
              </div>
            </div>
          )}

          <button
            onClick={onChangePw}
            disabled={busy || !pw.cur || !pw.new || !pw.con}
            className="w-full py-2.5 bg-gradient-to-r from-red-500 to-red-600 text-white text-sm font-medium rounded-xl hover:from-red-600 hover:to-red-700 disabled:opacity-50 transition-all"
          >
            {busy ? '更新中…' : '更新密码'}
          </button>
        </div>
      </div>

      {/* 2FA Section */}
      <div className="bg-white dark:bg-gray-800 rounded-2xl border border-gray-100 dark:border-gray-700 shadow-sm p-6">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 bg-indigo-100 dark:bg-indigo-900/30 rounded-xl flex items-center justify-center">
            <Shield className="w-5 h-5 text-indigo-600 dark:text-indigo-400"/>
          </div>
          <div>
            <h3 className="font-semibold text-gray-900 dark:text-white">双重验证 (2FA)</h3>
            <p className="text-xs text-gray-500 dark:text-gray-400">为你的账户增加额外安全层</p>
          </div>
        </div>

        {!fa && !qr && (
          <button
            onClick={onSetup2FA}
            className="w-full py-3 px-4 bg-gradient-to-r from-indigo-500 to-purple-600 text-white text-sm font-medium rounded-xl hover:from-indigo-600 hover:to-purple-700 transition-all flex items-center justify-center gap-2"
          >
            <Fingerprint className="w-4 h-4"/>
            启用双重验证
          </button>
        )}

        {!fa && qr && (
          <div className="space-y-4">
            <div className="flex flex-col items-center p-6 bg-gray-50 dark:bg-gray-900 rounded-2xl">
              <img src={qr} alt="2FA QR Code" className="w-48 h-48 rounded-xl"/>
              {secret && (
                <div className="mt-3 flex items-center gap-2 px-4 py-2 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-600">
                  <code className="text-xs font-mono text-gray-600 dark:text-gray-400">{secret}</code>
                  <button
                    onClick={() => navigator.clipboard.writeText(secret)}
                    className="text-gray-400 hover:text-blue-500 rounded-lg hover:bg-blue-50 dark:hover:bg-blue-900/20"
                  >
                    <Copy className="w-3.5 h-3.5"/>
                  </button>
                </div>
              )}
            </div>
            <div className="flex gap-2 max-w-xs mx-auto">
              <input
                type="text"
                value={vc}
                onChange={e => onVcChange(e.target.value.replace(/\D/g, '').slice(0, 6))}
                placeholder="000000"
                className="flex-1 text-center text-xl tracking-[0.4em] px-3 py-3 border-2 border-gray-200 dark:border-gray-600 rounded-xl bg-gray-50 dark:bg-gray-900 focus:outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-500/10 dark:text-white font-mono transition-all"
              />
              <button
                onClick={onEnable2FA}
                className="px-5 py-3 bg-blue-600 text-white text-sm font-medium rounded-xl hover:bg-blue-700 shrink-0"
              >
                验证
              </button>
            </div>
          </div>
        )}

        {fa && (
          <div>
            <div className="flex items-center justify-between p-4 bg-green-50 dark:bg-green-900/20 rounded-2xl border border-green-200 dark:border-green-800/30">
              <div className="flex items-center gap-3">
                <CheckCircle2 className="w-5 h-5 text-green-600"/>
                <div>
                  <p className="text-sm font-medium text-green-800 dark:text-green-200">双重验证已启用</p>
                  <p className="text-xs text-green-700 dark:text-green-300">你的账户受到额外保护</p>
                </div>
              </div>
              <button
                onClick={onDisable2FA}
                className="px-3 py-1.5 text-xs font-medium text-red-500 bg-white dark:bg-gray-800 rounded-lg hover:bg-red-50 dark:hover:bg-red-900/20 border border-red-200 dark:border-red-800/30"
              >
                禁用
              </button>
            </div>

            {codes.length > 0 && (
              <div className="mt-4 p-5 bg-amber-50 dark:bg-amber-900/20 rounded-2xl border border-amber-200 dark:border-amber-800/30">
                <div className="flex items-center gap-2 mb-3">
                  <AlertCircle className="w-4 h-4 text-amber-600"/>
                  <span className="text-sm font-semibold text-amber-800 dark:text-amber-200">备用恢复码</span>
                </div>
                <p className="text-xs text-amber-700 dark:text-amber-300 mb-3">请妥善保存这些备用码，每个只能使用一次。</p>
                <div className="grid grid-cols-2 gap-2">
                  {codes.map(c => (
                    <code key={c} className="px-3 py-1.5 bg-white dark:bg-gray-800 rounded-lg text-xs font-mono text-gray-700 dark:text-gray-300 text-center">{c}</code>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default SecurityTab;
