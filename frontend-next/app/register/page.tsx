'use client';

import React, {useState} from 'react';
import Link from 'next/link';
import {useRouter} from 'next/navigation';
import {apiClient} from '@/lib/api';

const RegisterPage = () => {
  const router = useRouter();
  const [currentStep, setCurrentStep] = useState(1);
  const totalSteps = 4;
  const [registerForm, setRegisterForm] = useState({
    username: '',
    email: '',
    password: '',
    confirmPassword: '',
    displayName: '',
    bio: '',
    location: '',
    website: '',
    profilePrivate: false,
    newsletter: false,
    marketingEmails: false,
    terms: false,
    locale: 'zh_CN'
  });
  const [registerLoading, setRegisterLoading] = useState(false);
  const [passwordVisible, setPasswordVisible] = useState(true);
  const [usernameFeedback, setUsernameFeedback] = useState<{ message: string; type: 'success' | 'error' } | null>(null);
  const [emailFeedback, setEmailFeedback] = useState<{ message: string; type: 'success' | 'error' } | null>(null);
  const [confirmPasswordFeedback, setConfirmPasswordFeedback] = useState<{ message: string; type: 'success' | 'error' } | null>(null);
  
  // 密码强度相关
  const [strengthPercentage, setStrengthPercentage] = useState(0);
  const [strengthText, setStrengthText] = useState('');
  const [strengthClass, setStrengthClass] = useState('');
  const [strengthColor, setStrengthColor] = useState('#ccc');
  const [requirements, setRequirements] = useState({
    length: false,
    uppercase: false,
    lowercase: false,
    number: false,
    special: false
  });

  const progressPercentage = (currentStep / totalSteps) * 100;

  const handleInputChange = (field: string, value: any) => {
    setRegisterForm(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const handleNext = async () => {
    if (currentStep < totalSteps) {
      if (currentStep === 1) {
        // 验证第一步
        const usernameValid = checkUsernameAvailability(registerForm.username);
        const emailValid = checkEmailAvailability(registerForm.email);
        
        if (!usernameValid || !emailValid) {
          return;
        }
      } else if (currentStep === 2) {
        // 验证第二步
        if (registerForm.password !== registerForm.confirmPassword) {
          setConfirmPasswordFeedback({ message: '密码不匹配', type: 'error' });
          return;
        } else {
          setConfirmPasswordFeedback({ message: '密码匹配', type: 'success' });
        }
      }
      
      setCurrentStep(prev => prev + 1);
    }
  };

  const handlePrevious = () => {
    if (currentStep > 1) {
      setCurrentStep(prev => prev - 1);
    }
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    
    // 验证必填字段
    if (!registerForm.username || !registerForm.email || !registerForm.password) {
      console.error('用户名、邮箱和密码不能为空');
      alert('用户名、邮箱和密码不能为空');
      return;
    }
    
    // 验证密码确认
    if (registerForm.password !== registerForm.confirmPassword) {
      setConfirmPasswordFeedback({ message: '密码不匹配', type: 'error' });
      return;
    }
    
    if (!registerForm.terms) {
      console.error('请同意服务条款和隐私政策');
      alert('请在第4步"偏好设置和条款"中勾选"我同意服务条款和隐私政策"');
      return;
    }
    
    setRegisterLoading(true);
    
    try {
      // 调用后端注册API
      const response = await apiClient.post('/auth/register', {
        username: registerForm.username,
        email: registerForm.email,
        password: registerForm.password
      });
      
      if (response && response.success) {
        console.log('注册成功:', response.data);
        // 注册成功后跳转到登录页面
        router.push('/login?registered=true');
        router.refresh(); // 刷新路由以更新UI
      } else {
        console.error('注册失败:', response?.error || '未知错误');
        // 显示错误消息
        alert(response?.error || '注册失败，请稍后重试');
      }
    } catch (error) {
      console.error('注册过程中发生错误:', error);
      alert('网络错误或服务器无响应，请稍后重试');
    } finally {
      setRegisterLoading(false);
    }
  };

  const checkUsernameAvailability = (username: string) => {
    // 模拟检查用户名可用性
    if (username.length < 3) {
      setUsernameFeedback({ message: '用户名至少需要3个字符', type: 'error' });
      return false;
    }
    setUsernameFeedback({ message: '用户名可用', type: 'success' });
    return true;
  };

  const checkEmailAvailability = (email: string) => {
    // 模拟检查邮箱可用性
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
      setEmailFeedback({ message: '邮箱格式不正确', type: 'error' });
      return false;
    }
    setEmailFeedback({ message: '邮箱可用', type: 'success' });
    return true;
  };

  const checkPasswordStrength = (password: string) => {
    const reqs = {
      length: password.length >= 8,
      uppercase: /[A-Z]/.test(password),
      lowercase: /[a-z]/.test(password),
      number: /\d/.test(password),
      special: /[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>?]/.test(password)
    };

    setRequirements(reqs);

    const score = Object.values(reqs).filter(Boolean).length;

    if (score === 0) {
      setStrengthPercentage(0);
      setStrengthText('弱');
      setStrengthClass('text-red-500');
      setStrengthColor('#ccc');
    } else if (score <= 2) {
      setStrengthPercentage(25);
      setStrengthText('弱');
      setStrengthClass('text-red-500');
      setStrengthColor('#ef4444');
    } else if (score <= 3) {
      setStrengthPercentage(50);
      setStrengthText('中等');
      setStrengthClass('text-yellow-500');
      setStrengthColor('#f59e0b');
    } else if (score <= 4) {
      setStrengthPercentage(75);
      setStrengthText('强');
      setStrengthClass('text-blue-500');
      setStrengthColor('#3b82f6');
    } else {
      setStrengthPercentage(100);
      setStrengthText('很强');
      setStrengthClass('text-green-500');
      setStrengthColor('#10b981');
    }
  };

  // 监听密码变化
  React.useEffect(() => {
    if (registerForm.password) {
      checkPasswordStrength(registerForm.password);
    } else {
      // 如果密码为空，重置强度指标
      setStrengthPercentage(0);
      setStrengthText('');
      setStrengthClass('');
      setStrengthColor('#ccc');
      setRequirements({
        length: false,
        uppercase: false,
        lowercase: false,
        number: false,
        special: false
      });
    }
  }, [registerForm.password]);

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center py-12">
      <div className="container mx-auto px-4">
        <div className="w-full max-w-md mx-auto bg-white dark:bg-gray-800 rounded-lg shadow-md p-8">
          {/* 注册头部 */}
          <div className="text-center mb-8">
            <div className="flex justify-center mb-4">
              <div className="w-12 h-12 bg-indigo-600 rounded-lg flex items-center justify-center">
                <i className="fas fa-user-plus text-white"></i>
              </div>
            </div>
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white">创建新账户</h2>
            <p className="mt-2 text-sm text-gray-600 dark:text-gray-300">
              已有账户?
              <Link href="/login" className="font-medium text-indigo-600 hover:text-indigo-500 dark:text-indigo-400 dark:hover:text-indigo-300">
                {' '}立即登录
              </Link>
            </p>
          </div>

          {/* 注册表单容器 */}
          <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-6">
            {/* 注册进度 */}
            <div className="mb-6">
              <div className="flex justify-between items-center mb-2">
                <span className="text-xs font-medium text-indigo-600 dark:text-indigo-400">注册进度</span>
                <span className="text-xs font-medium text-indigo-600 dark:text-indigo-400">{currentStep}/{totalSteps}</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2.5 dark:bg-gray-600">
                <div 
                  className="bg-indigo-600 h-2.5 rounded-full" 
                  style={{ width: `${progressPercentage}%` }}
                ></div>
              </div>
            </div>

            <form onSubmit={handleRegister}>
              {/* 步骤1: 基本信息 */}
              {currentStep === 1 && (
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                      用户名
                    </label>
                    <div className="relative">
                      <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                        <i className="fas fa-user text-gray-400"></i>
                      </div>
                      <input
                        type="text"
                        value={registerForm.username}
                        onChange={(e) => handleInputChange('username', e.target.value)}
                        placeholder="用户名"
                        className="w-full pl-10 pr-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:bg-gray-600 dark:border-gray-500 dark:text-white"
                      />
                    </div>
                    {usernameFeedback && (
                      <div className={`mt-1 text-xs ${usernameFeedback.type === 'success' ? 'text-green-600' : 'text-red-600'}`}>
                        {usernameFeedback.message}
                      </div>
                    )}
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                      邮箱地址
                    </label>
                    <div className="relative">
                      <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                        <i className="fas fa-envelope text-gray-400"></i>
                      </div>
                      <input
                        type="email"
                        value={registerForm.email}
                        onChange={(e) => handleInputChange('email', e.target.value)}
                        placeholder="邮箱地址"
                        className="w-full pl-10 pr-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:bg-gray-600 dark:border-gray-500 dark:text-white"
                      />
                    </div>
                    {emailFeedback && (
                      <div className={`mt-1 text-xs ${emailFeedback.type === 'success' ? 'text-green-600' : 'text-red-600'}`}>
                        {emailFeedback.message}
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* 步骤2: 密码设置 */}
              {currentStep === 2 && (
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                      密码
                    </label>
                    <div className="relative">
                      <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                        <i className="fas fa-lock text-gray-400"></i>
                      </div>
                      <input
                        type={passwordVisible ? 'text' : 'password'}
                        value={registerForm.password}
                        onChange={(e) => handleInputChange('password', e.target.value)}
                        placeholder="密码"
                        className="w-full pl-10 pr-10 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:bg-gray-600 dark:border-gray-500 dark:text-white"
                      />
                      <button
                        type="button"
                        onClick={() => setPasswordVisible(!passwordVisible)}
                        className="absolute inset-y-0 right-0 pr-3 flex items-center"
                      >
                        <i className={`fas ${passwordVisible ? 'fa-eye-slash' : 'fa-eye'} text-gray-400`}></i>
                      </button>
                    </div>
                    
                    {/* 密码强度指示器 */}
                    <div className="mt-4">
                      <div className="flex justify-between items-center mb-2">
                        <span className="text-xs text-gray-500 dark:text-gray-400">密码强度</span>
                        <span className={`text-xs ${strengthClass}`}>{strengthText}</span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-2.5 dark:bg-gray-600">
                        <div 
                          className="h-2.5 rounded-full" 
                          style={{ width: `${strengthPercentage}%`, backgroundColor: strengthColor }}
                        ></div>
                      </div>
                      
                      {/* 密码要求列表 */}
                      <div className="mt-4 space-y-2">
                        <div className="flex items-center">
                          <i className={`fas mr-2 ${requirements.length ? 'text-green-600' : 'text-gray-500'}`}>
                            {requirements.length ? 'fa-check-circle' : 'fa-times-circle'}
                          </i>
                          <span className={`text-xs ${requirements.length ? 'text-green-600' : 'text-gray-500'}`}>
                            至少8个字符
                          </span>
                        </div>
                        <div className="flex items-center">
                          <i className={`fas mr-2 ${requirements.uppercase ? 'text-green-600' : 'text-gray-500'}`}>
                            {requirements.uppercase ? 'fa-check-circle' : 'fa-times-circle'}
                          </i>
                          <span className={`text-xs ${requirements.uppercase ? 'text-green-600' : 'text-gray-500'}`}>
                            包含大写字母
                          </span>
                        </div>
                        <div className="flex items-center">
                          <i className={`fas mr-2 ${requirements.lowercase ? 'text-green-600' : 'text-gray-500'}`}>
                            {requirements.lowercase ? 'fa-check-circle' : 'fa-times-circle'}
                          </i>
                          <span className={`text-xs ${requirements.lowercase ? 'text-green-600' : 'text-gray-500'}`}>
                            包含小写字母
                          </span>
                        </div>
                        <div className="flex items-center">
                          <i className={`fas mr-2 ${requirements.number ? 'text-green-600' : 'text-gray-500'}`}>
                            {requirements.number ? 'fa-check-circle' : 'fa-times-circle'}
                          </i>
                          <span className={`text-xs ${requirements.number ? 'text-green-600' : 'text-gray-500'}`}>
                            包含数字
                          </span>
                        </div>
                        <div className="flex items-center">
                          <i className={`fas mr-2 ${requirements.special ? 'text-green-600' : 'text-gray-500'}`}>
                            {requirements.special ? 'fa-check-circle' : 'fa-times-circle'}
                          </i>
                          <span className={`text-xs ${requirements.special ? 'text-green-600' : 'text-gray-500'}`}>
                            包含特殊字符
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                      确认密码
                    </label>
                    <div className="relative">
                      <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                        <i className="fas fa-lock text-gray-400"></i>
                      </div>
                      <input
                        type="password"
                        value={registerForm.confirmPassword}
                        onChange={(e) => handleInputChange('confirmPassword', e.target.value)}
                        placeholder="确认密码"
                        className="w-full pl-10 pr-10 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:bg-gray-600 dark:border-gray-500 dark:text-white"
                      />
                      <div className="absolute inset-y-0 right-0 pr-3 flex items-center">
                        <i className={`fas ${
                          registerForm.confirmPassword && registerForm.password === registerForm.confirmPassword 
                            ? 'fa-check-circle text-green-500' 
                            : registerForm.confirmPassword && registerForm.password !== registerForm.confirmPassword 
                              ? 'fa-times-circle text-red-500' 
                              : 'fa-lock text-gray-400'
                        }`}></i>
                      </div>
                    </div>
                    {confirmPasswordFeedback && (
                      <div className={`mt-1 text-xs ${confirmPasswordFeedback.type === 'success' ? 'text-green-600' : 'text-red-600'}`}>
                        {confirmPasswordFeedback.message}
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* 步骤3: 个人信息 */}
              {currentStep === 3 && (
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                      显示名称
                    </label>
                    <input
                      type="text"
                      value={registerForm.displayName}
                      onChange={(e) => handleInputChange('displayName', e.target.value)}
                      placeholder="显示名称"
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:bg-gray-600 dark:border-gray-500 dark:text-white"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                      个人简介
                    </label>
                    <textarea
                      value={registerForm.bio}
                      onChange={(e) => handleInputChange('bio', e.target.value)}
                      placeholder="个人简介"
                      rows={3}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:bg-gray-600 dark:border-gray-500 dark:text-white"
                    />
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                        位置
                      </label>
                      <input
                        type="text"
                        value={registerForm.location}
                        onChange={(e) => handleInputChange('location', e.target.value)}
                        placeholder="位置"
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:bg-gray-600 dark:border-gray-500 dark:text-white"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                        网站
                      </label>
                      <input
                        type="text"
                        value={registerForm.website}
                        onChange={(e) => handleInputChange('website', e.target.value)}
                        placeholder="网站"
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:bg-gray-600 dark:border-gray-500 dark:text-white"
                      />
                    </div>
                  </div>
                </div>
              )}

              {/* 步骤4: 偏好设置和条款 */}
              {currentStep === 4 && (
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                      语言偏好
                    </label>
                    <select
                      value={registerForm.locale}
                      onChange={(e) => handleInputChange('locale', e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:bg-gray-600 dark:border-gray-500 dark:text-white"
                    >
                      <option value="zh_CN">中文</option>
                      <option value="en">English</option>
                    </select>
                  </div>

                  <div className="space-y-2">
                    <label className="flex items-center">
                      <input
                        type="checkbox"
                        checked={registerForm.profilePrivate}
                        onChange={(e) => handleInputChange('profilePrivate', e.target.checked)}
                        className="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded"
                      />
                      <span className="ml-2 text-sm text-gray-700 dark:text-gray-300">
                        私密个人资料
                      </span>
                    </label>

                    <label className="flex items-center">
                      <input
                        type="checkbox"
                        checked={registerForm.newsletter}
                        onChange={(e) => handleInputChange('newsletter', e.target.checked)}
                        className="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded"
                      />
                      <span className="ml-2 text-sm text-gray-700 dark:text-gray-300">
                        订阅新闻通讯
                      </span>
                    </label>

                    <label className="flex items-center">
                      <input
                        type="checkbox"
                        checked={registerForm.marketingEmails}
                        onChange={(e) => handleInputChange('marketingEmails', e.target.checked)}
                        className="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded"
                      />
                      <span className="ml-2 text-sm text-gray-700 dark:text-gray-300">
                        接收营销邮件
                      </span>
                    </label>

                    <label className="flex items-start">
                      <input
                        type="checkbox"
                        checked={registerForm.terms}
                        onChange={(e) => handleInputChange('terms', e.target.checked)}
                        className="mt-1 h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded"
                      />
                      <span className="ml-2 text-sm text-gray-700 dark:text-gray-300">
                        我同意
                        <a href="#" className="text-indigo-600 hover:text-indigo-500 dark:text-indigo-400 dark:hover:text-indigo-300">
                          {' '}服务条款
                        </a>
                        {' '}和
                        <a href="#" className="text-indigo-600 hover:text-indigo-500 dark:text-indigo-400 dark:hover:text-indigo-300">
                          {' '}隐私政策
                        </a>
                      </span>
                    </label>
                  </div>
                </div>
              )}

              {/* 导航按钮 */}
              <div className="mt-6 flex items-center justify-between">
                {currentStep > 1 && (
                  <button
                    type="button"
                    onClick={handlePrevious}
                    className="flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 dark:bg-gray-600 dark:text-white dark:border-gray-500 dark:hover:bg-gray-500"
                  >
                    <i className="fas fa-arrow-left mr-2"></i>
                    上一步
                  </button>
                )}

                {currentStep < totalSteps ? (
                  <button
                    type="button"
                    onClick={handleNext}
                    className="ml-auto flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
                  >
                    下一步
                    <i className="fas fa-arrow-right ml-2"></i>
                  </button>
                ) : (
                  <button
                    type="submit"
                    disabled={registerLoading}
                    className="ml-auto flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 disabled:opacity-50"
                  >
                    {registerLoading ? (
                      <span className="flex items-center">
                        <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                        </svg>
                        注册中...
                      </span>
                    ) : (
                      <>
                        <i className="fas fa-user-plus mr-2"></i>
                        创建账户
                      </>
                    )}
                  </button>
                )}
              </div>
            </form>
          </div>

          {/* 社交注册分隔线 */}
          <div className="mt-6 flex items-center">
            <div className="flex-1 border-t border-gray-300 dark:border-gray-600"></div>
            <span className="px-4 text-sm text-gray-500 dark:text-gray-400">或使用社交账号注册</span>
            <div className="flex-1 border-t border-gray-300 dark:border-gray-600"></div>
          </div>

          {/* 社交注册按钮 */}
          <div className="mt-6 grid grid-cols-2 gap-3">
            <button
              type="button"
              className="w-full flex items-center justify-center py-2 px-4 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 dark:bg-gray-600 dark:text-white dark:border-gray-500 dark:hover:bg-gray-500"
            >
              <svg className="w-5 h-5 mr-2" viewBox="0 0 24 24">
                <path fill="currentColor" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                <path fill="currentColor" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                <path fill="currentColor" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66 2.84.81-.62z"/>
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
};

export default RegisterPage;