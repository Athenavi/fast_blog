'use client';

import React, {useEffect, useState} from 'react';
import {apiClient} from '@/lib/api/base-client';
import type {Article} from '@/lib/api/base-types';

interface Props { slug?: string; }

const ArticleDetail: React.FC<Props> = ({slug: propSlug}) => {
  const [article, setArticle] = useState<Article | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    // 获取 slug：优先使用 prop，其次从 URL 获取
    const slug = propSlug || (typeof window !== 'undefined' ? new URLSearchParams(window.location.search).get('slug') : '') || '';

    console.log('[ArticleDetail] Component mounted, slug:', slug);

    if (!slug) { 
      console.log('[ArticleDetail] No slug available, showing error');
      setError('缺少文章参数');
      setLoading(false);
      return; 
    }

    console.log('[ArticleDetail] Loading article with slug:', slug);
    (async () => {
      try {
        const apiUrl = `/articles/p/${slug}`;
        console.log('[ArticleDetail] Making API request to:', apiUrl);
        const res = await apiClient.get(apiUrl);
        console.log('[ArticleDetail] API response:', res);
        if (res.success && res.data) {
          setArticle(res.data.article || res.data as any);
        } else {
          console.error('[ArticleDetail] API returned error:', res.error);
          setError(res.error || '文章不存在');
        }
      } catch (err) {
        console.error('[ArticleDetail] Error loading article:', err);
        setError('加载失败，请稍后重试');
      } finally {
        setLoading(false);
      }
    })();
  }, [propSlug]);

  if (loading) return <div className="min-h-[50vh] flex items-center justify-center"><div className="animate-spin w-8 h-8 border-2 border-blue-600 border-t-transparent rounded-full"/></div>;
  if (error || !article) return (
    <div className="min-h-[50vh] flex items-center justify-center">
      <div className="text-center">
        <h1 className="text-2xl font-bold text-gray-800 dark:text-gray-200 mb-2">{error || '文章不存在'}</h1>
        <a href="/articles" className="text-blue-600 hover:underline">返回文章列表</a>
      </div>
    </div>
  );

  return (
    <div className="prose prose-lg dark:prose-invert max-w-none">
      <div dangerouslySetInnerHTML={{__html: article.content || '<p>暂无内容</p>'}} />
    </div>
  );
};

export default ArticleDetail;
