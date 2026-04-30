'use client';

import React, {useEffect, useRef, useState} from 'react';
import Link from 'next/link';
import Image from 'next/image';
import tocbot from 'tocbot';
import {ArticleDetailResponse} from "@/lib/api/article-service";
import CommentSection from '@/components/CommentSection';
import Breadcrumbs from '@/components/Breadcrumbs';

interface ArticleDetailClientProps {
    articleData: ArticleDetailResponse;
}

const ArticleDetailClient: React.FC<ArticleDetailClientProps> = ({articleData}) => {
    const {article, author, i18n_versions = [], aid} = articleData;

    // 确保获取正确的文章ID - 优先使用 article_id（从 URL 注入），然后 fallback 到其他字段
    const articleId = articleData?.article_id || article?.id || aid;

    const [likes, setLikes] = useState<number>(article.likes || 0);
    const [hasLiked, setHasLiked] = useState<boolean>(false);
    const contentRef = useRef<HTMLDivElement>(null);

    // 生成面包屑数据
    const breadcrumbs = [
        {name: '首页', url: '/', position: 1},
        ...(article.category_name ? [{
            name: article.category_name,
            url: `/categories/${article.category_slug || article.category_id || ''}`,
            position: 2
        }] : []),
        {
            name: article.title,
            url: null,
            position: article.category_name ? 3 : 2
        }
    ];

    // 处理点赞
    const handleLike = async () => {
        if (hasLiked) return;

        setLikes(prev => prev + 1);
        setHasLiked(true);

        try {
            const response = await fetch(`/api/articles/${articleId}/like`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
            });

            if (!response.ok) {
                setLikes(prev => prev - 1);
                setHasLiked(false);
            }
        } catch (error) {
            console.error('点赞失败:', error);
            setLikes(prev => prev - 1);
            setHasLiked(false);
        }
    };

    // 初始化目录
    useEffect(() => {
        if (typeof window === 'undefined' || !article.content) return;

        let initAttempts = 0;
        const maxAttempts = 8;

        const tryInitializeToc = () => {
            initAttempts++;
            const contentElement = contentRef.current;
            const tocContainer = document.querySelector('.js-toc');

            if (!contentElement || !tocContainer) return false;
            if (!contentElement.innerHTML?.trim()) return false;

            const headings = contentElement.querySelectorAll('h1, h2, h3, h4, h5, h6');

            if (headings.length === 0) {
                tocContainer.innerHTML = '<p class="text-gray-500 text-sm py-4">本文无结构化标题</p>';
                return true;
            }

            try {
                tocbot.init({
                    tocSelector: '.js-toc',
                    contentSelector: '.article-content',
                    headingSelector: 'h1, h2, h3, h4, h5, h6',
                    includeHtml: true,
                    headingsOffset: 10,
                    ignoreSelector: '.js-toc-ignore',
                    linkClass: 'toc-link',
                    activeLinkClass: 'is-active-link',
                    listClass: 'toc-list',
                    listItemClass: 'toc-list-item',
                    collapseDepth: 0,
                    orderedList: false,
                    onClick: function (e) {
                        e.preventDefault();
                        const target = e.target as HTMLAnchorElement;
                        const targetId = target.getAttribute('href')?.substring(1);
                        if (targetId) {
                            const targetElement = document.getElementById(targetId);
                            if (targetElement) {
                                targetElement.scrollIntoView({behavior: 'smooth', block: 'center'});
                                targetElement.style.backgroundColor = 'rgba(59, 130, 246, 0.1)';
                                setTimeout(() => {
                                    targetElement.style.backgroundColor = '';
                                }, 1000);
                            }
                        }
                    }
                });
                console.log('✅ 目录初始化成功');
                return true;
            } catch (error) {
                console.error('Tocbot 初始化失败:', error);
                return false;
            }
        };

        const scheduleInit = () => {
            if (initAttempts >= maxAttempts) {
                const tocContainer = document.querySelector('.js-toc');
                if (tocContainer) {
                    tocContainer.innerHTML = '<p class="text-gray-500 text-sm py-4">目录生成失败</p>';
                }
                return;
            }

            requestAnimationFrame(() => {
                if (!tryInitializeToc()) {
                    const delay = Math.min(500 * Math.pow(1.5, initAttempts), 3000);
                    setTimeout(scheduleInit, delay);
                }
            });
        };

        const initTimer = setTimeout(scheduleInit, 1000);

        return () => {
            clearTimeout(initTimer);
            try {
                tocbot.destroy();
            } catch (error) {
                console.warn('清理 Tocbot 时出错:', error);
            }
        };
    }, [article.content]);

    // 格式化日期
    const formatDate = (dateString: string) => {
        const date = new Date(dateString);
        return date.toLocaleDateString('zh-CN', {
            year: 'numeric',
            month: 'long',
            day: 'numeric'
        });
    };

    // 阅读时间估算
    const estimateReadTime = (content: string) => {
        const words = content.replace(/<[^>]*>/g, '').length;
        const minutes = Math.ceil(words / 300); // 假设每分钟阅读300字
        return minutes;
    };

    return (
        <div className="min-h-screen bg-white dark:bg-gray-950">
            {/* 文章头部 - 带背景图 */}
            <header className="relative border-b border-gray-200 dark:border-gray-800 overflow-hidden">
                {/* 背景图 */}
                {article.cover_image && (
                    <div className="absolute inset-0 z-0">
                        <Image
                            src={article.cover_image}
                            alt={article.title}
                            fill
                            className="object-cover"
                            priority
                            sizes="100vw"
                        />
                        {/* 渐变遮罩 - 从半透明到完全不透明 */}
                        <div
                            className="absolute inset-0 bg-gradient-to-b from-black/40 via-black/60 to-white dark:from-black/60 dark:via-black/70 dark:to-gray-950"/>
                    </div>
                )}

                <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16 sm:py-24">
                    {/* 面包屑导航 */}
                    <nav className="mb-6" aria-label="Breadcrumb">
                        <Breadcrumbs items={breadcrumbs}/>
                    </nav>

                    {/* 分类标签 */}
                    {article.category_name && (
                        <div className="mb-6">
                            <Link
                                href={`/categories/${article.category_slug || article.category_id}`}
                                className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-white/90 backdrop-blur-sm text-blue-700 hover:bg-white dark:bg-gray-900/90 dark:text-blue-300 dark:hover:bg-gray-900 transition-colors shadow-lg"
                            >
                                {article.category_name}
                            </Link>
                        </div>
                    )}

                    {/* 标题 */}
                    <h1 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-white leading-tight mb-6 drop-shadow-lg">
                        {article.title}
                    </h1>

                    {/* 摘要 */}
                    {article.excerpt && (
                        <p className="text-lg sm:text-xl text-white/90 leading-relaxed mb-8 drop-shadow-md">
                            {article.excerpt}
                        </p>
                    )}

                    {/* 作者信息和元数据 */}
                    <div className="flex flex-wrap items-center gap-4 sm:gap-6">
                        {/* 作者 */}
                        <div className="flex items-center gap-3">
                            <div
                                className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-purple-500 flex items-center justify-center text-white font-semibold ring-2 ring-white/50">
                                {author?.username?.charAt(0).toUpperCase() || 'U'}
                            </div>
                            <div>
                                <div className="text-sm font-medium text-white">
                                    {author?.username || '未知作者'}
                                </div>
                                <div className="text-xs text-white/80">
                                    {formatDate(article.created_at)}
                                </div>
                            </div>
                        </div>

                        {/* 分隔符 */}
                        <div className="hidden sm:block w-px h-10 bg-white/30"/>

                        {/* 阅读时间和浏览量 */}
                        <div className="flex items-center gap-4 text-sm text-white/80">
                            <span className="flex items-center gap-1">
                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                                          d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/>
                                </svg>
                                {estimateReadTime(article.content || '')} 分钟阅读
                            </span>
                            <span className="flex items-center gap-1">
                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                                          d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                                          d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/>
                                </svg>
                                {article.views}
                            </span>
                        </div>
                    </div>
                </div>
            </header>

            {/* 文章内容区域 */}
            <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">

                {/* 文章内容 */}
                <div className="lg:grid lg:grid-cols-12 lg:gap-12">
                    {/* 主内容区 */}
                    <article className="lg:col-span-9 xl:col-span-10">

                        {/* 文章内容 */}
                        <div
                            ref={contentRef}
                            className="article-content prose prose-lg dark:prose-invert max-w-none
                                prose-headings:font-bold prose-headings:text-gray-900 dark:prose-headings:text-white
                                prose-h1:text-3xl prose-h2:text-2xl prose-h3:text-xl
                                prose-p:text-gray-700 dark:prose-p:text-gray-300 prose-p:leading-relaxed
                                prose-a:text-blue-600 dark:prose-a:text-blue-400 prose-a:no-underline hover:prose-a:underline
                                prose-blockquote:border-l-4 prose-blockquote:border-blue-500 prose-blockquote:pl-4 prose-blockquote:italic
                                prose-code:bg-gray-100 dark:prose-code:bg-gray-800 prose-code:px-2 prose-code:py-1 prose-code:rounded
                                prose-pre:bg-gray-900 dark:prose-pre:bg-gray-800 prose-pre:text-gray-100
                                prose-img:rounded-lg prose-img:shadow-lg
                                prose-strong:font-semibold prose-strong:text-gray-900 dark:prose-strong:text-white"
                            dangerouslySetInnerHTML={{__html: article.content || ''}}
                        />

                        {/* 标签 */}
                        {article.tags && Array.isArray(article.tags) && article.tags.length > 0 && (
                            <div className="mt-12 pt-8 border-t border-gray-200 dark:border-gray-800">
                                <div className="flex flex-wrap gap-2">
                                    {article.tags.map((tag, index) => (
                                        <Link
                                            key={index}
                                            href={`/tags/${tag}`}
                                            className="inline-flex items-center px-3 py-1.5 rounded-full text-sm font-medium bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700 transition-colors"
                                        >
                                            #{tag}
                                        </Link>
                                    ))}
                                </div>
                            </div>
                        )}

                        {/* 互动按钮 */}
                        <div className="mt-12 pt-8 border-t border-gray-200 dark:border-gray-800">
                            <div className="flex items-center justify-between">
                                <button
                                    type="button"
                                    onClick={handleLike}
                                    disabled={hasLiked}
                                    className={`flex items-center gap-2 px-6 py-3 rounded-full font-medium transition-all ${
                                        hasLiked
                                            ? 'bg-red-50 text-red-600 dark:bg-red-900/30 dark:text-red-400'
                                            : 'bg-gray-100 text-gray-700 hover:bg-red-50 hover:text-red-600 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-red-900/30 dark:hover:text-red-400'
                                    }`}
                                >
                                    <svg className={`w-5 h-5 ${hasLiked ? 'fill-current' : ''}`} fill="none"
                                         stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                                              d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z"/>
                                    </svg>
                                    <span>{likes}</span>
                                </button>

                                {/* 分享按钮 */}
                                <div className="flex items-center gap-3">
                                    <button
                                        onClick={() => {
                                            if (navigator.share) {
                                                navigator.share({
                                                    title: article.title,
                                                    url: window.location.href
                                                }).catch(console.error);
                                            } else {
                                                navigator.clipboard.writeText(window.location.href);
                                            }
                                        }}
                                        className="p-3 rounded-full bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700 transition-colors"
                                        title="分享"
                                    >
                                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                                                  d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z"/>
                                        </svg>
                                    </button>
                                </div>
                            </div>
                        </div>

                        {/* 评论区 */}
                        <div className="mt-12">
                            <CommentSection articleId={articleId}/>
                        </div>
                    </article>

                    {/* 侧边栏 - 目录 */}
                    <aside className="hidden lg:block lg:col-span-3 xl:col-span-2">
                        <div className="sticky top-8">
                            {/* 简单的目录容器 */}
                            <div
                                className="bg-gray-50 dark:bg-gray-900 rounded-xl p-6 border border-gray-200 dark:border-gray-800">
                                <h3 className="text-sm font-semibold text-gray-900 dark:text-white uppercase tracking-wider mb-4">
                                    目录
                                </h3>
                                <div className="js-toc toc-container">
                                    <style jsx>{`
                                        .toc-list {
                                            list-style: none;
                                            padding: 0;
                                            margin: 0;
                                            space-y: 0.5rem;
                                        }

                                        .toc-list-item {
                                            margin-bottom: 0.5rem;
                                        }

                                        .toc-link {
                                            display: block;
                                            padding: 0.25rem 0;
                                            font-size: 0.875rem;
                                            line-height: 1.5;
                                            word-break: break-word;
                                            color: rgb(55 65 81);
                                            transition: color 0.2s;
                                        }

                                        .toc-link:hover {
                                            color: rgb(37 99 235);
                                        }

                                        .is-active-link {
                                            color: rgb(37 99 235);
                                            font-weight: 600;
                                        }

                                        .dark .toc-link {
                                            color: rgb(209 213 219);
                                        }

                                        .dark .toc-link:hover,
                                        .dark .is-active-link {
                                            color: rgb(96 165 250);
                                        }
                                    `}</style>
                                </div>
                            </div>
                        </div>
                    </aside>
                </div>
            </main>
        </div>
    );
};

export default ArticleDetailClient;
