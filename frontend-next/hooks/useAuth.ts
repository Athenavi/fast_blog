import {useEffect, useState} from 'react';
import {apiClient} from '@/lib/api';
import {ApiResponse} from "@/lib/api/base-types";

interface User {
  id: number;
  username: string;
  email: string;
  avatar?: string;
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
      const response: ApiResponse<User> = await apiClient.get('/users/me');
      
      if (response.success && response.data) {
        setUser(response.data);
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
      const response: ApiResponse<User> = await apiClient.get('/users/me');
      
      if (response.success && response.data) {
        setUser(response.data);
        return response.data;
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
      // 调用后端登出API
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
      // 重定向到首页
      window.location.href = '/';
    }
  };

  useEffect(() => {
    checkAuthStatus();
  }, []);

  return { user, loading, error, checkAuthStatus, refreshUser, logout };
};