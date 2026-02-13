'use client';

import React, {useEffect, useState} from 'react';
import {motion} from 'framer-motion';
import {ArrowRight, Award, BookOpen, Calendar, Clock, Eye, TrendingUp, Zap} from 'lucide-react';
import {Article, Category} from '@/lib/api';
import ArticleCard from '@/components/ArticleCard';
import Pagination from '@/components/Pagination';

// 类型定义
interface HomePageData {
  featuredArticles: Article[];
  recentArticles: Article[];
  popularArticles: Article[];
  categories: Category[];
  stats: {
    totalArticles: number;
    totalUsers: number;
    totalViews: number;
  };
}

interface HomePageConfig {
  hero: {
    title: string;
    subtitle: string;
    backgroundImage: string;
    ctaText: string;
    ctaLink: string;
  };
  sections: {
    featuredTitle: string;
    recentTitle: string;
    popularTitle: string;
    categoriesTitle: string;
  };
}

// 加载状态组件
const LoadingSkeleton = () => (
  <div className="animate-pulse">
    <div className="h-96 bg-gradient-to-r from-gray-200 to-gray-300 dark:from-gray-700 dark:to-gray-800 rounded-2xl mb-12" />
    <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-16">
      {[1, 2, 3].map(i => (
        <div key={i} className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-lg">
          <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded mb-4" />
          <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded mb-2" />
          <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-3/4" />
        </div>
      ))}
    </div>
  </div>
);

// 错误状态组件
const ErrorDisplay = ({ message, retryAction }: { message: string; retryAction: () => void }) => (
  <div className="min-h-screen flex items-center justify-center">
    <div className="text-center">
      <div className="text-6xl mb-4">⚠️</div>
      <h2 className="text-2xl font-bold text-gray-800 dark:text-gray-200 mb-2">加载失败</h2>
      <p className="text-gray-600 dark:text-gray-400 mb-6">{message}</p>
      <button
        onClick={retryAction}
        className="px-6 py-3 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
      >
        重新加载
      </button>
    </div>
  </div>
);

// 英雄区域组件
const HeroSection = ({ config }: { config: HomePageConfig['hero'] }) => (
  <section className="relative min-h-screen flex items-center overflow-hidden">
    {/* 背景渐变 */}
    <div className="absolute inset-0 bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50 dark:from-gray-900 dark:via-gray-800 dark:to-gray-900" />
    
    {/* 动态背景元素 */}
    <div className="absolute inset-0">
      <div className="absolute top-20 left-10 w-72 h-72 bg-blue-500/10 rounded-full blur-3xl animate-pulse" />
      <div className="absolute bottom-20 right-10 w-96 h-96 bg-purple-500/10 rounded-full blur-3xl animate-pulse delay-1000" />
      <div className="absolute top-1/2 left-1/4 w-64 h-64 bg-indigo-500/10 rounded-full blur-3xl animate-pulse delay-500" />
    </div>

    {/* 内容区域 */}
    <div className="relative z-10 container mx-auto px-4 sm:px-6 lg:px-8 py-20">
      <motion.div 
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8 }}
        className="max-w-4xl mx-auto text-center"
      >
        {/* 主标题 */}
        <motion.h1 
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="text-5xl md:text-7xl font-bold text-gray-900 dark:text-white mb-6 leading-tight"
        >
          {config.title.split(' ').map((word, index) => (
            <span 
              key={index} 
              className="inline-block hover:text-blue-600 dark:hover:text-blue-400 transition-colors duration-300"
            >
              {word}{' '}
            </span>
          ))}
        </motion.h1>

        {/* 副标题 */}
        <motion.p 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="text-xl md:text-2xl text-gray-600 dark:text-gray-300 mb-10 max-w-3xl mx-auto leading-relaxed"
        >
          {config.subtitle}
        </motion.p>
      </motion.div>
    </div>

    {/* 滚动指示器 */}
    <motion.div 
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ delay: 1 }}
      className="absolute bottom-8 left-1/2 transform -translate-x-1/2 animate-bounce"
    >
      <div className="w-6 h-10 border-2 border-gray-400 dark:border-gray-500 rounded-full flex justify-center">
        <div className="w-1 h-3 bg-gray-400 dark:bg-gray-500 rounded-full mt-2 animate-pulse"></div>
      </div>
    </motion.div>
  </section>
);

