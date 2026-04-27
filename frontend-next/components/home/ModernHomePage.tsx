'use client';

import React, {useEffect, useState} from 'react';
import {motion} from 'framer-motion';
import {ArrowRight, BookOpen, Calendar, ChevronRight, Eye, Flame, Heart, Search, Star, Tag} from 'lucide-react';
import {Article, Category} from '@/lib/api';
import {loadRuntimeConfig} from '@/lib/config';
import ArticleCard from '../ArticleCard';
import {useThemeBgColor, useThemeGradient, useThemeStyles, useThemeTextColor} from '@/hooks/useThemeStyles';

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

// 加载状态组件 - 更现代的骨架屏
const LoadingSkeleton = () => (
    <div className="animate-pulse">
        {/* Hero 区域骨架 */}
        <div
            className="h-[85vh] bg-gradient-to-br from-gray-200 to-gray-300 dark:from-gray-700 dark:to-gray-800 relative overflow-hidden">
            <div
                className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent animate-shimmer"/>
        </div>

        {/* 文章列表骨架 */}
        <div className="py-20">
            <div className="container mx-auto px-4">
                <div className="h-10 w-64 bg-gray-200 dark:bg-gray-700 rounded-lg mx-auto mb-12"/>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
                    {[1, 2, 3, 4, 5, 6].map(i => (
                        <div key={i} className="bg-white dark:bg-gray-800 rounded-2xl overflow-hidden shadow-lg">
                            <div className="h-56 bg-gray-200 dark:bg-gray-700"/>
                            <div className="p-6">
                                <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded mb-3"/>
                                <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded mb-2"/>
                                <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-3/4"/>
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    </div>
);

// CSS for shimmer animation (需要在 globals.css 中添加)
const shimmerStyles = `
@keyframes shimmer {
    0% { transform: translateX(-100%); }
    100% { transform: translateX(100%); }
}
.animate-shimmer {
    animation: shimmer 2s infinite;
}
`;

// 错误状态组件 - 更友好的设计
const ErrorDisplay = ({message, retryAction}: { message: string; retryAction: () => void }) => (
    <div
        className="min-h-screen flex items-center justify-center bg-gradient-to-br from-red-50 to-orange-50 dark:from-gray-900 dark:to-gray-800">
        <motion.div
            initial={{opacity: 0, scale: 0.9}}
            animate={{opacity: 1, scale: 1}}
            className="text-center max-w-md mx-auto px-4"
        >
            <div
                className="w-24 h-24 mx-auto mb-6 rounded-full bg-gradient-to-br from-red-500 to-orange-500 flex items-center justify-center shadow-2xl">
                <span className="text-5xl">⚠️</span>
            </div>
            <h2 className="text-3xl font-black text-gray-900 dark:text-white mb-4">
                加载失败
            </h2>
            <p className="text-gray-600 dark:text-gray-400 mb-8 text-lg">
                {message}
            </p>
            <button
                onClick={retryAction}
                className="px-8 py-4 bg-gradient-to-r from-blue-600 to-purple-600 text-white font-bold rounded-xl hover:shadow-2xl transition-all hover:scale-105"
            >
                重新加载
            </button>
        </motion.div>
    </div>
);

// 英雄区域组件 - 更现代的设计
const HeroSection = ({config, stats}: { config: HomePageConfig['hero']; stats?: HomePageData['stats'] }) => {
    const [searchQuery, setSearchQuery] = useState('');

    // 使用主题样式
    const heroGradient = useThemeGradient('primary', 'accent');
    const textColor = useThemeTextColor('primary');
    const bgStyles = useThemeBgColor('background');
    const themeStyles = useThemeStyles();

    return (
        <section
            className="relative min-h-[85vh] flex items-center overflow-hidden"
            style={heroGradient}
        >
            {/* 动态网格背景 */}
            <div className="absolute inset-0 opacity-20">
                <div className="absolute inset-0" style={{
                    backgroundImage: `linear-gradient(rgba(255,255,255,0.1) 1px, transparent 1px),
                                     linear-gradient(90deg, rgba(255,255,255,0.1) 1px, transparent 1px)`,
                    backgroundSize: '50px 50px'
                }}/>
            </div>

            {/* 浮动光斑 */}
            <div className="absolute inset-0 overflow-hidden">
                <motion.div
                    animate={{
                        x: [0, 100, 0],
                        y: [0, -50, 0],
                    }}
                    transition={{duration: 20, repeat: Infinity, ease: "linear"}}
                    className="absolute top-20 left-10 w-72 h-72 bg-white/10 rounded-full blur-3xl"
                />
                <motion.div
                    animate={{
                        x: [0, -100, 0],
                        y: [0, 50, 0],
                    }}
                    transition={{duration: 25, repeat: Infinity, ease: "linear"}}
                    className="absolute bottom-20 right-10 w-96 h-96 bg-yellow-500/10 rounded-full blur-3xl"
                />
            </div>

            {/* 内容区域 */}
            <div className="relative z-10 container mx-auto px-4 sm:px-6 lg:px-8 py-20">
                <div className="max-w-5xl mx-auto text-center">
                    {/* 主标题 */}
                    <motion.div
                        initial={{opacity: 0, y: 30}}
                        animate={{opacity: 1, y: 0}}
                        transition={{duration: 0.8}}
                    >
                        <h1 className="text-6xl md:text-8xl lg:text-9xl font-black mb-6 tracking-tight drop-shadow-2xl"
                            style={{...textColor, color: 'white'}}>
                            FastBlog
                        </h1>
                    </motion.div>

                    {/* 副标题徽章 */}
                    <motion.div
                        initial={{scale: 0.9, opacity: 0}}
                        animate={{scale: 1, opacity: 1}}
                        transition={{delay: 0.3}}
                        className="inline-block px-8 py-4 backdrop-blur-xl rounded-2xl mb-8 border shadow-2xl"
                        style={{
                            backgroundColor: 'rgba(255, 255, 255, 0.1)',
                            borderColor: 'rgba(255, 255, 255, 0.2)',
                        }}
                    >
                        <p className="text-xl md:text-2xl font-light" style={{color: 'rgba(255, 255, 255, 0.9)'}}>
                            {config.subtitle}
                        </p>
                    </motion.div>

                    {/* 搜索框 */}
                    <motion.div
                        initial={{opacity: 0, y: 20}}
                        animate={{opacity: 1, y: 0}}
                        transition={{delay: 0.6}}
                        className="max-w-3xl mx-auto mb-12"
                    >
                        <div className="relative group">
                            <input
                                type="text"
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                                placeholder="搜索文章、话题或作者..."
                                className="w-full px-8 py-5 pl-14 rounded-2xl bg-white/95 backdrop-blur-sm text-gray-800 placeholder-gray-500 shadow-2xl focus:outline-none focus:ring-4 focus:ring-white/30 transition-all text-lg"
                                onKeyDown={(e) => {
                                    if (e.key === 'Enter' && searchQuery.trim()) {
                                        window.location.href = `/search?q=${encodeURIComponent(searchQuery)}`;
                                    }
                                }}
                            />
                            <Search
                                className="absolute left-6 top-1/2 transform -translate-y-1/2 w-6 h-6 text-gray-400 group-focus-within:text-blue-600 transition-colors"/>
                            <button
                                onClick={() => searchQuery.trim() && (window.location.href = `/search?q=${encodeURIComponent(searchQuery)}`)}
                                className="absolute right-3 top-1/2 transform -translate-y-1/2 px-6 py-2.5 bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-xl font-medium hover:shadow-lg transition-all"
                            >
                                搜索
                            </button>
                        </div>
                    </motion.div>

                    {/* CTA 按钮组 */}
                    <motion.div
                        initial={{opacity: 0, y: 20}}
                        animate={{opacity: 1, y: 0}}
                        transition={{delay: 0.8}}
                        className="flex flex-wrap gap-4 justify-center"
                    >
                        <a
                            href="/articles"
                            className="group inline-flex items-center gap-3 px-10 py-5 bg-white text-blue-600 font-bold rounded-2xl hover:bg-gray-50 transition-all shadow-2xl hover:shadow-white/50 hover:scale-105"
                        >
                            <BookOpen className="w-6 h-6"/>
                            <span>{config.ctaText}</span>
                            <ArrowRight className="w-5 h-5 group-hover:translate-x-2 transition-transform"/>
                        </a>
                        <a
                            href="/register"
                            className="group inline-flex items-center gap-3 px-10 py-5 bg-white/10 backdrop-blur-sm text-white font-bold rounded-2xl border-2 border-white/50 hover:bg-white/20 transition-all hover:scale-105"
                        >
                            <Star className="w-6 h-6"/>
                            <span>立即加入</span>
                        </a>
                    </motion.div>

                    {/* 统计信息 */}
                    {stats && (
                        <motion.div
                            initial={{opacity: 0, y: 20}}
                            animate={{opacity: 1, y: 0}}
                            transition={{delay: 1}}
                            className="grid grid-cols-3 gap-8 mt-16 max-w-3xl mx-auto"
                        >
                            <div className="text-center">
                                <div className="text-4xl md:text-5xl font-black text-white mb-2">
                                    {stats.totalArticles.toLocaleString()}
                                </div>
                                <div className="text-white/80 font-medium">篇文章</div>
                            </div>
                            <div className="text-center">
                                <div className="text-4xl md:text-5xl font-black text-white mb-2">
                                    {stats.totalUsers.toLocaleString()}
                                </div>
                                <div className="text-white/80 font-medium">位用户</div>
                            </div>
                            <div className="text-center">
                                <div className="text-4xl md:text-5xl font-black text-white mb-2">
                                    {stats.totalViews.toLocaleString()}
                                </div>
                                <div className="text-white/80 font-medium">次浏览</div>
                            </div>
                        </motion.div>
                    )}
                </div>
            </div>

            {/* 滚动指示器 */}
            <motion.div
                initial={{opacity: 0}}
                animate={{opacity: 1}}
                transition={{delay: 1.2}}
                className="absolute bottom-8 left-1/2 transform -translate-x-1/2"
            >
                <motion.div
                    animate={{y: [0, 10, 0]}}
                    transition={{duration: 2, repeat: Infinity}}
                    className="w-8 h-12 border-2 border-white/50 rounded-full flex justify-center p-2"
                >
                    <div className="w-1.5 h-3 bg-white/80 rounded-full"></div>
                </motion.div>
            </motion.div>
        </section>
    );
};

// 最新文章区域 - 使用卡片网格布局
const RecentArticlesSection = ({
                                   articles,
                                   title
                               }: {
    articles: Article[];
    title: string;
}) => (
    <section className="py-20 bg-white dark:bg-gray-900">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8">
            <motion.div
                initial={{opacity: 0, y: 20}}
                whileInView={{opacity: 1, y: 0}}
                viewport={{once: true}}
                className="text-center mb-16"
            >
                <div className="inline-flex items-center gap-3 mb-4">
                    <div className="p-3 rounded-xl bg-gradient-to-r from-blue-500 to-cyan-500">
                        <BookOpen className="w-6 h-6 text-white"/>
                    </div>
                    <h2 className="text-4xl font-black text-gray-900 dark:text-white">
                        {title}
                    </h2>
                </div>
                <p className="text-xl text-gray-600 dark:text-gray-400 max-w-2xl mx-auto">
                    探索最新发布的优质内容
                </p>
            </motion.div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
                {articles.slice(0, 6).map((article, index) => (
                    <motion.div
                        key={article.id}
                        initial={{opacity: 0, y: 30}}
                        whileInView={{opacity: 1, y: 0}}
                        transition={{delay: index * 0.1}}
                        viewport={{once: true}}
                    >
                        <ArticleCard
                            article={article}
                            categoryName={article.category_name && article.category_name !== '未分类' ? article.category_name : ''}
                            authorName={article.author?.username || '匿名'}
                            variant="modern"
                        />
                    </motion.div>
                ))}
            </div>

            <motion.div
                initial={{opacity: 0, y: 20}}
                whileInView={{opacity: 1, y: 0}}
                viewport={{once: true}}
                className="text-center mt-16"
            >
                <a
                    href="/articles"
                    className="inline-flex items-center gap-3 px-8 py-4 bg-gradient-to-r from-blue-600 to-cyan-600 text-white font-bold rounded-xl hover:shadow-2xl transition-all duration-300 hover:scale-105"
                >
                    查看更多文章
                    <ChevronRight className="w-5 h-5"/>
                </a>
            </motion.div>
        </div>
    </section>
);
// 热门文章区域 - 列表式布局
const PopularArticlesSection = ({
                                    articles,
                                    title
                                }: {
    articles: Article[];
    title: string;
}) => (
    <section className="py-20 bg-gradient-to-br from-gray-50 to-blue-50 dark:from-gray-800 dark:to-gray-900">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8">
            <motion.div
                initial={{opacity: 0, y: 20}}
                whileInView={{opacity: 1, y: 0}}
                viewport={{once: true}}
                className="text-center mb-16"
            >
                <div className="inline-flex items-center gap-3 mb-4">
                    <div className="p-3 rounded-xl bg-gradient-to-r from-orange-500 to-red-500">
                        <Flame className="w-6 h-6 text-white"/>
                    </div>
                    <h2 className="text-4xl font-black text-gray-900 dark:text-white">
                        {title}
                    </h2>
                </div>
                <p className="text-xl text-gray-600 dark:text-gray-400 max-w-2xl mx-auto">
                    社区最受欢迎的精选内容
                </p>
            </motion.div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-6xl mx-auto">
                {articles.slice(0, 6).map((article, index) => (
                    <motion.a
                        key={article.id}
                        href={`/blog/detail?slug=${article.slug}`}
                        initial={{opacity: 0, x: -20}}
                        whileInView={{opacity: 1, x: 0}}
                        transition={{delay: index * 0.1}}
                        viewport={{once: true}}
                        className="group flex gap-6 p-6 bg-white dark:bg-gray-800 rounded-2xl shadow-lg hover:shadow-2xl transition-all duration-300 border border-gray-100 dark:border-gray-700 hover:border-orange-200 dark:hover:border-orange-800 overflow-hidden relative"
                    >
                        {/* 排名徽章 */}
                        <div className="flex-shrink-0">
                            <div
                                className={`w-14 h-14 rounded-full flex items-center justify-center font-black text-xl ${
                                    index === 0 ? 'bg-gradient-to-r from-yellow-400 to-yellow-500 text-white' :
                                        index === 1 ? 'bg-gradient-to-r from-gray-300 to-gray-400 text-white' :
                                            index === 2 ? 'bg-gradient-to-r from-amber-600 to-amber-700 text-white' :
                                                'bg-gradient-to-r from-gray-100 to-gray-200 dark:from-gray-700 dark:to-gray-600 text-gray-600 dark:text-gray-300'
                                }`}>
                                #{index + 1}
                            </div>
                        </div>

                        {/* 内容 */}
                        <div className="flex-grow min-w-0">
                            <div className="flex items-center gap-3 mb-2 text-sm">
                                {article.category_name && article.category_name !== '未分类' && (
                                    <span
                                        className="px-3 py-1 bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 rounded-full font-medium">
                                        {article.category_name}
                                    </span>
                                )}
                                <div className="flex items-center gap-1 text-gray-500 dark:text-gray-400">
                                    <Eye className="w-4 h-4"/>
                                    <span>{(article.views || 0).toLocaleString()} 次浏览</span>
                                </div>
                            </div>

                            <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-2 group-hover:text-orange-600 dark:group-hover:text-orange-400 transition-colors line-clamp-2">
                                {article.title}
                            </h3>

                            <p className="text-gray-600 dark:text-gray-400 mb-4 line-clamp-2">
                                {article.excerpt || article.summary || '暂无摘要'}
                            </p>

                            <div className="flex items-center justify-between">
                                <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
                                    <Calendar className="w-4 h-4"/>
                                    <span>{new Date(article.created_at || '').toLocaleDateString('zh-CN')}</span>
                                </div>
                                <div
                                    className="flex items-center gap-1 text-orange-500 dark:text-orange-400 font-medium">
                                    <span>阅读更多</span>
                                    <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform"/>
                                </div>
                            </div>
                        </div>

                        {/* 悬停效果 */}
                        <div
                            className="absolute inset-0 bg-gradient-to-r from-orange-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none"/>
                    </motion.a>
                ))}
            </div>
        </div>
    </section>
);

// 分类导航区域 - 现代化卡片设计
const CategoriesSection = ({
                               categories,
                               title
                           }: {
    categories: Category[];
    title: string;
}) => (
    <section className="py-20 bg-white dark:bg-gray-900">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8">
            <motion.div
                initial={{opacity: 0, y: 20}}
                whileInView={{opacity: 1, y: 0}}
                viewport={{once: true}}
                className="text-center mb-16"
            >
                <div className="inline-flex items-center gap-3 mb-4">
                    <div className="p-3 rounded-xl bg-gradient-to-r from-purple-500 to-pink-500">
                        <Tag className="w-6 h-6 text-white"/>
                    </div>
                    <h2 className="text-4xl font-black text-gray-900 dark:text-white">
                        {title}
                    </h2>
                </div>
                <p className="text-xl text-gray-600 dark:text-gray-400 max-w-2xl mx-auto">
                    按主题探索精彩内容
                </p>
            </motion.div>

            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6 max-w-6xl mx-auto">
                {categories.slice(0, 8).map((category, index) => (
                    <motion.a
                        key={category.id}
                        href={`/category/detail?name=${category.name}`}
                        initial={{opacity: 0, scale: 0.9}}
                        whileInView={{opacity: 1, scale: 1}}
                        transition={{delay: index * 0.1}}
                        viewport={{once: true}}
                        className="group relative overflow-hidden bg-gradient-to-br from-white to-gray-50 dark:from-gray-800 dark:to-gray-700 rounded-2xl p-8 shadow-lg hover:shadow-2xl transition-all duration-300 border border-gray-100 dark:border-gray-700 hover:border-purple-300 dark:hover:border-purple-600"
                    >
                        {/* 背景装饰 */}
                        <div
                            className="absolute -right-4 -top-4 w-24 h-24 bg-gradient-to-br from-purple-500/10 to-pink-500/10 rounded-full blur-2xl group-hover:from-purple-500/20 group-hover:to-pink-500/20 transition-all"/>

                        <div className="relative">
                            {/* 图标 */}
                            <div
                                className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center group-hover:scale-110 group-hover:rotate-6 transition-all duration-300 shadow-lg">
                                <BookOpen className="w-8 h-8 text-white"/>
                            </div>

                            {/* 标题 */}
                            <h3 className="text-lg font-bold text-gray-900 dark:text-white text-center mb-2 group-hover:text-purple-600 dark:group-hover:text-purple-400 transition-colors">
                                {category.name}
                            </h3>

                            {/* 描述 */}
                            <p className="text-sm text-gray-600 dark:text-gray-400 text-center line-clamp-2 mb-4">
                                {category.description || '探索这个分类下的所有文章'}
                            </p>

                            {/* 查看链接 */}
                            <div
                                className="flex items-center justify-center gap-2 text-purple-600 dark:text-purple-400 font-medium opacity-0 group-hover:opacity-100 transition-opacity">
                                <span>查看详情</span>
                                <ChevronRight className="w-4 h-4 group-hover:translate-x-1 transition-transform"/>
                            </div>
                        </div>
                    </motion.a>
                ))}
            </div>

            <motion.div
                initial={{opacity: 0, y: 20}}
                whileInView={{opacity: 1, y: 0}}
                viewport={{once: true}}
                className="text-center mt-16"
            >
                <a
                    href="/categories"
                    className="inline-flex items-center gap-3 px-8 py-4 bg-gradient-to-r from-purple-600 to-pink-600 text-white font-bold rounded-xl hover:shadow-2xl transition-all duration-300 hover:scale-105"
                >
                    浏览所有分类
                    <ChevronRight className="w-5 h-5"/>
                </a>
            </motion.div>
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

                // 加载运行时配置
                const config = await loadRuntimeConfig();
                const baseUrl = config.API_BASE_URL;
                const apiPrefix = config.API_PREFIX;

                console.log('使用 API 配置:', {baseUrl, apiPrefix});

                // 并行发起两个请求：数据和配置
                const [dataResponse, configResponse] = await Promise.all([
                    fetch(`${baseUrl}${apiPrefix}/home/data`),
                    fetch(`${baseUrl}${apiPrefix}/home/config`)
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
                            category_name: article.category_name || article.categoryName || undefined,
                            created_at: article.created_at || article.createdAt || new Date().toISOString()
                        })),
                        recentArticles: (dataResult.data.recentArticles || []).map((article: Record<string, unknown>) => ({
                            ...article,
                            cover_image: article.cover_image || article.coverImage || '',
                            category_name: article.category_name || article.categoryName || undefined,
                            created_at: article.created_at || article.createdAt || new Date().toISOString()
                        })),
                        popularArticles: (dataResult.data.popularArticles || []).map((article: Record<string, unknown>) => ({
                            ...article,
                            cover_image: article.cover_image || article.coverImage || '',
                            category_name: article.category_name || article.categoryName || undefined,
                            created_at: article.created_at || article.createdAt || new Date().toISOString()
                        })),
                        categories: dataResult.data.categories || [],
                        stats: dataResult.data.stats || {totalArticles: 0, totalUsers: 0, totalViews: 0}
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
                <LoadingSkeleton/>
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
        <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
            {/* 英雄区域 */}
            <HeroSection config={config.hero} stats={data.stats}/>

            {/* 最新文章 - 作为主要内容展示 */}
            {data.recentArticles.length > 0 && (
                <RecentArticlesSection
                    articles={data.recentArticles}
                    title={config.sections.recentTitle || '最新文章'}
                />
            )}

            {/* 热门文章 */}
            {data.popularArticles.length > 0 && (
                <PopularArticlesSection
                    articles={data.popularArticles}
                    title={config.sections.popularTitle || '热门文章'}
                />
            )}

            {/* 分类导航 */}
            {data.categories.length > 0 && (
                <CategoriesSection
                    categories={data.categories}
                    title={config.sections.categoriesTitle || '内容分类'}
                />
            )}

            {/* CTA 区域 - 更现代的设计 */}
            <section
                className="py-24 bg-gradient-to-br from-indigo-600 via-purple-600 to-pink-500 relative overflow-hidden">
                {/* 背景装饰 */}
                <div className="absolute inset-0 opacity-20">
                    <div className="absolute top-0 left-1/4 w-96 h-96 bg-white/10 rounded-full blur-3xl"/>
                    <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-yellow-500/10 rounded-full blur-3xl"/>
                </div>

                <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
                    <motion.div
                        initial={{opacity: 0, y: 30}}
                        whileInView={{opacity: 1, y: 0}}
                        viewport={{once: true}}
                        className="max-w-4xl mx-auto text-center"
                    >
                        <div
                            className="w-20 h-20 mx-auto mb-8 rounded-2xl bg-white/20 backdrop-blur-xl flex items-center justify-center">
                            <Heart className="w-10 h-10 text-white"/>
                        </div>

                        <h2 className="text-5xl md:text-6xl font-black text-white mb-6 leading-tight">
                            准备好开始创作了吗？
                        </h2>
                        <p className="text-2xl text-white/90 mb-12 max-w-2xl mx-auto">
                            加入 FastBlog 社区，与万千开发者分享你的技术见解和经验
                        </p>
                        <div className="flex flex-wrap gap-4 justify-center">
                            <a
                                href="/register"
                                className="group inline-flex items-center gap-3 px-10 py-5 bg-white text-blue-600 font-bold rounded-2xl hover:bg-gray-50 transition-all shadow-2xl hover:shadow-white/50 hover:scale-105"
                            >
                                <Star className="w-6 h-6"/>
                                <span>立即注册</span>
                                <ArrowRight className="w-5 h-5 group-hover:translate-x-2 transition-transform"/>
                            </a>
                            <a
                                href="/about"
                                className="inline-flex items-center gap-3 px-10 py-5 bg-white/10 backdrop-blur-sm text-white font-bold rounded-2xl border-2 border-white/50 hover:bg-white/20 transition-all hover:scale-105"
                            >
                                <BookOpen className="w-6 h-6"/>
                                <span>了解更多</span>
                            </a>
                        </div>
                    </motion.div>
                </div>
            </section>
        </div>
    );
};