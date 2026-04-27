'use client';

import {useEffect, useState} from 'react';
import {Button} from '@/components/ui/button';
import {Globe} from 'lucide-react';
import {getDirection, isRTL, locales} from '@/i18n';

const localeNames: Record<string, string> = {
  'zh-CN': '简体中文',
  'en': 'English',
  'ar': 'العربية (Arabic)',
  'he': 'עברית (Hebrew)',
};

export default function LanguageSwitcher() {
  const [currentLocale, setCurrentLocale] = useState<string>('zh-CN');

  useEffect(() => {
    // 从localStorage加载语言设置
    const savedLocale = localStorage.getItem('locale');
    if (savedLocale && locales.includes(savedLocale as typeof locales[number])) {
      setCurrentLocale(savedLocale);
      applyLocale(savedLocale);
    }
  }, []);

  const handleLocaleChange = (locale: string) => {
    setCurrentLocale(locale);
    localStorage.setItem('locale', locale);

    // 先应用语言设置
    applyLocale(locale);

    // 尝试触发浏览器翻译
    triggerNativeTranslation(locale);

    // 延迟刷新页面以应用RTL/LTR变化
    setTimeout(() => {
      window.location.reload();
    }, 1000);
  };

  const triggerNativeTranslation = (targetLang: string) => {
    // 方法1: 移除notranslate标记(如果存在)
    const metaNotranslate = document.querySelector('meta[name="google"][content="notranslate"]');
    if (metaNotranslate) {
      metaNotranslate.remove();
    }

    // 方法2: 确保html标签有正确的lang属性
    document.documentElement.lang = targetLang;

    // 方法3: 添加translate=yes属性
    document.documentElement.setAttribute('translate', 'yes');

    // 方法4: 对于Chrome/Edge,可以通过修改URL hash来触发
    // 这会迫使浏览器重新检测页面语言
    const currentHash = window.location.hash;
    window.location.hash = `#lang-${targetLang}`;

    // 方法5: 触发自定义事件(某些浏览器扩展会监听)
    window.dispatchEvent(new CustomEvent('languagechange', {
      detail: {language: targetLang}
    }));

    console.log(`Translation triggered for: ${targetLang}`);
    console.log('If translation bar does not appear, please right-click and select "Translate to ' + localeNames[targetLang] + '"');
  };

  const applyLocale = (locale: string) => {
    const direction = getDirection(locale as typeof locales[number]);
    document.documentElement.lang = locale;
    document.documentElement.dir = direction;
    
    // 添加/移除RTL类
    if (direction === 'rtl') {
      document.documentElement.classList.add('rtl');
    } else {
      document.documentElement.classList.remove('rtl');
    }
  };

  return (
      <div className="relative group">
      <Button variant="outline" size="sm" className="flex items-center space-x-2">
        <Globe className="w-4 h-4" />
        <span>{localeNames[currentLocale]}</span>
      </Button>

        {/* 语言选择下拉菜单 - 使用CSS hover显示 */}
        <div
            className="absolute right-0 top-full mt-2 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg z-50 min-w-[200px] py-1 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200">
        {locales.map((locale) => (
          <button
            key={locale}
            onClick={() => handleLocaleChange(locale)}
            className={`w-full text-left px-4 py-2 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors ${
                currentLocale === locale ? 'bg-blue-50 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400' : 'text-gray-700 dark:text-gray-300'
            }`}
          >
            {localeNames[locale]}
            {isRTL(locale as typeof locales[number]) && (
              <span className="ml-2 text-xs text-gray-500">(RTL)</span>
            )}
          </button>
        ))}
      </div>
    </div>
  );
}
