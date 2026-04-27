'use client';

import React from 'react';
import Link from 'next/link';
import {ChevronRight, Home} from 'lucide-react';

interface BreadcrumbItem {
  name: string;
  url: string | null; // 允许 url 为 null，用于表示当前页面
}

interface BreadcrumbsProps {
  breadcrumbs?: BreadcrumbItem[];
  items?: BreadcrumbItem[]; // 兼容旧版本
  showHomeIcon?: boolean;
  separator?: React.ReactNode;
  className?: string;
}

/**
 * 面包屑导航组件
 * 
 * @example
 * ```tsx
 * <Breadcrumbs 
 *   breadcrumbs={[
 *     { name: '首页', url: '/' },
 *     { name: '技术教程', url: '/category/tech' },
 *     { name: 'FastAPI入门', url: '/article/fastapi-intro' }
 *   ]}
 * />
 * ```
 */
const Breadcrumbs: React.FC<BreadcrumbsProps> = ({
  breadcrumbs,
  items,
  showHomeIcon = true,
  separator = <ChevronRight className="w-4 h-4 text-gray-400" />,
  className = ''
}) => {
  // 兼容两种prop名称
  const breadcrumbItems = breadcrumbs || items || [];
  
  if (!breadcrumbItems || breadcrumbItems.length === 0) {
    return null;
  }

  return (
    <nav 
      aria-label="Breadcrumb" 
      className={`flex items-center space-x-2 text-sm text-gray-600 dark:text-gray-400 ${className}`}
    >
      <ol className="flex items-center space-x-2 flex-wrap">
        {breadcrumbItems.map((crumb, index) => {
          const isLast = index === breadcrumbItems.length - 1;
          
          return (
            <React.Fragment key={index}>
              <li className="flex items-center">
                {index > 0 && (
                  <span className="mx-2" aria-hidden="true">
                    {separator}
                  </span>
                )}
                
                {isLast ? (
                  // 最后一项：当前页面，不可点击
                  <span 
                    className="text-gray-900 dark:text-gray-100 font-medium truncate max-w-xs"
                    aria-current="page"
                  >
                    {showHomeIcon && index === 0 ? (
                      <span className="flex items-center gap-1">
                        <Home className="w-4 h-4" />
                        {crumb.name}
                      </span>
                    ) : (
                      crumb.name
                    )}
                  </span>
                ) : (
                    // 非最后一项：可点击链接（url 不能为 null）
                    crumb.url ? (
                        <Link
                            href={crumb.url}
                            className="hover:text-blue-600 dark:hover:text-blue-400 transition-colors duration-200 flex items-center"
                        >
                          {showHomeIcon && index === 0 ? (
                              <span className="flex items-center gap-1">
                          <Home className="w-4 h-4"/>
                                {crumb.name}
                        </span>
                          ) : (
                              crumb.name
                          )}
                        </Link>
                    ) : (
                        // 如果 url 为 null 但不是最后一项，显示为普通文本
                        <span className="text-gray-700 dark:text-gray-300">
                      {crumb.name}
                    </span>
                    )
                )}
              </li>
            </React.Fragment>
          );
        })}
      </ol>
      
      {/* JSON-LD 结构化数据（用于SEO） */}
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify({
            "@context": "https://schema.org",
            "@type": "BreadcrumbList",
            "itemListElement": breadcrumbItems.map((crumb, index) => ({
              "@type": "ListItem",
              "position": index + 1,
              "name": crumb.name,
              "item": `${process.env.NEXT_PUBLIC_SITE_URL || ''}${crumb.url}`
            }))
          })
        }}
      />
    </nav>
  );
};

export default Breadcrumbs;
