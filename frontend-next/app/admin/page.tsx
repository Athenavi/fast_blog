'use client';

import React, {useEffect, useState} from 'react';
import {FaChartBar, FaChartPie, FaCog, FaEye, FaFileAlt, FaHeart, FaUserPlus, FaUsers} from 'react-icons/fa';
import {type Activity, DashboardService} from '@/lib/api';

interface Stats {
  usersCount: number;
  articlesCount: number;
  totalViews: number;
  totalLikes: number;
  totalComments: number;
}

const AdminDashboard = () => {
  const [stats, setStats] = useState<Stats>({
    usersCount: 0,
    articlesCount: 0,
    totalViews: 0,
    totalLikes: 0,
    totalComments: 0
  });

  const [activities, setActivities] = useState<Activity[]>([]);
  const [loading, setLoading] = useState(true);

  // 获取统计数据
  useEffect(() => {
    const fetchData = async () => {
      try {
        // 并行获取数据
        const [statsResponse, articlesResponse] = await Promise.all([
          DashboardService.getDashboardStats(),
          DashboardService.getRecentArticles()
        ]);
        
        // 处理统计数据
        if (statsResponse.success && statsResponse.data) {
          setStats({
            usersCount: statsResponse.data.users || 0,
            articlesCount: statsResponse.data.articles || 0,
            totalViews: statsResponse.data.visitors || 0,
            totalLikes: statsResponse.data.likes || 0,
            totalComments: statsResponse.data.comments || 0
          });
        } else {
          console.warn('Failed to fetch stats:', statsResponse.error);
          // 如果API失败，仍然设置为0值
          setStats({
            usersCount: 0,
            articlesCount: 0,
            totalViews: 0,
            totalLikes: 0,
            totalComments: 0
          });
        }
        
        // 处理最近文章数据
        if (articlesResponse.success && articlesResponse.data) {
          // 将文章数据转换为活动格式
          const convertedActivities: Activity[] = articlesResponse.data.map((article) => ({
            id: article.id,
            user_name: typeof article.author === 'string' ? article.author : (article.author as any)?.username || 'Unknown',
            activity_type: article.status === 'published' ? 'publish_article' : 'create_article',
            target_type: 'article',
            target_id: article.id,
            details: `Created article: ${article.title}`,
            created_at: article.created_at,
            icon: 'fas fa-file-alt'
          }));
          setActivities(convertedActivities);
        } else {
          console.warn('Failed to fetch recent articles:', articlesResponse.error);
          // 如果API失败，仍然设置为空数组
          setActivities([]);
        }
      } catch (error) {
        console.error('Error fetching data:', error);
        // 出错时设置为0值和空数组
        setStats({
          usersCount: 0,
          articlesCount: 0,
          totalViews: 0,
          totalLikes: 0,
          totalComments: 0
        });
        setActivities([]);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  // 格式化日期
  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('zh-CN', {
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  return (
    <div className="space-y-6">
      {/* 统计卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6 mb-8">
        <div className="bg-white rounded-xl shadow-sm p-6 card-hover">
          <div className="flex items-center">
            <div className="p-3 rounded-lg bg-blue-100 text-primary">
              <FaUsers className="text-xl" />
            </div>
            <div className="ml-4">
              <h2 className="text-sm font-medium text-gray-500">用户总数</h2>
              <p className="text-2xl font-semibold text-gray-800">{stats.usersCount}</p>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-xl shadow-sm p-6 card-hover">
          <div className="flex items-center">
            <div className="p-3 rounded-lg bg-green-100 text-success">
              <FaFileAlt className="text-xl" />
            </div>
            <div className="ml-4">
              <h2 className="text-sm font-medium text-gray-500">文章总数</h2>
              <p className="text-2xl font-semibold text-gray-800">{stats.articlesCount}</p>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-xl shadow-sm p-6 card-hover">
          <div className="flex items-center">
            <div className="p-3 rounded-lg bg-purple-100 text-purple-600">
              <FaEye className="text-xl" />
            </div>
            <div className="ml-4">
              <h2 className="text-sm font-medium text-gray-500">总浏览量</h2>
              <p className="text-2xl font-semibold text-gray-800">{stats.totalViews}</p>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-xl shadow-sm p-6 card-hover">
          <div className="flex items-center">
            <div className="p-3 rounded-lg bg-pink-100 text-pink-600">
              <FaHeart className="text-xl" />
            </div>
            <div className="ml-4">
              <h2 className="text-sm font-medium text-gray-500">总点赞数</h2>
              <p className="text-2xl font-semibold text-gray-800">{stats.totalLikes}</p>
            </div>
          </div>
        </div>
      </div>

      {/* 最近活动和快速操作 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl shadow-sm p-6">
          <div className="flex justify-between items-center mb-6">
            <h3 className="text-lg font-semibold text-gray-800">最近活动</h3>
          </div>
          
          {loading ? (
            <div className="text-center py-4">
              <div className="inline-block animate-spin rounded-full h-6 w-6 border-t-2 border-b-2 border-primary"></div>
            </div>
          ) : (
            <div className="space-y-4">
              {activities.length > 0 ? (
                activities.map((activity) => (
                  <div key={activity.id} className="flex items-start border-b border-gray-100 pb-3 last:border-0 last:pb-0">
                    <div className="p-2 rounded-full bg-blue-100 text-blue-600 mr-3">
                      <FaChartBar className="text-sm" />
                    </div>
                    <div>
                      <p className="text-gray-800">
                        用户 <span className="font-medium">{activity.user_name}</span> {activity.activity_type.includes('publish') ? '发布了' : '创建了'}文章
                      </p>
                      <p className="text-sm text-gray-500">{formatDate(activity.created_at)}</p>
                    </div>
                  </div>
                ))
              ) : (
                <p className="text-sm text-gray-500 text-center py-4">暂无最近活动</p>
              )}
            </div>
          )}
        </div>

        <div className="bg-white rounded-xl shadow-sm p-6">
          <h3 className="text-lg font-semibold text-gray-800 mb-6">快速操作</h3>
          <div className="grid grid-cols-2 gap-4">
            <a 
              href="/admin/blog?autoRun=showArticleModal" 
              className="flex flex-col items-center justify-center p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
            >
              <div className="h-12 w-12 rounded-lg bg-blue-100 flex items-center justify-center text-primary mb-2">
                <FaChartPie className="text-xl" />
              </div>
              <span className="text-sm font-medium text-gray-700">新建文章</span>
            </a>
            <a 
              href="/admin/user?autoRun=showUserModal"
              className="flex flex-col items-center justify-center p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
            >
              <div className="h-12 w-12 rounded-lg bg-green-100 flex items-center justify-center text-success mb-2">
                <FaUserPlus className="text-xl" />
              </div>
              <span className="text-sm font-medium text-gray-700">添加用户</span>
            </a>
            <a 
              href="/admin/analytics" 
              className="flex flex-col items-center justify-center p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
            >
              <div className="h-12 w-12 rounded-lg bg-purple-100 flex items-center justify-center text-purple-600 mb-2">
                <FaChartBar className="text-xl" />
              </div>
              <span className="text-sm font-medium text-gray-700">数据分析</span>
            </a>
            <a 
              href="/admin/settings" 
              className="flex flex-col items-center justify-center p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
            >
              <div className="h-12 w-12 rounded-lg bg-yellow-100 flex items-center justify-center text-warning mb-2">
                <FaCog className="text-xl" />
              </div>
              <span className="text-sm font-medium text-gray-700">系统设置</span>
            </a>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AdminDashboard;