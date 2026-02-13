'use client';

import React, {useEffect, useState} from 'react';
import Link from 'next/link';
import WithAuthProtection from '@/components/WithAuthProtection';
import {RelationService, UserRelation} from "@/lib/api/user-relation-services";

const DiscoverUsersPage = () => {
  const [users, setUsers] = useState<UserRelation[]>([]);
  const [followingIds, setFollowingIds] = useState<number[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState<string>('');

  useEffect(() => {
    const fetchUsersList = async () => {
      try {
        setLoading(true);
        const response = await RelationService.getUsers();
        
        if (response.success && response.data) {
          setUsers(response.data.users || []);
          setFollowingIds(response.data.following_ids || []);
        } else {
          setError(response.error || '获取用户列表失败');
        }
      } catch (err) {
        console.error('获取用户列表失败:', err);
        setError('获取用户列表失败');
      } finally {
        setLoading(false);
      }
    };

    fetchUsersList();
  }, []);

  const toggleFollow = async (userId: number, isFollowing: boolean) => {
    try {
      let response;
      if (isFollowing) {
        response = await RelationService.unfollowUser(userId);
      } else {
        response = await RelationService.followUser(userId);
      }

      if (response.success) {
        // 更新本地状态
        if (isFollowing) {
          setFollowingIds(prev => prev.filter(id => id !== userId));
        } else {
          setFollowingIds(prev => [...prev, userId]);
        }
      } else {
        alert(response.error || (isFollowing ? '取消关注失败' : '关注失败'));
      }
    } catch (err) {
      console.error(isFollowing ? '取消关注失败:' : '关注失败:', err);
      alert(isFollowing ? '取消关注失败' : '关注失败');
    }
  };

  // 过滤用户列表
  const filteredUsers = users.filter(user => 
    user.username.toLowerCase().includes(searchTerm.toLowerCase()) ||
    user.email.toLowerCase().includes(searchTerm.toLowerCase())
  );

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
    <WithAuthProtection loadingMessage="正在加载用户列表...">
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 py-12">
        <div className="container mx-auto px-4 max-w-4xl">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow">
            {/* Header */}
            <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-2xl font-bold text-gray-900 dark:text-white">发现用户</h2>
                  <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">找到感兴趣的用户并关注他们</p>
                </div>
                <div className="flex items-center space-x-2">
                  <div className="relative">
                    <input 
                      type="text"
                      placeholder="搜索用户..."
                      className="pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                      value={searchTerm}
                      onChange={(e) => setSearchTerm(e.target.value)}
                    />
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                      <i className="fas fa-search text-gray-400"></i>
                    </div>
                  </div>
                </div>
              </div>
            </div>

          {/* Users Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 p-6">
            {filteredUsers.length > 0 ? (
              filteredUsers.map((user) => (
                <div 
                  key={user.id} 
                  className="bg-gray-50 dark:bg-gray-700 rounded-lg p-6 hover:shadow-md transition-shadow duration-200"
                >
                  <div className="text-center">
                    {/* Avatar */}
                    <div 
                      className="mx-auto mb-4 cursor-pointer" 
                      onClick={() => window.location.href = `/user/${user.id.toString()}`}
                    >
                      {user.profile_picture ? (
                        <img 
                          className="h-16 w-16 rounded-full object-cover mx-auto"
                          src={`/api/avatar/${user.id}`} // 假设有一个头像API
                          alt={user.username}
                        />
                      ) : (
                        <div className="h-16 w-16 rounded-full bg-gradient-to-r from-purple-400 to-pink-500 flex items-center justify-center mx-auto">
                          <span className="text-white font-medium text-xl">
                            {user.username[0].toUpperCase()}
                          </span>
                        </div>
                      )}
                    </div>

                    {/* User Info */}
                    <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-1">{user.username}</h3>
                    <p className="text-sm text-gray-600 dark:text-gray-300 mb-2">{user.email}</p>

                    {user.bio ? (
                      <p className="text-sm text-gray-700 dark:text-gray-200 mb-4 line-clamp-3">{user.bio}</p>
                    ) : (
                      <p className="text-sm text-gray-500 dark:text-gray-400 mb-4 italic">这个用户还没有填写个人简介</p>
                    )}

                    {/* Follow Button */}
                    {followingIds.includes(user.id) ? (
                      <button 
                        onClick={() => toggleFollow(user.id, true)}
                        className="w-full bg-gray-200 text-gray-700 px-4 py-2 rounded-lg text-sm font-medium hover:bg-gray-300 transition-colors duration-200 dark:bg-gray-600 dark:text-gray-200 dark:hover:bg-gray-500"
                      >
                        <i className="fas fa-user-check mr-1"></i>
                        已关注
                      </button>
                    ) : (
                      <button 
                        onClick={() => toggleFollow(user.id, false)}
                        className="w-full bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors duration-200"
                      >
                        <i className="fas fa-user-plus mr-1"></i>
                        关注
                      </button>
                    )}
                  </div>
                </div>
              ))
            ) : (
              // Empty State
              <div className="col-span-full px-6 py-12 text-center">
                <div className="mx-auto h-24 w-24 text-gray-300 mb-4 dark:text-gray-600">
                  <i className="fas fa-users text-6xl"></i>
                </div>
                <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">暂无其他用户</h3>
                <p className="text-gray-600 dark:text-gray-400">系统中还没有其他用户，请稍后再来看看！</p>
              </div>
            )}
          </div>
          </div>
        </div>
      </div>
    </WithAuthProtection>
  );
};

export default DiscoverUsersPage;