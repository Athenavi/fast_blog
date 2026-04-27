'use client';

import {useEffect} from 'react';
import {useRouter, useSearchParams} from 'next/navigation';
import {apiClient} from '@/lib/api';

const QrScanHandlerPage = () => {
  const router = useRouter();
  const searchParams = useSearchParams();
  const loginToken = searchParams.get('login_token');

  useEffect(() => {
    const handleQrScan = async () => {
      if (!loginToken) {
        // 如果没有登录token，跳转回登录页面
        router.push('/login');
        return;
      }

      try {
        // 尝试调用后端接口进行扫码确认
        const response = await apiClient.get(`/phone/scan?login_token=${loginToken}`);
        
        if (response.success) {
          // 扫码成功，显示成功信息
          alert('授权成功！请回到PC端完成登录。');
          router.push('/login');
        } else {
          // 扫码失败，可能是未登录
          if (response.message && typeof response.message === 'string' && response.message.includes('未登录')) {
            // 重定向到登录页面，并保存原始参数
            router.push(`/login?redirect=/auth/qr-scan-handler?login_token=${loginToken}`);
          } else {
            alert(response.message || '扫码授权失败，请重试');
            router.push('/login');
          }
        }
      } catch (error: any) {
        // 检查错误是否与认证有关
        if (error.message && (error.message.includes('401') || error.message.includes('认证') || error.message.includes('Unauthorized'))) {
          // 用户未登录，重定向到登录页面
          router.push(`/login?redirect=/auth/qr-scan-handler?login_token=${loginToken}`);
        } else {
          console.error('Error during QR scan:', error);
          alert('扫码过程中出现错误，请重试');
          router.push('/login');
        }
      }
    };

    handleQrScan();
  }, [loginToken, router]);

  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-50">
      <div className="text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto"></div>
        <p className="mt-4 text-lg text-gray-600">正在处理扫码授权...</p>
      </div>
    </div>
  );
};

export default QrScanHandlerPage;