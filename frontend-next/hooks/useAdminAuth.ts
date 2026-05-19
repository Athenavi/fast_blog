import {useEffect} from 'react';
import {useRouter} from 'next/navigation';
import {useAuth} from './useAuth';

export const useAdminAuth = () => {
  const { user, loading, checkAuthStatus } = useAuth();
  const router = useRouter();

  useEffect(() => {
    const verifyAdmin = async () => {
      if (!loading) {
        // 等待认证状态确定
        await new Promise(resolve => setTimeout(resolve, 0));
        
        if (!user) {
          // 用户未登录，重定向到登录页
          router.push('/login');
        } else if (!user.is_superuser) {
          // 用户不是管理员，重定向到首页
          router.push('/');
        }
      }
    };

    verifyAdmin();
  }, [user, loading, router]);

  return { user, loading, isAdmin: user?.is_superuser };
};