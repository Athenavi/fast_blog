'use client';

/**
 * 首页精选 - 编辑式杂志网格
 * - Hero 已展示 featured[0]，本区块展示其余头条（最多 4 篇）
 * - 不对称网格：首篇大图 + 衬线标题，其余竖排小条目
 * - 无卡片边框、无渐变遮罩、无图标堆砌
 */
import React from 'react';
import {motion} from 'framer-motion';
import {getFullMediaUrl} from '@/lib/utils';
import {Article, fadeUp, Section, SectionHeader} from './_shared';

interface Props {
  featured: Article[];
  title: string;
  noSummaryMsg?: string;
}

export default function HomeFeatured({featured, title, noSummaryMsg = '暂无摘要'}: Props) {
  const rest = featured.slice(1, 5);
  if (!rest.length) return null;

  const [lead, ...others] = rest;

  return (
    <Section className="relative bg-[#05070f]">
      <div className="max-w-7xl mx-auto px-6 sm:px-8 py-20 sm:py-28">
        <SectionHeader title={title} href="/articles"/>

        <div className="grid lg:grid-cols-12 gap-x-12 gap-y-10">
          {/* 头条大图 */}
          <motion.a variants={fadeUp} href={`/view?slug=${lead.slug}`}
                    className="group lg:col-span-7 block">
            <div className="relative aspect-[16/10] overflow-hidden rounded-xl bg-slate-900">
              {lead.cover_image ? (
                <img src={getFullMediaUrl(lead.cover_image)} alt={lead.title}
                     className="w-full h-full object-cover transition-transform duration-700 group-hover:scale-[1.03]"
                     loading="lazy"/>
              ) : (
                <div className="w-full h-full flex items-center justify-center">
                  <span className="font-serif text-5xl text-slate-800">F</span>
                </div>
              )}
            </div>
            <div className="mt-6">
              {lead.tags?.[0] &&
                <p className="mb-3 text-xs font-medium tracking-[0.15em] text-blue-400">{lead.tags[0]}</p>}
              <h3
                className="font-serif text-2xl sm:text-3xl font-semibold text-slate-100 leading-snug transition-colors duration-300 group-hover:text-blue-300">
                {lead.title}
              </h3>
              <p
                className="mt-3 text-sm leading-relaxed text-slate-400 line-clamp-2">{lead.excerpt || lead.summary || noSummaryMsg}</p>
              <p className="mt-4 text-xs text-slate-600">
                {lead.created_at ? new Date(lead.created_at).toLocaleDateString('zh-CN') : ''}
                {lead.views !== undefined ? ` · ${lead.views.toLocaleString()} 次阅读` : ''}
              </p>
            </div>
          </motion.a>

          {/* 竖排小条目 */}
          <div className="lg:col-span-5 flex flex-col divide-y divide-white/[0.06]">
            {others.map((article, i) => (
              <motion.a key={article.id} variants={fadeUp} href={`/view?slug=${article.slug}`}
                        className="group flex items-center gap-5 py-6 first:pt-0 last:pb-0">
                <div className="flex-shrink-0 w-24 h-20 overflow-hidden rounded-lg bg-slate-900 sm:w-28 sm:h-22">
                  {article.cover_image ? (
                    <img src={getFullMediaUrl(article.cover_image)} alt={article.title}
                         className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
                         loading="lazy"/>
                  ) : (
                    <div className="w-full h-full flex items-center justify-center">
                      <span className="font-serif text-2xl text-slate-800">F</span>
                    </div>
                  )}
                </div>
                <div className="min-w-0 flex-1">
                  <h4
                    className="font-medium text-slate-100 leading-snug line-clamp-2 transition-colors duration-300 group-hover:text-blue-300">
                    {article.title}
                  </h4>
                  <p className="mt-1.5 text-xs text-slate-600">
                    {article.created_at ? new Date(article.created_at).toLocaleDateString('zh-CN') : ''}
                    {article.views !== undefined ? ` · ${article.views.toLocaleString()} 次阅读` : ''}
                  </p>
                </div>
              </motion.a>
            ))}
          </div>
        </div>
      </div>
    </Section>
  );
}
