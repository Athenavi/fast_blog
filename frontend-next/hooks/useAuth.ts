import {useCallback, useEffect, useState} from 'react';
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

  // 从 cookie 获取 token
  const getTokenFromCookie = useCallback((): string | null => {
    if (typeof document === 'undefined') return null;
    const cookies = document.cookie.split(';');
    for (const cookie of cookies) {
      const [name, value] = cookie.trim().split('=');
      if (name === 'access_token' && value) {
        return decodeURIComponent(value);
      }
    }
    return null;
  }, []);

  const checkAuthStatus = useCallback(async () => {
    try {
      setLoading(true);

      // 先检查 cookie 中是否有 token
      const token = getTokenFromCookie();
      if (!token) {
        setUser(null);
        setLoading(false);
        return;
      }
      
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
  }, [getTokenFromCookie]);

  const refreshUser = useCallback(async () => {
    try {
      // 先检查 cookie 中是否有 token
      const token = getTokenFromCookie();
      if (!token) {
        setUser(null);
        return null;
      }
      
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
  }, [getTokenFromCookie]);

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
      // 清除 cookie 中的 token
      if (typeof window !== 'undefined') {
        document.cookie = 'access_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
        document.cookie = 'refresh_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
      }
      // 重定向到首页
      window.location.href = '/';
    }
  };

  useEffect(() => {
    checkAuthStatus();
  }, [checkAuthStatus]);

  return { user, loading, error, checkAuthStatus, refreshUser, logout };
};