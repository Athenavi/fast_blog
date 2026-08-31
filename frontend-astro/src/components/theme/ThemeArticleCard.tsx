'use client';

/**
 * ArticleCard 槽位组件 — 由主题契约 componentSlots.articleCard 决定卡片样式：
 * - "default"：标准卡片（grid=大图卡片 / list=横向条目），与默认渲染一致
 * - "compact"：紧凑卡片（更小封面、更少信息层级）
 *
 * 用于文章列表页（ArticleList）等公共列表。
 */
import React from 'react';
import {motion} from 'framer-motion';
import {BookOpen, Clock, Crown, Eye, Hash, Heart} from 'lucide-react';
import {getFullMediaUrl} from '@/lib/utils';
import {useThemeSlots} from '@/lib/theme-components';

interface Props {
  article: any;
  layout?: 'grid' | 'list';
  index?: number;
}

export default function ThemeArticleCard({article, layout = 'grid', index = 0}: Props) {
  const {articleCard} = useThemeSlots();
  const cover = article.cover_image ? getFullMediaUrl(article.cover_image) : '';
  const date = article.created_at ? new Date(article.created_at).toLocaleDateString('zh-CN') : '';
  const tag = article.tags?.[0];
  const href = `/view?slug=${article.slug}`;

  if (articleCard === 'compact') {
    // ── 紧凑变体 ──
    return (
      <motion.a key={article.id} initial={{opacity: 0, y: 12}} animate={{opacity: 1, y: 0}}
                transition={{delay: index * 0.04, duration: 0.35}}
                href={href}
                className="group flex items-center gap-4 p-3 rounded-xl border theme-border card-hover relative">
        {cover ? (
          <img src={cover} alt="" loading="lazy"
               className="w-20 h-16 rounded-lg object-cover flex-shrink-0"/>
        ) : (
          <div className="w-20 h-16 rounded-lg bg-gray-100 dark:bg-gray-800 flex items-center justify-center flex-shrink-0 relative">
            <BookOpen className="w-5 h-5 text-gray-300 dark:text-gray-600"/>
          </div>
        )}
        {article.is_vip_only && (
          <div className="absolute top-0.5 left-0.5">
            <span className="badge bg-amber-400/90 dark:bg-amber-500/20 text-amber-700 dark:text-amber-300 backdrop-blur-sm text-[8px] flex items-center gap-0.5 px-1 py-0.5">
              <Crown className="w-2 h-2"/>VIP
            </span>
          </div>
        )}
        <div className="min-w-0 flex-1">
          <h3 className="text-sm font-medium text-gray-900 dark:text-white line-clamp-2 group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">
            {article.title}
          </h3>
          <p className="mt-1 text-xs text-gray-400 flex items-center gap-2">
            <span className="flex items-center gap-1"><Clock className="w-3 h-3"/>{date}</span>
            {article.views !== undefined && (
              <span className="flex items-center gap-1"><Eye className="w-3 h-3"/>{article.views}</span>
            )}
          </p>
        </div>
      </motion.a>
    );
  }

  if (layout === 'list') {
    // ── 默认：横向条目（列表视图）──
    return (
      <motion.a key={article.id} initial={{opacity: 0, x: -20}} animate={{opacity: 1, x: 0}}
                transition={{delay: index * 0.03, duration: 0.4}}
                href={href}
                className="group flex gap-5 p-5 theme-bg rounded-2xl border theme-border card-hover">
        <div className="w-40 h-28 rounded-xl overflow-hidden bg-gray-50 dark:bg-gray-800 flex-shrink-0 hidden sm:block relative">
          {cover ? (
            <img src={cover} alt="" className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-700" loading="lazy"/>
          ) : (
            <div className="w-full h-full flex items-center justify-center">
              <BookOpen className="w-6 h-6 text-gray-200 dark:text-gray-700"/>
            </div>
          )}
          {article.is_vip_only && (
            <div className="absolute top-2 right-2">
              <span className="badge bg-amber-400/90 dark:bg-amber-500/20 text-amber-700 dark:text-amber-300 backdrop-blur-sm text-[9px] flex items-center gap-0.5 px-1.5 py-0.5">
                <Crown className="w-2.5 h-2.5"/>VIP
              </span>
            </div>
          )}
        </div>
        <div className="flex-1 min-w-0 flex flex-col justify-center">
          <div className="flex items-center gap-2 text-xs text-gray-400 mb-1.5">
            {tag && <span className="text-blue-600 dark:text-blue-400 font-medium">{tag}</span>}
            {tag && <span>·</span>}
            <span>{date}</span>
          </div>
          <h3 className="font-semibold text-gray-900 dark:text-white line-clamp-1 group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors mb-1">
            {article.title}
          </h3>
          <p className="text-sm text-gray-500 dark:text-gray-400 line-clamp-2">{article.excerpt || article.summary || ''}</p>
          <div className="flex items-center gap-4 text-xs text-gray-400 mt-2">
            <span className="flex items-center gap-1"><Eye className="w-3 h-3"/>{article.views || 0}</span>
            <span className="flex items-center gap-1"><Heart className="w-3 h-3"/>{article.likes || 0}</span>
          </div>
        </div>
      </motion.a>
    );
  }

  // ── 默认：网格卡片 ──
  return (
    <motion.a key={article.id} initial={{opacity: 0, y: 20}} animate={{opacity: 1, y: 0}}
              transition={{delay: index * 0.05, duration: 0.4}}
              href={href}
              className="group theme-bg rounded-2xl border theme-border overflow-hidden card-hover">
      <div className="aspect-[16/10] bg-gray-50 dark:bg-gray-800 overflow-hidden relative">
        {cover ? (
          <img src={cover} alt={article.title} className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-700" loading="lazy"/>
        ) : (
          <div className="w-full h-full flex items-center justify-center">
            <BookOpen className="w-8 h-8 text-gray-200 dark:text-gray-700"/>
          </div>
        )}
        {article.category?.name && (
          <div className="absolute top-3 left-3">
            <span className="badge bg-white/90 dark:bg-gray-900/90 text-gray-700 dark:text-gray-300 backdrop-blur-sm text-[10px]">
              {article.category.name}
            </span>
          </div>
        )}
        {article.is_vip_only && (
          <div className="absolute top-3 right-3">
            <span className="badge bg-amber-400/90 dark:bg-amber-500/20 text-amber-700 dark:text-amber-300 backdrop-blur-sm text-[10px] flex items-center gap-1">
              <Crown className="w-3 h-3"/>VIP
            </span>
          </div>
        )}
      </div>
      <div className="p-5">
        <div className="flex items-center gap-2 text-xs text-gray-400 mb-2.5">
          {tag && <span className="text-blue-600 dark:text-blue-400 font-medium flex items-center gap-0.5"><Hash className="w-3 h-3"/>{tag}</span>}
          {tag && <span>·</span>}
          <span className="flex items-center gap-1"><Clock className="w-3 h-3"/>{date}</span>
        </div>
        <h3 className="font-semibold text-gray-900 dark:text-white text-sm line-clamp-2 group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors leading-relaxed mb-2">
          {article.title}
        </h3>
        <p className="text-xs text-gray-400 line-clamp-2 mb-3">{article.excerpt || article.summary || ''}</p>
        <div className="flex items-center gap-3 text-xs text-gray-400">
          <span className="flex items-center gap-1"><Eye className="w-3 h-3"/>{article.views || 0}</span>
          <span className="flex items-center gap-1"><Heart className="w-3 h-3"/>{article.likes || 0}</span>
        </div>
      </div>
    </motion.a>
  );
}
