'use client';

import Link from 'next/link';
import { WifiOff } from 'lucide-react';

export default function OfflinePage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
      <div className="text-center p-8">
        <WifiOff className="w-24 h-24 mx-auto mb-6 text-gray-400" />
        <h1 className="text-3xl font-bold text-gray-800 dark:text-white mb-4">
          您已离线
        </h1>
        <p className="text-gray-600 dark:text-gray-400 mb-8">
          请检查网络连接后重试
        </p>
        <Link
          href="/"
          className="inline-block px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          返回首页
        </Link>
      </div>
    </div>
  );
}
