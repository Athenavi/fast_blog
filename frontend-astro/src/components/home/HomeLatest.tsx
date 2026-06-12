'use client';

import React from 'react';
import {motion} from 'framer-motion';
import {ArrowRight, BookOpen, Clock, Eye, Hash, Heart} from 'lucide-react';
import {getFullMediaUrl} from '@/lib/utils';
import {Article} from './_shared';
import {Section, fadeUp} from './_shared';

interface Props {
  articles: Article[];
  title: string;
}

export default function HomeLatest({articles, title}: Props) {
  if (!articles.length) return null;
  return (
    <Section className="max-w-7xl mx-auto px-6 sm:px-8 py-20 sm:py-28">
      <motion.div variants={fadeUp} className="flex items-end justify-between mb-12">
        <div>
          <div className="flex items-center gap-3 mb-3">
            <div className="w-10 h-1 bg-gradient-to-r from-emerald-600 to-teal-500 rounded-full" />
            <span className="text-sm font-semibold text-emerald-600 dark:text-emerald-400 uppercase tracking-widest">Latest</span>
          </div>
          <h2 className="text-3xl sm:text-4xl font-black theme-text tracking-tight">{title}</h2>
        </div>
        <a href="/articles" className="hidden sm:flex items-center gap-2 text-sm font-semibold text-gray-500 hover:text-emerald-600 dark:text-gray-400 dark:hover:text-emerald-400 transition-colors group">
          查看全部 <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-1" />
        </a>
      </motion.div>

      <div className="grid sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
        {articles.map((article) => (
          <motion.a key={article.id} variants={fadeUp} href={`/view?slug=${article.slug}`}
            className="group flex flex-col theme-bg rounded-2xl border theme-border overflow-hidden
              hover:theme-border transition-all duration-500 hover:-translate-y-1">
            <div className="relative aspect-[16/10] bg-gray-50 dark:bg-gray-800 overflow-hidden">
              {article.cover_image ? (
                <img src={getFullMediaUrl(article.cover_image)} alt={article.title}
                  className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-700" loading="lazy" />
              ) : (
                <div className="w-full h-full flex items-center justify-center"><BookOpen className="w-10 h-10 text-gray-200 dark:text-gray-700" /></div>
              )}
              {article.category && (
                <div className="absolute top-3 left-3">
                  <span className="px-2.5 py-1 bg-white/90 dark:bg-gray-900/90 backdrop-blur-sm text-gray-700 dark:text-gray-300 text-[11px] font-medium rounded-lg border border-gray-200/50 dark:border-gray-700/50">{article.category}</span>
                </div>
              )}
            </div>
            <div className="flex-1 p-5 flex flex-col">
              <div className="flex items-center gap-2 text-xs text-gray-400 mb-3">
                {article.tags?.[0] && <span className="text-blue-600 dark:text-blue-400 font-medium flex items-center gap-0.5"><Hash className="w-3 h-3" />{article.tags[0]}</span>}
                {article.tags?.[0] && <span>·</span>}
                {article.created_at && <span className="flex items-center gap-1"><Clock className="w-3 h-3" />{new Date(article.created_at).toLocaleDateString('zh-CN')}</span>}
              </div>
              <h3 className="font-bold theme-text text-sm line-clamp-2 group-hover:theme-text-primary transition-colors leading-relaxed mb-3">{article.title}</h3>
              <p className="text-xs theme-text-secondary line-clamp-2 leading-relaxed mb-4 flex-1">{article.excerpt || article.summary || ''}</p>
              <div className="flex items-center justify-between text-xs text-gray-400 pt-3 border-t border-gray-50 dark:border-gray-800/50">
                <div className="flex items-center gap-3">
                  <span><Eye className="w-3 h-3 inline" /> {article.views || 0}</span>
                  <span><Heart className="w-3 h-3 inline" /> {article.likes || 0}</span>
                </div>
                {article.author && (
                  <div className="flex items-center gap-1.5">
                    {article.author.avatar ? <img src={article.author.avatar} alt="" className="w-5 h-5 rounded-full" /> :
                      <div className="w-5 h-5 rounded-full bg-gradient-to-br from-blue-400 to-purple-400" />}
                    <span className="font-medium text-gray-500 dark:text-gray-400">{article.author.username}</span>
                  </div>
                )}
              </div>
            </div>
          </motion.a>
        ))}
      </div>
    </Section>
  );
}
