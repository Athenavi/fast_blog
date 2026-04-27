/**
 * Magazine主题 - 文章卡片组件
 */
'use client';

import React from 'react';
import {Article} from '@/lib/api';
import {useThemeStyles} from '@/hooks/useThemeStyles';

interface MagazineArticleCardProps {
    article: Article;
}

export const MagazineArticleCard: React.FC<MagazineArticleCardProps> = ({article}) => {
    const themeStyles = useThemeStyles();

    return (
        <article className="group cursor-pointer">
            <div className="overflow-hidden rounded-lg mb-4">
                <img
                    src={article.thumbnail || '/placeholder.jpg'}
                    alt={article.title}
                    className="w-full h-48 object-cover transition-transform duration-300 group-hover:scale-110"
                />
            </div>
            <h3
                className="text-xl font-bold mb-2 line-clamp-2 group-hover:underline"
                style={{color: themeStyles.foreground}}
            >
                {article.title}
            </h3>
            <p className="text-sm line-clamp-3 mb-3" style={{color: themeStyles.secondary}}>
                {article.excerpt || '暂无摘要...'}
            </p>
            <div className="flex items-center gap-3 text-xs" style={{color: themeStyles.secondary}}>
                <span>{article.author?.username}</span>
                <span>•</span>
                <span>{new Date(article.created_at).toLocaleDateString('zh-CN')}</span>
            </div>
        </article>
    );
};

export default MagazineArticleCard;
