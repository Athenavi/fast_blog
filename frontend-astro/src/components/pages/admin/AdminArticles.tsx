'use client';

import React, {useEffect, useState} from 'react';
import {ArticleManagementService} from '@/lib/api';
import type {Article} from '@/lib/api/base-types';

const AdminArticles: React.FC = () => {
  const [articles, setArticles] = useState<Article[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    ArticleManagementService.getArticles({page: 1, per_page: 20}).then(res => {
      if (res.success && res.data) setArticles(res.data.articles || []);
    }).finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="animate-spin w-8 h-8 border-2 border-blue-600 border-t-transparent rounded-full mx-auto" />;

  return (
    <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
      <table className="w-full">
        <thead className="bg-gray-50 dark:bg-gray-800">
          <tr>
            <th className="px-6 py-3 text-left text-sm font-medium text-gray-500">标题</th>
            <th className="px-6 py-3 text-left text-sm font-medium text-gray-500">状态</th>
            <th className="px-6 py-3 text-left text-sm font-medium text-gray-500">浏览</th>
            <th className="px-6 py-3 text-left text-sm font-medium text-gray-500">时间</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
          {articles.map(a => (
            <tr key={a.id} className="hover:bg-gray-50 dark:hover:bg-gray-800">
              <td className="px-6 py-4 text-sm text-gray-900 dark:text-white">{a.title}</td>
              <td className="px-6 py-4"><span className="px-2 py-1 text-xs rounded-full bg-green-100 text-green-700">{a.status}</span></td>
              <td className="px-6 py-4 text-sm text-gray-500">{a.views}</td>
              <td className="px-6 py-4 text-sm text-gray-500">{new Date(a.created_at).toLocaleDateString('zh-CN')}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default AdminArticles;
