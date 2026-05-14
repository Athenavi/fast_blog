'use client';

import React, {useCallback, useEffect, useRef, useState} from 'react';
import Link from 'next/link';
import Image from 'next/image';
import tocbot from 'tocbot';
import {ArticleService} from '@/lib/api';
import type {ArticleDetailResponse} from '@/lib/api/article-service';
import CommentSection from '@/components/CommentSection';
import Breadcrumbs from '@/components/Breadcrumbs';
import ArticleSchema from '@/components/ArticleSchema';
import PasswordProtectedArticle from '@/components/PasswordProtectedArticle';
import LoadingState from '@/components/LoadingState';

// 工具函数移到组件外部，避免重复创建
const formatDate = (dateString: string) => {
  const date = new Date(dateString);
  return date.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });
};

const estimateReadTime = (content: string) => {
  const text = content.replace(/<[^>]*>/g, '');
  return Math.ceil(text.length / 300);
};

// 为标题元素添加 ID（如果还没有的话）
const addHeadingIds = (contentElement: HTMLElement) => {
  const headings = contentElement.querySelectorAll('h1, h2, h3, h4, h5, h6');
  const idCounts: Record<string, number> = {};

  headings.forEach((heading) => {
      const h = heading as unknown as HTMLElement;
    if (!h.id) {
      // 从标题文本生成 ID
      const text = h.textContent || '';
      let baseId = text
          .toLowerCase()
          .replace(/[\s\u4e00-\u9fa5]+/g, '') // 将空格和中文替换为连字符
          .replace(/[^a-z0-9-]/g, '') // 移除特殊字符
          .replace(/-+/g, '') // 合并多个连字符
          .replace(/^-|-$/g, ''); // 移除首尾连字符

      // 如果生成的 ID 为空，使用默认值
      if (!baseId) {
        baseId = 'heading';
      }

      // 处理重复 ID
      if (idCounts[baseId]) {
        idCounts[baseId]++;
        h.id = `${baseId}-${idCounts[baseId]}`;
      } else {
        idCounts[baseId] = 1;
        h.id = baseId;
      }
    }
  });

  console.log(`✅ 已为 ${headings.length} 个标题添加 ID`);
};

interface PasswordArticleInfo {
  article_id: number;
  article_title: string;
  excerpt: string;
}

interface BlogDetailContentProps {
  slug: string;
}

