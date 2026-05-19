'use client';

import React from 'react';

interface SkeletonProps {
    className?: string;
}

/**
 * 通用骨架屏组件
 */
export function Skeleton({className = ''}: SkeletonProps) {
    return (
        <div className={`skeleton ${className}`}/>
    );
}

/**
 * 文本骨架屏
 */
export function TextSkeleton({lines = 3, className = ''}: { lines?: number; className?: string }) {
    return (
        <div className={className}>
            {Array.from({length: lines}).map((_, index) => (
                <div
                    key={index}
                    className={`skeleton skeleton-text ${index === lines - 1 ? 'w-3/4' : 'w-full'}`}
                />
            ))}
        </div>
    );
}

/**
 * 标题骨架屏
 */
export function TitleSkeleton({className = ''}: { className?: string }) {
    return (
        <div className={`skeleton skeleton-title ${className}`}/>
    );
}

/**
 * 头像骨架屏
 */
export function AvatarSkeleton({size = 'md', className = ''}: { size?: 'sm' | 'md' | 'lg'; className?: string }) {
    const sizeClasses = {
        sm: 'w-8 h-8',
        md: 'w-12 h-12',
        lg: 'w-16 h-16',
    };

    return (
        <div className={`skeleton skeleton-avatar ${sizeClasses[size]} ${className}`}/>
    );
}

/**
 * 图片骨架屏
 */
export function ImageSkeleton({className = ''}: { className?: string }) {
    return (
        <div className={`skeleton skeleton-image ${className}`}/>
    );
}

/**
 * 卡片骨架屏
 */
export function CardSkeleton({className = ''}: { className?: string }) {
    return (
        <div className={`space-y-4 p-4 border rounded-lg ${className}`}>
            <div className="flex items-center space-x-4">
                <AvatarSkeleton size="md"/>
                <div className="flex-1 space-y-2">
                    <TitleSkeleton className="w-1/2"/>
                    <TextSkeleton lines={1} className="w-3/4"/>
                </div>
            </div>
            <ImageSkeleton className="h-48"/>
            <TextSkeleton lines={3}/>
        </div>
    );
}

/**
 * 列表项骨架屏
 */
export function ListItemSkeleton({className = ''}: { className?: string }) {
    return (
        <div className={`flex items-center space-x-4 p-4 border-b ${className}`}>
            <AvatarSkeleton size="sm"/>
            <div className="flex-1 space-y-2">
                <TitleSkeleton className="w-1/3"/>
                <TextSkeleton lines={1} className="w-2/3"/>
            </div>
        </div>
    );
}

/**
 * 文章卡片骨架屏
 */
export function ArticleCardSkeleton({className = ''}: { className?: string }) {
    return (
        <div className={`space-y-4 p-6 border rounded-lg shadow-sm ${className}`}>
            <ImageSkeleton className="h-56 w-full"/>
            <div className="space-y-3">
                <TitleSkeleton className="w-3/4"/>
                <TextSkeleton lines={2}/>
                <div className="flex items-center justify-between pt-2">
                    <div className="flex items-center space-x-2">
                        <AvatarSkeleton size="sm"/>
                        <div className="skeleton w-24 h-4"/>
                    </div>
                    <div className="skeleton w-20 h-4"/>
                </div>
            </div>
        </div>
    );
}

/**
 * 表格骨架屏
 */
export function TableSkeleton({rows = 5, cols = 4, className = ''}: {
    rows?: number;
    cols?: number;
    className?: string;
}) {
    return (
        <div className={`overflow-hidden border rounded-lg ${className}`}>
            {/* 表头 */}
            <div className="grid gap-4 p-4 bg-gray-50 dark:bg-gray-800 border-b">
                <div className={`grid grid-cols-${cols} gap-4`}>
                    {Array.from({length: cols}).map((_, index) => (
                        <div key={index} className="skeleton h-6"/>
                    ))}
                </div>
            </div>

            {/* 表格行 */}
            <div className="divide-y">
                {Array.from({length: rows}).map((_, rowIndex) => (
                    <div key={rowIndex} className="grid gap-4 p-4">
                        <div className={`grid grid-cols-${cols} gap-4`}>
                            {Array.from({length: cols}).map((_, colIndex) => (
                                <div key={colIndex} className="skeleton h-4"/>
                            ))}
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}

/**
 * 图表骨架屏
 */
export function ChartSkeleton({height = 'h-64', className = ''}: {
    height?: string;
    className?: string;
}) {
    return (
        <div className={`space-y-4 p-4 border rounded-lg ${className}`}>
            <div className="flex items-center justify-between">
                <TitleSkeleton className="w-1/4"/>
                <div className="skeleton w-32 h-8"/>
            </div>
            <div className={`skeleton ${height} w-full`}/>
        </div>
    );
}

/**
 * 侧边栏骨架屏
 */
export function SidebarSkeleton({className = ''}: { className?: string }) {
    return (
        <div className={`space-y-6 p-4 ${className}`}>
            {/* 搜索框 */}
            <div className="skeleton h-10 w-full"/>

            {/* 分类列表 */}
            <div className="space-y-3">
                <TitleSkeleton className="w-1/2"/>
                {Array.from({length: 5}).map((_, index) => (
                    <div key={index} className="skeleton h-6 w-full"/>
                ))}
            </div>

            {/* 标签云 */}
            <div className="space-y-3">
                <TitleSkeleton className="w-1/3"/>
                <div className="flex flex-wrap gap-2">
                    {Array.from({length: 8}).map((_, index) => (
                        <div key={index} className="skeleton h-6 w-16 rounded-full"/>
                    ))}
                </div>
            </div>
        </div>
    );
}

/**
 * 评论列表骨架屏
 */
export function CommentListSkeleton({count = 3, className = ''}: {
    count?: number;
    className?: string;
}) {
    return (
        <div className={`space-y-6 ${className}`}>
            {Array.from({length: count}).map((_, index) => (
                <div key={index} className="flex space-x-4">
                    <AvatarSkeleton size="md"/>
                    <div className="flex-1 space-y-3">
                        <div className="flex items-center space-x-2">
                            <div className="skeleton h-4 w-24"/>
                            <div className="skeleton h-3 w-20"/>
                        </div>
                        <TextSkeleton lines={2}/>
                        <div className="flex items-center space-x-4">
                            <div className="skeleton h-4 w-16"/>
                            <div className="skeleton h-4 w-16"/>
                        </div>
                    </div>
                </div>
            ))}
        </div>
    );
}
