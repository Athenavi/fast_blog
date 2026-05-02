/**
 * 首页数据获取Hook
 * 为不同主题的首页组件提供统一的数据接口
 */

'use client';

import {useEffect, useState} from 'react';
import {Article, Category} from '@/lib/api';
import {cachedFetch} from '@/lib/api-cache';

interface HomePageData {
    featuredArticles: Article[];
    recentArticles: Article[];
    popularArticles: Article[];
    categories: Category[];
    loading: boolean;
    error: string | null;
}

export function useHomePageData() {
    const [data, setData] = useState<HomePageData>({
        featuredArticles: [],
        recentArticles: [],
        popularArticles: [],
        categories: [],
        loading: true,
        error: null
    });

    useEffect(() => {
        const fetchData = async () => {
            try {
                setData(prev => ({...prev, loading: true, error: null}));

                // 使用完整的后端 API URL
                const config = await import('@/lib/config');
                const apiConfig = config.getConfig();
                const apiUrl = `${apiConfig.API_BASE_URL}${apiConfig.API_PREFIX}`;

                // 并行获取所有数据，使用缓存
                const [articlesRes, categoriesRes] = await Promise.all([
                    cachedFetch(`${apiUrl}/articles?page=1&page_size=20`, undefined, 5 * 60 * 1000), // 5分钟缓存
                    cachedFetch(`${apiUrl}/categories`, undefined, 10 * 60 * 1000) // 10分钟缓存
                ]);

                const articlesData = articlesRes;
                const categoriesData = categoriesRes;

                if (articlesData.success && categoriesData.success) {
                    const articles = articlesData.data || [];
                    const categories = categoriesData.data || [];

                    // 分类文章
                    const featuredArticles = articles.filter((a: Article) => a.is_featured).slice(0, 3);
                    const recentArticles = articles.slice(0, 9);
                    const popularArticles = [...articles].sort((a: Article, b: Article) => (b.views || 0) - (a.views || 0)).slice(0, 8);

                    setData({
                        featuredArticles,
                        recentArticles,
                        popularArticles,
                        categories: categories.slice(0, 6),
                        loading: false,
                        error: null
                    });
                } else {
                    setData(prev => ({
                        ...prev,
                        loading: false,
                        error: articlesData.error || categoriesData.error || '获取数据失败'
                    }));
                }
            } catch (err) {
                console.error('[useHomePageData] 获取数据失败:', err);
                setData(prev => ({
                    ...prev,
                    loading: false,
                    error: err instanceof Error ? err.message : '未知错误'
                }));
            }
        };

        fetchData();
    }, []);

    return data;
}
