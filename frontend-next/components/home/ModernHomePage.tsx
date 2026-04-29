'use client';

import React, {useEffect, useState} from 'react';
import Link from 'next/link';
import Image from 'next/image';
import {motion, useScroll, useTransform} from 'framer-motion';
import {
    ArrowRight,
    BookOpen,
    TrendingUp,
    Clock,
    Search,
    ChevronRight,
    Sparkles,
    Zap,
    Users,
    FileText
} from 'lucide-react';
import {ArticleService} from '@/lib/api';
import type {Article, Category} from '@/lib/api/base-types';

// 动画配置
const fadeInUp = {
    initial: {opacity: 0, y: 20},
    animate: {opacity: 1, y: 0},
    transition: {duration: 0.5}
};

const staggerContainer = {
    animate: {
        transition: {
            staggerChildren: 0.1
        }
    }
};

// Hero Section - 极简大气
const HeroSection = () => {
    const [searchQuery, setSearchQuery] = useState('');

    return (
        <section
            className="relative min-h-screen flex items-center justify-center overflow-hidden bg-white dark:bg-gray-950">
            {/* 背景渐变 */}
            <div
                className="absolute inset-0 bg-gradient-to-br from-blue-50 via-white to-purple-50 dark:from-gray-950 dark:via-gray-900 dark:to-gray-950"/>

            {/* 网格背景 */}
            <div
                className="absolute inset-0 opacity-[0.03] dark:opacity-[0.05]"
                style={{
                    backgroundImage: `radial-gradient(circle at 1px 1px, currentColor 1px, transparent 0)`,
                    backgroundSize: '40px 40px'
                }}
            />

            {/* 浮动光晕 */}
            <motion.div
                animate={{
                    scale: [1, 1.2, 1],
                    opacity: [0.3, 0.5, 0.3],
                }}
                transition={{duration: 8, repeat: Infinity}}
                className="absolute top-1/4 left-1/4 w-96 h-96 bg-blue-400/20 rounded-full blur-3xl"
            />
            <motion.div
                animate={{
                    scale: [1, 1.3, 1],
                    opacity: [0.2, 0.4, 0.2],
                }}
                transition={{duration: 10, repeat: Infinity, delay: 2}}
                className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-purple-400/20 rounded-full blur-3xl"
            />

            {/* 内容 */}
            <div className="relative z-10 max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
                <motion.div
                    initial={{opacity: 0, y: 30}}
                    animate={{opacity: 1, y: 0}}
                    transition={{duration: 0.8}}
                    className="mb-8"
                >
                    <div
                        className="inline-flex items-center gap-2 px-4 py-2 bg-blue-50 dark:bg-blue-900/20 rounded-full mb-6">
                        <Sparkles className="w-4 h-4 text-blue-600 dark:text-blue-400"/>
                        <span className="text-sm font-medium text-blue-600 dark:text-blue-400">
                            发现精彩内容
                        </span>
                    </div>

                    <h1 className="text-5xl sm:text-6xl md:text-7xl lg:text-8xl font-black text-gray-900 dark:text-white tracking-tight leading-none mb-6">
                        探索知识
                        <br/>
                        <span className="bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
                            分享智慧
                        </span>
                    </h1>

                    <p className="text-lg sm:text-xl text-gray-600 dark:text-gray-400 max-w-2xl mx-auto mb-12">
                        在这里，每一篇文章都是一次思想的碰撞，每一次阅读都是一场心灵的旅行
                    </p>
                </motion.div>

                {/* 搜索框 */}
                <motion.div
                    initial={{opacity: 0, y: 20}}
                    animate={{opacity: 1, y: 0}}
                    transition={{delay: 0.3}}
                    className="max-w-2xl mx-auto mb-12"
                >
                    <div className="relative group">
                        <Search
                            className="absolute left-5 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400 group-focus-within:text-blue-600 transition-colors"/>
                        <input
                            type="text"
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            placeholder="搜索文章、话题或作者..."
                            className="w-full pl-14 pr-6 py-4 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-2xl text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent shadow-lg hover:shadow-xl transition-all text-lg"
                        />
                        <div className="absolute right-3 top-1/2 -translate-y-1/2">
                            <kbd
                                className="hidden sm:inline-block px-3 py-1.5 text-xs font-semibold text-gray-500 bg-gray-100 dark:bg-gray-800 dark:text-gray-400 rounded-lg border border-gray-200 dark:border-gray-700">
                                ⌘K
                            </kbd>
                        </div>
                    </div>
                </motion.div>

                {/* CTA 按钮 */}
                <motion.div
                    initial={{opacity: 0}}
                    animate={{opacity: 1}}
                    transition={{delay: 0.5}}
                    className="flex flex-col sm:flex-row items-center justify-center gap-4"
                >
                    <Link
                        href="/blog"
                        className="group inline-flex items-center gap-2 px-8 py-4 bg-gray-900 dark:bg-white text-white dark:text-gray-900 font-semibold rounded-xl hover:bg-gray-800 dark:hover:bg-gray-100 transition-all hover:scale-105"
                    >
                        开始阅读
                        <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform"/>
                    </Link>

                    <Link
                        href="/categories"
                        className="inline-flex items-center gap-2 px-8 py-4 bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-white font-semibold rounded-xl hover:bg-gray-200 dark:hover:bg-gray-700 transition-all"
                    >
                        浏览分类
                    </Link>
                </motion.div>
            </div>

            {/* 滚动提示 */}
            <motion.div
                initial={{opacity: 0}}
                animate={{opacity: 1}}
                transition={{delay: 1}}
                className="absolute bottom-8 left-1/2 -translate-x-1/2"
            >
                <motion.div
                    animate={{y: [0, 10, 0]}}
                    transition={{duration: 2, repeat: Infinity}}
                    className="w-6 h-10 border-2 border-gray-400 dark:border-gray-600 rounded-full flex justify-center pt-2"
                >
                    <motion.div className="w-1 h-2 bg-gray-400 dark:bg-gray-600 rounded-full"/>
                </motion.div>
            </motion.div>
        </section>
    );
};

