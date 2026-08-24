'use client';

import React, {useCallback, useEffect, useMemo, useRef, useState} from 'react';
import {AnimatePresence, motion} from 'framer-motion';
import {ArticleService} from '@/lib/api';
import type {Article} from '@/lib/api/base-types';
import {
  BookOpen,
  ChevronLeft,
  ChevronRight,
  Filter,
  Grid,
  Hash,
  List,
  Search,
  SlidersHorizontal,
  X
} from 'lucide-react';
import ThemeArticleCard from '@/components/theme/ThemeArticleCard';

type ViewMode = 'grid' | 'list';
type SortBy = 'newest' | 'oldest' | 'popular' | 'views';

const ArticleList: React.FC<{
  initialArticles?: Article[];
  initialTotalPages?: number;
  initialTotalCount?: number;
}> = ({
  initialArticles = [],
  initialTotalPages: initPages = 1,
  initialTotalCount: initCount = 0,
}) => {
  const hasSsrData = initialArticles.length > 0;
  const [articles, setArticles] = useState<Article[]>(initialArticles);
  const [loading, setLoading] = useState(!hasSsrData);
    const [searchQuery, setSearchQuery] = useState('');
    const [viewMode, setViewMode] = useState<ViewMode>('grid');
    const [sortBy, setSortBy] = useState<SortBy>('newest');
    const [currentPage, setCurrentPage] = useState(1);
    const [totalPages, setTotalPages] = useState(initPages);
    const [totalCount, setTotalCount] = useState(initCount);
    const [selectedTag, setSelectedTag] = useState<string | null>(null);
    const [showFilters, setShowFilters] = useState(false);
    const perPage = 12;

    // Fetch articles — 使用 ref 取消机制防止竞态
    const abortRef = useRef<AbortController | null>(null);
    const fetchArticles = useCallback(async () => {
        // 取消前一个未完成的请求
        abortRef.current?.abort();
        const controller = new AbortController();
        abortRef.current = controller;

        setLoading(true);
        try {
            const res = await ArticleService.getArticles({
                page: currentPage,
                per_page: perPage,
                search: searchQuery || undefined,
            } as any);
            if (controller.signal.aborted) return; // 已被新请求取消
            if (res.success && res.data) {
                const d = res.data as any;
                setArticles(d.data || d.articles || []);
                setTotalPages(d.pagination?.total_pages || d.total_pages || Math.ceil((d.pagination?.total || d.total || 0) / perPage));
                setTotalCount(d.pagination?.total || d.total || 0);
            }
        } catch (err: any) {
            if (err?.name === 'AbortError') return;
        } finally {
            if (!controller.signal.aborted) setLoading(false);
        }
    }, [currentPage, searchQuery]);

    const initialLoadDone = useRef(hasSsrData);

    useEffect(() => {
        if (initialLoadDone.current) {
            initialLoadDone.current = false;
            return;
        }
        fetchArticles();
        return () => abortRef.current?.abort();
    }, [fetchArticles]);

    // Debounced search
    const [searchInput, setSearchInput] = useState('');
  useEffect(() => {
      const timer = setTimeout(() => {
          setSearchQuery(searchInput);
          setCurrentPage(1);
      }, 400);
      return () => clearTimeout(timer);
  }, [searchInput]);

    // All unique tags from articles
    const allTags = useMemo(() => {
        const tags = new Set<string>();
        articles.forEach(a => (a.tags || []).forEach(t => tags.add(t)));
        return Array.from(tags).slice(0, 10);
    }, [articles]);

    // Sort options
    const sortOptions: { value: SortBy; label: string }[] = [
        {value: 'newest', label: '最新发布'},
        {value: 'oldest', label: '最早发布'},
        {value: 'popular', label: '最受欢迎'},
        {value: 'views', label: '浏览最多'},
    ];

    // ═══ Skeleton ═══
    const ArticleSkeleton = ({mode}: { mode: ViewMode }) => {
        if (mode === 'list') {
            return (
                <div className="flex gap-4 p-5 rounded-2xl border border-gray-100 dark:border-gray-800">
                    <div className="w-32 h-24 skeleton rounded-xl flex-shrink-0"/>
                    <div className="flex-1 space-y-2">
                        <div className="h-3 w-16 skeleton rounded"/>
                        <div className="h-5 w-3/4 skeleton rounded"/>
                        <div className="h-3 w-full skeleton rounded"/>
                    </div>
                </div>
            );
        }
        return (
            <div className="rounded-2xl overflow-hidden border theme-border">
                <div className="aspect-[16/10] skeleton"/>
                <div className="p-5 space-y-3">
                    <div className="h-3 w-16 skeleton rounded"/>
                    <div className="h-5 skeleton rounded"/>
                    <div className="h-3 w-3/4 skeleton rounded"/>
                </div>
            </div>
        );
    };

  return (
      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8 lg:py-12">
          {/* ═══ Header ═══ */}
          <div className="mb-8">
              <h1 className="text-3xl font-extrabold theme-text mb-2">文章</h1>
              <p className="theme-text-secondary">浏览所有发布的文章内容</p>
          </div>

          {/* ═══ Toolbar ═══ */}
          <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3 mb-8">
              {/* Search */}
              <div className="relative flex-1 w-full sm:max-w-md">
                  <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400"/>
                  <input
                      type="text"
                      value={searchInput}
                      onChange={e => setSearchInput(e.target.value)}
                      placeholder="搜索文章..."
                      className="input-base !pl-10 !pr-10"
                  />
                  {searchInput && (
                      <button
                          onClick={() => setSearchInput('')}
                          className="absolute right-3 top-1/2 -translate-y-1/2 p-0.5 rounded hover:bg-gray-100 dark:hover:bg-gray-800"
                      >
                          <X className="w-4 h-4 text-gray-400"/>
                      </button>
                  )}
              </div>

              <div className="flex items-center gap-2 w-full sm:w-auto">
                  {/* Sort */}
                  <select
                      value={sortBy}
                      onChange={e => {
                          setSortBy(e.target.value as SortBy);
                          setCurrentPage(1);
                      }}
                      className="input-base !w-auto !py-2 text-sm cursor-pointer"
                  >
                      {sortOptions.map(opt => (
                          <option key={opt.value} value={opt.value}>{opt.label}</option>
                      ))}
                  </select>

                  {/* Filter toggle */}
                  <button
                      onClick={() => setShowFilters(!showFilters)}
                      className={`p-2.5 rounded-xl border transition-colors ${showFilters ? 'bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800 text-blue-600' : 'border-gray-200 dark:border-gray-700 text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800'}`}
                  >
                      <SlidersHorizontal className="w-4 h-4"/>
                  </button>

                  {/* View mode */}
                  <div
                      className="flex items-center border border-gray-200 dark:border-gray-700 rounded-xl overflow-hidden">
                      <button
                          onClick={() => setViewMode('grid')}
                          className={`p-2.5 transition-colors ${viewMode === 'grid' ? 'bg-blue-50 dark:bg-blue-900/20 text-blue-600' : 'text-gray-400 hover:text-gray-600'}`}
                      >
                          <Grid className="w-4 h-4"/>
                      </button>
                      <button
                          onClick={() => setViewMode('list')}
                          className={`p-2.5 transition-colors ${viewMode === 'list' ? 'bg-blue-50 dark:bg-blue-900/20 text-blue-600' : 'text-gray-400 hover:text-gray-600'}`}
                      >
                          <List className="w-4 h-4"/>
                      </button>
                  </div>
              </div>
          </div>

          {/* ═══ Tag Filters ═══ */}
          <AnimatePresence>
              {showFilters && (
                  <motion.div
                      initial={{height: 0, opacity: 0}}
                      animate={{height: 'auto', opacity: 1}}
                      exit={{height: 0, opacity: 0}}
                      transition={{duration: 0.2}}
                      className="overflow-hidden mb-6"
                  >
                      <div
                          className="p-4 rounded-xl border border-gray-100 dark:border-gray-800 bg-gray-50/50 dark:bg-gray-900/50">
                          <div className="flex items-center gap-2 mb-3">
                              <Filter className="w-4 h-4 text-gray-400"/>
                              <span className="text-sm font-medium text-gray-700 dark:text-gray-300">标签筛选</span>
                              {selectedTag && (
                                  <button
                                      onClick={() => {
                                          setSelectedTag(null);
                                          setCurrentPage(1);
                                      }}
                                      className="text-xs text-blue-600 hover:text-blue-700 ml-auto"
                                  >
                                      清除筛选
                                  </button>
                              )}
                          </div>
                          <div className="flex flex-wrap gap-2">
                              {allTags.map(tag => (
                                  <button
                                      key={tag}
                                      onClick={() => {
                                          setSelectedTag(selectedTag === tag ? null : tag);
                                          setCurrentPage(1);
                                      }}
                                      className={`px-3 py-1.5 text-xs rounded-lg font-medium transition-colors ${
                                          selectedTag === tag
                                              ? 'bg-blue-600 text-white'
                                              : 'bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-400 border border-gray-200 dark:border-gray-700 hover:border-blue-300 dark:hover:border-blue-700'
                                      }`}
                                  >
                                      <Hash className="w-3 h-3 inline mr-0.5"/>
                                      {tag}
                                  </button>
                              ))}
                          </div>
                      </div>
                  </motion.div>
              )}
          </AnimatePresence>

          {/* ═══ Results Count ═══ */}
          {!loading && (
            <p className="text-sm theme-text-secondary mb-6">
                  {totalCount > 0
                      ? `共 ${totalCount} 篇文章${searchQuery ? ` · 搜索 "${searchQuery}"` : ''}${selectedTag ? ` · 标签 "${selectedTag}"` : ''}`
                      : '未找到相关文章'
                  }
              </p>
          )}

          {/* ═══ Articles Grid / List ═══ */}
          {loading ? (
              <div className={viewMode === 'grid'
                  ? 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6'
                  : 'space-y-4'
              }>
                  {[...Array(6)].map((_, i) => <ArticleSkeleton key={i} mode={viewMode}/>)}
              </div>
          ) : articles.length === 0 ? (
              <div className="text-center py-20">
                  <BookOpen className="w-16 h-16 text-gray-200 dark:text-gray-700 mx-auto mb-4"/>
                <h3 className="text-lg font-semibold text-gray-500 dark:text-gray-400 mb-2">暂无文章</h3>
                  <p className="text-sm text-gray-400">
                      {searchQuery ? '尝试换个关键词搜索' : '还没有发布任何文章'}
                  </p>
              </div>
          ) : viewMode === 'grid' ? (
              /* ── Grid View ── */
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                  {articles.map((article, i) => (
                      <ThemeArticleCard key={article.id} article={article} layout="grid" index={i} />
                  ))}
              </div>
          ) : (
              /* ── List View ── */
              <div className="space-y-4">
                  {articles.map((article, i) => (
                      <ThemeArticleCard key={article.id} article={article} layout="list" index={i} />
                  ))}
              </div>
          )}

          {/* ═══ Pagination ═══ */}
          {totalPages > 1 && (
              <div className="flex items-center justify-center gap-2 mt-10">
                  <button
                      onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                      disabled={currentPage <= 1}
                      className="p-2.5 rounded-xl border border-gray-200 dark:border-gray-700 text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                  >
                      <ChevronLeft className="w-4 h-4"/>
                  </button>
                  {/* Page numbers */}
                  {Array.from({length: Math.min(totalPages, 7)}, (_, i) => {
                      let page: number;
                      if (totalPages <= 7) {
                          page = i + 1;
                      } else if (currentPage <= 4) {
                          page = i + 1;
                      } else if (currentPage >= totalPages - 3) {
                          page = totalPages - 6 + i;
                      } else {
                          page = currentPage - 3 + i;
                      }
                      return (
                          <button
                              key={page}
                              onClick={() => setCurrentPage(page)}
                              className={`w-10 h-10 rounded-xl text-sm font-medium transition-colors ${
                                  currentPage === page
                                      ? 'bg-blue-600 text-white shadow-sm'
                                      : 'border border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800'
                              }`}
                          >
                              {page}
                          </button>
                      );
                  })}
                  <button
                      onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                      disabled={currentPage >= totalPages}
                      className="p-2.5 rounded-xl border border-gray-200 dark:border-gray-700 text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                  >
                      <ChevronRight className="w-4 h-4"/>
                  </button>
              </div>
          )}
    </div>
  );
};

export default ArticleList;
