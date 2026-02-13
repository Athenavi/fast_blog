'use client';

import React from 'react';
import {Article} from '@/lib/api';
import ArticleCard from '@/components/ArticleCard';
import Pagination from '@/components/Pagination';
import {ArrowRight, Calendar, ChevronRight, Clock, Filter, Mail, Sparkles, User} from 'lucide-react';

// 加载状态组件
export const LoadingState = ({ type = 'articles' }: { type?: 'config' | 'articles' }) => (
  <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800">
    <div className="text-center">
      <div className="relative">
        <div className="w-16 h-16 border-4 border-blue-500/30 border-t-blue-500 rounded-full animate-spin mx-auto"></div>
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="w-8 h-8 bg-blue-500 rounded-full animate-ping"></div>
        </div>
      </div>
      <p className="mt-6 text-gray-600 dark:text-gray-400 font-medium">
        {type === 'config' ? '正在加载配置...' : '正在加载内容...'}
      </p>
      <p className="mt-2 text-sm text-gray-500 dark:text-gray-500">
        精彩内容马上呈现
      </p>
    </div>
  </div>
);

// 错误状态组件
export const ErrorState = ({ message, retryAction }: { message: string; retryAction: () => void }) => (
  <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800">
    <div className="max-w-md text-center px-4">
      <div className="w-20 h-20 mx-auto mb-6 rounded-full bg-red-100 dark:bg-red-900/30 flex items-center justify-center">
        <div className="text-red-500 text-2xl">⚠️</div>
      </div>
      <h3 className="text-xl font-semibold text-gray-800 dark:text-gray-200 mb-2">
        加载失败
      </h3>
      <p className="text-gray-600 dark:text-gray-400 mb-6">
        {message || '无法加载页面内容'}
      </p>
      <button
        onClick={retryAction}
        className="inline-flex items-center justify-center px-6 py-3 bg-gradient-to-r from-blue-500 to-blue-600 text-white font-medium rounded-lg hover:from-blue-600 hover:to-blue-700 transition-all duration-300 shadow-lg hover:shadow-xl"
      >
        <span>重新加载</span>
        <ArrowRight className="ml-2 w-4 h-4" />
      </button>
    </div>
  </div>
);

// 英雄区域组件
interface HeroSectionProps {
  config: {
    title: string;
    subtitle: string;
    background_image: string;
    cta_button_text: string;
    cta_button_link: string;
    cta_button_target: string;
  };
  isLoading: boolean;
}

