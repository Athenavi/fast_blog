import {useEffect, useState} from 'react';
import {apiClient} from '@/lib/api';
import {ApiResponse} from "@/lib/api/base-types";

interface User {
  id: number;
  username: string;
  email: string;
  profile_picture?: string;
  is_active: boolean;
  is_superuser: boolean;
  created_at: string;
  last_login?: string;
}

export const useAuth = () => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const checkAuthStatus = async () => {
    try {
      setLoading(true);
      // 使用 user-management 端点获取当前用户信息
      const response: ApiResponse<any> = await apiClient.get('/management/me/profile');
      
      if (response.success && response.data) {
        // 从嵌套的数据结构中提取用户信息
          const userData = (response.data as any).user || response.data;
        setUser(userData);
      } else {
        setUser(null);
      }
    } catch (err: unknown) {
      setUser(null);
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  const refreshUser = async () => {
    try {
      // 使用 user-management 端点获取当前用户信息
      const response: ApiResponse<any> = await apiClient.get('/management/me/profile');
      
      if (response.success && response.data) {
        // 从嵌套的数据结构中提取用户信息
          const userData = (response.data as any).user || response.data;
        setUser(userData);
        return userData;
      } else {
        setUser(null);
        return null;
      }
    } catch (err: unknown) {
      setUser(null);
      setError(err instanceof Error ? err.message : 'An error occurred');
      return null;
    }
  };

  const logout = async () => {
    try {
      // 调用后端登出 API
      const response = await apiClient.post('/auth/logout');

      if (response.success) {
        // 清除本地用户信息
        setUser(null);
      }
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      // 无论后端登出是否成功，都清除本地状态并重定向
      setUser(null);
      // 清除本地存储的 token
      if (typeof window !== 'undefined') {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
      }
      // 重定向到首页
      window.location.href = '/';
    }
  };

  useEffect(() => {
    checkAuthStatus();
  }, []);

  return { user, loading, error, checkAuthStatus, refreshUser, logout };
};