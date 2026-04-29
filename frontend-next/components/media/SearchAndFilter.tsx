'use client';

import React, {memo, useRef} from 'react';
import {Search, Filter, Upload, Image as ImageIcon, Video, Music, FileText} from 'lucide-react';

interface SearchAndFilterProps {
  filterMediaType: string;
  setFilterMediaType: (type: string) => void;
  searchQuery: string;
  handleSearchChange: (value: string) => void;
  totalItems: number;
  setCurrentPage: (page: number) => void;
  onUploadRequest?: (files: File[]) => void; // 添加这个props
}

const SearchAndFilter: React.FC<SearchAndFilterProps> = memo(({
  filterMediaType,
  setFilterMediaType,
  searchQuery,
  handleSearchChange,
  totalItems,
  setCurrentPage,
  onUploadRequest
}) => {
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileSelect = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0 && onUploadRequest) {
      onUploadRequest(Array.from(files));
      // 重置input以便可以再次选择相同文件
      e.target.value = '';
    }
  };

  return (
      <div
          className="bg-white dark:bg-gray-900 rounded-2xl shadow-sm border border-gray-200 dark:border-gray-800 p-4 mb-6">
          <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-4">
              {/* 左侧：筛选和搜索 */}
              <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3 w-full lg:w-auto">
                  {/* 类型筛选 */}
                  <div className="relative w-full sm:w-48">
                      <Filter className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400"/>
                      <select
                          value={filterMediaType}
                          onChange={(e) => {
                              setFilterMediaType(e.target.value);
                              setCurrentPage(1);
                          }}
                          className="w-full pl-10 pr-4 py-2.5 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white appearance-none cursor-pointer"
                      >
                          <option value="">所有类型</option>
                          <option value="image">图片</option>
                          <option value="video">视频</option>
                          <option value="audio">音频</option>
                          <option value="document">文档</option>
                          <option value="application/pdf">PDF</option>
                          <option value="application/zip">压缩包</option>
                      </select>
          </div>

                  {/* 搜索框 */}
                  <div className="relative w-full sm:w-72">
                      <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400"/>
                      <input
                          value={searchQuery}
                          onChange={(e) => handleSearchChange(e.target.value)}
                          className="w-full pl-10 pr-4 py-2.5 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white"
                          placeholder="搜索文件名..."
                          type="text"
                      />
                  </div>
              </div>

              {/* 右侧：上传按钮和统计 */}
              <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3 w-full lg:w-auto">
                  <button
                      onClick={handleFileSelect}
                      className="inline-flex items-center gap-2 px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-xl transition-colors w-full sm:w-auto justify-center cursor-pointer shadow-lg hover:shadow-xl"
                  >
                      <Upload className="w-4 h-4"/>
                      <span>上传文件</span>
                  </button>
                  <input
                      ref={fileInputRef}
                      type="file"
                      multiple
                      accept="*/*"
                      className="hidden"
                      onChange={handleFileChange}
                  />
                  <span className="text-sm text-gray-600 dark:text-gray-400">
            共 <span className="font-bold text-gray-900 dark:text-white">{totalItems}</span> 个文件
          </span>
              </div>
      </div>
    </div>
  );
});

SearchAndFilter.displayName = 'SearchAndFilter';

export default SearchAndFilter;