export const HeroSection: React.FC<HeroSectionProps> = ({ config, isLoading }) => {
  if (isLoading) {
    return (
      <div className="relative h-[85vh] overflow-hidden bg-gradient-to-br from-gray-200 to-gray-300 dark:from-gray-800 dark:to-gray-900 animate-pulse">
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="w-12 h-12 border-4 border-white/30 border-t-white rounded-full animate-spin"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="relative h-[85vh] overflow-hidden">
      {/* 渐变背景 */}
      <div className="absolute inset-0 bg-gradient-to-br from-blue-500/10 via-purple-500/10 to-pink-500/10" />

      {/* 网格背景 */}
      <div className="absolute inset-0 bg-[linear-gradient(to_right,#f0f0f0_1px,transparent_1px),linear-gradient(to_bottom,#f0f0f0_1px,transparent_1px)] bg-[size:4rem_4rem] opacity-5 dark:opacity-10" />

      {/* 动态背景图 */}
      <div
        className="absolute inset-0 bg-cover bg-center transition-all duration-1000"
        style={{ backgroundImage: `url('${config.background_image}')` }}
      >
        <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-black/30 to-transparent" />
        <div className="absolute inset-0 bg-gradient-to-r from-black/30 to-transparent" />
      </div>

      {/* 漂浮动画元素 */}
      <div className="absolute top-1/4 left-1/4 w-72 h-72 bg-blue-500/10 rounded-full blur-3xl animate-float" />
      <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-purple-500/10 rounded-full blur-3xl animate-float-delayed" />

      {/* 内容区域 */}
      <div className="relative z-10 h-full flex items-center">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8">
          <div className="max-w-3xl">
            {/* 标签 */}
            <div className="inline-flex items-center px-4 py-2 rounded-full bg-white/10 backdrop-blur-sm border border-white/20 mb-8">
              <Sparkles className="w-4 h-4 text-yellow-300 mr-2" />
              <span className="text-sm font-medium text-white/90">探索最新内容</span>
            </div>

            {/* 标题 */}
            <h1 className="text-5xl md:text-7xl font-bold text-white mb-6 leading-tight">
              {config.title.split(' ').map((word, idx) => (
                <span key={idx} className="inline-block mr-2 hover:scale-105 transition-transform duration-300">
                  {word}
                </span>
              ))}
            </h1>

            {/* 副标题 */}
            <p className="text-xl md:text-2xl text-white/90 mb-10 max-w-2xl leading-relaxed">
              {config.subtitle}
            </p>

            {/* 行动按钮组 */}
            <div className="flex flex-col sm:flex-row gap-4">
              <a
                href={config.cta_button_link}
                target={config.cta_button_target === '_blank' ? '_blank' : undefined}
                rel={config.cta_button_target === '_blank' ? 'noopener noreferrer' : undefined}
                className="group inline-flex items-center justify-center px-8 py-4 bg-gradient-to-r from-blue-500 to-blue-600 text-white font-semibold rounded-xl hover:from-blue-600 hover:to-blue-700 transition-all duration-300 shadow-lg hover:shadow-xl hover:scale-105"
              >
                <span>{config.cta_button_text}</span>
                <ArrowRight className="ml-2 w-5 h-5 group-hover:translate-x-1 transition-transform" />
              </a>

              <button className="group inline-flex items-center justify-center px-8 py-4 bg-white/10 backdrop-blur-sm text-white font-semibold rounded-xl border border-white/30 hover:bg-white/20 transition-all duration-300">
                <span>查看全部</span>
                <ChevronRight className="ml-2 w-5 h-5 group-hover:translate-x-1 transition-transform" />
              </button>
            </div>

            {/* 统计信息 */}
            <div className="flex flex-wrap gap-8 mt-12 pt-8 border-t border-white/20">
              <div className="text-center">
                <div className="text-3xl font-bold text-white mb-1">100+</div>
                <div className="text-sm text-white/70">精品文章</div>
              </div>
              <div className="text-center">
                <div className="text-3xl font-bold text-white mb-1">50+</div>
                <div className="text-sm text-white/70">专业作者</div>
              </div>
              <div className="text-center">
                <div className="text-3xl font-bold text-white mb-1">10K+</div>
                <div className="text-sm text-white/70">阅读用户</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* 滚动指示器 */}
      <div className="absolute bottom-8 left-1/2 transform -translate-x-1/2 animate-bounce">
        <div className="w-6 h-10 border-2 border-white/50 rounded-full flex justify-center">
          <div className="w-1 h-3 bg-white rounded-full mt-2 animate-pulse"></div>
        </div>
      </div>
    </div>
  );
};

// 特色文章区域组件
interface FeaturedArticlesSectionProps {
  title: string;
  articles: Article[];
  isLoading: boolean;
  emptyState: {
    title: string;
    subtitle: string;
  };
  defaultMessages: {
    no_category: string;
    unknown_author: string;
    no_summary: string;
  };
}

