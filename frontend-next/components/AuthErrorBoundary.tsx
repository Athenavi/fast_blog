'use client';

import React, {useEffect} from 'react';
import {useRouter} from 'next/navigation';

interface AuthErrorBoundaryProps {
  error: string;
  children: React.ReactNode;
  onRetry?: () => void;
  showLoginButton?: boolean;
  redirectPath?: string;
}

/**
 * 通用认证错误边界组件
 * 自动处理 401 未授权错误，提供友好的用户体验
 */
const AuthErrorBoundary: React.FC<AuthErrorBoundaryProps> = ({
  error,
  children,
  onRetry,
  showLoginButton = true,
  redirectPath
}) => {
  const router = useRouter();
  const isUnauthorized = error.includes('401') || error.toLowerCase().includes('unauthorized') || error.includes('requires_auth');

  useEffect(() => {
    // 如果是401错误且需要自动重定向
    if (isUnauthorized && typeof window !== 'undefined') {
      // 保存当前路径用于登录后重定向
      const currentPath = redirectPath || window.location.pathname + window.location.search;
      localStorage.setItem('redirect_after_login', currentPath);
      
      // 构造带next参数的登录URL
      const nextParam = encodeURIComponent(currentPath);
      const loginUrl = `/login?next=${nextParam}`;
      
      // 延迟重定向，给用户一点时间看到错误信息
      const timer = setTimeout(() => {
        router.push(loginUrl as any);
      }, 3200);
      
      return () => clearTimeout(timer);
    }
  }, [isUnauthorized, router, redirectPath]);

  // 如果不是认证错误，渲染子组件
  if (!isUnauthorized) {
    return <>{children}</>;
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 py-12">
      <div className="container mx-auto px-4">
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-yellow-200 dark:border-yellow-800 p-8 max-w-lg mx-auto">
          <div className="text-yellow-500 mb-4 flex justify-center">
            <svg className="w-12 h-12" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          </div>
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-2 text-center">需要登录</h2>
          <p className="text-gray-600 dark:text-gray-300 mb-6 text-center">
            {error || '您需要登录才能访问此页面'}
          </p>
          
          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            {showLoginButton && (
              <button
                onClick={() => {
                  const currentPath = redirectPath || window.location.pathname + window.location.search;
                  const nextParam = encodeURIComponent(currentPath);
                  router.push(`/login?next=${nextParam}` as any);
                }}
                className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors text-center"
              >
                前往登录
              </button>
            )}
            
            {onRetry && (
              <button
                onClick={onRetry}
                className="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-800 transition-colors text-center"
              >
                重试
              </button>
            )}
          </div>
          
          {isUnauthorized && (
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-4 text-center">
              正在为您跳转到登录页面...
            </p>
          )}
        </div>
      </div>
    </div>
  );
};

export default AuthErrorBoundary;