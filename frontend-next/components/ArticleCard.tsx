'use client';

import React from 'react';
import {Article} from '@/lib/api';
import {BookOpen, Calendar, Clock, Eye, User} from 'lucide-react';

interface ArticleCardProps {
  article: Article & { is_sticky?: boolean; sticky_until?: string };
  categoryName: string;
  authorName: string;
  showActions?: boolean;
    variant?: 'default' | 'modern' | 'simple';
}

const ArticleCard: React.FC<ArticleCardProps> = ({
  article,
  categoryName,
  authorName,
  showActions = true,
                                                     variant = 'simple'
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

            {/* 分类标签 - 仅在分类名称存在且不为空时显示 */}
            {categoryName && (
                <div className="absolute top-4 left-4">
              <span
                  className="inline-block px-3 py-1.5 bg-gradient-to-r from-blue-500 to-blue-600 text-white text-xs font-semibold rounded-full shadow-md">
                {categoryName}
              </span>
                </div>
            )}
            
            {/* 粘性文章标识 */}
            {article.is_sticky && (
                <div className="absolute top-4 right-4">
                    <span className="inline-flex items-center gap-1 px-3 py-1.5 bg-gradient-to-r from-red-500 to-red-600 text-white text-xs font-semibold rounded-full shadow-md">
                        <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                            <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                        </svg>
                        置顶
                    </span>
                </div>
            )}
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
                  <span>{article.summary?.length ? Math.ceil(article.summary.length / 1000) + '分钟阅读' : '5 分钟阅读'}</span>
              </div>
              <div className="flex items-center gap-1.5 text-sm text-gray-500 dark:text-gray-400">
                <Eye className="w-4 h-4" />
                <span>{article.views_count || article.views || 0}</span>
              </div>
            </div>

            {showActions && (
              <a
                href={`/blog?slug=${article.slug}`}
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

    // 默认简单样式（用于新首页）
  return (
      <div style={{
          background: '#fff',
          borderRadius: '12px',
          overflow: 'hidden',
          boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
          transition: 'transform 0.2s, box-shadow 0.2s',
          cursor: 'pointer',
      }}
           onMouseEnter={(e) => {
               e.currentTarget.style.transform = 'translateY(-4px)';
               e.currentTarget.style.boxShadow = '0 8px 16px rgba(0,0,0,0.12)';
           }}
           onMouseLeave={(e) => {
               e.currentTarget.style.transform = 'translateY(0)';
               e.currentTarget.style.boxShadow = '0 2px 8px rgba(0,0,0,0.08)';
           }}
      >
          {article.cover_image ? (
              <img
                  src={article.cover_image}
                  alt={article.title}
                  style={{
                      width: '100%',
                      height: '200px',
                      objectFit: 'cover',
                      background: '#f3f4f6',
                  }}
                  loading="lazy"
              />
          ) : (
              <div style={{
                  width: '100%',
                  height: '200px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  background: '#f3f4f6',
                  color: '#999',
              }}>
                  暂无封面
              </div>
          )}
          <div style={{padding: '1.5rem'}}>
              {categoryName && (
        <span style={{
            display: 'inline-block',
            padding: '0.25rem 0.75rem',
            background: '#667eea',
            color: '#fff',
            borderRadius: '9999px',
            fontSize: '0.75rem',
            fontWeight: '500',
            marginBottom: '0.75rem',
        }}>
          {categoryName}
        </span>
              )}
              
              {/* 粘性文章标识 */}
              {article.is_sticky && (
                  <span style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '0.25rem',
                      padding: '0.25rem 0.75rem',
                      background: '#ef4444',
                      color: '#fff',
                      borderRadius: '9999px',
                      fontSize: '0.75rem',
                      fontWeight: '500',
                      marginBottom: '0.75rem',
                      marginLeft: '0.5rem',
                  }}>
                      <svg width="12" height="12" fill="currentColor" viewBox="0 0 20 20">
                          <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                      </svg>
                      置顶
                  </span>
              )}
              <h3 style={{
                  fontSize: '1.25rem',
                  fontWeight: '600',
                  marginBottom: '0.75rem',
                  color: '#1a1a1a',
                  lineHeight: '1.4',
              }}>
                  {article.title}
              </h3>
              <p style={{
                  fontSize: '0.95rem',
                  color: '#666',
                  marginBottom: '1rem',
                  lineHeight: '1.6',
                  display: '-webkit-box',
                  WebkitLineClamp: 2,
                  WebkitBoxOrient: 'vertical',
                  overflow: 'hidden',
              }}>
                  {article.excerpt || article.summary || '暂无摘要'}
              </p>
              <div style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  fontSize: '0.875rem',
                  color: '#999',
              }}>
                  <span>{new Date(article.created_at || '').toLocaleDateString('zh-CN')}</span>
                  <span>{article.views || article.views_count || 0} 阅读</span>
              </div>
          </div>
    </div>
  );
};

export default ArticleCard;