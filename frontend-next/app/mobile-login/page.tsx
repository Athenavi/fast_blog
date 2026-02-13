'use client';

import React, {Suspense} from 'react';
import {useRouter, useSearchParams} from 'next/navigation';

const MobileLoginPageContent = () => {
  const router = useRouter();
  const searchParams = useSearchParams();

  // 获取URL参数
  const code = searchParams.get('code');
  const state = searchParams.get('state');
  const error = searchParams.get('error');

  React.useEffect(() => {
    // 在这里处理移动端的登录逻辑
    if (error) {
      console.error('Mobile login error:', error);
      // 处理错误情况
      alert(`登录失败: ${error}`);
      // 可以重定向到登录页面或其他地方
      router.push('/login');
    } else if (code) {
      // 有授权码，发送给后端换取令牌
      handleMobileLogin(code, state || undefined);
    }
  }, [code, error]);

  const handleMobileLogin = async (code: string, state?: string) => {
    try {
      // 发送请求到后端API，交换访问令牌
      const response = await fetch(`/api/v1/auth/mobile/callback`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ code, state }),
      });

      const result = await response.json();

      if (result.success && result.data) {
        // 保存令牌到本地存储
        if (typeof window !== 'undefined') {
          localStorage.setItem('access_token', result.data.access_token);
          
          // 如果有refresh_token，也保存
          if (result.data.refresh_token) {
            localStorage.setItem('refresh_token', result.data.refresh_token);
          }
        }

        // 重定向到首页或原始请求的页面
        const redirectUrl = state || '/';
        router.push(redirectUrl as any);
      } else {
        throw new Error(result.error || '移动登录失败');
      }
    } catch (err) {
      console.error('Mobile login error:', err);
      const errorMessage = err instanceof Error ? err.message : '移动登录过程中发生错误';
      alert(errorMessage);
      router.push('/login');
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center py-12">
      <div className="text-center">
        <div className="inline-block animate-spin rounded-full h-10 w-10 border-t-2 border-b-2 border-indigo-600 mb-4"></div>
        <p className="text-gray-600 dark:text-gray-300">正在处理移动登录...</p>
      </div>
    </div>
  );
};

const MobileLoginPage = () => {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center py-12">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-10 w-10 border-t-2 border-b-2 border-indigo-600 mb-4"></div>
          <p className="text-gray-600 dark:text-gray-300">正在加载...</p>
        </div>
      </div>
    }>
      <MobileLoginPageContent />
    </Suspense>
  );
};

export default MobileLoginPage;