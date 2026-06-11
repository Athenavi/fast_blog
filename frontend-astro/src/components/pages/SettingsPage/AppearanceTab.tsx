'use client';

import React from 'react';
import {Check, Monitor, Moon, Palette, Sun} from 'lucide-react';

interface Props {
  theme: string;
  onSetTheme: (theme: string) => void;
}

const AppearanceTab: React.FC<Props> = ({theme, onSetTheme}) => {
  const themes = [
    {
      id: 'light',
      label: '浅色',
      icon: Sun,
      gradient: 'from-amber-50 to-orange-50',
      activeBorder: 'border-amber-400',
    },
    {
      id: 'dark',
      label: '深色',
      icon: Moon,
      gradient: 'from-gray-800 to-gray-900',
      activeBorder: 'border-blue-400',
    },
    {
      id: 'system',
      label: '跟随系统',
      icon: Monitor,
      gradient: 'from-blue-50 to-indigo-50',
      activeBorder: 'border-indigo-400',
    },
  ];

  return (
    <div className="space-y-6">
      <div className="bg-white dark:bg-gray-800 rounded-2xl border border-gray-100 dark:border-gray-700 shadow-sm p-6">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 bg-purple-100 dark:bg-purple-900/30 rounded-xl flex items-center justify-center">
            <Palette className="w-5 h-5 text-purple-600 dark:text-purple-400"/>
          </div>
          <div>
            <h3 className="font-semibold text-gray-900 dark:text-white">主题设置</h3>
            <p className="text-xs text-gray-500 dark:text-gray-400">选择你喜欢的界面主题</p>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-4">
          {themes.map(t => {
            const Icon = t.icon;
            const isActive = theme === t.id;
            return (
              <button
                key={t.id}
                onClick={() => onSetTheme(t.id)}
                className={`relative p-5 rounded-2xl border-2 transition-all duration-200 ${
                  isActive
                    ? `${t.activeBorder} bg-gradient-to-br ${t.gradient} dark:from-gray-700 dark:to-gray-800 shadow-md`
                    : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600 bg-white dark:bg-gray-800'
                }`}
              >
                {isActive && (
                  <div className="absolute top-2 right-2 w-5 h-5 bg-blue-500 rounded-full flex items-center justify-center">
                    <Check className="w-3 h-3 text-white"/>
                  </div>
                )}
                <Icon className={`w-8 h-8 mx-auto mb-3 ${isActive ? 'text-blue-600 dark:text-blue-400' : 'text-gray-400'}`}/>
                <span className={`text-sm font-medium ${isActive ? 'text-gray-900 dark:text-white' : 'text-gray-600 dark:text-gray-400'}`}>
                  {t.label}
                </span>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
};

export default AppearanceTab;
