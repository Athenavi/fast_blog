'use client';

import React, {useEffect, useState} from 'react';
import {type VIPFeature, VIPService} from '@/lib/api';
import Link from 'next/link';

const VIPFeaturesPage = () => {
  const [featuresByLevel, setFeaturesByLevel] = useState<Record<number, VIPFeature[]>>({});
  const [features, setFeatures] = useState<VIPFeature[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchVipFeatures = async () => {
      try {
        setLoading(true);
        const response = await VIPService.getVipFeatures();
        
        if (response.success && response.data) {
          setFeaturesByLevel(response.data.features_by_level || {});
          setFeatures(response.data.features || []);
        } else {
          setError(response.error || '获取VIP特权失败');
        }
      } catch (err) {
        console.error('获取VIP特权失败:', err);
        setError('获取VIP特权失败');
      } finally {
        setLoading(false);
      }
    };

    fetchVipFeatures();
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 py-12">
        <div className="container mx-auto px-4 max-w-6xl">
          <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary mx-auto"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 py-12">
        <div className="container mx-auto px-4 max-w-6xl">
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
      <div className="container mx-auto px-4 max-w-6xl">
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-6 mb-6">
          <div className="text-center mb-8">
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">VIP会员特权</h1>
            <p className="text-gray-600 dark:text-gray-400">尊享专属权益，提升您的使用体验</p>
          </div>

          {/* 特权等级介绍 */}
          <div className="grid md:grid-cols-3 gap-6 mb-8">
            <div className="text-center p-6 border rounded-lg">
              <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <i className="fas fa-user text-blue-600 text-2xl"></i>
              </div>
              <h3 className="text-lg font-semibold mb-2">VIP 1级</h3>
              <p className="text-gray-600 text-sm">基础特权，适合普通用户升级</p>
              <div className="mt-4 text-blue-600 font-semibold">¥9.9/月</div>
            </div>

            <div className="text-center p-6 border-2 border-purple-500 rounded-lg relative">
              <div className="absolute -top-3 left-1/2 transform -translate-x-1/2">
                <span className="bg-purple-500 text-white px-3 py-1 rounded-full text-sm">推荐</span>
              </div>
              <div className="w-16 h-16 bg-purple-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <i className="fas fa-crown text-purple-600 text-2xl"></i>
              </div>
              <h3 className="text-lg font-semibold mb-2">VIP 2级</h3>
              <p className="text-gray-600 text-sm">进阶特权，最受欢迎的选择</p>
              <div className="mt-4 text-purple-600 font-semibold">¥19.9/月</div>
            </div>

            <div className="text-center p-6 border rounded-lg">
              <div className="w-16 h-16 bg-orange-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <i className="fas fa-star text-orange-600 text-2xl"></i>
              </div>
              <h3 className="text-lg font-semibold mb-2">VIP 3级</h3>
              <p className="text-gray-600 text-sm">尊享特权，极致体验</p>
              <div className="mt-4 text-orange-600 font-semibold">¥29.9/月</div>
            </div>
          </div>

          {/* 特权详情 */}
          <div className="space-y-6">
            {[1, 2, 3].map((level) => (
              <div key={level} className="border rounded-lg overflow-hidden">
                <div className={`${
                  level === 1 ? 'bg-gradient-to-r from-blue-500 to-blue-600' :
                  level === 2 ? 'bg-gradient-to-r from-purple-500 to-purple-600' :
                  'bg-gradient-to-r from-orange-500 to-orange-600'
                } text-white p-4`}>
                  <h2 className="text-xl font-bold flex items-center">
                    <i className={`${
                      level === 1 ? 'fa-user' :
                      level === 2 ? 'fa-crown' :
                      'fa-star'
                    } fas mr-2`}></i>
                    VIP {level} 级特权
                  </h2>
                </div>
                
                <div className="p-6">
                  <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {(featuresByLevel[level] || []).map((feature, index) => (
                      <div key={index} className="flex items-start p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
                        <div className={`flex-shrink-0 w-10 h-10 rounded-full ${
                          level === 1 ? 'bg-blue-100 text-blue-600' :
                          level === 2 ? 'bg-purple-100 text-purple-600' :
                          'bg-orange-100 text-orange-600'
                        } flex items-center justify-center mr-3`}>
                          <i className="fas fa-check"></i>
                        </div>
                        <div>
                          <h4 className="font-semibold text-gray-900 dark:text-white">{feature.name}</h4>
                          <p className="text-sm text-gray-600 dark:text-gray-300 mt-1">{feature.description}</p>
                        </div>
                      </div>
                    ))}
                    {(featuresByLevel[level] || []).length === 0 && (
                      <div className="col-span-3 text-center py-8 text-gray-500 dark:text-gray-400">
                        <i className="fas fa-info-circle text-3xl mb-2"></i>
                        <p>该等级暂无特权信息</p>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* 特权对比表 */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-6">
          <h2 className="text-2xl font-bold mb-6">特权详细对比</h2>
          
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 dark:bg-gray-700">
                  <th className="px-4 py-3 text-left font-semibold">特权功能</th>
                  <th className="px-4 py-3 text-center font-semibold">VIP 1级</th>
                  <th className="px-4 py-3 text-center font-semibold">VIP 2级</th>
                  <th className="px-4 py-3 text-center font-semibold">VIP 3级</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                {features.map((feature, index) => (
                  <tr key={index} className="hover:bg-gray-50 dark:hover:bg-gray-750">
                    <td className="px-4 py-3">
                      <div className="font-medium text-gray-900 dark:text-white">{feature.name}</div>
                      <div className="text-gray-600 text-xs dark:text-gray-400">{feature.description}</div>
                    </td>
                    <td className="px-4 py-3 text-center">
                      {feature.required_level <= 1 ? (
                        <i className="fas fa-check text-green-500"></i>
                      ) : (
                        <i className="fas fa-times text-gray-300 dark:text-gray-600"></i>
                      )}
                    </td>
                    <td className="px-4 py-3 text-center">
                      {feature.required_level <= 2 ? (
                        <i className="fas fa-check text-green-500"></i>
                      ) : (
                        <i className="fas fa-times text-gray-300 dark:text-gray-600"></i>
                      )}
                    </td>
                    <td className="px-4 py-3 text-center">
                      {feature.required_level <= 3 ? (
                        <i className="fas fa-check text-green-500"></i>
                      ) : (
                        <i className="fas fa-times text-gray-300 dark:text-gray-600"></i>
                      )}
                    </td>
                  </tr>
                ))}
                {features.length === 0 && (
                  <tr>
                    <td colSpan={4} className="px-4 py-8 text-center text-gray-500 dark:text-gray-400">
                      暂无特权信息
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
          
          <div className="mt-6 text-center">
            <Link 
              href="/vip/plans"
              className="bg-purple-600 text-white px-8 py-3 rounded-lg font-semibold hover:bg-purple-700 transition inline-block"
            >
              立即选择套餐
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
};

export default VIPFeaturesPage;