// 特色文章卡片
const FeaturedArticleCard: React.FC<{ article: Article; index: number }> = ({article, index}) => {
    return (
        <motion.article
            variants={fadeInUp}
            className="group relative bg-white dark:bg-gray-900 rounded-2xl overflow-hidden border border-gray-200 dark:border-gray-800 hover:border-gray-300 dark:hover:border-gray-700 transition-all hover:shadow-xl"
        >
            <Link href={`/blog/detail?slug=${article.slug}`} className="block">
                {/* 封面图 */}
                {article.cover_image && (
                    <div className="relative aspect-video overflow-hidden">
                        <Image
                            src={article.cover_image}
                            alt={article.title}
                            fill
                            className="object-cover group-hover:scale-105 transition-transform duration-500"
                            sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw"
                        />
                        <div
                            className="absolute inset-0 bg-gradient-to-t from-black/50 to-transparent opacity-0 group-hover:opacity-100 transition-opacity"/>
                    </div>
                )}

                {/* 内容 */}
                <div className="p-6">
                    {/* 标签 */}
                    {article.tags && article.tags.length > 0 && (
                        <div className="flex items-center gap-2 mb-3">
                            <span
                                className="px-3 py-1 bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400 text-xs font-medium rounded-full">
                                {article.tags[0]}
                            </span>
                        </div>
                    )}

                    <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-3 line-clamp-2 group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">
                        {article.title}
                    </h3>

                    <p className="text-gray-600 dark:text-gray-400 text-sm mb-4 line-clamp-2">
                        {article.excerpt || article.summary || '暂无摘要'}
                    </p>

                    {/* 元数据 */}
                    <div className="flex items-center justify-between text-sm text-gray-500 dark:text-gray-400">
                        <div className="flex items-center gap-4">
                            <span className="flex items-center gap-1">
                                <Clock className="w-4 h-4"/>
                                {article.created_at ? new Date(article.created_at).toLocaleDateString('zh-CN') : ''}
                            </span>
                            <span className="flex items-center gap-1">
                                <FileText className="w-4 h-4"/>
                                {Math.ceil((article.content?.length || 0) / 300)} 分钟
                            </span>
                        </div>

                        <div className="flex items-center gap-3">
                            <span className="flex items-center gap-1">
                                <TrendingUp className="w-4 h-4"/>
                                {article.views || 0}
                            </span>
                            <span className="flex items-center gap-1">
                                <Zap className="w-4 h-4"/>
                                {article.likes || 0}
                            </span>
                        </div>
                    </div>
                </div>
            </Link>
        </motion.article>
    );
};

