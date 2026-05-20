'use client';

import React, {useEffect, useState} from 'react';
import {apiClient} from '@/lib/api';
import {ArrowRight, Calendar, ChevronRight, Clock, Eye} from 'lucide-react';

interface Article {id:number;title:string;slug:string;excerpt?:string;summary?:string;cover_image?:string;content?:string;views:number;likes:number;created_at:string;tags?:string[];category?:string;author?:{username:string;avatar?:string};}

export default function ModernHomePage() {
  const [featured, setFeatured] = useState<Article[]>([]);
  const [recent, setRecent] = useState<Article[]>([]);
  const [popular, setPopular] = useState<Article[]>([]);
  const [categories, setCategories] = useState<any[]>([]);
  const [stats, setStats] = useState<any>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const [featRes, recentRes, popRes, catRes, statRes] = await Promise.all([
          apiClient.get<any>('/home/featured'),
          apiClient.get<any>('/home/recent'),
          apiClient.get<any>('/home/popular'),
          apiClient.get<any>('/home/categories'),
          apiClient.get<any>('/home/stats'),
        ]);
        if (featRes.success) setFeatured(Array.isArray(featRes.data) ? featRes.data : featRes.data?.articles||[]);
        if (recentRes.success) setRecent(Array.isArray(recentRes.data) ? recentRes.data.slice(0,8) : recentRes.data?.articles?.slice(0,8)||[]);
        if (popRes.success) setPopular(Array.isArray(popRes.data) ? popRes.data.slice(0,4) : popRes.data?.articles?.slice(0,4)||[]);
        if (catRes.success) setCategories(Array.isArray(catRes.data) ? catRes.data : catRes.data?.categories||[]);
        if (statRes.success) setStats(statRes.data||{});
      } catch {} finally { setLoading(false); }
    })();
  }, []);

  if (loading) return (
    <div className="min-h-screen bg-white dark:bg-gray-950">
      <div className="max-w-6xl mx-auto px-4 py-24 space-y-8">
        <div className="h-12 w-64 bg-gray-100 dark:bg-gray-800 rounded-xl animate-pulse"/>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[1,2,3].map(i=><div key={i} className="aspect-[4/5] bg-gray-100 dark:bg-gray-800 rounded-2xl animate-pulse"/>)}
        </div>
      </div>
    </div>
  );

  const f = featured.length > 0 ? featured[0] : null;
  const fSub = featured.length > 1 ? featured.slice(1, 4) : [];

  return (
    <div className="bg-white dark:bg-gray-950">
      {/* ═══ Hero — Clean & bold, no blobs ═══ */}
      <section className="relative border-b border-gray-100 dark:border-gray-900">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-16 sm:py-20 lg:py-28">
          <div className="max-w-2xl">
            <div className="inline-flex items-center gap-2 px-3 py-1 bg-blue-50 dark:bg-blue-900/20 rounded-full text-xs font-medium text-blue-600 dark:text-blue-400 mb-6">
              <span className="w-1.5 h-1.5 bg-blue-600 rounded-full animate-pulse"/>最新动态
            </div>
            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold text-gray-900 dark:text-white tracking-tight leading-[1.1] mb-5">
              探索未知的<span className="text-blue-600">知识海洋</span>
            </h1>
            <p className="text-base sm:text-lg text-gray-500 dark:text-gray-400 mb-8 leading-relaxed max-w-xl">
              在这里，每一篇文章都是一次思想的碰撞。加入我们的社区，发现精选内容，连接有趣的思想。
            </p>
            <div className="flex flex-wrap gap-3">
              <a href="/articles" className="px-6 py-3 bg-gray-900 dark:bg-white text-white dark:text-gray-900 font-semibold rounded-xl hover:bg-gray-800 dark:hover:bg-gray-100 transition-all shadow-sm text-sm flex items-center gap-2">
                浏览文章 <ArrowRight className="w-4 h-4"/>
              </a>
              <a href="/categories" className="px-6 py-3 border border-gray-200 dark:border-gray-800 text-gray-700 dark:text-gray-300 font-medium rounded-xl hover:bg-gray-50 dark:hover:bg-gray-800 transition-all text-sm">
                分类浏览
              </a>
            </div>
          </div>
          {/* Right side visual — minimal decorative element */}
          <div className="hidden lg:block absolute right-12 top-1/2 -translate-y-1/2 opacity-[0.04] dark:opacity-[0.06] pointer-events-none select-none">
            <svg width="400" height="400" viewBox="0 0 400 400" fill="none"><circle cx="200" cy="200" r="180" stroke="currentColor" strokeWidth="2" strokeDasharray="8 8"/><circle cx="200" cy="200" r="120" stroke="currentColor" strokeWidth="2"/><circle cx="200" cy="200" r="60" stroke="currentColor" strokeWidth="2"/><path d="M200 20v360M20 200h360" stroke="currentColor" strokeWidth="2"/></svg>
          </div>
        </div>
      </section>

      {/* ═══ Stats bar ═══ */}
      <section className="border-b border-gray-100 dark:border-gray-900">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-6">
          <div className="flex flex-wrap gap-8 sm:gap-12 text-sm">
            <div><span className="font-bold text-2xl text-gray-900 dark:text-white">{stats?.total_articles || featured.length + recent.length || '—'}</span><p className="text-gray-400 mt-0.5">文章</p></div>
            <div><span className="font-bold text-2xl text-gray-900 dark:text-white">{stats?.total_users || '—'}</span><p className="text-gray-400 mt-0.5">用户</p></div>
            <div><span className="font-bold text-2xl text-gray-900 dark:text-white">{stats?.total_views || '—'}</span><p className="text-gray-400 mt-0.5">总阅读</p></div>
            <div><span className="font-bold text-2xl text-gray-900 dark:text-white">{categories.length || '—'}</span><p className="text-gray-400 mt-0.5">分类</p></div>
          </div>
        </div>
      </section>

      {/* ═══ Featured Article — Hero card ═══ */}
      {f && (
        <section className="max-w-6xl mx-auto px-4 sm:px-6 py-12 sm:py-16">
          <div className="grid lg:grid-cols-5 gap-8 items-center">
            <div className="lg:col-span-3 relative aspect-[4/3] lg:aspect-auto lg:h-[400px] rounded-2xl overflow-hidden bg-gray-50 dark:bg-gray-900">
              {f.cover_image ? <img src={f.cover_image} alt={f.title} className="w-full h-full object-cover"/> :
                <div className="w-full h-full flex items-center justify-center text-gray-200 dark:text-gray-700 text-6xl">📝</div>}
            </div>
            <div className="lg:col-span-2">
              {f.tags?.[0] && <span className="text-xs font-semibold text-blue-600 dark:text-blue-400 uppercase tracking-wider">{f.tags[0]}</span>}
              <h2 className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-white mt-2 mb-4 leading-tight">
                <a href={`/view?slug=f.slug`} className="hover:text-blue-600 transition-colors">{f.title}</a>
              </h2>
              <p className="text-gray-500 dark:text-gray-400 text-sm leading-relaxed mb-6 line-clamp-3">{f.excerpt||f.summary||'...'}</p>
              <div className="flex items-center gap-4 text-xs text-gray-400">
                {f.created_at && <span className="flex items-center gap-1"><Calendar className="w-3.5 h-3.5"/>{new Date(f.created_at).toLocaleDateString('zh-CN')}</span>}
                <span className="flex items-center gap-1"><Eye className="w-3.5 h-3.5"/>{f.views||0}</span>
                <a href={`/view?slug=f.slug`} className="ml-auto text-blue-600 hover:text-blue-700 font-medium flex items-center gap-1">阅读全文 <ChevronRight className="w-3.5 h-3.5"/></a>
              </div>
            </div>
          </div>
          {/* Sub featured */}
          {fSub.length > 0 && (
            <div className="grid sm:grid-cols-3 gap-4 mt-6">
              {fSub.map(a => (
                  <a key={a.id} href={`/view?slug=${a.slug}`}
                     className="group p-4 rounded-xl border border-gray-100 dark:border-gray-800 hover:border-gray-200 dark:hover:border-gray-700 transition-all">
                  <p className="text-xs text-blue-600 mb-1 font-medium uppercase tracking-wider">{a.tags?.[0]||'精选'}</p>
                  <h3 className="font-semibold text-gray-900 dark:text-white text-sm line-clamp-2 group-hover:text-blue-600 transition-colors">{a.title}</h3>
                  <p className="text-xs text-gray-400 mt-2 flex items-center gap-1"><Eye className="w-3 h-3"/>{a.views||0}</p>
                </a>
              ))}
            </div>
          )}
        </section>
      )}

      {/* ═══ Recent Articles ═══ */}
      <section className="bg-gray-50 dark:bg-gray-900/50 border-t border-b border-gray-100 dark:border-gray-900">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-12 sm:py-16">
          <div className="flex items-center justify-between mb-8">
            <div><h2 className="text-2xl font-bold text-gray-900 dark:text-white">最新文章</h2><p className="text-sm text-gray-500 mt-1">新鲜出炉的内容</p></div>
            <a href="/articles" className="text-sm text-blue-600 hover:text-blue-700 font-medium flex items-center gap-1">查看全部 <ChevronRight className="w-4 h-4"/></a>
          </div>
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-5">
            {recent.slice(0, 4).map(a => (
                <a key={a.id} href={`/view?slug=${a.slug}`}
                   className="group bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 overflow-hidden hover:border-gray-200 dark:hover:border-gray-700 transition-all hover:shadow-sm">
                <div className="aspect-[16/10] bg-gray-50 dark:bg-gray-800 overflow-hidden">
                  {a.cover_image ? <img src={a.cover_image} alt="" className="w-full h-full object-cover group-hover:scale-[1.02] transition-transform duration-500"/> :
                    <div className="w-full h-full flex items-center justify-center text-3xl text-gray-200 dark:text-gray-700">📄</div>}
                </div>
                <div className="p-4">
                  <div className="flex items-center gap-2 text-xs text-gray-400 mb-2">
                    {a.tags?.[0] && <span className="text-blue-600 font-medium">{a.tags[0]}</span>}
                    <span>·</span>
                    <span className="flex items-center gap-0.5"><Clock className="w-3 h-3"/>{a.created_at ? new Date(a.created_at).toLocaleDateString('zh-CN') : ''}</span>
                  </div>
                  <h3 className="font-semibold text-gray-900 dark:text-white text-sm line-clamp-2 leading-snug group-hover:text-blue-600 transition-colors">{a.title}</h3>
                  <p className="text-xs text-gray-400 mt-2 line-clamp-1">{a.excerpt||a.summary||''}</p>
                </div>
              </a>
            ))}
          </div>
        </div>
      </section>

      {/* ═══ Middle Section: Popular + Categories ═══ */}
      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-12 sm:py-16 grid lg:grid-cols-3 gap-10">
        {/* Popular */}
        <div className="lg:col-span-2">
          <div className="flex items-center justify-between mb-5"><h2 className="text-xl font-bold text-gray-900 dark:text-white">热门文章</h2><a href="/articles" className="text-sm text-blue-600 font-medium">更多</a></div>
          <div className="space-y-3">
            {popular.slice(0, 5).map((a, i) => (
                <a key={a.id} href={`/view?slug=${a.slug}`}
                   className="flex items-center gap-4 p-3 rounded-xl hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors group">
                <span className="text-2xl font-bold text-gray-200 dark:text-gray-700 w-8 shrink-0">{String(i+1).padStart(2,'0')}</span>
                <div className="flex-1 min-w-0"><h3 className="font-medium text-sm text-gray-900 dark:text-white line-clamp-1 group-hover:text-blue-600 transition-colors">{a.title}</h3><p className="text-xs text-gray-400 mt-0.5"><Eye className="w-3 h-3 inline mr-0.5"/>{a.views||0} 阅读</p></div>
              </a>
            ))}
          </div>
        </div>
        {/* Categories */}
        <div>
          <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-5">分类浏览</h2>
          <div className="space-y-2">
            {categories.map((c: any, i: number) => (
              <a key={i} href={`/category/${c.slug||c.id}`} className="flex items-center justify-between p-3 rounded-xl bg-gray-50 dark:bg-gray-800/50 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors">
                <span className="text-sm font-medium text-gray-700 dark:text-gray-300">{c.name||c}</span>
                <span className="text-xs text-gray-400">{c.articles_count||c.count||''}</span>
              </a>
            ))}
          </div>
        </div>
      </div>

      {/* ═══ CTA — Clean, no gradient mess ═══ */}
      <section className="border-t border-gray-100 dark:border-gray-900">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-16 text-center">
          <h2 className="text-3xl font-bold text-gray-900 dark:text-white mb-3">加入我们的社区</h2>
          <p className="text-gray-500 mb-8 max-w-md mx-auto">与志同道合的创作者一起分享知识、交流想法</p>
          <div className="flex gap-3 justify-center">
            <a href="/register" className="px-6 py-3 bg-gray-900 dark:bg-white text-white dark:text-gray-900 font-semibold rounded-xl hover:bg-gray-800 dark:hover:bg-gray-100 transition-all text-sm">立即注册</a>
            <a href="/about" className="px-6 py-3 border border-gray-200 dark:border-gray-800 text-gray-700 dark:text-gray-300 font-medium rounded-xl hover:bg-gray-50 dark:hover:bg-gray-800 transition-all text-sm">了解我们</a>
          </div>
        </div>
      </section>
    </div>
  );
}
