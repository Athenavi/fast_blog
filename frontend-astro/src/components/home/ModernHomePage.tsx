'use client';

import React, {useCallback, useEffect, useMemo, useState} from 'react';
import {apiClient} from '@/lib/api/base-client';
import {HOME} from '@/lib/api/api-paths';
import type {HomeConfig} from '@/hooks/useHomeConfig';
import {useHomeConfig} from '@/hooks/useHomeConfig';
import {Article, Category} from './_shared';
import HomeHero from './HomeHero';
import HomeFeatured from './HomeFeatured';
import HomeCategories from './HomeCategories';
import HomeLatest from './HomeLatest';
import HomePopular from './HomePopular';
import HomeNewsletter from './HomeNewsletter';
import {useBreakpoint} from '@/lib/hooks/useMediaQuery';
import {useNetworkState} from '@/lib/hooks/useNetworkState';
import {useMediaQuery} from '@/lib/utils';

// 响应式布局配置
const RESPONSIVE_CONFIG = {
  gridCols: {
    sm: 1,
    md: 2,
    lg: 3,
    xl: 3,
    '2xl': 4,
  },
  featuredCount: {
    sm: 1,
    md: 2,
    lg: 3,
    xl: 4,
    '2xl': 6,
  },
  popularCount: {
    sm: 3,
    md: 4,
    lg: 6,
    xl: 8,
    '2xl': 12,
  },
} as const;

interface Props {
    /** SSR 注入的初始数据 — 有值则跳过客户端首次请求 */
    initialFeatured?: Article[];
    initialRecent?: Article[];
    initialPopular?: Article[];
    initialCategories?: Category[];
    initialConfig?: HomeConfig | null;
}

