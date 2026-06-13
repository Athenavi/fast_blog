'use client';

import React from 'react';
import Head from 'next/head';

interface HreflangEntry {
  hreflang: string;
  href: string;
}

interface HreflangMetaProps {
  entries: HreflangEntry[];
  defaultLang?: string;
  defaultHref?: string;
}

export default function HreflangMeta({ entries, defaultLang, defaultHref }: HreflangMetaProps) {
  if (!entries || entries.length === 0) return null;

  return (
    <Head>
      {entries.map((entry, i) => (
        <link key={i} rel="alternate" hrefLang={entry.hreflang} href={entry.href} />
      ))}
      {defaultLang && defaultHref && (
        <link rel="alternate" hrefLang="x-default" href={defaultHref} />
      )}
    </Head>
  );
}
