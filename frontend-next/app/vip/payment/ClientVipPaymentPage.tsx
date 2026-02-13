'use client';

import {useEffect, useState} from 'react';
import {useSearchParams} from 'next/navigation';
import {type CreatePaymentRequest, PaymentService, type VIPPlan, VIPService} from '@/lib/api';
import Link from 'next/link';

const VipPaymentPage = () => {
  const searchParams = useSearchParams();
  const planId = searchParams.get('planId');
  
  const [plan, setPlan] = useState<VIPPlan | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedMethod, setSelectedMethod] = useState<'alipay' | 'wechat' | null>(null);
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [showModal, setShowModal] = useState<boolean>(false);

  useEffect(() => {
    if (!planId) {
      setError('未指定套餐ID');
      setLoading(false);
      return;
    }

    const fetchPlanDetails = async () => {
      try {
        setLoading(true);
        const response = await VIPService.getVipPlans();
        
        if (response.success && response.data) {
          const foundPlan = response.data.plans.find(p => p.id === parseInt(planId));
          if (foundPlan) {
            setPlan(foundPlan);
          } else {
            setError('未找到指定的套餐');
          }
        } else {
          setError(response.error || '获取套餐信息失败');
        }
      } catch (err) {
        console.error('获取套餐信息失败:', err);
        setError('获取套餐信息失败');
      } finally {
        setLoading(false);
      }
    };

    fetchPlanDetails();
  }, [planId]);

  const handlePayment = async () => {
    if (!plan || !selectedMethod) {
      alert('请先选择支付方式');
      return;
    }

    setIsProcessing(true);
    try {
      const paymentData: CreatePaymentRequest = {
        user_id: 1, // 这里应该是当前用户ID，实际项目中应从认证状态获取
        plan_id: plan.id,
        payment_method: selectedMethod
      };

      const response = await PaymentService.createPayment(paymentData);

      if (response.success && response.data) {
        setShowModal(true);
        
        // 根据支付方式处理
        if (selectedMethod === 'alipay' && response.data.payment_data.pay_url) {
          // 直接跳转到支付宝支付页面
          window.location.href = response.data.payment_data.pay_url;
        } else if (selectedMethod === 'wechat') {
          // 微信支付通常显示二维码
          console.log('微信支付二维码数据:', response.data.payment_data.qr_code);
          // 这里可以显示二维码供用户扫描
        }
      } else {
        alert(response.error || '支付请求失败');
      }
    } catch (err) {
      console.error('支付请求失败:', err);
      alert('支付请求失败');
    } finally {
      setIsProcessing(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 py-12">
        <div className="container mx-auto px-4 max-w-2xl">
          <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary mx-auto"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 py-12">
        <div className="container mx-auto px-4 max-w-2xl">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6 text-center">
            <p className="text-red-500">{error}</p>
            <Link href="/vip/plans" className="mt-4 inline-block text-blue-600 hover:text-blue-800">
              返回套餐选择
            </Link>
          </div>
        </div>
      </div>
    );
  }

  if (!plan) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 py-12">
        <div className="container mx-auto px-4 max-w-2xl">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6 text-center">
            <p className="text-red-500">未找到套餐信息</p>
            <Link href="/vip/plans" className="mt-4 inline-block text-blue-600 hover:text-blue-800">
              返回套餐选择
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 py-8">
      <div className="max-w-2xl mx-auto">
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-6 mb-6">
          <div className="text-center mb-8">
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">确认支付订单</h1>
            <p className="text-gray-600 dark:text-gray-400">请选择支付方式完成VIP会员购买</p>
          </div>

          {/* 订单信息 */}
          <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-6 mb-8">
            <h2 className="text-lg font-semibold mb-4">订单详情</h2>
            <div className="space-y-3">
              <div className="flex justify-between">
                <span className="text-gray-600 dark:text-gray-300">套餐名称:</span>
                <span className="font-medium">{plan.name}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600 dark:text-gray-300">套餐等级:</span>
                <span className="font-medium">VIP {plan.level}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600 dark:text-gray-300">有效期:</span>
                <span className="font-medium">{plan.duration_days} 天</span>
              </div>
              <div className="flex justify-between pt-3 border-t border-gray-200 dark:border-gray-600">
                <span className="text-lg font-semibold">应付金额:</span>
                <span className="text-2xl font-bold text-purple-600 dark:text-purple-400">¥{plan.price}</span>
              </div>
            </div>
          </div>

          {/* 支付方式选择 */}
          <div className="mb-8">
            <h2 className="text-lg font-semibold mb-4">选择支付方式</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* 支付宝支付 */}
              <div 
                className={`border rounded-lg p-4 hover:border-purple-500 hover:bg-purple-50 dark:hover:bg-purple-900/20 transition cursor-pointer ${
                  selectedMethod === 'alipay' 
                    ? 'border-purple-500 bg-purple-50 dark:bg-purple-900/20' 
                    : 'border-gray-200 dark:border-gray-700'
                }`}
                onClick={() => setSelectedMethod('alipay')}
              >
                <div className="flex items-center">
                  <div className="w-12 h-12 bg-blue-500 rounded-full flex items-center justify-center mr-4">
                    <i className="fab fa-alipay text-white text-2xl"></i>
                  </div>
                  <div>
                    <h3 className="font-medium">支付宝</h3>
                    <p className="text-sm text-gray-600 dark:text-gray-400">推荐使用支付宝APP扫码支付</p>
                  </div>
                  <div className="ml-auto">
                    <div className={`w-5 h-5 rounded-full border flex items-center justify-center ${
                      selectedMethod === 'alipay' 
                        ? 'border-purple-500' 
                        : 'border-gray-300 dark:border-gray-600'
                    }`}>
                      <div className={`w-3 h-3 rounded-full ${
                        selectedMethod === 'alipay' ? 'bg-purple-500' : ''
                      }`}></div>
                    </div>
                  </div>
                </div>
              </div>

              {/* 微信支付 */}
              <div 
                className={`border rounded-lg p-4 hover:border-green-500 hover:bg-green-50 dark:hover:bg-green-900/20 transition cursor-pointer ${
                  selectedMethod === 'wechat' 
                    ? 'border-green-500 bg-green-50 dark:bg-green-900/20' 
                    : 'border-gray-200 dark:border-gray-700'
                }`}
                onClick={() => setSelectedMethod('wechat')}
              >
                <div className="flex items-center">
                  <div className="w-12 h-12 bg-green-500 rounded-full flex items-center justify-center mr-4">
                    <i className="fab fa-weixin text-white text-2xl"></i>
                  </div>
                  <div>
                    <h3 className="font-medium">微信支付</h3>
                    <p className="text-sm text-gray-600 dark:text-gray-400">微信APP扫码支付</p>
                  </div>
                  <div className="ml-auto">
                    <div className={`w-5 h-5 rounded-full border flex items-center justify-center ${
                      selectedMethod === 'wechat' 
                        ? 'border-green-500' 
                        : 'border-gray-300 dark:border-gray-600'
                    }`}>
                      <div className={`w-3 h-3 rounded-full ${
                        selectedMethod === 'wechat' ? 'bg-green-500' : ''
                      }`}></div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* 支付按钮 */}
          <div className="text-center">
            <button
              className={`${
                selectedMethod 
                  ? 'bg-purple-600 text-white hover:bg-purple-700' 
                  : 'bg-gray-300 text-gray-500 cursor-not-allowed'
              } px-8 py-3 rounded-lg font-semibold transition`}
              disabled={!selectedMethod || isProcessing}
              onClick={handlePayment}
            >
              {isProcessing ? '处理中...' : selectedMethod ? '立即支付' : '请选择支付方式'}
            </button>
          </div>
        </div>
      </div>

      {/* 支付模态框 */}
      {showModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-gray-800 rounded-lg p-6 max-w-md w-full mx-4">
            <div className="text-center">
              <h3 className="text-xl font-semibold mb-2">正在跳转到支付页面</h3>
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600 mx-auto mb-4"></div>
              <p className="text-gray-600 dark:text-gray-400">请稍候...</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default VipPaymentPage;