// 最新文章列表项
const RecentArticleItem: React.FC<{ article: Article; index: number }> = ({article, index}) => {
    return (
        <motion.div
            variants={fadeInUp}
            className="group flex gap-6 p-6 bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-800 hover:border-gray-300 dark:hover:border-gray-700 transition-all hover:shadow-lg cursor-pointer"
            onClick={() => window.location.href = `/blog/detail?slug=${article.slug}`}
        >
            {/* 序号 */}
            <div
                className="hidden sm:flex items-center justify-center w-12 h-12 bg-gray-100 dark:bg-gray-800 rounded-xl font-bold text-gray-400 dark:text-gray-600">
                {String(index + 1).padStart(2, '0')}
            </div>

            {/* 封面图 */}
            {article.cover_image && (
                <div className="relative w-32 h-24 flex-shrink-0 rounded-xl overflow-hidden">
                    <Image
                        src={article.cover_image}
                        alt={article.title}
                        fill
                        className="object-cover group-hover:scale-105 transition-transform duration-500"
                        sizes="128px"
                    />
                </div>
            )}

            {/* 内容 */}
            <div className="flex-1 min-w-0">
                <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-2 line-clamp-2 group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">
                    {article.title}
                </h3>

                <p className="text-gray-600 dark:text-gray-400 text-sm mb-3 line-clamp-1">
                    {article.excerpt || article.summary || '暂无摘要'}
                </p>

                <div className="flex items-center gap-4 text-sm text-gray-500 dark:text-gray-400">
                    <span>{article.created_at ? new Date(article.created_at).toLocaleDateString('zh-CN') : ''}</span>
                    <span>·</span>
                    <span className="flex items-center gap-1">
                        <TrendingUp className="w-4 h-4"/>
                        {article.views || 0}
                    </span>
                </div>
            </div>

            <ChevronRight
                className="hidden sm:block w-5 h-5 text-gray-400 group-hover:text-blue-600 group-hover:translate-x-1 transition-all"/>
        </motion.div>
    );
};

// 分类卡片
const CategoryCard: React.FC<{ category: Category; index: number }> = ({category, index}) => {
    const colors = [
        'from-blue-500 to-cyan-500',
        'from-purple-500 to-pink-500',
        'from-green-500 to-emerald-500',
        'from-orange-500 to-red-500',
        'from-indigo-500 to-purple-500',
        'from-teal-500 to-blue-500',
    ];
    const color = colors[index % colors.length];

    return (
        <motion.div
            variants={fadeInUp}
            whileHover={{scale: 1.05}}
            className="group relative overflow-hidden rounded-2xl cursor-pointer"
        >
            <Link href={`/category/detail?name=${encodeURIComponent(category.name)}`} className="block">
                <div className={`aspect-square bg-gradient-to-br ${color} p-6 flex flex-col justify-between`}>
                    <div>
                        <h3 className="text-xl font-bold text-white mb-2">{category.name}</h3>
                        <p className="text-white/80 text-sm line-clamp-2">
                            {category.description || '探索更多精彩內容'}
                        </p>
                    </div>

                    <div className="flex items-center justify-between">
                        <span className="text-white/90 text-sm font-medium">
                            {category.article_count || 0} 篇文章
                        </span>
                        <ArrowRight className="w-5 h-5 text-white group-hover:translate-x-1 transition-transform"/>
                    </div>
                </div>
            </Link>
        </motion.div>
    );
};

