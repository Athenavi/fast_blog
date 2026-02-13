import React from 'react';
import {notFound} from 'next/navigation';
import {ArticleService} from '@/lib/api';
import ArticleDetailClient from '@/components/ArticleDetailClient';

// 服务器组件获取文章数据
async function getArticleBySlug(slug: string) {
  try {
    const response = await ArticleService.getArticleBySlug(slug);
    
    if (response.success && response.data) {
      return response.data;
    } else {
      return null;
    }
  } catch (err) {
    console.error('获取文章时发生错误:', err);
    return null;
  }
}

// 主页面组件 - 直接使用解构赋值
interface ArticleDetailPageProps {
  params: Promise<{ slug: string }>;
}

const BlogArticleDetailPage: React.FC<ArticleDetailPageProps> = async ({ params }) => {
  // 使用 await 解包 params
  const resolvedParams = await params;
  const articleData = await getArticleBySlug(resolvedParams.slug);

  if (!articleData) {
    notFound();
  }

  return <ArticleDetailClient articleData={articleData} />;
};

export default BlogArticleDetailPage;