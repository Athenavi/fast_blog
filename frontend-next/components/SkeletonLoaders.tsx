'use client';

import React from 'react';

export const SkeletonCard = () => (
  <div className="bg-white dark:bg-gray-800 rounded-xl shadow-md overflow-hidden animate-pulse">
    <div className="h-48 bg-gray-200 dark:bg-gray-700 w-full"></div>
    <div className="p-5">
      <div className="h-5 bg-gray-200 dark:bg-gray-700 rounded w-4/5 mb-3"></div>
      <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-full mb-2"></div>
      <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-3/4 mb-4"></div>
      <div className="flex justify-between items-center">
        <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-1/3"></div>
        <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-1/4"></div>
      </div>
    </div>
  </div>
);

export const SkeletonFeatured = () => (
  <div className="relative group overflow-hidden rounded-2xl h-96 animate-pulse">
    <div className="absolute inset-0 bg-gradient-to-t from-black/70 to-transparent z-10"></div>
    <div className="bg-gray-200 dark:bg-gray-700 w-full h-full"></div>
    <div className="absolute bottom-0 left-0 z-20 p-8 text-white w-full">
      <div className="h-8 bg-gray-300 dark:bg-gray-600 rounded w-3/4 mb-4"></div>
      <div className="h-4 bg-gray-300 dark:bg-gray-600 rounded w-full mb-2"></div>
      <div className="h-4 bg-gray-300 dark:bg-gray-600 rounded w-5/6 mb-4"></div>
      <div className="flex items-center space-x-4">
        <div className="h-4 bg-gray-300 dark:bg-gray-600 rounded w-1/4"></div>
        <div className="h-4 bg-gray-300 dark:bg-gray-600 rounded w-1/5"></div>
      </div>
    </div>
  </div>
);

export const ConfigLoadingSkeleton = () => (
  <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center">
    <div className="text-center">
      <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto"></div>
      <p className="mt-4 text-gray-600 dark:text-gray-400">加载配置中...</p>
    </div>
  </div>
);