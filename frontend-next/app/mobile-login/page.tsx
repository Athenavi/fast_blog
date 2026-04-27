'use client';

import React, {Suspense} from 'react';
import {useRouter, useSearchParams} from 'next/navigation';

const MobileLoginPageContent = () => {
  const router = useRouter();
  const searchParams = useSearchParams();

  // 获取 URL 参数 - 支持 login_token（扫码登录）和 code/state（OAuth 登录）
  const loginToken = searchParams.get('login_token');
  const code = searchParams.get('code');
  const state = searchParams.get('state');
  const error = searchParams.get('error');

  React.useEffect(() => {
    // 处理错误情况
    if (error) {
      console.error('Mobile login error:', error);
      alert(`登录失败：${error}`);
      router.push('/login');
      return;
    }

    // 优先处理扫码登录（login_token 参数）
    if (loginToken) {
      handleQRScan(loginToken);
      return;
    }

    // 处理 OAuth 登录（code 参数）
    if (code) {
      handleMobileLogin(code, state || undefined);
    }
  }, [loginToken, code, error]);

  // 处理二维码扫码确认
  const handleQRScan = async (token: string) => {
    try {
      // 使用运行时配置的后端 API 地址
      const config = await import('@/lib/config');
      const apiConfig = config.getConfig();
      const fullUrl = `${apiConfig.API_BASE_URL}${apiConfig.API_PREFIX}/phone/scan?login_token=${token}`;

      console.log('调用扫码 API:', fullUrl);

      // 调用后端 API 进行扫码确认
      const response = await fetch(fullUrl, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include', // 包含 cookie
      });

      const result = await response.json();

      if (result.success) {
        // 扫码成功，显示成功消息
        alert('授权成功！请回到PC端完成登录。');
        // 可以关闭当前窗口或返回上一页
        if (window.opener) {
          window.opener.location.reload();
          window.close();
        } else {
          router.push('/');
        }
      } else if (result.requires_auth) {
        // 需要登录，重定向到登录页面
        alert('请先登录移动端账户');
        router.push(`/login?redirect=/mobile-login?login_token=${token}`);
      } else {
        throw new Error(result.message || '扫码确认失败');
      }
    } catch (err) {
      console.error('QR scan error:', err);
      const errorMessage = err instanceof Error ? err.message : '扫码确认过程中发生错误';
      alert(errorMessage);
      router.push('/login');
    }
  };

  const handleMobileLogin = async (code: string, state?: string) => {
    try {
      // 使用运行时配置的后端 API 地址
      const config = await import('@/lib/config');
      const apiConfig = config.getConfig();
      const fullUrl = `${apiConfig.API_BASE_URL}${apiConfig.API_PREFIX}/auth/mobile/callback`;

      console.log('调用移动端登录 API:', fullUrl);

      // 发送请求到后端 API，交换访问令牌
      const response = await fetch(fullUrl, {
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