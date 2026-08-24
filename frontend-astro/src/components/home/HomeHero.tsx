'use client';

/**
 * 首页 Hero - 完全重构版
 * 设计语言（用户确认）：编辑杂志 × 暗色科技
 * - 三维线框物件（three.js，懒加载）为主视觉，浮在深色基底上
 * - 左侧衬线头条标题 + 摘要 + 单 CTA，编辑报头式排版
 * - 滚动视差：文字层上移淡出，场景层缓移
 * - 无轮播、无粒子雨、无玻璃 pill、无 `01/05` 分页
 */
import React, {lazy, Suspense, useRef} from 'react';
import {motion, useReducedMotion, useScroll, useTransform} from 'framer-motion';
import {ArrowRight} from 'lucide-react';
import {Article} from './_shared';

const WireframeScene = lazy(() => import('./three/WireframeScene'));

interface Props {
  featured: Article[];
  heroTitle: string;
  heroSubtitle: string;
  heroCtaText: string;
  heroCtaLink: string;
  ctaTarget: string;
  heroBg?: string;
  loading?: boolean;
}

export default function HomeHero({
  featured, heroTitle, heroSubtitle, heroCtaText,
                                   heroCtaLink, ctaTarget,
}: Props) {
  const reduced = useReducedMotion();
  const heroRef = useRef<HTMLElement>(null);
  const {scrollYProgress} = useScroll({target: heroRef, offset: ['start start', 'end start']});
  const textY = useTransform(scrollYProgress, [0, 1], [0, 140]);
  const sceneY = useTransform(scrollYProgress, [0, 1], [0, 70]);
  const fade = useTransform(scrollYProgress, [0, 0.7], [1, 0]);

  const head = featured[0] || {};
  const hasHeadline = !!head.title;
  const headline = hasHeadline ? head.title : (heroTitle || '');
  const summary = (head.excerpt || head.summary || heroSubtitle || '').replace(/\s+/g, ' ').trim();
  const primaryHref = hasHeadline && head.slug ? `/view?slug=${head.slug}` : (heroCtaLink || '/articles');
  const primaryText = hasHeadline ? '阅读全文' : (heroCtaText || '开始阅读');

  return (
    <section ref={heroRef} className="relative min-h-[100dvh] overflow-hidden bg-[#05070f]">
      {/* 深空基底：品牌蓝径向光晕，克制 */}
      <div
        className="absolute inset-0"
        style={{background: 'radial-gradient(ellipse 70% 60% at 35% 38%, rgba(30, 58, 138, 0.4), transparent 65%), radial-gradient(ellipse 50% 45% at 85% 80%, rgba(15, 23, 42, 0.9), transparent 70%)'}}
      />

      {/* three.js 线框场景（懒加载，透明 Canvas 浮于基底） */}
      <motion.div style={{y: reduced ? 0 : sceneY}} className="absolute inset-0" aria-hidden>
        <Suspense fallback={null}>
          <WireframeScene reducedMotion={!!reduced}/>
        </Suspense>
      </motion.div>

      {/* 左侧文字区：编辑报头式 */}
      <motion.div style={reduced ? undefined : {y: textY, opacity: fade}}
                  className="relative z-10 flex min-h-[100dvh] items-center">
        <div className="max-w-7xl mx-auto px-6 sm:px-8 w-full pt-24 pb-20">
          <div className="max-w-2xl">
            <motion.p
              initial={{opacity: 0, y: 24}} animate={{opacity: 1, y: 0}}
              transition={{duration: 0.6, delay: 0.15}}
              className="mb-6 text-sm font-medium tracking-[0.2em] text-blue-400/90"
            >
              {head.category || '精选内容'}
            </motion.p>

            <motion.h1
              initial={{opacity: 0, y: 32}} animate={{opacity: 1, y: 0}}
              transition={{duration: 0.8, delay: 0.3}}
              className="font-serif text-4xl sm:text-5xl lg:text-6xl font-semibold text-slate-100 leading-[1.15] tracking-tight text-balance"
            >
              {headline || 'FastBlog'}
            </motion.h1>

            <motion.p
              initial={{opacity: 0, y: 24}} animate={{opacity: 1, y: 0}}
              transition={{duration: 0.7, delay: 0.5}}
              className="mt-6 max-w-xl text-base sm:text-lg leading-relaxed text-slate-400"
            >
              {summary || heroSubtitle}
            </motion.p>

            <motion.div
              initial={{opacity: 0, y: 20}} animate={{opacity: 1, y: 0}}
              transition={{duration: 0.6, delay: 0.7}}
              className="mt-10 flex flex-wrap items-center gap-5"
            >
              <a
                href={primaryHref}
                target={ctaTarget as React.HTMLAttributeAnchorTarget | undefined}
                className="group inline-flex items-center gap-2.5 px-7 py-3.5 rounded-full bg-blue-600 text-white text-sm font-semibold
                  hover:bg-blue-500 transition-colors duration-300 shadow-lg shadow-blue-900/40 active:scale-[0.98]"
              >
                {primaryText}
                <ArrowRight className="w-4 h-4 transition-transform duration-300 group-hover:translate-x-1"/>
              </a>
              <a
                href="/articles"
                className="text-sm font-medium text-slate-300 underline decoration-slate-600 underline-offset-4
                  hover:text-white hover:decoration-blue-500 transition-colors duration-300"
              >
                浏览全部文章
              </a>
            </motion.div>

            {/* 头条元数据：编辑式细线分隔（无图标堆砌） */}
            {hasHeadline && head.created_at && (
              <motion.div
                initial={{opacity: 0}} animate={{opacity: 1}}
                transition={{duration: 0.6, delay: 0.9}}
                className="mt-14 flex items-center gap-3 text-xs text-slate-500"
              >
                <span>{new Date(head.created_at).toLocaleDateString('zh-CN', {
                  year: 'numeric',
                  month: 'long',
                  day: 'numeric'
                })}</span>
                {head.views !== undefined && (
                  <>
                    <span className="w-px h-3 bg-slate-700"/>
                    <span>{head.views.toLocaleString()} 次阅读</span>
                  </>
                )}
              </motion.div>
            )}
          </div>
        </div>
      </motion.div>

      {/* 底部与下一区块衔接的暗色过渡 */}
      <div
        className="absolute bottom-0 left-0 right-0 h-24 bg-gradient-to-t from-[#05070f] to-transparent pointer-events-none"/>
    </section>
  );
}
