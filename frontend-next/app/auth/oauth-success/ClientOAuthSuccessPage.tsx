'use client';

import {useEffect} from 'react';
import {useRouter, useSearchParams} from 'next/navigation';

// 验证重定向URL的安全性
function isValidRedirect(url: string): boolean {
    try {
        const parsedUrl = new URL(url, window.location.origin);
        // 只允许同域的路径
        return parsedUrl.origin === window.location.origin;
    } catch {
        // 如果URL无效，则检查是否为相对路径
        return url.startsWith('/') && !url.startsWith('//');
    }
}


const OAuthSuccessPage = () => {
  const router = useRouter();
  const searchParams = useSearchParams();
  
  useEffect(() => {
    // 获取URL参数中的next参数
    const nextParam = searchParams.get('next');
    
    // 1秒后跳转到指定页面
    const timer = setTimeout(() => {
        if (nextParam && isValidRedirect(nextParam)) {
            // 使用 window.location.href 进行跳转以避免类型问题
            window.location.href = nextParam;
        } else {
            router.push('/profile');
        }
    }, 1000);

    return () => clearTimeout(timer);
  }, [router, searchParams]);

  return (
    <div 
      style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        height: '100vh',
        backgroundColor: '#f0f2f5'
      }}
    >
      <div 
        style={{
          textAlign: 'center',
          padding: '2rem',
          backgroundColor: 'white',
          borderRadius: '8px',
          boxShadow: '0 2px 10px rgba(0,0,0,0.1)'
        }}
      >
        <div style={{ fontSize: '3rem', color: '#4CAF50', marginBottom: '1rem' }}>✓</div>
        <h2 style={{ color: '#333' }}>登录成功</h2>
        <p style={{ color: '#666', marginTop: '1rem' }}>您已成功登录，正在跳转...</p>
      </div>
    </div>
  );
};

export default OAuthSuccessPage;