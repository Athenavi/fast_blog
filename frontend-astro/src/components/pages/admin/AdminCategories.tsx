'use client';

import React, {useEffect, useState} from 'react';
import {CategoryService} from '@/lib/api';
import type {Category} from '@/lib/api/base-types';

const AdminCategories: React.FC = () => {
  const [categories, setCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    CategoryService.getCategories({per_page: 50}).then(res => {
      if (res.success && res.data) setCategories(res.data.categories || []);
    }).finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="animate-spin w-8 h-8 border-2 border-blue-600 border-t-transparent rounded-full mx-auto" />;

  return (
    <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
      <table className="w-full">
        <thead className="bg-gray-50 dark:bg-gray-800">
          <tr>
            <th className="px-6 py-3 text-left text-sm font-medium text-gray-500">名称</th>
            <th className="px-6 py-3 text-left text-sm font-medium text-gray-500">描述</th>
            <th className="px-6 py-3 text-left text-sm font-medium text-gray-500">文章数</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
          {categories.map(c => (
            <tr key={c.id} className="hover:bg-gray-50 dark:hover:bg-gray-800">
              <td className="px-6 py-4 text-sm font-medium text-gray-900 dark:text-white">{c.name}</td>
              <td className="px-6 py-4 text-sm text-gray-500">{c.description || '-'}</td>
              <td className="px-6 py-4 text-sm text-gray-500">{c.article_count || 0}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default AdminCategories;
