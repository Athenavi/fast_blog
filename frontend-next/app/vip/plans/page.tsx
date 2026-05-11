'use client';

import React, {useEffect, useState} from 'react';
import {useRouter} from 'next/navigation';
import Link from 'next/link';

interface VipPlan {
  id: number;
  name: string;
  price: number;
  original_price?: number;
  duration_days: number;
  level: number;
  daily_cost?: number;
}

interface Feature {
  id: number;
  name: string;
  description: string;
  required_level: number;
}

const VipPlansPage = () => {
  const router = useRouter();
  const [plans, setPlans] = useState<VipPlan[]>([]);
  const [features, setFeatures] = useState<Feature[]>([]);
  const [userVipLevel, setUserVipLevel] = useState(0);

  // 模拟加载VIP计划数据
  useEffect(() => {
    // 在真实实现中，这里会调用API
    // const loadPlans = async () => {
    //   try {
    //     const response = await vipService.getVipPlans()
    //     if (response.success) {
    //       setPlans(response.data.plans)
    //       setFeatures(response.data.features)
    //     }
    //   } catch (error) {
    //     console.error('加载VIP计划失败:', error)
    //   }
    // }

    // 模拟数据
    setTimeout(() => {
      const mockPlans: VipPlan[] = [
        {
          id: 1,
          name: 'VIP 1级',
          price: 9.9,
          original_price: 19.9,
          duration_days: 30,
          level: 1,
          daily_cost: 9.9 / 30
        },
        {
          id: 2,
          name: 'VIP 2级',
          price: 19.9,
          original_price: 29.9,
          duration_days: 30,
          level: 2,
          daily_cost: 19.9 / 30
        },
        {
          id: 3,
          name: 'VIP 3级',
          price: 29.9,
          original_price: 39.9,
          duration_days: 30,
          level: 3,
          daily_cost: 29.9 / 30
        }
      ];

      const mockFeatures: Feature[] = [
        {
          id: 1,
          name: "专属内容访问",
          description: "访问只有VIP用户才能看到的独家内容",
          required_level: 1
        },
        {
          id: 2,
          name: "无广告体验",
          description: "享受完全无广告的清爽浏览体验",
          required_level: 1
        },
        {
          id: 3,
          name: "优先客服支持",
          description: "获得VIP专属客服通道，优先解决问题",
          required_level: 2
        },
        {
          id: 4,
          name: "高级个性化设置",
          description: "解锁更多个性化主题和功能选项",
          required_level: 2
        },
        {
          id: 5,
          name: "专属活动参与",
          description: "参加仅限VIP用户参与的特别活动",
          required_level: 3
        },
        {
          id: 6,
          name: "专属内容创作工具",
          description: "使用高级内容创作工具和资源",
          required_level: 3
        }
      ];

      setPlans(mockPlans);
      setFeatures(mockFeatures);
      setUserVipLevel(0); // 模拟用户VIP等级
    }, 500);
  }, []);

  const getDiscountPercent = (originalPrice: number, currentPrice: number) => {
    if (!originalPrice || originalPrice <= currentPrice) return 0;
    return Math.round(((originalPrice - currentPrice) / originalPrice) * 100);
  };

  const upgradeToPlan = (planId: number) => {
    // 在真实实现中，这里会检查用户认证状态
    // if (!userStore.isAuthenticated) {
    //   router.push(`/login?next=${encodeURIComponent(router.currentRoute.value.fullPath)}`)
    //   return
    // }
    
    router.push(`/vip/payment?planId=${planId}`);
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 py-12">
      <div className="max-w-6xl mx-auto p-6">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">选择适合您的VIP套餐</h1>
          <p className="text-gray-600 dark:text-gray-400">多种套餐选择，满足不同需求</p>
        </div>

        <div className="grid lg:grid-cols-3 gap-8 mb-8">
          {plans.map((plan) => (
            <div 
              key={plan.id}
              className={`bg-white rounded-xl shadow-lg border ${
                plan.level === 2 
                  ? 'border-purple-500 ring-4 ring-purple-100 transform scale-105 dark:ring-purple-900 dark:border-purple-600' 
                  : 'dark:bg-gray-800 dark:border-gray-700'
              }`}
            >
              {plan.level === 2 && (
                <div className="bg-purple-500 text-white text-center py-2 rounded-t-xl dark:bg-purple-600">
                  <i className="fas fa-crown mr-2"></i>最受欢迎
                </div>
              )}

              <div className="p-8">
                <div className="text-center mb-6">
                  <h3 className="text-2xl font-bold text-gray-900 dark:text-white">{plan.name}</h3>
                  <div className="my-4">
                    <span className="text-4xl font-bold text-purple-600 dark:text-purple-400">¥{plan.price}</span>
                    {plan.original_price && plan.original_price > plan.price && (
                      <>
                        <span className="text-gray-400 line-through ml-2 dark:text-gray-500">¥{plan.original_price}</span>
                        <span className="bg-red-100 text-red-800 text-xs font-semibold ml-2 px-2.5 py-0.5 rounded dark:bg-red-900 dark:text-red-200">
                          {getDiscountPercent(plan.original_price, plan.price)}% OFF
                        </span>
                      </>
                    )}
                    <span className="text-gray-600 block mt-1 dark:text-gray-400">/ {plan.duration_days}天</span>
                  </div>
                  
                  {/* 日均费用 */}
                  {plan.daily_cost && (
                    <p className="text-green-600 font-semibold dark:text-green-400">平均每天仅 ¥{plan.daily_cost.toFixed(2)}</p>
                  )}
                </div>

                <ul className="space-y-3 mb-8">
                  {features.map((feature) => (
                    <li 
                      key={feature.id}
                      className={`flex items-center ${
                        feature.required_level <= plan.level 
                          ? 'text-gray-800 dark:text-gray-200' 
                          : 'text-gray-400 dark:text-gray-500'
                      }`}
                    >
                      <i 
                        className={`fas mr-3 ${
                          feature.required_level <= plan.level 
                            ? 'fa-check text-green-500' 
                            : 'fa-times text-gray-300 dark:text-gray-600'
                        }`}
                      ></i>
                      <span>{feature.name}</span>
                      {feature.required_level > plan.level && (
                        <span className="ml-2 text-xs bg-gray-100 px-2 py-1 rounded dark:bg-gray-700 dark:text-gray-300">
                          VIP {feature.required_level}
                        </span>
                      )}
                    </li>
                  ))}
                </ul>
                
                <div className="flex justify-center">
                  {userVipLevel < plan.level ? (
                    <button
                      onClick={() => upgradeToPlan(plan.id)}
                      className="bg-purple-600 text-white px-4 py-2 rounded-lg hover:bg-purple-700 transition-colors dark:bg-purple-600 dark:hover:bg-purple-700"
                    >
                      立即升级
                    </button>
                  ) : userVipLevel === plan.level ? (
                    <button
                      className="bg-gray-300 text-gray-800 px-4 py-2 rounded-lg dark:bg-gray-600 dark:text-gray-300"
                      disabled
                    >
                      已订阅相同等级
                    </button>
                  ) : (
                    <button
                      className="bg-gray-300 text-gray-800 px-4 py-2 rounded-lg dark:bg-gray-600 dark:text-gray-300"
                      disabled
                    >
                      已有更高等级
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* 常见问题 */}
        <div className="bg-white rounded-lg shadow-sm p-6 dark:bg-gray-800 dark:border-gray-700">
          <h2 className="text-2xl font-bold mb-6 dark:text-white">常见问题</h2>
          <div className="grid md:grid-cols-2 gap-6">
            <div>
              <h3 className="font-semibold mb-2 dark:text-white">Q: VIP会员可以随时取消吗？</h3>
              <p className="text-gray-600 dark:text-gray-400">A: 是的，VIP会员服务按周期计费，您可以随时取消自动续费。</p>
            </div>
            <div>
              <h3 className="font-semibold mb-2 dark:text-white">Q: 购买后可以退款吗？</h3>
              <p className="text-gray-600 dark:text-gray-400">A: 虚拟商品一经购买概不退款，请在购买前确认需求。</p>
            </div>
            <div>
              <h3 className="font-semibold mb-2 dark:text-white">Q: 可以同时拥有多个套餐吗？</h3>
              <p className="text-gray-600 dark:text-gray-400">A: 不可以，每个用户只能激活一个VIP套餐。</p>
            </div>
            <div>
              <h3 className="font-semibold mb-2 dark:text-white">Q: VIP特权包含哪些内容？</h3>
              <p className="text-gray-600 dark:text-gray-400">
                A: 包含专属内容、去广告、个性化功能等，具体请查看
                <Link href="/vip/features" className="text-purple-600 hover:underline dark:text-purple-400">特权详情</Link>。
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default VipPlansPage;