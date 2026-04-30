'use client';

import React, {memo} from 'react';
import {Search, Filter, ChevronDown, ChevronUp, PanelLeftClose, PanelLeftOpen} from 'lucide-react';

interface SearchAndFilterProps {
  filterMediaType: string;
  setFilterMediaType: (type: string) => void;
  searchQuery: string;
  handleSearchChange: (value: string) => void;
  totalItems: number;
  setCurrentPage: (page: number) => void;
    uploadAreaCollapsed: boolean;
    onToggleUploadArea: () => void;
    sidebarCollapsed?: boolean;
    onToggleSidebar?: () => void;
}

const SearchAndFilter: React.FC<SearchAndFilterProps> = memo(({
  filterMediaType,
  setFilterMediaType,
  searchQuery,
  handleSearchChange,
  totalItems,
  setCurrentPage,
                                                                  uploadAreaCollapsed,
                                                                  onToggleUploadArea,
                                                                  sidebarCollapsed,
                                                                  onToggleSidebar
}) => {

  return (
      <div
          className="dark:bg-gray-900 rounded-2xl shadow-sm border border-gray-200 dark:border-gray-800 p-4 mb-6">
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

              {/* 右侧：折叠/展开按钮和统计 */}
              <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3 w-full lg:w-auto">
                  {/* 移动端侧边栏切换按钮 */}
                  {onToggleSidebar && (
                      <button
                          onClick={onToggleSidebar}
                          className="lg:hidden inline-flex items-center justify-center p-2.5 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300 font-medium rounded-xl transition-colors cursor-pointer"
                          title={sidebarCollapsed ? '展开侧边栏' : '折叠侧边栏'}
                      >
                          {sidebarCollapsed ? (
                              <PanelLeftOpen className="w-4 h-4"/>
                          ) : (
                              <PanelLeftClose className="w-4 h-4"/>
                          )}
                      </button>
                  )}
                  
                  <button
                      onClick={onToggleUploadArea}
                      className="inline-flex items-center gap-2 px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-xl transition-colors w-full sm:w-auto justify-center cursor-pointer shadow-lg hover:shadow-xl"
                      title={uploadAreaCollapsed ? '展开上传区域' : '折叠上传区域'}
                  >
                      {uploadAreaCollapsed ? (
                          <>
                              <ChevronDown className="w-4 h-4"/>
                          </>
                      ) : (
                          <>
                              <ChevronUp className="w-4 h-4"/>
                          </>
                      )}
                  </button>
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