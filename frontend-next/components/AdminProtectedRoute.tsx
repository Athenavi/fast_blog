'use client';

import React, {useEffect, useState} from 'react';
import {useRouter} from 'next/navigation';
import {useAuth} from '@/hooks/useAuth';

interface AdminProtectedRouteProps {
  children: React.ReactNode;
}

const AdminProtectedRoute: React.FC<AdminProtectedRouteProps> = ({ children }) => {
  const { user, loading } = useAuth();
  const router = useRouter();
  const [authorized, setAuthorized] = useState<boolean | null>(null);

  useEffect(() => {
    if (!loading) {
      if (!user) {
        // 用户未登录，重定向到登录页
        router.push('/login');
      } else if (!user.is_superuser) {
        // 用户不是管理员，重定向到首页
        router.push('/');
      } else {
        // 用户是管理员，允许访问
        setAuthorized(true);
      }
    }
  }, [user, loading, router]);

  if (authorized === null || loading) {
    // 正在检查权限时显示加载状态
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  if (!authorized) {
    return null; // 或者显示无权限页面
  }

  return <>{children}</>;
};

export default AdminProtectedRoute;