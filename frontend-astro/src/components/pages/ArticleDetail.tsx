'use client';

import React from 'react';

interface Props {
  slug: string;
}

const ArticleDetail: React.FC<Props> = ({slug}) => {
  return (
    <div className="prose dark:prose-invert max-w-none">
      <p className="text-gray-500">加载文章 <code>{slug}</code>...</p>
    </div>
  );
};

export default ArticleDetail;
