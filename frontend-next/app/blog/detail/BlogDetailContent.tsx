'use client';

import React, {useEffect, useState} from 'react';
import {ArticleService} from '@/lib/api';
import ArticleDetailClient from '@/components/ArticleDetailClient';
import ArticleSchema from '@/components/ArticleSchema';
import PasswordProtectedArticle from '@/components/PasswordProtectedArticle';

interface BlogDetailContentProps {
    slug: string;
}

const BlogDetailContent: React.FC<BlogDetailContentProps> = ({slug}) => {
    const [articleData, setArticleData] = useState<any>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [requiresPassword, setRequiresPassword] = useState(false);
    const [passwordArticleInfo, setPasswordArticleInfo] = useState<{article_id: number; article_title: string; excerpt: string} | null>(null);

    useEffect(() => {
        if (!slug) {
            return;
        }

        const fetchArticle = async () => {
            try {
                setLoading(true);
                console.log('🚀 开始获取文章, slug:', slug);
                const response = await ArticleService.getArticleBySlug(slug);
                console.log('📦 API返回结果:', response);
                console.log('📦 response.success:', response.success);
                console.log('📦 response.error:', response.error);
                console.log('📦 response.data:', response.data);

                if (response.success && response.data) {
                    console.log('✅ 文章数据获取成功:', response.data);
                    console.log('✅ articleData.article:', response.data.article);
                    console.log('✅ articleData.author:', response.data.author);
                    setArticleData(response.data);
                    setRequiresPassword(false);
                } else {
                    console.error('❌ API返回失败:', response);
                    console.error('❌ response.success:', response.success);
                    console.error('❌ response.data:', response.data);
                    console.error('❌ response.error:', response.error);
                    
                    // 检查是否需要密码
                    const responseData = response.data as any;
                    if (response.error === 'Password required' && responseData?.requires_password) {
                        console.log('🔒 文章需要密码验证');
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
                console.error('❌ 获取文章时发生错误:', err);
                setError(err instanceof Error ? err.message : '加载失败');
            } finally {
                setLoading(false);
            }
        };

        fetchArticle();
    }, [slug]);

    if (loading) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
            </div>
        );
    }

    // 如果需要密码验证，显示密码输入界面
    if (requiresPassword && passwordArticleInfo) {
        return (
            <div className="min-h-screen py-12 px-4">
                <PasswordProtectedArticle
                    articleId={passwordArticleInfo.article_id}
                    onPasswordVerified={() => {
                        // 密码验证成功后重新加载文章
                        setRequiresPassword(false);
                        setPasswordArticleInfo(null);
                        setLoading(true);
                        // 重新获取文章（此时cookie中已有access_token）
                        setTimeout(() => {
                            window.location.reload();
                        }, 500);
                    }}
                />
            </div>
        );
    }

    if (error || !articleData) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <div className="text-center">
                    <h2 className="text-2xl font-bold text-gray-900 mb-2">{error || '文章不存在'}</h2>
                    <p className="text-gray-600">请检查链接是否正确</p>
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