export const FeaturedArticlesSection: React.FC<FeaturedArticlesSectionProps> = ({
  title,
  articles,
  isLoading,
  emptyState,
  defaultMessages
}) => {
  if (isLoading) {
    return (
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {[1, 2, 3].map((i) => (
          <div key={i} className="bg-white dark:bg-gray-800 rounded-2xl shadow-xl overflow-hidden animate-pulse">
            <div className="h-64 bg-gray-200 dark:bg-gray-700" />
            <div className="p-6">
              <div className="h-6 bg-gray-200 dark:bg-gray-700 rounded mb-4" />
              <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded mb-2" />
              <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-3/4 mb-6" />
              <div className="flex items-center justify-between">
                <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-1/3" />
                <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-1/4" />
              </div>
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (articles.length === 0) {
    return (
      <div className="bg-gradient-to-br from-gray-50 to-white dark:from-gray-800 dark:to-gray-900 rounded-3xl p-12 text-center shadow-lg">
        <div className="w-20 h-20 mx-auto mb-6 rounded-full bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center">
          <Sparkles className="w-10 h-10 text-blue-500" />
        </div>
        <h3 className="text-2xl font-bold text-gray-800 dark:text-gray-200 mb-3">
          {emptyState.title}
        </h3>
        <p className="text-gray-600 dark:text-gray-400 max-w-md mx-auto">
          {emptyState.subtitle}
        </p>
      </div>
    );
  }

  return (
    <div className="mb-16">
      {/* 标题区域 */}
      <div className="flex items-center justify-between mb-10">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-xl bg-gradient-to-r from-blue-500 to-blue-600">
            <Sparkles className="w-6 h-6 text-white" />
          </div>
          <h2 className="text-3xl font-bold text-gray-800 dark:text-gray-200">
            {title}
          </h2>
        </div>
        <a
          href="/articles"
          className="group inline-flex items-center text-blue-600 dark:text-blue-400 font-medium hover:text-blue-700 dark:hover:text-blue-300 transition-colors"
        >
          查看全部
          <ChevronRight className="ml-1 w-4 h-4 group-hover:translate-x-1 transition-transform" />
        </a>
      </div>

      {/* 文章网格 */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {articles.map((article, index) => (
          <div
            key={article.id}
            className={`group relative overflow-hidden rounded-2xl shadow-xl hover:shadow-2xl transition-all duration-500 ${
              index === 0 ? 'lg:col-span-2 lg:row-span-2' : ''
            }`}
          >
            {/* 图片 */}
            <div className={`relative overflow-hidden ${
              index === 0 ? 'h-96' : 'h-64'
            }`}>
              <img
                src={article.cover_image || '/images/default-article.jpg'}
                alt={article.title}
                className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-700"
              />
              <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-black/40 to-transparent" />

              {/* 标签 */}
              <div className="absolute top-4 left-4">
                <span className="inline-block px-3 py-1 bg-gradient-to-r from-blue-500 to-blue-600 text-white text-xs font-medium rounded-full">
                  {article.category_name || defaultMessages.no_category}
                </span>
              </div>
            </div>

            {/* 内容 */}
            <div className="absolute bottom-0 left-0 right-0 p-6 text-white">
              <div className="flex items-center gap-3 mb-3">
                <div className="flex items-center gap-2">
                  <User className="w-4 h-4" />
                  <span className="text-sm opacity-90">
                    {article.author?.username || defaultMessages.unknown_author}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <Calendar className="w-4 h-4" />
                  <span className="text-sm opacity-90">
                    {new Date(article.created_at || '').toLocaleDateString('zh-CN')}
                  </span>
                </div>
              </div>

              <h3 className={`font-bold mb-3 ${
                index === 0 ? 'text-2xl' : 'text-xl'
              } group-hover:text-blue-300 transition-colors`}>
                {article.title}
              </h3>

              <p className="mb-4 opacity-90 line-clamp-2">
                {article.summary || article.content?.substring(0, 120) || defaultMessages.no_summary}
              </p>

              <div className="flex items-center justify-between">
                <span className="text-sm opacity-80">
                  <Clock className="w-4 h-4 inline mr-1" />
                  {article.summary?.length ? Math.ceil(article.summary.length / 1000) + '分钟阅读' : '5分钟阅读'}
                </span>
                <a
                  href={`/articles/${article.slug}`}
                  className="inline-flex items-center text-sm font-medium hover:text-blue-300 transition-colors"
                >
                  阅读全文
                  <ChevronRight className="ml-1 w-4 h-4" />
                </a>
              </div>
            </div>

            {/* 悬停效果 */}
            <div className="absolute inset-0 bg-gradient-to-t from-blue-500/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
          </div>
        ))}
      </div>
    </div>
  );
};

// 主要内容区域组件
interface MainContentSectionProps {
  title: string;
  filterButtons: Array<{ text: string; value: string }>;
  activeFilter: string;
  onFilterChange: (value: string) => void;
  articles: Article[];
  isLoading: boolean;
  emptyState: {
    title: string;
    subtitle: string;
  };
  defaultMessages: {
    no_category: string;
    unknown_author: string;
    no_summary: string;
  };
  pagination: {
    current_page: number;
    total_pages: number;
    has_prev: boolean;
    has_next: boolean;
  };
  onPageChange: (page: number) => void;
}

export const MainContentSection: React.FC<MainContentSectionProps> = ({
  title,
  filterButtons,
  activeFilter,
  onFilterChange,
  articles,
  isLoading,
  emptyState,
  defaultMessages,
  pagination,
  onPageChange
}) => {
  // 过滤掉特色文章
  const featuredIds = new Set(articles.slice(0, 3).map(article => article.id));
  const mainArticles = articles.filter(article => !featuredIds.has(article.id));

  return (
    <div className="container mx-auto px-4 sm:px-6 lg:px-8 py-16">
      {/* 标题和筛选器 */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-12 gap-6">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <div className="p-2 rounded-xl bg-gradient-to-r from-green-500 to-green-600">
              <Filter className="w-6 h-6 text-white" />
            </div>
            <h2 className="text-3xl font-bold text-gray-800 dark:text-gray-200">
              {title}
            </h2>
          </div>
          <p className="text-gray-600 dark:text-gray-400">
            发现更多精彩内容，涵盖各种主题
          </p>
        </div>

        {/* 筛选器 */}
        <div className="flex flex-wrap gap-2">
          {filterButtons.map((button) => (
            <button
              key={button.value}
              onClick={() => onFilterChange(button.value)}
              className={`px-5 py-2.5 rounded-xl font-medium transition-all duration-300 ${
                activeFilter === button.value
                  ? 'bg-gradient-to-r from-green-500 to-green-600 text-white shadow-lg'
                  : 'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700'
              }`}
            >
              {button.text}
            </button>
          ))}
        </div>
      </div>

      {/* 文章网格 */}
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div key={i} className="bg-white dark:bg-gray-800 rounded-2xl shadow-lg overflow-hidden animate-pulse">
              <div className="h-48 bg-gray-200 dark:bg-gray-700" />
              <div className="p-6">
                <div className="h-5 bg-gray-200 dark:bg-gray-700 rounded mb-4" />
                <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded mb-2" />
                <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-3/4 mb-6" />
                <div className="flex items-center justify-between">
                  <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-1/3" />
                  <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-1/4" />
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : mainArticles.length > 0 ? (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            {mainArticles.map((article) => (
              <ArticleCard
                key={article.id}
                article={article}
                categoryName={article.category_name || defaultMessages.no_category}
                authorName={article.author?.username || defaultMessages.unknown_author}
                showActions={true}
                variant="modern"
              />
            ))}
          </div>

          {/* 分页 */}
          {pagination.total_pages > 1 && (
            <div className="mt-16">
              <Pagination
                currentPage={pagination.current_page}
                totalPages={pagination.total_pages}
                hasNext={pagination.has_next}
                hasPrev={pagination.has_prev}
                onPageChange={onPageChange}
                variant="modern"
              />
            </div>
          )}
        </>
      ) : (
        <div className="bg-gradient-to-br from-gray-50 to-white dark:from-gray-800 dark:to-gray-900 rounded-3xl p-12 text-center shadow-lg">
          <div className="w-20 h-20 mx-auto mb-6 rounded-full bg-green-100 dark:bg-green-900/30 flex items-center justify-center">
            <Filter className="w-10 h-10 text-green-500" />
          </div>
          <h3 className="text-2xl font-bold text-gray-800 dark:text-gray-200 mb-3">
            {emptyState.title}
          </h3>
          <p className="text-gray-600 dark:text-gray-400 max-w-md mx-auto mb-8">
            {emptyState.subtitle}
          </p>
          <button
            onClick={() => onFilterChange('all')}
            className="inline-flex items-center justify-center px-6 py-3 bg-gradient-to-r from-green-500 to-green-600 text-white font-medium rounded-lg hover:from-green-600 hover:to-green-700 transition-all duration-300"
          >
            重置筛选
          </button>
        </div>
      )}
    </div>
  );
};

// 新闻订阅区域组件
interface NewsletterSectionProps {
  title: string;
  subtitle: string;
  placeholder: string;
  buttonText: string;
  onSubmit: (e: React.FormEvent) => void;
}

export const NewsletterSection: React.FC<NewsletterSectionProps> = ({
  title,
  subtitle,
  placeholder,
  buttonText,
  onSubmit
}) => {
  return (
    <div className="relative overflow-hidden py-20">
      {/* 背景装饰 */}
      <div className="absolute inset-0 bg-gradient-to-r from-blue-500/10 via-purple-500/10 to-pink-500/10" />
      <div className="absolute top-0 left-0 w-64 h-64 bg-blue-500/5 rounded-full -translate-x-1/2 -translate-y-1/2" />
      <div className="absolute bottom-0 right-0 w-96 h-96 bg-purple-500/5 rounded-full translate-x-1/3 translate-y-1/3" />

      <div className="relative container mx-auto px-4 sm:px-6 lg:px-8">
        <div className="max-w-3xl mx-auto">
          <div className="bg-gradient-to-br from-white to-gray-50 dark:from-gray-800 dark:to-gray-900 rounded-3xl p-8 md:p-12 shadow-2xl border border-gray-100 dark:border-gray-700">
            <div className="text-center">
              {/* 图标 */}
              <div className="w-20 h-20 mx-auto mb-6 rounded-2xl bg-gradient-to-r from-blue-500 to-blue-600 flex items-center justify-center shadow-lg">
                <Mail className="w-10 h-10 text-white" />
              </div>

              {/* 标题 */}
              <h2 className="text-3xl md:text-4xl font-bold text-gray-800 dark:text-gray-200 mb-4">
                {title}
              </h2>

              {/* 副标题 */}
              <p className="text-gray-600 dark:text-gray-400 text-lg mb-10 max-w-2xl mx-auto">
                {subtitle}
              </p>

              {/* 订阅表单 */}
              <form onSubmit={onSubmit} className="max-w-md mx-auto">
                <div className="flex flex-col sm:flex-row gap-3">
                  <div className="flex-grow">
                    <input
                      type="email"
                      name="email"
                      placeholder={placeholder}
                      required
                      className="w-full px-6 py-4 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                    />
                  </div>
                  <button
                    type="submit"
                    className="px-8 py-4 bg-gradient-to-r from-blue-500 to-blue-600 text-white font-semibold rounded-xl hover:from-blue-600 hover:to-blue-700 transition-all duration-300 shadow-lg hover:shadow-xl whitespace-nowrap"
                  >
                    {buttonText}
                  </button>
                </div>

                <p className="text-sm text-gray-500 dark:text-gray-400 mt-4">
                  订阅即表示您同意我们的
                  <a href="/privacy" className="text-blue-500 hover:text-blue-600 dark:text-blue-400 dark:hover:text-blue-300 ml-1">
                    隐私政策
                  </a>
                </p>
              </form>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};