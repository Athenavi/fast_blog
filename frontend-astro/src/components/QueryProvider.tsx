'use client';

import React, {useState} from 'react';
import {focusManager, QueryClient, QueryClientProvider} from '@tanstack/react-query';
import {ErrorBoundary} from '@/components/ui/ErrorBoundary';
import {ConfirmProvider} from '@/components/ui/confirm-provider';
import {I18nProvider} from '@/lib/i18n';
import {perfMark, perfMeasure} from '@/lib/perf-monitor';

export function QueryProvider({children}: {children: React.ReactNode}) {
  const [qc] = useState(() => {
    perfMark('query-client:create');
    const client = new QueryClient({
      defaultOptions: {
        queries: {
          staleTime: 60_000,
          gcTime: 5 * 60_000,
          retry: 1,
          retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 10_000),
          refetchOnWindowFocus: false,
          refetchOnMount: true,
          refetchOnReconnect: true,
          // 性能优化: 减少重复渲染
          structuralSharing: true,
          // 网络优化: 弱网模式下增加超时时间
          networkMode: 'online',
        },
        mutations: {
          retry: 0,
        },
      },
      // 开发模式: 性能监控
      logger: import.meta.env.DEV ? {
        log: console.log,
        warn: console.warn,
        error: console.error,
      } : undefined,
    });
    perfMark('query-client:created');
    perfMeasure('query-client:creation', 'query-client:create', 'query-client:created');

    // 性能优化: 仅在页面聚焦时重新获取数据
    focusManager.setEventListener((onFocus) => {
      window.addEventListener('focus', onFocus);
      return () => window.removeEventListener('focus', onFocus);
    });

    return client;
  });

  return (
      <ErrorBoundary>
        <I18nProvider>
          <QueryClientProvider client={qc}>
            <ConfirmProvider>
              {children}
            </ConfirmProvider>
          </QueryClientProvider>
        </I18nProvider>
      </ErrorBoundary>
  );
}
