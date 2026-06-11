'use client';

import React from 'react';
import {LogOut, Monitor, Palette, Shield, User} from 'lucide-react';
import {useSettingsState} from './useSettingsState';
import ProfileTab from './ProfileTab';
import SecurityTab from './SecurityTab';
import AppearanceTab from './AppearanceTab';
import SessionsTab from './SessionsTab';

const iconMap: Record<string, React.ElementType> = {
  User,
  Shield,
  Palette,
  Monitor,
};

function SettingsPageInner() {
  const {
    tab, setTab,
    p,
    av, un, bio, loc, priv,
    pw, showPw,
    fa, qr, secret, vc, codes,
    sessions,
    busy, savedField, pwStrength,
    avRef,
    save, uploadAv, changePw,
    setup2FA, enable2FA, disable2FA,
    loadS, revokeSession, revokeAllOther,
    handleLogout, formatDevice, getDeviceIcon,
    TABS,
    pwStrengthColors, pwStrengthLabels,
    theme, setTheme,
    setUn, setBio, setLoc, setPriv,
    setPw, setShowPw, setVc,
  } = useSettingsState();

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50 dark:from-gray-950 dark:to-gray-900">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-1">设置</h1>
          <p className="text-gray-500 dark:text-gray-400">管理你的账户设置和偏好</p>
        </div>

        <div className="flex flex-col lg:flex-row gap-6">
          {/* ═══ Sidebar Navigation ═══ */}
          <div className="lg:w-64 shrink-0">
            <nav className="bg-white dark:bg-gray-800 rounded-2xl border border-gray-100 dark:border-gray-700 shadow-sm overflow-hidden p-1.5">
              {TABS.map((t, i) => {
                const Icon = iconMap[t.icon as keyof typeof iconMap];
                return (
                  <button
                    key={t.id}
                    onClick={() => setTab(i)}
                    className={`w-full flex items-center gap-3 px-4 py-3.5 rounded-xl text-left transition-all duration-200 ${
                      tab === i
                        ? 'bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 text-blue-700 dark:text-blue-300 shadow-sm'
                        : 'text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-750'
                    }`}
                  >
                    <div className={`w-9 h-9 rounded-lg flex items-center justify-center shrink-0 ${
                      tab === i
                        ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400'
                        : 'bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400'
                    }`}>
                      <Icon className="w-4.5 h-4.5"/>
                    </div>
                    <div className="min-w-0">
                      <span className="block text-sm font-medium">{t.label}</span>
                      <span className="block text-[11px] opacity-60 truncate">{t.desc}</span>
                    </div>
                  </button>
                );
              })}

              {/* Logout */}
              <div className="border-t border-gray-100 dark:border-gray-700 mt-1.5 pt-1.5">
                <button
                  onClick={handleLogout}
                  className="w-full flex items-center gap-3 px-4 py-3.5 rounded-xl text-left text-red-500 hover:bg-red-50 dark:hover:bg-red-900/10 transition-colors"
                >
                  <div className="w-9 h-9 rounded-lg bg-red-100 dark:bg-red-900/20 flex items-center justify-center">
                    <LogOut className="w-4.5 h-4.5"/>
                  </div>
                  <span className="text-sm font-medium">退出登录</span>
                </button>
              </div>
            </nav>
          </div>

          {/* ═══ Main Content ═══ */}
          <div className="flex-1 min-w-0">
            {/* Profile Tab */}
            {tab === 0 && (
              <ProfileTab
                un={un}
                bio={bio}
                loc={loc}
                priv={priv}
                av={av}
                savedField={savedField}
                busy={busy}
                p={p}
                avRef={avRef}
                onUploadAv={uploadAv}
                onSave={save}
                onChangeUn={setUn}
                onChangeBio={setBio}
                onChangeLoc={setLoc}
                onChangePriv={setPriv}
              />
            )}

            {/* Security Tab */}
            {tab === 1 && (
              <SecurityTab
                pw={pw}
                showPw={showPw}
                busy={busy}
                pwStrength={pwStrength}
                fa={fa}
                qr={qr}
                secret={secret}
                vc={vc}
                codes={codes}
                onPwChange={(field, value) => setPw(prev => ({...prev, [field]: value}))}
                onShowPwToggle={(field) => setShowPw(prev => ({...prev, [field]: !prev[field]}))}
                onChangePw={changePw}
                onSetup2FA={setup2FA}
                onEnable2FA={enable2FA}
                onDisable2FA={disable2FA}
                onVcChange={setVc}
                pwStrengthColors={pwStrengthColors}
                pwStrengthLabels={pwStrengthLabels}
              />
            )}

            {/* Appearance Tab */}
            {tab === 2 && (
              <AppearanceTab
                theme={theme}
                onSetTheme={(t) => setTheme(t as any)}
              />
            )}

            {/* Sessions Tab */}
            {tab === 3 && (
              <SessionsTab
                sessions={sessions}
                onRevokeSession={revokeSession}
                onRevokeAllOther={revokeAllOther}
                onRefresh={loadS}
                formatDevice={formatDevice}
                getDeviceIcon={getDeviceIcon}
              />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default function SettingsPage() {
  return <SettingsPageInner />;
}
