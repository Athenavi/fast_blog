/**
 * SEO 工具函数
 * 生成 Open Graph、Twitter Cards 等 meta 标签
 */

export interface SEOMeta {
    title: string;
    description: string;
    url: string;
    image?: string;
    type?: 'article' | 'website';
    publishedTime?: string;
    modifiedTime?: string;
    author?: string;
    tags?: string[];
    siteName?: string;
}

/**
 * 生成 Open Graph meta 数据
 */
export function generateOpenGraph(meta: SEOMeta) {
    const {
        title,
        description,
        url,
        image,
        type = 'article',
        publishedTime,
        modifiedTime,
        author,
        tags,
        siteName = 'FastBlog',
    } = meta;

    return {
        title,
        description,
        url,
        type,
        siteName,
        images: image ? [{url: image}] : undefined,
        publishedTime,
        modifiedTime,
        authors: author ? [author] : undefined,
        tags,
    };
}

/**
 * 生成 Twitter Card meta 数据
 */
export function generateTwitterCard(meta: SEOMeta) {
    const {title, description, image} = meta;

    return {
        card: 'summary_large_image' as const,
        title,
        description,
        images: image ? [image] : undefined,
    };
}

/**
 * 生成完整的 SEO meta 数据（用于 Next.js Metadata）
 */
export function generateSEOMeta(meta: SEOMeta) {
    const {title, description, url, image} = meta;

    return {
        title,
        description,
        openGraph: generateOpenGraph(meta),
        twitter: generateTwitterCard(meta),
        alternates: {
            canonical: url,
        },
        robots: 'index, follow',
    };
}

/**
 * 生成文章 Schema.org JSON-LD 结构化数据
 */
export function generateArticleSchema(article: any, baseUrl: string = '') {
    const siteUrl = baseUrl || process.env.NEXT_PUBLIC_SITE_URL || 'http://localhost:3000';

    // 构建文章 URL
    const articleUrl = article.slug
        ? `${siteUrl}/blog/p/${article.slug}`
        : `${siteUrl}/blog/${article.id}.html`;

    // 获取作者信息
    const authors = article.authors && article.authors.length > 0
        ? article.authors.map((author: any) => ({
            '@type': 'Person',
            name: author.username,
            url: `${siteUrl}/author/${author.id}`,
        }))
        : [{
            '@type': 'Person',
            name: article.author_username || 'Unknown',
        }];

    // 提取标签
    const tags = article.tags ? article.tags.split(',').map((t: string) => t.trim()) : [];

    return {
        '@context': 'https://schema.org',
        '@type': 'BlogPosting',
        headline: article.title,
        description: article.seo_description || article.excerpt || article.content?.substring(0, 200),
        image: article.cover_image || article.og_image ? [article.cover_image || article.og_image] : undefined,
        datePublished: article.created_at,
        dateModified: article.updated_at,
        author: authors,
        publisher: {
            '@type': 'Organization',
            name: process.env.NEXT_PUBLIC_SITE_NAME || 'FastBlog',
            logo: {
                '@type': 'ImageObject',
                url: `${siteUrl}/logo.png`,
            },
        },
        mainEntityOfPage: {
            '@type': 'WebPage',
            '@id': articleUrl,
        },
        keywords: tags.join(', '),
        wordCount: article.content?.length || 0,
    };
}

/**
 * 生成面包屑导航 Schema.org JSON-LD
 */
export function generateBreadcrumbSchema(items: Array<{ name: string; url: string }>) {
    return {
        '@context': 'https://schema.org',
        '@type': 'BreadcrumbList',
        itemListElement: items.map((item, index) => ({
            '@type': 'ListItem',
            position: index + 1,
            name: item.name,
            item: item.url,
        })),
    };
}

/**
 * 生成网站 Schema.org JSON-LD
 */
export function generateWebsiteSchema(siteName: string = 'FastBlog', siteUrl: string = '') {
    const url = siteUrl || process.env.NEXT_PUBLIC_SITE_URL || 'http://localhost:3000';

    return {
        '@context': 'https://schema.org',
        '@type': 'WebSite',
        name: siteName,
        url: url,
        potentialAction: {
            '@type': 'SearchAction',
            target: `${url}/search?q={search_term_string}`,
            'query-input': 'required name=search_term_string',
        },
    };
}

/**
 * 从文章数据生成 SEO meta
 */
export function generateArticleSEO(article: any, baseUrl: string = '') {
    const siteUrl = baseUrl || process.env.NEXT_PUBLIC_SITE_URL || 'http://localhost:3000';

    // 构建文章 URL
    const articleUrl = article.slug
        ? `${siteUrl}/blog/p/${article.slug}`
        : `${siteUrl}/blog/${article.id}.html`;

    // 获取封面图片
    const ogImage = article.cover_image || article.og_image || null;

    // 提取作者信息
    let author = undefined;
    if (article.authors && article.authors.length > 0) {
        author = article.authors[0].username;
    } else if (article.author_username) {
        author = article.author_username;
    }

    // 提取标签
    const tags = article.tags ? article.tags.split(',').map((t: string) => t.trim()) : [];

    return generateSEOMeta({
        title: article.seo_title || article.title,
        description: article.seo_description || article.excerpt || article.content?.substring(0, 200) || '',
        url: articleUrl,
        image: ogImage,
        type: 'article',
        publishedTime: article.created_at,
        modifiedTime: article.updated_at,
        author,
        tags,
        siteName: process.env.NEXT_PUBLIC_SITE_NAME || 'FastBlog',
    });
}

/**
 * 生成多语言 hreflang 链接
 */
export function generateHreflangLinks(article: any, baseUrl: string = '') {
    const siteUrl = baseUrl || process.env.NEXT_PUBLIC_SITE_URL || 'http://localhost:3000';

    if (!article.i18n_versions || article.i18n_versions.length === 0) {
        return null;
    }

    const links: Array<{ hrefLang: string; href: string }> = [];

    // 添加当前语言版本
    const currentUrl = article.slug
        ? `${siteUrl}/blog/p/${article.slug}`
        : `${siteUrl}/blog/${article.id}.html`;

    // 添加所有翻译版本
    article.i18n_versions.forEach((version: any) => {
        const versionUrl = version.slug
            ? `${siteUrl}/${version.language_code}/blog/p/${version.slug}`
            : `${siteUrl}/${version.language_code}/blog/${article.id}.html`;

        links.push({
            hrefLang: version.language_code,
            href: versionUrl
        });
    });

    // 添加 x-default（使用主语言版本）
    links.push({
        hrefLang: 'x-default',
        href: currentUrl
    });

    return links;
}
