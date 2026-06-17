'use client';

import React from 'react';
import { ChevronRight, Home } from 'lucide-react';

interface BreadcrumbItem {
  name: string;
  url?: string;
}

interface BreadcrumbsProps {
  items: BreadcrumbItem[];
  className?: string;
}

export default function Breadcrumbs({ items, className = '' }: BreadcrumbsProps) {
  if (!items || items.length === 0) return null;

  const jsonLd = {
    '@context': 'https://schema.org',
    '@type': 'BreadcrumbList',
    itemListElement: [
      {
        '@type': 'ListItem',
        position: 1,
        name: '首页',
        item: typeof window !== 'undefined' ? window.location.origin + '/' : '/',
      },
      ...items.map((item, i) => ({
        '@type': 'ListItem',
        position: i + 2,
        name: item.name,
        ...(item.url ? { item: typeof window !== 'undefined' ? `${window.location.origin}${item.url}` : item.url } : {}),
      })),
    ],
  };

  return (
    <>
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />
      <nav aria-label="面包屑导航" className={`flex items-center gap-1 text-sm text-gray-500 dark:text-gray-400 ${className}`}>
        <a href="/" className="hover:text-gray-700 dark:hover:text-gray-200 transition-colors">
          <Home className="w-4 h-4" />
        </a>
        {items.map((item, i) => (
          <React.Fragment key={i}>
            <ChevronRight className="w-3.5 h-3.5 text-gray-300" />
            {item.url ? (
              <a href={item.url} className="hover:text-gray-700 dark:hover:text-gray-200 transition-colors truncate max-w-[200px]">
                {item.name}
              </a>
            ) : (
              <span className="text-gray-900 dark:text-white font-medium truncate max-w-[200px]">{item.name}</span>
            )}
          </React.Fragment>
        ))}
      </nav>
    </>
  );
}
