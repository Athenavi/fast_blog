'use client';

import React, {useCallback, useEffect, useRef, useState} from 'react';
import {motion, useInView} from 'framer-motion';
import {ChevronLeft, ChevronRight} from 'lucide-react';

/* ─── Types ─── */
export interface Article {
  id: number;
  title: string;
  slug: string;
  excerpt?: string;
  summary?: string;
  cover_image?: string;
  created_at?: string;
  views?: number;
  likes?: number;
  tags?: string[];
  category?: string;
  author?: { username?: string; avatar?: string };
}

export interface Category {
  id: number;
  name: string;
  slug: string;
  count?: number;
  image?: string;
  description?: string;
}

export interface Stats {
  total_articles?: number;
  total_users?: number;
  total_views?: number;
  total_comments?: number;
}

/* ─── Animation Variants ─── */
export const fadeUp = {
  hidden: {opacity: 0, y: 40},
  visible: {opacity: 1, y: 0, transition: {duration: 0.7, ease: [0.22, 1, 0.36, 1] as const}},
};

export const fadeIn = {
  hidden: {opacity: 0},
  visible: {opacity: 1, transition: {duration: 0.6}},
};

export const staggerContainer = {
  hidden: {},
  visible: {transition: {staggerChildren: 0.1, delayChildren: 0.1}},
};

export const scaleIn = {
  hidden: {opacity: 0, scale: 0.9},
  visible: {opacity: 1, scale: 1, transition: {duration: 0.5, ease: [0.22, 1, 0.36, 1] as const}},
};

export const slideFromLeft = {
  hidden: {opacity: 0, x: -60},
  visible: {opacity: 1, x: 0, transition: {duration: 0.8, ease: [0.22, 1, 0.36, 1] as const}},
};

export const slideFromRight = {
  hidden: {opacity: 0, x: 60},
  visible: {opacity: 1, x: 0, transition: {duration: 0.8, ease: [0.22, 1, 0.36, 1] as const}},
};

/* ─── Section Wrapper ─── */
export const Section: React.FC<{ children: React.ReactNode; className?: string; id?: string }> = ({children, className = '', id}) => {
  const ref = useRef(null);
  const isInView = useInView(ref, {once: true, margin: '-80px'});
  return (
    <motion.section ref={ref} id={id} initial="hidden" animate={isInView ? 'visible' : 'hidden'}
      variants={staggerContainer} className={className}>
      {children}
    </motion.section>
  );
};

/* ─── Animated Counter ─── */
export const AnimatedNumber: React.FC<{ value: number; suffix?: string }> = ({value, suffix = ''}) => {
  const [display, setDisplay] = useState(0);
  const ref = useRef<HTMLSpanElement>(null);
  const isInView = useInView(ref, {once: true});
  useEffect(() => {
    if (!isInView || value === 0) return;
    const start = Date.now();
    const tick = () => {
      const p = Math.min((Date.now() - start) / 1800, 1);
      setDisplay(Math.floor((1 - Math.pow(1 - p, 3)) * value));
      if (p < 1) requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  }, [isInView, value]);
  return <span ref={ref}>{display.toLocaleString()}{suffix}</span>;
};

/* ─── Horizontal Scroll Container ─── */
export const HorizontalScroll: React.FC<{ children: React.ReactNode; className?: string }> = ({children, className = ''}) => {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [canScrollLeft, setCanScrollLeft] = useState(false);
  const [canScrollRight, setCanScrollRight] = useState(true);

  const check = useCallback(() => {
    const el = scrollRef.current;
    if (!el) return;
    setCanScrollLeft(el.scrollLeft > 10);
    setCanScrollRight(el.scrollLeft < el.scrollWidth - el.clientWidth - 10);
  }, []);

  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    el.addEventListener('scroll', check, {passive: true});
    check();
    return () => el.removeEventListener('scroll', check);
  }, [check]);

  const scroll = (dir: 'left' | 'right') => {
    const el = scrollRef.current;
    if (!el) return;
    el.scrollBy({left: (dir === 'left' ? -1 : 1) * el.clientWidth * 0.75, behavior: 'smooth'});
  };

  const btn = (dir: 'left' | 'right', show: boolean, Icon: typeof ChevronLeft) =>
    show ? <button onClick={() => scroll(dir)}
      className={`absolute top-1/2 -translate-y-1/2 z-20 w-12 h-12 flex items-center justify-center
        bg-white/90 dark:bg-gray-900/90 backdrop-blur-sm rounded-full shadow-xl border border-gray-200/50 dark:border-gray-700/50
        opacity-0 group-hover/scroll:opacity-100 transition-all duration-300 hover:scale-110 ${dir === 'left' ? '-translate-x-2 left-0' : 'translate-x-2 right-0'}`}
      aria-label={`${dir === 'left' ? '向左' : '向右'}滚动`}>
      <Icon className="w-5 h-5 text-gray-700 dark:text-gray-300"/>
    </button> : null;

  return (
    <div className="relative group/scroll">
      {btn('left', canScrollLeft, ChevronLeft)}
      {btn('right', canScrollRight, ChevronRight)}
      <div ref={scrollRef}
        className={`flex gap-6 overflow-x-auto scroll-smooth snap-x snap-mandatory pb-4 scrollbar-hide ${className}`}
        style={{scrollbarWidth: 'none', msOverflowStyle: 'none'}}>
        {children}
      </div>
    </div>
  );
};
