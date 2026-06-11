'use client';

import React, {useRef} from 'react';
import {AnimatePresence, motion, useScroll, useTransform} from 'framer-motion';
import {ArrowRight, ArrowUpRight, BookOpen, Eye, Heart, Sparkles} from 'lucide-react';
import {getFullMediaUrl} from '@/lib/utils';
import {Article} from './_shared';
import {fadeUp, staggerContainer} from './_shared';

const isVideo = (url: string) => /\.(mp4|webm|ogg|mov|avi|mkv)(\?|$)/i.test(url);

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
  heroCtaLink, ctaTarget, heroBg,
}: Props) {
  const [slide, setSlide] = React.useState(0);
  const heroRef = useRef<HTMLDivElement>(null);
  const {scrollYProgress} = useScroll({target: heroRef, offset: ['start start', 'end start']});
  const parallaxY = useTransform(scrollYProgress, [0, 1], [0, 150]);
  const opacity = useTransform(scrollYProgress, [0, 0.8], [1, 0]);

  const items = featured.slice(0, 5);
  const current = items[slide] || {};
  const bgUrl = current.cover_image || heroBg || '';
  const fullBg = bgUrl ? getFullMediaUrl(bgUrl) : '';

  // Auto-rotate
  React.useEffect(() => {
    if (items.length <= 1) return;
    const t = setInterval(() => setSlide(s => (s + 1) % items.length), 6000);
    return () => clearInterval(t);
  }, [items.length]);

  return (
    <section ref={heroRef} className="relative h-[90vh] min-h-[650px] max-h-[1000px] overflow-hidden">
      {/* Background parallax */}
      <motion.div style={{y: parallaxY}} className="absolute inset-0 -top-[10%] -bottom-[10%]">
        {fullBg && isVideo(current.cover_image || '') ? (
          <video src={fullBg} className="w-full h-full object-cover" autoPlay loop muted playsInline />
        ) : fullBg ? (
          <img src={fullBg} alt="" className="w-full h-full object-cover" loading="lazy" />
        ) : (
          <div className="w-full h-full bg-gradient-to-br from-gray-900 via-blue-950 to-gray-900" />
        )}
      </motion.div>

      {/* Overlays */}
      <div className="absolute inset-0 bg-gradient-to-r from-black/80 via-black/50 to-transparent" />
      <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-transparent to-black/30" />
      <div className="absolute bottom-0 left-0 right-0 h-32 bg-gradient-to-t from-white dark:from-gray-950 to-transparent" />

      {/* Particles */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        {[...Array(20)].map((_, i) => (
          <motion.div key={i} className="absolute w-1 h-1 bg-white/20 rounded-full"
            initial={{x: Math.random() * 1920, y: Math.random() * 1080}}
            animate={{y: [null, Math.random() * -300], opacity: [0, 0.6, 0]}}
            transition={{duration: Math.random() * 8 + 6, repeat: Infinity, delay: Math.random() * 5, ease: 'linear'}} />
        ))}
      </div>

      {/* Content */}
      <motion.div style={{opacity}} className="relative h-full flex items-center">
        <div className="max-w-7xl mx-auto px-6 sm:px-8 w-full">
          <div className="max-w-2xl">
            <motion.div initial={{opacity: 0, y: 20}} animate={{opacity: 1, y: 0}} transition={{duration: 0.6, delay: 0.2}}>
              <span className="inline-flex items-center gap-2 px-4 py-2 bg-white/10 backdrop-blur-md rounded-full text-sm font-medium text-white/90 border border-white/20 mb-8">
                <Sparkles className="w-4 h-4 text-amber-400" />{current.category || '精选内容'}
              </span>
            </motion.div>

            <AnimatePresence mode="wait">
              <motion.h1 key={slide} initial={{opacity: 0, y: 30}} animate={{opacity: 1, y: 0}} exit={{opacity: 0, y: -20}}
                transition={{duration: 0.7}} className="text-4xl sm:text-5xl lg:text-6xl xl:text-7xl font-black text-white tracking-tight leading-[1.05] mb-6">
                {current.title || heroTitle}
              </motion.h1>
            </AnimatePresence>

            <AnimatePresence mode="wait">
              <motion.p key={`s-${slide}`} initial={{opacity: 0, y: 20}} animate={{opacity: 1, y: 0}} exit={{opacity: 0, y: -10}}
                transition={{duration: 0.6, delay: 0.1}} className="text-base sm:text-lg lg:text-xl text-white/70 mb-10 leading-relaxed max-w-xl">
                {current.excerpt || current.summary || heroSubtitle}
              </motion.p>
            </AnimatePresence>

            <motion.div initial={{opacity: 0, y: 20}} animate={{opacity: 1, y: 0}} transition={{duration: 0.6, delay: 0.4}} className="flex flex-wrap gap-4">
              <a href={current.slug ? `/view?slug=${current.slug}` : heroCtaLink}
                target={ctaTarget as React.HTMLAttributeAnchorTarget}
                className="group inline-flex items-center gap-3 px-8 py-4 bg-white text-gray-900 font-bold rounded-xl hover:bg-gray-100 transition-all duration-300 shadow-2xl shadow-black/20 hover:shadow-white/20 hover:-translate-y-0.5">
                {heroCtaText} <ArrowRight className="w-5 h-5 transition-transform group-hover:translate-x-1" />
              </a>
              <a href="/articles" className="inline-flex items-center gap-3 px-8 py-4 bg-white/10 backdrop-blur-sm text-white font-medium rounded-xl border border-white/20 hover:bg-white/20 transition-all duration-300 hover:-translate-y-0.5">
                浏览全部 <ArrowUpRight className="w-5 h-5" />
              </a>
            </motion.div>

            {items.length > 1 && (
              <motion.div initial={{opacity: 0}} animate={{opacity: 1}} transition={{delay: 0.8}} className="flex items-center gap-2 mt-12">
                {items.map((_, i) => (
                  <button key={i} onClick={() => setSlide(i)}
                    className={`h-1 rounded-full transition-all duration-500 ${i === slide ? 'w-10 bg-white' : 'w-3 bg-white/30 hover:bg-white/50'}`} />
                ))}
                <span className="text-white/40 text-sm ml-3 font-mono">{String(slide + 1).padStart(2, '0')} / {String(items.length).padStart(2, '0')}</span>
              </motion.div>
            )}
          </div>
        </div>
      </motion.div>
    </section>
  );
}
