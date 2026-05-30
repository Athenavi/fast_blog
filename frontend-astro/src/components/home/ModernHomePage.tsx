'use client';

import React, {useEffect, useRef, useState} from 'react';
import {motion, useInView} from 'framer-motion';
import {apiClient} from '@/lib/api/api-client';
import {
    ArrowRight, BookOpen, Calendar, ChevronRight, Clock, Eye,
    FolderTree, Hash, Heart, MessageSquare, TrendingUp, Users, Zap
} from 'lucide-react';

// ═══ Types ═══
interface Article {
    id: number;
    title: string;
    slug: string;
    excerpt?: string;
    summary?: string;
    cover_image?: string;
    content?: string;
    views: number;
    likes: number;
    created_at: string;
    tags?: string[];
    category?: string;
    author?: { username: string; avatar?: string };
}

interface Category {
    id: number;
    name: string;
    slug: string;
    count?: number;
    icon?: string;
    color?: string;
}

interface Stats {
    total_articles?: number;
    total_users?: number;
    total_views?: number;
    total_comments?: number;
}

// ═══ Animation Variants ═══
const fadeUp = {
    hidden: {opacity: 0, y: 30},
    visible: {
        opacity: 1,
        y: 0,
        transition: {duration: 0.6, ease: [0.22, 1, 0.36, 1] as [number, number, number, number]}
    }
};

const stagger = {
    visible: {transition: {staggerChildren: 0.1}}
};

const scaleIn = {
    hidden: {opacity: 0, scale: 0.95},
    visible: {
        opacity: 1,
        scale: 1,
        transition: {duration: 0.5, ease: [0.22, 1, 0.36, 1] as [number, number, number, number]}
    }
};

// ═══ Animated Section Wrapper ═══
const AnimatedSection: React.FC<{ children: React.ReactNode; className?: string; delay?: number }> = ({
                                                                                                          children,
                                                                                                          className = '',
                                                                                                          delay = 0
                                                                                                      }) => {
    const ref = useRef(null);
    const isInView = useInView(ref, {once: true, margin: '-80px'});

    return (
        <motion.div
            ref={ref}
            initial="hidden"
            animate={isInView ? 'visible' : 'hidden'}
            variants={stagger}
            className={className}
        >
            {children}
        </motion.div>
    );
};

// ═══ Stat Counter Animation ═══
const StatNumber: React.FC<{ value: number; suffix?: string }> = ({value, suffix = ''}) => {
    const [count, setCount] = useState(0);
    const ref = useRef(null);
    const isInView = useInView(ref, {once: true});

    useEffect(() => {
        if (!isInView) return;
        const duration = 1500;
        const start = Date.now();
        const step = () => {
            const elapsed = Date.now() - start;
            const progress = Math.min(elapsed / duration, 1);
            const eased = 1 - Math.pow(1 - progress, 3); // easeOutCubic
            setCount(Math.floor(eased * value));
            if (progress < 1) requestAnimationFrame(step);
        };
        requestAnimationFrame(step);
    }, [isInView, value]);

    return <span ref={ref}>{count.toLocaleString()}{suffix}</span>;
};

