'use client';

import React, {useEffect, useState} from 'react';
import {apiClient} from '@/lib/api/base-client';
import {Loader2, FileQuestion} from 'lucide-react';

interface BlockData {
  type: string;
  data?: Record<string, any>;
  styles?: Record<string, any>;
  children?: BlockData[];
}

interface PageData {
  id: number;
  title: string;
  slug: string;
  blocks_data: BlockData[];
  template_name?: string;
  is_published: boolean;
  created_at?: string;
  updated_at?: string;
}

export default function PageRenderer({slug}: {slug: string}) {
  const [page, setPage] = useState<PageData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    (async () => {
      // 先尝试获取页面构建器页面（公开、已发布的）
      try {
        const res = await apiClient.get(`/cms/page-builder/pages/slug/${slug}`);
        if (!cancelled && res.success && res.data) {
          setPage(res.data);
          setLoading(false);
          document.title = res.data.title || slug;
          return;
        }
      } catch { /* 不是页面构建器页面 */ }

      // 回退：尝试获取文章
      try {
        const res = await apiClient.get(`/articles/p/${slug}`);
        if (!cancelled && res.success && res.data) {
          setPage({
            id: res.data.id,
            title: res.data.title || slug,
            slug,
            blocks_data: [
              {type: 'article-content', data: {article: res.data}}
            ],
            is_published: true,
          });
          setLoading(false);
          document.title = res.data.title || slug;
          return;
        }
      } catch { /* 不是文章 */ }

      if (!cancelled) {
        setError('页面不存在');
        setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [slug]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Loader2 className="w-8 h-8 animate-spin text-blue-600"/>
      </div>
    );
  }

  if (error || !page) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] text-gray-400">
        <FileQuestion className="w-16 h-16 mb-4"/>
        <p className="text-lg font-medium">页面不存在</p>
        <p className="text-sm mt-1">请检查链接是否正确</p>
      </div>
    );
  }

  return (
    <article className="max-w-4xl mx-auto px-4 py-8">
      {page.blocks_data && page.blocks_data.length > 0 ? (
        <div className="space-y-6">
          {page.blocks_data.map((block, i) => (
            <BlockRenderer key={i} block={block}/>
          ))}
        </div>
      ) : (
        <div className="text-center py-16 text-gray-400">
          <p>此页面暂无内容</p>
        </div>
      )}
    </article>
  );
}

