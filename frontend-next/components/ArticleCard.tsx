'use client';

import React from 'react';
import {Article} from '@/lib/api';
import {BookOpen, Calendar, Clock, Eye, User} from 'lucide-react';

interface ArticleCardProps {
  article: Article;
  categoryName: string;
  authorName: string;
  showActions?: boolean;
  variant?: 'default' | 'modern';
}

const ArticleCard: React.FC<ArticleCardProps> = ({
  article,
  categoryName,
  authorName,
  showActions = true,
  variant = 'modern'
}) => {
  if (variant === 'modern') {
    return (
      <article className="group relative bg-white dark:bg-gray-800 rounded-2xl shadow-lg hover:shadow-2xl transition-all duration-500 overflow-hidden border border-gray-100 dark:border-gray-700 hover:border-blue-200 dark:hover:border-blue-800">
        {/* 图片区域 */}
        <div className="relative h-56 overflow-hidden">
          <img
            src={article.cover_image || '/images/default-article.jpg'}
            alt={article.title}
            className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-700"
          />
          <div className="absolute inset-0 bg-gradient-to-t from-black/30 to-transparent" />

          {/* 分类标签 */}
          <div className="absolute top-4 left-4">
            <span className="inline-block px-3 py-1.5 bg-gradient-to-r from-blue-500 to-blue-600 text-white text-xs font-semibold rounded-full shadow-md">
              {categoryName}
            </span>
          </div>
        </div>

        {/* 内容区域 */}
        <div className="p-6">
          {/* 元信息 */}
          <div className="flex items-center gap-4 text-sm text-gray-500 dark:text-gray-400 mb-4">
            <div className="flex items-center gap-1.5">
              <User className="w-4 h-4" />
              <span>{authorName}</span>
            </div>
            <div className="flex items-center gap-1.5">
              <Calendar className="w-4 h-4" />
              <span>{new Date(article.created_at || '').toLocaleDateString('zh-CN')}</span>
            </div>
          </div>

          {/* 标题 */}
          <h3 className="text-xl font-bold text-gray-800 dark:text-gray-200 mb-3 group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors line-clamp-2">
            {article.title}
          </h3>

          {/* 摘要 */}
          <p className="text-gray-600 dark:text-gray-400 mb-6 line-clamp-3 leading-relaxed">
            {article.summary || article.content?.substring(0, 150) || '暂无摘要'}
          </p>

          {/* 底部信息 */}
          <div className="flex items-center justify-between pt-4 border-t border-gray-100 dark:border-gray-700">
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-1.5 text-sm text-gray-500 dark:text-gray-400">
                <Clock className="w-4 h-4" />
                <span>{article.summary?.length ? Math.ceil(article.summary.length / 1000) + '分钟阅读' : '5分钟阅读'}</span>
              </div>
              <div className="flex items-center gap-1.5 text-sm text-gray-500 dark:text-gray-400">
                <Eye className="w-4 h-4" />
                <span>{article.views_count || article.views || 0}</span>
              </div>
            </div>

            {showActions && (
              <a
                href={`/blog/${article.slug}`}
                className="inline-flex items-center text-blue-600 dark:text-blue-400 font-medium hover:text-blue-700 dark:hover:text-blue-300 transition-colors"
              >
                阅读全文
                <BookOpen className="ml-2 w-4 h-4" />
              </a>
            )}
          </div>
        </div>

        {/* 悬停效果 */}
        <div className="absolute inset-0 bg-gradient-to-t from-blue-500/5 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none" />
      </article>
    );
  }

  // 默认样式（保持兼容性）
  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl shadow-md overflow-hidden">
      {/* 原有实现 */}
    </div>
  );
};

export default ArticleCard;