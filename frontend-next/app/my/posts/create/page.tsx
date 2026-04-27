'use client';

import React, {useEffect, useState} from 'react';
import {useRouter} from 'next/navigation';
import dynamic from 'next/dynamic';
import {ArticleService} from '@/lib/api';
import LoadingState from '@/components/LoadingState';
import ErrorState from '@/components/ErrorState';

// 动态导入表单组件
const ArticleForm = dynamic(
    () => import('@/components/ArticleForm'),
    {
        ssr: false,
        loading: () => <LoadingState message="加载表单中..."/>
    }
);

const CreateArticlePage = () => {
    const router = useRouter();
    const [categories, setCategories] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    // 加载分类数据
    useEffect(() => {
        const fetchCategories = async () => {
            try {
                const result = await ArticleService.getNewArticleData();

                if (result.success && result.data) {
                    setCategories(result.data.categories || []);
                } else {
                    setError(result.error || '获取分类失败');
                }
            } catch (err) {
                console.error('加载分类失败:', err);
                setError('加载失败，请刷新重试');
            } finally {
                setLoading(false);
            }
        };

        fetchCategories();
    }, []);

    // 处理表单提交
    const handleSubmit = async (formData: any) => {
        try {
            const form = new FormData();
            Object.entries(formData).forEach(([key, value]) => {
                if (key === 'tags') {
                    form.append(key, (value as string[]).join(','));
                } else if (['hidden', 'is_vip_only', 'is_featured'].includes(key)) {
                    form.append(key, value ? '1' : '0');
                } else {
                    form.append(key, String(value));
                }
            });

            const result = await ArticleService.createArticle(form);
            return result;
        } catch (err) {
            console.error('创建文章失败:', err);
            return {success: false, error: '创建失败'};
        }
    };

    const handleCancel = () => {
        router.back();
    };

    if (loading) {
        return <LoadingState message="加载中..."/>;
    }

    if (error) {
        return <ErrorState error={error} retryAction={() => window.location.reload()}/>;
    }

    return (
        <ArticleForm
            mode="create"
            categories={categories}
            onSubmit={handleSubmit}
            onCancel={handleCancel}
            isLoading={loading}
        />
    );
};

export default CreateArticlePage;