'use client';

import React from 'react';

/**
 * 403 权限拒绝提示页
 */
export function Forbidden({message = '您没有权限执行此操作'}: {message?: string}) {
  return (
    <div className="min-h-[60vh] flex items-center justify-center">
      <div className="text-center max-w-md">
        <div className="text-6xl mb-4 text-red-400">🔒</div>
        <h1 className="text-2xl font-bold text-gray-800 dark:text-gray-100 mb-2">
          权限不足
        </h1>
        <p className="text-gray-500 dark:text-gray-400 mb-6">{message}</p>
        <a
          href="/admin"
          className="inline-block px-6 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          返回管理首页
        </a>
      </div>
    </div>
  );
}
