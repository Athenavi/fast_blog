'use client';

import React, {memo, useRef} from 'react';

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
    <div className="px-6 py-4 border-b border-gray-200 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
      <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4 w-full sm:w-auto">
        <select
          value={filterMediaType}
          onChange={(e) => {
            setFilterMediaType(e.target.value);
            setCurrentPage(1);
          }}
          className="block w-full sm:w-40 pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-blue-500 focus:border-blue-500 rounded-lg"
        >
          <option value="">所有类型</option>
          <option value="image">图片</option>
          <option value="video">视频</option>
          <option value="audio">音频</option>
          <option value="document">文档</option>
          <option value="application/pdf">PDF</option>
          <option value="application/zip">压缩包</option>
        </select>

        <div className="relative w-full sm:w-64">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <i className="fas fa-search text-gray-400"></i>
          </div>
          <input
            value={searchQuery}
            onChange={(e) => handleSearchChange(e.target.value)}
            className="block w-full pl-10 pr-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-blue-500 focus:border-blue-500"
            placeholder="搜索文件名..."
            type="text"
          />
        </div>
      </div>

      <div className="flex flex-col sm:flex-row items-start sm:items-center gap-2 w-full sm:w-auto">
        <button
          onClick={handleFileSelect}
          className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors flex items-center w-full sm:w-auto justify-center cursor-pointer"
        >
          <i className="fas fa-upload mr-2"></i>上传文件
        </button>
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept="image/*,video/*,audio/*,.pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.zip,.rar"
          className="hidden"
          onChange={handleFileChange}
        />
        <span className="text-sm text-gray-500">
          共 <span className="font-semibold">{totalItems}</span> 个媒体文件
        </span>
      </div>
    </div>
  );
});

SearchAndFilter.displayName = 'SearchAndFilter';

export default SearchAndFilter;