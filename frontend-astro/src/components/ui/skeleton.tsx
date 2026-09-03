/**
 * Skeleton - 统一骨架屏组件
 * 用于加载状态的占位动画，支持多种形状
 */

import React from 'react';

interface SkeletonProps {
  className?: string;
  style?: React.CSSProperties;
  variant?: 'pulse' | 'shimmer';
  width?: string | number;
  height?: string | number;
  borderRadius?: string;
  animated?: boolean;
}

export const Skeleton: React.FC<SkeletonProps> = ({
                                                    className = '',
                                                    style = {},
                                                    variant = 'pulse',
                                                    width,
                                                    height,
                                                    borderRadius = '0.5rem',
                                                    animated = true,
                                                  }) => {
  return (
    <div
      className={`skeleton ${variant === 'shimmer' ? 'skeleton-shimmer' : 'animate-pulse'} ${className}`}
      style={{
        width,
        height,
        borderRadius,
        backgroundColor: 'rgba(100, 116, 139, 0.2)',
        ...style,
      }}
      role="status"
      aria-label="加载中"
    />
  );
};

export const SkeletonCard: React.FC<{ variant?: 'article' | 'media' | 'user' }> = ({variant = 'article'}) => {
  if (variant === 'media') {
    return (
      <div className="rounded-2xl overflow-hidden border theme-border bg-card">
        <Skeleton height="160px" borderRadius="0"/>
        <div className="p-3 space-y-2">
          <Skeleton height="14px" width="60%"/>
          <Skeleton height="10px" width="40%"/>
        </div>
      </div>
    );
  }
  if (variant === 'user') {
    return (
      <div className="flex items-center gap-3 p-3">
        <Skeleton width="40px" height="40px" borderRadius="50%"/>
        <div className="space-y-2 flex-1">
          <Skeleton height="14px" width="60%"/>
          <Skeleton height="10px" width="40%"/>
        </div>
      </div>
    );
  }
  return (
    <div className="rounded-2xl overflow-hidden border theme-border bg-card">
      <Skeleton height="200px" borderRadius="0"/>
      <div className="p-4 space-y-3">
        <Skeleton height="12px" width="30%"/>
        <Skeleton height="16px"/>
        <Skeleton height="12px" width="80%"/>
      </div>
    </div>
  );
};
