'use client';

import React, {Suspense, useEffect, useState} from 'react';
import {useRouter, useSearchParams} from 'next/navigation';
import dynamic from 'next/dynamic';
import {ArticleService, Category} from '@/lib/api';
import LoadingState from '@/components/LoadingState';
import ErrorState from '@/components/ErrorState';
import AuthErrorBoundary from '@/components/AuthErrorBoundary';
import {Button} from '@/components/ui/button';
import {Badge} from '@/components/ui/badge';
import {Users, Wifi, WifiOff} from 'lucide-react';

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
    const articleId = searchParams?.get('id');

  const [categories, setCategories] = useState<Category[]>([]);
  const [initialData, setInitialData] = useState<ArticleData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
    const [currentContent, setCurrentContent] = useState<string>('');
    const [showCollaboration, setShowCollaboration] = useState(false);
    const [collabDocId, setCollabDocId] = useState<string>('');

    // 监听获取编辑器内容的事件
    useEffect(() => {
        const handleGetEditorContent = (e: CustomEvent) => {
            console.log('收到getEditorContent事件，当前内容长度:', currentContent?.length);
            if (e.detail?.callback && typeof e.detail.callback === 'function') {
                console.log('调用回调函数...');
                e.detail.callback(currentContent);
            }
        };

        // 监听编辑器内容变化
        const handleContentChanged = (e: CustomEvent) => {
            console.log('收到editorContentChanged事件，新内容长度:', e.detail?.content?.length);
            setCurrentContent(e.detail?.content || '');
        };

        window.addEventListener('getEditorContent', handleGetEditorContent as EventListener);
        window.addEventListener('editorContentChanged', handleContentChanged as EventListener);
        console.log('已注册getEditorContent和editorContentChanged监听器');
        return () => {
            window.removeEventListener('getEditorContent', handleGetEditorContent as EventListener);
            window.removeEventListener('editorContentChanged', handleContentChanged as EventListener);
            console.log('已移除监听器');
        };
    }, [currentContent]);
      
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

          // 初始化当前内容
          setCurrentContent(content);
          console.log('初始化currentContent，长度:', content?.length);

          // 设置协作文档ID (使用文章ID)
          setCollabDocId(`article-${article.id}`);

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
    const handleSubmit = async (formData: ArticleData, createRevision?: boolean) => {
        // 更新当前内容
        setCurrentContent(formData.content);
        
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

        // 添加是否创建修订的参数
        form.append('create_revision', createRevision !== false ? 'true' : 'false');

      const result = await ArticleService.updateArticle(Number(articleId), form);

        // 如果是因为去重而跳过，也视为成功
        if (result.success && (result.data as any)?.skipped) {
            console.log('去重提示:', (result.data as any).message);
        }
      
      return result;
    } catch (err) {
      console.error('更新文章失败:', err);
      return { success: false, error: '更新失败' };
    }
  };

  const handleCancel = () => {
    router.push(`/blog/detail?slug=${initialData?.slug || articleId}`);
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
          {/* 协作编辑面板 */}
          {showCollaboration && collabDocId && (
              <div
                  className="fixed top-4 right-4 z-50 bg-white dark:bg-gray-800 rounded-lg shadow-lg p-4 border max-w-sm">
                  <div className="flex items-center justify-between mb-3">
                      <h3 className="font-semibold flex items-center gap-2">
                          <Users className="w-4 h-4"/>
                          协作编辑
                      </h3>
                      <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setShowCollaboration(false)}
                      >
                          ×
                      </Button>
                  </div>

                  <div className="space-y-3">
                      <div className="text-sm text-gray-600 dark:text-gray-400">
                          <p>文档ID: <code
                              className="bg-gray-100 dark:bg-gray-700 px-2 py-1 rounded">{collabDocId}</code></p>
                      </div>

                      <Button
                          className="w-full"
                          size="sm"
                          onClick={() => {
                              window.open(`/collaboration?doc=${collabDocId}`, '_blank');
                          }}
                      >
                          打开协作编辑器
                      </Button>

                      <p className="text-xs text-gray-500">
                          点击按钮在新窗口打开协作编辑器，可邀请多人同时编辑
                      </p>
                  </div>
              </div>
          )}

          {/* 协作编辑按钮 */}
          <div className="fixed bottom-4 right-4 z-40">
              <Button
                  variant={showCollaboration ? "default" : "secondary"}
                  size="sm"
                  onClick={() => setShowCollaboration(!showCollaboration)}
                  className="shadow-lg"
              >
                  <Users className="w-4 h-4 mr-2"/>
                  协作编辑
              </Button>
          </div>
          
          <ArticleForm
              mode="edit"
              initialData={initialData}
              categories={categories}
              onSubmit={handleSubmit}
              onCancel={handleCancel}
              articleId={articleId ? Number(articleId) : null}
              isLoading={loading}
          />
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
