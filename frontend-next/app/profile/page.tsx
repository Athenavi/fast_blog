'use client';

import React, {useEffect, useState} from 'react';
import {useParams, useRouter} from 'next/navigation';
import Link from 'next/link';
import WithAuthProtection from '@/components/WithAuthProtection';
import {apiClient, UserProfileResponse} from '@/lib/api';

const UserProfilePage = () => {
  const router = useRouter();
  const [userData, setUserData] = useState<UserProfileResponse | null>(null);
  const [loading, setLoading] = useState(true);
  
  // Note: In a real implementation, we would use useParams() for dynamic routing
  // For this MVP, we'll simulate the data
  const params = useParams();
  const userId = params.id as string || 'me';

  useEffect(() => {
    // 加载用户资料
    async function fetchUserProfile() {
      try {
        // 使用真实的API获取用户资料
        // 对于当前用户，应该使用 /users/me/profile 端点
        const response = await apiClient.get('/users/me/profile');
        
        if (response.success && response.data) {
          console.log('User data fetched successfully:', response.data); // Debug log
          
          // 检查数据结构，如果API返回了嵌套在data.user中的数据，则使用该结构
          if ((response.data as UserProfileResponse).user) {
            // 如果response.data包含user字段，说明API返回了嵌套结构
            setUserData(response.data as UserProfileResponse);
          } else {
            // 否则直接使用response.data
            setUserData(response.data as UserProfileResponse);
          }
        } else {
          console.error('Failed to fetch user data:', response);
          console.error('Response message:', response.message);
          console.error('Response error:', response.error);
        }
      } catch (error) {
        console.error('Error fetching user profile:', error);
      } finally {
        setLoading(false);
      }
    }
    
    fetchUserProfile();
  }, []);



  if (loading || !userData) {
    return (
      <div className="min-h-screen bg-gray-50 py-12">
        <div className="container mx-auto px-4">
          <div className="text-center py-16">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto"></div>
            <p className="mt-4 text-gray-600">正在加载用户资料...</p>
          </div>
        </div>
      </div>
    );
  }

  const user = userData.user;
  const recentArticles = userData.recent_articles || [];

  return (
    <WithAuthProtection loadingMessage="正在加载用户资料...">
      <div className="min-h-screen bg-gray-50">
        {/* 顶部横幅 */}
        <div className="bg-gradient-to-r from-blue-500 to-purple-600 py-12">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex flex-col md:flex-row items-center justify-between">
              <div className="flex items-center space-x-6">
                <div className="w-24 h-24 bg-white rounded-full overflow-hidden border-4 border-white shadow-lg">
                  <div className="bg-gray-200 w-full h-full flex items-center justify-center">
                    <span className="text-3xl font-bold text-gray-600">
                      {user.username.charAt(0).toUpperCase()}
                    </span>
                  </div>
                </div>
                <div>
                  <h1 className="text-3xl font-bold text-white">{user.display_name || user.username}</h1>
                  <p className="text-blue-100 mt-1">@{user.username}</p>
                  <p className="text-blue-100 mt-2">{user.bio || '暂无简介'}</p>
                </div>
              </div>
              <div className="mt-6 md:mt-0 flex space-x-3">
                <button className="bg-white text-blue-600 px-6 py-2 rounded-full font-medium hover:bg-blue-50 transition-colors">
                  {userData.is_following ? '取消关注' : '关注'}
                </button>
                <button className="bg-blue-700 text-white px-6 py-2 rounded-full font-medium hover:bg-blue-800 transition-colors flex items-center">
                  <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"></path>
                  </svg>
                  消息
                  {userData.has_unread_message && (
                    <span className="ml-2 w-2 h-2 bg-red-500 rounded-full inline-block"></span>
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
          {/* 侧边栏 */}
          <div className="lg:col-span-1">
            <div className="bg-white rounded-xl shadow-sm p-6 sticky top-8">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">个人信息</h2>
              <div className="space-y-3">
                <div>
                  <span className="text-sm text-gray-500">邮箱</span>
                  <p className="text-gray-900">{user.email}</p>
                </div>
                <div>
                  <span className="text-sm text-gray-500">位置</span>
                  <p className="text-gray-900">{user.location || '未设置'}</p>
                </div>
                <div>
                  <span className="text-sm text-gray-500">网站</span>
                  <p className="text-gray-900 truncate">{user.website || '未设置'}</p>
                </div>
                <div>
                  <span className="text-sm text-gray-500">地区</span>
                  <p className="text-gray-900">{user.locale || '未设置'}</p>
                </div>
                <div>
                  <span className="text-sm text-gray-500">注册时间</span>
                  <p className="text-gray-900">{user.created_at ? new Date(user.created_at).toLocaleDateString() : '未知'}</p>
                </div>
                <div>
                  <span className="text-sm text-gray-500">隐私设置</span>
                  <p className="text-gray-900">{user.profile_private ? '私密' : '公开'}</p>
                </div>
              </div>

              <div className="mt-6 pt-6 border-t border-gray-200">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">统计信息</h3>
                <div className="grid grid-cols-3 gap-4">
                  <div className="bg-blue-50 p-3 rounded-lg text-center">
                    <div className="text-2xl font-bold text-blue-600">{userData.stats.articles_count}</div>
                    <div className="text-xs text-gray-500">文章</div>
                  </div>
                  <div className="bg-green-50 p-3 rounded-lg text-center">
                    <div className="text-2xl font-bold text-green-600">{userData.stats.followers_count}</div>
                    <div className="text-xs text-gray-500">粉丝</div>
                  </div>
                  <div className="bg-purple-50 p-3 rounded-lg text-center">
                    <div className="text-2xl font-bold text-purple-600">{userData.stats.following_count}</div>
                    <div className="text-xs text-gray-500">关注</div>
                  </div>
                </div>
              </div>

              <div className="mt-6 pt-6 border-t border-gray-200">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">操作</h3>
                <div className="space-y-3">
                  <button 
                    onClick={() => router.push('/my/posts')}
                    className="w-full bg-gray-100 hover:bg-gray-200 text-gray-800 py-2 px-4 rounded-lg font-medium transition-colors"
                  >
                    我的文章
                  </button>
                  <button 
                    onClick={() => router.push('/media')}
                    className="w-full bg-gray-100 hover:bg-gray-200 text-gray-800 py-2 px-4 rounded-lg font-medium transition-colors"
                  >
                    媒体库
                  </button>
                  <button 
                    onClick={() => router.push('/settings')}
                    className="w-full bg-gray-100 hover:bg-gray-200 text-gray-800 py-2 px-4 rounded-lg font-medium transition-colors"
                  >
                    设置
                  </button>
                </div>
              </div>
            </div>
          </div>

          {/* 主内容区 */}
          <div className="lg:col-span-3">
            <div className="bg-white rounded-xl shadow-sm overflow-hidden">
              <div className="border-b border-gray-200 bg-white px-6 py-4">
                <h2 className="text-xl font-semibold text-gray-900">最新文章</h2>
              </div>
              
              {recentArticles.length > 0 ? (
                <div className="divide-y divide-gray-100">
                  {recentArticles.map((article) => (
                    <Link href={{ pathname: '/blog', query: { slug: article.slug } }} key={article.id} className="block hover:bg-gray-50 transition-colors">
                      <article className="p-6">
                        <div className="flex flex-col md:flex-row gap-6">
                          {article.cover_image && (
                            <div className="md:w-32 h-20 flex-shrink-0">
                              <img 
                                src={article.cover_image} 
                                alt={article.title}
                                className="w-full h-full object-cover rounded-lg"
                                onError={(e) => {
                                  const target = e.target as HTMLImageElement;
                                  target.onerror = null;
                                  target.src = '/placeholder-image.jpg';
                                }}
                              />
                            </div>
                          )}
                          <div className="flex-1 min-w-0">
                            <h3 className="text-lg font-semibold text-gray-900 line-clamp-2">
                              {article.title}
                            </h3>
                            <p className="text-gray-600 mt-2 text-sm line-clamp-2">
                              {article.excerpt}
                            </p>
                            <div className="flex items-center mt-4 space-x-4">
                              <div className="flex items-center text-xs text-gray-500">
                                <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path>
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"></path>
                                </svg>
                                {article.views} 次浏览
                              </div>
                              <div className="flex items-center text-xs text-gray-500">
                                <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z"></path>
                                </svg>
                                {article.likes} 个赞
                              </div>
                              <div className="text-xs text-gray-500">
                                {new Date(article.created_at).toLocaleDateString()}
                              </div>
                            </div>
                            {article.tags && article.tags.length > 0 && (
                              <div className="flex flex-wrap gap-2 mt-3">
                                {article.tags.map((tag, index) => (
                                  <span 
                                    key={index} 
                                    className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800"
                                  >
                                    #{tag}
                                  </span>
                                ))}
                              </div>
                            )}
                          </div>
                        </div>
                      </article>
                    </Link>
                  ))}
                </div>
              ) : (
                <div className="p-12 text-center">
                  <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
                  </svg>
                  <h3 className="mt-2 text-sm font-medium text-gray-900">暂无文章</h3>
                  <p className="mt-1 text-sm text-gray-500">您还没有发布任何文章。</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
      </div>
    </WithAuthProtection>
  );
};

export default UserProfilePage;