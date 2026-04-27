'use client';

import React, {Suspense, useEffect, useState} from 'react';
import {useRouter, useSearchParams} from 'next/navigation';
import dynamic from 'next/dynamic';
import {ArticleService, Category} from '@/lib/api';
import LoadingState from '@/components/LoadingState';
import ErrorState from '@/components/ErrorState';
import AuthErrorBoundary from '@/components/AuthErrorBoundary';
import ArticleRevisionsSidebar from '@/components/ArticleRevisionsSidebar';

// 动态导入表单组件
const ArticleForm = dynamic(
  () => import('@/components/ArticleForm'),
  {
    ssr: false,
    loading: () => <LoadingState message="加载表单中..." />
  }
);

interface ArticleData {
  id?: number;
  title: string;
  slug: string;
  excerpt: string;
  content: string;
  cover_image: string;
  tags: string[];
  status: number;
  hidden: boolean;
  is_vip_only: boolean;
  required_vip_level: number;
  article_ad: string;
  is_featured: boolean;
  category_id: number | null;
}

// EditArticlePage 内部组件 - 使用 searchParams
const EditArticlePageContent = () => {
  const router = useRouter();
  const searchParams = useSearchParams();

  // 使用 searchParams 获取查询参数
  const articleId = searchParams.get('id');

  const [categories, setCategories] = useState<Category[]>([]);
  const [initialData, setInitialData] = useState<ArticleData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
    const [showRevisionsSidebar, setShowRevisionsSidebar] = useState(false);

  // 加载文章数据
  useEffect(() => {
    const fetchArticleData = async () => {
      if (!articleId) {
        setError('文章 ID 未指定');
        setLoading(false);
        return;
      }

      try {
        const result = await ArticleService.getEditArticleData(Number(articleId));

        if (!result.success || !result.data) {
          throw new Error(result.error || '获取文章数据失败');
        }

        const article = result.data.article;
        const content = result.data.content || '';

        if (!article) {
          throw new Error('文章数据不存在');
        }

        // 确保 article.tags 是可访问的
        const articleTags = article.tags;

        // 转换标签格式
        const tags = Array.isArray(article.tags)
          ? article.tags as string[]
          : typeof article.tags === 'string'
            ? (article.tags as string).split(',').filter(Boolean).map(t => t.trim())
            : [];

        setInitialData({
          id: article.id,
          title: article.title || '',
          slug: article.slug || '',
          excerpt: article.excerpt || '',
          content: content,
          cover_image: article.cover_image || '',
          tags: tags,
          status: article.status ?? 0,
          hidden: Boolean(article.hidden),
          is_vip_only: Boolean(article.is_vip_only),
          required_vip_level: article.required_vip_level || 0,
          article_ad: article.article_ad || '',
          is_featured: Boolean(article.is_featured),
          category_id: article.category_id ?? null
        });

        setCategories(result.data.categories || []);
      } catch (err) {
        console.error('加载文章失败:', err);
        setError(err instanceof Error ? err.message : '加载文章失败');
      } finally {
        setLoading(false);
      }
    };

    fetchArticleData();
  }, [articleId]);

  // 处理表单提交
  const handleSubmit = async (formData: ArticleData) => {
    if (!articleId) {
      return { success: false, error: '文章 ID 未指定' };
    }

    try {
      const form = new FormData();

      Object.entries(formData).forEach(([key, value]) => {
        if (key === 'tags') {
          form.append(key, (value as string[]).join(','));
        } else if (['hidden', 'is_vip_only', 'is_featured'].includes(key)) {
          form.append(key, value ? '1' : '0');
        } else {
          form.append(key, String(value ?? ''));
        }
      });

      const result = await ArticleService.updateArticle(Number(articleId), form);
      return result;
    } catch (err) {
      console.error('更新文章失败:', err);
      return { success: false, error: '更新失败' };
    }
  };

  const handleCancel = () => {
    router.push(`/blog/detail?slug=${initialData?.slug || articleId}`);
  };

    const handleViewRevisions = () => {
        setShowRevisionsSidebar(true);
    };

    // 回滚完成后刷新文章数据
    const handleRollbackComplete = async () => {
        if (!articleId) return;

        try {
            setLoading(true);
            const result = await ArticleService.getEditArticleData(Number(articleId));

            if (result.success && result.data) {
                const article = result.data.article;
                const content = result.data.content || '';

                if (!article) {
                    console.error('文章数据不存在');
                    return;
                }

                const tags = Array.isArray(article.tags)
                    ? article.tags as string[]
                    : typeof article.tags === 'string'
                        ? (article.tags as string).split(',').filter(Boolean).map(t => t.trim())
                        : [];

                setInitialData({
                    id: article.id,
                    title: article.title || '',
                    slug: article.slug || '',
                    excerpt: article.excerpt || '',
                    content: content,
                    cover_image: article.cover_image || '',
                    tags: tags,
                    status: article.status ?? 0,
                    hidden: Boolean(article.hidden),
                    is_vip_only: Boolean(article.is_vip_only),
                    required_vip_level: article.required_vip_level || 0,
                    article_ad: article.article_ad || '',
                    is_featured: Boolean(article.is_featured),
                    category_id: article.category_id ?? null
                });
            }
        } catch (err) {
            console.error('刷新文章数据失败:', err);
        } finally {
            setLoading(false);
        }
    };

  if (loading) {
    return <LoadingState message="加载文章数据中..." />;
  }

  if (error) {
    // 使用认证错误边界包装，自动处理 401 错误
    return (
      <AuthErrorBoundary 
        error={error}
        retryAction={() => window.location.reload()}
        redirectPath={`/my/posts/edit?id=${articleId}`}
      >
        <ErrorState
          error={error}
          retryAction={() => window.location.reload()}
          secondaryAction={{
            label: '返回文章',
            onClick: () => router.push(`/blog/detail?slug=${initialData?.slug || articleId}`)
          }}
          type={error.includes('401') ? 'warning' : 'error'}
        />
      </AuthErrorBoundary>
    );
  }

  if (!initialData) {
    return <ErrorState error="文章数据不存在" />;
  }

  return (
      <>
          <ArticleForm
              mode="edit"
              initialData={initialData}
              categories={categories}
              onSubmit={handleSubmit}
              onCancel={handleCancel}
              onViewRevisions={handleViewRevisions}
              isLoading={loading}
          />

          {/* 修订历史侧边栏 */}
          {articleId && (
              <ArticleRevisionsSidebar
                  articleId={Number(articleId)}
                  isOpen={showRevisionsSidebar}
                  onClose={() => setShowRevisionsSidebar(false)}
                  onRollbackComplete={handleRollbackComplete}
              />
          )}
      </>
  );
};

// 主页面组件 - 用 Suspense 包装
const EditArticlePage: React.FC = () => {
  return (
      <Suspense fallback={<LoadingState message="加载编辑器中..."/>}>
        <EditArticlePageContent/>
      </Suspense>
  );
};

export default EditArticlePage;
