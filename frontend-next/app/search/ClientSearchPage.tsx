'use client';

import React, {useEffect, useState} from 'react';
import {useSearchParams} from 'next/navigation';

interface SearchResult {
  id?: string | number;
  title: string;
  link: string;
  [key: string]: any;
}

const ClientSearchPage = () => {
  const searchParams = useSearchParams();
  const [searchKeyword, setSearchKeyword] = useState('');
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [searchHistory, setSearchHistory] = useState<string[]>([]);
  const [isSearching, setIsSearching] = useState(false);

  // 从URL参数获取关键词
  useEffect(() => {
    const keyword = searchParams.get('keyword');
    if (keyword) {
      const decodedKeyword = decodeURIComponent(keyword);
      setSearchKeyword(decodedKeyword);
      performSearch(decodedKeyword);
    }
    
    // 加载搜索历史
    loadSearchHistory();
  }, [searchParams]);

  const performSearch = async (keyword = searchKeyword) => {
    if (!keyword.trim()) return;

    setIsSearching(true);
    try {
      // 在真实实现中，这里会调用搜索API
      // const response = await searchService.search(keyword);
      
      // 模拟搜索结果
      setTimeout(() => {
        const mockResults = Array.from({ length: 5 }, (_, i) => ({
          id: i + 1,
          title: `${keyword} 示例结果 ${i + 1}`,
          link: `/blog/${keyword}-article-${i + 1}`
        }));
        
        setSearchResults(mockResults);
        addToSearchHistory(keyword);
        setIsSearching(false);
      }, 500);
    } catch (error) {
      console.error('搜索失败:', error);
      setSearchResults([]);
      setIsSearching(false);
    }
  };

  const addToSearchHistory = (keyword: string) => {
    // 确保历史记录中不重复，并限制数量
    const index = searchHistory.indexOf(keyword);
    if (index !== -1) {
      searchHistory.splice(index, 1);
    }
    const newHistory = [keyword, ...searchHistory];
    const trimmedHistory = newHistory.slice(0, 10); // 限制最多10条历史记录
    setSearchHistory(trimmedHistory);
    
    // 保存到localStorage
    try {
      localStorage.setItem('searchHistory', JSON.stringify(trimmedHistory));
    } catch (error) {
      console.error('保存搜索历史失败:', error);
    }
  };

  const useSearchHistory = (keyword: string) => {
    setSearchKeyword(keyword);
    performSearch(keyword);
  };

  const loadSearchHistory = () => {
    try {
      const history = localStorage.getItem('searchHistory');
      if (history) {
        setSearchHistory(JSON.parse(history));
      }
    } catch (error) {
      console.error('加载搜索历史失败:', error);
      setSearchHistory([]);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    performSearch();
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-gray-900 dark:to-gray-800 flex items-center justify-center p-4">
      <div className="w-full max-w-2xl">
        <div className="bg-white rounded-xl shadow-lg p-8 transition-transform duration-300 hover:shadow-xl dark:bg-gray-800 dark:shadow-xl">
          <h1 className="text-3xl font-bold text-center mb-4 bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent dark:from-blue-400 dark:to-purple-400">
            智能搜索
          </h1>
          <p className="text-gray-600 text-center mb-8 dark:text-gray-300">探索您需要的信息</p>

          <form className="search-form" onSubmit={handleSubmit} role="search">
            <div className="search-input-container relative mb-6">
              <input
                value={searchKeyword}
                onChange={(e) => setSearchKeyword(e.target.value)}
                type="search"
                className="search-input w-full px-6 py-4 border-2 border-gray-200 rounded-xl text-lg focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-200 transition-all dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                placeholder="输入关键词..."
                required
              />
            </div>
            <button 
              type="submit" 
              disabled={isSearching}
              className="search-button w-full bg-blue-600 hover:bg-blue-700 text-white py-4 rounded-xl text-lg font-semibold transition-all duration-300 transform hover:-translate-y-1 hover:shadow-lg active:translate-y-0 dark:bg-blue-600 dark:hover:bg-blue-700 disabled:opacity-75"
            >
              {isSearching ? (
                <span className="flex items-center justify-center">
                  <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  搜索中...
                </span>
              ) : '搜索'}
            </button>
          </form>

          {searchHistory.length > 0 && (
            <div className="history-section mt-8 animate-fadeIn">
              <h3 className="section-title flex items-center text-xl font-semibold mb-4 text-gray-800 dark:text-white">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" className="w-5 h-5 mr-2">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/>
                </svg>
                搜索历史
              </h3>
              <ul className="history-list">
                {searchHistory.map((history, index) => (
                  <li 
                    key={index}
                    className="history-item bg-gray-100 hover:bg-gray-200 text-gray-700 hover:text-blue-600 p-3 rounded-lg mb-2 cursor-pointer transition-colors dark:bg-gray-700 dark:hover:bg-gray-600 dark:text-gray-300 dark:hover:text-blue-400"
                    onClick={() => useSearchHistory(history)}
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16" className="inline mr-2">
                      <path d="M11.742 10.344a6.5 6.5 0 1 0-1.397 1.398h-.001c.03.04.062.078.098.115l3.85 3.85a1 1 0 0 0 1.415-1.414l-3.85-3.85a1.007 1.007 0 0 0-.115-.1zM12 6.5a5.5 5.5 0 1 1-11 0 5.5 5.5 0 0 1 11 0z"/>
                    </svg>
                    {history}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {searchResults.length > 0 ? (
            <div className="results-section mt-8 animate-fadeIn">
              <h3 className="section-title flex items-center text-xl font-semibold mb-4 text-gray-800 dark:text-white">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" className="w-5 h-5 mr-2">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"/>
                </svg>
                搜索结果
              </h3>
              <ul className="results-list">
                {searchResults.map((result, index) => (
                  <li 
                    key={result.id || result.title}
                    className="result-item bg-white border border-gray-200 rounded-lg mb-2 hover:border-blue-500 hover:shadow-md transition-all duration-200 dark:bg-gray-700 dark:border-gray-600 dark:hover:border-blue-400"
                  >
                    <a 
                      href={result.link} 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="result-link block p-3 flex justify-between items-center text-gray-700 hover:text-blue-600 dark:text-gray-300 dark:hover:text-blue-400"
                    >
                      <span className="result-title font-medium">{result.title}</span>
                      <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16" className="external-icon opacity-70 transition-opacity group-hover:opacity-100">
                        <path fillRule="evenodd" d="M8.636 3.5a.5.5 0 0 0-.5-.5H1.5A1.5 1.5 0 0 0 0 4.5v10A1.5 1.5 0 0 0 1.5 16h10a1.5 1.5 0 0 0 1.5-1.5V7.864a.5.5 0 0 0-1 0V14.5a.5.5 0 0 1-.5.5h-10a.5.5 0 0 1-.5-.5v-10a.5.5 0 0 1 .5-.5h6.636a.5.5 0 0 0 .5-.5z"/>
                        <path fillRule="evenodd" d="M16 .5a.5.5 0 0 0-.5-.5h-5a.5.5 0 0 0 0 1h3.793L6.146 9.146a.5.5 0 1 0 .708.708L15 1.707V5.5a.5.5 0 0 0 1 0v-5z"/>
                      </svg>
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          ) : searchKeyword && !isSearching ? (
            <div className="no-results text-center py-8 text-gray-600 dark:text-gray-400">
              没有找到相关结果，请尝试其他关键词
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
};

export default ClientSearchPage;