'use client';

import React, {memo, useEffect, useRef, useState} from 'react';
import {HardDrive} from 'lucide-react';

interface StorageStatsProps {
  stats: {
    storage_percentage: number;
    storage_used: string;
    storage_total: string;
    image_count: number;
    video_count: number;
    canBeUploaded: boolean;
    totalUsed: number;
  };
  loading?: boolean;
}

const StorageStats: React.FC<StorageStatsProps> = memo(({ stats, loading = false }) => {
  const [animatedPercentage, setAnimatedPercentage] = useState(0);
  const animationRef = useRef<number | null>(null);
  const startTimeRef = useRef<number | null>(null);
  const duration = 1000;

  const easeOutCubic = (t: number) => {
    return 1 - Math.pow(1 - t, 3);
  };

  useEffect(() => {
    if (animationRef.current) {
      cancelAnimationFrame(animationRef.current);
    }

    startTimeRef.current = performance.now();
    const startValue = animatedPercentage;
    const targetValue = stats.storage_percentage;
    const diff = targetValue - startValue;

    const animate = (currentTime: number) => {
      if (!startTimeRef.current) return;
      const elapsed = currentTime - startTimeRef.current;
      const progress = Math.min(elapsed / duration, 1);
      const easedProgress = easeOutCubic(progress);
      const currentValue = startValue + diff * easedProgress;

      setAnimatedPercentage(currentValue);

      if (progress < 1) {
        animationRef.current = requestAnimationFrame(animate);
      } else {
        setAnimatedPercentage(targetValue);
      }
    };

    animationRef.current = requestAnimationFrame(animate);

    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [stats.storage_percentage]);

  const getProgressBarColor = () => {
    if (stats.storage_percentage > 80) return 'bg-red-500';
    if (stats.storage_percentage > 60) return 'bg-yellow-500';
    return 'bg-green-500';
  };

  if (loading) {
    return (
        <div
            className="dark:bg-gray-900 rounded-2xl shadow-sm border border-gray-200 dark:border-gray-800 p-6 animate-pulse">
          <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-1/4 mb-3"></div>
          <div className="h-2 bg-gray-200 dark:bg-gray-700 rounded-full mb-3"></div>
          <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-1/2"></div>
      </div>
    );
  }

  return (
      <div className="dark:bg-gray-900 rounded-2xl shadow-sm border border-gray-200 dark:border-gray-800 p-6">
        {/* 标题 */}
        <div className="flex items-center gap-2 mb-4">
          <HardDrive className="w-5 h-5 text-blue-600 dark:text-blue-400"/>
          <span className="text-lg font-bold text-gray-900 dark:text-white">存储使用情况</span>
        </div>

        {/* 进度条 */}
        <div className="mb-4">
          <div className="flex justify-between items-center mb-2">
            <span className="text-sm text-gray-600 dark:text-gray-400">已使用</span>
            <span
                className="text-sm font-semibold text-gray-900 dark:text-white">{Math.round(animatedPercentage)}%</span>
          </div>

          <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-3 overflow-hidden">
            <div
                className={`${getProgressBarColor()} h-3 rounded-full transition-all duration-1000 ease-out`}
                style={{width: `${animatedPercentage}%`}}
            ></div>
          </div>

          <div className="text-xs text-gray-500 dark:text-gray-400 mt-2">
            {stats.storage_used} / {stats.storage_total}
          </div>
        </div>

        {/* 统计信息 */}
        <div className="pt-4 border-t border-gray-200 dark:border-gray-800">
          <div className="grid grid-cols-2 gap-4">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 bg-blue-50 dark:bg-blue-900/20 rounded-lg flex items-center justify-center">
                <svg className="w-4 h-4 text-blue-600 dark:text-blue-400" fill="none" stroke="currentColor"
                     viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2"
                        d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"/>
                </svg>
              </div>
              <div>
                <div className="text-xs text-gray-500 dark:text-gray-400">图片</div>
                <div className="text-lg font-bold text-gray-900 dark:text-white">{stats.image_count}</div>
              </div>
          </div>
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 bg-purple-50 dark:bg-purple-900/20 rounded-lg flex items-center justify-center">
                <svg className="w-4 h-4 text-purple-600 dark:text-purple-400" fill="none" stroke="currentColor"
                     viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2"
                        d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"/>
                </svg>
              </div>
              <div>
                <div className="text-xs text-gray-500 dark:text-gray-400">视频</div>
                <div className="text-lg font-bold text-gray-900 dark:text-white">{stats.video_count}</div>
              </div>
          </div>
        </div>
      </div>
    </div>
  );
});

StorageStats.displayName = 'StorageStats';

export default StorageStats;