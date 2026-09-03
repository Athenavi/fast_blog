'use client';

/**
 * 首页热门 - 大数字排名列表
 * - 超大衬线排名数字（前 3 名蓝色 tint），标题 + 摘要 + 浏览量
 * - 细线分隔，无卡片无火焰图标
 */
import React from 'react';
import {motion} from 'framer-motion';
import {Article, fadeUp, Section, SectionHeader} from './_shared';

interface Props {
  articles: Article[];
}

export default React.memo((props: Props) => HomePopular(props));
HomePopular.displayName = 'HomePopular';

function HomePopular({articles}: Props) {
  if (!articles.length) return null;
  const list = articles.slice(0, 8);

  return (
    <Section id="trending" className="relative bg-[#05070f]">
      <div className="max-w-7xl mx-auto px-6 sm:px-8 py-20 sm:py-28">
        <SectionHeader title="热门趋势" href="/articles"/>

        <div className="grid lg:grid-cols-2 gap-x-16">
          {[list.slice(0, 4), list.slice(4, 8)].map((column, colIdx) => (
            <div key={colIdx} className="divide-y divide-white/[0.06]">
              {column.map((article, i) => {
                const rank = colIdx * 4 + i + 1;
                return (
                  <motion.a key={article.id} variants={fadeUp} href={`/view?slug=${article.slug}`}
                            className="group flex items-start gap-6 py-6">
                    <span className={`font-serif text-4xl sm:text-5xl font-semibold leading-none tabular-nums
                      ${rank <= 3 ? 'text-blue-500/90' : 'text-slate-700'} transition-colors duration-300 group-hover:text-blue-400`}>
                      {rank}
                    </span>
                    <div className="min-w-0 flex-1">
                      <h3
                        className="font-medium text-slate-100 leading-snug transition-colors duration-300 group-hover:text-blue-300 line-clamp-2">
                        {article.title}
                      </h3>
                      <p
                        className="mt-2 text-sm text-slate-500 line-clamp-2">{article.excerpt || article.summary || ''}</p>
                      <p className="mt-2.5 text-xs text-slate-600">
                        {article.views !== undefined ? `${article.views.toLocaleString()} 次阅读` : ''}
                        {article.likes !== undefined && article.views !== undefined &&
                          <span className="mx-1.5 text-slate-700">·</span>}
                        {article.likes !== undefined && `${article.likes.toLocaleString()} 次点赞`}
                      </p>
                    </div>
                  </motion.a>
                );
              })}
            </div>
          ))}
        </div>
      </div>
    </Section>
  );
}