// 特色文章区域
const FeaturedArticlesSection = ({ 
  articles, 
  title 
}: { 
  articles: Article[]; 
  title: string;
}) => (
  <section className="py-20 bg-gradient-to-b from-white to-gray-50 dark:from-gray-900 dark:to-gray-800">
    <div className="container mx-auto px-4 sm:px-6 lg:px-8">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {articles.slice(0, 4).map((article, index) => (
          <motion.div
            key={article.id}
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.1 }}
            viewport={{ once: true }}
            className={`group relative overflow-hidden rounded-2xl shadow-xl hover:shadow-2xl transition-all duration-500 ${
              index === 0 ? 'lg:row-span-2' : ''
            }`}
          >
            <div className={`relative overflow-hidden ${index === 0 ? 'h-96' : 'h-72'}`}>
              <img
                src={article.cover_image || '/images/default-article.jpg'}
                alt={article.title}
                className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-700"
              />
              <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-black/40 to-transparent" />
              
              {/* 角落标签 */}
              <div className="absolute top-4 left-4">
                <span className="inline-block px-3 py-1 bg-gradient-to-r from-yellow-500 to-orange-500 text-white text-xs font-medium rounded-full">
                  精选
                </span>
              </div>
            </div>

            <div className="absolute bottom-0 left-0 right-0 p-6 text-white">
              <div className="flex items-center gap-4 mb-3 text-sm opacity-90">
                <div className="flex items-center gap-1">
                  <Calendar className="w-4 h-4" />
                  <span>{new Date(article.created_at || '').toLocaleDateString('zh-CN')}</span>
                </div>
                <div className="flex items-center gap-1">
                  <Clock className="w-4 h-4" />
                  <span>{Math.ceil((article.excerpt?.length || 1000) / 1000)}分钟阅读</span>
                </div>
              </div>

              <h3 className={`font-bold mb-3 ${
                index === 0 ? 'text-2xl' : 'text-xl'
              } group-hover:text-yellow-300 transition-colors`}>
                {article.title}
              </h3>

              <p className="mb-4 opacity-90 line-clamp-2">
                {article.excerpt || '暂无摘要'}
              </p>

              <a
                href={`/article?id=${article.id}`}
                className="inline-flex items-center text-sm font-medium hover:text-yellow-300 transition-colors"
              >
                阅读全文
                <ArrowRight className="ml-1 w-4 h-4" />
              </a>
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  </section>
);

// 最新文章区域
const RecentArticlesSection = ({ 
  articles, 
  title,
  pagination
}: { 
  articles: Article[]; 
  title: string;
  pagination: Record<string, unknown>;
}) => (
  <section className="py-20">
    <div className="container mx-auto px-4 sm:px-6 lg:px-8">
      <div className="flex items-center justify-between mb-12">
        <div className="flex items-center gap-3">
          <div className="p-3 rounded-xl bg-gradient-to-r from-green-500 to-emerald-500">
            <Zap className="w-6 h-6 text-white" />
          </div>
          <h2 className="text-3xl font-bold text-gray-900 dark:text-white">
            {title}
          </h2>
        </div>
        <a
          href="/articles"
          className="group inline-flex items-center text-green-600 dark:text-green-400 font-medium hover:text-green-700 dark:hover:text-green-300 transition-colors"
        >
          查看全部
          <ArrowRight className="ml-1 w-4 h-4 group-hover:translate-x-1 transition-transform" />
        </a>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8 mb-12">
        {articles.map((article, index) => (
          <motion.div
            key={article.id}
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.1 }}
            viewport={{ once: true }}
          >
            <ArticleCard
              article={article}
              categoryName={article.category_name || '未分类'}
              authorName={article.author?.username || '匿名作者'}
              showActions={true}
              variant="modern"
            />
          </motion.div>
        ))}
      </div>

      {pagination && (pagination.total_pages as number) > 1 && (
        <div className="flex justify-center">
          <Pagination
            currentPage={pagination.current_page as number}
            totalPages={pagination.total_pages as number}
            hasNext={pagination.has_next as boolean}
            hasPrev={pagination.has_prev as boolean}
            onPageChange={(page) => console.log('切换到页面:', page)}
            variant="modern"
          />
        </div>
      )}
    </div>
  </section>
);

