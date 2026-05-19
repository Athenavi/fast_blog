'use client';

import React from 'react';

const ArticleEditor: React.FC = () => {
  return (
    <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 p-6">
      <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-6">文章编辑器</h2>
      <p className="text-gray-500">编辑器组件将在后续迭代中接入 Tiptap</p>
    </div>
  );
};

export default ArticleEditor;
