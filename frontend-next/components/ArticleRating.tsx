'use client';

import React, {useEffect, useState} from 'react';
import {getAccessTokenFromCookie} from "@/lib/auth-utils";
import {getConfig} from '@/lib/config';

interface RatingStats {
    average: number;
    count: number;
    distribution: Record<string, number>;
    percentage: number;
}

interface ArticleRatingProps {
    articleId: number | string;
}

const ArticleRating: React.FC<ArticleRatingProps> = ({articleId}) => {
    const [stats, setStats] = useState<RatingStats>({
        average: 0,
        count: 0,
        distribution: {},
        percentage: 0,
    });
    const [userRating, setUserRating] = useState<number>(0);
    const [hoverRating, setHoverRating] = useState<number>(0);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [success, setSuccess] = useState<string | null>(null);

    // 获取文章评分统计
    useEffect(() => {
        fetchRatingStats();
    }, [articleId]);

    const fetchRatingStats = async () => {
        try {
            // 从文章数据中获取评分统计（如果后端已附加）
            // 这里假设文章数据中已经包含了 rating_stats
            // 如果没有，可以单独调用 API 获取
        } catch (err) {
            console.error('获取评分统计失败:', err);
        }
    };

    // 提交评分
    const submitRating = async (rating: number) => {
        setLoading(true);
        setError(null);
        setSuccess(null);

        try {
            // 获取 JWT token
            const token = getAccessTokenFromCookie() || null;

            if (!token) {
                setError('请先登录后再评分');
                setLoading(false);
                return;
            }

            // 获取 API 配置
            const config = getConfig();

            // 调用后端 API 提交评分 - 使用完整的后端地址
            // 注意：文章评分API在 v1 版本中
            const apiUrl = `${config.API_BASE_URL}/api/v1/plugins/article-rating`;
            const response = await fetch(`${apiUrl}/rate`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`, // 添加 JWT token
                },
                body: JSON.stringify({
                    article_id: String(articleId),
                    rating: rating,
                    comment: '',
                }),
            });

            // 检查响应状态
            if (!response.ok) {
                const errorText = await response.text();
                console.error('API 错误响应:', errorText);
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();

            if (data.success) {
                setStats(data.data);
                setUserRating(rating);
                setSuccess('评分成功！');
                setTimeout(() => setSuccess(null), 3000);
            } else {
                setError(data.message || '评分失败');
            }
        } catch (err) {
            const errorMessage = err instanceof Error ? err.message : '网络错误，请稍后重试';
            setError(errorMessage);
            console.error('提交评分失败:', err);
        } finally {
            setLoading(false);
        }
    };

    // 渲染星级
    const renderStars = (interactive: boolean = true) => {
        const stars = [];
        const displayRating = interactive ? (hoverRating || userRating) : stats.average;

        for (let i = 1; i <= 5; i++) {
            const isFilled = i <= displayRating;
            const isHalf = !isFilled && i - 0.5 <= displayRating;

            stars.push(
                <button
                    key={i}
                    type="button"
                    disabled={!interactive || loading}
                    onClick={() => interactive && submitRating(i)}
                    onMouseEnter={() => interactive && setHoverRating(i)}
                    onMouseLeave={() => interactive && setHoverRating(0)}
                    className={`relative flex-shrink-0 ${interactive ? 'cursor-pointer hover:scale-110' : 'cursor-default'} transition-transform`}
                    aria-label={`${i} 星`}
                >
                    <svg
                        className={`w-5 h-5 sm:w-6 sm:h-6 ${
                            isFilled
                                ? 'text-yellow-400 fill-current'
                                : isHalf
                                    ? 'text-yellow-400'
                                    : 'text-gray-300 dark:text-gray-600'
                        }`}
                        viewBox="0 0 24 24"
                    >
                        {isHalf ? (
                            <>
                                {/* 半星效果 */}
                                <defs>
                                    <linearGradient id={`half-${i}`}>
                                        <stop offset="50%" stopColor="currentColor"/>
                                        <stop offset="50%" stopColor="transparent"/>
                                    </linearGradient>
                                </defs>
                                <path
                                    fill={`url(#half-${i})`}
                                    stroke="currentColor"
                                    strokeWidth="1"
                                    d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"
                                />
                            </>
                        ) : (
                            <path
                                d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>
                        )}
                    </svg>
                </button>
            );
        }

        return stars;
    };

    // 渲染评分分布
    const renderDistribution = () => {
        if (stats.count === 0) return null;

        return (
            <div className="mt-4 space-y-2">
                {[5, 4, 3, 2, 1].map((star) => {
                    const count = stats.distribution[star] || 0;
                    const percentage = stats.count > 0 ? (count / stats.count) * 100 : 0;

                    return (
                        <div key={star} className="flex items-center gap-2 text-sm">
                            <span className="text-gray-600 dark:text-gray-400 w-8">{star} 星</span>
                            <div className="flex-1 h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                                <div
                                    className="h-full bg-yellow-400 rounded-full transition-all duration-300"
                                    style={{width: `${percentage}%`}}
                                />
                            </div>
                            <span className="text-gray-600 dark:text-gray-400 w-8 text-right">{count}</span>
                        </div>
                    );
                })}
            </div>
        );
    };

    return (
        <div
            className="bg-gradient-to-br from-blue-50 to-purple-50 dark:from-gray-800 dark:to-gray-900 rounded-xl p-4 sm:p-6 border border-blue-100 dark:border-gray-700 shadow-sm w-full overflow-hidden">
            <h3 className="text-base sm:text-lg font-semibold text-gray-900 dark:text-white mb-3 sm:mb-4 flex items-center gap-2">
                <svg className="w-5 h-5 text-yellow-500 flex-shrink-0" fill="currentColor" viewBox="0 0 24 24">
                    <path
                        d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>
                </svg>
                <span className="truncate">文章评分</span>
            </h3>

            {/* 平均评分显示 */}
            <div className="mb-3 sm:mb-4">
                <div className="flex items-center gap-2 sm:gap-3 mb-2">
                    <div className="flex items-center gap-0.5 flex-shrink-0">{renderStars(false)}</div>
                    <div className="text-xl sm:text-2xl font-bold text-gray-900 dark:text-white">
                        {stats.average.toFixed(1)}
                    </div>
                </div>
                <div className="text-xs sm:text-sm text-gray-600 dark:text-gray-400">
                    共 {stats.count} 人评分
                </div>
            </div>

            {/* 评分分布 */}
            {stats.count > 0 && (
                <div className="mt-3 sm:mt-4 space-y-1.5 sm:space-y-2">
                    {[5, 4, 3, 2, 1].map((star) => {
                        const count = stats.distribution[star] || 0;
                        const percentage = stats.count > 0 ? (count / stats.count) * 100 : 0;

                        return (
                            <div key={star} className="flex items-center gap-2 text-xs sm:text-sm w-full">
                                <span
                                    className="text-gray-600 dark:text-gray-400 w-6 sm:w-8 flex-shrink-0">{star} 星</span>
                                <div
                                    className="flex-1 min-w-0 h-1.5 sm:h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                                    <div
                                        className="h-full bg-yellow-400 rounded-full transition-all duration-300"
                                        style={{width: `${percentage}%`}}
                                    />
                                </div>
                                <span
                                    className="text-gray-600 dark:text-gray-400 w-6 sm:w-8 text-right flex-shrink-0">{count}</span>
                            </div>
                        );
                    })}
                </div>
            )}

            {/* 用户评分区域 */}
            <div className="mt-4 sm:mt-6 pt-4 sm:pt-6 border-t border-blue-200 dark:border-gray-700">
                <p className="text-xs sm:text-sm text-gray-700 dark:text-gray-300 mb-2 sm:mb-3">
                    {userRating > 0 ? '您的评分：' : '点击星星评分：'}
                </p>
                <div className="flex items-center gap-1 sm:gap-2 flex-wrap">{renderStars(true)}</div>

                {/* 成功/错误提示 */}
                {success && (
                    <div
                        className="mt-2 sm:mt-3 text-xs sm:text-sm text-green-600 dark:text-green-400 flex items-center gap-1.5 break-words">
                        <svg className="w-3.5 h-3.5 sm:w-4 sm:h-4 flex-shrink-0" fill="none" stroke="currentColor"
                             viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7"/>
                        </svg>
                        <span className="break-words">{success}</span>
                    </div>
                )}

                {error && (
                    <div
                        className="mt-2 sm:mt-3 text-xs sm:text-sm text-red-600 dark:text-red-400 flex items-center gap-1.5 break-words">
                        <svg className="w-3.5 h-3.5 sm:w-4 sm:h-4 flex-shrink-0" fill="none" stroke="currentColor"
                             viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                                  d="M6 18L18 6M6 6l12 12"/>
                        </svg>
                        <span className="break-words">{error}</span>
                    </div>
                )}
            </div>
        </div>
    );
};

export default ArticleRating;