const LoadingScreen = React.memo(() => (
  <div className="min-h-screen bg-[#05070f]">
    <div className="relative h-[85vh] min-h-[600px] bg-slate-900/60 animate-pulse" aria-label="页面加载中">
      <div className="absolute inset-0 flex items-center">
        <div className="max-w-7xl mx-auto px-6 w-full">
          <div className="max-w-2xl space-y-6">
            <div className="h-4 w-32 bg-slate-800 rounded"/>
            <div className="h-16 w-96 bg-slate-800 rounded-lg"/>
            <div className="h-6 w-80 bg-slate-800/70 rounded"/>
            <div className="flex gap-4 mt-8">
              <div className="h-12 w-36 bg-slate-800 rounded-full"/>
            </div>
          </div>
        </div>
      </div>
    </div>
    <div className="max-w-7xl mx-auto px-6 py-20 space-y-16">
      {[1, 2].map(s => (
        <div key={s}>
          <div className="h-8 w-48 bg-slate-800/70 rounded mb-8"/>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {[1, 2, 3].map(i => (
              <div key={i} className="rounded-xl overflow-hidden bg-slate-900/60">
                <div className="aspect-[16/10] bg-slate-800/70"/>
                <div className="p-5 space-y-3">
                  <div className="h-4 w-16 bg-slate-800/70 rounded"/>
                  <div className="h-6 bg-slate-800 rounded"/>
                  <div className="h-4 w-3/4 bg-slate-800/70 rounded"/>
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  </div>
));
LoadingScreen.displayName = 'LoadingScreen';

const HomeContent = React.memo(({
                                  featured, hero, sections, newsletter, messages, categories, recent, popular,
                                }: {
  featured: Article[];
  hero: Props['initialConfig'] & {
    title: string;
    subtitle: string;
    ctaText: string;
    ctaLink: string;
    ctaTarget: string;
    backgroundImage: string
  };
  sections: any;
  newsletter: any;
  messages: any;
  categories: Category[];
  recent: Article[];
  popular: Article[];
}) => (
  <>
    <HomeHero featured={featured} heroTitle={hero.title || ''} heroSubtitle={hero.subtitle || ''}
              heroCtaText={hero.ctaText || ''} heroCtaLink={hero.ctaLink || ''} ctaTarget={hero.ctaTarget || ''}
              heroBg={hero.backgroundImage || ''}/>
    <HomeFeatured featured={featured} title={sections.featuredTitle || ''}
                  noSummaryMsg={messages?.noSummary || '暂无摘要'}/>
    <HomeCategories categories={categories} title={sections.categoriesTitle || ''}/>
    <HomeLatest articles={recent} title={sections.mainTitle || ''}/>
    <HomePopular articles={popular}/>
    <HomeNewsletter title={newsletter.title || ''} subtitle={newsletter.subtitle || ''}
                    buttonText={newsletter.buttonText || ''}/>
  </>
));
HomeContent.displayName = 'HomeContent';

function ModernHomePage({
  initialFeatured = [],
  initialRecent = [],
  initialPopular = [],
  initialCategories = [],
  initialConfig = null,
}: Props) {
  const isMobile = useMediaQuery('(max-width: 768px)');
  const breakpoint = useBreakpoint();
  const {saveData} = useNetworkState();
  const hasSsrData = initialFeatured.length > 0 || initialRecent.length > 0;
  const [featured, setFeatured] = useState<Article[]>(initialFeatured);
  const [recent, setRecent] = useState<Article[]>(initialRecent);
  const [popular, setPopular] = useState<Article[]>(initialPopular);
  const [categories, setCategories] = useState<Category[]>(initialCategories);
  const [loading, setLoading] = useState(!hasSsrData);
  const {hero, sections, newsletter, messages, loading: cfgLoading} = useHomeConfig(initialConfig);
  const featuredCount = RESPONSIVE_CONFIG.featuredCount[breakpoint];
  const popularCount = RESPONSIVE_CONFIG.popularCount[breakpoint];
  const limitedRecent = saveData ? 6 : 12;

  // 移动端弱网络: 使用 requestIdleCallback 延迟加载非关键数据
  const fetchNonCriticalData = useCallback(async () => {
    try {
      const [p, c] = await Promise.all([
        apiClient.get(HOME.POPULAR),
        apiClient.get(HOME.CATEGORIES),
      ]);
      if (p.success) setPopular(Array.isArray(p.data) ? p.data.slice(0, popularCount) : p.data?.articles?.slice(0, popularCount) || []);
      if (c.success) setCategories(Array.isArray(c.data) ? c.data : c.data?.categories || []);
    } catch { /* ignore */
    }
  }, [popularCount]);

  useEffect(() => {
    if (hasSsrData) return; // SSR 已提供数据，跳过客户端首次请求
    (async () => {
      try {
        // 核心数据优先
        const [f, r] = await Promise.all([
          apiClient.get(HOME.FEATURED),
          apiClient.get(HOME.RECENT),
        ]);
        if (f.success) setFeatured(Array.isArray(f.data) ? f.data.slice(0, featuredCount) : f.data?.articles?.slice(0, featuredCount) || []);
        if (r.success) setRecent(Array.isArray(r.data) ? r.data.slice(0, limitedRecent) : r.data?.articles?.slice(0, limitedRecent) || []);

        // 非核心数据延迟加载 (移动端弱网络优化)
        if (isMobile) {
          const idleCb = typeof requestIdleCallback !== 'undefined' ? requestIdleCallback : (cb: any) => setTimeout(cb, 1);
          idleCb(fetchNonCriticalData, {timeout: 2000});
        } else {
          const [p, c] = await Promise.all([
            apiClient.get(HOME.POPULAR),
            apiClient.get(HOME.CATEGORIES),
          ]);
          if (p.success) setPopular(Array.isArray(p.data) ? p.data.slice(0, popularCount) : p.data?.articles?.slice(0, popularCount) || []);
          if (c.success) setCategories(Array.isArray(c.data) ? c.data : c.data?.categories || []);
        }
      } catch { /* ignore */ } finally { setLoading(false); }
    })();
  }, [featuredCount, limitedRecent, popularCount]);

  const heroMemo = useMemo(() => ({
    title: hero.title || '',
    subtitle: hero.subtitle || '',
    ctaText: hero.ctaText || '',
    ctaLink: hero.ctaLink || '',
    ctaTarget: hero.ctaTarget || '',
    backgroundImage: hero.backgroundImage || '',
  }), [hero]);

  if (loading || cfgLoading) return <LoadingScreen />;

  return (
    <div className="bg-[#05070f] overflow-hidden">
      <HomeContent
        featured={featured}
        hero={heroMemo}
        sections={sections}
        newsletter={newsletter}
        messages={messages}
        categories={categories}
        recent={recent}
        popular={popular}
      />
      <div className="h-8" />
    </div>
  );
}

export default React.memo(ModernHomePage);
