'use client';

import React from 'react';
import {motion} from 'framer-motion';
import {Eye, Flame, TrendingUp} from 'lucide-react';
import {getFullMediaUrl} from '@/lib/utils';
import {Article} from './_shared';
import {Section, fadeUp} from './_shared';

interface Props {
  articles: Article[];
}

const rankBgs = ['bg-amber-500 text-white shadow-lg shadow-amber-500/30', 'bg-gray-400 text-white', 'bg-orange-600 text-white'];

export default function HomePopular({articles}: Props) {
  if (!articles.length) return null;
  return (
    <Section id="trending" className="py-20 sm:py-28 bg-gray-50 dark:bg-gray-900/50 border-y border-gray-100 dark:border-gray-900">
      <div className="max-w-7xl mx-auto px-6 sm:px-8">
        <motion.div variants={fadeUp} className="flex items-end justify-between mb-12">
          <div>
            <div className="flex items-center gap-3 mb-3">
              <div className="w-10 h-1 bg-gradient-to-r from-orange-500 to-red-500 rounded-full" />
              <span className="text-sm font-semibold text-orange-600 dark:text-orange-400 uppercase tracking-widest">Trending</span>
            </div>
            <h2 className="text-3xl sm:text-4xl font-black text-gray-900 dark:text-white tracking-tight flex items-center gap-3">
              <Flame className="w-8 h-8 text-orange-500" /> 热门趋势
            </h2>
            <p className="text-gray-500 dark:text-gray-400 mt-2">最受欢迎的内容</p>
          </div>
        </motion.div>

        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-5">
          {articles.map((article, i) => (
            <motion.a key={article.id} variants={fadeUp} href={`/view?slug=${article.slug}`}
              className="group relative flex flex-col bg-white dark:bg-gray-900 rounded-2xl border border-gray-100 dark:border-gray-800 overflow-hidden
                hover:border-gray-200 dark:hover:border-gray-700 hover:shadow-xl hover:shadow-black/5 dark:hover:shadow-black/30 transition-all duration-500 hover:-translate-y-1">
              <div className="absolute top-3 left-3 z-10">
                <span className={`inline-flex items-center justify-center w-8 h-8 rounded-lg text-sm font-black ${rankBgs[i] || 'bg-gray-200 dark:bg-gray-700 text-gray-500 dark:text-gray-400'}`}>{i + 1}</span>
              </div>
              <div className="relative aspect-[16/10] bg-gray-50 dark:bg-gray-800 overflow-hidden">
                {article.cover_image ? (
                  <img src={getFullMediaUrl(article.cover_image)} alt={article.title}
                    className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-700" loading="lazy" />
                ) : (
                  <div className="w-full h-full flex items-center justify-center"><TrendingUp className="w-10 h-10 text-gray-200 dark:text-gray-700" /></div>
                )}
              </div>
              <div className="p-4 flex-1">
                <h3 className="font-bold text-gray-900 dark:text-white text-sm line-clamp-2 group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors leading-relaxed mb-3">{article.title}</h3>
                <div className="flex items-center gap-3 text-xs text-gray-400">
                  <span><Eye className="w-3 h-3 inline" /> {article.views || 0}</span>
                  <span><Eye className="w-3 h-3 inline" /> {article.likes || 0}</span>
                </div>
              </div>
            </motion.a>
          ))}
        </div>
      </div>
    </Section>
  );
}