const ArticleDetail: React.FC<{ articleData: ArticleDetailResponse }> = ({articleData}) => {
  const {article, author} = articleData;
  const articleId = articleData.article_id || article.id;
  const [likes, setLikes] = useState(article.likes || 0);
  const [hasLiked, setHasLiked] = useState(false);
  const [showMobileToc, setShowMobileToc] = useState(false);
  const contentRef = useRef<HTMLDivElement>(null);

  const breadcrumbs = React.useMemo(() => {
    const items: Array<{ name: string; url: string | null; position: number }> = [
      {name: '首页', url: '/', position: 1},
    ];
    if (article.category_name) {
      items.push({
        name: article.category_name,
        url: `/categories/${article.category_slug || article.category_id || ''}`,
        position: 2,
      });
    }
    items.push({
      name: article.title,
      url: null,
      position: article.category_name ? 3 : 2,
    });
    return items;
  }, [article.category_name, article.category_slug, article.category_id, article.title]);

  const handleLike = useCallback(async () => {
    if (hasLiked) return;
    setLikes((prev) => prev + 1);
    setHasLiked(true);
    try {
      await fetch(`/api/articles/${articleId}/like`, {method: 'POST'});
    } catch (error) {
      // 静默处理，UI 不回滚以保持体验
      console.error('点赞失败:', error);
    }
  }, [hasLiked, articleId]);

  // 改进的目录初始化：增加重试机制和更好的错误处理
  useEffect(() => {
    if (!article.content) return;

    let retryCount = 0;
    const maxRetries = 5;

    const initToc = () => {
      const contentElement = contentRef.current;
      // 查找所有目录容器（移动端和桌面端）
      const tocContainers = document.querySelectorAll('.js-toc');

      if (!contentElement || tocContainers.length === 0) {
        if (retryCount < maxRetries) {
          retryCount++;
          setTimeout(initToc, 300 * retryCount); // 递增延迟重试
        }
        return;
      }

      // 检查是否有标题元素
      const headings = contentElement.querySelectorAll('h1, h2, h3, h4, h5, h6');
      if (headings.length === 0) {
        tocContainers.forEach(container => {
          container.innerHTML = '<p class="text-gray-500 text-sm py-4">本文无结构化标题</p>';
        });
        return;
      }

      try {
        // 先为标题添加 ID（如果还没有）
        addHeadingIds(contentElement);
        
        // 先销毁之前的实例
        tocbot.destroy();

        // 初始化新的 tocbot 实例
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
          onClick: (e: Event) => {
            e.preventDefault();
            const target = (e.target as HTMLAnchorElement).getAttribute('href')?.substring(1);
            if (target) {
              const element = document.getElementById(target);
              if (element) {
                try {
                  element.scrollIntoView({behavior: 'smooth', block: 'center'});
                  // 添加高亮效果
                  element.style.backgroundColor = 'rgba(59, 130, 246, 0.1)';
                  setTimeout(() => {
                    element.style.backgroundColor = '';
                  }, 1000);
                } catch (error) {
                  console.error('滚动到目标元素失败:', error);
                }
              } else {
                console.warn(`未找到ID为 "${target}" 的元素`);
              }
            }
          },
        });

        console.log('✅ 目录初始化成功');
        console.log('找到标题数量:', headings.length);
      } catch (error) {
        console.error('❌ 目录初始化失败:', error);
        tocContainers.forEach(container => {
          container.innerHTML = '<p class="text-gray-500 text-sm py-4">目录生成失败，请刷新页面</p>';
        });
      }
    };

    // 延迟初始化以确保 DOM 完全渲染
    const timer = setTimeout(initToc, 500);

    return () => {
      clearTimeout(timer);
      try {
        tocbot.destroy();
      } catch {
      }
    };
  }, [article.content]); // 移除 showMobileToc 依赖以避免不必要的重新渲染

  return (
      <div className="min-h-screen bg-white dark:bg-gray-950 transition-colors duration-300">
        <header className="relative border-b border-gray-200 dark:border-gray-800 overflow-hidden">
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
                <div
                    className="absolute inset-0 bg-gradient-to-b from-black/40 via-black/60 to-white dark:to-gray-950"/>
              </div>
          )}

          <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16 sm:py-24">
            <nav className="mb-6" aria-label="Breadcrumb">
              <Breadcrumbs items={breadcrumbs}/>
            </nav>

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

            <h1 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-white leading-tight mb-6 drop-shadow-lg">
              {article.title}
            </h1>

            {article.excerpt && (
                <p className="text-lg sm:text-xl text-white/90 leading-relaxed mb-8 drop-shadow-md">
                  {article.excerpt}
                </p>
            )}

            <div className="flex flex-wrap items-center gap-4 sm:gap-6">
              <div className="flex items-center gap-3">
                <div
                    className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-purple-500 flex items-center justify-center text-white font-semibold ring-2 ring-white/50">
                  {author?.username?.charAt(0).toUpperCase() || 'U'}
                </div>
                <div>
                  <div className="text-sm font-medium text-white">{author?.username || '未知作者'}</div>
                  <div className="text-xs text-white/80">{formatDate(article.created_at)}</div>
                </div>
              </div>

              <div className="hidden sm:block w-px h-10 bg-white/30"/>

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

        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
          {/* 移动端目录切换按钮 */}
          <div className="lg:hidden mb-6">
            <button
                onClick={() => setShowMobileToc(!showMobileToc)}
                className="w-full flex items-center justify-between px-4 py-3 bg-gray-100 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700"
            >
              <span className="font-medium text-gray-900 dark:text-white">文章目录</span>
              <svg
                  className={`w-5 h-5 text-gray-500 transition-transform ${showMobileToc ? 'rotate-180' : ''}`}
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7"/>
              </svg>
            </button>

            {/* 移动端目录内容 */}
            {showMobileToc && (
                <div
                    className="mt-2 bg-gray-50 dark:bg-gray-900 rounded-lg p-4 border border-gray-200 dark:border-gray-800 max-h-96 overflow-y-auto">
                  <div className="js-toc toc-container"/>
                </div>
            )}
          </div>

          <div className="lg:grid lg:grid-cols-12 lg:gap-12">
            <article className="lg:col-span-9 xl:col-span-10">
              <div
                  ref={contentRef}
                  className="article-content prose prose-lg dark:prose-invert max-w-none"
                  dangerouslySetInnerHTML={{__html: article.content || ''}}
              />

              {Array.isArray(article.tags) && article.tags.length > 0 && (
                  <div className="mt-12 pt-8 border-t border-gray-200 dark:border-gray-800">
                    <div className="flex flex-wrap gap-2">
                      {article.tags.map((tag: string) => (
                          <Link
                              key={tag}
                              href={`/tags/${tag}`}
                              className="inline-flex items-center px-3 py-1.5 rounded-full text-sm font-medium bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700 transition-colors"
                          >
                            #{tag}
                          </Link>
                      ))}
                    </div>
                  </div>
              )}

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
                    <svg className={`w-5 h-5 ${hasLiked ? 'fill-current' : ''}`} fill="none" stroke="currentColor"
                         viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                            d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z"/>
                    </svg>
                    <span>{likes}</span>
                  </button>

                  <div className="flex items-center gap-3">
                    <button
                        onClick={() => {
                          if (navigator.share) {
                            navigator.share({title: article.title, url: window.location.href}).catch(console.error);
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

              <div className="mt-12">
                <CommentSection articleId={articleId}/>
              </div>
            </article>

            <aside className="lg:col-span-3 xl:col-span-2">
              <div className="sticky top-8">
                <div
                    className="bg-gray-50 dark:bg-gray-900 rounded-xl p-6 border border-gray-200 dark:border-gray-800 max-h-[calc(100vh-8rem)] overflow-y-auto">
                  <h3 className="text-sm font-semibold text-gray-900 dark:text-white uppercase tracking-wider mb-4">
                    目录
                  </h3>
                  <div className="js-toc toc-container"/>
                </div>
              </div>
            </aside>
          </div>
        </main>
      </div>
  );
};

const BlogDetailContent: React.FC<BlogDetailContentProps> = ({slug}) => {
  const [articleData, setArticleData] = useState<ArticleDetailResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [requiresPassword, setRequiresPassword] = useState(false);
  const [passwordArticleInfo, setPasswordArticleInfo] = useState<{
    article_id: number;
    article_title: string;
    excerpt: string;
  } | null>(null);

  // 使用 useRef 来跟踪当前 slug，避免不必要的重复请求
  const prevSlugRef = useRef<string | null>(null);

  // 提取 fetchArticle 函数以便复用
  const fetchArticle = useCallback(async () => {
    if (!slug) return;

    try {
      setLoading(true);
      const response = await ArticleService.getArticleBySlug(slug);

      if (response.success && response.data) {
        setArticleData(response.data);
        setRequiresPassword(false);
      } else {
        const data = response.data as { requires_password?: boolean } & Partial<PasswordArticleInfo>;
        if (response.error === 'Password required' && data?.requires_password) {
          setRequiresPassword(true);
          setPasswordArticleInfo({
            article_id: data.article_id!,
            article_title: data.article_title!,
            excerpt: data.excerpt!,
          });
        } else {
          setError(response.error || '文章不存在');
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载失败');
    } finally {
      setLoading(false);
    }
  }, [slug]);

  useEffect(() => {
    // 如果 slug 没有变化且已有数据，不重新请求
    if (prevSlugRef.current === slug && articleData) {
      return;
    }

    prevSlugRef.current = slug;
    fetchArticle();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [slug, fetchArticle]);

  if (loading) return <LoadingState message="加载文章中..."/>;

  if (requiresPassword && passwordArticleInfo) {
    return (
        <div className="min-h-screen py-12 px-4">
          <PasswordProtectedArticle
              articleId={passwordArticleInfo.article_id}
              onPasswordVerified={() => {
                setRequiresPassword(false);
                setPasswordArticleInfo(null);
                // 重新获取文章数据，而不是刷新整个页面
                fetchArticle();
              }}
          />
        </div>
    );
  }

  if (error || !articleData) {
    return (
        <div className="min-h-screen flex items-center justify-center">
          <div className="text-center">
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">{error || '文章不存在'}</h2>
            <p className="text-gray-600 dark:text-gray-400">请检查链接是否正确</p>
          </div>
        </div>
    );
  }

  return (
      <>
        <ArticleSchema article={articleData}/>
        <ArticleDetail articleData={articleData as ArticleDetailResponse}/>
      </>
  );
};

export default BlogDetailContent;