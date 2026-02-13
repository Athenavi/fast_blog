'use client';

import React, {useEffect, useState} from 'react';
import Link from 'next/link';
import WithAuthProtection from '@/components/WithAuthProtection';
import {RelationService, RelationWithDate} from "@/lib/api/user-relation-services";

const FansPage = () => {
    const [fansList, setFansList] = useState<RelationWithDate[]>([]);
    const [fansCount, setFansCount] = useState<number>(0);
    const [loading, setLoading] = useState<boolean>(true);
    const [error, setError] = useState<string | null>(null);

    // 相对时间格式化函数
    const formatRelativeTime = (dateString: string): string => {
        const now = new Date();
        const past = new Date(dateString);
        const diffInSeconds = Math.floor((now.getTime() - past.getTime()) / 1000);

        if (diffInSeconds < 60) return `${diffInSeconds}秒前`;
        if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)}分钟前`;
        if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)}小时前`;
        if (diffInSeconds < 2592000) return `${Math.floor(diffInSeconds / 86400)}天前`;
        return past.toLocaleDateString('zh-CN');
    };

    useEffect(() => {
        const fetchFansList = async () => {
            try {
                setLoading(true);
                const response = await RelationService.getFollowers();

                if (response.success && response.data) {
                    setFansList(response.data.fans_list || []);
                    setFansCount(response.data.fans_count || 0);
                } else {
                    setError(response.error || '获取粉丝列表失败');
                }
            } catch (err) {
                console.error('获取粉丝列表失败:', err);
                setError('获取粉丝列表失败');
            } finally {
                setLoading(false);
            }
        };

        fetchFansList();
    }, []);

    if (loading) {
        return (
            <div className="min-h-screen bg-gray-50 dark:bg-gray-900 py-12">
                <div className="container mx-auto px-4 max-w-4xl">
                    <div
                        className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary mx-auto"></div>
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
        <WithAuthProtection loadingMessage="正在加载粉丝列表...">
            <div className="min-h-screen bg-gray-50 dark:bg-gray-900 py-12">
                <div className="container mx-auto px-4 max-w-4xl">
                    <div className="bg-white dark:bg-gray-800 rounded-lg shadow">
                        {/* Header */}
                        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
                            <div className="flex items-center justify-between">
                                <div>
                                    <h2 className="text-2xl font-bold text-gray-900 dark:text-white">我的粉丝</h2>
                                    <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                                        共 {fansCount} 位粉丝关注了你
                                    </p>
                                </div>
                                <div className="flex items-center space-x-2">
                    <span
                        className="bg-blue-100 text-blue-800 text-xs font-medium px-2.5 py-0.5 rounded-full dark:bg-blue-900 dark:text-blue-300">
                      {fansCount} 粉丝
                    </span>
                                </div>
                            </div>
                        </div>

                    {/* Fans List */}
                    <div className="divide-y divide-gray-200 dark:divide-gray-700">
                        {fansList.length > 0 ? (
                            fansList.map((fanRelation, index) => {
                                const fan = fanRelation.user;
                                return (
                                    <div
                                        key={index}
                                        className="px-6 py-4 hover:bg-gray-50 dark:hover:bg-gray-750 transition-colors duration-200"
                                    >
                                        <div className="flex items-center justify-between">
                                            <div className="flex items-center space-x-4">
                                                {/* Avatar */}
                                                <div
                                                    className="flex-shrink-0 cursor-pointer"
                                                    onClick={() => window.location.href = `/user/${fan.id.toString()}`}
                                                >
                                                    {fan.profile_picture ? (
                                                        <img
                                                            className="h-12 w-12 rounded-full object-cover"
                                                            src={`/api/avatar/${fan.id}`} // 假设有一个头像API
                                                            alt={fan.username}
                                                        />
                                                    ) : (
                                                        <div
                                                            className="h-12 w-12 rounded-full bg-gradient-to-r from-blue-400 to-purple-500 flex items-center justify-center">
                              <span className="text-white font-medium text-lg">
                                {fan.username[0].toUpperCase()}
                              </span>
                                                        </div>
                                                    )}
                                                </div>

                                                {/* User Info */}
                                                <div className="flex-1 min-w-0">
                                                    <div className="flex items-center space-x-2">
                                                        <h3 className="text-lg font-medium text-gray-900 dark:text-white truncate">
                                                            {fan.username}
                                                        </h3>
                                                        <span className="text-sm text-gray-500 dark:text-gray-400">
                              <i className="fas fa-at"></i>{fan.email}
                            </span>
                                                    </div>
                                                    {fan.bio && (
                                                        <p className="text-sm text-gray-600 dark:text-gray-300 mt-1 line-clamp-2">
                                                            {fan.bio}
                                                        </p>
                                                    )}
                                                    <div
                                                        className="flex items-center space-x-4 mt-2 text-xs text-gray-500 dark:text-gray-400">
                            <span>
                              <i className="fas fa-calendar-alt mr-1"></i>
                              关注时间: {formatRelativeTime(fanRelation.created_at)}
                            </span>
                                                    </div>
                                                </div>
                                            </div>

                                            {/* Actions */}
                                            <div className="flex items-center space-x-2">
                                                <a
                                                    href={`/user/${fan.id.toString()}`}
                                                    className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors duration-200"
                                                >
                                                    <i className="fas fa-user mr-1"></i>
                                                    查看
                                                </a>
                                            </div>
                                        </div>
                                    </div>
                                );
                            })
                        ) : (
                            // Empty State
                            <div className="px-6 py-12 text-center">
                                <div className="mx-auto h-24 w-24 text-gray-300 mb-4 dark:text-gray-600">
                                    <i className="fas fa-user-friends text-6xl"></i>
                                </div>
                                <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">还没有粉丝</h3>
                                <p className="text-gray-600 dark:text-gray-400 mb-6">分享你的精彩内容，吸引更多关注者吧！</p>
                                <Link
                                    href="/fans/discover"
                                    className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors duration-200"
                                >
                                    <i className="fas fa-search mr-2"></i>
                                    发现用户
                                </Link>
                            </div>
                        )}
                    </div>
                    </div>
                </div>
            </div>
        </WithAuthProtection>
    );
};

export default FansPage;