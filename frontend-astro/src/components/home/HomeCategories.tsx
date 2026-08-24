'use client';

/**
 * 首页分类 - 编辑式编号网格
 * - 无横向滚动、无渐变卡片；名称 + 数量 + 描述，细线分隔
 */
import React from 'react';
import {motion} from 'framer-motion';
import {ArrowUpRight} from 'lucide-react';
import {Category, fadeUp, Section, SectionHeader} from './_shared';

interface Props {
  categories: Category[];
  title: string;
}

const pad = (n: number) => String(n).padStart(2, '0');

export default function HomeCategories({categories, title}: Props) {
  if (!categories.length) return null;
  const list = categories.slice(0, 9);

  return (
    <Section id="categories" className="relative bg-[#070a14]">
      <div className="max-w-7xl mx-auto px-6 sm:px-8 py-20 sm:py-28">
        <SectionHeader title={title} href="/categories"/>

        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-x-12">
          {list.map((cat, i) => (
            <motion.a key={cat.id} variants={fadeUp} href={`/category?slug=${cat.slug}`}
                      className="group flex items-start justify-between gap-4 border-b border-white/[0.06] py-5">
              <div className="flex items-baseline gap-4 min-w-0">
                <span
                  className="font-mono text-xs text-slate-600 tabular-nums transition-colors duration-300 group-hover:text-blue-400">
                  {pad(i + 1)}
                </span>
                <div className="min-w-0">
                  <h3 className="font-medium text-slate-100 transition-colors duration-300 group-hover:text-blue-300">
                    {cat.name}
                  </h3>
                  {cat.description && (
                    <p className="mt-1 text-sm text-slate-500 line-clamp-1">{cat.description}</p>
                  )}
                </div>
              </div>
              <div className="flex shrink-0 items-center gap-2 text-xs text-slate-600">
                {cat.count !== undefined && <span>{cat.count} 篇</span>}
                <ArrowUpRight
                  className="w-3.5 h-3.5 opacity-0 -translate-x-1 transition-all duration-300 group-hover:opacity-100 group-hover:translate-x-0 text-blue-400"/>
              </div>
            </motion.a>
          ))}
        </div>
      </div>
    </Section>
  );
}
