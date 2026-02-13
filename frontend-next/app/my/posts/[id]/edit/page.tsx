'use client';

import React, {useEffect, useState} from 'react';
import {useParams, useRouter} from 'next/navigation';
import dynamic from 'next/dynamic';
import {ArticleService, Category} from '@/lib/api';
import LoadingState from '@/components/LoadingState';
import ErrorState from '@/components/ErrorState';
import AuthErrorBoundary from '@/components/AuthErrorBoundary';

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

const EditArticlePage = () => {
  const router = useRouter();
  const params = useParams();

  // 获取文章ID
  const articleId = params?.id
    ? (Array.isArray(params.id) ? params.id[0] : params.id)
    : null;

  const [categories, setCategories] = useState<Category[]>([]);
  const [initialData, setInitialData] = useState<ArticleData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // 加载文章数据
  useEffect(() => {
    const fetchArticleData = async () => {
      if (!articleId) {
        setError('文章ID未指定');
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
      return { success: false, error: '文章ID未指定' };
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

      const result = await ArticleService.updateArticle(articleId, form);
      return result;
    } catch (err) {
      console.error('更新文章失败:', err);
      return { success: false, error: '更新失败' };
    }
  };

  const handleCancel = () => {
    router.push(`/blog/${initialData?.slug || articleId}`);
  };

  if (loading) {
    return <LoadingState message="加载文章数据中..." />;
  }

  if (error) {
    // 使用认证错误边界包装，自动处理401错误
    return (
      <AuthErrorBoundary 
        error={error}
        onRetry={() => window.location.reload()}
        redirectPath={`/my/posts/${articleId}/edit`}
      >
        <ErrorState
          error={error}
          onRetry={() => window.location.reload()}
          secondaryAction={{
            label: '返回文章',
            onClick: () => router.push(`/blog/${initialData?.slug || articleId}`)
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
    <ArticleForm
      mode="edit"
      initialData={initialData}
      categories={categories}
      onSubmit={handleSubmit}
      onCancel={handleCancel}
      isLoading={loading}
    />
  );
};

export default EditArticlePage;