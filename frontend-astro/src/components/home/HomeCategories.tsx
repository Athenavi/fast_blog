'use client';

import React from 'react';
import {motion} from 'framer-motion';
import {ArrowRight, ArrowUpRight, BookOpen, Hash, Sparkles, Star, Flame, Zap} from 'lucide-react';
import {Category} from './_shared';
import {Section, HorizontalScroll, fadeUp, scaleIn} from './_shared';

const gradients = [
  'from-blue-600 via-blue-500 to-cyan-400', 'from-purple-600 via-purple-500 to-pink-400',
  'from-emerald-600 via-emerald-500 to-teal-400', 'from-orange-600 via-orange-500 to-amber-400',
  'from-indigo-600 via-indigo-500 to-blue-400', 'from-rose-600 via-rose-500 to-pink-400',
];
const icons = [Sparkles, Star, Flame, Zap, BookOpen, Hash];

interface Props {
  categories: Category[];
  title: string;
}

export default function HomeCategories({categories, title}: Props) {
  if (!categories.length) return null;
  return (
    <Section id="categories" className="py-20 sm:py-28 bg-gray-50 dark:bg-gray-900/50 border-y border-gray-100 dark:border-gray-900">
      <div className="max-w-7xl mx-auto px-6 sm:px-8">
        <motion.div variants={fadeUp} className="flex items-end justify-between mb-12">
          <div>
            <div className="flex items-center gap-3 mb-3">
              <div className="w-10 h-1 bg-gradient-to-r from-purple-600 to-pink-500 rounded-full" />
              <span className="text-sm font-semibold text-purple-600 dark:text-purple-400 uppercase tracking-widest">Explore</span>
            </div>
            <h2 className="text-3xl sm:text-4xl font-black text-gray-900 dark:text-white tracking-tight">{title}</h2>
            <p className="text-gray-500 dark:text-gray-400 mt-2">按主题浏览感兴趣的内容</p>
          </div>
          <a href="/categories" className="hidden sm:flex items-center gap-2 text-sm font-semibold text-gray-500 hover:text-purple-600 dark:text-gray-400 dark:hover:text-purple-400 transition-colors group">
            查看全部 <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-1" />
          </a>
        </motion.div>

        <HorizontalScroll>
          {categories.map((cat, i) => {
            const Icon = icons[i % icons.length];
            return (
              <motion.a key={cat.id} variants={scaleIn} href={`/category?slug=${cat.slug}`} className="group flex-shrink-0 w-[260px] snap-start">
                <div className="relative h-52 rounded-2xl overflow-hidden border border-gray-100 dark:border-gray-800 bg-white dark:bg-gray-900
                  hover:border-gray-200 dark:hover:border-gray-700 hover:shadow-2xl hover:shadow-black/10 dark:hover:shadow-black/40 transition-all duration-500 hover:-translate-y-2">
                  <div className={`absolute inset-0 bg-gradient-to-br ${gradients[i % gradients.length]} opacity-10 group-hover:opacity-20 transition-opacity duration-500`} />
                  <div className="relative h-full flex flex-col items-center justify-center p-6 text-center">
                    <div className={`w-14 h-14 rounded-2xl bg-gradient-to-br ${gradients[i % gradients.length]}
                      flex items-center justify-center mb-4 shadow-lg group-hover:scale-110 group-hover:rotate-3 transition-all duration-500`}>
                      <Icon className="w-7 h-7 text-white" />
                    </div>
                    <h3 className="font-bold text-gray-900 dark:text-white text-base mb-1.5">{cat.name}</h3>
                    <p className="text-xs text-gray-500 dark:text-gray-400">{cat.count || 0} 篇文章</p>
                    <div className="absolute bottom-4 right-4 w-8 h-8 rounded-full bg-gray-100 dark:bg-gray-800 flex items-center justify-center opacity-0 group-hover:opacity-100 translate-y-2 group-hover:translate-y-0 transition-all duration-300">
                      <ArrowUpRight className="w-4 h-4 text-gray-500 dark:text-gray-400" />
                    </div>
                  </div>
                </div>
              </motion.a>
            );
          })}
        </HorizontalScroll>
      </div>
    </Section>
  );
}
