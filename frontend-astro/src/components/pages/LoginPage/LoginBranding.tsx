'use client';

import React from 'react';
import {BookOpen, Sparkles, Zap, Shield} from 'lucide-react';
import {useTranslation} from '@/lib/i18n';

const features = [
  {icon: Sparkles, titleKey: 'login.features.aiWriting', descKey: 'login.features.aiWritingDesc'},
  {icon: Zap, titleKey: 'login.features.fastPublish', descKey: 'login.features.fastPublishDesc'},
  {icon: BookOpen, titleKey: 'login.features.immersiveReading', descKey: 'login.features.immersiveReadingDesc'},
  {icon: Shield, titleKey: 'login.features.secure', descKey: 'login.features.secureDesc'},
];

const LoginBranding: React.FC = () => {
  const {t} = useTranslation();

  return (
    <div className="hidden lg:flex lg:w-1/2 xl:w-[45%] relative overflow-hidden">
      <div className="absolute inset-0 bg-gradient-to-br from-blue-600 via-indigo-600 to-purple-700"/>
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute -top-20 -left-20 w-80 h-80 bg-blue-400/20 rounded-full blur-3xl animate-pulse" style={{animationDuration: '4s'}}/>
        <div className="absolute bottom-20 right-10 w-60 h-60 bg-purple-400/20 rounded-full blur-3xl animate-pulse" style={{animationDuration: '6s'}}/>
        <div className="absolute top-1/3 left-1/3 w-40 h-40 bg-indigo-400/20 rounded-full blur-3xl animate-pulse" style={{animationDuration: '5s'}}/>
      </div>
      <div className="absolute inset-0 opacity-10" style={{
        backgroundImage: 'radial-gradient(circle at 1px 1px, white 1px, transparent 0)',
        backgroundSize: '40px 40px'
      }}/>
      <div className="relative z-10 flex flex-col justify-between p-12 xl:p-16 w-full">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 bg-white/20 backdrop-blur-sm rounded-xl flex items-center justify-center">
              <BookOpen className="w-5 h-5 text-white"/>
            </div>
            <span className="text-xl font-bold text-white">FastBlog</span>
          </div>
        </div>
        <div className="space-y-8">
          <div>
            <h2 className="text-3xl xl:text-4xl font-bold text-white leading-tight mb-4">
              {t('login.branding.tagline').split('\n').map((line, i) => (
                <React.Fragment key={i}>{i > 0 && <br/>}{line}</React.Fragment>
              ))}
            </h2>
            <p className="text-blue-100/80 text-lg leading-relaxed max-w-md">{t('login.branding.description')}</p>
          </div>
          <div className="grid grid-cols-2 gap-4">
            {features.map((feat, i) => {
              const Icon = feat.icon;
              return (
                <div key={i} className="group p-4 rounded-2xl bg-white/10 backdrop-blur-sm border border-white/10 hover:bg-white/15 transition-all duration-300">
                  <Icon className="w-6 h-6 text-blue-200 mb-3 group-hover:scale-110 transition-transform"/>
                  <h3 className="text-sm font-semibold text-white mb-1">{t(feat.titleKey)}</h3>
                  <p className="text-xs text-blue-100/70 leading-relaxed">{t(feat.descKey)}</p>
                </div>
              );
            })}
          </div>
        </div>
        <div className="flex items-center gap-8">
          <div>
            <div className="text-2xl font-bold text-white">50K+</div>
            <div className="text-sm text-blue-100/70">{t('login.branding.activeUsers')}</div>
          </div>
          <div className="w-px h-10 bg-white/20"/>
          <div>
            <div className="text-2xl font-bold text-white">1M+</div>
            <div className="text-sm text-blue-100/70">{t('login.branding.qualityArticles')}</div>
          </div>
          <div className="w-px h-10 bg-white/20"/>
          <div>
            <div className="text-2xl font-bold text-white">100+</div>
            <div className="text-sm text-blue-100/70">{t('login.branding.countries')}</div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LoginBranding;
