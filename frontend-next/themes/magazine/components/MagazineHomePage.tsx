/**
 * Magazine主题 - 首页组件
 * 杂志风格：网格布局、特色文章、分类区块
 */

'use client';

import React, {useEffect, useState} from 'react';
import {motion} from 'framer-motion';
import {BookOpen, Clock, TrendingUp} from 'lucide-react';
import {Article, Category} from '@/lib/api';
import {useThemeStyles} from '@/hooks/useThemeStyles';

interface MagazineHomePageProps {
    featuredArticles?: Article[];
    recentArticles?: Article[];
    popularArticles?: Article[];
    categories?: Category[];
}

export const MagazineHomePage: React.FC<MagazineHomePageProps> = ({
                                                                      featuredArticles = [],
                                                                      recentArticles = [],
                                                                      popularArticles = [],
                                                                      categories = []
                                                                  }) => {
    const themeStyles = useThemeStyles();
    const [isLoading, setIsLoading] = useState(true);

    useEffect(() => {
        // 模拟数据加载
        const timer = setTimeout(() => setIsLoading(false), 500);
        return () => clearTimeout(timer);
    }, []);

    if (isLoading) {
        return <MagazineSkeleton/>;
    }

    return (
        <div className="min-h-screen" style={{backgroundColor: themeStyles.background}}>
            {/* Breaking News Bar */}
            <BreakingNewsBar/>

            {/* Magazine Header Area */}
            <MagazineHeroSection featuredArticles={featuredArticles}/>

            {/* Category Sections */}
            <CategorySections categories={categories} recentArticles={recentArticles}/>

            {/* Popular Articles Sidebar Style */}
            <PopularSection popularArticles={popularArticles}/>

            {/* Newsletter Signup */}
            <NewsletterSection/>
        </div>
    );
};

/**
 * Breaking News Bar - 突发新闻栏
 */
const BreakingNewsBar: React.FC = () => {
    const themeStyles = useThemeStyles();

    return (
        <div
            className="py-2 px-4 flex items-center gap-4 overflow-hidden"
            style={{
                background: `linear-gradient(90deg, ${themeStyles.primary}, #ef4444)`
            }}
        >
            <span
                className="px-3 py-1 rounded text-xs font-bold uppercase tracking-wider whitespace-nowrap"
                style={{
                    backgroundColor: themeStyles.background,
                    color: themeStyles.primary
                }}
            >
                Breaking
            </span>
            <div className="flex-1 overflow-hidden">
                <motion.div
                    animate={{x: ['100%', '-100%']}}
                    transition={{duration: 20, repeat: Infinity, ease: 'linear'}}
                    className="text-white text-sm font-medium whitespace-nowrap"
                >
                    🔥 这是Magazine主题的突发新闻栏 - 可以显示重要公告或热门文章
                </motion.div>
            </div>
        </div>
    );
};

/**
 * Magazine Hero Section - 杂志风格的特色文章区域
 */
