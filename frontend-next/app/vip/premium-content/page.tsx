'use client';

import {useEffect, useState} from 'react';
import {type PremiumArticle, VIPService} from '@/lib/api/index';
import Link from 'next/link';

const VipPremiumContentPage = () => {
  const [activeStatus, setActiveStatus] = useState<boolean>(false);
  const [currentVipLevel, setCurrentVipLevel] = useState<number>(0);
  const [articles, setArticles] = useState<PremiumArticle[]>([]);
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
    const fetchPremiumContent = async () => {
      try {
        setLoading(true);
        const response = await VIPService.getPremiumContent();
        
        if (response.success && response.data) {
          setActiveStatus(response.data.active_status);
          setCurrentVipLevel(response.data.current_vip_level);
          setArticles(response.data.articles || []);
        } else {
          setError(response.error || '获取VIP专属内容失败');
        }
      } catch (err) {
        console.error('获取VIP专属内容失败:', err);
        setError('获取VIP专属内容失败');
      } finally {
        setLoading(false);
      }
    };

    fetchPremiumContent();
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
    <div className="min-h-screen bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-900 dark:to-indigo-900 dark:text-white py-8">
      <div className="container mx-auto px-4 max-w-6xl">
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-6 mb-6">
          <div className="flex justify-between items-start mb-6">
            <div>
              <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">VIP专属内容</h1>
              <p className="text-gray-600 dark:text-gray-400">仅对VIP会员开放的优质内容</p>
            </div>

            {activeStatus && (
              <div className="bg-gradient-to-r from-green-500 to-teal-500 text-white px-4 py-2 rounded-full">
                <i className="fas fa-crown mr-2"></i>VIP {currentVipLevel} 级会员
              </div>
            )}
          </div>

          {!activeStatus && (
            // 非VIP用户提示
            <div className="bg-gradient-to-r from-yellow-50 to-orange-50 dark:from-yellow-900 dark:to-orange-900 border border-yellow-200 dark:border-yellow-700 rounded-lg p-8 text-center mb-8">
              <i className="fas fa-lock text-5xl text-yellow-500 mb-4"></i>
              <h2 className="text-2xl font-bold text-yellow-800 dark:text-yellow-300 mb-2">此内容仅对VIP会员开放</h2>
              <p className="text-yellow-700 dark:text-yellow-400 mb-6">升级VIP即可解锁全部专属内容</p>
              <div className="space-x-4">
                <Link 
                  href="/vip/plans"
                  className="bg-yellow-500 text-white px-6 py-3 rounded-lg font-semibold hover:bg-yellow-600 transition"
                >
                  立即升级VIP
                </Link>
                <Link 
                  href="/vip/features"
                  className="border border-yellow-500 text-yellow-500 dark:border-yellow-600 dark:text-yellow-400 px-6 py-3 rounded-lg font-semibold hover:bg-yellow-50 dark:hover:bg-yellow-900/20 transition"
                >
                  查看特权详情
                </Link>
              </div>
            </div>
          )}

          {/* 内容筛选 */}
          <div className="flex flex-wrap gap-4 mb-6">
            <button className="px-4 py-2 bg-purple-600 text-white rounded-lg font-semibold">
              全部内容
            </button>
            <button className="px-4 py-2 bg-gray-200 text-gray-700 dark:bg-gray-700 dark:text-gray-300 rounded-lg font-semibold hover:bg-gray-300 dark:hover:bg-gray-600 transition">
              精选文章
            </button>
            <button className="px-4 py-2 bg-gray-200 text-gray-700 dark:bg-gray-700 dark:text-gray-300 rounded-lg font-semibold hover:bg-gray-300 dark:hover:bg-gray-600 transition">
              深度分析
            </button>
            <button className="px-4 py-2 bg-gray-200 text-gray-700 dark:bg-gray-700 dark:text-gray-300 rounded-lg font-semibold hover:bg-gray-300 dark:hover:bg-gray-600 transition">
              独家教程
            </button>
          </div>

          {/* 内容列表 */}
          {activeStatus && articles && articles.length > 0 ? (
            <div className="grid gap-6">
              {articles.map((article) => (
                <div 
                  key={article.id} 
                  className="border rounded-lg overflow-hidden hover:shadow-md transition dark:border-gray-700"
                >
                  <div className="md:flex">
                    {article.cover_image && (
                      <div className="md:w-48 flex-shrink-0">
                        <img 
                          src={article.cover_image} 
                          alt={article.title}
                          className="w-full h-32 md:h-full object-cover"
                        />
                      </div>
                    )}

                    <div className="p-6 flex-1">
                      <div className="flex justify-between items-start mb-2">
                        <h3 className="text-xl font-semibold text-gray-900 dark:text-white">{article.title}</h3>
                        {article.required_vip_level > 0 && (
                          <span className="bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200 px-2 py-1 rounded text-xs font-medium">
                            VIP {article.required_vip_level}
                          </span>
                        )}
                      </div>

                      <p className="text-gray-600 dark:text-gray-300 mb-4">
                        {article.excerpt || '暂无摘要'}
                      </p>

                      <div className="flex justify-between items-center">
                        <div className="flex items-center space-x-4 text-sm text-gray-500 dark:text-gray-400">
                          <span>{article.author.username}</span>
                          <span>{article.created_at ? formatRelativeTime(article.created_at) : '未知时间'}</span>
                          <span>
                            <i className="fas fa-eye mr-1"></i>
                            {article.views}
                          </span>
                          <span>
                            <i className="fas fa-heart mr-1"></i>
                            {article.likes}
                          </span>
                        </div>

                        <Link 
                          href={`/blog/${article.slug}`}
                          className="text-purple-600 hover:text-purple-700 dark:text-purple-400 dark:hover:text-purple-300 font-semibold"
                        >
                          阅读全文 <i className="fas fa-arrow-right ml-1"></i>
                        </Link>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            // 空状态
            <div className="text-center py-12">
              <i className="fas fa-newspaper text-5xl text-gray-300 dark:text-gray-600 mb-4"></i>
              <h3 className="text-xl font-semibold text-gray-600 dark:text-gray-400 mb-2">暂无专属内容</h3>
              <p className="text-gray-500 dark:text-gray-500">更多优质内容正在筹备中，敬请期待</p>
            </div>
          )}

          {/* 分页 */}
          {activeStatus && articles && articles.length > 0 && (
            <div className="mt-8 flex justify-center">
              <nav className="flex space-x-2">
                <button className="px-3 py-2 bg-gray-200 text-gray-700 dark:bg-gray-700 dark:text-gray-300 rounded hover:bg-gray-300 dark:hover:bg-gray-600 transition">
                  上一页
                </button>
                <button className="px-3 py-2 bg-purple-600 text-white rounded">1</button>
                <button className="px-3 py-2 bg-gray-200 text-gray-700 dark:bg-gray-700 dark:text-gray-300 rounded hover:bg-gray-300 dark:hover:bg-gray-600 transition">
                  2
                </button>
                <button className="px-3 py-2 bg-gray-200 text-gray-700 dark:bg-gray-700 dark:text-gray-300 rounded hover:bg-gray-300 dark:hover:bg-gray-600 transition">
                  3
                </button>
                <button className="px-3 py-2 bg-gray-200 text-gray-700 dark:bg-gray-700 dark:text-gray-300 rounded hover:bg-gray-300 dark:hover:bg-gray-600 transition">
                  下一页
                </button>
              </nav>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default VipPremiumContentPage;