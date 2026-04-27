'use client';

import React, {Suspense} from 'react';
import {useSearchParams} from 'next/navigation';
import BlogDetailContent from './BlogDetailContent';
import LoadingState from '@/components/LoadingState';

// 文章内容组件
const BlogDetailContentWrapper = () => {
  const searchParams = useSearchParams();
  const slug = searchParams.get('slug');

  if (!slug) {
    return (
        <div className="min-h-screen flex items-center justify-center">
          <div className="text-center">
            <h2 className="text-2xl font-bold text-gray-900 mb-2">文章不存在</h2>
            <p className="text-gray-600">未找到指定的文章</p>
          </div>
        </div>
    );
  }

  return <BlogDetailContent slug={slug}/>;
};

// 主页面组件 - 使用 Suspense 包裹
const BlogArticleDetailPage: React.FC = () => {
  return (
      <Suspense fallback={<LoadingState/>}>
        <BlogDetailContentWrapper/>
      </Suspense>
  );
};

export default BlogArticleDetailPage;
