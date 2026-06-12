'use client';

import React from 'react';
import {motion} from 'framer-motion';
import {ArrowRight, BookOpen, Calendar, Eye, Hash, Heart} from 'lucide-react';
import {getFullMediaUrl} from '@/lib/utils';
import {Article} from './_shared';
import {Section, fadeUp} from './_shared';

interface Props {
  featured: Article[];
  title: string;
  noSummaryMsg?: string;
}

export default function HomeFeatured({featured, title, noSummaryMsg = '暂无摘要'}: Props) {
  if (!featured.length) return null;
  return (
    <Section className="max-w-7xl mx-auto px-6 sm:px-8 py-20 sm:py-28">
      <motion.div variants={fadeUp} className="flex items-end justify-between mb-12">
        <div>
          <div className="flex items-center gap-3 mb-3">
            <div className="w-10 h-1 bg-gradient-to-r from-blue-600 to-cyan-500 rounded-full" />
            <span className="text-sm font-semibold text-blue-600 dark:text-blue-400 uppercase tracking-widest">Featured</span>
          </div>
          <h2 className="text-3xl sm:text-4xl font-black theme-text tracking-tight">{title}</h2>
        </div>
        <a href="/articles" className="hidden sm:flex items-center gap-2 text-sm font-semibold theme-text-secondary hover:theme-text-primary transition-colors group">
          查看全部 <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-1" />
        </a>
      </motion.div>

      <div className="grid lg:grid-cols-12 gap-6">
        {/* Main */}
        <motion.div variants={fadeUp} className="lg:col-span-7">
          <a href={`/view?slug=${featured[0].slug}`} className="group block relative aspect-[16/10] rounded-2xl overflow-hidden theme-bg-muted">
            {featured[0].cover_image ? (
              <img src={getFullMediaUrl(featured[0].cover_image)} alt={featured[0].title}
                className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-700" loading="lazy" />
            ) : (
              <div className="w-full h-full flex items-center justify-center bg-gradient-to-br from-blue-50 to-purple-50 dark:from-blue-950/50 dark:to-purple-950/50">
                <BookOpen className="w-20 h-20 text-gray-200 dark:text-gray-800" />
              </div>
            )}
            <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/20 to-transparent" />
            <div className="absolute bottom-0 left-0 right-0 p-6 sm:p-8">
              {featured[0].tags?.[0] && (
                <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-blue-600 text-white text-xs font-semibold rounded-full mb-4">
                  <Hash className="w-3 h-3" />{featured[0].tags[0]}
                </span>
              )}
              <h3 className="text-2xl sm:text-3xl font-bold text-white mb-3 leading-tight line-clamp-2 group-hover:text-blue-200 transition-colors">{featured[0].title}</h3>
              <p className="text-white/70 text-sm line-clamp-2 max-w-lg mb-4">{featured[0].excerpt || featured[0].summary || noSummaryMsg}</p>
              <div className="flex items-center gap-4 text-xs text-white/50">
                {featured[0].created_at && (<span className="flex items-center gap-1.5"><Calendar className="w-3.5 h-3.5" />{new Date(featured[0].created_at).toLocaleDateString('zh-CN')}</span>)}
                <span className="flex items-center gap-1.5"><Eye className="w-3.5 h-3.5" />{featured[0].views || 0}</span>
                <span className="flex items-center gap-1.5"><Heart className="w-3.5 h-3.5" />{featured[0].likes || 0}</span>
              </div>
            </div>
          </a>
        </motion.div>

        {/* Side list */}
        <div className="lg:col-span-5 flex flex-col gap-4">
          {featured.slice(1, 4).map(article => (
            <motion.a key={article.id} variants={fadeUp} href={`/view?slug=${article.slug}`}
              className="group flex gap-4 p-3 rounded-xl border theme-border hover:theme-border-primary theme-bg transition-all duration-300">
              <div className="flex-shrink-0 w-28 h-20 rounded-lg overflow-hidden bg-gray-100 dark:bg-gray-800">
                {article.cover_image ? (
                  <img src={getFullMediaUrl(article.cover_image)} alt={article.title}
                    className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" loading="lazy" />
                ) : (
                  <div className="w-full h-full flex items-center justify-center"><BookOpen className="w-6 h-6 text-gray-300 dark:text-gray-700" /></div>
                )}
              </div>
              <div className="flex-1 min-w-0 flex flex-col justify-center">
                <h4 className="font-semibold theme-text text-sm line-clamp-2 group-hover:theme-text-primary transition-colors leading-snug">{article.title}</h4>
                <div className="flex items-center gap-3 mt-2 text-xs text-gray-400">
                  <span><Eye className="w-3 h-3 inline" /> {article.views || 0}</span>
                  <span><Heart className="w-3 h-3 inline" /> {article.likes || 0}</span>
                </div>
              </div>
            </motion.a>
          ))}
        </div>
      </div>
    </Section>
  );
}
