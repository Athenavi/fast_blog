'use client';

import React, {useEffect, useState} from 'react';
import {useSearchParams} from 'next/navigation';
import {SearchService} from '@/lib/api/search-service';
import type {Article} from '@/lib/api/base-types';

interface SearchResult {
  id?: string | number;
  title: string;
  link: string;
  excerpt?: string;
  views?: number;
  likes?: number;
  created_at?: string;
  article?: Article;
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
      // 调用真实的搜索 API
      const response = await SearchService.search(keyword, 1, 20);

      if (response.success && response.data) {
        // 转换搜索结果为组件需要的格式
        const results: SearchResult[] = response.data.articles.map(article => ({
          id: article.id,
          title: article.title,
          link: `/blog/detail?slug=${article.slug || article.id}`,
          excerpt: article.excerpt || '',
          views: article.views,
          likes: article.likes,
          created_at: article.created_at,
          article
        }));

        setSearchResults(results);
        SearchService.saveToLocalStorage(keyword);
      } else {
        console.error('搜索失败:', response.error);
        setSearchResults([]);
      }
    } catch (error) {
      console.error('搜索失败:', error);
      setSearchResults([]);
    } finally {
      setIsSearching(false);
    }
  };


  const applySearchHistory = (keyword: string) => {
    setSearchKeyword(keyword);
    performSearch(keyword);
  };

  const loadSearchHistory = () => {
    const history = SearchService.loadFromLocalStorage();
    setSearchHistory(history);
  };

  const handleHistoryClick = (keyword: string) => {
    applySearchHistory(keyword);
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
                    onClick={() => applySearchHistory(history)}
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16" className="inline mr-2">
                      <path d="M11.742 10.344a6.5 6.5 0 1 0-1.397 1.398h-.001c.03.04.062.078.098.115l3.85 3.85a1 1 0 0 0 1.415-1.414l-3.85-3.85a1.007 1.007 0 0 0-.115-.1zM12 6.5a5.5 5.5 0 1 1-11 0 5.5 5.5 0 0 1 11 0z"/>
                    </svg>
                    {history}
                  </li>
                ))}
              </ul>
              {searchHistory.length > 0 && (
                  <div className="mt-4 text-right">
                    <button
                        onClick={() => {
                          SearchService.clearHistory();
                          setSearchHistory([]);
                        }}
                        className="text-sm text-red-600 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300"
                    >
                      清除搜索历史
                    </button>
                  </div>
              )}
            </div>
          )}

          {searchResults.length > 0 ? (
            <div className="results-section mt-8 animate-fadeIn">
              <h3 className="section-title flex items-center text-xl font-semibold mb-4 text-gray-800 dark:text-white">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" className="w-5 h-5 mr-2">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"/>
                </svg>
                搜索结果（共 {searchResults.length} 条）
              </h3>
              <ul className="results-list">
                {searchResults.map((result, index) => (
                  <li 
                    key={result.id || result.title}
                    className="result-item bg-white border border-gray-200 rounded-lg mb-2 hover:border-blue-500 hover:shadow-md transition-all duration-200 dark:bg-gray-700 dark:border-gray-600 dark:hover:border-blue-400"
                  >
                    <a
                        href={result.link}
                        className="result-link block p-4 dark:text-gray-200"
                    >
                      <h4 className="result-title font-medium text-lg mb-2 text-blue-600 dark:text-blue-400 hover:underline">
                        {result.title}
                      </h4>
                      {result.excerpt && (
                          <p className="text-gray-600 dark:text-gray-400 text-sm mb-2 line-clamp-2">
                            {result.excerpt}
                          </p>
                      )}
                      <div className="flex items-center gap-4 text-xs text-gray-500 dark:text-gray-400">
                        {result.views !== undefined && (
                            <span className="flex items-center">
                            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" fill="currentColor"
                                 viewBox="0 0 16 16" className="mr-1">
                              <path
                                  d="M16 8s-3-5.5-8-5.5S0 8 0 8s3 5.5 8 5.5S16 8 16 8zM1.173 8a13.133 13.133 0 0 1 1.66-2.043C4.12 4.668 5.88 3.5 8 3.5c2.12 0 3.879 1.168 5.168 2.457A13.133 13.133 0 0 1 14.828 8c-.058.087-.123.183-.197.284-.335.48-.83 1.12-1.465 1.755C11.879 11.332 10.119 12.5 8 12.5c-2.12 0-3.879-1.168-5.168-2.457A13.134 13.134 0 0 1 1.172 8z"/>
                              <path
                                  d="M8 5.5a2.5 2.5 0 1 0 0 5 2.5 2.5 0 0 0 0-5zM4.5 8a3.5 3.5 0 1 1 7 0 3.5 3.5 0 0 1-7 0z"/>
                            </svg>
                              {result.views}
                          </span>
                        )}
                        {result.likes !== undefined && (
                            <span className="flex items-center">
                            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" fill="currentColor"
                                 viewBox="0 0 16 16" className="mr-1">
                              <path
                                  d="m8 2.748-.717-.737C5.6.281 2.514.878 1.4 3.053c-.523 1.023-.641 2.5.314 4.385.92 1.815 2.834 3.989 6.286 6.357 3.452-2.368 5.365-4.542 6.286-6.357.955-1.886.838-3.362.314-4.385C13.486.878 10.4.28 8.717 2.01L8 2.748zM8 15C-7.333 4.868 3.279-3.04 7.824 1.143c.06.055.119.112.176.171a3.12 3.12 0 0 1 .176-.17C12.72-3.042 23.333 4.867 8 15z"/>
                            </svg>
                              {result.likes}
                          </span>
                        )}
                        {result.created_at && (
                            <span className="flex items-center">
                            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" fill="currentColor"
                                 viewBox="0 0 16 16" className="mr-1">
                              <path
                                  d="M8 3.5a.5.5 0 0 0-1 0V9a.5.5 0 0 0 .252.434l3.5 2a.5.5 0 0 0 .496-.868L8 8.71V3.5z"/>
                              <path d="M8 16A8 8 0 1 0 8 0a8 8 0 0 0 0 16zm7-8A7 7 0 1 1 1 8a7 7 0 0 1 14 0z"/>
                            </svg>
                              {new Date(result.created_at).toLocaleDateString('zh-CN')}
                          </span>
                        )}
                      </div>
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