'use client';

import React, {useEffect, useState} from 'react';
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

interface Props {
    /** SSR 注入的初始数据 — 有值则跳过客户端首次请求 */
    initialFeatured?: Article[];
    initialRecent?: Article[];
    initialPopular?: Article[];
    initialCategories?: Category[];
    initialConfig?: HomeConfig | null;
}

const LoadingScreen = () => (
  <div className="min-h-screen bg-[#05070f]">
    <div className="relative h-[85vh] min-h-[600px] bg-slate-900/60 animate-pulse">
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
);

export default function ModernHomePage({
  initialFeatured = [],
  initialRecent = [],
  initialPopular = [],
  initialCategories = [],
  initialConfig = null,
}: Props) {
  const hasSsrData = initialFeatured.length > 0 || initialRecent.length > 0;
  const [featured, setFeatured] = useState<Article[]>(initialFeatured);
  const [recent, setRecent] = useState<Article[]>(initialRecent);
  const [popular, setPopular] = useState<Article[]>(initialPopular);
  const [categories, setCategories] = useState<Category[]>(initialCategories);
  const [loading, setLoading] = useState(!hasSsrData);
  const {hero, sections, newsletter, messages, loading: cfgLoading} = useHomeConfig(initialConfig);

  useEffect(() => {
    if (hasSsrData) return; // SSR 已提供数据，跳过客户端首次请求
    (async () => {
      try {
        const [f, r, p, c] = await Promise.all([
          apiClient.get(HOME.FEATURED), apiClient.get(HOME.RECENT),
          apiClient.get(HOME.POPULAR), apiClient.get(HOME.CATEGORIES),
        ]);
        if (f.success) setFeatured(Array.isArray(f.data) ? f.data : f.data?.articles || []);
        if (r.success) setRecent(Array.isArray(r.data) ? r.data.slice(0, 12) : r.data?.articles?.slice(0, 12) || []);
        if (p.success) setPopular(Array.isArray(p.data) ? p.data.slice(0, 8) : p.data?.articles?.slice(0, 8) || []);
        if (c.success) setCategories(Array.isArray(c.data) ? c.data : c.data?.categories || []);
      } catch { /* ignore */ } finally { setLoading(false); }
    })();
  }, []);

  if (loading || cfgLoading) return <LoadingScreen />;

  return (
    <div className="bg-[#05070f] overflow-hidden">
      <HomeHero featured={featured} heroTitle={hero.title || ''} heroSubtitle={hero.subtitle || ''}
        heroCtaText={hero.ctaText || ''} heroCtaLink={hero.ctaLink || ''} ctaTarget={hero.ctaTarget || ''} heroBg={hero.backgroundImage || ''} />
      <HomeFeatured featured={featured} title={sections.featuredTitle || ''} noSummaryMsg={messages?.noSummary || '暂无摘要'} />
      <HomeCategories categories={categories} title={sections.categoriesTitle || ''} />
      <HomeLatest articles={recent} title={sections.mainTitle || ''} />
      <HomePopular articles={popular} />
      <HomeNewsletter title={newsletter.title || ''} subtitle={newsletter.subtitle || ''} buttonText={newsletter.buttonText || ''} />
      <div className="h-8" />
    </div>
  );
}
