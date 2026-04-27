'use client';

import React, {memo, useEffect, useRef, useState} from 'react';

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
      <div className="bg-gray-50 rounded-lg p-4 mb-6 animate-pulse">
        <div className="h-4 bg-gray-200 rounded w-1/4 mb-2"></div>
        <div className="h-2 bg-gray-200 rounded-full mb-2"></div>
        <div className="h-3 bg-gray-200 rounded w-1/2"></div>
      </div>
    );
  }

  return (
    <div className="bg-gray-50 rounded-lg p-4 mb-6">
      <div className="flex justify-between items-center mb-2">
        <span className="text-sm font-medium text-gray-700">存储使用情况</span>
        <span className="text-sm text-gray-500">{Math.round(animatedPercentage)}%</span>
      </div>

      <div className="w-full bg-gray-200 rounded-full h-2.5 mb-2">
        <div
          className={`${getProgressBarColor()} h-2.5 rounded-full transition-all duration-1000 ease-out`}
          style={{ width: `${animatedPercentage}%` }}
        ></div>
      </div>

      <div className="text-xs text-gray-600 mt-1">
        {stats.storage_used} / {stats.storage_total}
      </div>

      <div className="mt-3 pt-3 border-t border-gray-200">
        <div className="grid grid-cols-2 gap-2">
          <div className="text-xs text-gray-600">
            图片: <span className="font-medium">{stats.image_count}</span>
          </div>
          <div className="text-xs text-gray-600">
            视频: <span className="font-medium">{stats.video_count}</span>
          </div>
        </div>
      </div>
    </div>
  );
});

StorageStats.displayName = 'StorageStats';

export default StorageStats;