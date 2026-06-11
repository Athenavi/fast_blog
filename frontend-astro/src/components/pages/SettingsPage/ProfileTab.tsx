'use client';

import React from 'react';
import {Camera, Check, User, Globe} from 'lucide-react';

interface Props {
  un: string;
  bio: string;
  loc: string;
  priv: boolean;
  av: string;
  savedField: string | null;
  busy: boolean;
  p: any;
  avRef: React.RefObject<HTMLInputElement | null>;
  onUploadAv: (e: React.ChangeEvent<HTMLInputElement>) => void;
  onSave: (field: string, value: any) => void;
  onChangeUn: (v: string) => void;
  onChangeBio: (v: string) => void;
  onChangeLoc: (v: string) => void;
  onChangePriv: (v: boolean) => void;
}

const ProfileTab: React.FC<Props> = ({
  un, bio, loc, priv, av, savedField, busy, p, avRef,
  onUploadAv, onSave, onChangeUn, onChangeBio, onChangeLoc, onChangePriv,
}) => {
  return (
    <div className="space-y-6">
      {/* Avatar Section */}
      <div className="bg-white dark:bg-gray-800 rounded-2xl border border-gray-100 dark:border-gray-700 shadow-sm overflow-hidden">
        <div className="h-20 bg-gradient-to-r from-blue-500 to-indigo-500"/>
        <div className="px-6 pb-6">
          <div className="flex flex-col sm:flex-row items-start sm:items-end gap-4 -mt-10">
            <div className="relative group">
              <img
                src={av}
                alt=""
                className="w-20 h-20 rounded-2xl object-cover border-4 border-white dark:border-gray-800 shadow-lg bg-gray-100"
                onError={e => {
                  (e.target as HTMLImageElement).src = `https://ui-avatars.com/api/?name=${encodeURIComponent(p?.username || 'U')}&background=random`
                }}
              />
              <button
                onClick={() => avRef.current?.click()}
                className="absolute inset-0 bg-black/40 rounded-2xl opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center"
              >
                <Camera className="w-6 h-6 text-white"/>
              </button>
              {savedField === 'avatar' && (
                <div className="absolute -top-2 -right-2 w-6 h-6 bg-green-500 rounded-full flex items-center justify-center">
                  <Check className="w-3.5 h-3.5 text-white"/>
                </div>
              )}
              <input ref={avRef} type="file" accept="image/jpeg,image/png,image/webp" className="hidden" onChange={onUploadAv}/>
            </div>
            <div className="flex-1 min-w-0">
              <p className="font-semibold text-gray-900 dark:text-white">{p?.username || '用户'}</p>
              <p className="text-sm text-gray-500 dark:text-gray-400">{p?.email || ''}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Username */}
      <div className="bg-white dark:bg-gray-800 rounded-2xl border border-gray-100 dark:border-gray-700 shadow-sm p-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 bg-blue-100 dark:bg-blue-900/30 rounded-xl flex items-center justify-center">
            <User className="w-5 h-5 text-blue-600 dark:text-blue-400"/>
          </div>
          <div>
            <h3 className="font-semibold text-gray-900 dark:text-white">用户名</h3>
            <p className="text-xs text-gray-500 dark:text-gray-400">你的唯一标识</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <div className="relative flex-1">
            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 text-sm">@</span>
            <input
              type="text"
              value={un}
              onChange={e => onChangeUn(e.target.value)}
              className="w-full pl-8 pr-4 py-2.5 bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-600 rounded-xl text-sm text-gray-900 dark:text-white focus:outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-500/10 transition-all"
            />
          </div>
          <button
            onClick={() => onSave('username', un)}
            disabled={busy}
            className="px-4 py-2.5 bg-blue-600 text-white text-sm font-medium rounded-xl hover:bg-blue-700 disabled:opacity-50 shrink-0 transition-colors"
          >
            {busy ? '保存中…' : (savedField === 'username' ? <Check className="w-4 h-4"/> : '保存')}
          </button>
        </div>
      </div>

      {/* Bio */}
      <div className="bg-white dark:bg-gray-800 rounded-2xl border border-gray-100 dark:border-gray-700 shadow-sm p-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 bg-purple-100 dark:bg-purple-900/30 rounded-xl flex items-center justify-center">
            <svg className="w-5 h-5 text-purple-600 dark:text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16m-7 6h7"/></svg>
          </div>
          <div>
            <h3 className="font-semibold text-gray-900 dark:text-white">个人简介</h3>
            <p className="text-xs text-gray-500 dark:text-gray-400">向大家介绍你自己</p>
          </div>
        </div>
        <div className="flex items-start gap-3">
          <textarea
            value={bio}
            onChange={e => onChangeBio(e.target.value)}
            rows={3}
            className="flex-1 px-4 py-2.5 bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-600 rounded-xl text-sm text-gray-900 dark:text-white focus:outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-500/10 transition-all resize-none"
            placeholder="介绍一下自己…"
          />
          <button
            onClick={() => onSave('bio', bio)}
            disabled={busy}
            className="px-4 py-2.5 bg-blue-600 text-white text-sm font-medium rounded-xl hover:bg-blue-700 disabled:opacity-50 shrink-0 transition-colors"
          >
            {busy ? '保存中…' : (savedField === 'bio' ? <Check className="w-4 h-4"/> : '保存')}
          </button>
        </div>
      </div>

      {/* Language */}
      <div className="bg-white dark:bg-gray-800 rounded-2xl border border-gray-100 dark:border-gray-700 shadow-sm p-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 bg-green-100 dark:bg-green-900/30 rounded-xl flex items-center justify-center">
            <Globe className="w-5 h-5 text-green-600 dark:text-green-400"/>
          </div>
          <div>
            <h3 className="font-semibold text-gray-900 dark:text-white">界面语言</h3>
            <p className="text-xs text-gray-500 dark:text-gray-400">选择你的首选语言</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <select
            value={loc}
            onChange={e => onChangeLoc(e.target.value)}
            className="flex-1 px-4 py-2.5 bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-600 rounded-xl text-sm text-gray-900 dark:text-white focus:outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-500/10 transition-all"
          >
            <option value="zh_CN">中文（简体）</option>
            <option value="zh_TW">中文（繁体）</option>
            <option value="en">English</option>
            <option value="ja">日本語</option>
          </select>
          <button
            onClick={() => onSave('locale', loc)}
            disabled={busy}
            className="px-4 py-2.5 bg-blue-600 text-white text-sm font-medium rounded-xl hover:bg-blue-700 disabled:opacity-50 shrink-0 transition-colors"
          >
            {busy ? '保存中…' : (savedField === 'locale' ? <Check className="w-4 h-4"/> : '保存')}
          </button>
        </div>
      </div>

      {/* Privacy */}
      <div className="bg-white dark:bg-gray-800 rounded-2xl border border-gray-100 dark:border-gray-700 shadow-sm p-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 bg-amber-100 dark:bg-amber-900/30 rounded-xl flex items-center justify-center">
            <svg className="w-5 h-5 text-amber-600 dark:text-amber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"/></svg>
          </div>
          <div>
            <h3 className="font-semibold text-gray-900 dark:text-white">隐私设置</h3>
            <p className="text-xs text-gray-500 dark:text-gray-400">控制你的个人资料可见性</p>
          </div>
        </div>
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-gray-900 dark:text-white">私密资料</p>
            <p className="text-xs text-gray-500 dark:text-gray-400">开启后只有登录用户可查看你的资料</p>
          </div>
          <button
            onClick={() => onChangePriv(!priv)}
            className={`relative w-11 h-6 rounded-full transition-colors ${priv ? 'bg-blue-600' : 'bg-gray-300 dark:bg-gray-600'}`}
          >
            <div className={`absolute top-0.5 w-5 h-5 bg-white rounded-full shadow transition-transform ${priv ? 'translate-x-[22px]' : 'translate-x-0.5'}`}/>
          </button>
        </div>
      </div>
    </div>
  );
};

export default ProfileTab;
