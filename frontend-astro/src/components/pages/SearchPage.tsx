'use client';

import React, { useState, useCallback, useEffect, useRef } from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api/base-client';
import { QueryProvider } from '@/components/QueryProvider';
import { Search, Loader2, FileText, Calendar, User, Tag, ChevronLeft, ChevronRight } from 'lucide-react';

interface SearchResult {
  id: number;
  title: string;
  excerpt?: string;
  slug?: string;
  cover_image?: string;
  category_name?: string;
  author_name?: string;
  created_at?: number;
  views?: number;
  likes?: number;
  tags?: string[];
  highlighted_title?: string;
  highlighted_excerpt?: string;
}

interface SearchResponse {
  articles: SearchResult[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
  query: string;
  processing_time_ms?: number;
}

function useDebounce<T>(value: T, delay: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(t);
  }, [value, delay]);
  return debounced;
}

function SearchPageInner() {
  const inputRef = useRef<HTMLInputElement>(null);
  const [query, setQuery] = useState('');
  const [page, setPage] = useState(1);
  const [showSuggestions, setShowSuggestions] = useState(false);

  // 初始化：从 URL 参数读取搜索词
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const q = params.get('q') || '';
    if (q) setQuery(q);
  }, []);

  const debouncedQuery = useDebounce(query, 300);

  // Fetch autocomplete suggestions
  const { data: suggestions } = useQuery<string[]>({
    queryKey: ['search-suggestions', debouncedQuery],
    queryFn: async () => {
      if (!debouncedQuery || debouncedQuery.length < 2) return [];
      const res = await apiClient.get('/search/suggestions', { q: debouncedQuery });
      return res.data?.suggestions || [];
    },
    enabled: debouncedQuery.length >= 2,
  });

  // Fetch search results
  const { data, isLoading } = useQuery<SearchResponse | null>({
    queryKey: ['search-results', debouncedQuery, page],
    queryFn: async () => {
      if (!debouncedQuery) return null;
      const res = await apiClient.get('/search/articles', { q: debouncedQuery, page, per_page: 20 });
      const d = res.data;
      if (!d) return null;
      return {
        articles: d.articles || [],
        total: d.total || 0,
        page: d.page || page,
        per_page: d.per_page || 20,
        total_pages: d.total_pages || Math.ceil((d.total || 0) / 20),
        query: debouncedQuery,
        processing_time_ms: d.processing_time_ms,
      } as SearchResponse;
    },
    enabled: debouncedQuery.length >= 2,
  });

  const onSearch = useCallback((q: string) => {
    setQuery(q);
    setPage(1);
    setShowSuggestions(false);
    const params = new URLSearchParams(window.location.search);
    if (q) params.set('q', q);
    else params.delete('q');
    const newUrl = `/search?${params.toString()}`;
    window.history.replaceState(null, '', newUrl);
  }, []);

  const highlight = (text?: string) => {
    if (!text) return '';
    // The API already returns <mark> tags from Meilisearch
    return text;
  };

  const formatDate = (ts?: number) => {
    if (!ts) return '';
    return new Date(ts * 1000).toLocaleDateString('zh-CN');
  };

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      {/* Search Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-6">搜索</h1>
        <div className="relative">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
          <input
            ref={inputRef}
            value={query}
            onChange={e => { setQuery(e.target.value); setPage(1); }}
            onFocus={() => setShowSuggestions(true)}
            onBlur={() => setTimeout(() => setShowSuggestions(false), 200)}
            placeholder="搜索文章..."
            autoFocus
            className="w-full pl-12 pr-4 py-3.5 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-2xl text-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all"
          />

          {/* Suggestions dropdown */}
          {showSuggestions && suggestions && suggestions.length > 0 && (
            <div className="absolute top-full left-0 right-0 mt-1 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-xl shadow-lg z-50 overflow-hidden">
              {suggestions.map((s, i) => (
                <button
                  key={i}
                  onMouseDown={() => onSearch(s)}
                  className="w-full px-4 py-2.5 text-left text-sm hover:bg-gray-50 dark:hover:bg-gray-800 flex items-center gap-2 transition-colors"
                >
                  <Search className="w-3.5 h-3.5 text-gray-400" />
                  <span>{s}</span>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Loading skeleton */}
      {isLoading && (
        <div className="space-y-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 p-6 animate-pulse">
              <div className="h-5 bg-gray-200 dark:bg-gray-700 rounded w-3/4 mb-3" />
              <div className="h-4 bg-gray-100 dark:bg-gray-800 rounded w-full mb-2" />
              <div className="h-4 bg-gray-100 dark:bg-gray-800 rounded w-2/3" />
            </div>
          ))}
        </div>
      )}

      {/* Search results */}
      {data && !isLoading && (
        <>
          {/* Results header */}
          <div className="flex items-center justify-between mb-4">
            <p className="text-sm text-gray-500">
              找到 <span className="font-semibold text-gray-900 dark:text-white">{data.total}</span> 条结果
              {data.processing_time_ms ? ` (${data.processing_time_ms}ms)` : ''}
            </p>
          </div>

          {data.articles.length === 0 ? (
            <div className="text-center py-20">
              <Search className="w-16 h-16 mx-auto mb-4 text-gray-300" />
              <p className="text-lg font-medium text-gray-500 mb-1">未找到结果</p>
              <p className="text-sm text-gray-400">尝试使用不同的关键词搜索</p>
            </div>
          ) : (
            <div className="space-y-4">
              {data.articles.map((hit: SearchResult) => (
                <a
                  key={hit.id}
                  href={`/p/${hit.slug || hit.id}`}
                  className="block bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 p-6 hover:border-blue-300 dark:hover:border-blue-700 hover:shadow-md transition-all group"
                >
                  <h2
                    className="text-lg font-semibold text-gray-900 dark:text-white mb-2 group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors"
                    dangerouslySetInnerHTML={{ __html: highlight(hit.highlighted_title || hit.title) }}
                  />
                  {(hit.highlighted_excerpt || hit.excerpt) && (
                    <p
                      className="text-sm text-gray-600 dark:text-gray-400 mb-3 line-clamp-2"
                      dangerouslySetInnerHTML={{ __html: highlight(hit.highlighted_excerpt || hit.excerpt) }}
                    />
                  )}
                  <div className="flex items-center gap-3 text-xs text-gray-400">
                    {hit.category_name && (
                      <span className="flex items-center gap-1">
                        <Tag className="w-3 h-3" />
                        {hit.category_name}
                      </span>
                    )}
                    {hit.created_at && (
                      <span className="flex items-center gap-1">
                        <Calendar className="w-3 h-3" />
                        {formatDate(hit.created_at)}
                      </span>
                    )}
                    {hit.author_name && (
                      <span className="flex items-center gap-1">
                        <User className="w-3 h-3" />
                        {hit.author_name}
                      </span>
                    )}
                    {hit.views !== undefined && (
                      <span>{hit.views} 次浏览</span>
                    )}
                  </div>
                </a>
              ))}
            </div>
          )}

          {/* Pagination */}
          {data.total_pages > 1 && (
            <div className="flex items-center justify-center gap-2 mt-8">
              <button
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page <= 1}
                className="p-2 rounded-xl border border-gray-200 dark:border-gray-700 disabled:opacity-30 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              {Array.from({ length: Math.min(data.total_pages, 7) }, (_, i) => {
                let p: number;
                if (data.total_pages <= 7) {
                  p = i + 1;
                } else if (page <= 4) {
                  p = i + 1;
                } else if (page >= data.total_pages - 3) {
                  p = data.total_pages - 6 + i;
                } else {
                  p = page - 3 + i;
                }
                return (
                  <button
                    key={p}
                    onClick={() => setPage(p)}
                    className={`w-9 h-9 rounded-xl text-sm font-medium transition-colors ${
                      p === page
                        ? 'bg-blue-600 text-white'
                        : 'border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800'
                    }`}
                  >
                    {p}
                  </button>
                );
              })}
              <button
                onClick={() => setPage(p => Math.min(data.total_pages, p + 1))}
                disabled={page >= data.total_pages}
                className="p-2 rounded-xl border border-gray-200 dark:border-gray-700 disabled:opacity-30 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          )}
        </>
      )}

      {/* Initial / empty state */}
      {!query && !isLoading && (
        <div className="text-center py-20">
          <Search className="w-16 h-16 mx-auto mb-4 text-gray-300" />
          <p className="text-lg font-medium text-gray-500">输入关键词开始搜索</p>
          <p className="text-sm text-gray-400 mt-1">搜索文章标题和内容</p>
        </div>
      )}
    </div>
  );
}

export default function SearchPage() {
  return <QueryProvider><SearchPageInner /></QueryProvider>;
}
