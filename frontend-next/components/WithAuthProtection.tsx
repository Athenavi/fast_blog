'use client';

import React from 'react';
import {useAuthGuard} from '@/hooks/useAuthGuard';
import LoadingState from '@/components/LoadingState';

interface WithAuthProtectionProps {
  children: React.ReactNode;
  redirectTo?: string;
  loadingMessage?: string;
}

/**
 * 认证保护高阶组件
 * 自动处理未认证用户的重定向
 */
const WithAuthProtection: React.FC<WithAuthProtectionProps> = ({
  children,
  redirectTo = '/login',
  loadingMessage = '正在验证登录状态...'
}) => {
  const { isAuthenticated, isLoading } = useAuthGuard({
    redirectTo,
    redirectIfUnauthenticated: true,
    saveRedirectPath: true
  });

  if (isLoading) {
    return <LoadingState message={loadingMessage} />;
  }

  if (!isAuthenticated) {
    // useAuthGuard 会自动重定向，这里可以返回 null 或加载状态
    return <LoadingState message="正在跳转到登录页面..." />;
  }

  return <>{children}</>;
};

export default WithAuthProtection;