// 主页面组件
const ModernHomePage: React.FC = () => {
    const [featuredArticles, setFeaturedArticles] = useState<Article[]>([]);
    const [recentArticles, setRecentArticles] = useState<Article[]>([]);
    const [categories, setCategories] = useState<Category[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const loadData = async () => {
            try {
                // 获取最新文章
                const recentResponse = await ArticleService.getHomeArticles({page: 1, per_page: 6});
                if (recentResponse.success && recentResponse.data) {
                    setRecentArticles(recentResponse.data.data || []);
                }

                // 获取精选文章（前3篇）
                const featuredResponse = await ArticleService.getHomeArticles({page: 1, per_page: 3});
                if (featuredResponse.success && featuredResponse.data) {
                    setFeaturedArticles(featuredResponse.data.data?.slice(0, 3) || []);
                }

                // 获取分类
                // 这里假设有 CategoryService，实际需要根据你的 API 调整
                // const categoryResponse = await CategoryService.getCategories({per_page: 6});
                // if (categoryResponse.success && categoryResponse.data) {
                //     setCategories(categoryResponse.data.categories || []);
                // }
            } catch (error) {
                console.error('加载首页数据失败:', error);
            } finally {
                setLoading(false);
            }
        };

        loadData();
    }, []);

    if (loading) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-white dark:bg-gray-950">
                <motion.div
                    animate={{rotate: 360}}
                    transition={{duration: 1, repeat: Infinity, ease: "linear"}}
                    className="w-12 h-12 border-4 border-blue-600 border-t-transparent rounded-full"
                />
            </div>
        );
    }

    return (
        <div className="bg-white dark:bg-gray-950">
            {/* Hero Section */}
            <HeroSection/>

            {/* 精选文章 */}
            {featuredArticles.length > 0 && (
                <section className="py-20 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto">
                    <motion.div
                        initial={{opacity: 0, y: 20}}
                        whileInView={{opacity: 1, y: 0}}
                        viewport={{once: true}}
                        className="mb-12"
                    >
                        <div className="flex items-center gap-2 mb-4">
                            <Sparkles className="w-5 h-5 text-blue-600 dark:text-blue-400"/>
                            <h2 className="text-3xl sm:text-4xl font-black text-gray-900 dark:text-white">
                                精选推荐
                            </h2>
                        </div>
                        <p className="text-gray-600 dark:text-gray-400">编辑精心挑选的优质内容</p>
                    </motion.div>

                    <motion.div
                        variants={staggerContainer}
                        initial="initial"
                        whileInView="animate"
                        viewport={{once: true}}
                        className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
                    >
                        {featuredArticles.map((article, index) => (
                            <FeaturedArticleCard key={article.id} article={article} index={index}/>
                        ))}
                    </motion.div>
                </section>
            )}

            {/* 最新文章 */}
            {recentArticles.length > 0 && (
                <section className="py-20 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto">
                    <motion.div
                        initial={{opacity: 0, y: 20}}
                        whileInView={{opacity: 1, y: 0}}
                        viewport={{once: true}}
                        className="mb-12"
                    >
                        <div className="flex items-center gap-2 mb-4">
                            <Clock className="w-5 h-5 text-purple-600 dark:text-purple-400"/>
                            <h2 className="text-3xl sm:text-4xl font-black text-gray-900 dark:text-white">
                                最新发布
                            </h2>
                        </div>
                        <p className="text-gray-600 dark:text-gray-400">第一时间获取新鲜内容</p>
                    </motion.div>

                    <motion.div
                        variants={staggerContainer}
                        initial="initial"
                        whileInView="animate"
                        viewport={{once: true}}
                        className="space-y-4"
                    >
                        {recentArticles.slice(0, 5).map((article, index) => (
                            <RecentArticleItem key={article.id} article={article} index={index}/>
                        ))}
                    </motion.div>

                    <motion.div
                        initial={{opacity: 0}}
                        whileInView={{opacity: 1}}
                        viewport={{once: true}}
                        className="mt-12 text-center"
                    >
                        <Link
                            href="/blog"
                            className="inline-flex items-center gap-2 px-8 py-4 bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-white font-semibold rounded-xl hover:bg-gray-200 dark:hover:bg-gray-700 transition-all"
                        >
                            查看更多文章
                            <ArrowRight className="w-5 h-5"/>
                        </Link>
                    </motion.div>
                </section>
            )}

            {/* CTA Section */}
            <section className="py-20 px-4 sm:px-6 lg:px-8">
                <div className="max-w-5xl mx-auto">
                    <motion.div
                        initial={{opacity: 0, scale: 0.95}}
                        whileInView={{opacity: 1, scale: 1}}
                        viewport={{once: true}}
                        className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-blue-600 to-purple-600 p-12 sm:p-16 text-center"
                    >
                        {/* 背景装饰 */}
                        <div className="absolute inset-0 opacity-20">
                            <div
                                className="absolute top-0 left-0 w-64 h-64 bg-white rounded-full blur-3xl -translate-x-1/2 -translate-y-1/2"/>
                            <div
                                className="absolute bottom-0 right-0 w-64 h-64 bg-white rounded-full blur-3xl translate-x-1/2 translate-y-1/2"/>
                        </div>

                        <div className="relative z-10">
                            <h2 className="text-3xl sm:text-4xl md:text-5xl font-black text-white mb-6">
                                准备好开始了吗？
                            </h2>
                            <p className="text-lg text-white/90 mb-8 max-w-2xl mx-auto">
                                加入我们的社区，与志同道合的人一起分享知识、交流想法
                            </p>

                            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
                                <Link
                                    href="/register"
                                    className="px-8 py-4 bg-white text-blue-600 font-bold rounded-xl hover:bg-gray-100 transition-all hover:scale-105"
                                >
                                    立即注册
                                </Link>
                                <Link
                                    href="/about"
                                    className="px-8 py-4 bg-white/10 backdrop-blur-sm text-white font-semibold rounded-xl hover:bg-white/20 transition-all border border-white/20"
                                >
                                    了解更多
                                </Link>
                            </div>
                        </div>
                    </motion.div>
                </div>
            </section>

            {/* Footer Spacer */}
            <div className="h-20"/>
        </div>
    );
};

export default ModernHomePage;