const MagazineHeroSection: React.FC<{ featuredArticles: Article[] }> = ({featuredArticles}) => {
    const themeStyles = useThemeStyles();

    if (!featuredArticles || featuredArticles.length === 0) {
        return (
            <section className="py-16 px-4">
                <div className="container mx-auto max-w-7xl">
                    <h1
                        className="text-6xl md:text-8xl font-black text-center mb-4"
                        style={{
                            fontFamily: themeStyles.fontFamily,
                            color: themeStyles.foreground
                        }}
                    >
                        FastBlog Magazine
                    </h1>
                    <p className="text-xl text-center" style={{color: themeStyles.secondary}}>
                        深度报道 · 专业分析 · 前沿观点
                    </p>
                </div>
            </section>
        );
    }

    return (
        <section className="py-8 px-4">
            <div className="container mx-auto max-w-7xl">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    {/* 主特色文章 - 占据2列 */}
                    {featuredArticles[0] && (
                        <div
                            className="md:col-span-2 relative group cursor-pointer overflow-hidden rounded-lg shadow-2xl">
                            <img
                                src={featuredArticles[0].thumbnail || '/placeholder.jpg'}
                                alt={featuredArticles[0].title}
                                className="w-full h-[500px] object-cover transition-transform duration-500 group-hover:scale-105"
                            />
                            <div
                                className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/40 to-transparent"/>
                            <div className="absolute bottom-0 left-0 right-0 p-8">
                                <span
                                    className="inline-block px-3 py-1 rounded text-xs font-bold uppercase mb-3"
                                    style={{backgroundColor: themeStyles.primary, color: 'white'}}
                                >
                                    Featured
                                </span>
                                <h2 className="text-4xl font-bold text-white mb-3 leading-tight">
                                    {featuredArticles[0].title}
                                </h2>
                                <div className="flex items-center gap-4 text-white/80 text-sm">
                                    <span className="flex items-center gap-1">
                                        <Clock size={14}/>
                                        {new Date(featuredArticles[0].created_at).toLocaleDateString('zh-CN')}
                                    </span>
                                    <span>{featuredArticles[0].author?.username}</span>
                                </div>
                            </div>
                        </div>
                    )}

                    {/* 侧边特色文章 */}
                    <div className="space-y-6">
                        {featuredArticles.slice(1, 3).map((article, index) => (
                            article && (
                                <div key={article.id || index}
                                     className="relative group cursor-pointer overflow-hidden rounded-lg shadow-lg">
                                    <img
                                        src={article.thumbnail || '/placeholder.jpg'}
                                        alt={article.title}
                                        className="w-full h-[240px] object-cover transition-transform duration-500 group-hover:scale-105"
                                    />
                                    <div className="absolute inset-0 bg-gradient-to-t from-black/80 to-transparent"/>
                                    <div className="absolute bottom-0 left-0 right-0 p-4">
                                        <h3 className="text-xl font-bold text-white mb-2 line-clamp-2">
                                            {article.title}
                                        </h3>
                                        <span className="text-white/70 text-xs">
                                            {new Date(article.created_at).toLocaleDateString('zh-CN')}
                                        </span>
                                    </div>
                                </div>
                            )
                        ))}
                    </div>
                </div>
            </div>
        </section>
    );
};

/**
 * Category Sections - 分类内容区块
 */
const CategorySections: React.FC<{ categories: Category[], recentArticles: Article[] }> = ({
                                                                                               categories,
                                                                                               recentArticles
                                                                                           }) => {
    const themeStyles = useThemeStyles();

    if (categories.length === 0) return null;

    return (
        <section className="py-12 px-4">
            <div className="container mx-auto max-w-7xl">
                {categories.slice(0, 3).map((category, catIndex) => (
                    <div key={category.id} className="mb-12">
                        {/* Category Header */}
                        <div
                            className="flex items-center justify-between pb-3 mb-6 border-b-2"
                            style={{borderColor: themeStyles.primary}}
                        >
                            <h2
                                className="text-3xl font-bold uppercase tracking-wide"
                                style={{color: themeStyles.primary}}
                            >
                                {category.name}
                            </h2>
                            <a
                                href={`/categories/${category.slug || category.id}`}
                                className="text-sm font-medium hover:underline"
                                style={{color: themeStyles.secondary}}
                            >
                                查看更多 →
                            </a>
                        </div>

                        {/* Articles Grid */}
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                            {recentArticles.slice(catIndex * 3, (catIndex + 1) * 3).map((article, idx) => (
                                article && <MagazineArticleCard key={article.id || idx} article={article}/>
                            ))}
                        </div>
                    </div>
                ))}
            </div>
        </section>
    );
};

/**
 * Magazine Article Card - 杂志风格文章卡片
 */
