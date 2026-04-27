/**
 * 系统管理页面 - 缓存和安全
 */

'use client';

import {useEffect, useState} from 'react';

export default function SystemPage() {
    const [cacheStats, setCacheStats] = useState<any>(null);
    const [securityStats, setSecurityStats] = useState<any>(null);
    const [isLoading, setIsLoading] = useState(true);

    useEffect(() => {
        loadSystemInfo();
    }, []);

    const loadSystemInfo = async () => {
        try {
            const [cacheRes, securityRes] = await Promise.all([
                fetch('/api/v1/system/cache/stats'),
                fetch('/api/v1/system/security/login-attempts'),
            ]);

            const cacheData = await cacheRes.json();
            const securityData = await securityRes.json();

            if (cacheData.success) setCacheStats(cacheData.data);
            if (securityData.success) setSecurityStats(securityData.data);
        } catch (error) {
            console.error('加载系统信息失败:', error);
        } finally {
            setIsLoading(false);
        }
    };

    const handleClearCache = async () => {
        if (!confirm('确定要清空缓存吗?')) return;

        try {
            const response = await fetch('/api/v1/system/cache/clear', {
                method: 'POST',
            });

            const result = await response.json();

            if (result.success) {
                alert('缓存已清空');
                loadSystemInfo();
            } else {
                alert(`清空失败: ${result.error}`);
            }
        } catch (error) {
            console.error('清空缓存失败:', error);
            alert('清空缓存失败');
        }
    };

    if (isLoading) {
        return <div className="min-h-screen flex items-center justify-center">加载中...</div>;
    }

    return (
        <div className="min-h-screen bg-gray-50 py-8">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                <div className="mb-8">
                    <h1 className="text-3xl font-bold text-gray-900">系统管理</h1>
                    <p className="mt-2 text-gray-600">监控系统性能和安全性</p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {/* 数据库迁移 */}
                    <div className="bg-white rounded-lg shadow-md p-6 hover:shadow-lg transition-shadow cursor-pointer"
                         onClick={() => window.location.href = '/admin/system/migrations'}>
                        <h2 className="text-xl font-semibold mb-4 flex items-center">
                            <svg className="w-6 h-6 mr-2 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4" />
                            </svg>
                            数据库迁移
                        </h2>
                        <p className="text-gray-600">管理数据库结构和版本迁移</p>
                    </div>

                    {/* 站点健康检查 */}
                    <div className="bg-white rounded-lg shadow-md p-6 hover:shadow-lg transition-shadow cursor-pointer"
                         onClick={() => window.location.href = '/admin/system/health'}>
                        <h2 className="text-xl font-semibold mb-4 flex items-center">
                            <svg className="w-6 h-6 mr-2 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                            </svg>
                            站点健康检查
                        </h2>
                        <p className="text-gray-600">检查系统运行状态和性能指标</p>
                    </div>

                    {/* 缓存管理 */}
                    <div className="bg-white rounded-lg shadow-md p-6">
                        <h2 className="text-xl font-semibold mb-4 flex items-center">
                            <svg className="w-6 h-6 mr-2 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                            </svg>
                            缓存管理
                        </h2>

                        <div className="space-y-4">
                            <div className="flex justify-between items-center">
                                <span className="text-gray-600">缓存项目数:</span>
                                <span className="text-2xl font-bold text-blue-600">
                  {cacheStats?.cached_items || 0}
                </span>
                            </div>

                            <button
                                onClick={handleClearCache}
                                className="w-full px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700"
                            >
                                清空缓存
                            </button>
                        </div>
                    </div>

                    {/* 安全管理 */}
                    <div className="bg-white rounded-lg shadow-md p-6">
                        <h2 className="text-xl font-semibold mb-4 flex items-center">
                            <svg className="w-6 h-6 mr-2 text-orange-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                            </svg>
                            安全管理
                        </h2>

                        <div className="space-y-4">
                            <div className="flex justify-between items-center">
                                <span className="text-gray-600">登录尝试记录:</span>
                                <span className="text-2xl font-bold text-orange-600">
                  {securityStats?.attempts || 0}
                </span>
                            </div>

                            <div className="pt-4 border-t">
                                <p className="text-sm text-gray-500">
                                    系统会自动限制连续失败的登录尝试
                                </p>
                            </div>
                        </div>
                    </div>
                </div>

                {/* 系统信息 */}
                <div className="mt-6 bg-white rounded-lg shadow-md p-6">
                    <h2 className="text-xl font-semibold mb-4">系统信息</h2>

                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                        <div className="p-4 bg-gray-50 rounded">
                            <p className="text-sm text-gray-600">Python版本</p>
                            <p className="text-lg font-semibold">3.10+</p>
                        </div>
                        <div className="p-4 bg-gray-50 rounded">
                            <p className="text-sm text-gray-600">框架</p>
                            <p className="text-lg font-semibold">FastAPI</p>
                        </div>
                        <div className="p-4 bg-gray-50 rounded">
                            <p className="text-sm text-gray-600">数据库</p>
                            <p className="text-lg font-semibold">MySQL</p>
                        </div>
                        <div className="p-4 bg-gray-50 rounded">
                            <p className="text-sm text-gray-600">前端</p>
                            <p className="text-lg font-semibold">Next.js</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
