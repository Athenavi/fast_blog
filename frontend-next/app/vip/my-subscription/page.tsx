'use client';

import React, {useEffect, useState} from 'react';
import {VIPService, type VIPSubscription} from '@/lib/api/index';
import Link from 'next/link';

const MySubscriptionPage = () => {
  const [activeSubscription, setActiveSubscription] = useState<VIPSubscription | undefined>();
  const [subscriptionHistory, setSubscriptionHistory] = useState<VIPSubscription[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // 相对时间格式化函数
  const formatDate = (dateString: string): string => {
    return new Date(dateString).toLocaleDateString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit'
    });
  };

  useEffect(() => {
    const fetchMySubscription = async () => {
      try {
        setLoading(true);
        const response = await VIPService.getMySubscription();
        
        if (response.success && response.data) {
          setActiveSubscription(response.data.active_subscription);
          setSubscriptionHistory(response.data.subscription_history || []);
        } else {
          setError(response.error || '获取订阅信息失败');
        }
      } catch (err) {
        console.error('获取订阅信息失败:', err);
        setError('获取订阅信息失败');
      } finally {
        setLoading(false);
      }
    };

    fetchMySubscription();
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 py-12">
        <div className="container mx-auto px-4 max-w-4xl">
          <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary mx-auto"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 py-12">
        <div className="container mx-auto px-4 max-w-4xl">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6 text-center">
            <p className="text-red-500">{error}</p>
            <Link href="/" className="mt-4 inline-block text-blue-600 hover:text-blue-800">
              返回首页
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 py-8">
      <div className="container mx-auto px-4 max-w-4xl">
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-6">
          <h1 className="text-2xl font-bold mb-6">我的VIP订阅</h1>

          {activeSubscription ? (
            // 当前订阅
            <div className="bg-gradient-to-r from-green-50 to-blue-50 dark:from-green-900 dark:to-blue-900 border border-green-200 dark:border-green-700 rounded-lg p-6 mb-6">
              <div className="flex justify-between items-start mb-4">
                <div>
                  <h3 className="text-xl font-semibold text-green-800 dark:text-green-300 flex items-center">
                    <i className="fas fa-check-circle mr-2"></i>有效订阅
                  </h3>
                  <p className="text-green-600 dark:text-green-400">您的VIP会员服务正常</p>
                </div>
                <span className="bg-green-100 text-green-800 dark:bg-green-800 dark:text-green-200 px-3 py-1 rounded-full text-sm font-medium">
                  有效期至 {formatDate(activeSubscription.expires_at)}
                </span>
              </div>

              <div className="grid md:grid-cols-3 gap-4">
                <div className="text-center">
                  <div className="text-2xl font-bold text-gray-900 dark:text-white">
                    {activeSubscription.plan_id ? `套餐${activeSubscription.plan_id}` : '未知套餐'}
                  </div>
                  <div className="text-gray-600 dark:text-gray-400">套餐类型</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-gray-900 dark:text-white">
                    VIP {activeSubscription.plan_id ? activeSubscription.plan_id : '未知等级'}
                  </div>
                  <div className="text-gray-600 dark:text-gray-400">会员等级</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-gray-900 dark:text-white">
                    ¥{activeSubscription.payment_amount || '未知'}
                  </div>
                  <div className="text-gray-600 dark:text-gray-400">支付金额</div>
                </div>
              </div>
            </div>
          ) : (
            // 无有效订阅
            <div className="bg-gradient-to-r from-yellow-50 to-orange-50 dark:from-yellow-900 dark:to-orange-900 border border-yellow-200 dark:border-yellow-700 rounded-lg p-6 mb-6">
              <div className="text-center py-8">
                <i className="fas fa-crown text-5xl text-yellow-500 mb-4"></i>
                <h3 className="text-xl font-semibold text-yellow-800 dark:text-yellow-300 mb-2">您还没有激活的VIP订阅</h3>
                <p className="text-yellow-600 dark:text-yellow-400 mb-4">立即订阅享受专属特权</p>
                <Link 
                  href="/vip/plans" 
                  className="bg-yellow-500 text-white px-6 py-2 rounded-lg hover:bg-yellow-600 transition"
                >
                  选择套餐
                </Link>
              </div>
            </div>
          )}

          {/* 订阅历史 */}
          <div>
            <h3 className="text-lg font-semibold mb-4">订阅历史</h3>
            {subscriptionHistory.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50 dark:bg-gray-700">
                    <tr>
                      <th className="px-4 py-2 text-left">套餐</th>
                      <th className="px-4 py-2 text-left">状态</th>
                      <th className="px-4 py-2 text-left">开始时间</th>
                      <th className="px-4 py-2 text-left">结束时间</th>
                      <th className="px-4 py-2 text-left">金额</th>
                    </tr>
                  </thead>
                  <tbody>
                    {subscriptionHistory.map((subscription, index) => (
                      <tr key={index} className="border-b border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-750">
                        <td className="px-4 py-3">{subscription.plan_id}</td>
                        <td className="px-4 py-3">
                          <span className={`px-2 py-1 rounded-full text-xs ${
                            subscription.status === 1 
                              ? 'bg-green-100 text-green-800 dark:bg-green-800 dark:text-green-200' 
                              : 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200'
                          }`}>
                            {subscription.status === 1 ? '有效' : subscription.status === -1 ? '已过期' : '其他'}
                          </span>
                        </td>
                        <td className="px-4 py-3">{formatDate(subscription.starts_at)}</td>
                        <td className="px-4 py-3">
                          {subscription.expires_at ? formatDate(subscription.expires_at) : '-'}
                        </td>
                        <td className="px-4 py-3">¥{subscription.payment_amount || '-'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="text-center py-8 text-gray-500 dark:text-gray-400">
                <i className="fas fa-history text-3xl mb-2"></i>
                <p>暂无订阅记录</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default MySubscriptionPage;