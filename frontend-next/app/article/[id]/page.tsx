import React from 'react';
import {notFound} from 'next/navigation';
import {ArticleService} from '@/lib/api';
import ArticleDetailClient from '@/components/ArticleDetailClient';

// 服务器组件获取文章数据
async function getArticleData(id: string) {
  try {
    const response = await ArticleService.getArticleWithI18n(id);
    
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
  params: Promise<{ id: string }>;
}

const ArticleDetailPage: React.FC<ArticleDetailPageProps> = async ({ params }) => {
  // 使用 await 解包 params
  const resolvedParams = await params;
  const articleData = await getArticleData(resolvedParams.id);

  if (!articleData) {
    notFound();
  }

  return <ArticleDetailClient articleData={articleData} />;
};

export default ArticleDetailPage;