export default function ModernHomePage() {
  const [featured, setFeatured] = useState<Article[]>([]);
  const [recent, setRecent] = useState<Article[]>([]);
  const [popular, setPopular] = useState<Article[]>([]);
    const [categories, setCategories] = useState<Category[]>([]);
    const [stats, setStats] = useState<Stats>({});
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
          if (featRes.success) setFeatured(Array.isArray(featRes.data) ? featRes.data : featRes.data?.articles || []);
          if (recentRes.success) setRecent(Array.isArray(recentRes.data) ? recentRes.data.slice(0, 8) : recentRes.data?.articles?.slice(0, 8) || []);
          if (popRes.success) setPopular(Array.isArray(popRes.data) ? popRes.data.slice(0, 6) : popRes.data?.articles?.slice(0, 6) || []);
          if (catRes.success) setCategories(Array.isArray(catRes.data) ? catRes.data : catRes.data?.categories || []);
          if (statRes.success) setStats(statRes.data || {});
      } catch {
      } finally {
          setLoading(false);
      }
    })();
  }, []);

    // ═══ Loading Skeleton ═══
  if (loading) return (
    <div className="min-h-screen bg-white dark:bg-gray-950">
        {/* Hero skeleton */}
        <div className="max-w-6xl mx-auto px-4 py-24">
            <div className="max-w-2xl space-y-4">
                <div className="h-5 w-24 skeleton rounded-full"/>
                <div className="h-14 w-96 skeleton rounded-xl"/>
                <div className="h-6 w-80 skeleton rounded-lg"/>
                <div className="flex gap-3 mt-6">
                    <div className="h-11 w-36 skeleton rounded-xl"/>
                    <div className="h-11 w-28 skeleton rounded-xl"/>
                </div>
            </div>
        </div>
        {/* Grid skeleton */}
        <div className="max-w-6xl mx-auto px-4 space-y-8">
            <div className="h-8 w-48 skeleton rounded-lg"/>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {[1, 2, 3, 4, 5, 6].map(i =>
                <div key={i} className="rounded-2xl overflow-hidden border border-gray-100 dark:border-gray-800">
                    <div className="aspect-[16/10] skeleton"/>
                    <div className="p-5 space-y-3">
                        <div className="h-4 w-16 skeleton rounded"/>
                        <div className="h-6 skeleton rounded"/>
                        <div className="h-4 w-3/4 skeleton rounded"/>
                    </div>
                </div>
            )}
        </div>
      </div>
    </div>
  );

  const f = featured.length > 0 ? featured[0] : null;
  const fSub = featured.length > 1 ? featured.slice(1, 4) : [];

    const categoryColors = [
        'from-blue-500 to-cyan-500',
        'from-purple-500 to-pink-500',
        'from-emerald-500 to-teal-500',
        'from-orange-500 to-red-500',
        'from-indigo-500 to-blue-500',
        'from-rose-500 to-pink-500',
    ];

  return (
      <div className="bg-white dark:bg-gray-950 overflow-hidden">
          {/* ═══════════════════════════════════
          HERO SECTION
         ═══════════════════════════════════ */}
          <section className="relative overflow-hidden">
              {/* Background mesh gradient */}
              <div className="absolute inset-0 gradient-mesh pointer-events-none"/>
              <div
                  className="absolute inset-0 bg-gradient-to-b from-transparent via-transparent to-white dark:to-gray-950 pointer-events-none"/>

              <div className="relative max-w-6xl mx-auto px-4 sm:px-6 py-20 sm:py-28 lg:py-36">
          <div className="max-w-2xl">
              <motion.div
                  initial={{opacity: 0, y: 20}}
                  animate={{opacity: 1, y: 0}}
                  transition={{duration: 0.6}}
              >
                  <div
                      className="inline-flex items-center gap-2 px-3.5 py-1.5 bg-blue-50 dark:bg-blue-900/20 rounded-full text-xs font-semibold text-blue-600 dark:text-blue-400 mb-8 border border-blue-100 dark:border-blue-800/30">
                      <Zap className="w-3.5 h-3.5"/>
                      <span>全新升级 · 更强大的创作工具</span>
                  </div>
              </motion.div>

              <motion.h1
                  initial={{opacity: 0, y: 30}}
                  animate={{opacity: 1, y: 0}}
                  transition={{duration: 0.7, delay: 0.1}}
                  className="text-4xl sm:text-5xl lg:text-6xl xl:text-7xl font-extrabold text-gray-900 dark:text-white tracking-tight leading-[1.08] mb-6"
              >
                  用文字<span className="gradient-text">连接</span><br/>
                  每一个<span className="gradient-text">想法</span>
              </motion.h1>

              <motion.p
                  initial={{opacity: 0, y: 30}}
                  animate={{opacity: 1, y: 0}}
                  transition={{duration: 0.7, delay: 0.2}}
                  className="text-base sm:text-lg lg:text-xl text-gray-500 dark:text-gray-400 mb-10 leading-relaxed max-w-xl"
              >
                  FastBlog 是一个现代化的内容创作平台，为创作者提供极致的写作体验，让灵感自由流动。
              </motion.p>

              <motion.div
                  initial={{opacity: 0, y: 30}}
                  animate={{opacity: 1, y: 0}}
                  transition={{duration: 0.7, delay: 0.3}}
                  className="flex flex-wrap gap-3"
              >
                  <a href="/articles" className="btn-primary text-base !px-8 !py-3.5 flex items-center gap-2.5">
                      开始阅读 <ArrowRight className="w-4.5 h-4.5"/>
              </a>
                  <a href="/categories" className="btn-secondary text-base !px-8 !py-3.5 flex items-center gap-2">
                      <FolderTree className="w-4.5 h-4.5"/>
                      浏览分类
              </a>
              </motion.div>
          </div>

                  {/* Decorative floating cards */}
                  <div className="hidden xl:block absolute right-0 top-1/2 -translate-y-1/2 w-[400px] h-[320px]">
                      <motion.div
                          animate={{y: [0, -10, 0]}}
                          transition={{duration: 4, repeat: Infinity, ease: 'easeInOut'}}
                          className="absolute top-0 right-8 w-56 p-4 glass rounded-2xl shadow-lg"
                      >
                          <div className="flex items-center gap-3 mb-2">
                              <div
                                  className="w-8 h-8 rounded-lg bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center">
                                  <BookOpen className="w-4 h-4 text-blue-600"/>
                              </div>
                              <div>
                                  <p className="text-xs font-semibold text-gray-900 dark:text-white">最新文章</p>
                                  <p className="text-[10px] text-gray-500">刚刚发布</p>
                              </div>
                          </div>
                          <div className="h-3 w-full skeleton rounded mb-2"/>
                          <div className="h-3 w-3/4 skeleton rounded"/>
                      </motion.div>

                      <motion.div
                          animate={{y: [0, 10, 0]}}
                          transition={{duration: 5, repeat: Infinity, ease: 'easeInOut', delay: 1}}
                          className="absolute bottom-0 right-0 w-48 p-4 glass rounded-2xl shadow-lg"
                      >
                          <div className="flex items-center gap-2 mb-2">
                              <TrendingUp className="w-4 h-4 text-emerald-500"/>
                              <span className="text-xs font-semibold text-gray-900 dark:text-white">数据趋势</span>
                          </div>
                          <div className="flex items-end gap-1 h-10">
                              {[30, 50, 35, 60, 45, 70, 55].map((h, i) => (
                                  <div key={i} className="flex-1 rounded-sm bg-blue-500/20" style={{height: `${h}%`}}>
                                      <div className="w-full rounded-sm bg-blue-500"
                                           style={{height: `${60 + Math.random() * 40}%`}}/>
                                  </div>
                              ))}
                          </div>
                      </motion.div>
          </div>
        </div>
      </section>

          {/* ═══════════════════════════════════
          STATS BAR
         ═══════════════════════════════════ */}
          <section className="border-y border-gray-100 dark:border-gray-900 bg-gray-50/50 dark:bg-gray-900/30">
              <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8">
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-6 sm:gap-8">
                      {[
                          {
                              label: '篇文章',
                              value: stats.total_articles || featured.length + recent.length || 0,
                              icon: BookOpen,
                              color: 'text-blue-600'
                          },
                          {label: '位用户', value: stats.total_users || 0, icon: Users, color: 'text-emerald-600'},
                          {label: '次阅读', value: stats.total_views || 0, icon: Eye, color: 'text-purple-600'},
                          {
                              label: '条评论',
                              value: stats.total_comments || 0,
                              icon: MessageSquare,
                              color: 'text-orange-600'
                          },
                      ].map((stat, i) => {
                          const Icon = stat.icon;
                          return (
                              <motion.div
                                  key={i}
                                  initial={{opacity: 0, y: 20}}
                                  whileInView={{opacity: 1, y: 0}}
                                  viewport={{once: true}}
                                  transition={{delay: i * 0.1}}
                                  className="text-center sm:text-left"
                              >
                                  <div className="flex items-center justify-center sm:justify-start gap-2 mb-1">
                                      <Icon className={`w-4 h-4 ${stat.color}`}/>
                                      <span
                                          className="font-extrabold text-2xl lg:text-3xl text-gray-900 dark:text-white tabular-nums">
                      <StatNumber value={typeof stat.value === 'number' ? stat.value : 0}/>
                    </span>
                                  </div>
                                  <p className="text-sm text-gray-500 dark:text-gray-400">{stat.label}</p>
                              </motion.div>
                          );
                      })}
          </div>
        </div>
      </section>

          {/* ═══════════════════════════════════
          FEATURED ARTICLE
         ═══════════════════════════════════ */}
      {f && (
          <AnimatedSection className="max-w-6xl mx-auto px-4 sm:px-6 py-16 sm:py-20">
              <motion.div variants={fadeUp} className="flex items-center gap-3 mb-8">
                  <div className="w-1 h-6 gradient-primary rounded-full"/>
                  <h2 className="text-2xl font-bold text-gray-900 dark:text-white">精选推荐</h2>
              </motion.div>

              <motion.div variants={fadeUp} className="grid lg:grid-cols-5 gap-8 items-stretch">
                  {/* Hero Image */}
                  <div
                      className="lg:col-span-3 relative rounded-2xl overflow-hidden bg-gray-100 dark:bg-gray-900 group">
                      <a href={`/view?slug=${f.slug}`} className="block aspect-[16/10] lg:aspect-auto lg:h-full">
                          {f.cover_image ? (
                              <img
                                  src={f.cover_image}
                                  alt={f.title}
                                  className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-700"
                                  loading="eager"
                                  fetchpriority="high"
                              />
                          ) : (
                              <div
                                  className="w-full h-full min-h-[300px] flex items-center justify-center text-gray-200 dark:text-gray-700">
                                  <BookOpen className="w-16 h-16"/>
                              </div>
                          )}
                          {/* Overlay gradient */}
                          <div
                              className="absolute inset-0 bg-gradient-to-t from-black/40 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500"/>
                      </a>
                  </div>

                  {/* Content */}
                  <div className="lg:col-span-2 flex flex-col justify-center">
                      {f.tags?.[0] && (
                          <span className="badge badge-blue w-fit mb-4">
                  <Hash className="w-3 h-3 mr-0.5"/>
                              {f.tags[0]}
                </span>
                      )}
                      <h3 className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-white mb-4 leading-tight">
                          <a href={`/view?slug=${f.slug}`}
                             className="hover:text-blue-600 dark:hover:text-blue-400 transition-colors">
                              {f.title}
                          </a>
                      </h3>
                      <p className="text-gray-500 dark:text-gray-400 text-sm leading-relaxed mb-6 line-clamp-3">
                          {f.excerpt || f.summary || '...'}
                      </p>
                      <div className="flex items-center gap-4 text-xs text-gray-400 mb-6">
                          {f.created_at && (
                              <span className="flex items-center gap-1.5">
                    <Calendar className="w-3.5 h-3.5"/>
                                  {new Date(f.created_at).toLocaleDateString('zh-CN')}
                  </span>
                          )}
                          <span className="flex items-center gap-1.5">
                  <Eye className="w-3.5 h-3.5"/>
                              {f.views || 0}
                </span>
                          <span className="flex items-center gap-1.5">
                  <Heart className="w-3.5 h-3.5"/>
                              {f.likes || 0}
                </span>
                      </div>
                      <a
                          href={`/view?slug=${f.slug}`}
                          className="btn-primary !w-fit flex items-center gap-2"
                      >
                          阅读全文 <ChevronRight className="w-4 h-4"/>
                      </a>
                  </div>
              </motion.div>

          {/* Sub featured */}
          {fSub.length > 0 && (
              <div className="grid sm:grid-cols-3 gap-4 mt-8">
                  {fSub.map((a, i) => (
                      <motion.a
                          key={a.id}
                          variants={scaleIn}
                          href={`/view?slug=${a.slug}`}
                          className="group p-5 rounded-xl border border-gray-100 dark:border-gray-800 hover:border-blue-200 dark:hover:border-blue-800 transition-all card-hover bg-white dark:bg-gray-900"
                      >
                          <p className="text-xs text-blue-600 dark:text-blue-400 mb-2 font-semibold uppercase tracking-wider flex items-center gap-1">
                              <Hash className="w-3 h-3"/>
                              {a.tags?.[0] || '精选'}
                          </p>
                          <h3 className="font-semibold text-gray-900 dark:text-white text-sm line-clamp-2 group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors leading-relaxed">
                              {a.title}
                          </h3>
                          <div className="flex items-center gap-3 text-xs text-gray-400 mt-3">
                              <span className="flex items-center gap-1"><Eye className="w-3 h-3"/>{a.views || 0}</span>
                              <span className="flex items-center gap-1"><Heart
                                  className="w-3 h-3"/>{a.likes || 0}</span>
                          </div>
                      </motion.a>
                  ))}
              </div>
          )}
          </AnimatedSection>
      )}

          {/* ═══════════════════════════════════
          CATEGORIES
         ═══════════════════════════════════ */}
          {categories.length > 0 && (
              <section className="bg-gray-50 dark:bg-gray-900/50 border-y border-gray-100 dark:border-gray-900">
                  <div className="max-w-6xl mx-auto px-4 sm:px-6 py-16 sm:py-20">
                      <AnimatedSection>
                          <motion.div variants={fadeUp} className="flex items-center justify-between mb-10">
                              <div className="flex items-center gap-3">
                                  <div className="w-1 h-6 gradient-accent rounded-full"/>
                                  <div>
                                      <h2 className="text-2xl font-bold text-gray-900 dark:text-white">探索分类</h2>
                                      <p className="text-sm text-gray-500 mt-1">按主题浏览感兴趣的内容</p>
                                  </div>
                              </div>
                              <a href="/categories"
                                 className="text-sm text-blue-600 hover:text-blue-700 font-medium flex items-center gap-1">
                                  查看全部 <ChevronRight className="w-4 h-4"/>
                </a>
                          </motion.div>

                          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
                              {categories.slice(0, 6).map((cat, i) => (
                                  <motion.a
                                      key={cat.id}
                                      variants={scaleIn}
                                      href={`/category?slug=${cat.slug}`}
                                      className="group relative p-5 rounded-2xl bg-white dark:bg-gray-900 border border-gray-100 dark:border-gray-800 hover:border-gray-200 dark:hover:border-gray-700 transition-all card-hover text-center overflow-hidden"
                                  >
                                      <div
                                          className={`w-12 h-12 mx-auto mb-3 rounded-xl bg-gradient-to-br ${categoryColors[i % categoryColors.length]} flex items-center justify-center text-white text-lg font-bold shadow-sm`}>
                                          {cat.name?.[0] || '#'}
                                      </div>
                                      <h3 className="font-semibold text-gray-900 dark:text-white text-sm mb-1">{cat.name}</h3>
                                      <p className="text-xs text-gray-400">{cat.count || 0} 篇文章</p>
                                  </motion.a>
                              ))}
                          </div>
                      </AnimatedSection>
                  </div>
        </section>
      )}

          {/* ═══════════════════════════════════
          RECENT ARTICLES
         ═══════════════════════════════════ */}
          {recent.length > 0 && (
              <div className="max-w-6xl mx-auto px-4 sm:px-6 py-16 sm:py-20">
                  <AnimatedSection>
                      <motion.div variants={fadeUp} className="flex items-center justify-between mb-10">
                          <div className="flex items-center gap-3">
                              <div className="w-1 h-6 gradient-cool rounded-full"/>
                              <div>
                                  <h2 className="text-2xl font-bold text-gray-900 dark:text-white">最新发布</h2>
                                  <p className="text-sm text-gray-500 mt-1">新鲜出炉的优质内容</p>
                              </div>
                          </div>
                          <a href="/articles"
                             className="text-sm text-blue-600 hover:text-blue-700 font-medium flex items-center gap-1">
                              查看全部 <ChevronRight className="w-4 h-4"/>
                          </a>
                      </motion.div>

                      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-5">
                          {recent.map((a, i) => (
                              <motion.a
                                  key={a.id}
                                  variants={fadeUp}
                                  href={`/view?slug=${a.slug}`}
                                  className="group bg-white dark:bg-gray-900 rounded-2xl border border-gray-100 dark:border-gray-800 overflow-hidden card-hover"
                              >
                                  {/* Cover */}
                                  <div className="aspect-[16/10] bg-gray-50 dark:bg-gray-800 overflow-hidden relative">
                                      {a.cover_image ? (
                                          <img
                                              src={a.cover_image}
                                              alt={a.title}
                                              className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-700"
                                              loading="lazy"
                                          />
                                      ) : (
                                          <div className="w-full h-full flex items-center justify-center">
                                              <BookOpen className="w-8 h-8 text-gray-200 dark:text-gray-700"/>
                                          </div>
                                      )}
                                      {/* Category badge on image */}
                                      {a.category && (
                                          <div className="absolute top-3 left-3">
                        <span
                            className="badge bg-white/90 dark:bg-gray-900/90 text-gray-700 dark:text-gray-300 backdrop-blur-sm text-[10px]">
                          {a.category}
                        </span>
                                          </div>
                                      )}
                                  </div>
                                  {/* Content */}
                                  <div className="p-4.5">
                                      <div className="flex items-center gap-2 text-xs text-gray-400 mb-2.5">
                                          {a.tags?.[0] && (
                                              <span
                                                  className="text-blue-600 dark:text-blue-400 font-medium flex items-center gap-0.5">
                          <Hash className="w-3 h-3"/>{a.tags[0]}
                        </span>
                                          )}
                                          <span>·</span>
                                          <span className="flex items-center gap-1">
                        <Clock className="w-3 h-3"/>
                                              {a.created_at ? new Date(a.created_at).toLocaleDateString('zh-CN') : ''}
                      </span>
                                      </div>
                                      <h3 className="font-semibold text-gray-900 dark:text-white text-sm line-clamp-2 group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors leading-relaxed mb-3">
                                          {a.title}
                                      </h3>
                                      <p className="text-xs text-gray-400 line-clamp-2 mb-3 leading-relaxed">{a.excerpt || a.summary || ''}</p>
                                      <div className="flex items-center justify-between text-xs text-gray-400">
                                          <div className="flex items-center gap-3">
                                              <span className="flex items-center gap-1"><Eye
                                                  className="w-3 h-3"/>{a.views || 0}</span>
                                              <span className="flex items-center gap-1"><Heart
                                                  className="w-3 h-3"/>{a.likes || 0}</span>
                                          </div>
                                          {a.author && (
                                              <div className="flex items-center gap-1.5">
                                                  {a.author.avatar ? (
                                                      <img src={a.author.avatar} alt=""
                                                           className="w-4 h-4 rounded-full"/>
                                                  ) : (
                                                      <div
                                                          className="w-4 h-4 rounded-full bg-gray-200 dark:bg-gray-700"/>
                                                  )}
                                                  <span>{a.author.username}</span>
                                              </div>
                                          )}
                                      </div>
                                  </div>
                              </motion.a>
                          ))}
                      </div>
                  </AnimatedSection>
              </div>
          )}

          {/* ═══════════════════════════════════
          POPULAR / TRENDING
         ═══════════════════════════════════ */}
          {popular.length > 0 && (
              <section className="bg-gray-50 dark:bg-gray-900/50 border-y border-gray-100 dark:border-gray-900">
                  <div className="max-w-6xl mx-auto px-4 sm:px-6 py-16 sm:py-20">
                      <AnimatedSection>
                          <motion.div variants={fadeUp} className="flex items-center gap-3 mb-10">
                              <div className="w-1 h-6 gradient-warm rounded-full"/>
                              <div>
                                  <h2 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
                                      <TrendingUp className="w-6 h-6 text-orange-500"/>
                                      热门趋势
                                  </h2>
                                  <p className="text-sm text-gray-500 mt-1">最受欢迎的内容</p>
                              </div>
                          </motion.div>

                          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
                              {popular.map((a, i) => (
                                  <motion.a
                                      key={a.id}
                                      variants={fadeUp}
                                      href={`/view?slug=${a.slug}`}
                                      className="group flex gap-4 p-4 rounded-2xl bg-white dark:bg-gray-900 border border-gray-100 dark:border-gray-800 card-hover"
                                  >
                                      {/* Rank number */}
                                      <div
                                          className={`flex-shrink-0 w-10 h-10 rounded-xl flex items-center justify-center text-lg font-extrabold ${
                                              i === 0 ? 'bg-yellow-100 dark:bg-yellow-900/20 text-yellow-600' :
                                                  i === 1 ? 'bg-gray-100 dark:bg-gray-800 text-gray-500' :
                                                      i === 2 ? 'bg-orange-100 dark:bg-orange-900/20 text-orange-600' :
                                                          'bg-gray-50 dark:bg-gray-800 text-gray-400'
                                          }`}>
                                          {i + 1}
                                      </div>
                                      <div className="flex-1 min-w-0">
                                          <h3 className="font-semibold text-gray-900 dark:text-white text-sm line-clamp-2 group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors leading-relaxed">
                                              {a.title}
                                          </h3>
                                          <div className="flex items-center gap-3 text-xs text-gray-400 mt-2">
                                              <span className="flex items-center gap-1"><Eye
                                                  className="w-3 h-3"/>{a.views || 0}</span>
                                              <span className="flex items-center gap-1"><Heart
                                                  className="w-3 h-3"/>{a.likes || 0}</span>
                                          </div>
                                      </div>
                                  </motion.a>
                              ))}
                          </div>
                      </AnimatedSection>
                  </div>
              </section>
          )}

          {/* ═══════════════════════════════════
          CTA SECTION
         ═══════════════════════════════════ */}
          <section className="max-w-6xl mx-auto px-4 sm:px-6 py-16 sm:py-20">
              <AnimatedSection>
                  <motion.div
                      variants={scaleIn}
                      className="relative rounded-3xl overflow-hidden p-8 sm:p-12 lg:p-16 text-center"
                  >
                      {/* Background */}
                      <div className="absolute inset-0 gradient-primary opacity-90"/>
                      <div
                          className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDAiIGhlaWdodD0iNDAiIHZpZXdCb3g9IjAgMCA0MCA0MCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48ZyBmaWxsPSJub25lIiBmaWxsLXJ1bGU9ImV2ZW5vZGQiPjxjaXJjbGUgY3g9IjIwIiBjeT0iMjAiIHI9IjEiIGZpbGw9InJnYmEoMjU1LDI1NSwyNTUsMC4xKSIvPjwvZz48L3N2Zz4=')] opacity-30"/>

                      <div className="relative z-10">
                          <h2 className="text-3xl sm:text-4xl font-bold text-white mb-4">
                              准备好开始创作了吗？
                          </h2>
                          <p className="text-blue-100 text-lg mb-8 max-w-lg mx-auto">
                              加入 FastBlog，与数千名创作者一起分享你的知识和想法。
                          </p>
                          <div className="flex flex-wrap items-center justify-center gap-4">
                              <a href="/register"
                                 className="px-8 py-3.5 bg-white text-blue-600 font-semibold rounded-xl hover:bg-blue-50 transition-colors shadow-lg">
                                  免费注册
                              </a>
                              <a href="/about"
                                 className="px-8 py-3.5 border-2 border-white/30 text-white font-medium rounded-xl hover:bg-white/10 transition-colors">
                                  了解更多
                              </a>
                          </div>
                      </div>
                  </motion.div>
              </AnimatedSection>
      </section>
    </div>
  );
}
