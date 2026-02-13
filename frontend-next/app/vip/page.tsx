'use client';

import React from 'react';
import Link from 'next/link';

const VipPage = () => {
  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-50 to-blue-50 dark:from-purple-900 dark:to-blue-900 py-8">
      <div className="container mx-auto px-4 max-w-6xl">
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-gray-900 dark:text-white mb-4">VIP会员中心</h1>
          <p className="text-xl text-gray-600 dark:text-gray-300 max-w-2xl mx-auto">
            享受专属特权，获得更好的使用体验
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-12">
          <Link href="/vip/features" className="bg-white dark:bg-gray-800 rounded-xl shadow-md p-6 hover:shadow-lg transition-shadow duration-300 flex flex-col items-center text-center group">
            <div className="w-16 h-16 bg-gradient-to-r from-blue-500 to-purple-600 rounded-full flex items-center justify-center mb-4 group-hover:scale-110 transition-transform duration-300">
              <i className="fas fa-star text-white text-2xl"></i>
            </div>
            <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">VIP特权</h3>
            <p className="text-gray-600 dark:text-gray-400">查看不同VIP等级的专属特权</p>
          </Link>

          <Link href="/vip/plans" className="bg-white dark:bg-gray-800 rounded-xl shadow-md p-6 hover:shadow-lg transition-shadow duration-300 flex flex-col items-center text-center group">
            <div className="w-16 h-16 bg-gradient-to-r from-green-500 to-teal-600 rounded-full flex items-center justify-center mb-4 group-hover:scale-110 transition-transform duration-300">
              <i className="fas fa-shopping-cart text-white text-2xl"></i>
            </div>
            <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">购买套餐</h3>
            <p className="text-gray-600 dark:text-gray-400">选择适合您的VIP套餐</p>
          </Link>

          <Link href="/vip/my-subscription" className="bg-white dark:bg-gray-800 rounded-xl shadow-md p-6 hover:shadow-lg transition-shadow duration-300 flex flex-col items-center text-center group">
            <div className="w-16 h-16 bg-gradient-to-r from-yellow-500 to-orange-600 rounded-full flex items-center justify-center mb-4 group-hover:scale-110 transition-transform duration-300">
              <i className="fas fa-id-card text-white text-2xl"></i>
            </div>
            <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">我的订阅</h3>
            <p className="text-gray-600 dark:text-gray-400">管理您的VIP订阅信息</p>
          </Link>

          <Link href="/vip/premium-content" className="bg-white dark:bg-gray-800 rounded-xl shadow-md p-6 hover:shadow-lg transition-shadow duration-300 flex flex-col items-center text-center group">
            <div className="w-16 h-16 bg-gradient-to-r from-red-500 to-pink-600 rounded-full flex items-center justify-center mb-4 group-hover:scale-110 transition-transform duration-300">
              <i className="fas fa-book text-white text-2xl"></i>
            </div>
            <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">专属内容</h3>
            <p className="text-gray-600 dark:text-gray-400">浏览VIP专享的高质量内容</p>
          </Link>

          <Link href="/vip/payment" className="bg-white dark:bg-gray-800 rounded-xl shadow-md p-6 hover:shadow-lg transition-shadow duration-300 flex flex-col items-center text-center group">
            <div className="w-16 h-16 bg-gradient-to-r from-indigo-500 to-purple-600 rounded-full flex items-center justify-center mb-4 group-hover:scale-110 transition-transform duration-300">
              <i className="fas fa-credit-card text-white text-2xl"></i>
            </div>
            <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">支付管理</h3>
            <p className="text-gray-600 dark:text-gray-400">管理您的支付方式和订单</p>
          </Link>

          <Link href="/vip/payment-methods" className="bg-white dark:bg-gray-800 rounded-xl shadow-md p-6 hover:shadow-lg transition-shadow duration-300 flex flex-col items-center text-center group">
            <div className="w-16 h-16 bg-gradient-to-r from-teal-500 to-green-600 rounded-full flex items-center justify-center mb-4 group-hover:scale-110 transition-transform duration-300">
              <i className="fas fa-wallet text-white text-2xl"></i>
            </div>
            <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">支付方式</h3>
            <p className="text-gray-600 dark:text-gray-400">添加和管理支付方式</p>
          </Link>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm p-8">
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-6 text-center">为什么选择成为VIP？</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            <div className="flex items-start">
              <div className="bg-blue-100 dark:bg-blue-900/50 text-blue-600 dark:text-blue-300 p-3 rounded-lg mr-4">
                <i className="fas fa-ad text-xl"></i>
              </div>
              <div>
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">无广告干扰</h3>
                <p className="text-gray-600 dark:text-gray-400">享受纯净的浏览体验，告别烦人的广告干扰。</p>
              </div>
            </div>
            
            <div className="flex items-start">
              <div className="bg-purple-100 dark:bg-purple-900/50 text-purple-600 dark:text-purple-300 p-3 rounded-lg mr-4">
                <i className="fas fa-download text-xl"></i>
              </div>
              <div>
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">优先下载</h3>
                <p className="text-gray-600 dark:text-gray-400">享受更快的下载速度和更高的下载权限。</p>
              </div>
            </div>
            
            <div className="flex items-start">
              <div className="bg-green-100 dark:bg-green-900/50 text-green-600 dark:text-green-300 p-3 rounded-lg mr-4">
                <i className="fas fa-file-alt text-xl"></i>
              </div>
              <div>
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">专属内容</h3>
                <p className="text-gray-600 dark:text-gray-400">访问只有VIP会员才能看到的独家内容和资源。</p>
              </div>
            </div>
            
            <div className="flex items-start">
              <div className="bg-yellow-100 dark:bg-yellow-900/50 text-yellow-600 dark:text-yellow-300 p-3 rounded-lg mr-4">
                <i className="fas fa-headset text-xl"></i>
              </div>
              <div>
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">专属客服</h3>
                <p className="text-gray-600 dark:text-gray-400">享受24小时专属客服支持，快速解决问题。</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default VipPage;