const MagazineArticleCard: React.FC<{ article: Article }> = ({article}) => {
    const themeStyles = useThemeStyles();

    return (
        <article className="group cursor-pointer">
            <div className="overflow-hidden rounded-lg mb-4">
                <img
                    src={article.thumbnail || '/placeholder.jpg'}
                    alt={article.title}
                    className="w-full h-48 object-cover transition-transform duration-300 group-hover:scale-110"
                />
            </div>
            <h3
                className="text-xl font-bold mb-2 line-clamp-2 group-hover:underline"
                style={{color: themeStyles.foreground}}
            >
                {article.title}
            </h3>
            <p className="text-sm line-clamp-3 mb-3" style={{color: themeStyles.secondary}}>
                {article.excerpt || '暂无摘要...'}
            </p>
            <div className="flex items-center gap-3 text-xs" style={{color: themeStyles.secondary}}>
                <span>{article.author?.username}</span>
                <span>•</span>
                <span>{new Date(article.created_at).toLocaleDateString('zh-CN')}</span>
            </div>
        </article>
    );
};

/**
 * Popular Section - 热门文章区域
 */
const PopularSection: React.FC<{ popularArticles: Article[] }> = ({popularArticles}) => {
    const themeStyles = useThemeStyles();

    if (!popularArticles || popularArticles.length === 0) return null;

    return (
        <section className="py-12 px-4" style={{backgroundColor: themeStyles.muted}}>
            <div className="container mx-auto max-w-7xl">
                <div className="flex items-center gap-3 mb-8">
                    <TrendingUp size={32} style={{color: themeStyles.primary}}/>
                    <h2 className="text-3xl font-bold" style={{color: themeStyles.foreground}}>
                        热门文章
                    </h2>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                    {popularArticles.slice(0, 4).map((article, index) => (
                        article && (
                            <div key={article.id || index} className="flex gap-4 group cursor-pointer">
                                <div
                                    className="text-5xl font-black opacity-20"
                                    style={{color: themeStyles.primary}}
                                >
                                    {String(index + 1).padStart(2, '0')}
                                </div>
                                <div>
                                    <h4
                                        className="font-bold mb-2 line-clamp-2 group-hover:underline"
                                        style={{color: themeStyles.foreground}}
                                    >
                                        {article.title}
                                    </h4>
                                    <div className="text-xs" style={{color: themeStyles.secondary}}>
                                        <span>{article.view_count || article.views || 0} 阅读</span>
                                    </div>
                                </div>
                            </div>
                        )
                    ))}
                </div>
            </div>
        </section>
    );
};

/**
 * Newsletter Section - 订阅区域
 */
const NewsletterSection: React.FC = () => {
    const themeStyles = useThemeStyles();

    return (
        <section className="py-16 px-4" style={{backgroundColor: themeStyles.primary}}>
            <div className="container mx-auto max-w-4xl text-center">
                <BookOpen size={48} className="mx-auto mb-6 text-white"/>
                <h2 className="text-4xl font-bold text-white mb-4">
                    订阅我们的通讯
                </h2>
                <p className="text-white/90 mb-8 text-lg">
                    获取最新的文章推送和独家内容
                </p>
                <div className="flex flex-col sm:flex-row gap-4 max-w-xl mx-auto">
                    <input
                        type="email"
                        placeholder="输入您的邮箱地址"
                        className="flex-1 px-6 py-4 rounded-lg focus:outline-none focus:ring-4 focus:ring-white/30"
                        style={{backgroundColor: 'rgba(255,255,255,0.9)'}}
                    />
                    <button
                        className="px-8 py-4 rounded-lg font-bold transition-all hover:scale-105"
                        style={{
                            backgroundColor: themeStyles.background,
                            color: themeStyles.primary
                        }}
                    >
                        立即订阅
                    </button>
                </div>
            </div>
        </section>
    );
};

/**
 * Loading Skeleton
 */
const MagazineSkeleton: React.FC = () => {
    return (
        <div className="min-h-screen bg-gray-50 animate-pulse">
            <div className="h-8 bg-gray-200"/>
            <div className="container mx-auto max-w-7xl py-8 px-4">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    <div className="md:col-span-2 h-[500px] bg-gray-200 rounded-lg"/>
                    <div className="space-y-6">
                        <div className="h-[240px] bg-gray-200 rounded-lg"/>
                        <div className="h-[240px] bg-gray-200 rounded-lg"/>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default MagazineHomePage;
