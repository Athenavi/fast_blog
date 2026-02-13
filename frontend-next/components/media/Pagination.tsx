'use client';

import React, {memo, useMemo} from 'react';

interface PaginationProps {
  currentPage: number;
  totalPages: number;
  totalItems: number;
  perPage: number;
  goToPage: (page: number) => void;
  startIndex: number;
  endIndex: number;
}

const Pagination: React.FC<PaginationProps> = memo(({
  currentPage,
  totalPages,
  totalItems,
  perPage,
  goToPage,
  startIndex,
  endIndex
}) => {
  const getPageNumbers = useMemo(() => {
    const pages: (number | string)[] = [];
    const start = Math.max(1, currentPage - 2);
    const end = Math.min(totalPages, currentPage + 2);

    if (start > 1) {
      pages.push(1);
      if (start > 2) {
        pages.push('...');
      }
    }

    for (let i = start; i <= end; i++) {
      pages.push(i);
    }

    if (end < totalPages) {
      if (end < totalPages - 1) {
        pages.push('...');
      }
      pages.push(totalPages);
    }

    return pages;
  }, [currentPage, totalPages]);

  if (totalPages <= 1) return null;

  return (
    <div className="px-6 py-4 border-t border-gray-200 flex flex-col sm:flex-row items-center justify-between">
      <div className="flex items-center space-x-2 mb-4 sm:mb-0">
        <button
          disabled={currentPage === 1}
          className={`px-3 py-1 rounded border text-sm ${
            currentPage === 1
              ? 'border-gray-300 text-gray-400 cursor-not-allowed'
              : 'border-gray-300 text-gray-700 hover:bg-gray-50'
          }`}
          onClick={() => goToPage(currentPage - 1)}
        >
          上一页
        </button>

        {getPageNumbers.map((pageNum, index) => (
          <React.Fragment key={index}>
            {typeof pageNum === 'number' ? (
              <button
                className={`px-3 py-1 rounded text-sm ${
                  pageNum === currentPage
                    ? 'bg-blue-500 text-white'
                    : 'border border-gray-300 text-gray-700 hover:bg-gray-50'
                }`}
                onClick={() => goToPage(pageNum)}
              >
                {pageNum}
              </button>
            ) : (
              <span className="px-2">...</span>
            )}
          </React.Fragment>
        ))}

        <button
          disabled={currentPage === totalPages}
          className={`px-3 py-1 rounded border text-sm ${
            currentPage === totalPages
              ? 'border-gray-300 text-gray-400 cursor-not-allowed'
              : 'border-gray-300 text-gray-700 hover:bg-gray-50'
          }`}
          onClick={() => goToPage(currentPage + 1)}
        >
          下一页
        </button>
      </div>

      <div className="text-sm text-gray-500">
        显示 {startIndex}-{Math.min(endIndex, totalItems)} 条，共 {totalItems} 个文件
      </div>
    </div>
  );
});

Pagination.displayName = 'Pagination';

export default Pagination;