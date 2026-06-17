'use client';

import React from 'react';

interface SchemaJsonLdProps {
  type: 'Article' | 'Organization' | 'WebSite' | 'BreadcrumbList' | 'FAQPage' | 'Person';
  data: Record<string, any>;
}

export default function SchemaJsonLd({ type, data }: SchemaJsonLdProps) {
  const schema = {
    '@context': 'https://schema.org',
    '@type': type,
    ...data,
  };

  return (
    <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(schema) }} />
  );
}

// Helper: Website schema
export function WebsiteSchema() {
  return (
    <SchemaJsonLd
      type="WebSite"
      data={{
        name: typeof window !== 'undefined' ? document.title?.split(' - ')[1] || 'FastBlog' : 'FastBlog',
        url: typeof window !== 'undefined' ? window.location.origin : '/',
        potentialAction: {
          '@type': 'SearchAction',
          target: {
            '@type': 'EntryPoint',
            urlTemplate: `${typeof window !== 'undefined' ? window.location.origin : ''}/search?q={search_term_string}`,
          },
          'query-input': 'required name=search_term_string',
        },
      }}
    />
  );
}

// Helper: Article schema
export function ArticleSchema({
  title,
  description,
  url,
  image,
  datePublished,
  dateModified,
  author,
}: {
  title: string;
  description?: string;
  url?: string;
  image?: string;
  datePublished?: string;
  dateModified?: string;
  author?: string;
}) {
  return (
    <SchemaJsonLd
      type="Article"
      data={{
        headline: title,
        description: description || title,
        url: url || (typeof window !== 'undefined' ? window.location.href : ''),
        ...(image ? { image } : {}),
        ...(datePublished ? { datePublished } : {}),
        ...(dateModified ? { dateModified } : {}),
        ...(author ? { author: { '@type': 'Person', name: author } } : {}),
      }}
    />
  );
}

// Helper: Organization schema
export function OrganizationSchema({
  name,
  url,
  logo,
}: {
  name: string;
  url?: string;
  logo?: string;
}) {
  return (
    <SchemaJsonLd
      type="Organization"
      data={{
        name,
        ...(url ? { url } : {}),
        ...(logo ? { logo } : {}),
      }}
    />
  );
}