function BlockRenderer({block}: {block: BlockData}) {
  if (!block) return null;

  const styles: React.CSSProperties = block.styles || {};

  switch (block.type) {
    case 'hero-section':
      return (
        <section className="rounded-2xl overflow-hidden" style={styles}>
          <div className="max-w-3xl mx-auto text-center px-6 py-16">
            <h1 className="text-4xl md:text-5xl font-bold mb-4" style={{color: styles.color}}>
              {block.data?.title}
            </h1>
            {block.data?.subtitle && (
              <p className="text-lg md:text-xl opacity-80 mb-6" style={{color: styles.color}}>
                {block.data.subtitle}
              </p>
            )}
            {block.data?.cta_text && (
              <a href={block.data?.cta_link || '#'}
                 className="inline-flex items-center px-6 py-3 bg-blue-600 text-white rounded-xl font-medium hover:bg-blue-700 transition-colors">
                {block.data.cta_text}
              </a>
            )}
          </div>
        </section>
      );

    case 'features-grid':
      return (
        <section className="py-12 px-4" style={styles}>
          {block.data?.title && (
            <h2 className="text-2xl font-bold text-center mb-8 text-gray-900 dark:text-white">
              {block.data.title}
            </h2>
          )}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-4xl mx-auto">
            {(block.data?.features || []).map((f: any, i: number) => (
              <div key={i} className="p-6 rounded-xl bg-white dark:bg-gray-800 border border-gray-100 dark:border-gray-700 shadow-sm">
                <h3 className="font-semibold text-gray-900 dark:text-white mb-2">{f.title}</h3>
                <p className="text-sm text-gray-500 dark:text-gray-400">{f.desc}</p>
              </div>
            ))}
          </div>
        </section>
      );

    case 'testimonials':
      return (
        <section className="py-12 px-4" style={styles}>
          {block.data?.title && (
            <h2 className="text-2xl font-bold text-center mb-8 text-gray-900 dark:text-white">
              {block.data.title}
            </h2>
          )}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-3xl mx-auto">
            {(block.data?.testimonials || []).map((t: any, i: number) => (
              <div key={i} className="p-6 rounded-xl bg-white dark:bg-gray-800 border border-gray-100 dark:border-gray-700 shadow-sm">
                <p className="text-sm text-gray-600 dark:text-gray-300 italic mb-3">"{t.quote}"</p>
                <p className="text-sm font-medium text-gray-900 dark:text-white">{t.name}</p>
                {t.role && <p className="text-xs text-gray-400">{t.role}</p>}
              </div>
            ))}
          </div>
        </section>
      );

    case 'cta-section':
      return (
        <section className="rounded-2xl text-center py-16 px-6" style={styles}>
          <h2 className="text-3xl font-bold mb-3" style={{color: styles.color}}>{block.data?.title}</h2>
          {block.data?.subtitle && (
            <p className="text-lg opacity-80 mb-6" style={{color: styles.color}}>{block.data.subtitle}</p>
          )}
          {block.data?.button_text && (
            <a href={block.data?.button_link || '#'}
               className="inline-flex items-center px-6 py-3 bg-white text-gray-900 rounded-xl font-medium hover:bg-gray-100 transition-colors">
              {block.data.button_text}
            </a>
          )}
        </section>
      );

    case 'pricing-table':
      return (
        <section className="py-12 px-4" style={styles}>
          {block.data?.title && (
            <h2 className="text-2xl font-bold text-center mb-8 text-gray-900 dark:text-white">
              {block.data.title}
            </h2>
          )}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-4xl mx-auto">
            {(block.data?.plans || []).map((p: any, i: number) => (
              <div key={i} className={`p-6 rounded-xl border ${p.highlighted ? 'border-blue-500 ring-2 ring-blue-100 dark:ring-blue-900/30' : 'border-gray-200 dark:border-gray-700'} bg-white dark:bg-gray-800 shadow-sm`}>
                <h3 className="font-semibold text-gray-900 dark:text-white mb-1">{p.name}</h3>
                <p className="text-2xl font-bold text-blue-600 mb-4">{p.price}</p>
                <ul className="space-y-2 mb-6">
                  {(p.features || []).map((f: string, j: number) => (
                    <li key={j} className="text-sm text-gray-600 dark:text-gray-300 flex items-center gap-2">
                      <span className="text-green-500">✓</span>{f}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </section>
      );

    case 'faq-section':
      return (
        <section className="py-12 px-4 max-w-3xl mx-auto" style={styles}>
          {block.data?.title && (
            <h2 className="text-2xl font-bold text-center mb-8 text-gray-900 dark:text-white">
              {block.data.title}
            </h2>
          )}
          <div className="space-y-3">
            {(block.data?.faqs || []).map((faq: any, i: number) => (
              <details key={i} className="p-4 rounded-xl bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700">
                <summary className="font-medium text-gray-900 dark:text-white cursor-pointer">{faq.question}</summary>
                <p className="mt-2 text-sm text-gray-600 dark:text-gray-300">{faq.answer}</p>
              </details>
            ))}
          </div>
        </section>
      );

    case 'contact-form':
      return (
        <section className="py-12 px-4 max-w-lg mx-auto" style={styles}>
          {block.data?.title && (
            <h2 className="text-2xl font-bold text-center mb-2 text-gray-900 dark:text-white">{block.data.title}</h2>
          )}
          {block.data?.subtitle && <p className="text-center text-gray-500 mb-6">{block.data.subtitle}</p>}
          <form className="space-y-4" onSubmit={e => e.preventDefault()}>
            {(block.data?.fields || ['name', 'email', 'message']).map((f: string) => (
              <div key={f}>
                {f === 'message' ? (
                  <textarea placeholder="您的消息" rows={4}
                    className="w-full px-4 py-3 border border-gray-200 dark:border-gray-700 rounded-xl bg-white dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white"/>
                ) : (
                  <input type={f === 'email' ? 'email' : 'text'} placeholder={f === 'name' ? '您的姓名' : '您的邮箱'}
                    className="w-full px-4 py-3 border border-gray-200 dark:border-gray-700 rounded-xl bg-white dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white"/>
                )}
              </div>
            ))}
            <button type="submit" className="w-full px-6 py-3 bg-blue-600 text-white rounded-xl font-medium hover:bg-blue-700">发送</button>
          </form>
        </section>
      );

    case 'article-content':
      // 文章内容回退显示
      const article = block.data?.article;
      if (!article) return null;
      return (
        <div className="prose prose-lg dark:prose-invert max-w-none">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-4">{article.title}</h1>
          {article.excerpt && <p className="text-gray-500 mb-6">{article.excerpt}</p>}
          {article.content && (
            <div dangerouslySetInnerHTML={{__html: article.content}} className="leading-relaxed"/>
          )}
        </div>
      );

    case 'team-members':
      return (
        <section className="py-12 px-4" style={styles}>
          {block.data?.title && <h2 className="text-2xl font-bold text-center mb-8">{block.data.title}</h2>}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-3xl mx-auto">
            {(block.data?.members || []).map((m: any, i: number) => (
              <div key={i} className="text-center p-4">
                <div className="w-20 h-20 mx-auto mb-3 rounded-full bg-gradient-to-br from-blue-400 to-purple-500"/>
                <p className="font-semibold">{m.name}</p>
                <p className="text-sm text-gray-500">{m.role}</p>
              </div>
            ))}
          </div>
        </section>
      );

    default:
      return (
        <div className="p-4 border border-gray-200 dark:border-gray-700 rounded-xl bg-white dark:bg-gray-800" style={styles}>
          {block.data?.title && <h3 className="font-semibold mb-2">{block.data.title}</h3>}
          {block.data?.content && <p className="text-sm text-gray-600">{block.data.content}</p>}
          {block.children?.map((child, i) => <BlockRenderer key={i} block={child}/>)}
        </div>
      );
  }
}
