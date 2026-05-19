'use client';

import React from 'react';
import {generateArticleSchema, generateHreflangLinks} from '@/lib/seo';

/**
 * Schema.org 结构化数据组件
 * 在客户端注入 JSON-LD 脚本和 hreflang 标签
 */
const ArticleSchema: React.FC<{ article: any }> = ({article}) => {
    const schema = generateArticleSchema(article);
    const hreflangLinks = generateHreflangLinks(article);

    return (
        <>
            {/* Schema.org 结构化数据 */}
            <script
                type="application/ld+json"
                dangerouslySetInnerHTML={{__html: JSON.stringify(schema)}}
            />

            {/* Hreflang 多语言链接 */}
            {hreflangLinks && hreflangLinks.map((link, index) => (
                <link
                    key={index}
                    rel="alternate"
                    hrefLang={link.hrefLang}
                    href={link.href}
                />
            ))}
        </>
    );
};

export default ArticleSchema;
