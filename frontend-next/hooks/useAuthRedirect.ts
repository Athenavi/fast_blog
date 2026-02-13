import {useEffect} from 'react';
import {useRouter} from 'next/navigation';
import {apiClient} from '@/lib/api';

export const useAuthRedirect = () => {
  const router = useRouter();

  useEffect(() => {
    const checkAuthAndRedirect = async () => {
      try {
        // 尝试获取当前用户信息，如果成功说明用户已登录
        const response = await apiClient.get('/users/me');
        
        if (response.success && response.data) {
          // 用户已登录，重定向到主页或个人资料页
          router.push('/profile');
        }
      } catch {
        // 如果请求失败，说明用户未登录，保持在登录页面
        console.log('User not logged in, staying on login page');
      }
    };

    void checkAuthAndRedirect();
  }, [router]);
};