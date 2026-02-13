'use client';

import React, {useEffect, useRef, useState} from 'react';
import Link from 'next/link';
import {useRouter} from 'next/navigation';
import {apiClient} from '@/lib/api'; // 导入API客户端
import type {QrCodeResponse, QrLoginSuccessResponse} from '@/lib/api/base-types';

const LoginPage = () => {
  const router = useRouter();
  const [loginForm, setLoginForm] = useState({
    email: '',
    password: '',
    rememberMe: false
  });
  const [loginLoading, setLoginLoading] = useState(false);
  const [passwordVisible, setPasswordVisible] = useState(false);
  const [activeMethod, setActiveMethod] = useState<'password' | 'qr'>('password');
  const [errorMessage, setErrorMessage] = useState(''); // 添加错误消息状态
  const [checkingAuth, setCheckingAuth] = useState(true); // 添加认证检查状态
  // 新增二维码相关状态
  const [qrCodeImage, setQrCodeImage] = useState<string>('');
  const [qrToken, setQrToken] = useState<string>('');
  const [qrExpiresAt, setQrExpiresAt] = useState<number>(0);
  const [qrStatus, setQrStatus] = useState<'pending' | 'scanned' | 'confirmed' | 'expired'>('pending');
  const [countdown, setCountdown] = useState<number>(0);
  const [qrPolling, setQrPolling] = useState<boolean>(false);
  
  // 使用 useRef 来跟踪最新状态
  const qrStatusRef = useRef(qrStatus);
  const countdownRef = useRef(countdown);
  
  // 更新 ref 值
  useEffect(() => {
    qrStatusRef.current = qrStatus;
    countdownRef.current = countdown;
  }, [qrStatus, countdown]);

  // 检查用户是否已登录
  useEffect(() => {
    let isMounted = true; // 防止组件卸载后仍执行状态更新
    let hasCheckedAuth = false; // 防止重复检查
    
    const checkAuthAndRedirect = async () => {
      // 确保只检查一次
      if (hasCheckedAuth) return;
      hasCheckedAuth = true;
      
      try {
        // 简单检查本地存储中的令牌是否存在，而不通过API客户端
        const accessToken = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null;
        
        if (accessToken) {
          // 如果存在访问令牌，尝试验证它
          const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000/api/v1'}/users/me`, {
            method: 'GET',
            headers: {
              'Authorization': `Bearer ${accessToken}`,
              'Content-Type': 'application/json',
            },
          });
          
          if (response.ok) {
            const data = await response.json();
            if (data && data.success && data.data) {
              // 用户已登录，重定向到主页或个人资料页
              const nextUrl = new URLSearchParams(window.location.search).get('next') || '/profile';
              window.location.replace(nextUrl);
              return;
            }
          }
        }
        
        // 用户未登录或令牌无效，继续显示登录页面
        if (isMounted) {
          setCheckingAuth(false);
        }
      } catch (error: unknown) {
        // 如果请求失败，说明用户未登录，继续显示登录页面
        console.log('Authentication check failed:', (error as Error)?.message || String(error));
        if (isMounted) {
          setCheckingAuth(false);
        }
      }
    };

    checkAuthAndRedirect();
    
    // 清理函数
    return () => {
      isMounted = false;
    };
  }, []); // 依赖数组为空，只在组件挂载时执行一次

  // 生成二维码
  const generateQRCode = async () => {
    try {
      const response = await apiClient.get<QrCodeResponse>('/qr/generate');
      
      // 直接使用response作为数据，因为后端可能直接返回了完整的数据结构
      if (response.success && response.data) {
        // 检查response本身是否包含了所需的数据
        const qrData = response.data;
        
        setQrCodeImage(qrData.qr_code);
        setQrToken(qrData.token);
        setQrExpiresAt(typeof qrData.expires_at === 'string' ? parseInt(qrData.expires_at) : qrData.expires_at as number);
        const status = qrData.status;
        const validStatus: 'pending' | 'scanned' | 'confirmed' | 'expired' = 
          (status === 'pending' || status === 'scanned' || status === 'confirmed' || status === 'expired')
            ? status
            : 'pending';
        setQrStatus(validStatus);
        setCountdown(180); // 设置倒计时为3分钟（180秒）
        return true;
      } else {
        setErrorMessage(response.error || response.message || '生成二维码失败');
        return false;
      }
    } catch (error) {
      console.error('Error generating QR code:', error);
      setErrorMessage('生成二维码时发生错误');
      return false;
    }
  };

  // 检查二维码状态 - 现在使用轮询机制
  const checkQRStatus = async () => {
    if (!qrToken) return;

    try {
      const response = await apiClient.get(`/qr/status?token=${qrToken}&next=/profile`);
      
      // 处理需要认证的情况
      if (response.requires_auth) {
        console.log('QR scan requires authentication on mobile device');
        // 这种情况应该不会在PC端的轮询中出现，因为我们调用的是状态检查API
        return false;
      }
      
      // 检查是否是401错误，如果是，继续轮询而不是失败
      if ('status' in response && response.status === 401) {
        console.log('QR status check received 401, continuing to poll');
        return false;
      }
      
      if (response.success && response.data) {
        // 检查响应结构，兼容可能的后端响应格式变化
        const statusData = response.data as QrLoginSuccessResponse;
        const status = statusData.status;
        
        if (status && String(status) === 'success') {
          // 扫码成功，获取访问令牌并跳转
          if (statusData.access_token) {
            // 保存令牌到本地存储和cookie
            if (typeof window !== 'undefined') {
              localStorage.setItem('access_token', statusData.access_token);
              // 设置cookie以匹配后端期望
              const expirationDate = new Date();
              expirationDate.setTime(expirationDate.getTime() + (60 * 60 * 1000)); // 1小时后过期
              document.cookie = `access_token=${statusData.access_token}; expires=${expirationDate.toUTCString()}; path=/; SameSite=Strict;`;
              
              // 如果有refresh_token，也一并保存
              if (statusData.refresh_token) {
                localStorage.setItem('refresh_token', statusData.refresh_token);
                // 设置refresh_token的cookie
                const refreshExpirationDate = new Date();
                refreshExpirationDate.setTime(refreshExpirationDate.getTime() + (7 * 24 * 60 * 60 * 1000)); // 7天后过期
                document.cookie = `refresh_token=${statusData.refresh_token}; expires=${refreshExpirationDate.toUTCString()}; path=/; SameSite=Strict;`;
              } else {
                console.warn('Warning: No refresh_token returned from QR login, this may affect session persistence');
              }
            }
            setQrStatus('confirmed');
            // 跳转到目标页面
            const nextUrl = new URLSearchParams(window.location.search).get('next') || statusData.next_url || '/profile';
            const validatedNextUrl = typeof nextUrl === 'string' && nextUrl ? nextUrl : '/profile';
            // 延迟跳转以确保令牌已保存
            setTimeout(() => {
              window.location.href = validatedNextUrl;
            }, 300);
            return true;
          }
        } else if (status && String(status) === 'pending') {
          setQrStatus('pending');
        } else if (status && String(status) === 'scanned') {
          setQrStatus('scanned');
        } else if ((status && String(status) === 'expired') || Date.now() / 1000 > qrExpiresAt) {
          setQrStatus('expired');
          stopQRPolling();
        } else {
          // 其他状态，保持当前状态或设置为pending
          const validStatus = ['pending', 'scanned', 'confirmed', 'expired'].includes(String(status)) 
            ? String(status) as 'pending' | 'scanned' | 'confirmed' | 'expired'
            : 'pending';
          setQrStatus(validStatus);
        }
      } else {
        // 请求失败，可能需要处理错误
        console.log('QR status check failed:', response.message || response.error);
      }
    } catch (error) {
      console.error('Error checking QR status:', error);
      // 遇到错误时继续轮询
    }
    return false;
  };

  // 开始二维码状态轮询
  const startQRPolling = () => {
    if (qrPolling) return;
    setQrPolling(true);
    
    // 开始轮询二维码状态，每3秒检查一次
    const interval = setInterval(async () => {
      try {
        const success = await checkQRStatus();
        // 使用 ref 获取最新状态值
        if (success || qrStatusRef.current === 'expired' || Date.now() / 1000 > qrExpiresAt) {
          clearInterval(interval);
          setQrPolling(false);
        }
      } catch (error) {
        console.error('Error in QR polling:', error);
        // 继续轮询，不要因为单个错误而停止
      }
    }, 3000); // 每3秒检查一次状态

    // 清理函数
    return () => {
      clearInterval(interval);
    };
  };

  // 停止二维码状态轮询
  const stopQRPolling = () => {
    setQrPolling(false);
  };

  // 当切换到二维码登录时，生成二维码
  useEffect(() => {
    if (activeMethod === 'qr' && !qrCodeImage) {
      generateQRCode();
    } else if (activeMethod === 'qr' && qrCodeImage) {
      // 重新激活轮询
      startQRPolling();
    } else {
      // 停止轮询
      stopQRPolling();
    }

    // 组件卸载时停止轮询
    return () => {
      stopQRPolling();
    };
  }, [activeMethod]);

  // 二维码倒计时
  useEffect(() => {
    let timer: NodeJS.Timeout;
    if (activeMethod === 'qr' && countdown > 0 && qrStatus !== 'confirmed') {
      timer = setTimeout(() => {
        setCountdown(countdown - 1);
      }, 1000);
    } else if (countdown === 0 && qrStatus !== 'confirmed' && activeMethod === 'qr') {
      setQrStatus('expired');
    }

    return () => {
      if (timer) clearTimeout(timer);
    };
  }, [countdown, activeMethod, qrStatus]);

  // 刷新二维码
  const refreshQRCode = async () => {
    setQrCodeImage('');
    setQrToken('');
    setQrStatus('pending');
    await generateQRCode();
    startQRPolling();
  };

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoginLoading(true);
    setErrorMessage(''); // 清除之前的错误消息
    
    try {
      // 发送登录请求到后端API，包含remember_me参数
      const response = await apiClient.post('/auth/login', {
        email: loginForm.email,
        password: loginForm.password,
        remember_me: loginForm.rememberMe
      });

      if (response.success && response.data) {
        const loginData = response.data as { access_token?: string; refresh_token?: string };
        // 登录成功，保存访问令牌
        if (loginData.access_token) {
          if (typeof window !== 'undefined') {
            localStorage.setItem('access_token', loginData.access_token);
            // 设置cookie以匹配后端期望
            const expirationDate = new Date();
            expirationDate.setTime(expirationDate.getTime() + (60 * 60 * 1000)); // 1小时后过期
            document.cookie = `access_token=${loginData.access_token}; expires=${expirationDate.toUTCString()}; path=/; SameSite=Strict;`;
            
            // 如果有refresh_token，也一并保存
            if (loginData.refresh_token) {
              localStorage.setItem('refresh_token', loginData.refresh_token);
              // 设置refresh_token的cookie
              const refreshExpirationDate = new Date();
              refreshExpirationDate.setTime(refreshExpirationDate.getTime() + (7 * 24 * 60 * 60 * 1000)); // 7天后过期
              document.cookie = `refresh_token=${loginData.refresh_token}; expires=${refreshExpirationDate.toUTCString()}; path=/; SameSite=Strict;`;
            }
          }
        }
        // 跳转到主页或目标页面
        const nextUrl = new URLSearchParams(window.location.search).get('next') || '/profile';
        const validatedNextUrl = typeof nextUrl === 'string' && nextUrl ? nextUrl : '/profile';
        // 延迟跳转以确保令牌已保存
        setTimeout(() => {
          window.location.href = validatedNextUrl;
        }, 300);
      } else {
        // 登录失败，显示错误消息
        setErrorMessage(response.error || '登录失败，请检查邮箱和密码');
      }
    } catch (error: unknown) {
      console.error('Login error:', error);
      
      // 检查错误类型并提供更精确的错误信息
      const errorObj = error as any;
      if (errorObj.status === 401) {
        setErrorMessage('邮箱或密码错误，请重新输入');
      } else if (errorObj.status === 400) {
        setErrorMessage('请求参数错误，请检查输入');
      } else if (errorObj.message && errorObj.message.includes('NetworkError')) {
        setErrorMessage('网络连接错误，请检查网络连接');
      } else {
        // 对于其他错误，提供通用错误信息
        setErrorMessage(errorObj.message || '登录过程中发生错误，请稍后重试');
      }
    } finally {
      setLoginLoading(false);
    }
  };

  const handleInputChange = (field: string, value: string | boolean) => {
    setLoginForm(prev => ({
      ...prev,
      [field]: value
    }));
  };

  // 如果仍在检查认证状态，则不显示登录表单
  if (checkingAuth) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center py-12">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-10 w-10 border-t-2 border-b-2 border-indigo-600 mb-4"></div>
          <p className="text-gray-600 dark:text-gray-300">正在检查登录状态...</p>
        </div>
      </div>
    );
  }
  
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center py-12">
      <div className="container mx-auto px-4">
        <div className="w-full max-w-md mx-auto bg-white dark:bg-gray-800 rounded-lg shadow-md p-8">
          <div className="text-center mb-8">
            <div className="flex justify-center mb-4">
              <div className="w-12 h-12 bg-indigo-600 rounded-lg flex items-center justify-center">
                <i className="fas fa-lock text-white"></i>
              </div>
            </div>
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white">登录您的账户</h2>
            <p className="mt-2 text-sm text-gray-600 dark:text-gray-300">
              或者
              <Link href="/register" className="font-medium text-indigo-600 hover:text-indigo-500 dark:text-indigo-400 dark:hover:text-indigo-300">
                {' '}创建新账户
              </Link>
            </p>
          </div>

          <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-1 mb-6">
            <div className="flex">
              <button
                onClick={() => setActiveMethod('password')}
                className={`flex-1 py-2 px-4 text-sm font-medium rounded-md transition-colors ${
                  activeMethod === 'password' 
                    ? 'bg-white text-gray-900 shadow dark:bg-gray-600 dark:text-white' 
                    : 'text-gray-500 dark:text-gray-400'
                }`}
              >
                <i className="fas fa-envelope mr-2"></i>
                密码登录
              </button>
              <button
                onClick={() => setActiveMethod('qr')}
                className={`flex-1 py-2 px-4 text-sm font-medium rounded-md transition-colors ${
                  activeMethod === 'qr' 
                    ? 'bg-white text-gray-900 shadow dark:bg-gray-600 dark:text-white' 
                    : 'text-gray-500 dark:text-gray-400'
                }`}
              >
                <i className="fas fa-qrcode mr-2"></i>
                二维码登录
              </button>
            </div>
          </div>

          {/* 显示错误消息 */}
          {errorMessage && (
            <div className="mb-4 p-3 bg-red-100 border border-red-400 text-red-700 rounded-md">
              {errorMessage}
            </div>
          )}

          {/* 密码登录表单 */}
          {activeMethod === 'password' && (
            <form onSubmit={handleLogin}>
              <div className="mb-4">
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <i className="fas fa-envelope text-gray-400"></i>
                  </div>
                  <input
                    type="email"
                    value={loginForm.email}
                    onChange={(e) => handleInputChange('email', e.target.value)}
                    placeholder="邮箱地址"
                    className="w-full pl-10 pr-3 py-3 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:bg-gray-600 dark:border-gray-500 dark:text-white"
                    required
                  />
                </div>
              </div>

              <div className="mb-4">
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <i className="fas fa-lock text-gray-400"></i>
                  </div>
                  <input
                    type={passwordVisible ? 'text' : 'password'}
                    value={loginForm.password}
                    onChange={(e) => handleInputChange('password', e.target.value)}
                    placeholder="密码"
                    className="w-full pl-10 pr-10 py-3 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:bg-gray-600 dark:border-gray-500 dark:text-white"
                    required
                  />
                  <button
                    type="button"
                    onClick={() => setPasswordVisible(!passwordVisible)}
                    className="absolute inset-y-0 right-0 pr-3 flex items-center"
                  >
                    <i className={`fas ${passwordVisible ? 'fa-eye-slash' : 'fa-eye'} text-gray-400`}></i>
                  </button>
                </div>
              </div>

              <div className="flex items-center justify-between mb-6">
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    checked={loginForm.rememberMe}
                    onChange={(e) => handleInputChange('rememberMe', e.target.checked)}
                    className="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded"
                  />
                  <span className="ml-2 text-sm text-gray-600 dark:text-gray-300">记住我</span>
                </label>
                <a href="#" className="text-sm text-indigo-600 hover:text-indigo-500 dark:text-indigo-400 dark:hover:text-indigo-300">
                  忘记密码?
                </a>
              </div>

              <button
                type="submit"
                disabled={loginLoading}
                className="w-full flex justify-center py-3 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50"
              >
                {loginLoading ? (
                  <span className="flex items-center">
                    <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    登录中...
                  </span>
                ) : '登录'}
              </button>
            </form>
          )}

          {/* 二维码登录 */}
          {activeMethod === 'qr' && (
            <div className="text-center">
              <div className="mb-6">
                <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">二维码登录</h3>
                <p className="text-sm text-gray-500 dark:text-gray-400">请使用手机扫描下方二维码登录</p>
              </div>

              <div className="flex flex-col items-center">
                {qrCodeImage ? (
                  <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm mb-4">
                    <img src={qrCodeImage} alt="登录二维码" className="w-48 h-48" />
                  </div>
                ) : (
                  <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm mb-4">
                    <div className="w-48 h-48 bg-gray-200 border-2 border-dashed rounded-xl flex items-center justify-center text-gray-500">
                      {qrStatus === 'expired' ? '二维码已过期' : '加载中...'}
                    </div>
                  </div>
                )}
                
                <p className="text-sm text-gray-600 dark:text-gray-300 flex items-center justify-center mb-2">
                  <i className="fas fa-mobile mr-2"></i>
                  打开手机客户端扫描二维码
                </p>
                
                {qrStatus === 'pending' && (
                  <div className="text-sm text-gray-500 dark:text-gray-400 mb-4">
                    二维码将在 <span className="font-medium">{countdown}</span> 秒后过期
                  </div>
                )}
                
                {qrStatus === 'scanned' && (
                  <div className="text-sm text-yellow-600 dark:text-yellow-400 mb-4">
                    <i className="fas fa-exclamation-circle mr-1"></i>请在手机上确认登录
                  </div>
                )}
                
                {qrStatus === 'confirmed' && (
                  <div className="text-sm text-green-600 dark:text-green-400 mb-4">
                    <i className="fas fa-check-circle mr-1"></i>登录成功，跳转中...
                  </div>
                )}
                
                {qrStatus === 'expired' && (
                  <div className="text-sm text-red-600 dark:text-red-400 mb-4">
                    <i className="fas fa-times-circle mr-1"></i>二维码已过期
                  </div>
                )}
                
                {(qrStatus === 'expired' || !qrCodeImage) && (
                  <button
                    onClick={refreshQRCode}
                    className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
                  >
                    <i className="fas fa-sync-alt mr-2"></i>刷新二维码
                  </button>
                )}
              </div>
            </div>
          )}

          {/* 社交登录分隔线 */}
          <div className="mt-8 flex items-center">
            <div className="flex-1 border-t border-gray-300 dark:border-gray-600"></div>
            <span className="px-4 text-sm text-gray-500 dark:text-gray-400">或使用社交账号登录</span>
            <div className="flex-1 border-t border-gray-300 dark:border-gray-600"></div>
          </div>

          {/* 社交登录按钮 */}
          <div className="mt-6 grid grid-cols-2 gap-3">
            <button
              type="button"
              className="w-full flex items-center justify-center py-2 px-4 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 dark:bg-gray-600 dark:text-white dark:border-gray-500 dark:hover:bg-gray-500"
            >
              <svg className="w-5 h-5 mr-2" viewBox="0 0 24 24">
                <path fill="currentColor" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                <path fill="currentColor" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                <path fill="currentColor" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                <path fill="currentColor" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
              </svg>
              Google
            </button>
            <button
              type="button"
              className="w-full flex items-center justify-center py-2 px-4 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 dark:bg-gray-600 dark:text-white dark:border-gray-500 dark:hover:bg-gray-500"
            >
              <svg className="w-5 h-5 mr-2" viewBox="0 0 24 24">
                <path fill="currentColor" d="M12.001 2c-5.525 0-10 4.475-10 10a9.994 9.994 0 0 0 6.837 9.488c.5.087.687-.213.687-.476c0-.237-.013-1.024-.013-1.862c-2.512.463-3.162-.612-3.362-1.175c-.113-.288-.6-1.175-1.025-1.413c-.35-.187-.85-.65-.013-.662c.788-.013 1.35.725 1.538 1.025c.9 1.512 2.337 1.087 2.912.825c.088-.65.35-1.087.638-1.337c-2.225-.25-4.55-1.112-4.55-4.937c0-1.088.387-1.987 1.025-2.687c-.1-.25-.45-1.275.1-2.65c0 0 .837-.262 2.75 1.026a9.28 9.28 0 0 1 2.5-.338c.85 0 1.7.112 2.5.337c1.913-1.3 2.75-1.024 2.75-1.024c.55 1.375.2 2.4.1 2.65c.637.7 1.025 1.587 1.025 2.687c0 3.838-2.337 4.688-4.563 4.938c.363.312.676.912.676 1.85c0 1.337-.013 2.412-.013 2.75c0 .262.188.574.688.474A10.016 10.016 0 0 0 22 12c0-5.525-4.475-10-10-10Z"/>
              </svg>
              GitHub
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default LoginPage;