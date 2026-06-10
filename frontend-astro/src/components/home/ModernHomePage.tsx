'use client';

import React, {useEffect, useState} from 'react';
import {apiClient} from '@/lib/api/base-client';
import {HOME} from '@/lib/api/api-paths';
import {useHomeConfig} from '@/hooks/useHomeConfig';
import {Article, Category} from './_shared';
import HomeHero from './HomeHero';
import HomeFeatured from './HomeFeatured';
import HomeCategories from './HomeCategories';
import HomeLatest from './HomeLatest';
import HomePopular from './HomePopular';
import HomeNewsletter from './HomeNewsletter';

const LoadingScreen = () => (
  <div className="min-h-screen bg-white dark:bg-gray-950">
    <div className="relative h-[85vh] min-h-[600px] bg-gray-100 dark:bg-gray-900 animate-pulse">
      <div className="absolute inset-0 flex items-center">
        <div className="max-w-7xl mx-auto px-6 w-full">
          <div className="max-w-2xl space-y-6">
            <div className="h-4 w-32 bg-gray-200 dark:bg-gray-800 rounded-full" />
            <div className="h-16 w-96 bg-gray-200 dark:bg-gray-800 rounded-xl" />
            <div className="h-6 w-80 bg-gray-200 dark:bg-gray-800 rounded-lg" />
            <div className="flex gap-4 mt-8">
              <div className="h-14 w-40 bg-gray-200 dark:bg-gray-800 rounded-xl" />
              <div className="h-14 w-36 bg-gray-200 dark:bg-gray-800 rounded-xl" />
            </div>
          </div>
        </div>
      </div>
    </div>
    <div className="max-w-7xl mx-auto px-6 py-20 space-y-16">
      {[1, 2].map(s => (
        <div key={s}>
          <div className="h-8 w-48 bg-gray-100 dark:bg-gray-900 rounded-lg mb-8" />
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {[1, 2, 3].map(i => (
              <div key={i} className="rounded-2xl overflow-hidden border border-gray-100 dark:border-gray-800">
                <div className="aspect-[16/10] bg-gray-100 dark:bg-gray-900" />
                <div className="p-5 space-y-3">
                  <div className="h-4 w-16 bg-gray-100 dark:bg-gray-900 rounded" />
                  <div className="h-6 bg-gray-100 dark:bg-gray-900 rounded" />
                  <div className="h-4 w-3/4 bg-gray-100 dark:bg-gray-900 rounded" />
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  </div>
);

export default function ModernHomePage() {
  const [featured, setFeatured] = useState<Article[]>([]);
  const [recent, setRecent] = useState<Article[]>([]);
  const [popular, setPopular] = useState<Article[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState(true);
  const {hero, sections, newsletter, messages, loading: cfgLoading} = useHomeConfig();

  useEffect(() => {
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
    <div className="bg-white dark:bg-gray-950 overflow-hidden">
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
