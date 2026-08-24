'use client';

/**
 * 首页最新 - 编辑式编号列表
 * - 双列列表，细线分隔，左侧 mono 编号，无卡片无边框
 * - 报纸首页式的阅读节奏
 */
import React from 'react';
import {motion} from 'framer-motion';
import {Article, fadeUp, Section, SectionHeader} from './_shared';

interface Props {
  articles: Article[];
  title: string;
}

const pad = (n: number) => String(n).padStart(2, '0');

export default function HomeLatest({articles, title}: Props) {
  if (!articles.length) return null;
  const left = articles.slice(0, 6);
  const right = articles.slice(6, 12);

  const renderList = (items: Article[], startIndex: number) => (
    <div className="divide-y divide-white/[0.06]">
      {items.map((article, i) => (
        <motion.a key={article.id} variants={fadeUp} href={`/view?slug=${article.slug}`}
                  className="group flex items-start gap-5 py-5">
          <span
            className="pt-0.5 font-mono text-xs leading-6 text-slate-600 tabular-nums transition-colors duration-300 group-hover:text-blue-400">
            {pad(startIndex + i + 1)}
          </span>
          <div className="min-w-0 flex-1">
            <h3
              className="font-medium text-slate-100 leading-snug transition-colors duration-300 group-hover:text-blue-300 line-clamp-1">
              {article.title}
            </h3>
            <p className="mt-1.5 text-sm text-slate-500 line-clamp-1">{article.excerpt || article.summary || ''}</p>
            <p className="mt-2 text-xs text-slate-600">
              {article.category && <span className="text-blue-400/80">{article.category}</span>}
              {article.category && article.created_at && <span className="mx-1.5 text-slate-700">·</span>}
              {article.created_at && new Date(article.created_at).toLocaleDateString('zh-CN')}
              {article.views !== undefined && (
                <>
                  <span className="mx-1.5 text-slate-700">·</span>
                  {article.views.toLocaleString()} 次阅读
                </>
              )}
            </p>
          </div>
        </motion.a>
      ))}
    </div>
  );

  return (
    <Section className="relative bg-[#070a14]">
      <div className="max-w-7xl mx-auto px-6 sm:px-8 py-20 sm:py-28">
        <SectionHeader title={title} href="/articles"/>

        <div className="grid lg:grid-cols-2 gap-x-16">
          {renderList(left, 0)}
          {right.length > 0 && renderList(right, left.length)}
        </div>
      </div>
    </Section>
  );
}
