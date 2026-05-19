'use client';

import React from 'react';
import ArticleRating from '@/components/ArticleRating';
import TableOfContents from '@/components/TableOfContents';

interface ArticleSidebarProps {
    articleId: number | string;
}

const ArticleSidebar: React.FC<ArticleSidebarProps> = ({articleId}) => {
    return (
        <aside className="lg:col-span-4 xl:col-span-3">
            <div className="sticky top-8 space-y-6 w-full">
                {/* 文章评分组件 */}
                <div className="w-full">
                    <ArticleRating articleId={articleId}/>
                </div>

                {/* 目录 */}
                <div
                    className="bg-gray-50 dark:bg-gray-900 rounded-xl p-4 sm:p-6 border border-gray-200 dark:border-gray-800 w-full">
                    <h3 className="text-sm font-semibold text-gray-900 dark:text-white uppercase tracking-wider mb-4">
                        目录
                    </h3>
                    <TableOfContents/>
                </div>
            </div>
        </aside>
    );
};

export default ArticleSidebar;
