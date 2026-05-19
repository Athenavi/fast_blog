'use client';

import React, {useEffect, useState} from 'react';
import {ArticleService} from '@/lib/api';
import type {Article} from '@/lib/api/base-types';

const ArticleList: React.FC = () => {
  const [articles, setArticles] = useState<Article[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    ArticleService.getArticles({page: 1, per_page: 20}).then(res => {
      if (res.success && res.data) {
        setArticles(res.data.data || []);
      }
    }).finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="text-center py-8"><div className="animate-spin w-8 h-8 border-2 border-blue-600 border-t-transparent rounded-full mx-auto" /></div>;

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      {articles.map(article => (
        <a key={article.id} href={`/articles/${article.slug}`} className="block p-6 bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 hover:shadow-lg transition-all">
          <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-2">{article.title}</h3>
          <p className="text-sm text-gray-600 dark:text-gray-400 line-clamp-2">{article.excerpt || article.summary}</p>
          <div className="mt-4 flex items-center gap-4 text-xs text-gray-500">
            <span>{new Date(article.created_at).toLocaleDateString('zh-CN')}</span>
            <span>{article.views} 次浏览</span>
          </div>
        </a>
      ))}
    </div>
  );
};

export default ArticleList;