// 热门文章区域
const PopularArticlesSection = ({ 
  articles, 
  title 
}: { 
  articles: Article[]; 
  title: string;
}) => (
  <section className="py-20 bg-gray-50 dark:bg-gray-800/50">
    <div className="container mx-auto px-4 sm:px-6 lg:px-8">
      <div className="text-center mb-16">
        <div className="inline-flex items-center gap-3 mb-4">
          <div className="p-3 rounded-xl bg-gradient-to-r from-red-500 to-pink-500">
            <TrendingUp className="w-6 h-6 text-white" />
          </div>
          <h2 className="text-3xl font-bold text-gray-900 dark:text-white">
            {title}
          </h2>
        </div>
        <p className="text-xl text-gray-600 dark:text-gray-400 max-w-2xl mx-auto">
          最受欢迎的内容，不容错过
        </p>
      </div>

      <div className="space-y-6">
        {articles.slice(0, 5).map((article, index) => (
          <motion.div
            key={article.id}
            initial={{ opacity: 0, x: -30 }}
            whileInView={{ opacity: 1, x: 0 }}
            transition={{ delay: index * 0.1 }}
            viewport={{ once: true }}
            className="group bg-white dark:bg-gray-800 rounded-xl p-6 shadow-lg hover:shadow-xl transition-all duration-300 border border-gray-100 dark:border-gray-700"
          >
            <div className="flex items-start gap-6">
              <div className="flex-shrink-0">
                <div className="w-12 h-12 rounded-full bg-gradient-to-r from-red-500 to-pink-500 flex items-center justify-center text-white font-bold">
                  {index + 1}
                </div>
              </div>
              
              <div className="flex-grow">
                <div className="flex items-center gap-4 mb-2">
                  <span className="text-sm text-gray-500 dark:text-gray-400">
                    {article.category_name || '未分类'}
                  </span>
                  <div className="flex items-center gap-1 text-sm text-gray-500 dark:text-gray-400">
                    <Eye className="w-4 h-4" />
                    <span>{article.views || 0} 浏览</span>
                  </div>
                </div>
                
                <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-2 group-hover:text-red-600 dark:group-hover:text-red-400 transition-colors">
                  {article.title}
                </h3>
                
                <p className="text-gray-600 dark:text-gray-400 mb-4 line-clamp-2">
                  {article.excerpt || '暂无摘要'}
                </p>
                
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-500 dark:text-gray-400">
                    by {article.author?.username || '匿名作者'}
                  </span>
                  <a
                    href={`/article/${article.id}`}
                    className="text-red-500 dark:text-red-400 font-medium hover:text-red-600 dark:hover:text-red-300 transition-colors"
                  >
                    阅读更多 →
                  </a>
                </div>
              </div>
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  </section>
);

// 分类导航区域
const CategoriesSection = ({ 
  categories, 
  title 
}: { 
  categories: Category[]; 
  title: string;
}) => (
  <section className="py-20">
    <div className="container mx-auto px-4 sm:px-6 lg:px-8">
      <div className="text-center mb-16">
        <div className="inline-flex items-center gap-3 mb-4">
          <div className="p-3 rounded-xl bg-gradient-to-r from-purple-500 to-indigo-500">
            <Award className="w-6 h-6 text-white" />
          </div>
          <h2 className="text-3xl font-bold text-gray-900 dark:text-white">
            {title}
          </h2>
        </div>
        <p className="text-xl text-gray-600 dark:text-gray-400 max-w-2xl mx-auto">
          探索不同领域的精彩内容
        </p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
        {categories.slice(0, 8).map((category, index) => (
          <motion.a
            key={category.id}
            href={`/category/${category.name}`}
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.1 }}
            viewport={{ once: true }}
            className="group block bg-white dark:bg-gray-800 rounded-xl p-6 shadow-lg hover:shadow-xl transition-all duration-300 border border-gray-100 dark:border-gray-700 hover:border-purple-200 dark:hover:border-purple-800"
          >
            <div className="text-center">
              <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-gradient-to-r from-purple-500 to-indigo-500 flex items-center justify-center group-hover:scale-110 transition-transform">
                <BookOpen className="w-8 h-8 text-white" />
              </div>
              <h3 className="font-bold text-lg text-gray-900 dark:text-white mb-2 group-hover:text-purple-600 dark:group-hover:text-purple-400 transition-colors">
                {category.name}
              </h3>
              <p className="text-sm text-gray-600 dark:text-gray-400 line-clamp-2">
                {category.description || '暂无描述'}
              </p>
            </div>
          </motion.a>
        ))}
      </div>

      <div className="text-center mt-12">
        <a
          href="/categories"
          className="inline-flex items-center px-6 py-3 bg-gradient-to-r from-purple-500 to-indigo-500 text-white font-medium rounded-lg hover:from-purple-600 hover:to-indigo-600 transition-all duration-300 shadow-lg hover:shadow-xl"
        >
          浏览所有分类
          <ArrowRight className="ml-2 w-5 h-5" />
        </a>
      </div>
    </div>
  </section>
);

// 新闻订阅区域
const NewsletterSection = () => (
  <section className="py-20 bg-gradient-to-r from-blue-500 to-indigo-600 dark:from-blue-600 dark:to-indigo-700">
    <div className="container mx-auto px-4 sm:px-6 lg:px-8">
      <div className="max-w-3xl mx-auto text-center">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
        >
          <div className="w-20 h-20 mx-auto mb-6 rounded-2xl bg-white/20 backdrop-blur-sm flex items-center justify-center">
            <svg className="w-10 h-10 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 4.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
            </svg>
          </div>
          
          <h2 className="text-3xl md:text-4xl font-bold text-white mb-4">
            订阅我们的新闻通讯
          </h2>
          
          <p className="text-xl text-blue-100 mb-8">
            第一时间获取最新文章和独家内容
          </p>
          
          <form className="max-w-md mx-auto">
            <div className="flex flex-col sm:flex-row gap-3">
              <input
                type="email"
                placeholder="输入您的邮箱地址"
                className="flex-grow px-6 py-4 rounded-xl bg-white/90 backdrop-blur-sm focus:outline-none focus:ring-2 focus:ring-white transition-all"
                required
              />
              <button
                type="submit"
                className="px-8 py-4 bg-white text-blue-600 font-semibold rounded-xl hover:bg-blue-50 transition-all duration-300 shadow-lg hover:shadow-xl whitespace-nowrap"
              >
                立即订阅
              </button>
            </div>
            
            <p className="text-sm text-blue-100 mt-4">
              我们尊重您的隐私，随时可以取消订阅
            </p>
          </form>
        </motion.div>
      </div>
    </div>
  </section>
);

// 主组件
export const ModernHomePage = () => {
  const [data, setData] = useState<HomePageData | null>(null);
  const [config, setConfig] = useState<HomePageConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // 真实数据获取
  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        setError(null);
        
        console.log('开始获取首页数据和配置...');
        
        // 并行发起两个请求：数据和配置
        const [dataResponse, configResponse] = await Promise.all([
          fetch('/api/v1/home/data'),
          fetch('/api/v1/home/config')
        ]);
        
        const [dataResult, configResult] = await Promise.all([
          dataResponse.json(),
          configResponse.json()
        ]);
        
        console.log('数据API响应:', dataResult);
        console.log('配置API响应:', configResult);
        
        if (dataResult.success && configResult.success) {
          // 转换API数据格式，确保字段名匹配
          const apiData: HomePageData = {
            featuredArticles: (dataResult.data.featuredArticles || []).map((article: Record<string, unknown>) => ({
              ...article,
              cover_image: article.cover_image || article.coverImage || '',
              category_name: article.category_name || article.categoryName || '未分类',
              created_at: article.created_at || article.createdAt || new Date().toISOString()
            })),
            recentArticles: (dataResult.data.recentArticles || []).map((article: Record<string, unknown>) => ({
              ...article,
              cover_image: article.cover_image || article.coverImage || '',
              category_name: article.category_name || article.categoryName || '未分类',
              created_at: article.created_at || article.createdAt || new Date().toISOString()
            })),
            popularArticles: (dataResult.data.popularArticles || []).map((article: Record<string, unknown>) => ({
              ...article,
              cover_image: article.cover_image || article.coverImage || '',
              category_name: article.category_name || article.categoryName || '未分类',
              created_at: article.created_at || article.createdAt || new Date().toISOString()
            })),
            categories: dataResult.data.categories || [],
            stats: dataResult.data.stats || { totalArticles: 0, totalUsers: 0, totalViews: 0 }
          };

          // 使用后端返回的配置
          const apiConfig: HomePageConfig = {
            hero: {
              title: configResult.data.hero?.title || '欢迎来到 FastBlog',
              subtitle: configResult.data.hero?.subtitle || '发现精彩内容，连接智慧世界。这里有丰富的技术文章和生活分享，与您一同探索无限可能。',
              backgroundImage: configResult.data.hero?.backgroundImage || 'https://images.unsplash.com/photo-1499750310107-5fef28a66643?w=1920',
              ctaText: configResult.data.hero?.ctaText || '开始探索',
              ctaLink: configResult.data.hero?.ctaLink || '/articles'
            },
            sections: {
              featuredTitle: configResult.data.sections?.featuredTitle || '精选文章',
              recentTitle: configResult.data.sections?.recentTitle || '最新内容',
              popularTitle: configResult.data.sections?.popularTitle || '热门文章',
              categoriesTitle: configResult.data.sections?.categoriesTitle || '内容分类'
            }
          };

          console.log('处理后的配置数据:', apiConfig);
          
          setData(apiData);
          setConfig(apiConfig);
          
          console.log('数据和配置设置完成');
        } else {
          const errorMessage = dataResult.error || configResult.error || '数据加载失败';
          console.error('API返回错误:', errorMessage);
          setError(errorMessage);
        }
      } catch (err) {
        console.error('API调用失败:', err);
        setError('网络错误，请稍后重试');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-gray-50 to-white dark:from-gray-900 dark:to-gray-800">
        <LoadingSkeleton />
      </div>
    );
  }

  if (error || !data || !config) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-gray-50 to-white dark:from-gray-900 dark:to-gray-800">
        <ErrorDisplay 
          message={error || '数据加载失败'} 
          retryAction={() => window.location.reload()} 
        />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-white dark:bg-gray-900">
      {/* 英雄区域 */}
      <HeroSection config={config.hero} />
      
      {/* 特色文章 */}
      <FeaturedArticlesSection 
        articles={data.featuredArticles} 
        title={config.sections.featuredTitle} 
      />
      
      {/* 最新文章 */}
      <RecentArticlesSection 
        articles={data.recentArticles} 
        title={config.sections.recentTitle}
        pagination={{}}
      />
      
      {/* 热门文章 */}
      <PopularArticlesSection 
        articles={data.popularArticles} 
        title={config.sections.popularTitle} 
      />
      
      {/* 分类导航 */}
      <CategoriesSection 
        categories={data.categories} 
        title={config.sections.categoriesTitle} 
      />
      
      {/* 新闻订阅 */}
      <NewsletterSection />
    </div>
  );
};