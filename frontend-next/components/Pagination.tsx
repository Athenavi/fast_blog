'use client';

import React from 'react';
import {ChevronLeft, ChevronRight, MoreHorizontal} from 'lucide-react';

interface PaginationProps {
  currentPage: number;
  totalPages: number;
  hasNext: boolean;
  hasPrev: boolean;
  onPageChange: (page: number) => void;
  variant?: 'default' | 'modern';
}

const Pagination: React.FC<PaginationProps> = ({
  currentPage,
  totalPages,
  hasNext,
  hasPrev,
  onPageChange,
  variant = 'modern'
}) => {
  if (variant === 'modern') {
    // 生成页码数组
    const getPageNumbers = (): (number | string)[] => {
      const delta = 2;
      const range: number[] = [];
      const rangeWithDots: (number | string)[] = [];
      let l: number | undefined;

      for (let i = 1; i <= totalPages; i++) {
        if (i === 1 || i === totalPages || (i >= currentPage - delta && i <= currentPage + delta)) {
          range.push(i);
        }
      }

      range.forEach((i) => {
        if (l) {
          if (i - l === 2) {
            rangeWithDots.push(l + 1);
          } else if (i - l !== 1) {
            rangeWithDots.push('...');
          }
        }
        rangeWithDots.push(i);
        l = i;
      });

      return rangeWithDots;
    };

    const pageNumbers = getPageNumbers();

    if (totalPages <= 1) return null;

    return (
      <nav className="flex items-center justify-center space-x-2" aria-label="分页">
        {/* 上一页按钮 */}
        <button
          onClick={() => onPageChange(currentPage - 1)}
          disabled={!hasPrev}
          className={`p-2.5 rounded-xl transition-all duration-300 ${
            hasPrev
              ? 'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700'
              : 'bg-gray-50 dark:bg-gray-900 text-gray-400 dark:text-gray-600 cursor-not-allowed'
          }`}
          aria-label="上一页"
        >
          <ChevronLeft className="w-5 h-5" />
        </button>

        {/* 页码 */}
        {pageNumbers.map((pageNumber, index) => (
          <React.Fragment key={index}>
            {pageNumber === '...' ? (
              <span className="px-4 py-2.5 text-gray-400 dark:text-gray-600">
                <MoreHorizontal className="w-5 h-5" />
              </span>
            ) : (
              <button
                onClick={() => onPageChange(Number(pageNumber))}
                className={`px-4 py-2.5 min-w-[44px] rounded-xl font-medium transition-all duration-300 ${
                  currentPage === pageNumber
                    ? 'bg-gradient-to-r from-blue-500 to-blue-600 text-white shadow-lg scale-105'
                    : 'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700'
                }`}
                aria-current={currentPage === pageNumber ? 'page' : undefined}
              >
                {pageNumber}
              </button>
            )}
          </React.Fragment>
        ))}

        {/* 下一页按钮 */}
        <button
          onClick={() => onPageChange(currentPage + 1)}
          disabled={!hasNext}
          className={`p-2.5 rounded-xl transition-all duration-300 ${
            hasNext
              ? 'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700'
              : 'bg-gray-50 dark:bg-gray-900 text-gray-400 dark:text-gray-600 cursor-not-allowed'
          }`}
          aria-label="下一页"
        >
          <ChevronRight className="w-5 h-5" />
        </button>

        {/* 页面信息 */}
        <div className="ml-6 text-sm text-gray-500 dark:text-gray-400 hidden sm:block">
          第 <span className="font-semibold text-gray-700 dark:text-gray-300">{currentPage}</span> 页，
          共 <span className="font-semibold text-gray-700 dark:text-gray-300">{totalPages}</span> 页
        </div>
      </nav>
    );
  }

  // 默认样式（保持兼容性）
  return (
    <div className="flex items-center justify-center space-x-2">
      {/* 原有实现 */}
    </div>
  );
};

export default Pagination;