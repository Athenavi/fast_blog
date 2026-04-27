'use client';

import React, {Suspense, useEffect, useState} from 'react';
import {notFound, useSearchParams} from 'next/navigation';
import {ArticleService} from '@/lib/api';
import ArticleDetailClient from '@/components/ArticleDetailClient';
import LoadingState from '@/components/LoadingState';
import ErrorState from '@/components/ErrorState';
import PasswordProtectedArticle from '@/components/PasswordProtectedArticle';

// 文章内容组件
const ArticleContent: React.FC = () => {
  const searchParams = useSearchParams();
  const articleId = searchParams.get('id');

  const [articleData, setArticleData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [requiresPassword, setRequiresPassword] = useState(false);
  const [passwordArticleInfo, setPasswordArticleInfo] = useState<{article_id: number; article_title: string; excerpt: string} | null>(null);

  useEffect(() => {
    if (!articleId) {
      notFound();
      return;
    }

    const fetchArticle = async () => {
      try {
        setLoading(true);
        const response = await ArticleService.getArticleWithI18n(articleId);

        if (response.success && response.data) {
          setArticleData(response.data);
          setRequiresPassword(false);
        } else {
          // 检查是否需要密码
            const responseData = response.data as any;
            if (response.error === 'Password required' && responseData?.requires_password) {
            setRequiresPassword(true);
            setPasswordArticleInfo({
                article_id: responseData.article_id,
                article_title: responseData.article_title,
                excerpt: responseData.excerpt
            });
          } else {
            setError('文章不存在');
            setRequiresPassword(false);
          }
        }
      } catch (err) {
        console.error('获取文章时发生错误:', err);
        setError('加载失败');
      } finally {
        setLoading(false);
      }
    };

    fetchArticle();
  }, [articleId]);

  if (loading) {
    return <LoadingState/>;
  }

  // 如果需要密码验证，显示密码输入界面
  if (requiresPassword && passwordArticleInfo) {
    return (
      <div className="min-h-screen py-12 px-4">
        <PasswordProtectedArticle
          articleId={passwordArticleInfo.article_id}
          onPasswordVerified={() => {
            // 密码验证成功后重新加载文章
            setRequiresPassword(false);
            setPasswordArticleInfo(null);
            setLoading(true);
            // 重新获取文章（此时cookie中已有access_token）
            setTimeout(() => {
              window.location.reload();
            }, 500);
          }}
        />
      </div>
    );
  }

  if (error || !articleData) {
    return <ErrorState error={error || '文章不存在'}/>;
  }

  return <ArticleDetailClient articleData={articleData} />;
};

// 主页面组件 - 使用 Suspense 包裹 useSearchParams
const ArticleDetailPage: React.FC = () => {
  return (
      <Suspense fallback={<LoadingState/>}>
        <ArticleContent/>
      </Suspense>
  );
};

export default ArticleDetailPage;
