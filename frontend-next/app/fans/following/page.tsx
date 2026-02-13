'use client';

import React, {useEffect, useState} from 'react';
import Link from 'next/link';
import WithAuthProtection from '@/components/WithAuthProtection';
import {RelationService, RelationWithDate} from "@/lib/api/user-relation-services";

const FollowingPage = () => {
  const [followingList, setFollowingList] = useState<RelationWithDate[]>([]);
  const [followingCount, setFollowingCount] = useState<number>(0);
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
    const fetchFollowingList = async () => {
      try {
        setLoading(true);
        const response = await RelationService.getFollowing();
        
        if (response.success && response.data) {
          setFollowingList(response.data.following_list || []);
          setFollowingCount(response.data.following_count || 0);
        } else {
          setError(response.error || '获取关注列表失败');
        }
      } catch (err) {
        console.error('获取关注列表失败:', err);
        setError('获取关注列表失败');
      } finally {
        setLoading(false);
      }
    };

    fetchFollowingList();
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
    <WithAuthProtection loadingMessage="正在加载关注列表...">
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 py-12">
        <div className="container mx-auto px-4 max-w-4xl">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow">
            {/* Header */}
            <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-2xl font-bold text-gray-900 dark:text-white">我的关注</h2>
                  <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                    你关注了 {followingCount} 位用户
                  </p>
                </div>
                <div className="flex items-center space-x-2">
                  <span className="bg-green-100 text-green-800 text-xs font-medium px-2.5 py-0.5 rounded-full dark:bg-green-900 dark:text-green-300">
                    {followingCount} 关注
                  </span>
                </div>
              </div>
            </div>

          {/* Following List */}
          <div className="divide-y divide-gray-200 dark:divide-gray-700">
            {followingList.length > 0 ? (
              followingList.map((userRelation, index) => {
                const user = userRelation.user;
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
                          onClick={() => window.location.href = `/user/${user.id.toString()}`}
                        >
                          {user.profile_picture ? (
                            <img 
                              className="h-12 w-12 rounded-full object-cover"
                              src={`/api/avatar/${user.id}`} // 假设有一个头像API
                              alt={user.username}
                            />
                          ) : (
                            <div className="h-12 w-12 rounded-full bg-gradient-to-r from-green-400 to-blue-500 flex items-center justify-center">
                              <span className="text-white font-medium text-lg">
                                {user.username[0].toUpperCase()}
                              </span>
                            </div>
                          )}
                        </div>

                        {/* User Info */}
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center space-x-2">
                            <h3 className="text-lg font-medium text-gray-900 dark:text-white truncate">
                              {user.username}
                            </h3>
                            <span className="text-sm text-gray-500 dark:text-gray-400">
                              <i className="fas fa-at" title={user.email}></i>
                            </span>
                          </div>
                          {user.bio && (
                            <p className="text-sm text-gray-600 dark:text-gray-300 mt-1 line-clamp-2">
                              {user.bio}
                            </p>
                          )}
                          <div className="flex items-center space-x-4 mt-2 text-xs text-gray-500 dark:text-gray-400">
                            <span>
                              <i className="fas fa-heart mr-1 text-red-400"></i>
                              关注时间: {formatRelativeTime(userRelation.created_at)}
                            </span>
                          </div>
                        </div>
                      </div>

                      {/* Actions */}
                      <div className="flex items-center space-x-2">
                        <button 
                          className="bg-red-100 text-red-700 px-4 py-2 rounded-lg text-sm font-medium hover:bg-red-200 transition-colors duration-200"
                          onClick={async () => {
                            try {
                              const response = await RelationService.unfollowUser(user.id);
                              if (response.success) {
                                // 重新加载列表
                                const updatedResponse = await RelationService.getFollowing();
                                if (updatedResponse.success && updatedResponse.data) {
                                  setFollowingList(updatedResponse.data.following_list || []);
                                  setFollowingCount(updatedResponse.data.following_count || 0);
                                }
                              } else {
                                alert(response.error || '取消关注失败');
                              }
                            } catch (err) {
                              console.error('取消关注失败:', err);
                              alert('取消关注失败');
                            }
                          }}
                        >
                          <i className="fas fa-user-minus mr-1"></i>
                          取关
                        </button>
                      </div>
                    </div>
                  </div>
                );
              })
            ) : (
              // Empty State
              <div className="px-6 py-12 text-center">
                <div className="mx-auto h-24 w-24 text-gray-300 mb-4 dark:text-gray-600">
                  <i className="fas fa-heart text-6xl"></i>
                </div>
                <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">还没有关注任何人</h3>
                <p className="text-gray-600 dark:text-gray-400 mb-6">发现有趣的用户，开始你的关注之旅吧！</p>
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

export default FollowingPage;