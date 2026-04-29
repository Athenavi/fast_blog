'use client';

import React, {useEffect, useState} from 'react';
import {ArticleService} from '@/lib/api';
import ArticleDetailClient from './ArticleDetailClient';
import ArticleSchema from '@/components/ArticleSchema';
import PasswordProtectedArticle from '@/components/PasswordProtectedArticle';
import LoadingState from '@/components/LoadingState';

interface BlogDetailContentProps {
    slug: string;
}

const BlogDetailContent: React.FC<BlogDetailContentProps> = ({slug}) => {
    const [articleData, setArticleData] = useState<any>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [requiresPassword, setRequiresPassword] = useState(false);
    const [passwordArticleInfo, setPasswordArticleInfo] = useState<{
        article_id: number;
        article_title: string;
        excerpt: string
    } | null>(null);

    useEffect(() => {
        if (!slug) return;

        const fetchArticle = async () => {
            try {
                setLoading(true);
                const response = await ArticleService.getArticleBySlug(slug);

                if (response.success && response.data) {
                    setArticleData(response.data);
                    setRequiresPassword(false);
                } else {
                    const responseData = response.data as any;
                    if (response.error === 'Password required' && responseData?.requires_password) {
                        setRequiresPassword(true);
                        setPasswordArticleInfo({
                            article_id: responseData.article_id,
                            article_title: responseData.article_title,
                            excerpt: responseData.excerpt
                        });
                    } else {
                        setError(response.error || '文章不存在');
                        setRequiresPassword(false);
                    }
                }
            } catch (err) {
                setError(err instanceof Error ? err.message : '加载失败');
            } finally {
                setLoading(false);
            }
        };

        fetchArticle();
    }, [slug]);

    if (loading) {
        return <LoadingState message="加载文章中..."/>;
    }

    if (requiresPassword && passwordArticleInfo) {
        return (
            <div className="min-h-screen py-12 px-4">
                <PasswordProtectedArticle
                    articleId={passwordArticleInfo.article_id}
                    onPasswordVerified={() => {
                        setRequiresPassword(false);
                        setPasswordArticleInfo(null);
                        setLoading(true);
                        setTimeout(() => window.location.reload(), 500);
                    }}
                />
            </div>
        );
    }

    if (error || !articleData) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <div className="text-center">
                    <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
                        {error || '文章不存在'}
                    </h2>
                    <p className="text-gray-600 dark:text-gray-400">请检查链接是否正确</p>
                </div>
            </div>
        );
    }

    return (
        <>
            <ArticleSchema article={articleData}/>
            <ArticleDetailClient articleData={articleData}/>
        </>
    );
};

export default BlogDetailContent;
